"""Small, source-bound GPU qualification. No downloaded checkpoints or data.

Runs reviewed Soup APIs; a generated Llama validates instrumentation only.
All missing/failed assignments remain in the receipt. CUDA absence is failure.
"""
import argparse
import contextlib
import gc
import json
import os
from pathlib import Path
import time
import traceback

from common import bind_source, exact_tensor_report, provenance, save_json, sha
from staged_source import bind_runtime, staged_disk_builder

ARMS = ('ram', 'disk', 'staged_sync', 'staged_prefetch')
QUANTS = ('none', 'nf4')
SEQUENCES = (12, 64)


def memory_and_io():
    result = {}
    for filename, field in (('/proc/self/io', 'io'), ('/proc/self/status', 'status')):
        try:
            lines = Path(filename).read_text().splitlines()
            wanted = ('read_bytes:', 'write_bytes:', 'rchar:') if field == 'io' else ('VmRSS:', 'VmHWM:')
            result[field] = {s.split(':', 1)[0]: s.split(':', 1)[1].strip()
                             for s in lines if s.startswith(wanted)}
        except OSError:
            result[field] = None
    return result


def config_lora():
    from peft import LoraConfig, TaskType
    return LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, bias='none',
                      target_modules=['q_proj', 'v_proj'], task_type=TaskType.CAUSAL_LM)


def create_weights(path):
    import torch
    from transformers import LlamaConfig, LlamaForCausalLM
    from safetensors.torch import save_file
    torch.manual_seed(41009)
    config = LlamaConfig(vocab_size=64, hidden_size=64, intermediate_size=128,
                         num_hidden_layers=4, num_attention_heads=4, num_key_value_heads=2,
                         tie_word_embeddings=True, max_position_embeddings=256,
                         attention_dropout=0.0, use_cache=False)
    model = LlamaForCausalLM(config).float().eval()
    path.mkdir(parents=True, exist_ok=True)
    state = {k: v.detach().contiguous() for k, v in model.state_dict().items()}
    state.pop('lm_head.weight', None)
    save_file(state, str(path / 'model.safetensors'))
    config.save_pretrained(path)
    return {'kind': 'generated random tiny Llama; not a pretrained model',
            'parameters': sum(p.numel() for p in model.parameters()),
            'files': {p.name: sha(p) for p in sorted(path.iterdir()) if p.is_file()}}


def initialize_adapters(model, runtime):
    import torch
    result = {}
    # Per-name seeds make initialization independent of object construction order.
    for name, parameter in runtime.canonical_named_parameters(model):
        if 'lora_' not in name:
            continue
        seed = int.from_bytes(__import__('hashlib').sha256(name.encode()).digest()[:4], 'little')
        generator = torch.Generator(device='cpu').manual_seed(seed)
        with torch.no_grad():
            parameter.copy_((torch.randn(parameter.shape, generator=generator) * .02).to(parameter.device, parameter.dtype))
        result[name] = parameter.detach().cpu().clone()
    if len(result) != 16 or not all(float(p.abs().sum()) > 0 for p in result.values()):
        raise RuntimeError('expected sixteen nonzero adapter tensors')
    return result


def resident(weights, quant, runtime, *, matched=True):
    import torch
    from peft import get_peft_model
    from transformers import AutoModelForCausalLM
    kwargs = {'dtype': torch.bfloat16, 'device_map': {'': 'cuda'}, 'local_files_only': True,
              'trust_remote_code': False}
    if quant == 'nf4':
        kwargs['quantization_config'] = runtime.build_nf4_config('bfloat16')
    model = AutoModelForCausalLM.from_pretrained(str(weights), **kwargs)
    if quant == 'nf4' and matched:
        if runtime.install_dequant_forward(model) <= 0:
            raise RuntimeError('NF4 reference did not install matched dequant path')
    model.config.use_cache = False
    for p in model.parameters():
        p.requires_grad = False
    model = get_peft_model(model, config_lora())
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    initialize_adapters(model, runtime)
    return model


def streamed(weights, shard_dir, index, quant, arm, runtime):
    builder = (staged_disk_builder(runtime, prefetch=arm == 'staged_prefetch', pin=True)
               if arm.startswith('staged_') else contextlib.nullcontext())
    with builder:
        model, state = runtime.build_streamed_model(
            model_id=str(weights), shard_dir=str(shard_dir), index=index,
            lora_config=config_lora(), device='cuda', dtype='bfloat16', buffers=2,
            pin=True, require_pin=arm == 'ram', seed=3, quant=quant, double_quant=True,
            tier='ram' if arm == 'ram' else 'disk', trust_remote_code=False)
    try:
        if arm.startswith('staged_'):
            bind_runtime(state)
        initialize_adapters(model, runtime)
        if not any(p.is_meta for p in model.parameters()):
            raise RuntimeError('no meta parameters: streamed path not exercised')
        return model, state
    except BaseException:
        state.close()
        raise


