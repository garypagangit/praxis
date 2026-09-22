"""Past-only source-host authentication features; no target labels accepted."""
from __future__ import annotations

import hashlib
import numpy as np
from ..host_history_exfil.context import role

WINDOWS = (300_000., 1_800_000.)


def _query(times, at, width):
    return np.searchsorted(times, at, side="left") - np.searchsorted(times, at - width, side="left")


def build(start, src, events, observed):
    start, src = np.asarray(start), np.asarray(src)
    if len(src) != len(start) or not np.isfinite(start).all():
        raise ValueError("Invalid flow query")
    names = [str(s) for s in events["kind_names"]]
    for data in [events, observed]:
        if not (len(data["host"]) == len(data["time_ms"])) or not np.isfinite(data["time_ms"]).all():
            raise ValueError("Invalid event times")
    if len(events["kind"]) != len(events["time_ms"]) or np.any(events["kind"] < 0) or np.any(events["kind"] >= len(names)):
        raise ValueError("Invalid event kind")
    hosts = sorted(set(observed["host"].tolist()))
    family, obs_times, first, kind_times = {}, {}, {}, {}
    for host in hosts:
        mask = observed["host"] == host
        fam = np.unique(observed["family"][mask])
        if len(fam) != 1:
            raise ValueError("Ambiguous host log family")
        family[host] = str(fam[0]); obs_times[host] = np.sort(observed["time_ms"][mask])
        first[host] = obs_times[host][0]
        kind_times[host] = [np.sort(events["time_ms"][(events["host"] == host) & (events["kind"] == k)]) for k in range(len(names))]
    n, width = len(start), len(WINDOWS) * len(names)
    auth, wrong = np.zeros((n, width)), np.zeros((n, width))
    # Same availability controls enter every fitting arm. These describe observed
    # records, not proven uninterrupted telemetry collection.
    availability = np.zeros((n, 7))
    latest, wrong_latest = np.full(n, -1.), np.full(n, -1.)
    donors = np.full(n, "", dtype="U64")
    def auth_query(host, rows, target, latest_target):
        t = start[rows]
        for k, times in enumerate(kind_times[host]):
            for w, window in enumerate(WINDOWS):
                target[rows, w * len(names) + k] = np.log1p(_query(times, t, window))
            ends = np.searchsorted(times, t, side="left")
            known = ends > 0
            if known.any():
                r = rows[known]; last = times[ends[known] - 1]
                # Receipt reports the latest prior auth event, even if too old
                # to enter a lookback counter.
                latest_target[r] = np.maximum(latest_target[r], last)
    for host in np.unique(src):
        if host not in first:
            continue
        rows = np.flatnonzero(src == host); t = start[rows]
        times = obs_times[host]; ends = np.searchsorted(times, t, side="left")
        seen = ends > 0
        availability[rows, 0] = seen
        for w, window in enumerate(WINDOWS):
            availability[rows, 1 + w] = np.log1p(_query(times, t, window))
        recency = np.zeros(len(rows))
        recency[seen] = np.minimum(WINDOWS[-1], t[seen] - times[ends[seen] - 1])
        availability[rows, 3] = np.log1p(recency / 1000.)
        availability[rows, 4] = seen & (family[host] == "linux_audit")
        availability[rows, 5] = seen & (family[host] == "windows_security")
        auth_query(host, rows[seen], auth, latest)
        # Stable donor preference uses identities only for joining, never as
        # predictors. Donors must already have an observed event and share the
        # source's log family. The queried source must itself be observed.
        candidates = [h for h in hosts if h != host and family[h] == family[host] and role(h) == role(host)]
        candidates.sort(key=lambda h: hashlib.sha256(f"AUTH_DONOR_V1|{host}|{h}".encode()).digest())
        unassigned = seen.copy()
        for other in candidates:
            use = unassigned & (first[other] < t)
            selected = rows[use]
            if len(selected):
                donors[selected] = other; availability[selected, 6] = 1
                auth_query(other, selected, wrong, wrong_latest)
                unassigned[use] = False
    if not ((latest < start).all() and (wrong_latest < start).all()):
        raise ValueError("Future or equal-time event entered features")
    if np.any((donors != "") & (donors == src)):
        raise ValueError("Wrong-host control linked original host")
    return {"auth": auth, "wrong_auth": wrong, "availability": availability,
            "latest_auth": latest, "latest_wrong_auth": wrong_latest, "donor": donors,
            "feature_names": np.asarray([f"prior_{int(w/60000)}m_{name}" for w in WINDOWS for name in names]),
            "availability_names": np.asarray(["source_seen_before", "log_observed_5m", "log_observed_30m", "log_capped_observation_age_seconds", "linux_previously_observed", "windows_previously_observed", "eligible_wrong_host_exists"])}
