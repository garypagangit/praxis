"""Equal-budget normal reference banks and empirical calibration.

Only fitting graph rows enter reference banks. Clean and masked reference
vectors are two views of the same original entities; their multiplicity is
preserved. Pooled calibration likewise contains dependent views, and these
empirical tail probabilities do not establish a conformal coverage guarantee.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

from experiments.apt_final.embedding_baseline.scoring import ExactKNN, sample_bank_indices


ARMS = ("local_knn", "mlp_knn", "gin_knn")
NORMAL_GRAPHS = frozenset(("train0", "train1", "train2", "train3"))
# Domain separation keeps allocation distinct from sampling with bank_seed.
ALLOCATION_DOMAIN = 0x56494557  # ASCII VIEW


def _seed(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 0:
        raise ValueError("bank_seed must be a nonnegative integer")
    return int(value)


def _integer_vector(values, name, *, nonempty=False):
    result = np.asarray(values)
    if result.ndim != 1 or result.dtype.kind not in "iu" or (nonempty and len(result) == 0):
        raise ValueError(name + " must be a one-dimensional integer array")
    if np.any(result < 0) or (len(result) and np.max(result) > np.iinfo(np.int64).max):
        raise ValueError(name + " must contain nonnegative int64-compatible values")
    return np.array(result, dtype=np.int64, copy=True)


def _scores(values, name, *, nonempty=False):
    original = np.asarray(values)
    if original.ndim != 1 or original.dtype.kind not in "fiu" or (nonempty and len(original) == 0):
        raise ValueError(name + " must be a one-dimensional real numeric array")
    result = np.array(original, dtype=np.float64, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError(name + " must contain finite values")
    return result


def select_fit_rows(
    graph_sizes: Mapping[str, int],
    fit_graphs: Sequence[str],
    calibration_graph: str,
    validation_graph: str,
    bank_size: int = 8192,
    bank_seed: int = 3011,
):
    """Uniform original-row sample after enforcing the complete normal split.

    graph_sizes may also contain test0, but only the two named fitting graphs
    are ever supplied to the sampler. Sampling uses bank_seed alone, making
    the row set independent of encoder seed and representation.
    """
    if isinstance(fit_graphs, str):
        raise ValueError("fit_graphs must name two distinct normal graph files")
    fit = tuple(fit_graphs)
    if len(fit) != 2 or any(not isinstance(name, str) for name in fit):
        raise ValueError("fit_graphs must name two distinct normal graph files")
    if not isinstance(calibration_graph, str) or not isinstance(validation_graph, str):
        raise ValueError("calibration and validation must name normal graph files")
    roles = fit + (calibration_graph, validation_graph)
    if len(set(roles)) != 4 or set(roles) != NORMAL_GRAPHS:
        raise ValueError("roles must partition train0..train3 into two fit, one calibration, one validation")
    if not isinstance(graph_sizes, Mapping) or any(name not in graph_sizes for name in roles):
        raise ValueError("graph_sizes must contain every normal-role graph")
    for name in roles:
        size = graph_sizes[name]
        if isinstance(size, (bool, np.bool_)) or not isinstance(size, (int, np.integer)) or size < 1:
            raise ValueError("normal graph sizes must be positive integers")
    return sample_bank_indices({name: graph_sizes[name] for name in fit}, bank_size, _seed(bank_seed))


def _selected_view(path, row_ids):
    """Load primitive numeric arrays, reconstructing only selected entity rows."""
    with np.load(Path(path), allow_pickle=False) as view:
        node_type = _integer_vector(view["node_type"], "node_type", nonempty=True)
        degree = _scores(view["degree"], "degree", nonempty=True)
        if len(degree) != len(node_type) or np.any(degree < 0):
            raise ValueError("degree must be nonnegative and align with node_type")
        if len(row_ids) and row_ids[-1] >= len(node_type):
            raise ValueError("selected fitting row is outside its graph")
        selected = {}
        for arm in ARMS:
            unique = view[arm + "_unique"]
            if unique.ndim != 2 or min(unique.shape) < 1 or unique.dtype.kind not in "fiu":
                raise ValueError(arm + " unique vectors must be a nonempty real numeric matrix")
            if not np.all(np.isfinite(unique)):
                raise ValueError(arm + " unique vectors must be finite")
            inverse = _integer_vector(view[arm + "_inverse"], arm + " inverse", nonempty=True)
            if len(inverse) != len(node_type) or np.max(inverse) >= len(unique):
                raise ValueError(arm + " inverse must map every graph row to a valid vector")
            selected[arm] = np.array(unique[inverse[row_ids]], copy=True)
    return node_type, selected


def build_view_banks(caches, row_map, bank_seed=3011):
    """Build clean/pooled banks from a select_fit_rows result.

    caches must contain exactly the two fitting names in row_map and each
    maps 'clean' and 'masked' to numeric NPZ cache paths. Role validation must
    precede this call through select_fit_rows; this function has no labels or
    calibration/validation graph input. Original rows appear exactly once in
    each bank, including rows whose feature vectors are identical.

    For an odd population cap, floor(N/2) rows use clean views and the remainder
    use masked views. At the registered 8192-row budget this is 4096/4096.
    Metadata includes arrays intended for a numeric NPZ provenance artifact.
    """
    bank_seed = _seed(bank_seed)
    if not isinstance(row_map, Mapping) or len(row_map) != 2 or not set(row_map).issubset(NORMAL_GRAPHS):
        raise ValueError("row_map must contain exactly two normal fitting graphs")
    if not isinstance(caches, Mapping) or set(caches) != set(row_map):
        raise ValueError("cache graphs must equal the fitting row-map graphs")
    names = sorted(row_map)
    selected_rows = {}
    for name in names:
        rows = _integer_vector(row_map[name], name + " selected rows")
        if len(rows) > 1 and np.any(rows[1:] <= rows[:-1]):
            raise ValueError("selected row IDs must be distinct and sorted")
        selected_rows[name] = rows
    count = sum(map(len, selected_rows.values()))
    if count == 0:
        raise ValueError("reference bank must contain at least one selected fitting row")
    permutation = np.random.default_rng(np.random.SeedSequence([bank_seed, ALLOCATION_DOMAIN])).permutation(count)
    pooled_is_masked = np.zeros(count, dtype=np.bool_)
    pooled_is_masked[permutation[count // 2:]] = True
    pieces = {kind: {arm: [] for arm in ARMS} for kind in ("clean", "pooled")}
    row_graph, row_id, offset = [], [], 0
    widths = {}
    for graph_index, name in enumerate(names):
        if not isinstance(caches[name], Mapping) or set(caches[name]) != {"clean", "masked"}:
            raise ValueError("each fitting cache requires exactly clean and masked views")
        rows = selected_rows[name]
        clean_type, clean = _selected_view(caches[name]["clean"], rows)
        masked_type, masked = _selected_view(caches[name]["masked"], rows)
        if not np.array_equal(clean_type, masked_type):
            raise ValueError("clean and masked cache views have different node_type row ordering")
        mask = pooled_is_masked[offset:offset + len(rows)]
        for arm in ARMS:
            if clean[arm].shape != masked[arm].shape:
                raise ValueError("clean and masked vector dimensions differ for " + arm)
            width = clean[arm].shape[1]
            if arm in widths and widths[arm] != width:
                raise ValueError("vector dimensions differ between fitting graphs for " + arm)
            widths[arm] = width
            pieces["clean"][arm].append(clean[arm])
            pieces["pooled"][arm].append(np.where(mask[:, None], masked[arm], clean[arm]))
        row_graph.append(np.full(len(rows), graph_index, dtype=np.int64))
        row_id.append(rows)
        offset += len(rows)
    banks = {kind: {arm: np.concatenate(parts, axis=0) for arm, parts in value.items()}
             for kind, value in pieces.items()}
    metadata = {
        "graph_names": names,
        "bank_row_graph": np.concatenate(row_graph),
        "bank_row_id": np.concatenate(row_id),
        "pooled_is_masked": pooled_is_masked,
        "bank_rows": count,
        "clean_rows": count - int(pooled_is_masked.sum()),
        "masked_rows": int(pooled_is_masked.sum()),
        "bank_seed": bank_seed,
        "allocation_domain": ALLOCATION_DOMAIN,
        "allocation": "default_rng(SeedSequence([bank_seed, allocation_domain])).permutation; second half masked",
        "reference_multiplicity_preserved": True,
        "row_order": "sorted graph names, then sorted original node rows",
    }
    return banks, metadata


def fit_detectors(banks, k=10, epsilon=1e-3):
    """Fit two banks per representation; reuse clean scores across calibrations."""
    if not isinstance(banks, Mapping) or set(banks) != {"clean", "pooled"}:
        raise ValueError("banks must contain exactly clean and pooled reference banks")
    rows = set()
    for strategy in banks:
        if not isinstance(banks[strategy], Mapping) or set(banks[strategy]) != set(ARMS):
            raise ValueError("each reference bank requires every registered representation")
        for values in banks[strategy].values():
            if np.ndim(values) != 2:
                raise ValueError("reference vectors must be matrices")
            rows.add(len(values))
    if len(rows) != 1:
        raise ValueError("all reference banks must have the same row budget")
    return {kind: {arm: ExactKNN(banks[kind][arm], k=k, epsilon=epsilon) for arm in ARMS}
            for kind in ("clean", "pooled")}


def pool_calibration(clean_scores, masked_scores):
    """Concatenate equal-mass dependent views; no conformal guarantee is made."""
    clean = _scores(clean_scores, "clean calibration", nonempty=True)
    masked = _scores(masked_scores, "masked calibration", nonempty=True)
    if len(clean) != len(masked):
        raise ValueError("clean and masked calibration must cover the same number of entities")
    return np.concatenate((clean, masked))


def empirical_tail_margin(calibration, query_scores, alpha=0.01):
    """Tie-conservative empirical p; return (log(alpha/p), p), alert at >=0."""
    cal = _scores(calibration, "calibration", nonempty=True)
    query = _scores(query_scores, "query scores")
    if isinstance(alpha, (bool, np.bool_)):
        raise ValueError("alpha must be finite and strictly between zero and one")
    alpha = float(alpha)
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and strictly between zero and one")
    # side='left' counts all reference scores tied with the query as >= query.
    at_least = len(cal) - np.searchsorted(np.sort(cal), query, side="left")
    p = (1.0 + at_least) / (len(cal) + 1.0)
    return np.log(alpha / p), p
