"""Label-free host roles and causal completed-flow histories.

History is queried at current flow START; the current model also receives its
completed-flow summary. Thus decisions are retrospective at flow completion,
not early warnings. Equal-time and overlapping earlier-started flows are absent
from history until they have completed strictly before the current start.
"""
from __future__ import annotations

from bisect import bisect_left, insort
from collections import Counter, deque
import hashlib

import numpy as np

WINDOWS_MS = (300_000, 1_800_000)
ROLE_NAMES = ["OTHER_ADDRESS", "DEPARTMENT", "PUBLIC_SERVICES", "PRIVATE_SERVICES"]
STATE_NAMES = ["log_completed_flows", "log_transmitted_bytes", "log_received_bytes",
               "log_distinct_peers", "log_initiated_flows", "log_remote_admin_flows",
               "log_internal_peer_flows", "peer_seen_in_window", "host_seen_before"]


def role(ip):
    parts = str(ip).split(".")
    if len(parts) != 4 or parts[:2] != ["10", "1"]:
        return 0
    return {"1": 1, "2": 1, "3": 1, "4": 2, "5": 3}.get(parts[2], 0)


def role_features(src, dst):
    return np.column_stack([np.eye(4)[[role(s) for s in src]], np.eye(4)[[role(d) for d in dst]]])


class WindowState:
    def __init__(self):
        self.events = deque()
        self.peers = Counter()
        self.sums = np.zeros(5, dtype=float)

    def add(self, end, peer, tx, rx, initiated, admin, internal):
        values = np.array([tx, rx, initiated, admin, internal], dtype=float)
        self.events.append((end, peer, values))
        self.peers[peer] += 1
        self.sums += values

    def query(self, time, width, peer, known):
        while self.events and self.events[0][0] < time - width:
            _, old_peer, values = self.events.popleft()
            self.sums -= values
            self.peers[old_peer] -= 1
            if self.peers[old_peer] == 0:
                del self.peers[old_peer]
        # Counters and byte sums are integer-valued source measurements.
        if np.any(self.sums < -.01):
            raise ValueError("Negative historical sums")
        s = np.maximum(self.sums, 0)
        values = [np.log1p(len(self.events)), np.log1p(s[0]), np.log1p(s[1]),
                  np.log1p(len(self.peers)), np.log1p(s[2]), np.log1p(s[3]),
                  np.log1p(s[4]), float(peer in self.peers), float(known)]
        latest = self.events[-1][0] if self.events else -1.
        if latest >= time:
            raise ValueError("Future or equal-time event entered history")
        return values, latest


def history_features(start, end, src, dst, forward_bytes, reverse_bytes, remote_admin):
    """Inputs contain no labels. Wrong-host control uses only hosts seen so far.

    The wrong-host donor is SHA256(host) modulo the currently observed sorted
    inventory, shifted if it equals the queried host. It corrupts host linkage
    without importing a future event or assuming a future host inventory.
    """
    start, end = np.asarray(start), np.asarray(end)
    n = len(start)
    if any(len(v) != n for v in [end, src, dst, forward_bytes, reverse_bytes, remote_admin]):
        raise ValueError("Mismatched event arrays")
    if not np.isfinite(start).all() or not np.isfinite(end).all() or np.any(end < start):
        raise ValueError("Invalid event time")
    width = len(WINDOWS_MS) * 2 * len(STATE_NAMES)
    history, wrong = np.zeros((n, width)), np.zeros((n, width))
    latest, wrong_latest = np.full(n, -1.), np.full(n, -1.)
    states, known_hosts, hashes = {}, [], {}
    def ensure(host):
        if host not in states:
            states[host] = [WindowState() for _ in WINDOWS_MS]
            insort(known_hosts, host)
    def donor(host):
        if not known_hosts:
            return None
        if host not in hashes:
            hashes[host] = int.from_bytes(hashlib.sha256(str(host).encode()).digest()[:8], "big")
        index = hashes[host] % len(known_hosts)
        if known_hosts[index] == host:
            index = (index + 1) % len(known_hosts)
        return known_hosts[index] if known_hosts[index] != host else None
    def query(host, peer, time):
        if host not in states:
            return [0.] * (len(WINDOWS_MS) * len(STATE_NAMES)), -1.
        out, most_recent = [], -1.
        for duration, state in zip(WINDOWS_MS, states[host]):
            values, used = state.query(time, duration, peer, True)
            out.extend(values); most_recent = max(most_recent, used)
        return out, most_recent
    completed = np.argsort(end, kind="stable")
    pointer = 0
    for count, current in enumerate(np.argsort(start, kind="stable")):
        t = start[current]
        while pointer < n and end[completed[pointer]] < t:
            j = completed[pointer]
            for host, peer, tx, rx, initiated in [
                (src[j], dst[j], forward_bytes[j], reverse_bytes[j], 1),
                (dst[j], src[j], reverse_bytes[j], forward_bytes[j], 0),
            ]:
                ensure(host)
                for state in states[host]:
                    state.add(end[j], peer, tx, rx, initiated, remote_admin[j], role(peer) != 0)
            pointer += 1
        values, wrong_values = [], []
        for host, peer in [(src[current], dst[current]), (dst[current], src[current])]:
            a, used = query(host, peer, t)
            b, used_wrong = query(donor(host), peer, t)
            values.extend(a); wrong_values.extend(b)
            latest[current] = max(latest[current], used)
            wrong_latest[current] = max(wrong_latest[current], used_wrong)
        history[current], wrong[current] = values, wrong_values
        if count and count % 100000 == 0:
            print(f"HISTORY {count}/{n} observed_hosts={len(known_hosts)}", flush=True)
    if not ((latest < start).all() and (wrong_latest < start).all()):
        raise ValueError("History availability invariant failed")
    return history, wrong, latest, wrong_latest
