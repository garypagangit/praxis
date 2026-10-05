"""Session-level feature extraction.

Four families (see EXPERIMENT.md §4):
  T  timing
  C  content
  S  sequence
  E  error handling

Every feature is computed from the log dump alone (no honeypot trap required).
`FEATURE_FAMILIES` maps each feature name to its family so the evaluation can
run the timing-free ablation (RQ4) by dropping family T.
"""
from __future__ import annotations

import math
import re
import statistics as st
from collections import Counter

from .ingest import Session

# commands whose presence/outcome signals an error
_ERR_PATTERNS = re.compile(
    r"(command not found|no such file|permission denied|not recognized|"
    r"syntax error|cannot access|unknown option|invalid option|error)",
    re.IGNORECASE,
)
_FLAG_RE = re.compile(r"(?:^|\s)-{1,2}[A-Za-z][\w-]*")
_PIPE_RE = re.compile(r"[|]")
_CHAIN_RE = re.compile(r"(&&|;|\|\|)")
_REDIR_NULL_RE = re.compile(r"2>\s*/dev/null|>\s*/dev/null")

# rough recon/enum/action verb buckets for the phase-ordering score
_PHASE = {
    "recon": {"whoami", "id", "uname", "hostname", "pwd", "ls", "cat", "env",
              "ps", "netstat", "ss", "ifconfig", "ip", "w", "last"},
    "enum": {"find", "grep", "locate", "which", "dpkg", "rpm", "crontab",
             "sudo", "getcap", "lsof", "mount", "history"},
    "action": {"wget", "curl", "scp", "nc", "ncat", "python", "python3", "perl",
               "bash", "sh", "chmod", "chown", "ssh", "rm", "echo", "base64"},
}


def _safe(fn, default=0.0):
    try:
        v = fn()
        return float(v) if v is not None and not math.isnan(v) and not math.isinf(v) else default
    except (ValueError, st.StatisticsError, ZeroDivisionError, IndexError):
        return default


def _verb(cmd: str) -> str:
    cmd = cmd.strip()
    if not cmd:
        return ""
    tok = re.split(r"\s+", cmd)[0]
    tok = tok.split("/")[-1]
    return tok.lower()


def _entropy(counts) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts if c > 0)