def trajectory(model, seq, runtime, artifact):
    import torch
    from safetensors.torch import save_file
    snapshots = {}
    model.train()
    optim = torch.optim.SGD([p for p in model.parameters() if p.requires_grad], lr=.03)
    for step in range(2):
        generator = torch.Generator(device='cuda').manual_seed(900 + step)
        ids = torch.randint(0, 64, (1, seq), generator=generator, device='cuda')
        optim.zero_grad(set_to_none=True)
        output = model(input_ids=ids, labels=ids)
        output.loss.backward()
        snapshots[f'{step}/loss'] = output.loss.detach().cpu().clone()
        snapshots[f'{step}/logits'] = output.logits.detach().cpu().clone()
        grads = {n: p.grad for n, p in runtime.canonical_named_parameters(model) if p.requires_grad}
        if len(grads) != 16 or any(v is None for v in grads.values()):
            raise RuntimeError('missing assigned trainable gradients')
        for n, value in grads.items():
            if not torch.isfinite(value).all() or not float(value.abs().sum()) > 0:
                raise RuntimeError('nonfinite or vacuous gradient: ' + n)
            snapshots[f'{step}/grad/{n}'] = value.detach().cpu().clone()
        optim.step()
    for n, p in runtime.canonical_named_parameters(model):
        if p.requires_grad:
            snapshots['final/' + n] = p.detach().cpu().clone()
    if not all(torch.isfinite(v).all() for v in snapshots.values()):
        raise RuntimeError('nonfinite trajectory')
    artifact.parent.mkdir(parents=True, exist_ok=True)
    save_file({k: v.contiguous() for k, v in snapshots.items()}, str(artifact))
    return snapshots


def timing_block(weights, shard_dir, index, arm, runtime, block):
    import torch
    state = None
    model = None
    started = time.perf_counter()
    try:
        model, state = streamed(weights, shard_dir, index, 'nf4', arm, runtime)
        torch.cuda.synchronize()
        build_seconds = time.perf_counter() - started
        model.train()
        optimizer = torch.optim.SGD([p for p in model.parameters() if p.requires_grad], lr=0.0)
        generator = torch.Generator(device='cuda').manual_seed(12009)
        ids = torch.randint(0, 64, (1, 64), device='cuda', generator=generator)
        samples = []
        for step in range(5):
            before = memory_and_io()
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            start = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            loss = model(input_ids=ids, labels=ids).loss
            loss.backward()
            optimizer.step()
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            after = memory_and_io()
            if not torch.isfinite(loss):
                raise RuntimeError('nonfinite timing loss')
            samples.append({'step': step, 'warmup': step < 2, 'wall_seconds': elapsed,
                            'nonpadding_tokens': 64, 'loss': float(loss.detach()),
                            'gpu_allocated_peak_bytes': torch.cuda.max_memory_allocated(),
                            'gpu_reserved_peak_bytes': torch.cuda.max_memory_reserved(),
                            'process_before': before, 'process_after': after})
        return {'arm': arm, 'block': block, 'status': 'complete', 'build_seconds': build_seconds,
                'cache_condition': 'small store; warm after warmup; no cold-disk claim',
                'samples': samples, 'runtime': state.stats(),
                'staging': state.source.stats() if arm.startswith('staged_') else None}
    finally:
        if state is not None:
            state.close()
        del model, state
        gc.collect()
        torch.cuda.empty_cache()


