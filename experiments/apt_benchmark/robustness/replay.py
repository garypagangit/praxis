"""Causal fragment replay; labels and hidden linkage fields never enter features.

This is an offline event-roster evaluation. Ingestion times are simulated, not
measured. Completely hidden target events remain in the recall denominator.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import HashingVectorizer


def load_events(path):
    events = []
    ids = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event_id"] in ids:
            raise ValueError("Duplicate event ID")
        ids.add(event["event_id"])
        if event["split"] not in {"fit", "development", "calibration", "test"}:
            raise ValueError("Unknown split")
        if not math.isfinite(event["timestamp"]):
            raise ValueError("Nonfinite event timestamp")
        for fragment in event["fragments"]:
            if not math.isfinite(fragment["timestamp"]):
                raise ValueError("Nonfinite fragment timestamp")
            fragment["channel"] = fragment["channel"].upper()
            if not math.isfinite(fragment.get("available_at", fragment["timestamp"])):
                raise ValueError("Nonfinite availability timestamp")
            if "entity_keys" not in fragment:
                raise ValueError("Fragment-local entity keys are required")
        events.append(event)
    run_splits = defaultdict(set)
    for event in events:
        run_splits[event["run_id"]].add(event["split"])
    if any(len(splits) != 1 for splits in run_splits.values()):
        raise ValueError("A run crosses split boundaries")
    return sorted(events, key=lambda x: (x["run_id"], x["timestamp"], x["event_id"]))


def retained(event_id, fragment_number, seed, probability):
    digest = hashlib.sha256(f"{seed}|{event_id}|{fragment_number}".encode()).digest()
    value = int.from_bytes(digest[:8], "big") / 2**64
    return value >= probability


def visible_fragments(event, condition, seed, target_time, is_target=False):
    deadline = target_time + condition.get("deadline", 0)
    result = []
    for number, fragment in enumerate(event["fragments"]):
        timestamp = fragment["timestamp"]
        # No future source-event information even when the decision waits.
        if timestamp > target_time:
            continue
        kind = condition["kind"]
        channel = fragment["channel"]
        if kind == "random" and not retained(event["event_id"], number, seed, condition["drop_probability"]):
            continue
        if kind == "support_burst" and not is_target and timestamp >= target_time - condition["seconds"]:
            continue
        if kind == "channel_absent" and channel in condition["channels"]:
            continue
        arrival = fragment.get("available_at", timestamp)
        if kind == "delay" and channel in condition["channels"]:
            arrival += condition["delay_seconds"]
        if arrival <= deadline:
            result.append(fragment)
    return result


class Replay:
    def __init__(self, events, horizon=120, max_history=32):
        self.events = events
        self.horizon = horizon
        self.max_history = max_history
        # Index only accelerates candidate lookup; visible fragment keys must
        # match again before any candidate information is used.
        self.index = defaultdict(list)
        for number, event in enumerate(events):
            keys = {k for f in event["fragments"] for k in f["entity_keys"]}
            for key in keys:
                self.index[(event["run_id"], key)].append((event["timestamp"], number))
        for values in self.index.values():
            values.sort()

    def view(self, number, condition, seed, use_history, generic=False):
        event = self.events[number]
        target_time = event["timestamp"]
        current = visible_fragments(event, condition, seed, target_time, True)
        current_text = " ".join(f.get("baseline_text", f["text"]) if generic else f["text"] for f in current)
        if not current:
            return "", "", np.zeros(10, dtype=np.float32), False
        keys = {key for fragment in current for key in fragment["entity_keys"]}
        candidates = set()
        if use_history:
            for key in keys:
                values = self.index[(event["run_id"], key)]
                lower = bisect_left(values, (target_time - self.horizon, -1))
                upper = bisect_left(values, (target_time, -1))
                candidates.update(i for _, i in values[lower:upper])
        history = []
        ages = []
        for i in sorted(candidates, key=lambda j: (self.events[j]["timestamp"], self.events[j]["event_id"]), reverse=True):
            past = self.events[i]
            visible = visible_fragments(past, condition, seed, target_time)
            observed_keys = {k for fragment in visible for k in fragment["entity_keys"]}
            if not keys.intersection(observed_keys):
                continue
            history.append(" ".join(f["text"] for f in visible))
            ages.append(target_time - past["timestamp"])
            if len(history) == self.max_history:
                break
        channels = {f["channel"] for f in current}
        metadata = np.array([
            min(len(current), 20) / 20,
            float("SYSCALL" in channels), float("EXECVE" in channels),
            float("PROCTITLE" in channels), float("PATH" in channels),
            float(any(c.startswith("USER_") for c in channels)),
            min(len(history), self.max_history) / self.max_history,
            min(ages) / self.horizon if ages else 0,
            max(ages) / self.horizon if ages else 0,
            float(bool(history)),
        ], dtype=np.float32)
        return current_text, " ".join(history), metadata, True

    def matrix(self, indices, condition, seed, arm, dimensions=32768):
        use_history = arm in {"entity_context", "context_dropout"}
        views = [self.view(int(i), condition, seed, use_history, arm == "generic_event") for i in indices]
        vectorizer = HashingVectorizer(n_features=dimensions, alternate_sign=False, ngram_range=(1, 2), norm="l2", dtype=np.float64)
        now = vectorizer.transform(v[0] for v in views)
        history = vectorizer.transform(v[1] for v in views)
        metadata = sparse.csr_matrix(np.asarray([v[2] for v in views], dtype=np.float64))
        return sparse.hstack([now, history, metadata], format="csr"), np.asarray([v[3] for v in views], dtype=bool)
