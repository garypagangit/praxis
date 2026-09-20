"""Bounded v2 target feature cache; no fitting, scoring or outcome selection.

Only one execution's full source events are retained at a time. Eligible rows
are sorted exactly as the frozen Replay loader. Optional v1 reuse copies only
byte-verified, identical feature jobs after the current source target roster
has independently been rebuilt and matched.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import numpy as np
from scipy import sparse

from ..robustness import feature_cache as frozen_cache
from ..robustness.replay_fast import FastReplay

ROLES = frozen_cache.ROLES
FAMILIES = ("semantic_event", "entity_context")
_sha = frozen_cache._sha
_canonical = frozen_cache._canonical
_value_sha = frozen_cache._value_sha
_write = frozen_cache._write
_finite = frozen_cache._finite
_validate_event = frozen_cache._validate_event


def _implementation_hashes():
    root = Path(frozen_cache.__file__).parent
    return {"replay_sha256": _sha(root / "replay.py"),
            "fast_replay_sha256": _sha(root / "replay_fast.py"),
            "frozen_cache_helpers_sha256": _sha(Path(frozen_cache.__file__)),
            "cache_code_sha256": _sha(Path(__file__))}


def _jobs(protocol):
    dimensions = protocol["text_features"]["hash_dimensions_per_block"]
    if type(dimensions) is not int or dimensions < 1:
        raise ValueError("Positive integer feature dimensions required")
    horizon, count = protocol["history"]["seconds"], protocol["history"]["max_events"]
    if not _finite(horizon) or horizon <= 0 or type(count) is not int or count <= 0:
        raise ValueError("Positive finite history limits required")
    conditions = protocol["conditions"]
    if not conditions or conditions[0].get("kind") != "clean" or conditions[0].get("name") != "clean":
        raise ValueError("Frozen runner requires clean first")
    if len({c["name"] for c in conditions}) != len(conditions):
        raise ValueError("Duplicate condition name")
    for condition in conditions:
        kind = condition.get("kind")
        if kind not in {"clean", "random", "support_burst", "channel_absent", "delay"}:
            raise ValueError("Unknown corruption kind")
        if kind == "random" and (not _finite(condition.get("drop_probability")) or not 0 <= condition["drop_probability"] <= 1):
            raise ValueError("Invalid random loss probability")
        if kind in {"channel_absent", "delay"} and (not isinstance(condition.get("channels"), list)
                or not condition["channels"] or any(not isinstance(c, str) or not c or c != c.upper() for c in condition["channels"])):
            raise ValueError("Explicit uppercase channel names required")
        for field in ("deadline", "delay_seconds", "seconds"):
            if field in condition and (not _finite(condition[field]) or condition[field] < 0):
                raise ValueError("Invalid corruption clock")
    by_name = {c["name"]: c for c in conditions}
    seed = protocol["classifier"]["random_state"]
    augmentation_seed = protocol.get("dropout_training", {}).get("seed", seed)
    seeds = protocol["seeds"]
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in [seed, augmentation_seed, *seeds]):
        raise ValueError("Fixed unique integer seeds required")
    arms = protocol.get("arms")
    if not isinstance(arms, dict) or not arms:
        raise ValueError("Explicit arm family and training views required")
    jobs = {role: {} for role in ROLES}

    def add(role, family, condition, seed_value):
        specification = {"role": role, "family": family, "condition": condition,
                         "seed": seed_value, "dimensions": dimensions}
        jobs[role][_value_sha(specification)] = specification

    for name, arm in arms.items():
        if not isinstance(name, str) or not isinstance(arm, dict) or arm.get("family") not in FAMILIES:
            raise ValueError("Unknown arm feature family")
        views = arm.get("views")
        if not isinstance(views, list) or not views or len(set(views)) != len(views) or any(view not in by_name for view in views):
            raise ValueError("Unique known arm training views required")
        for view in views:
            add("fit", arm["family"], by_name[view], seed if view == "clean" else augmentation_seed)
    for family in FAMILIES:
        add("calibration", family, by_name["clean"], seed)
    for condition in conditions:
        for corruption_seed in seeds if condition["kind"] == "random" else seeds[:1]:
            for family in FAMILIES:
                add("test", family, condition, corruption_seed)
    return jobs


def _open_base(base_cache, protocol, events_sha, manifest_sha):
    if base_cache is None:
        return None
    path = Path(base_cache)
    root = path.parent if path.name == "MANIFEST.json" else path
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "robustness-feature-cache-v1":
        raise ValueError("Base reuse requires the original v1 feature cache")
    base = frozen_cache.CachedReplay(root, manifest["protocol"], events_sha)
    if base.manifest["source_manifest_sha256"] != manifest_sha:
        raise ValueError("Base cache source manifest differs")
    for key in ("history", "text_features"):
        if base.manifest["protocol"][key] != protocol[key]:
            raise ValueError("Base cache feature settings differ")
    base._reuse_manifest_sha = _sha(root / "MANIFEST.json")
    base._reuse_runs = {entry["run_id"]: entry for entry in base.manifest["runs"]}
    if len(base._reuse_runs) != len(base.manifest["runs"]):
        raise ValueError("Duplicate base run metadata")
    return base


def _process_run(events, role, ordinal, output, protocol, jobs, base):
    events.sort(key=lambda event: (event["timestamp"], event["event_id"]))
    if len({event["event_id"] for event in events}) != len(events):
        raise ValueError("Duplicate source event identifier within run")
    indices = np.asarray([i for i, event in enumerate(events) if event.get("target_eligible", True)], dtype=np.int64)
    folder = output / "chunks" / f"run_{ordinal:04d}"
    folder.mkdir(parents=True)
    target_path = folder / "TARGETS.jsonl"
    with target_path.open("w", encoding="utf-8", newline="\n") as stream:
        for index in indices:
            event = events[int(index)]
            value = {key: event[key] for key in ("event_id", "run_id", "split", "timestamp", "labels")}
            value["target_eligible"] = True
            stream.write(_canonical(value) + "\n")
    targets_sha = _sha(target_path)
    base_run = None
    if base is not None:
        base_run = base._reuse_runs.get(events[0]["run_id"])
        if (base_run is None or base_run["split"] != role or base_run["source_events"] != len(events)
                or base_run["targets"] != len(indices) or base_run["targets_sha256"] != targets_sha):
            raise ValueError("Base cache run source/target roster differs")
        # Metadata alone is insufficient: rehash the original target bytes.
        base._checked_file(base_run["targets_file"], targets_sha)
    chunks, reused = {}, 0
    replay = None
    if len(indices) and jobs[role]:
        for key, specification in jobs[role].items():
            matrix_path, mask_path = folder / (key + ".npz"), folder / (key + ".observed.npy")
            old = base_run["chunks"].get(key) if base_run is not None else None
            if old is not None:
                old_job = base.manifest["matrices"].get(key)
                if old_job is None or any(old_job.get(k) != v for k, v in specification.items()):
                    raise ValueError("Base feature job specification differs")
                source_matrix = base._checked_file(old["matrix"], old["matrix_sha256"])
                source_mask = base._checked_file(old["observed"], old["observed_sha256"])
                shutil.copyfile(source_matrix, matrix_path)
                shutil.copyfile(source_mask, mask_path)
                if _sha(matrix_path) != old["matrix_sha256"] or _sha(mask_path) != old["observed_sha256"]:
                    raise ValueError("Base cache bytes changed during copy")
                matrix, observed = sparse.load_npz(matrix_path), np.load(mask_path, allow_pickle=False)
                reused += 1
            else:
                if replay is None:
                    replay = FastReplay(events, protocol["history"]["seconds"], protocol["history"]["max_events"])
                matrix, observed = replay.matrix(indices, specification["condition"], specification["seed"],
                                                  specification["family"], specification["dimensions"])
                sparse.save_npz(matrix_path, matrix, compressed=True)
                np.save(mask_path, observed, allow_pickle=False)
            if (matrix.shape != (len(indices), 2 * specification["dimensions"] + 10)
                    or observed.shape != (len(indices),) or observed.dtype != np.bool_
                    or not np.isfinite(matrix.data).all()):
                raise ValueError("Per-run feature matrix/mask is invalid")
            chunks[key] = {"matrix": matrix_path.relative_to(output).as_posix(),
                           "observed": mask_path.relative_to(output).as_posix(),
                           "matrix_sha256": _sha(matrix_path), "observed_sha256": _sha(mask_path),
                           "generation": "verified_v1_copy" if old is not None else "frozen_replay"}
            del matrix, observed
    return {"run_id": events[0]["run_id"], "split": role, "source_events": len(events),
            "targets": len(indices), "targets_file": target_path.relative_to(output).as_posix(),
            "targets_sha256": targets_sha, "reused_jobs": reused, "chunks": chunks}


def prepare(events_path, manifest_path, protocol_path, output_dir, base_cache=None):
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
    implementation = _implementation_hashes()
    base = _open_base(base_cache, protocol, expected_events_sha, manifest_sha)
    source_stat = events_path.stat()
    output.mkdir(parents=True)
    digest = hashlib.sha256()
    summaries, seen_runs = [], set()
    current, current_run, current_role = [], None, None
    source_count = 0
    identity_path = output / "SOURCE_ID_UNIQUENESS.sqlite"
    identity = sqlite3.connect(identity_path)
    identity.execute("CREATE TABLE source_ids (event_id TEXT PRIMARY KEY) WITHOUT ROWID")
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
                summaries.append(_process_run(current, current_role, len(summaries), output, protocol, jobs, base))
                print(json.dumps({"cached_run": current_run, "source_events": len(current),
                                  "targets": summaries[-1]["targets"], "reused_jobs": summaries[-1]["reused_jobs"]}), flush=True)
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
        summaries.append(_process_run(current, current_role, len(summaries), output, protocol, jobs, base))
        print(json.dumps({"cached_run": current_run, "source_events": len(current),
                          "targets": summaries[-1]["targets"], "reused_jobs": summaries[-1]["reused_jobs"]}), flush=True)
        current.clear()
        del event
        gc.collect()
    if not summaries or digest.hexdigest() != expected_events_sha:
        raise ValueError("Empty source or streamed event hash differs from source manifest")
    final_stat = events_path.stat()
    if ((source_stat.st_size, source_stat.st_mtime_ns) != (final_stat.st_size, final_stat.st_mtime_ns)
            or _sha(manifest_path) != manifest_sha or _sha(protocol_path) != protocol_sha
            or _implementation_hashes() != implementation):
        raise ValueError("Source/metadata/protocol/feature implementation changed during preparation")
    if base is not None:
        if (base.manifest["source_event_count"] != source_count
                or set(base._reuse_runs) != {row["run_id"] for row in summaries}
                or _sha(base.root / "MANIFEST.json") != base._reuse_manifest_sha):
            raise ValueError("Base cache source roster changed or differs")
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
    result = {"status": "COMPLETE_FEATURE_CACHE", "schema_version": "robustness-feature-cache-v2",
        "created_utc": datetime.now(timezone.utc).isoformat(), "events_sha256": digest.hexdigest(),
        "source_manifest_sha256": manifest_sha, "protocol_sha256": protocol_sha,
        "protocol_canonical_sha256": _value_sha(protocol), "protocol": protocol, **implementation,
        "source_event_count": source_count, "target_count": target_count,
        "source_id_uniqueness_sha256": _sha(identity_path),
        "targets_file": "TARGETS.jsonl", "targets_sha256": _sha(target_path),
        "ordering": "run_id lexical, then timestamp/event_id; exact original load_events eligible-target order",
        "feature_generation": "Exact frozen FastReplay/Replay features; optional byte-verified identical v1 job copies; no model fit/inference",
        "memory_policy": "One source run at a time; development target metadata only; combined matrices contain eligible rows only",
        "base_reuse": {"manifest_sha256": base._reuse_manifest_sha, "jobs": sum(row["reused_jobs"] for row in summaries)} if base else None,
        "role_mapping": role_mapping, "runs": summaries, "matrices": matrices}
    _write(output / "MANIFEST.json", result)
    (output / "MANIFEST.sha256").write_text(_sha(output / "MANIFEST.json") + "\n", encoding="ascii")
    return result


class CachedReplay:
    def __init__(self, cache_path, protocol, events_sha):
        path = Path(cache_path)
        self.root = path.parent if path.name == "MANIFEST.json" else path
        if _sha(self.root / "MANIFEST.json") != (self.root / "MANIFEST.sha256").read_text(encoding="ascii").strip():
            raise ValueError("Cache manifest hash mismatch")
        self.manifest = json.loads((self.root / "MANIFEST.json").read_text(encoding="utf-8"))
        manifest = self.manifest
        if manifest.get("status") != "COMPLETE_FEATURE_CACHE" or manifest.get("schema_version") != "robustness-feature-cache-v2":
            raise ValueError("Incomplete or wrong-version feature cache")
        if manifest["events_sha256"] != events_sha or manifest["protocol_canonical_sha256"] != _value_sha(protocol):
            raise ValueError("Cache does not bind the supplied source/protocol")
        if manifest["protocol_canonical_sha256"] != _value_sha(manifest["protocol"]):
            raise ValueError("Cache embedded protocol is inconsistent")
        if any(manifest.get(key) != value for key, value in _implementation_hashes().items()):
            raise ValueError("Runtime replay/cache implementation differs from prepared cache")
        jobs = _jobs(protocol)
        expected_jobs = {key: specification for role in ROLES for key, specification in jobs[role].items()}
        if set(manifest["matrices"]) != set(expected_jobs):
            raise ValueError("Cached feature schedule is inconsistent")
        for key, specification in expected_jobs.items():
            if any(manifest["matrices"][key].get(k) != v for k, v in specification.items()):
                raise ValueError("Cached feature specification is inconsistent")
        target_path = self._checked_file(manifest["targets_file"], manifest["targets_sha256"])
        self.events = [json.loads(line) for line in target_path.read_text(encoding="utf-8").splitlines()]
        if len(self.events) != manifest["target_count"] or any(e.get("target_eligible") is not True for e in self.events):
            raise ValueError("Cached eligible-target roster is inconsistent")
        for event in self.events:
            if (not isinstance(event.get("event_id"), str) or not isinstance(event.get("run_id"), str)
                    or event.get("split") not in ROLES or not _finite(event.get("timestamp"))
                    or not isinstance(event.get("labels"), list)
                    or any(not isinstance(label, str) or not label for label in event["labels"])):
                raise ValueError("Invalid cached target metadata")
        if len({e["event_id"] for e in self.events}) != len(self.events):
            raise ValueError("Duplicate cached eligible event ID")
        if self.events != sorted(self.events, key=lambda e: (e["run_id"], e["timestamp"], e["event_id"])):
            raise ValueError("Cached target roster ordering differs")
        self.source_event_count = manifest["source_event_count"]
        if type(self.source_event_count) is not int or self.source_event_count < len(self.events):
            raise ValueError("Invalid cached source event count")
        runs = manifest["runs"]
        if len({row["run_id"] for row in runs}) != len(runs) or sum(row["source_events"] for row in runs) != self.source_event_count:
            raise ValueError("Cached run source counts are inconsistent")
        cursor = 0
        for row in runs:
            stop = cursor + row["targets"]
            selected = self.events[cursor:stop]
            if (row["global_target_start"] != cursor or row["global_target_stop"] != stop
                    or row["targets"] < 0 or row["source_events"] < row["targets"] or row["split"] not in ROLES
                    or any(e["run_id"] != row["run_id"] or e["split"] != row["split"] for e in selected)):
                raise ValueError("Cached run target roster is inconsistent")
            cursor = stop
        if cursor != len(self.events):
            raise ValueError("Cached run targets do not cover roster")
        self._roles = np.asarray([e["split"] for e in self.events])
        self._offset = np.full(len(self.events), -1, dtype=np.int64)
        self._conditions = {c["name"]: c for c in protocol["conditions"]}
        self._dimensions = protocol["text_features"]["hash_dimensions_per_block"]
        self._arms = protocol["arms"]
        if set(manifest["role_mapping"]) != set(ROLES):
            raise ValueError("Cached roles are inconsistent")
        for role, entry in manifest["role_mapping"].items():
            positions = np.load(self._checked_file(entry["file"], entry["sha256"]), allow_pickle=False)
            expected = np.flatnonzero(self._roles == role)
            if positions.dtype != np.int64 or not np.array_equal(positions, expected) or entry["rows"] != len(expected):
                raise ValueError("Cached role row mapping is inconsistent")
            self._offset[positions] = np.arange(len(positions))
        if np.any(self._offset < 0):
            raise ValueError("Unmapped cached target row")

    def _checked_file(self, relative, expected):
        candidate = self.root / relative
        if not candidate.resolve().is_relative_to(self.root.resolve()) or candidate.is_symlink():
            raise ValueError("Cache file escapes cache root")
        if _sha(candidate) != expected:
            raise ValueError("Cached file hash mismatch")
        return candidate

    def matrix(self, indices, condition, seed, arm, dimensions=32768):
        if type(dimensions) is not int or dimensions != self._dimensions:
            raise ValueError("Requested dimensions differ from cache protocol")
        if type(seed) is not int:
            raise ValueError("Invalid cache seed")
        if condition.get("name") not in self._conditions or _canonical(condition) != _canonical(self._conditions[condition["name"]]):
            raise ValueError("Requested condition parameters differ from frozen cache")
        family = self._arms[arm]["family"] if arm in self._arms else arm
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
                    or observed.shape != (matrix.shape[0],) or observed.dtype != np.bool_
                    or matrix.nnz != entry["nnz"] or int(observed.sum()) != entry["observed_rows"]
                    or not np.isfinite(matrix.data).all()):
                raise ValueError("Cache matrix/mask shape or content mismatch")
            local = self._offset[indices[selection]]
            parts.append(matrix[local].tocsr())
            observed_parts.append(observed[local])
            output_positions.append(selection)
        inverse = np.argsort(np.concatenate(output_positions))
        return sparse.vstack(parts, format="csr")[inverse], np.concatenate(observed_parts)[inverse]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-cache", type=Path)
    args = parser.parse_args()
    result = prepare(args.events, args.manifest, args.protocol, args.output, args.base_cache)
    print(json.dumps({"status": result["status"], "source_events": result["source_event_count"], "targets": result["target_count"]}), flush=True)


if __name__ == "__main__":
    main()
