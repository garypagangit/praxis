"""Qualification-only owned staging; no claim of a novel caching algorithm.

The reader owns each tensor until the caller's H2D completion event finishes.
No vendor file is modified. Tiny-model integration refuses large embedding/head
pools because their copy lifetime is a separate interface not qualified here.
"""
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
import math


class StagedSource:
    def __init__(self, runtime_module, shard_dir, n_layers, spec, *,
                 shard_paths=None, slots=2, prefetch=True, pin=False):
        if type(slots) is not int or slots < 2:
            raise ValueError("at least two owned staging slots required")
        self.specs = runtime_module.RamSource._normalize_layer_specs(spec, n_layers)
        self.paths = runtime_module.RamSource._normalize_shard_paths(
            shard_dir, n_layers, shard_paths)
        self.sizes = [sum(math.prod(shape) * runtime_module._dtype_size(dtype)
                          for shape, dtype in s.values()) for s in self.specs]
        self.n_layers = n_layers
        self.slots, self.prefetch, self.pinned = slots, prefetch, pin
        self.entries = OrderedDict()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="soup009-read")
        self.closed = False
        self.previous = None
        self.direction = 1
        self.peak_slots = self.peak_staging_bytes = self.requested_read_bytes = 0
        self.reads = self.waited_copy_events = 0
        self.disk_bytes = sum(self.sizes)
        self.nbytes = 0
        self.byte_bound = sum(sorted(self.sizes, reverse=True)[:slots])

    def _read(self, idx):
        import torch
        from safetensors import safe_open
        tensors = {}
        with safe_open(self.paths[idx], framework="pt", device="cpu") as handle:
            for name, (shape, dtype) in self.specs[idx].items():
                view = handle.get_tensor(name)
                if tuple(view.shape) != tuple(shape) or str(view.dtype).split('.')[-1] != dtype:
                    raise ValueError("shard schema differs from frozen specification")
                owned = torch.empty(tuple(shape), dtype=view.dtype, device="cpu",
                                    pin_memory=self.pinned)
                owned.copy_(view)
                tensors[name] = owned
                del view, owned
        return tensors

    def _evict_one(self, protected):
        candidates = [(idx, entry) for idx, entry in self.entries.items() if idx != protected]
        if not candidates:
            raise RuntimeError("no reclaimable staging slot")
        # Prefer a copied tensor over speculative work not yet consumed.
        idx, entry = next(((i, e) for i, e in candidates if e['copied']), candidates[0])
        entry['future'].result()  # surface failures, including speculative failures
        if entry['event'] is not None:
            entry['event'].synchronize()
            self.waited_copy_events += 1
        del self.entries[idx]

    def _ensure(self, idx, protected=None):
        if self.closed:
            raise RuntimeError("source is closed")
        if not 0 <= idx < self.n_layers:
            raise IndexError(idx)
        if idx in self.entries:
            return
        while len(self.entries) >= self.slots:
            self._evict_one(protected)
        if self.prefetch:
            future = self.executor.submit(self._read, idx)
        else:
            future = Future()
            try:
                future.set_result(self._read(idx))
            except BaseException as exc:
                future.set_exception(exc)
        self.entries[idx] = {'future': future, 'copied': False, 'event': None}
        self.reads += 1
        self.requested_read_bytes += self.sizes[idx]
        self.nbytes = sum(self.sizes[i] for i in self.entries)
        self.peak_slots = max(self.peak_slots, len(self.entries))
        self.peak_staging_bytes = max(self.peak_staging_bytes, self.nbytes)
        if self.peak_staging_bytes > self.byte_bound:
            raise RuntimeError("staging byte bound exceeded")

    def prepare(self, idx):
        if self.previous is not None:
            if idx < self.previous:
                self.direction = -1
            elif idx > self.previous:
                self.direction = 1
        self.previous = idx
        self._ensure(idx, protected=idx)
        nxt = idx + self.direction
        if self.prefetch and 0 <= nxt < self.n_layers:
            self._ensure(nxt, protected=idx)

    def get(self, idx, name):
        self._ensure(idx, protected=idx)
        return self.entries[idx]['future'].result()[name]

    def copied(self, idx, event=None):
        entry = self.entries[idx]
        entry['copied'] = True
        entry['event'] = event

    def stats(self):
        return {'slots': self.slots, 'peak_slots': self.peak_slots,
                'peak_staging_bytes': self.peak_staging_bytes, 'byte_bound': self.byte_bound,
                'requested_read_bytes': self.requested_read_bytes, 'reads': self.reads,
                'waited_copy_events': self.waited_copy_events, 'pin': self.pinned,
                'prefetch': self.prefetch,
                'physical_read_bytes': None, 'physical_read_note': 'Use process I/O counters; logical reads are not physical disk traffic.'}

    def close(self):
        if self.closed:
            return
        try:
            for entry in self.entries.values():
                # Completed-but-unconsumed speculative errors still count.
                entry['future'].result()
                if entry['event'] is not None:
                    entry['event'].synchronize()
        finally:
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.entries.clear()
            self.nbytes = 0
            self.closed = True


def bind_pool(pool, staged):
    original = pool.load_async

    def load(idx, source, stream=None):
        if source is not staged:
            raise RuntimeError("unexpected source in qualified pool")
        staged.prepare(idx)
        slot = original(idx, source, stream)
        event = pool.events[slot] if pool.is_cuda and stream is not None else None
        staged.copied(idx, event)
        return slot

    pool.load_async = load


@contextmanager
def staged_disk_builder(runtime_module, *, prefetch, pin):
    """Substitute only source construction, restoring the vendor API immediately."""
    original = runtime_module.DiskSource

    def construct(shard_dir, n_layers, spec, **kwargs):
        return StagedSource(runtime_module, shard_dir, n_layers, spec,
                            prefetch=prefetch, pin=pin, **kwargs)

    runtime_module.DiskSource = construct
    try:
        yield
    finally:
        runtime_module.DiskSource = original


def bind_runtime(runtime):
    if runtime.large_pool is not None:
        runtime.close()
        raise RuntimeError("large embedding/head pool is outside this tiny-model qualification")
    bind_pool(runtime.pool, runtime.source)
    bind_prefetcher(runtime.prefetcher, runtime.source)


def bind_prefetcher(prefetcher, source):
    original = prefetcher.prime

    def prime():
        source.previous = None
        source.direction = 1
        return original()

    prefetcher.prime = prime
