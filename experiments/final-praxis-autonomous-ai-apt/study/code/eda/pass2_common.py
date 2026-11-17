"""Study 3 EDA Pass 2: shared pieces.

Implements `real_lab3_eda_handoff.md` section 6, as amended by section 12a: Pass 2 is
run after the trials, as a report only. It cannot correct, add or drop a feature.

The Pass 1 code in this folder is part of Freeze 2 and is not edited. Pass 2 is
separate files. It imports `eda_common` (frozen) for the output helpers and the session
table, and adds what Pass 2 needs:

  * Inputs2: every input is on a fixed list and is checked against Freeze 1 or
    Freeze 2 before it is read. The evidence folder, `set_aside/`, the private key
    map and the test-label files are refused by name (handoff rule 2).
  * load_training: feature values and command text are read from rows marked `train`
    in the frozen split file and from no other row. The loader logs the row count of
    every split value and stops if a row of any other split is present (rule 3).
  * the rank statistics of handoff section 6. No model is fitted (rule 4).
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                              # allows python3 -I
_LIBS = os.environ.get("S3_LIBS")                     # where SciPy was installed, as for the trials
if _LIBS and _LIBS not in sys.path:
    sys.path.append(_LIBS)

import eda_common as E                                # frozen with Pass 1; imported, never edited

import numpy as np
from scipy import stats as sps

PASS2_VERSION = "study3-eda-pass2-1.0"
TRAIN = "train"
FLAG = 0.95                 # shortcut flag (handoff section 6)
DUP_RHO = 0.98              # near-duplicate rule
DUP_MIN_ROWS = 10           # reading P2-7: a pair needs this many rows where both are defined
MIN_WINDOWS = 10            # same-stage values resting on fewer are marked indicative
MIN_KW = 5                  # stage groups with fewer windows are left out of Kruskal-Wallis
TOP_N = 20
LENGTHS = [("w30", 30), ("w60", 60)]
TIERS = ["behavior", "command_content", "context", "input_channel"]
TIER_LABEL = {"behavior": "Behavior", "command_content": "Command content", "context": "Context",
              "input_channel": "Input channel"}
RANGES = ["Original Austin", "AHIR-03", "AHIR-01"]


class Inputs2(E.Inputs):
    """Inputs for Pass 2: allowlist, refusal by name, Freeze 1 or Freeze 2 check, log."""

    def __init__(self, allow):
        super().__init__(allow)
        fz2 = os.path.join(E.ROOT, "reports", "FREEZE_2.json")
        self.freeze2_sha256 = E.sha256_file(fz2)
        with open(fz2, encoding="utf-8") as f:
            self.freeze2 = json.load(f)["files"]

    def path(self, rel, columns=None):
        if any(part in rel for part in E.FORBIDDEN_PARTS):
            raise SystemExit("REFUSED: the EDA never opens " + rel)
        if rel not in self.allow:
            raise SystemExit("REFUSED: not in this pass's input list: " + rel)
        if not (rel.startswith("data/") or rel.startswith("reports/")):
            raise SystemExit("REFUSED: inputs come only from data/ and reports/: " + rel)
        p = os.path.join(E.ROOT, *rel.split("/"))
        digest, size = E.sha256_file(p), os.path.getsize(p)
        which, frozen = "freeze_1", self.freeze.get(rel)
        if frozen is None:
            which, frozen = "freeze_2", self.freeze2.get(rel)
        if frozen is None:
            raise SystemExit("STOP: input is listed in neither freeze: " + rel)
        if frozen["sha256"] != digest or frozen["bytes"] != size:
            raise SystemExit("STOP: input does not match %s: %s" % (which, rel))
        entry = {"bytes": size, "sha256": digest, which: "match"}
        if columns is not None:
            entry["columns_read"] = list(columns)
        self.opened[rel] = entry
        return p


def window_file(session_key, login_key, wl):
    return "data/windows/%s/%s/%s.jsonl" % (wl, session_key, login_key)


def pass2_inputs(wl_list=("w30", "w60")):
    """The fixed input list of Pass 2. Window files are added one by one for E1 only."""
    allow = [
        "reports/05_windows_report.json",            # session labels (P001 ...) beside the session keys
        "reports/10_features_report.json",           # tier counts and undefined columns of the whole table
        "data/labels/sessions.csv",                  # class of each session
        "data/description/sessions.csv",             # lab range of each session
        "reports/eda/tables/T3_split_counts.csv",    # Pass 1 outputs, for check 1
        "reports/eda/tables/T3_split_rows_by_stage_group.csv",
        "reports/eda/tables/E2_overview.csv",
        "reports/eda/tables/T1_dataset_summary_by_session.csv",
    ]
    for wl in wl_list:
        allow += [
            "data/splits/splits_%s.csv" % wl,
            "data/description/window_description_%s.csv" % wl,
            "data/features/%s/features.csv" % wl,
            "data/features/%s/feature_columns.json" % wl,
            "data/features/%s/per_command.jsonl" % wl,
        ]
    return allow


def load_columns(inp, wl):
    meta = inp.read_json("data/features/%s/feature_columns.json" % wl)
    cols = []
    for c in meta["columns"]:
        goes = c.get("goes_with", c["tier"])
        cols.append({"column": c["column"], "tier": c["tier"], "kind": c["kind"], "goes_with": goes,
                     "in_main": goes in ("behavior", "command_content"),
                     "definition": c["definition"], "undefined_when": c["undefined_when"]})
    return cols, meta


def load_training(inp, wl, sessions):
    """Training rows of one window length.

    Returns (rows, log). Each row: window_id, session_key, session, class, lab_range,
    stage_group, x (dict column -> float, or None where undefined).
    Feature values of rows that are not marked `train` are never parsed or kept.
    """
    by_key = {s["session_key"]: s for s in sessions}
    split_rows = inp.read_csv("data/splits/splits_%s.csv" % wl, ["window_id", "session_key", "split"])
    split_of = {r["window_id"]: r["split"] for r in split_rows}
    split_counts = {}
    for r in split_rows:
        split_counts[r["split"]] = split_counts.get(r["split"], 0) + 1
    train = {r["window_id"]: r["session_key"] for r in split_rows if r["split"] == TRAIN}

    desc = inp.read_csv("data/description/window_description_%s.csv" % wl, ["window_id", "stage_group", "keep"])
    stage = {r["window_id"]: r["stage_group"] for r in desc if r["window_id"] in train}

    rel = "data/features/%s/features.csv" % wl
    p = inp.path(rel)
    rows, seen = [], {}
    with open(p, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        if header[0] != "window_id":
            raise SystemExit("STOP: unexpected feature table header")
        columns = header[1:]
        for rec in reader:
            wid = rec[0]
            sp = split_of.get(wid)
            if sp is None:
                raise SystemExit("STOP: feature row has no split: " + wid)
            seen[sp] = seen.get(sp, 0) + 1
            if sp != TRAIN:
                continue                                  # values of this row are not parsed
            s = by_key[train[wid]]
            rows.append({"window_id": wid, "session_key": s["session_key"], "session": s["session"],
                         "class": s["class"], "lab_range": s["lab_range"], "stage_group": stage[wid],
                         "x": {c: (None if v == "" else float(v)) for c, v in zip(columns, rec[1:])}})
    loaded = {}
    for r in rows:
        sp = split_of[r["window_id"]]
        loaded[sp] = loaded.get(sp, 0) + 1
    other = sum(n for sp, n in loaded.items() if sp != TRAIN)
    if other or len(rows) != split_counts.get(TRAIN, 0) or len(rows) != len(train):
        raise SystemExit("STOP: a row of another split is present, or training rows are missing (%s)" % wl)
    inp.opened[rel]["rows_in_file"] = sum(seen.values())
    inp.opened[rel]["rows_kept"] = len(rows)
    log = {"split_file_rows_by_value": dict(sorted(split_counts.items())),
           "feature_rows_seen_by_split": dict(sorted(seen.items())),
           "feature_rows_loaded_by_split": {sp: loaded.get(sp, 0) for sp in E.SPLITS},
           "rows_of_another_split_loaded": other,
           "training_rows": len(rows),
           "columns": len(columns)}
    return rows, columns, log


def load_training_commands(inp, wl, rows):
    """Per-command rows whose window is a training row. Other rows are skipped unparsed
    beyond their window id. A program start that fell in a window that is not a
    training row is dropped from the row (rule 3)."""
    train = {r["window_id"] for r in rows}
    rel = "data/features/%s/per_command.jsonl" % wl
    p = inp.path(rel)
    cmds, n_all, starts = [], 0, {"in_training_windows": 0, "dropped_other_window": 0}
    with open(p, encoding="utf-8") as f:
        for line in f:
            n_all += 1
            o = json.loads(line)
            if o["window_id"] not in train:
                continue
            kept = [s for s in o["programs_started"] if s["window_id"] in train]
            starts["in_training_windows"] += len(kept)
            starts["dropped_other_window"] += len(o["programs_started"]) - len(kept)
            o["starts_dropped"] = len(o["programs_started"]) - len(kept)
            o["programs_started"] = kept
            cmds.append(o)
    inp.opened[rel]["rows_in_file"] = n_all
    inp.opened[rel]["rows_kept"] = len(cmds)
    return cmds, {"per_command_rows_in_file": n_all, "per_command_rows_of_training_windows": len(cmds),
                  "program_starts": starts}


# ----------------------------------------------------------------------------- statistics
def a_stat(ai, hu):
    """Share of (AI window, human window) pairs in which the AI value is higher, ties one half."""
    ai, hu = np.asarray(ai, dtype=float), np.asarray(hu, dtype=float)
    if len(ai) == 0 or len(hu) == 0:
        return None
    ranks = sps.rankdata(np.concatenate([ai, hu]), method="average")
    u = ranks[:len(ai)].sum() - len(ai) * (len(ai) + 1) / 2.0
    return float(u / (len(ai) * len(hu)))


def auc_of(a):
    return None if a is None else max(a, 1.0 - a)


def directed(a, a_ref):
    """AUC of `a` kept in the direction of the reference result (a_ref). Under 0.5: the direction reverses."""
    if a is None or a_ref is None:
        return None
    return a if a_ref >= 0.5 else 1.0 - a


def values(rows, col, cls=None, keep=None):
    out = []
    for r in rows:
        if cls is not None and r["class"] != cls:
            continue
        if keep is not None and not keep(r):
            continue
        v = r["x"][col]
        if v is not None:
            out.append(v)
    return out


def spearman(rows, c1, c2):
    xs, ys = [], []
    for r in rows:
        a, b = r["x"][c1], r["x"][c2]
        if a is not None and b is not None:
            xs.append(a)
            ys.append(b)
    n = len(xs)
    if n < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None, n
    return float(sps.spearmanr(xs, ys).statistic), n


def epsilon2(rows, col, cls):
    """Kruskal-Wallis H across stage groups within one class, divided by (n - 1)."""
    groups, used = [], []
    for g in E.STAGE_GROUPS:
        v = values(rows, col, cls, keep=lambda r, g=g: r["stage_group"] == g)
        if len(v) >= MIN_KW:
            groups.append(v)
            used.append(g)
    n = sum(len(g) for g in groups)
    if len(groups) < 2 or len(set(x for g in groups for x in g)) < 2:
        return None, used, n
    h = float(sps.kruskal(*groups).statistic)
    return h / (n - 1), used, n


def sessions_behind(rows, col, cls, keep=None):
    """Windows, sessions and the largest session among the defined rows of one class."""
    count = {}
    for r in rows:
        if r["class"] != cls or (keep is not None and not keep(r)) or r["x"][col] is None:
            continue
        count[r["session"]] = count.get(r["session"], 0) + 1
    n = sum(count.values())
    if not n:
        return 0, 0, "", ""
    top = sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    return n, len(count), top[0], "%.1f" % (100.0 * top[1] / n)


def pass1_table(inp, name, columns):
    """A Pass 1 table, read from the study folder and checked against Freeze 2."""
    return inp.read_csv("reports/eda/tables/" + name, columns)


def f4(v):
    return "" if v is None else "%.4f" % v


def g6(v):
    return "" if v is None else "%.6g" % v
