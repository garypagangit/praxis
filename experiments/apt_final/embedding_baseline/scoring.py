"""Exact, bounded-memory nearest-neighbor scoring for a frozen training bank.

Reference rows retain multiplicity: deduplicating benign reference rows would
change the density estimate. Repeated query rows may be evaluated once and
expanded back to their original order. This is exact KDTree Euclidean search,
not approximate nearest-neighbor retrieval. Labels are never accepted here.
"""
from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping

import numpy as np
from sklearn.neighbors import KDTree


def _positive_integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(name + " must be a positive integer")
    return int(value)


def _matrix(values, name, *, allow_empty=False):
    array = np.asarray(values)
    if array.ndim != 2 or array.shape[1] < 1 or (not allow_empty and len(array) == 0):
        raise ValueError(name + " must be a nonempty two-dimensional numeric matrix")
    if array.dtype.kind not in "fiu":
        raise ValueError(name + " must contain real numeric values")
    # Copies isolate the frozen bank and avoid mutating caller-owned arrays.
    result = np.array(array, dtype=np.float64, order="C", copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError(name + " must contain only finite values")
    return result


def _array_digest(array):
    h = hashlib.sha256()
    h.update(str(array.shape).encode("ascii"))
    h.update(array.dtype.str.encode("ascii"))
    h.update(array.tobytes(order="C"))
    return h.hexdigest()


def sample_bank_indices(graph_sizes: Mapping[str, int], bank_size: int, seed: int):
    """Uniform sample without replacement over the union of eligible graph rows.

    Caller supplies only training graphs. Names are sorted before assigning
    global offsets, making this independent of dictionary insertion order.
    The return value contains original zero-based row IDs for every graph,
    including an empty int64 array when that graph contributed no rows.
    """
    bank_size = _positive_integer(bank_size, "bank_size")
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not graph_sizes or any(not isinstance(name, str) or not name for name in graph_sizes):
        raise ValueError("graph_sizes requires nonempty graph names")
    names = sorted(graph_sizes)
    sizes = [_positive_integer(graph_sizes[name], "graph size") for name in names]
    total = sum(sizes)
    selected = np.sort(np.random.default_rng(int(seed)).choice(total, min(bank_size, total), replace=False))
    result, offset = {}, 0
    for name, size in zip(names, sizes):
        start, stop = np.searchsorted(selected, [offset, offset + size])
        result[name] = (selected[start:stop] - offset).astype(np.int64, copy=True)
        offset += size
    return result


class ExactKNN:
    """Bank-only standardization followed by mean distance to exactly k rows."""

    def __init__(self, reference, k=10, epsilon=1e-3, leaf_size=40):
        started = time.perf_counter()
        self.k = _positive_integer(k, "k")
        self.leaf_size = _positive_integer(leaf_size, "leaf_size")
        self.epsilon = float(epsilon)
        if not np.isfinite(self.epsilon) or self.epsilon <= 0:
            raise ValueError("epsilon must be finite and positive")
        self.bank_raw = _matrix(reference, "reference")
        if self.k > len(self.bank_raw):
            raise ValueError("reference bank contains fewer than k rows")
        with np.errstate(over="ignore", invalid="ignore"):
            self.mean = np.mean(self.bank_raw, axis=0, dtype=np.float64)
            self.scale = np.maximum(np.std(self.bank_raw, axis=0, dtype=np.float64, ddof=0), self.epsilon)
            self.bank_scaled = (self.bank_raw - self.mean) / self.scale
        if not all(np.all(np.isfinite(a)) for a in (self.mean, self.scale, self.bank_scaled)):
            raise ValueError("reference statistics overflowed float64")
        self.tree = KDTree(self.bank_scaled, leaf_size=self.leaf_size, metric="euclidean")
        for array in (self.bank_raw, self.bank_scaled, self.mean, self.scale):
            array.setflags(write=False)
        self.fit_metadata = {
            "backend": "sklearn.neighbors.KDTree",
            "search": "exact",
            "metric": "euclidean",
            "aggregation": "arithmetic mean of distances to k reference rows",
            "k": self.k,
            "reference_rows": len(self.bank_raw),
            "dimensions": self.bank_raw.shape[1],
            "reference_multiplicity_preserved": True,
            "scale_fit": "training reference bank only; population standard deviation",
            "standard_deviation_floor": self.epsilon,
            "leaf_size": self.leaf_size,
            "dtype": "float64",
            "reference_sha256": _array_digest(self.bank_raw),
            "scaled_reference_sha256": _array_digest(self.bank_scaled),
            "fit_seconds": time.perf_counter() - started,
        }

    def artifact_arrays(self):
        """Portable numeric fit state; this deliberately does not pickle KDTree."""
        return {name: getattr(self, name).copy() for name in ("bank_raw", "bank_scaled", "mean", "scale")}

    def score(self, queries, chunk_size=4096, deduplicate_queries=True):
        started = time.perf_counter()
        chunk_size = _positive_integer(chunk_size, "chunk_size")
        if type(deduplicate_queries) is not bool:
            raise ValueError("deduplicate_queries must be a boolean")
        query = _matrix(queries, "queries", allow_empty=True)
        if query.shape[1] != self.bank_raw.shape[1]:
            raise ValueError("query and reference dimensions differ")
        if deduplicate_queries and len(query):
            unique, inverse = np.unique(query, axis=0, return_inverse=True)
        else:
            unique, inverse = query, None
        # Chunking bounds transformed query and distance output allocations.
        scores = np.empty(len(unique), dtype=np.float64)
        query_started = time.perf_counter()
        for start in range(0, len(unique), chunk_size):
            stop = min(start + chunk_size, len(unique))
            with np.errstate(over="ignore", invalid="ignore"):
                scaled = (unique[start:stop] - self.mean) / self.scale
            if not np.all(np.isfinite(scaled)):
                raise ValueError("transformed query overflowed float64")
            distance = self.tree.query(scaled, k=self.k, return_distance=True, sort_results=True)[0]
            if not np.all(np.isfinite(distance)):
                raise ValueError("Euclidean distance overflowed float64")
            scores[start:stop] = distance.mean(axis=1)
        search_seconds = time.perf_counter() - query_started
        result = scores[inverse] if inverse is not None else scores
        metadata = {
            **self.fit_metadata,
            "query_rows": len(query),
            "evaluated_query_rows": len(unique),
            "query_duplicates_reused": len(query) - len(unique),
            "deduplicate_queries": deduplicate_queries,
            "query_chunk_size": chunk_size,
            "query_distance_output_bound_rows": min(chunk_size, len(unique)),
            "search_seconds": search_seconds,
            "score_seconds": time.perf_counter() - started,
            "query_order_preserved": True,
        }
        return result, metadata
