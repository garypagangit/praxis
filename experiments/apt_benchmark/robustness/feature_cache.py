"""Stream per-run, eligible-target feature caches using the frozen Replay.

No fitting or inference occurs. All context within the current run is retained
for Replay; only target rows survive into the cache. Final row order is the
same (run_id, timestamp, event_id) order as Replay.load_events.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import numpy as np
from scipy import sparse

from .replay_fast import FastReplay


ROLES = ("fit", "development", "calibration", "test")
FAMILIES = ("generic_event", "semantic_event", "entity_context")


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _value_sha(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _validate_event(event):
    if not isinstance(event, dict):
        raise ValueError("Event must be an object")
    for name in ("event_id", "run_id"):
        if not isinstance(event.get(name), str) or not event[name]:
            raise ValueError("Event/run identifiers are required")
    if event.get("split") not in ROLES or not _finite(event.get("timestamp")):
        raise ValueError("Invalid split or event clock")
    if not _finite(event.get("available_at", event["timestamp"])):
        raise ValueError("Nonfinite event availability")
    if type(event.get("target_eligible", True)) is not bool:
        raise ValueError("target_eligible must be boolean")
    if not isinstance(event.get("labels"), list) or any(not isinstance(x, str) or not x for x in event["labels"]):
        raise ValueError("Source labels must be explicit strings")
    if not isinstance(event.get("fragments"), list) or not event["fragments"]:
        raise ValueError("Original source event must contain fragments")
    for fragment in event["fragments"]:
        channel = fragment.get("channel")
        if not isinstance(channel, str) or not channel:
            raise ValueError("Fragment channel must be a nonempty string")
        # This is the same normalization performed by frozen load_events;
        # Casino serializes lowercase channel names.
        fragment["channel"] = channel.upper()
        if (not _finite(fragment.get("timestamp"))
                or not _finite(fragment.get("available_at", fragment["timestamp"]))):
            raise ValueError("Nonfinite fragment clock")
        if not isinstance(fragment.get("text"), str) or not isinstance(fragment.get("baseline_text", ""), str):
            raise ValueError("Fragment feature text must be a string")
        if not isinstance(fragment.get("entity_keys"), list) or any(not isinstance(k, str) or not k for k in fragment["entity_keys"]):
            raise ValueError("Explicit fragment-local linkage keys are required")


def _jobs(protocol):
    dimensions = protocol["text_features"]["hash_dimensions_per_block"]
    if type(dimensions) is not int or dimensions < 1:
        raise ValueError("Positive integer feature dimensions required")
    horizon, count = protocol["history"]["seconds"], protocol["history"]["max_events"]
    if not _finite(horizon) or horizon <= 0 or type(count) is not int or count <= 0:
        raise ValueError("Positive finite history limits required")
    conditions = protocol["conditions"]
    if not conditions or conditions[0].get("kind") != "clean":
        raise ValueError("Frozen runner requires clean first")
    if len({c["name"] for c in conditions}) != len(conditions):
        raise ValueError("Duplicate condition name")
    clean = conditions[0]
    by_name = {c["name"]: c for c in conditions}
    seed = protocol["classifier"]["random_state"]
    augmentation_seed = protocol["dropout_training"]["seed"]
    seeds = protocol["seeds"]
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in [seed, augmentation_seed, *seeds]):
        raise ValueError("Fixed unique integer seeds required")
    jobs = {role: {} for role in ROLES}

    def add(role, family, condition, seed_value):
        specification = {"role": role, "family": family, "condition": condition, "seed": seed_value,
                         "dimensions": dimensions}
        jobs[role][_value_sha(specification)] = specification

    for role in ("fit", "calibration"):
        for family in FAMILIES:
            add(role, family, clean, seed)
    for condition_name in protocol["dropout_training"]["views"]:
        if condition_name not in by_name:
            raise ValueError("Unknown augmentation condition")
        add("fit", "entity_context", by_name[condition_name], augmentation_seed)
    for condition in conditions:
        for corruption_seed in seeds if condition["kind"] == "random" else seeds[:1]:
            for family in FAMILIES:
                add("test", family, condition, corruption_seed)
    return jobs


def _process_run(events, role, ordinal, output, protocol, jobs):
    """All references to this run die on return; caller then clears its list."""
    events.sort(key=lambda event: (event["timestamp"], event["event_id"]))
    if len({event["event_id"] for event in events}) != len(events):
        raise ValueError("Duplicate source event identifier within run")
    indices = np.asarray([i for i, event in enumerate(events) if event.get("target_eligible", True)], dtype=np.int64)
    relative = Path("chunks") / f"run_{ordinal:04d}"
    folder = output / relative
    folder.mkdir(parents=True)
    target_path = folder / "TARGETS.jsonl"
    with target_path.open("w", encoding="utf-8", newline="\n") as stream:
        for index in indices:
            event = events[int(index)]
            value = {key: event[key] for key in ("event_id", "run_id", "split", "timestamp", "labels")}
            value["target_eligible"] = True
            stream.write(_canonical(value) + "\n")
    chunks = {}
    if len(indices) and jobs[role]:
        replay = FastReplay(events, protocol["history"]["seconds"], protocol["history"]["max_events"])
        for key, specification in jobs[role].items():
            matrix, observed = replay.matrix(indices, specification["condition"], specification["seed"],
                                              specification["family"], specification["dimensions"])
            matrix_path, mask_path = folder / (key + ".npz"), folder / (key + ".observed.npy")
            sparse.save_npz(matrix_path, matrix, compressed=True)
            np.save(mask_path, observed, allow_pickle=False)
            chunks[key] = {"matrix": matrix_path.relative_to(output).as_posix(),
                           "observed": mask_path.relative_to(output).as_posix(),
                           "matrix_sha256": _sha(matrix_path), "observed_sha256": _sha(mask_path)}
            del matrix, observed
        del replay
    return {"run_id": events[0]["run_id"], "split": role, "source_events": len(events),
            "targets": len(indices), "targets_file": target_path.relative_to(output).as_posix(),
            "targets_sha256": _sha(target_path), "chunks": chunks}


def prepare(events_path, manifest_path, protocol_path, output_dir):
    events_path, manifest_path, protocol_path, output = map(Path, (events_path, manifest_path, protocol_path, output_dir))
    if output.exists():
        raise FileExistsError("Refusing to overwrite cache evidence")
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_events_sha = source_manifest.get("events_sha256")
    if not isinstance(expected_events_sha, str) or len(expected_events_sha) != 64:
        raise ValueError("Source manifest must bind events_sha256")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    jobs = _jobs(protocol)
    manifest_sha, protocol_sha = _sha(manifest_path), _sha(protocol_path)
    replay_sha, code_sha = _sha(Path(__file__).with_name("replay.py")), _sha(Path(__file__))
    fast_replay_sha = _sha(Path(__file__).with_name("replay_fast.py"))
    output.mkdir(parents=True)
    digest = hashlib.sha256()
    summaries, seen_runs = [], set()
    current, current_run, current_role = [], None, None
    source_count = 0
    # A disk-backed unique index catches context-ID collisions across runs
    # without retaining all earlier IDs (or dictionaries) in memory.
    identity_path = output / "SOURCE_ID_UNIQUENESS.sqlite"
    identity = sqlite3.connect(identity_path)
    identity.execute("CREATE TABLE source_ids (event_id TEXT PRIMARY KEY) WITHOUT ROWID")
    # Binary iteration preserves exact source bytes in the running hash. The
    # next run's first row is the only object held while releasing the old run.
    with closing(identity), identity, events_path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            event = json.loads(raw.decode("utf-8"))
            _validate_event(event)
            try:
                identity.execute("INSERT INTO source_ids VALUES (?)", (event["event_id"],))
            except sqlite3.IntegrityError as error:
                raise ValueError("Duplicate source event identifier") from error
            run, role = event["run_id"], event["split"]
            if current_run is not None and run != current_run:
                summaries.append(_process_run(current, current_role, len(summaries), output, protocol, jobs))
                print(json.dumps({"cached_run": current_run, "source_events": len(current), "targets": summaries[-1]["targets"]}), flush=True)
                current.clear()
                gc.collect()
                identity.commit()
                seen_runs.add(current_run)
                current_run, current_role = None, None
            if current_run is None:
                if run in seen_runs:
                    raise ValueError("A run reappears after its contiguous block")
                current_run, current_role = run, role
            if role != current_role:
                raise ValueError("One run crosses split roles")
            current.append(event)
            source_count += 1
    if current:
        summaries.append(_process_run(current, current_role, len(summaries), output, protocol, jobs))
        print(json.dumps({"cached_run": current_run, "source_events": len(current), "targets": summaries[-1]["targets"]}), flush=True)
        current.clear()
        del event
        gc.collect()
    if not summaries or digest.hexdigest() != expected_events_sha:
        raise ValueError("Empty source or streamed event hash differs from source manifest")
    if (_sha(manifest_path) != manifest_sha or _sha(protocol_path) != protocol_sha
            or _sha(Path(__file__).with_name("replay.py")) != replay_sha or _sha(Path(__file__)) != code_sha
            or _sha(Path(__file__).with_name("replay_fast.py")) != fast_replay_sha):
        raise ValueError("Source metadata/protocol/feature implementation changed during preparation")
    # Only eligible metadata and sparse target matrices are combined, never
    # complete source events from prior runs. Canonical ordering matches Replay.
    summaries.sort(key=lambda item: item["run_id"])
    role_indices = {role: [] for role in ROLES}
    target_count, eligible_ids = 0, set()
    target_path = output / "TARGETS.jsonl"
    with target_path.open("w", encoding="utf-8", newline="\n") as destination:
        for summary in summaries:
            summary["global_target_start"] = target_count
            with (output / summary["targets_file"]).open(encoding="utf-8") as stream:
                for line in stream:
                    value = json.loads(line)
                    if value["event_id"] in eligible_ids:
                        raise ValueError("Eligible event ID repeats across runs")
                    eligible_ids.add(value["event_id"])
                    destination.write(line)
                    role_indices[summary["split"]].append(target_count)
                    target_count += 1
            summary["global_target_stop"] = target_count
    del eligible_ids
    folder = output / "matrices"
    folder.mkdir()
    role_mapping, matrices = {}, {}
    for role in ROLES:
        index_path = folder / (role + ".rows.npy")
        np.save(index_path, np.asarray(role_indices[role], dtype=np.int64), allow_pickle=False)
        role_mapping[role] = {"file": index_path.relative_to(output).as_posix(), "sha256": _sha(index_path), "rows": len(role_indices[role])}
        for key, specification in jobs[role].items():
            selected = [summary for summary in summaries if summary["split"] == role and summary["targets"]]
            chunks = [sparse.load_npz(output / summary["chunks"][key]["matrix"]) for summary in selected]
            matrix = sparse.vstack(chunks, format="csr") if chunks else sparse.csr_matrix((0, 2 * specification["dimensions"] + 10), dtype=np.float64)
            del chunks
            masks = [np.load(output / summary["chunks"][key]["observed"], allow_pickle=False) for summary in selected]
            observed = np.concatenate(masks) if masks else np.empty(0, dtype=bool)
            del masks
            if matrix.shape != (len(role_indices[role]), 2 * specification["dimensions"] + 10) or observed.shape != (len(role_indices[role]),):
                raise ValueError("Combined matrix/role row mapping mismatch")
            matrix_path, mask_path = folder / (key + ".npz"), folder / (key + ".observed.npy")
            sparse.save_npz(matrix_path, matrix, compressed=True)
            np.save(mask_path, observed, allow_pickle=False)
            matrices[key] = {**specification, "matrix": matrix_path.relative_to(output).as_posix(),
                "observed": mask_path.relative_to(output).as_posix(), "matrix_sha256": _sha(matrix_path),
                "observed_sha256": _sha(mask_path), "row_mapping": role_mapping[role],
                "rows": matrix.shape[0], "columns": matrix.shape[1], "nnz": matrix.nnz,
                "observed_rows": int(observed.sum())}
            del matrix, observed
    result = {"status": "COMPLETE_FEATURE_CACHE", "schema_version": "robustness-feature-cache-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(), "events_sha256": digest.hexdigest(),
        "source_manifest_sha256": manifest_sha, "protocol_sha256": protocol_sha,
        "protocol_canonical_sha256": _value_sha(protocol), "protocol": protocol,
        "replay_sha256": replay_sha, "fast_replay_sha256": fast_replay_sha, "cache_code_sha256": code_sha,
        "source_event_count": source_count, "target_count": target_count,
        "source_id_uniqueness_sha256": _sha(identity_path),
        "targets_file": "TARGETS.jsonl", "targets_sha256": _sha(target_path),
        "ordering": "run_id lexical, then timestamp/event_id; exact original load_events eligible-target order",
        "feature_generation": "Exact-equivalent FastReplay views with the original frozen Replay.matrix feature builder; no model fit/inference",
        "memory_policy": "One full source run at a time, released after its target chunks; combined matrices contain eligible rows only",
        "role_mapping": role_mapping, "runs": summaries, "matrices": matrices}
    _write(output / "MANIFEST.json", result)
    return result


class CachedReplay:
    def __init__(self, cache_path, protocol, events_sha):
        path = Path(cache_path)
        self.root = path.parent if path.name == "MANIFEST.json" else path
        self.manifest = json.loads((self.root / "MANIFEST.json").read_text(encoding="utf-8"))
        manifest = self.manifest
        if manifest.get("status") != "COMPLETE_FEATURE_CACHE":
            raise ValueError("Incomplete feature cache")
        if manifest["events_sha256"] != events_sha or manifest["protocol_canonical_sha256"] != _value_sha(protocol):
            raise ValueError("Cache does not bind the supplied source/protocol")
        if manifest["protocol_canonical_sha256"] != _value_sha(manifest["protocol"]):
            raise ValueError("Cache embedded protocol is inconsistent")
        if (manifest["replay_sha256"] != _sha(Path(__file__).with_name("replay.py"))
                or manifest["fast_replay_sha256"] != _sha(Path(__file__).with_name("replay_fast.py"))
                or manifest["cache_code_sha256"] != _sha(Path(__file__))):
            raise ValueError("Runtime replay/cache implementation differs from prepared cache")
        target_path = self._checked_file(manifest["targets_file"], manifest["targets_sha256"])
        self.events = []
        with target_path.open(encoding="utf-8") as stream:
            for line in stream:
                self.events.append(json.loads(line))
        if len(self.events) != manifest["target_count"] or any(e.get("target_eligible") is not True for e in self.events):
            raise ValueError("Cached eligible-target roster is inconsistent")
        if len({e["event_id"] for e in self.events}) != len(self.events):
            raise ValueError("Duplicate cached eligible event ID")
        self.source_event_count = manifest["source_event_count"]
        self._roles = np.asarray([e["split"] for e in self.events])
        self._offset = np.full(len(self.events), -1, dtype=np.int64)
        self._conditions = {c["name"]: c for c in protocol["conditions"]}
        self._dimensions = protocol["text_features"]["hash_dimensions_per_block"]
        for role, entry in manifest["role_mapping"].items():
            path = self._checked_file(entry["file"], entry["sha256"])
            positions = np.load(path, allow_pickle=False)
            expected = np.flatnonzero(self._roles == role)
            if positions.dtype != np.int64 or not np.array_equal(positions, expected) or entry["rows"] != len(expected):
                raise ValueError("Cached role row mapping is inconsistent")
            self._offset[positions] = np.arange(len(positions))
        if np.any(self._offset < 0):
            raise ValueError("Unmapped cached target row")

    def _checked_file(self, relative, expected):
        candidate = self.root / relative
        resolved_root, resolved = self.root.resolve(), candidate.resolve()
        if not resolved.is_relative_to(resolved_root) or candidate.is_symlink():
            raise ValueError("Cache file escapes cache root")
        # Rehash before every new matrix use: no stale validation after a file
        # replacement. Target/row metadata is already held in memory thereafter.
        if _sha(candidate) != expected:
            raise ValueError("Cached file hash mismatch")
        return candidate

    def matrix(self, indices, condition, seed, arm, dimensions=32768):
        if dimensions != self._dimensions or type(dimensions) is not int:
            raise ValueError("Requested dimensions differ from cache protocol")
        if type(seed) is not int:
            raise ValueError("Invalid cache seed")
        if condition.get("name") not in self._conditions or _canonical(condition) != _canonical(self._conditions[condition["name"]]):
            raise ValueError("Requested condition parameters differ from frozen cache")
        family = "entity_context" if arm == "context_dropout" else arm
        if family not in FAMILIES:
            raise ValueError("Unknown feature family")
        indices = np.asarray(indices)
        if indices.ndim != 1 or indices.dtype.kind not in "iu" or np.any(indices < 0) or np.any(indices >= len(self.events)):
            raise ValueError("Invalid eligible-target indices")
        indices = indices.astype(np.int64, copy=False)
        if not len(indices):
            return sparse.csr_matrix((0, 2 * dimensions + 10), dtype=np.float64), np.empty(0, dtype=bool)
        parts, observed_parts, output_positions = [], [], []
        for role in ROLES:
            selection = np.flatnonzero(self._roles[indices] == role)
            if not len(selection):
                continue
            specification = {"role": role, "family": family, "condition": condition, "seed": seed, "dimensions": dimensions}
            entry = self.manifest["matrices"].get(_value_sha(specification))
            if entry is None:
                raise ValueError("Feature request was not in the prepared role schedule")
            if any(entry[k] != v for k, v in specification.items()):
                raise ValueError("Cache matrix specification is inconsistent")
            matrix = sparse.load_npz(self._checked_file(entry["matrix"], entry["matrix_sha256"]))
            observed = np.load(self._checked_file(entry["observed"], entry["observed_sha256"]), allow_pickle=False)
            if (matrix.shape != (self.manifest["role_mapping"][role]["rows"], 2 * dimensions + 10)
                    or observed.shape != (matrix.shape[0],) or observed.dtype != np.bool_):
                raise ValueError("Cache matrix/mask shape mismatch")
            local = self._offset[indices[selection]]
            parts.append(matrix[local].tocsr())
            observed_parts.append(observed[local])
            output_positions.append(selection)
            del matrix, observed
        inverse = np.argsort(np.concatenate(output_positions))
        return sparse.vstack(parts, format="csr")[inverse], np.concatenate(observed_parts)[inverse]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.events, args.manifest, args.protocol, args.output)
    print(json.dumps({"status": result["status"], "source_events": result["source_event_count"], "targets": result["target_count"]}), flush=True)


if __name__ == "__main__":
    main()