def main(args):
    import torch
    runtime = bind_source(args.source)
    from soup_cli.utils.layer_shard import shard_checkpoint
    work, output = Path(args.work), Path(args.output)
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    result = {'scope': 'Tiny random-model instrumentation; warm-cache development timing only',
              'assigned_positive': 16, 'assigned_negative': 4,
              'comparisons': [], 'negative_controls': [], 'timing': [],
              'qualification_pass': False, 'provenance': provenance(), 'status': 'running'}
    receipt = output / 'GPU_QUALIFICATION.json'
    save_json(receipt, result)
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported(including_emulation=False):
        result.update(status='incomplete', reason='CUDA with hardware BF16 is required')
        save_json(receipt, result)
        return 2
    torch.set_num_threads(2)
    torch.manual_seed(41009)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    result['hardware'] = {'gpu': torch.cuda.get_device_name(0),
                          'capability': torch.cuda.get_device_capability(0),
                          'total_vram': torch.cuda.get_device_properties(0).total_memory,
                          'cuda_runtime': torch.version.cuda}
    weights = work / 'generated_weights'
    result['model'] = create_weights(weights)
    for quant in QUANTS:
        try:
            shard_dir = work / ('shards_' + quant)
            kwargs = {}
            if quant == 'nf4':
                probe = runtime.build_meta_skeleton(str(weights), dtype='bfloat16', quant=quant)
                kwargs = {'quant': quant, 'quant_suffixes': runtime.quantised_layer_suffixes(probe),
                          'quant_device': 'cuda', 'double_quant': True}
                del probe
            index = shard_checkpoint(str(weights), str(shard_dir), dtype='bfloat16', arch='llama', **kwargs)
            for seq in SEQUENCES:
                ref = resident(weights, quant, runtime)
                expected = trajectory(ref, seq, runtime, output / f'reference_{quant}_{seq}.safetensors')
                del ref
                gc.collect(); torch.cuda.empty_cache()
                for arm in ARMS:
                    state = None
                    model = None
                    row = {'quant': quant, 'seq': seq, 'arm': arm, 'passed': False}
                    try:
                        model, state = streamed(weights, shard_dir, index, quant, arm, runtime)
                        path = output / f'{arm}_{quant}_{seq}.safetensors'
                        got = trajectory(model, seq, runtime, path)
                        row.update(exact_tensor_report(expected, got), artifact=path.name,
                                   artifact_sha256=sha(path), runtime=state.stats())
                        if arm.startswith('staged_'):
                            row['staging'] = state.source.stats()
                            if row['staging']['peak_staging_bytes'] > row['staging']['byte_bound']:
                                row['passed'] = False
                        if arm == 'staged_prefetch':
                            changed = {k: v.clone() for k, v in got.items()}
                            first = next(k for k in changed if '/grad/' in k)
                            changed[first].view(-1)[0] += 1
                            rejected = not exact_tensor_report(expected, changed)['passed']
                            result['negative_controls'].append({'quant': quant, 'seq': seq,
                                'kind': 'deliberately corrupted recorded gradient', 'passed': rejected})
                    except Exception as exc:
                        row.update(error=repr(exc), traceback=traceback.format_exc())
                    finally:
                        if state is not None:
                            state.close()
                        del model, state
                        gc.collect(); torch.cuda.empty_cache()
                    result['comparisons'].append(row)
                    save_json(receipt, result)
        except Exception as exc:
            result.setdefault('infrastructure_errors', []).append({'quant': quant, 'error': repr(exc), 'traceback': traceback.format_exc()})
            save_json(receipt, result)
    existing = {(r['quant'], r['seq'], r['arm']) for r in result['comparisons']}
    for q in QUANTS:
        for s in SEQUENCES:
            for a in ARMS:
                if (q, s, a) not in existing:
                    result['comparisons'].append({'quant': q, 'seq': s, 'arm': a,
                        'passed': False, 'status': 'not_completed'})
    result['completed_positive'] = sum('artifact' in r for r in result['comparisons'])
    result['passed_positive'] = sum(r['passed'] for r in result['comparisons'])
    result['completed_negative'] = len(result['negative_controls'])
    result['passed_negative'] = sum(r['passed'] for r in result['negative_controls'])
    result['qualification_pass'] = (result['passed_positive'] == 16 and result['passed_negative'] == 4
                                    and not result.get('infrastructure_errors'))
    if result['qualification_pass']:
        order = ['disk', 'staged_sync', 'staged_prefetch']
        # All timing is development instrumentation; no efficacy p-value.
        for block in range(3):
            for arm in order[block:] + order[:block]:
                try:
                    row = timing_block(weights, work / 'shards_nf4', index, arm, runtime, block)
                except Exception as exc:
                    row = {'arm': arm, 'block': block, 'status': 'error',
                           'error': repr(exc), 'traceback': traceback.format_exc()}
                result['timing'].append(row)
                save_json(receipt, result)
    result['timing_assigned'] = 9
    result['timing_completed'] = sum(r['status'] == 'complete' for r in result['timing'])
    result['instrumentation_complete'] = result['qualification_pass'] and result['timing_completed'] == 9
    result['status'] = 'complete'
    save_json(receipt, result)
    print(json.dumps({k: result[k] for k in ['status', 'completed_positive', 'passed_positive', 'completed_negative', 'passed_negative', 'qualification_pass']}))
    return 0 if result['instrumentation_complete'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--work', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    # Bind before imports of Soup APIs, including those inside main.
    bind_source(args.source)
    raise SystemExit(main(args))
