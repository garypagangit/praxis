"""Study 3 trials: shared pieces.

Implements sections 5 to 9 of `real_lab3_feature_trial_design.md` (approved; amended
with F16 and F17 on 2026-11-13). Written fresh for study 3: nothing is imported from
the synthetic project or from the code of studies 1, 2 and 2b.

Two modes:
  plumbing  Every fold of every trial is fitted and calibrated. No held-out session
            and no test row is predicted. Only counts and hashes are written. The
            test-label files and the description files cannot be opened.
  scored    Needs reports/FREEZE_2.json and checks the code, the feature tables and
            the plumbing log against it. Each trial is scored once into results/.

The readings T1 to T16 named in the comments are listed in section 6a of the design.
"""
import csv
import hashlib
import itertools
import json
import os
import re
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"                       # T11: one thread a process
_LIBS = os.environ.get("S3_LIBS")              # where the pinned libraries were installed
if _LIBS and _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

import numpy as np

TRIAL_VERSION = "study3-trials-1.0"
SEED = 42
REFERENCE_MACRO_F1 = 0.809                     # Alt (2026), design section 7.2
N_BOOT = 2000
SESSION_AI_LINE = 0.5                          # design section 7.3: a fixed line
MODELS = ["lr", "rf", "gb", "hgb", "xgb"]
MODEL_LABEL = {"lr": "Logistic regression", "rf": "Random forest", "gb": "Gradient boosting",
               "hgb": "Histogram gradient boosting", "xgb": "XGBoost"}
LOOKBACK_WINDOWS = {"w30": 4, "w60": 2}        # 2 minutes (P4)
STAGE_GROUPS = ["1-4", "5", "6", "7"]
N_AI_SESSIONS = 4

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ROOT = os.environ.get("S3_ROOT") or os.path.dirname(CODE)
REPORTS = os.path.join(ROOT, "reports")
PLUMB = os.path.join(REPORTS, "plumbing")
RESULTS = os.path.join(ROOT, "results")
FREEZE_2 = os.path.join(REPORTS, "FREEZE_2.json")

# name -> (window length, configuration, row subset)
LOSO_TRIALS = {
    "main": ("w30", "main", None),
    "no_command_content": ("w30", "no_command_content", None),
    "no_context": ("w30", "no_context", None),
    "input_channel": ("w30", "input_channel", None),
    "h1_without": ("w30", "h1_without", None),
    "h1_window_form": ("w30", "h1_window_form", None),
    "h1_lookback_form": ("w30", "h1_lookback_form", None),
    "w60_main": ("w60", "main", None),
    "input_bearing_main": ("w30", "main", "input_bearing"),
}
INSIDE_TRIALS = {"inside_main": ("w30", "main")}
CHANCE_CONFIGS = ["main", "no_command_content"]            # F9
CONFIG_SIZE = {"main": 40, "no_command_content": 22, "no_context": 32, "input_channel": 60,
               "h1_without": 36, "h1_window_form": 38, "h1_lookback_form": 38}
H1_WINDOW = ["cmd_diversity", "transition_entropy"]
H1_LOOKBACK = ["ctx_cmd_diversity", "ctx_transition_entropy"]

# Column guard (design section 8, control 4): a name of this kind can never enter a model.
FORBIDDEN_NAME = re.compile(r"(duration|elapsed|position|index|order|session|login|stage|"
                            r"label|class|split|t_start|t_end)", re.I)
LOG_KINDS = ("count", "size", "time")          # log(1 + x) for logistic regression only
PLAIN_KINDS = ("ratio", "share", "entropy", "correlation")


