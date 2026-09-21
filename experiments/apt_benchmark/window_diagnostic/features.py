"""Frozen, label-independent audit features for fixed retrospective windows.

Only defender fragment ``text`` and record channels enter lexical features.
The source slice uses the existing author's run envelope, but absolute bins,
empty windows and earliest-event selection precede annotation lookup. All
source provenance stays in metadata, never in the feature vector.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize

from ..camlds.events import load_intervals

BIN_SECONDS = 10
TEXT_DIMENSIONS = 8192
CHANNELS = ("SYSCALL", "EXECVE", "PROCTITLE", "PATH", "OTHER")
REMOVED_CHANNELS = frozenset(("EXECVE", "PROCTITLE"))
TRANSFER_TOKENS = frozenset(("curl", "wget", "scp", "sftp", "tftp", "rsync"))
WORD = re.compile(r"(?u)\b\w+\b")
GENERIC_MARKERS = re.compile(r"\b(?:TECHNIQUE_MARKER|SCENARIO_MARKER|CHALLENGE_MARKER)\b", re.I)
EVENTS_SHA256 = "17bbb1a7cf7b55ff5f8bf72a88fd8cc9c54f563d0f368441a1a626537356620a"
SOURCE_MANIFEST_SHA256 = "3596db41fd7aef1c999d589042f14985631a3dd20aad0d68455e9f6ba515313b"


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def vectorizer():
    return HashingVectorizer(n_features=TEXT_DIMENSIONS, ngram_range=(1, 2),
                             alternate_sign=False, norm=None, binary=True,
                             dtype=np.float32)


def roster_rows(intervals, runs, family_splits):
    """Materialize all fully contained UTC bins before any label assignment."""
    rows = []
    for run in sorted(runs):
        steps = intervals[run]
        low = min(step["start"] for step in steps) - 120
        high = max(step["end"] for step in steps)
        first = math.ceil(low / BIN_SECONDS)
        stop = math.floor(high / BIN_SECONDS)
        family = run.split("_")[0]
        for bucket in range(first, stop):
            rows.append({"window_id": f"camlds-window:{run}:{bucket}",
                         "run_id": run, "family": family,
                         "split": family_splits[family],
                         "start": bucket * BIN_SECONDS,
                         "end": (bucket + 1) * BIN_SECONDS})
    return rows


def assign_labels(rows, intervals):
    """Positive T1105 overlap wins; other annotation is 0; unknown is -1."""
    for row in rows:
        active = [step for step in intervals[row["run_id"]]
                  if step["start"] < row["end"] and step["end"] > row["start"]]
        positive = [step["step_id"] for step in active
                    if any(label.split(".")[0] == "T1105" for label in step["labels"])]
        row["label"] = 1 if positive else 0 if active else -1
        row["positive_source_step_ids"] = sorted(positive)


def visible_parts(event, command_absent=False):
    return [part for part in event["fragments"]
            if not command_absent or part["channel"].upper() not in REMOVED_CHANNELS]


def feature_text(parts):
    # Explicit allowlist: metadata, baseline_text and entity_keys never enter.
    return GENERIC_MARKERS.sub(" ", " ".join(part["text"] for part in parts))


class ViewAccumulator:
    """Bounded event-text buffer plus one small binary hashed window vector."""

    def __init__(self, hasher):
        self.hasher = hasher
        self.presence = np.zeros(TEXT_DIMENSIONS, dtype=np.bool_)
        self.documents = []
        self.event_count = self.fragment_count = 0
        self.hosts = set()
        self.channels = Counter()
        self.rule_tokens = set()

    def add(self, event, parts):
        if not parts:
            return
        document = feature_text(parts)
        self.documents.append(document)
        self.event_count += 1
        self.fragment_count += len(parts)
        self.hosts.add(event["host"])
        for part in parts:
            channel = part["channel"].upper()
            self.channels[channel if channel in CHANNELS else "OTHER"] += 1
        self.rule_tokens.update(TRANSFER_TOKENS.intersection(WORD.findall(document.lower())))
        if len(self.documents) >= 512:
            self.flush()

    def flush(self):
        if self.documents:
            matrix = self.hasher.transform(self.documents)
            self.presence[matrix.indices] = True
            self.documents.clear()

    def result(self):
        self.flush()
        indices = np.flatnonzero(self.presence).astype(np.int32)
        text = sparse.csr_matrix((np.ones(len(indices), dtype=np.float32), indices,
                                  np.array([0, len(indices)], dtype=np.int32)),
                                 shape=(1, TEXT_DIMENSIONS))
        text = normalize(text, norm="l2", copy=False)
        observed = [self.event_count, self.fragment_count, len(self.hosts)]
        observed.extend(self.channels[channel] for channel in CHANNELS)
        counts = sparse.csr_matrix(np.log1p(np.asarray(observed, dtype=np.float32))[None, :])
        return sparse.hstack((text, counts), format="csr", dtype=np.float32), len(self.rule_tokens)


class WindowAccumulator:
    def __init__(self, hasher):
        self.views = {name: ViewAccumulator(hasher) for name in
                      ("pooled_clean", "pooled_command_absent", "first_clean", "first_command_absent")}
        self.events = 0
        self.previous_key = None

    def add(self, event):
        key = (event["timestamp"], event["event_id"])
        if self.previous_key is not None and key <= self.previous_key:
            raise ValueError("Events must have unique increasing timestamp/event_id keys")
        self.previous_key = key
        clean = visible_parts(event)
        absent = visible_parts(event, True)
        self.views["pooled_clean"].add(event, clean)
        self.views["pooled_command_absent"].add(event, absent)
        # Selection uses the source event before ablation. Never substitute the
        # next visible event when this earliest event loses every fragment.
        if self.events == 0:
            self.views["first_clean"].add(event, clean)
            self.views["first_command_absent"].add(event, absent)
        self.events += 1

    def result(self):
        return {name: value.result() for name, value in self.views.items()}


def stream_features(events, rows):
    """Consume chronological per-run events once; preserve empty roster bins."""
    hasher = vectorizer()
    matrices = {name: [] for name in
                ("pooled_clean", "pooled_command_absent", "first_clean", "first_command_absent")}
    rules = {name: [] for name in ("clean", "command_absent")}
    row_indices = {(row["run_id"], row["start"] // BIN_SECONDS): i for i, row in enumerate(rows)}
    if len(row_indices) != len(rows):
        raise ValueError("Duplicate fixed-bin roster rows")
    cursor = 0
    accumulator = WindowAccumulator(hasher)
    previous = None
    source_count = retained = excluded = 0

    def finish():
        nonlocal accumulator
        result = accumulator.result()
        rows[cursor]["clean_event_count"] = accumulator.events
        for name in matrices:
            matrices[name].append(result[name][0])
        for name in rules:
            rules[name].append(result["pooled_" + name][1])
        accumulator = WindowAccumulator(hasher)

    for event in events:
        source_count += 1
        key = (event["run_id"], event["timestamp"], event["event_id"])
        if not math.isfinite(event["timestamp"]):
            raise ValueError("Non-finite source event timestamp")
        if previous is not None and key <= previous:
            raise ValueError("Source event stream is not ordered or contains duplicate keys")
        previous = key
        bucket = math.floor(event["timestamp"] / BIN_SECONDS)
        index = row_indices.get((event["run_id"], bucket))
        if index is None:
            excluded += 1
            continue
        if index < cursor:
            raise ValueError("Source ordering disagrees with roster ordering")
        while cursor < index:
            finish()
            cursor += 1
        accumulator.add(event)
        retained += 1
    while cursor < len(rows):
        finish()
        cursor += 1
    width = TEXT_DIMENSIONS + 3 + len(CHANNELS)
    matrices = {name: sparse.vstack(parts, format="csr") if parts else
                sparse.csr_matrix((0, width), dtype=np.float32) for name, parts in matrices.items()}
    return matrices, {name: np.asarray(values, dtype=np.float32) for name, values in rules.items()}, {
        "source_events": source_count, "events_in_complete_bins": retained,
        "events_outside_complete_bins": excluded}


def json_events(path):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def prepare(source_root, output, protocol):
    source_root, output, protocol = Path(source_root), Path(output), Path(protocol)
    if output.exists():
        raise FileExistsError("Refusing to overwrite feature evidence")
    prepared = source_root / "prepared_masked_v2"
    source_manifest_path = prepared / "MANIFEST.json"
    events_path = prepared / "EVENTS.jsonl"
    if digest(source_manifest_path) != SOURCE_MANIFEST_SHA256:
        raise ValueError("Source manifest differs from frozen CAM input")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest["events_sha256"] != EVENTS_SHA256 or digest(events_path) != EVENTS_SHA256:
        raise ValueError("Source events differ from frozen CAM input")
    selection = source_manifest["selection"]
    for filename, key in (("labels.json", "labels_sha256"), ("attack_times.csv", "attack_times_sha256")):
        if digest(source_root / filename) != selection[key]:
            raise ValueError("Author annotation source differs from frozen input")
    protocol_hash = digest(protocol)
    # Require syntactically valid JSON; interpretation and freeze belong to the
    # runner's protocol validator. Preparation cannot tune from results.
    json.loads(protocol.read_text(encoding="utf-8-sig"))
    intervals = load_intervals(source_root)
    rows = roster_rows(intervals, selection["runs"], selection["family_splits"])
    matrices, rules, counts = stream_features(json_events(events_path), rows)
    if counts["source_events"] != source_manifest["events"]:
        raise ValueError("Source event count differs from manifest")
    # This call occurs after all observed feature matrices are complete.
    assign_labels(rows, intervals)
    output.mkdir(parents=True)
    for name, matrix in matrices.items():
        sparse.save_npz(output / (name + ".npz"), matrix, compressed=True)
    for name, values in rules.items():
        np.save(output / ("rules_" + name + ".npy"), values, allow_pickle=False)
    (output / "metadata.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    support = {}
    for split in ("fit", "development", "calibration", "test"):
        selected = [row for row in rows if row["split"] == split]
        support[split] = {"windows": len(selected), "positive": sum(row["label"] == 1 for row in selected),
                          "other_annotated": sum(row["label"] == 0 for row in selected),
                          "unknown": sum(row["label"] == -1 for row in selected),
                          "empty": sum(row["clean_event_count"] == 0 for row in selected)}
    artifacts = {path.name: {"sha256": digest(path), "bytes": path.stat().st_size}
                 for path in sorted(output.iterdir())}
    code_paths = {"features.py": Path(__file__), "camlds/events.py": Path(__file__).parents[1] / "camlds" / "events.py"}
    manifest = {"status": "FEATURES_PREPARED_NO_MODELS_FIT", "protocol_sha256": protocol_hash,
                "source_events_sha256": EVENTS_SHA256, "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
                "labels_sha256": selection["labels_sha256"], "attack_times_sha256": selection["attack_times_sha256"],
                "code_sha256": {name: digest(path) for name, path in code_paths.items()},
                "features": {"text_dimensions": TEXT_DIMENSIONS, "ngrams": [1, 2],
                             "stripped_generic_markers": ["TECHNIQUE_MARKER", "SCENARIO_MARKER", "CHALLENGE_MARKER"],
                             "binary_event_hashes": True, "binary_pooled_presence": True, "text_norm": "l2",
                             "observed_count_columns_log1p": ["events", "fragments", "hosts", *CHANNELS],
                             "dimensions": TEXT_DIMENSIONS + 8, "bin_seconds": BIN_SECONDS,
                             "pooled_rule_tokens": sorted(TRANSFER_TOKENS)},
                "counts": counts, "support": support, "windows": len(rows),
                "matrices": {name: {"shape": list(matrix.shape), "nnz": matrix.nnz} for name, matrix in matrices.items()},
                "artifacts": artifacts}
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "windows": len(rows), "support": support}), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_root, args.output, args.protocol)


if __name__ == "__main__":
    main()
