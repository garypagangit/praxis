"""Actual upstream CPU runtime and owned-staging controls; no pretrained model."""
import argparse
import copy
from pathlib import Path
import traceback

from common import bind_source, exact_tensor_report, provenance, save_json
from staged_source import StagedSource, bind_pool, bind_prefetcher


def run(source, work):
    import torch
    import torch.nn.functional as F
    from safetensors.torch import save_file
    runtime = bind_source(source)
    torch.set_num_threads(1)
    torch.manual_seed(41009)
    root = Path(work)
    root.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, action):
        try:
            detail = action()
            checks.append({'check': name, 'passed': True, 'detail': detail})
        except Exception as exc:
            checks.append({'check': name, 'passed': False, 'error': repr(exc),
                           'traceback': traceback.format_exc()})

    class Block(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.randn(8, 8) * .1, requires_grad=False)
            self.lora_A = torch.nn.Parameter(torch.randn(2, 8) * .1)
            self.lora_B = torch.nn.Parameter(torch.randn(8, 2) * .1)

        def forward(self, x):
            return x + torch.tanh(F.linear(x, self.weight) + F.linear(F.linear(x, self.lora_A), self.lora_B))

    reference_template = torch.nn.Sequential(*[Block() for _ in range(4)])
    paths = []
    for i, block in enumerate(reference_template):
        p = root / f'layer-{i}.safetensors'
        save_file({'weight': block.weight.detach().clone()}, str(p))
        paths.append(str(p))
    spec = {'weight': ((8, 8), 'float32')}

    def source_for(arm):
        if arm == 'ram':
            return runtime.RamSource(str(root), 4, spec, pin=False, shard_paths=paths)
        if arm == 'disk':
            return runtime.DiskSource(str(root), 4, spec, shard_paths=paths)
        return StagedSource(runtime, str(root), 4, spec, shard_paths=paths,
                            prefetch=arm == 'staged_prefetch', pin=False)

    def exercise(arm, corrupt=False):
        reference = copy.deepcopy(reference_template)
        src = source_for(arm)
        pool = runtime.LayerBufferPool(spec, n_buffers=2, device='cpu')
        if isinstance(src, StagedSource):
            bind_pool(pool, src)
        prefetcher = runtime.StreamPrefetcher(pool, src, 4)
        if isinstance(src, StagedSource):
            bind_prefetcher(prefetcher, src)
        blocks = []
        for i, block in enumerate(copy.deepcopy(reference_template)):
            block.weight = torch.nn.Parameter(torch.empty(8, 8, device='meta'), requires_grad=False)
            blocks.append(runtime.StreamedDecoderLayer(block, i, pool, prefetcher,
                                                        name_map={'weight': 'weight'}))
        streamed = torch.nn.Sequential(*blocks)
        if corrupt:
            with torch.no_grad():
                streamed[0].inner.lora_B[0, 0] += .25
        inputs = [torch.randn(2, 3, 8, generator=torch.Generator().manual_seed(100 + i)) for i in range(3)]
        opts = [torch.optim.SGD([p for p in m.parameters() if p.requires_grad], lr=.03)
                for m in (reference, streamed)]
        snapshots = [[], []]
        try:
            for step, x in enumerate(inputs):
                for side, model in enumerate((reference, streamed)):
                    if side:
                        prefetcher.prime()
                    opts[side].zero_grad(set_to_none=True)
                    output = model(x)
                    loss = output.square().mean()
                    loss.backward()
                    grads = {n.replace('.inner.', '.'): p.grad.detach().clone()
                             for n, p in model.named_parameters() if p.requires_grad and p.grad is not None}
                    assert len(grads) == 8 and all(torch.isfinite(v).all() for v in grads.values())
                    assert all(float(v.abs().sum()) > 0 for v in grads.values())
                    snapshots[side].append({'output': output.detach(), 'loss': loss.detach(), **grads})
                    opts[side].step()
            comparisons = [exact_tensor_report(a, b) for a, b in zip(*snapshots)]
            equal = all(c['passed'] for c in comparisons)
            assert equal is not corrupt, comparisons
            if isinstance(src, StagedSource):
                assert src.peak_slots <= 2 and src.peak_staging_bytes <= src.byte_bound
            return {'trajectory_steps': 3, 'comparisons': comparisons, 'negative_control': corrupt,
                    'layer_loads': pool.loads,
                    'staging': src.stats() if isinstance(src, StagedSource) else None}
        finally:
            close = getattr(src, 'close', None)
            if close:
                close()

    for arm in ('ram', 'disk', 'staged_sync', 'staged_prefetch'):
        check('all_gradients_and_trajectory_' + arm, lambda arm=arm: exercise(arm))
    check('corrupted_adapter_is_rejected', lambda: exercise('staged_prefetch', True))

    def owner_tripwire():
        src = source_for('disk')
        pool = runtime.LayerBufferPool(spec, n_buffers=2, device='cpu')
        try:
            pool.load_async(0, src)
            pool.load_async(2, src)
            try:
                pool.wait(0)
            except RuntimeError:
                return 'recycled owner rejected'
            raise AssertionError('recycled owner was accepted')
        finally:
            src.close()
    check('recycled_pool_ownership_is_rejected', owner_tripwire)

    def event_lifetime():
        src = source_for('staged_prefetch')
        class Event:
            calls = 0
            def synchronize(self):
                self.calls += 1
        event = Event()
        try:
            src.prepare(0)
            src.get(0, 'weight')
            src.copied(0, event)
            src.prepare(1)
            assert event.calls == 1
            return {'event_completed_before_reclaim': True}
        finally:
            src.close()
    check('copy_event_precedes_source_reclaim', event_lifetime)

    def missing_file():
        bad = paths.copy()
        bad[0] = str(root / 'absent.safetensors')
        src = StagedSource(runtime, str(root), 4, spec, shard_paths=bad, prefetch=True)
        try:
            try:
                src.prepare(0)
                src.get(0, 'weight')
            except FileNotFoundError:
                return 'read error surfaced'
            raise AssertionError('missing file accepted')
        finally:
            try:
                src.close()
            except FileNotFoundError:
                pass
            assert src.closed
    check('asynchronous_read_failure_is_visible', missing_file)

    def closed_source():
        src = source_for('staged_sync')
        src.close()
        src.close()
        try:
            src.get(0, 'weight')
        except RuntimeError:
            return 'idempotent close and read refusal'
        raise AssertionError('closed source accepted read')
    check('close_semantics', closed_source)

    def nan_refusal():
        assert not exact_tensor_report({'x': torch.tensor([float('nan')])},
                                       {'x': torch.tensor([float('nan')])})['passed']
        assert not exact_tensor_report({}, {})['passed']
        return 'nonfinite and empty comparisons rejected'
    check('comparison_cannot_pass_vacuously', nan_refusal)
    return {'scope': 'CPU instrumentation; generated toy blocks; no pretrained quality or GPU speed claim',
            'assigned': 10, 'completed': len(checks), 'passed': sum(c['passed'] for c in checks),
            'qualification_pass': len(checks) == 10 and all(c['passed'] for c in checks),
            'provenance': provenance(), 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--work', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = run(args.source, args.work)
    save_json(args.output, result)
    print(f"CPU controls: {result['passed']}/{result['assigned']}; pass={result['qualification_pass']}")
    raise SystemExit(0 if result['qualification_pass'] else 1)