# ----------------------------------------------------------------------------- files
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def dump_json(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_once(path, text, overwrite=False):
    """Write through a .part file. A scored output is never written twice."""
    if os.path.exists(path) and not overwrite:
        raise SystemExit("REFUSED: already written, and each trial is scored once: " + path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".part"
    with open(part, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(part, path)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Inputs:
    """Opens inputs by name, checks each against its recorded hash, logs it."""
    FORBID_ALWAYS = ("AHIR Participant Evidence", "set_aside", "_private")
    FORBID_PLUMBING = ("labels_test_", "data/description")

    def __init__(self, mode):
        if mode not in ("plumbing", "scored"):
            raise SystemExit("mode is plumbing or scored")
        self.mode = mode
        self.opened = {}
        fz = os.path.join(REPORTS, "FREEZE_1.json")
        self.freeze1_sha256 = sha256_file(fz)
        self.freeze1 = read_json(fz)["files"]
        self.feature_hashes = read_json(os.path.join(REPORTS, "10_features_checks.json"))["outputs"]

    def path(self, rel):
        forbid = self.FORBID_ALWAYS + (self.FORBID_PLUMBING if self.mode == "plumbing" else ())
        if any(part in rel for part in forbid):
            raise SystemExit("REFUSED: the %s run never opens %s" % (self.mode, rel))
        p = os.path.join(ROOT, *rel.split("/"))
        digest = sha256_file(p)
        if rel.startswith("data/features/"):
            want = self.feature_hashes.get(rel)
        else:
            want = self.freeze1.get(rel, {}).get("sha256")
        if want is None:
            raise SystemExit("STOP: input has no recorded hash: " + rel)
        if want != digest:
            raise SystemExit("STOP: input does not match its recorded hash: " + rel)
        self.opened[rel] = digest
        return p

    def rows(self, rel, columns):
        """CSV rows holding only the named columns; other columns are never kept."""
        out = []
        with open(self.path(rel), encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            missing = [c for c in columns if c not in rd.fieldnames]
            if missing:
                raise SystemExit("STOP: %s lacks columns %s" % (rel, missing))
            for r in rd:
                out.append({c: r[c] for c in columns})
        return out


def check_freeze_2(kinds=("trial_code", "feature_table", "design", "plumbing")):
    """Scored mode: the freeze exists and what is about to run is what was frozen."""
    if not os.path.exists(FREEZE_2):
        raise SystemExit("REFUSED: no score before Freeze 2 (reports/FREEZE_2.json is missing)")
    fz = read_json(FREEZE_2)
    bad = []
    for rel, meta in sorted(fz["files"].items()):
        if meta["kind"] not in kinds:
            continue
        base = CODE if rel.startswith("code/") else ROOT
        p = os.path.join(base, *rel.split("/")[1:]) if rel.startswith("code/") else os.path.join(ROOT, *rel.split("/"))
        if not os.path.exists(p) or sha256_file(p) != meta["sha256"]:
            bad.append(rel)
    if bad:
        raise SystemExit("STOP: changed since Freeze 2: " + ", ".join(bad))
    return sha256_file(FREEZE_2)


# ----------------------------------------------------------------------------- data
class Table:
    pass


def load_table(inp, window):
    """Kept windows of one window length: the 60 feature columns, and for each window
    its session, login, window index and input-record count. No stage, time or
    position column is read into memory."""
    colfile = read_json(inp.path("data/features/%s/feature_columns.json" % window))
    columns = [c["column"] for c in colfile["columns"]]
    info = {c["column"]: c for c in colfile["columns"]}
    if len(columns) != 60 or len(info) != 60:
        raise SystemExit("STOP: the column file does not hold the 60 columns of section 4")
    for c in columns:
        if FORBIDDEN_NAME.search(c):
            raise SystemExit("COLUMN GUARD: " + c)
        if info[c]["kind"] not in LOG_KINDS + PLAIN_KINDS:
            raise SystemExit("STOP: unknown column kind for " + c)
    kept = [r for r in inp.rows("data/windows/%s/windows.csv" % window,
                                ["window_id", "session_key", "login_key", "w_index", "n_input", "keep"])
            if r["keep"] == "1"]
    with open(inp.path("data/features/%s/features.csv" % window), encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        if header != ["window_id"] + columns:
            raise SystemExit("COLUMN GUARD: the feature table is not window_id and the 60 columns")
        rows = list(rd)
    if [r[0] for r in rows] != [k["window_id"] for k in kept]:
        raise SystemExit("STOP: the feature rows are not the kept windows, in order")
    rep = read_json(inp.path("reports/05_windows_report.json"))
    label_of = {v["session_key"]: lab for lab, v in rep["sessions"].items()}
    cls = {}
    for r in inp.rows("data/labels/sessions.csv", ["session_key", "class", "included"]):
        if r["included"] == "1":
            cls[label_of[r["session_key"]]] = 1 if r["class"] == "ai" else 0
    t = Table()
    t.window = window
    t.columns = columns
    t.info = info
    t.X = np.array([[float(v) if v != "" else np.nan for v in r[1:]] for r in rows], dtype=float)
    t.window_id = [k["window_id"] for k in kept]
    t.session = np.array([label_of[k["session_key"]] for k in kept])
    t.login = np.array([k["login_key"] for k in kept])
    t.w_index = np.array([int(k["w_index"]) for k in kept])
    t.n_input = np.array([int(k["n_input"]) for k in kept])
    t.sessions = sorted(cls)
    t.class_of = cls                       # session label -> 1 (AI) or 0 (human)
    if sorted(set(t.session)) != t.sessions:
        raise SystemExit("STOP: sessions of the windows and of the session table differ")
    if len(t.sessions) != 9 or sum(cls.values()) != N_AI_SESSIONS:
        raise SystemExit("STOP: the design is written for 5 human and 4 AI sessions")
    return t


def config_columns(table, config):
    """Columns of a configuration (design section 5), in column-file order."""
    tier = lambda c: table.info[c]["tier"]
    goes = lambda c: table.info[c].get("goes_with") or ""
    beh = [c for c in table.columns if tier(c) == "behavior"]
    con = [c for c in table.columns if tier(c) == "command_content"]
    ctx_b = [c for c in table.columns if tier(c) == "context" and goes(c) == "behavior"]
    ctx_c = [c for c in table.columns if tier(c) == "context" and goes(c) == "command_content"]
    ctx_i = [c for c in table.columns if tier(c) == "context" and goes(c) == "input_channel"]
    inp = [c for c in table.columns if tier(c) == "input_channel"]
    main = beh + con + ctx_b + ctx_c
    sets = {
        "main": main,
        "no_command_content": beh + ctx_b,
        "no_context": beh + con,
        "input_channel": main + inp + ctx_i,
        "h1_without": [c for c in main if c not in H1_WINDOW + H1_LOOKBACK],
        "h1_window_form": [c for c in main if c not in H1_LOOKBACK],
        "h1_lookback_form": [c for c in main if c not in H1_WINDOW],
    }
    cols = [c for c in table.columns if c in set(sets[config])]
    if len(cols) != CONFIG_SIZE[config] or len(set(cols)) != len(cols):
        raise SystemExit("COLUMN GUARD: configuration %s has %d columns" % (config, len(cols)))
    for c in cols:
        if c not in table.info or FORBIDDEN_NAME.search(c):
            raise SystemExit("COLUMN GUARD: " + c)
    if "cmd_count" not in cols:
        raise SystemExit("COLUMN GUARD: cmd_count is in every configuration")
    return cols


def subset_rows(table, subset):
    if subset is None:
        return np.arange(len(table.window_id))
    if subset == "input_bearing":          # T8: at least one input record in the window table
        return np.where(table.n_input >= 1)[0]
    raise SystemExit("unknown subset " + str(subset))


def chance_labelings(sessions):
    """Every way of calling 4 of the 9 sessions AI (P8), in the order of the session labels."""
    return list(itertools.combinations(sorted(sessions), N_AI_SESSIONS))


# ----------------------------------------------------------------------------- weights
def session_weights(sess, y):
    """Design section 6: 1 / (2 x sessions in the class x windows in the session).
    T1: multiplied by the number of rows, so the weights average 1. The shares are
    unchanged; the scale is the one the library defaults assume."""
    sess = np.asarray(sess)
    y = np.asarray(y)
    w = np.zeros(len(y), dtype=float)
    for c in (0, 1):
        in_class = sorted(set(sess[y == c]))
        if not in_class:
            raise SystemExit("STOP: a training set holds one class only")
        for s in in_class:
            m = sess == s
            w[m] = 1.0 / (2.0 * len(in_class) * m.sum())
    return w * len(y)


# ----------------------------------------------------------------------------- models
_NATIVE = None


def nan_groups():
    """Which models take undefined values as they are (design section 6). A model whose
    installed version refuses them is treated like logistic regression's group."""
    global _NATIVE
    if _NATIVE is None:
        Xp = np.array([[0.0, np.nan], [1.0, 1.0], [np.nan, 0.0], [1.0, 0.0]] * 5)
        yp = np.array([0, 1, 0, 1] * 5)
        _NATIVE = {}
        for name in ("rf", "hgb", "xgb"):
            try:
                make_model(name).fit(Xp, yp)
                _NATIVE[name] = True
            except Exception:
                _NATIVE[name] = False
    return _NATIVE


def prep_group(name):
    if name == "lr":
        return "impute_scale"
    if name == "gb":
        return "impute"
    return "native" if nan_groups()[name] else "impute"


def make_model(name):
    """Library defaults (P5) with the three departures of F7: seed 42, up to 1,000
    iterations for logistic regression, one thread for XGBoost."""
    if name == "lr":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(max_iter=1000, random_state=SEED)
    if name == "rf":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(random_state=SEED)
    if name == "gb":
        from sklearn.ensemble import GradientBoostingClassifier
        return GradientBoostingClassifier(random_state=SEED)
    if name == "hgb":
        from sklearn.ensemble import HistGradientBoostingClassifier
        return HistGradientBoostingClassifier(random_state=SEED)
    if name == "xgb":
        from xgboost import XGBClassifier
        return XGBClassifier(random_state=SEED, n_jobs=1)
    raise SystemExit("unknown model " + name)


class Prep:
    """Fitted on training rows only. native: nothing. impute: the training median of the
    defined values, and one extra column, 'the window has commands'. impute_scale: the
    same, then log(1 + x) for counts, sizes and times, then every column standardized."""

    def __init__(self, group, cols, info):
        self.group = group
        self.i_cmd = cols.index("cmd_count")
        self.log = np.array([info[c]["kind"] in LOG_KINDS for c in cols] + [False])

    def _fill(self, X):
        Z = np.where(np.isnan(X), self.med, X)
        has_cmd = (X[:, self.i_cmd] > 0).astype(float)
        return np.column_stack([Z, has_cmd])

    def _log(self, Z):
        Z = Z.copy()
        Z[:, self.log] = np.log1p(Z[:, self.log])
        return Z

    def fit(self, X):
        if self.group == "native":
            return self
        med = np.zeros(X.shape[1])
        for j in range(X.shape[1]):
            v = X[:, j][~np.isnan(X[:, j])]
            med[j] = float(np.median(v)) if len(v) else 0.0      # T5
        self.med = med
        if self.group == "impute_scale":
            Z = self._log(self._fill(X))
            self.mu = Z.mean(axis=0)                                # T6: not weighted
            sd = Z.std(axis=0)
            sd[sd == 0] = 1.0
            self.sd = sd
        return self

    def transform(self, X):
        if self.group == "native":
            return X
        Z = self._fill(X)
        if self.group == "impute_scale":
            Z = (self._log(Z) - self.mu) / self.sd
        return Z


def fit_model(name, cols, info, X, y, w):
    prep = Prep(prep_group(name), cols, info).fit(X)
    model = make_model(name)
    model.fit(prep.transform(X), y, sample_weight=w)
    return prep, model


def raw_score(fitted, X):
    """T2: what scikit-learn's own calibration reads: the decision value where the model
    has one (LR, GB, HGB), its predicted probability of AI otherwise (RF, XGBoost)."""
    prep, model = fitted
    Z = prep.transform(X)
    if hasattr(model, "decision_function"):
        return np.asarray(model.decision_function(Z), dtype=float)
    return np.asarray(model.predict_proba(Z)[:, 1], dtype=float)


def platt_fit(scores, y, w):
    """T2: Platt scaling as scikit-learn fits it (Platt's targets), with the weights of
    section 6."""
    from sklearn.calibration import _SigmoidCalibration
    return _SigmoidCalibration().fit(np.asarray(scores, dtype=float), np.asarray(y), sample_weight=w)


def confusion(y, called):
    y = np.asarray(y)
    c = np.asarray(called).astype(int)
    return (int(((y == 1) & (c == 1)).sum()), int(((y == 0) & (c == 1)).sum()),
            int(((y == 1) & (c == 0)).sum()), int(((y == 0) & (c == 0)).sum()))


def f1_parts(tp, fp, fn, tn):
    div = lambda a, b: (a / b) if b else 0.0
    f_ai = div(2 * tp, 2 * tp + fp + fn)
    f_h = div(2 * tn, 2 * tn + fn + fp)
    r_ai = div(tp, tp + fn)
    r_h = div(tn, tn + fp)
    return dict(macro_f1=(f_ai + f_h) / 2, f1_ai=f_ai, precision_ai=div(tp, tp + fp), recall_ai=r_ai,
                f1_human=f_h, precision_human=div(tn, tn + fn), recall_human=r_h,
                balanced_accuracy=(r_ai + r_h) / 2)


def best_threshold(p, y):
    """The cut on calibrated P(AI) with the highest macro-F1 (not weighted). T3: the
    candidate cuts are the midpoints between neighbouring distinct values; a window is
    called AI at or above the cut; among equal bests the cut nearest 0.5, then the lower."""
    p = np.asarray(p, dtype=float)
    y = np.asarray(y).astype(int)
    distinct = np.unique(p)
    if len(distinct) < 2:
        return 0.5
    cands = (distinct[:-1] + distinct[1:]) / 2.0
    order = np.argsort(p, kind="mergesort")
    ps, ys = p[order], y[order]
    k = np.searchsorted(ps, cands, side="left")            # windows below the cut
    pos_below = np.concatenate([[0], np.cumsum(ys)])[k]
    n, n_pos = len(y), int(y.sum())
    tp = n_pos - pos_below
    fn = pos_below
    fp = (n - k) - tp
    tn = k - pos_below
    with np.errstate(divide="ignore", invalid="ignore"):
        f_ai = np.where(2 * tp + fp + fn > 0, 2 * tp / (2 * tp + fp + fn), 0.0)
        f_h = np.where(2 * tn + fn + fp > 0, 2 * tn / (2 * tn + fn + fp), 0.0)
    macro = (f_ai + f_h) / 2.0
    best = np.where(macro >= macro.max() - 1e-12)[0]
    pick = sorted(best, key=lambda i: (abs(cands[i] - 0.5), cands[i]))[0]
    return float(cands[pick])


def _fold_digest(a, b, thr, pc):
    h = hashlib.sha256()
    h.update(("%.10f|%.10f|%.10f|" % (a, b, thr)).encode())
    h.update(np.round(np.asarray(pc, dtype=float), 10).tobytes())
    return h.hexdigest()


# ----------------------------------------------------------------------------- section 7.1
def run_loso(table, rows, cols, class_of, model, scored):
    """Leave one session out (design section 7.1).

    For each held-out session: every training session is left out once and predicted by
    a model fitted on the other seven; Platt scaling and the threshold are fitted on
    those predictions; a final model is fitted on all eight. In scored mode the final
    model then scores the held-out session once.

    T10: the model that leaves out sessions s and t serves both the fold that holds out
    s (as the calibration fold of t) and the fold that holds out t (as the calibration
    fold of s). It is the same fit either way, so it is made once.

    A fold's fitting reads the classes of its training sessions only.
    """
    info = table.info
    ci = [table.columns.index(c) for c in cols]
    X = table.X[np.ix_(rows, ci)]
    sess = table.session[rows]
    sessions = [s for s in table.sessions if (sess == s).any()]
    if len(sessions) != 9:
        raise SystemExit("STOP: a session has no row in this trial")
    idx = {s: np.where(sess == s)[0] for s in sessions}

    def labels(ix):
        return np.array([class_of[s] for s in sess[ix]], dtype=int)

    n_fits = 0
    pair = {}
    for s, t in itertools.combinations(sessions, 2):
        tr = np.where((sess != s) & (sess != t))[0]
        ytr = labels(tr)
        fitted = fit_model(model, cols, info, X[tr], ytr, session_weights(sess[tr], ytr))
        n_fits += 1
        pair[(s, t)] = {s: raw_score(fitted, X[idx[s]]), t: raw_score(fitted, X[idx[t]])}

    folds, preds, digests = [], [], []
    for s in sessions:
        others = [t for t in sessions if t != s]
        tr = np.concatenate([idx[t] for t in others])
        oof = np.concatenate([pair[tuple(sorted((s, t)))][t] for t in others])
        ytr = labels(tr)
        w = session_weights(sess[tr], ytr)
        cal = platt_fit(oof, ytr, w)
        pc = cal.predict(oof)
        thr = best_threshold(pc, ytr)
        final = fit_model(model, cols, info, X[tr], ytr, w)
        n_fits += 1
        digest = _fold_digest(cal.a_, cal.b_, thr, pc)
        digests.append(digest)
        fold = dict(held_out=s, n_train_rows=int(len(tr)), n_train_sessions=len(others),
                    n_calibration_predictions=int(len(oof)), fit_digest=digest,
                    train_matrix_sha256=sha256_bytes(np.ascontiguousarray(X[tr]).tobytes()))
        if scored:
            p = cal.predict(raw_score(final, X[idx[s]]))
            fold.update(platt_a=float(cal.a_), platt_b=float(cal.b_), threshold=thr)
            for j, i in enumerate(idx[s]):
                preds.append(dict(window_id=table.window_id[rows[i]], session=s,
                                  y=int(class_of[s]), p_ai=float(p[j]), called_ai=int(p[j] >= thr)))
        folds.append(fold)
    out = dict(n_rows=int(len(rows)), n_columns=len(cols), n_fits=n_fits, folds=folds,
               fit_hash=sha256_bytes("".join(digests).encode()),
               score_input={"lr": "decision value", "gb": "decision value", "hgb": "decision value",
                            "rf": "probability", "xgb": "probability"}[model],
               prep_group=prep_group(model))
    if scored:
        out["predictions"] = preds
    return out


# ----------------------------------------------------------------------------- section 7.6
def run_inside(table, cols, model, split_of, class_trainval, class_test, scored):
    """Inside sessions (design section 7.6): fitted on the rows marked train, calibrated
    and given the threshold on the rows marked val, the rows marked test scored once.
    Training and validation rows within the look-back after a test row of the same login
    are not used (T7: counted in window indexes of the login)."""
    lb = LOOKBACK_WINDOWS[table.window]
    info = table.info
    ci = [table.columns.index(c) for c in cols]
    split = np.array([split_of[w] for w in table.window_id])
    test_ix = {}
    for i in np.where(split == "test")[0]:
        test_ix.setdefault(table.login[i], set()).add(int(table.w_index[i]))
    embargo = np.zeros(len(split), dtype=bool)
    for i in np.where((split == "train") | (split == "val"))[0]:
        t = test_ix.get(table.login[i], ())
        if any((int(table.w_index[i]) - d) in t for d in range(1, lb + 1)):
            embargo[i] = True
    tr = np.where((split == "train") & ~embargo)[0]
    va = np.where((split == "val") & ~embargo)[0]
    te = np.where(split == "test")[0]
    X = table.X[:, ci]
    ytr = np.array([class_trainval[table.window_id[i]] for i in tr], dtype=int)
    yva = np.array([class_trainval[table.window_id[i]] for i in va], dtype=int)
    fitted = fit_model(model, cols, info, X[tr], ytr, session_weights(table.session[tr], ytr))
    sv = raw_score(fitted, X[va])
    cal = platt_fit(sv, yva, session_weights(table.session[va], yva))
    pc = cal.predict(sv)
    thr = best_threshold(pc, yva)
    digest = _fold_digest(cal.a_, cal.b_, thr, pc)
    out = dict(n_train_rows=int(len(tr)), n_val_rows=int(len(va)), n_test_rows=int(len(te)),
               n_embargoed_rows=int(embargo.sum()), n_columns=len(cols), n_fits=1,
               fit_hash=digest, prep_group=prep_group(model),
               train_matrix_sha256=sha256_bytes(np.ascontiguousarray(X[tr]).tobytes()))
    if scored:
        p = cal.predict(raw_score(fitted, X[te]))
        out.update(platt_a=float(cal.a_), platt_b=float(cal.b_), threshold=thr)
        out["predictions"] = [dict(window_id=table.window_id[i], session=str(table.session[i]),
                                   y=int(class_test[table.window_id[i]]), p_ai=float(p[j]),
                                   called_ai=int(p[j] >= thr)) for j, i in enumerate(te)]
    return out


def class_map_from_label_file(inp, rel):
    return {r["window_id"]: (1 if r["class"] == "ai" else 0) for r in inp.rows(rel, ["window_id", "class"])}


def library_versions():
    import sklearn
    import scipy
    import xgboost
    return dict(python=sys.version.split()[0], numpy=np.__version__, scikit_learn=sklearn.__version__,
                scipy=scipy.__version__, xgboost=xgboost.__version__)


def model_settings():
    out = {}
    for name in MODELS:
        params = make_model(name).get_params()
        out[name] = {k: (v if isinstance(v, (int, float, str, bool)) or v is None else repr(v))
                     for k, v in sorted(params.items())}
    return out