def extract(session: Session) -> dict[str, float]:
    cmds = session.commands
    n = len(cmds)
    texts = [c.text for c in cmds]
    gaps = [c.gap_ms for c in cmds if c.gap_ms is not None and c.gap_ms >= 0]
    verbs = [_verb(t) for t in texts if t]

    f: dict[str, float] = {}

    # ---------------- T: timing ----------------
    gaps_s = [g / 1000.0 for g in gaps]
    f["T_n_gaps"] = float(len(gaps_s))
    f["T_gap_mean"] = _safe(lambda: st.mean(gaps_s))
    f["T_gap_median"] = _safe(lambda: st.median(gaps_s))
    f["T_gap_std"] = _safe(lambda: st.pstdev(gaps_s)) if len(gaps_s) > 1 else 0.0
    f["T_gap_cov"] = _safe(lambda: st.pstdev(gaps_s) / st.mean(gaps_s)) if len(gaps_s) > 1 and st.mean(gaps_s) > 0 else 0.0
    f["T_gap_iqr"] = _safe(lambda: _iqr(gaps_s))
    f["T_gap_min"] = _safe(lambda: min(gaps_s)) if gaps_s else 0.0
    f["T_frac_lt_1s"] = _safe(lambda: sum(g < 1.0 for g in gaps_s) / len(gaps_s)) if gaps_s else 0.0
    f["T_frac_gt_10s"] = _safe(lambda: sum(g > 10.0 for g in gaps_s) / len(gaps_s)) if gaps_s else 0.0
    f["T_gap_entropy"] = _safe(lambda: _log_quantized_entropy(gaps_s))
    f["T_autocorr_lag1"] = _safe(lambda: _autocorr(gaps_s, 1))
    f["T_ks_lognormal"] = _safe(lambda: _ks_lognormal(gaps_s))

    # ---------------- C: content ----------------
    lens = [len(t) for t in texts if t]
    f["C_len_mean"] = _safe(lambda: st.mean(lens)) if lens else 0.0
    f["C_len_std"] = _safe(lambda: st.pstdev(lens)) if len(lens) > 1 else 0.0
    f["C_len_max"] = _safe(lambda: max(lens)) if lens else 0.0
    f["C_flag_density"] = _safe(lambda: sum(len(_FLAG_RE.findall(t)) for t in texts) / n) if n else 0.0
    f["C_pipe_rate"] = _safe(lambda: sum(bool(_PIPE_RE.search(t)) for t in texts) / n) if n else 0.0
    f["C_chain_rate"] = _safe(lambda: sum(bool(_CHAIN_RE.search(t)) for t in texts) / n) if n else 0.0
    f["C_long_oneliner_rate"] = _safe(lambda: sum(len(t) > 80 for t in texts) / n) if n else 0.0
    f["C_devnull_rate"] = _safe(lambda: sum(bool(_REDIR_NULL_RE.search(t)) for t in texts) / n) if n else 0.0
    f["C_verb_entropy"] = _entropy(list(Counter(verbs).values()))
    f["C_unique_verb_ratio"] = _safe(lambda: len(set(verbs)) / len(verbs)) if verbs else 0.0
    f["C_dup_cmd_rate"] = _safe(lambda: 1 - len(set(texts)) / len(texts)) if texts else 0.0
    # near-duplicate retries (same verb + >0.8 char overlap with an earlier cmd)
    f["C_near_dup_rate"] = _safe(lambda: _near_dup_rate(texts))
    f["C_has_base64"] = float(any("base64" in t for t in texts))

    # ---------------- S: sequence ----------------
    f["S_n_commands"] = float(n)
    f["S_bigram_entropy"] = _safe(lambda: _bigram_entropy(verbs))
    f["S_phase_order_score"] = _safe(lambda: _phase_order_score(verbs))
    f["S_ref_prev_output_rate"] = _safe(lambda: _ref_prev_output(cmds))
    f["S_repeat_after_error_rate"] = _safe(lambda: _repeat_after_error(cmds))

    # ---------------- E: error handling ----------------
    errs = [bool(_ERR_PATTERNS.search(c.output or "")) for c in cmds]
    f["E_error_rate"] = _safe(lambda: sum(errs) / n) if n else 0.0
    f["E_mean_cmds_to_recover"] = _safe(lambda: _mean_recover(errs))
    f["E_edit_rate"] = _safe(lambda: st.mean([c.__dict__.get("_edits", 0) for c in cmds])) if cmds else 0.0

    return f


