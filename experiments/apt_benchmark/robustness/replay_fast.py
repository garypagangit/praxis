"""Exact bounded-history replay using a lazy merge of entity indexes.

This changes candidate enumeration only. Visibility, history eligibility,
ordering, metadata, and the inherited feature-matrix builder retain Replay's
semantics. The original replay.py remains the frozen reference implementation.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from heapq import merge
from operator import itemgetter

import numpy as np

from .replay import Replay, visible_fragments


_TIMESTAMP = itemgetter(0)


def _reverse_range(values, lower, upper):
    """Iterate a bounded index backwards without copying its slice."""
    for position in range(upper - 1, lower - 1, -1):
        yield values[position]


class FastReplay(Replay):
    """Replay-equivalent views with bounded work on dense eligible histories.

    Inputs should be treated as immutable after construction, as with Replay.
    Qualified load_events inputs have unique IDs. Direct callers supplying
    duplicate IDs fall back to Replay, preserving its stable tie behavior.
    """

    def __init__(self, events, horizon=120, max_history=32):
        self.events = events
        self.horizon = horizon
        self.max_history = max_history
        self._reference_fallback = False
        self._ordered_index = defaultdict(list)
        seen_ids = set()
        for number, event in enumerate(events):
            if event["event_id"] in seen_ids:
                self._reference_fallback = True
                del self._ordered_index
                super().__init__(events, horizon, max_history)
                return
            seen_ids.add(event["event_id"])
            keys = {key for fragment in event["fragments"] for key in fragment["entity_keys"]}
            entry = (event["timestamp"], event["event_id"], number)
            for key in keys:
                self._ordered_index[(event["run_id"], key)].append(entry)
        for values in self._ordered_index.values():
            values.sort()

    def _candidate_indices(self, run_id, keys, target_time):
        streams = []
        for key in keys:
            values = self._ordered_index[(run_id, key)]
            lower = bisect_left(values, target_time - self.horizon, key=_TIMESTAMP)
            upper = bisect_left(values, target_time, key=_TIMESTAMP)
            if lower < upper:
                streams.append(_reverse_range(values, lower, upper))
        previous = None
        # A shared event has the identical tuple in every entity index, so its
        # duplicates are adjacent in this merge; no full candidate set is needed.
        for _, _, number in merge(*streams, reverse=True):
            if number != previous:
                yield number
                previous = number

    def view(self, number, condition, seed, use_history, generic=False):
        if self._reference_fallback:
            return super().view(number, condition, seed, use_history, generic)
        event = self.events[number]
        target_time = event["timestamp"]
        current = visible_fragments(event, condition, seed, target_time, True)
        current_text = " ".join(f.get("baseline_text", f["text"]) if generic else f["text"] for f in current)
        if not current:
            return "", "", np.zeros(10, dtype=np.float32), False
        keys = {key for fragment in current for key in fragment["entity_keys"]}
        candidates = self._candidate_indices(event["run_id"], keys, target_time) if use_history else ()
        history = []
        ages = []
        for i in candidates:
            past = self.events[i]
            visible = visible_fragments(past, condition, seed, target_time)
            observed_keys = {key for fragment in visible for key in fragment["entity_keys"]}
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
