"""Audit and passively normalize MAGIC CADETS/THEIA graphs for static development.

This module never calls pickle.load, a reducer, a pickle global, Torch, or DGL.
It interprets a small pickle opcode subset into inert records, then reads the
documented DGL COO and legacy Torch storage bytes as NumPy arrays. Unknown
globals, opcodes, storage formats, graph layouts, and non-contiguous views fail.
It is deliberately an adapter for the checked MAGIC archives, not a general
unpickler. NPZ outputs need only ``numpy.load(..., allow_pickle=False)``.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import pickletools
import struct
import subprocess
import zipfile

import numpy as np


class DataError(ValueError):
    """Input does not satisfy this narrowly scoped data contract."""


@dataclass(eq=False)
class Symbol:
    kind: str
    target: object
    args: object = None
    state: object = None


ALLOWED_GLOBALS = frozenset({
    "dgl.heterograph.DGLGraph", "dgl._ffi.object._new_object",
    "dgl.heterograph_index.HeteroGraphIndex",
    "dgl.heterograph_index.HeteroPickleStates", "builtins.bytearray",
    "torch._utils._rebuild_tensor_v2", "torch.storage._load_from_bytes",
    "collections.OrderedDict", "dgl.frame.Frame", "dgl.frame.Column",
    "builtins.getattr", "dgl.frame.Scheme", "torch.LongStorage",
    "torch.FloatStorage",
})
STATUS = "STATIC_DEVELOPMENT_ONLY"


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_bytes(path: str | Path, expected_hash: str) -> bytes:
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise DataError("Source hash mismatch")
    return data


def passive_pickle(stream: bytes | io.BytesIO, *, symbolic: bool = False,
                   audit: dict | None = None):
    """Read primitive containers; optionally retain known object tokens inertly.

    Even in symbolic mode REDUCE/NEWOBJ/BUILD never execute their targets.
    Multiple legacy Torch pickle sections can be read from one BytesIO.
    """
    stream = io.BytesIO(stream) if isinstance(stream, bytes) else stream
    stack, memo, mark = [], {}, object()
    counts, globals_seen = Counter(), set()

    def pop_mark():
        for i in range(len(stack) - 1, -1, -1):
            if stack[i] is mark:
                values = stack[i + 1:]
                del stack[i:]
                return values
        raise DataError("Pickle mark missing")

    def global_token(name):
        if not symbolic or name not in ALLOWED_GLOBALS:
            raise DataError("Pickle global refused: " + name)
        globals_seen.add(name)
        return Symbol("global", name)

    for op, arg, _ in pickletools.genops(stream):
        name = op.name
        counts[name] += 1
        if name in {"PROTO", "FRAME"}:
            continue
        if name == "STOP":
            if len(stack) != 1:
                raise DataError("Unexpected pickle stack at STOP")
            if audit is not None:
                audit.update(opcodes=dict(sorted(counts.items())),
                             globals=sorted(globals_seen),
                             globals_or_reducers_executed=0)
            return stack[0]
        if name == "MARK":
            stack.append(mark)
        elif name in {"BININT", "BININT1", "BININT2", "INT", "LONG", "LONG1", "LONG4",
                      "BINUNICODE", "SHORT_BINUNICODE", "BINUNICODE8", "UNICODE",
                      "BINBYTES", "SHORT_BINBYTES", "BINBYTES8", "BINFLOAT", "FLOAT"}:
            stack.append(arg)
        elif name in {"NONE", "NEWTRUE", "NEWFALSE"}:
            stack.append({"NONE": None, "NEWTRUE": True, "NEWFALSE": False}[name])
        elif name == "EMPTY_TUPLE":
            stack.append(())
        elif name == "EMPTY_LIST":
            stack.append([])
        elif name == "EMPTY_DICT":
            stack.append({})
        elif name in {"TUPLE1", "TUPLE2", "TUPLE3"}:
            n = int(name[-1]); values = tuple(stack[-n:]); del stack[-n:]
            stack.append(values)
        elif name == "TUPLE":
            stack.append(tuple(pop_mark()))
        elif name == "LIST":
            stack.append(pop_mark())
        elif name == "DICT":
            values = pop_mark()
            if len(values) % 2:
                raise DataError("Odd dictionary item count")
            stack.append(dict(zip(values[::2], values[1::2])))
        elif name == "APPEND":
            item = stack.pop()
            if type(stack[-1]) is not list:
                raise DataError("APPEND target must be a primitive list")
            stack[-1].append(item)
        elif name == "APPENDS":
            values = pop_mark()
            if type(stack[-1]) is not list:
                raise DataError("APPENDS target must be a primitive list")
            stack[-1].extend(values)
        elif name == "SETITEM":
            value, key = stack.pop(), stack.pop()
            if type(stack[-1]) is not dict:
                raise DataError("SETITEM target must be a primitive dict")
            stack[-1][key] = value
        elif name == "SETITEMS":
            values = pop_mark()
            if type(stack[-1]) is not dict or len(values) % 2:
                raise DataError("Invalid SETITEMS")
            stack[-1].update(zip(values[::2], values[1::2]))
        elif name == "MEMOIZE":
            memo[len(memo)] = stack[-1]
        elif name in {"BINPUT", "LONG_BINPUT", "PUT"}:
            memo[int(arg)] = stack[-1]
        elif name in {"BINGET", "LONG_BINGET", "GET"}:
            stack.append(memo[int(arg)])
        elif name == "GLOBAL":
            module, attr = arg.split(" ", 1)
            stack.append(global_token(module + "." + attr))
        elif name == "STACK_GLOBAL":
            attr, module = stack.pop(), stack.pop()
            if type(module) is not str or type(attr) is not str:
                raise DataError("Non-string pickle global")
            stack.append(global_token(module + "." + attr))
        elif name in {"REDUCE", "NEWOBJ"}:
            if not symbolic:
                raise DataError("Object pickle refused")
            args, target = stack.pop(), stack.pop()
            if not isinstance(target, Symbol) or not isinstance(args, tuple):
                raise DataError("Unexpected object constructor token")
            stack.append(Symbol(name.lower(), target, args))
        elif name == "BUILD":
            state = stack.pop()
            if not symbolic or not isinstance(stack[-1], Symbol):
                raise DataError("Object state refused")
            stack[-1].state = state
        elif name == "BINPERSID":
            if not symbolic:
                raise DataError("Persistent reference refused")
            stack.append(Symbol("persistent", stack.pop()))
        else:
            raise DataError("Unsupported pickle opcode: " + name)
    raise DataError("Pickle did not reach STOP")


def target_name(value):
    return value.target if isinstance(value, Symbol) and value.kind == "global" else None


def require_call(value, name):
    if not isinstance(value, Symbol) or value.kind != "reduce" or target_name(value.target) != name:
        raise DataError("Expected inert call to " + name)
    return value.args


def legacy_storage(data: bytes) -> np.ndarray:
    stream = io.BytesIO(data)
    magic = passive_pickle(stream)
    version = passive_pickle(stream)
    info = passive_pickle(stream)
    if magic != 119547037146038801333356 or version != 1001 or info.get("little_endian") is not True:
        raise DataError("Unsupported legacy Torch storage header")
    storage = passive_pickle(stream, symbolic=True)
    keys = passive_pickle(stream)
    if not isinstance(storage, Symbol) or storage.kind != "persistent":
        raise DataError("Missing storage descriptor")
    desc = storage.target
    if not isinstance(desc, tuple) or len(desc) != 6:
        raise DataError("Unsupported storage descriptor")
    kind, dtype, key, device, count, view = desc
    dt = {"torch.LongStorage": "<i8", "torch.FloatStorage": "<f4"}.get(target_name(dtype))
    if kind != "storage" or dt is None or device != "cpu" or view is not None or keys != [key]:
        raise DataError("Unsupported storage type/device/view")
    if type(count) is not int or count < 0:
        raise DataError("Invalid storage length")
    raw_count = stream.read(8)
    if len(raw_count) != 8 or struct.unpack("<Q", raw_count)[0] != count:
        raise DataError("Storage length header mismatch")
    offset = stream.tell()
    if len(data) - offset != count * np.dtype(dt).itemsize:
        raise DataError("Storage payload length mismatch")
    return np.frombuffer(data, dtype=dt, count=count, offset=offset)


def tensor_array(value) -> np.ndarray:
    args = require_call(value, "torch._utils._rebuild_tensor_v2")
    if len(args) != 6:
        raise DataError("Unsupported tensor constructor")
    storage, offset, shape, strides, requires_grad, hooks = args
    blob = require_call(storage, "torch.storage._load_from_bytes")
    if len(blob) != 1 or type(blob[0]) is not bytes or requires_grad:
        raise DataError("Unsupported tensor storage")
    if require_call(hooks, "collections.OrderedDict") != ():
        raise DataError("Unexpected tensor hooks")
    if type(shape) is not tuple or any(type(x) is not int or x < 0 for x in shape):
        raise DataError("Invalid tensor shape")
    expected = []
    stride = 1
    for n in reversed(shape):
        expected.insert(0, stride); stride *= n
    if offset != 0 or strides != tuple(expected):
        raise DataError("Only complete contiguous tensors are supported")
    array = legacy_storage(blob[0])
    if array.size != stride:
        raise DataError("Tensor shape/storage mismatch")
    return array.reshape(shape)


def object_state(value, name):
    if not isinstance(value, Symbol) or value.kind != "newobj" or target_name(value.target) != name:
        raise DataError("Unexpected DGL object")
    if value.args != () or type(value.state) is not dict:
        raise DataError("Unexpected DGL object state")
    return value.state


def frame_arrays(value):
    state = object_state(value, "dgl.frame.Frame")
    columns = state["_columns"]
    if set(columns) != {"type", "attr"}:
        raise DataError("Unexpected graph attributes")
    arrays = {}
    for key, column in columns.items():
        col = object_state(column, "dgl.frame.Column")
        if any(col.get(k) is not None for k in ("index", "device", "deferred_dtype", "_data_nd")):
            raise DataError("Deferred/indexed columns are unsupported")
        arrays[key] = tensor_array(col["storage"])
        if len(arrays[key]) != state["_num_rows"]:
            raise DataError("Column row count mismatch")
    return arrays


def validate_graph_arrays(node_type, src, dst, relation, node_dim, edge_dim):
    for name, array in (("node_type", node_type), ("src", src), ("dst", dst), ("relation", relation)):
        if array.ndim != 1 or array.dtype.kind not in "iu":
            raise DataError(name + " must be a one-dimensional integer array")
    if not len(node_type) or not len(src) or len(src) != len(dst) or len(src) != len(relation):
        raise DataError("Empty graph or unequal edge lengths")
    if min(int(src.min()), int(dst.min())) < 0 or max(int(src.max()), int(dst.max())) >= len(node_type):
        raise DataError("Edge endpoint outside graph")
    if node_type.min() < 0 or node_type.max() >= node_dim or relation.min() < 0 or relation.max() >= edge_dim:
        raise DataError("Type ID outside metadata dimensions")


def assert_one_hot(types, attrs, dim):
    if attrs.shape != (len(types), dim) or attrs.dtype.kind != "f":
        raise DataError("Unexpected one-hot attribute shape/type")
    # Check exact binary values and the known type column without allocating another dense matrix.
    if not np.all((attrs == 0) | (attrs == 1)) or not np.all(attrs.sum(axis=1) == 1):
        raise DataError("Attributes are not one-hot")
    if not np.all(attrs[np.arange(len(types)), types] == 1):
        raise DataError("One-hot attributes disagree with type IDs")


def extract_graph(data: bytes, node_dim: int, edge_dim: int):
    audit = {}
    stream = io.BytesIO(data)
    root = passive_pickle(stream, symbolic=True, audit=audit)
    if stream.tell() != len(data):
        raise DataError("Trailing data after graph pickle")
    state = object_state(root, "dgl.heterograph.DGLGraph")
    if state["_canonical_etypes"] != [("_N", "_E", "_N")]:
        raise DataError("Only one homogeneous COO graph is supported")
    graph = state["_graph"]
    if require_call(graph, "dgl._ffi.object._new_object")[0].target != "dgl.heterograph_index.HeteroGraphIndex":
        raise DataError("Unexpected graph index")
    index = graph.state
    if require_call(index, "dgl._ffi.object._new_object")[0].target != "dgl.heterograph_index.HeteroPickleStates":
        raise DataError("Unexpected graph pickle state")
    version, meta, tensors = index.state
    meta_args = require_call(meta, "builtins.bytearray")
    if version != 2 or len(meta_args) != 1 or type(meta_args[0]) is not bytes or len(tensors) != 2:
        raise DataError("Expected DGL version-2 COO serialization")
    meta_bytes = meta_args[0]
    # For this homogeneous version-2 layout, the tail is node-count vector
    # (length=1), node count, pinned flag, SparseFormat::kCOO=1, sorted flags.
    if len(meta_bytes) != 232:
        raise DataError("Unknown DGL graph metadata layout")
    ntypes, n_nodes, pinned, fmt, row_sorted, col_sorted = struct.unpack("<QQBIBB", meta_bytes[-23:])
    if ntypes != 1 or pinned != 0 or fmt != 1 or row_sorted not in (0, 1) or col_sorted not in (0, 1):
        raise DataError("Unsupported DGL sparse metadata")
    if len(state["_node_frames"]) != 1 or len(state["_edge_frames"]) != 1:
        raise DataError("Unexpected graph frame count")
    nodes = frame_arrays(state["_node_frames"][0])
    edges = frame_arrays(state["_edge_frames"][0])
    src, dst = [tensor_array(t) for t in tensors]
    arrays = {"node_type": nodes["type"], "src": src, "dst": dst, "relation": edges["type"]}
    validate_graph_arrays(**arrays, node_dim=node_dim, edge_dim=edge_dim)
    if n_nodes != len(arrays["node_type"]):
        raise DataError("DGL metadata node count disagrees with node column")
    assert_one_hot(nodes["type"], nodes["attr"], node_dim)
    assert_one_hot(edges["type"], edges["attr"], edge_dim)
    audit.update(dgl_sparse_format="COO", dgl_pickle_version=version,
                 dgl_metadata_sha256=hashlib.sha256(meta_bytes).hexdigest(),
                 node_attributes=["type", "attr"], edge_attributes=["type", "attr"],
                 one_hot_matches_type=True, timestamps_present=False, uuid_mapping_present=False)
    return {k: v.astype(np.int64, copy=True) for k, v in arrays.items()}, audit


def binary_labels(n_nodes: int, indices, *, training: bool = False,
                  accept_upstream_benign_assumption: bool = False):
    if type(n_nodes) is not int or n_nodes < 1:
        raise DataError("Node count must be a positive integer")
    if training:
        if not accept_upstream_benign_assumption or indices:
            raise DataError("Training labels require explicit upstream-benign assumption and no indices")
        return np.zeros(n_nodes, dtype=np.int8)
    if any(type(x) is not int or x < 0 or x >= n_nodes for x in indices):
        raise DataError("Malicious index outside graph or not an integer")
    if len(set(indices)) != len(indices):
        raise DataError("Duplicate malicious indices")
    y = np.zeros(n_nodes, dtype=np.int8)
    y[indices] = 1
    return y


def counts(array):
    values, count = np.unique(array, return_counts=True)
    return {str(int(v)): int(n) for v, n in zip(values, count)}


def graph_stats(arrays):
    n, e = len(arrays["node_type"]), len(arrays["src"])
    indegree = np.bincount(arrays["dst"], minlength=n)
    outdegree = np.bincount(arrays["src"], minlength=n)
    pairs = arrays["src"] * np.int64(n) + arrays["dst"]
    stats = {"n_nodes": n, "n_edges": e, "label_counts": counts(arrays["y"]),
             "node_type_counts": counts(arrays["node_type"]), "relation_counts": counts(arrays["relation"]),
             "self_edges": int(np.count_nonzero(arrays["src"] == arrays["dst"])),
             "duplicate_directed_pairs": e - len(np.unique(pairs)),
             "isolated_nodes": int(np.count_nonzero(indegree + outdegree == 0))}
    for name, degree in (("in_degree", indegree), ("out_degree", outdegree)):
        stats[name] = {"min": int(degree.min()), "max": int(degree.max()),
                       "mean": float(degree.mean()),
                       "quantiles_0_50_90_99_100": np.quantile(degree, [0, .5, .9, .99, 1]).tolist()}
    h = hashlib.sha256()
    for key in sorted(arrays):
        h.update(key.encode()); h.update(str(arrays[key].shape).encode()); h.update(arrays[key].tobytes())
    stats["normalized_content_sha256"] = h.hexdigest()
    return stats


def source_split_manifest(parser_path):
    tree = ast.parse(Path(parser_path).read_text(encoding="utf-8"))
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "metadata" for t in statement.targets):
            return ast.literal_eval(statement.value)
    raise DataError("Upstream parser split table not found")


def normalize_dataset(magic_root: Path, dataset: str, output_root: Path, source_commit: str, splits):
    archive = magic_root / "data" / dataset / "graphs.zip"
    rel = archive.relative_to(magic_root).as_posix()
    committed = subprocess.run(["git", "-C", str(magic_root), "show", f"{source_commit}:{rel}"],
                               check=True, capture_output=True).stdout
    expected = hashlib.sha256(committed).hexdigest()
    data = checked_bytes(archive, expected)
    out = output_root / dataset
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": dataset, "status": STATUS, "archive_sha256": expected,
                "archive_bytes": len(data), "matches_upstream_git_blob": True,
                "source_split_files": splits[dataset], "graphs": []}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise DataError("Duplicate archive members")
        meta_bytes = z.read("metadata.json")
        metadata = json.loads(meta_bytes)
        if metadata["n_train"] != 4 or metadata["n_test"] != 1:
            raise DataError("This adapter expects four training graphs and one labeled test graph")
        expected_names = {"metadata.json", "test0.pkl", *(f"train{i}.pkl" for i in range(4))}
        if set(names) != expected_names:
            raise DataError("Unexpected archive members")
        malicious, malicious_names = metadata["malicious"]
        if len(malicious) != len(malicious_names):
            raise DataError("Malicious index/name metadata lengths differ")
        manifest["metadata"] = {"sha256": hashlib.sha256(meta_bytes).hexdigest(),
            "node_feature_dim": metadata["node_feature_dim"], "edge_feature_dim": metadata["edge_feature_dim"],
            "n_train": 4, "n_test": 1, "malicious_index_count": len(malicious),
            "malicious_name_count": len(malicious_names), "malicious_indices_unique": len(set(malicious)) == len(malicious),
            "semantic_type_name_map_available": False}
        for name in [*(f"train{i}.pkl" for i in range(4)), "test0.pkl"]:
            raw = z.read(name)
            arrays, decoding = extract_graph(raw, metadata["node_feature_dim"], metadata["edge_feature_dim"])
            train = name.startswith("train")
            arrays["y"] = binary_labels(len(arrays["node_type"]), [] if train else malicious,
                training=train, accept_upstream_benign_assumption=train)
            path = out / (Path(name).stem + ".npz")
            np.savez_compressed(path, **arrays)
            row = {"source_member": name, "source_sha256": hashlib.sha256(raw).hexdigest(),
                "source_bytes": len(raw), "npz": path.relative_to(output_root).as_posix(),
                "npz_sha256": sha256(path), "npz_bytes": path.stat().st_size,
                "split": "upstream_train" if train else "upstream_test",
                "label_basis": "UPSTREAM_FILTERED_BENIGN_ASSUMPTION" if train else "UPSTREAM_THREATRACE_METADATA_INDICES",
                "decoding": decoding, **graph_stats(arrays)}
            manifest["graphs"].append(row)
            print(json.dumps({"dataset": dataset, "graph": name, "nodes": row["n_nodes"],
                              "edges": row["n_edges"], "labels": row["label_counts"]}), flush=True)
    content_hashes = [x["normalized_content_sha256"] for x in manifest["graphs"]]
    manifest["duplicate_whole_graph_contents"] = len(content_hashes) - len(set(content_hashes))
    manifest["cross_graph_entity_overlap"] = "UNMEASURABLE_WITHOUT_UUID_MAPPING"
    return manifest


def audit_and_normalize(magic_root: str | Path, output_root: str | Path):
    magic_root, output_root = Path(magic_root).resolve(), Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-C", str(magic_root), "rev-parse", "HEAD"],
                            check=True, capture_output=True, text=True).stdout.strip()
    sources = {}
    for rel in ("README.md", "utils/trace_parser.py", "utils/loaddata.py"):
        blob = subprocess.run(["git", "-C", str(magic_root), "show", f"{commit}:{rel}"],
                              check=True, capture_output=True).stdout
        # Git may check text out with CRLF; record that normalization explicitly.
        disk = (magic_root / rel).read_bytes()
        if disk.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
            raise DataError("Upstream source differs from recorded commit: " + rel)
        sources[rel] = {"sha256": hashlib.sha256(disk).hexdigest(),
                        "git_blob_sha256": hashlib.sha256(blob).hexdigest(),
                        "matches_git_after_newline_normalization": True,
                        "url": f"https://github.com/FDUDSDE/MAGIC/blob/{commit}/{rel}"}
    splits = source_split_manifest(magic_root / "utils/trace_parser.py")
    result = {"schema": "apt-final-native-graph-data-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": STATUS, "adapter_sha256": sha256(Path(__file__)), "source_repository": "https://github.com/FDUDSDE/MAGIC",
        "source_commit": commit, "source_files": sources,
        "allowed_use": ["static_binary_entity_detection_development", "synthetic_edge_missingness_stress_test"],
        "not_established": ["independent_campaign_generalization", "temporal_or_delayed_log_evaluation",
                            "five_stage_classification", "cross_dataset_type_semantic_alignment", "confirmatory_evidence"],
        "label_caveats": ["Training zero labels encode the upstream filtered-benign assumption, not an independent audit.",
            "The parser excludes annotated malicious endpoints from training except MemoryObject endpoints.",
            "Test zeros mean absent from supplied malicious-index list; annotation completeness is not independently established.",
            "Only one labeled test graph per dataset is supplied; nodes are not independent campaigns."],
        "graph_caveats": ["Parser orders events by timestamp, then drops timestamps and UUID mappings from these prepared graphs.",
            "Parser reverses READ/RECV/LOAD directions and collapses repeated directed pairs to one edge.",
            "Type IDs are assigned separately for each dataset; equal IDs across CADETS/THEIA do not imply equal semantics.",
            "The metadata dimensions use both train and test type vocabulary in the upstream loader.",
            "Source-file split definitions are available; temporal separation and cross-file entity overlap cannot be audited from prepared tensors."],
        "decoding_reference": "https://github.com/dmlc/dgl/blob/1.0.x/src/graph/pickle.cc",
        "arrays": {"node_type": "int64[N]", "src": "int64[E]", "dst": "int64[E]", "relation": "int64[E]", "y": "int8[N]; 1=metadata-malicious, 0=other or assumed benign training"},
        "node_id_policy": "Preserve every original zero-based row index; no relabeling, deduplication, or sampling.",
        "datasets": []}
    for dataset in ("cadets", "theia"):
        result["datasets"].append(normalize_dataset(magic_root, dataset, output_root, commit, splits))
    result["total_nodes"] = sum(g["n_nodes"] for d in result["datasets"] for g in d["graphs"])
    result["total_edges"] = sum(g["n_edges"] for d in result["datasets"] for g in d["graphs"])
    result["scientific_positive_result_claimed"] = False
    (output_root / "MANIFEST.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--magic-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit_and_normalize(args.magic_root, args.output)
    print(json.dumps({"status": result["status"], "total_nodes": result["total_nodes"], "total_edges": result["total_edges"]}))


if __name__ == "__main__":
    main()
