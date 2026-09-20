"""Exact nearest-neighbor scoring with multiplicity-preserving duplicate compression.

This is a runtime optimization, not a new detector. Standardization must happen
on the full original bank before this class is constructed. No rows are sampled,
rounded, averaged, or removed from the mathematical reference multiset.
"""
from __future__ import annotations

import time

import numpy as np
import torch


def synchronize(device):
    if torch.device(device).type == "cuda":
        torch.cuda.synchronize(device)


class ExactFullReferenceKNN:
    """Same public scoring API as the frozen uncompressed implementation.

    At most k nearest *distinct* rows need to survive each tile: every distinct
    row has at least one original occurrence, so a row beyond those k cannot
    enter the expanded k-neighbor result. Final integer counts recover exactly
    k original occurrences, including a partial multiplicity at the boundary.
    Equal-distance boundary choices have the same weighted distance sum.
    """
    def __init__(self, bank, k, device="cuda:0", query_batch_size=128, reference_batch_size=16384):
        started = time.perf_counter()
        bank = np.asarray(bank)
        if bank.ndim != 2 or not len(bank) or bank.shape[1] == 0 or bank.dtype.kind not in "fiu" or not np.isfinite(bank).all():
            raise ValueError("Expected a finite nonempty numeric reference matrix")
        if isinstance(k, bool) or int(k) != k or not 1 <= k <= len(bank):
            raise ValueError("k must be an integer within the original reference population")
        if query_batch_size < 1 or reference_batch_size < 1 or int(query_batch_size) != query_batch_size or int(reference_batch_size) != reference_batch_size:
            raise ValueError("Chunk sizes must be positive integers")
        self.device = torch.device(device)
        self.k = int(k)
        self.query_batch_size = int(query_batch_size)
        self.reference_batch_size = int(reference_batch_size)
        self.original_rows, self.dimension = bank.shape
        unique_started = time.perf_counter()
        unique, counts = np.unique(bank, axis=0, return_counts=True)
        self.unique_construction_seconds = time.perf_counter() - unique_started
        if int(counts.sum()) != self.original_rows or np.any(counts < 1):
            raise RuntimeError("Invalid duplicate multiplicity inventory")
        self.unique_rows = len(unique)
        self.bank = torch.as_tensor(np.ascontiguousarray(unique), dtype=torch.float64, device=self.device)
        self.counts = torch.as_tensor(counts, dtype=torch.int64, device=self.device)
        synchronize(self.device)
        self.construction_seconds = time.perf_counter() - started

    def score(self, queries, check_budget=lambda: None):
        queries = np.asarray(queries)
        if queries.ndim != 2 or queries.shape[1] != self.dimension or queries.dtype.kind not in "fiu" or not np.isfinite(queries).all():
            raise ValueError("Expected finite numeric queries of the reference dimension")
        started = time.perf_counter()
        output = np.empty(len(queries), dtype=np.float64)
        with torch.no_grad():
            for offset in range(0, len(queries), self.query_batch_size):
                check_budget()
                query = torch.as_tensor(np.ascontiguousarray(queries[offset:offset + self.query_batch_size]),
                                        dtype=torch.float64, device=self.device)
                distances_best = torch.empty((len(query), 0), dtype=torch.float64, device=self.device)
                counts_best = torch.empty((len(query), 0), dtype=torch.int64, device=self.device)
                for reference_offset in range(0, self.unique_rows, self.reference_batch_size):
                    check_budget()
                    reference = self.bank[reference_offset:reference_offset + self.reference_batch_size]
                    count = self.counts[reference_offset:reference_offset + self.reference_batch_size]
                    distances = torch.cdist(query, reference, p=2, compute_mode="donot_use_mm_for_euclid_dist")
                    distances_all = torch.cat((distances_best, distances), dim=1)
                    counts_all = torch.cat((counts_best, count.expand(len(query), -1)), dim=1)
                    selected = torch.topk(distances_all, min(self.k, distances_all.shape[1]),
                                          largest=False, sorted=False, dim=1)
                    distances_best = selected.values
                    counts_best = torch.gather(counts_all, 1, selected.indices)
                distances_sorted, order = torch.sort(distances_best, dim=1)
                counts_sorted = torch.gather(counts_best, 1, order)
                previous_count = torch.cumsum(counts_sorted, dim=1) - counts_sorted
                remaining = torch.clamp(self.k - previous_count, min=0)
                used = torch.minimum(counts_sorted, remaining)
                if not torch.all(used.sum(dim=1) == self.k):
                    raise RuntimeError("Compressed nearest neighbors did not preserve k occurrences")
                output[offset:offset + len(query)] = ((distances_sorted * used).sum(dim=1) / self.k).cpu().numpy()
        synchronize(self.device)
        return output, {"seconds": time.perf_counter() - started, "query_rows": len(queries),
                        "reference_rows": self.original_rows, "original_reference_rows": self.original_rows,
                        "unique_reference_rows": self.unique_rows, "reference_occurrences_preserved": self.original_rows,
                        "duplicate_fraction": 1 - self.unique_rows / self.original_rows,
                        "unique_construction_seconds": self.unique_construction_seconds,
                        "construction_seconds": self.construction_seconds,
                        "k": self.k, "dimension": self.dimension, "reference_sampling": False,
                        "reference_duplicates_preserved": True, "integer_multiplicities_preserved": True,
                        "exactness_definition": "mean Euclidean distance of k nearest rows in original expanded multiset; float64 arithmetic",
                        "search": "exact", "distance": "direct_float64_euclidean",
                        "query_batch_size": self.query_batch_size,
                        "reference_batch_size": self.reference_batch_size, "device": str(self.device)}