# ------------------------- helpers ------------------------- #
def _iqr(xs):
    if len(xs) < 2:
        return 0.0
    xs = sorted(xs)
    q1 = xs[len(xs) // 4]
    q3 = xs[(3 * len(xs)) // 4]
    return q3 - q1


def _autocorr(xs, lag):
    if len(xs) <= lag + 1:
        return 0.0
    m = st.mean(xs)
    num = sum((xs[i] - m) * (xs[i + lag] - m) for i in range(len(xs) - lag))
    den = sum((x - m) ** 2 for x in xs)
    return num / den if den else 0.0


def _log_quantized_entropy(xs):
    if not xs:
        return 0.0
    buckets = Counter()
    for x in xs:
        b = 0 if x <= 0 else int(math.floor(math.log10(x + 1e-9) * 2))
        buckets[b] += 1
    return _entropy(list(buckets.values()))


def _ks_lognormal(xs):
    """KS distance between observed gaps and a fitted log-normal."""
    xs = [x for x in xs if x > 0]
    if len(xs) < 3:
        return 0.0
    logs = [math.log(x) for x in xs]
    mu, sigma = st.mean(logs), (st.pstdev(logs) or 1e-6)
    xs_sorted = sorted(xs)
    n = len(xs_sorted)
    d = 0.0
    for i, x in enumerate(xs_sorted):
        z = (math.log(x) - mu) / sigma
        cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        d = max(d, abs(cdf - (i + 1) / n), abs(cdf - i / n))
    return d


def _bigram_entropy(verbs):
    if len(verbs) < 2:
        return 0.0
    bg = Counter(zip(verbs, verbs[1:]))
    return _entropy(list(bg.values()))


def _phase_order_score(verbs):
    """Fraction of adjacent verb pairs that respect recon→enum→action order.
    Agents tend to follow the textbook phase order closely."""
    rank = {}
    for i, (_, vs) in enumerate(_PHASE.items()):
        for v in vs:
            rank[v] = i
    seq = [rank[v] for v in verbs if v in rank]
    if len(seq) < 2:
        return 0.0
    ok = sum(a <= b for a, b in zip(seq, seq[1:]))
    return ok / (len(seq) - 1)


def _ref_prev_output(cmds):
    """Rate at which a command contains a token that appeared in the previous
    command's output (quoting enumerated results — common for agents)."""
    if len(cmds) < 2:
        return 0.0
    hits = 0
    for prev, cur in zip(cmds, cmds[1:]):
        out_toks = set(re.findall(r"[A-Za-z0-9_./-]{4,}", prev.output or ""))
        cur_toks = set(re.findall(r"[A-Za-z0-9_./-]{4,}", cur.text))
        if out_toks & cur_toks:
            hits += 1
    return hits / (len(cmds) - 1)


def _repeat_after_error(cmds):
    if len(cmds) < 2:
        return 0.0
    rep = tot = 0
    for prev, cur in zip(cmds, cmds[1:]):
        if _ERR_PATTERNS.search(prev.output or ""):
            tot += 1
            if cur.text.strip() == prev.text.strip():
                rep += 1
    return rep / tot if tot else 0.0


def _mean_recover(errs):
    gaps, run = [], None
    for i, e in enumerate(errs):
        if e and run is None:
            run = i
        elif not e and run is not None:
            gaps.append(i - run)
            run = None
    return st.mean(gaps) if gaps else 0.0


def _near_dup_rate(texts):
    if len(texts) < 2:
        return 0.0
    hits = 0
    for i, t in enumerate(texts[1:], 1):
        for prev in texts[max(0, i - 3):i]:
            if prev and t and _verb(prev) == _verb(t) and prev != t:
                overlap = len(set(prev) & set(t)) / max(len(set(prev) | set(t)), 1)
                if overlap > 0.8:
                    hits += 1
                    break
    return hits / (len(texts) - 1)


# feature → family map (built once from a probe session)
FEATURE_FAMILIES = {}
def _build_family_map():
    prefix = {"T_": "T", "C_": "C", "S_": "S", "E_": "E"}
    probe = Session(session_id="_probe", label="agent", source="x",
                    commands=[])
    # extract on an empty session just to enumerate names
    from .ingest import Command
    probe.commands = [Command("ls -la", 100.0, "x"), Command("whoami", 2000.0, "y")]
    for name in extract(probe):
        FEATURE_FAMILIES[name] = next((fam for p, fam in prefix.items() if name.startswith(p)), "?")
_build_family_map()


def feature_names(exclude_families=()):
    return [n for n, fam in FEATURE_FAMILIES.items() if fam not in exclude_families]


def to_matrix(sessions, exclude_families=()):
    """Return (X, y, groups_dict, names) for a list of Sessions."""
    import numpy as np
    names = feature_names(exclude_families)
    rows, y, models, envs, tasks, fams, sids = [], [], [], [], [], [], []
    for s in sessions:
        feats = extract(s)
        rows.append([feats.get(nm, 0.0) for nm in names])
        y.append(s.label)
        models.append(s.model)
        fams.append(s.model_family)
        envs.append(s.environment)
        tasks.append(s.task)
        sids.append(s.session_id)
    X = np.asarray(rows, dtype=float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    groups = {"model": models, "family": fams, "environment": envs, "task": tasks, "session_id": sids}
    return X, y, groups, names
