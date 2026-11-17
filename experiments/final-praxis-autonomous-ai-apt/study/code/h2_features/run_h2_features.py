"""Study 3, H2, the "why": which features carry the separation in each ATT&CK stage group.

    python3 -I -B code/h2_features/run_h2_features.py

Descriptive and post hoc (2026-11-14). The rules are in
results_h2_features/H2_FEATURES_RULE_BEFORE_RUN.md and were written before this ran.

Layer 1  single-feature AUC within each stage group: read from EDA Pass 2's table.
Layer 2  feature tiers by stage group: from the saved held-out predictions of the
         trials main, no_command_content and no_context. Nothing is fitted.
Layer 3  what XGBoost relies on in each stage group: the nine models of the main trial
         are fitted again by the frozen fit_model (same rows, weights, seed), must
         reproduce the saved held-out predictions, and each held-out window gets its
         SHAP values from the model that never saw its session.

Nothing in results/, results_h2_stage/, data/, reports/ or the frozen code is written.
Outputs hold column names and numbers only.
"""
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(CODE, "trials"))            # the frozen trial code, read only
import trial_common as T
import summarize as S                                        # frozen: session bootstrap helpers

np = T.np
VERSION = "study3-h2-features-1.0"
OUT = os.path.join(T.ROOT, "results_h2_features")
TABLES = os.path.join(OUT, "tables")
RULE = os.path.join(OUT, "H2_FEATURES_RULE_BEFORE_RUN.md")
RULE_GROUPS = ["1-4", "5", "7"]
ALL_GROUPS = T.STAGE_GROUPS + ["all"]
ALL_KINDS = ("trial_code", "feature_table", "design", "plumbing", "feature_code", "eda_code",
             "feature_report", "eda_output", "plumbing_parts")
MODEL = "xgb"
L2_TRIALS = ["main", "no_command_content", "no_context"]
L2_DIFFS = [("command_content_adds", "no_command_content"), ("context_adds", "no_context")]
TOP, TOP_WIDE, MIN_N = 5, 10, 10
STAGE_LABEL = {"1-4": "Discovery (stages 1-4)", "5": "Execution (stage 5)",
               "6": "Account manipulation (stage 6), indicative",
               "7": "Lateral movement and collection (stage 7)", "all": "All windows"}
TIER_LABEL = {"behavior": "Behavior", "command_content": "Command content", "context": "Context"}
L1_TABLE = "reports/eda/tables/T7_same_stage_auc_all_features_w30.csv"
L1_PROFILE = "reports/eda/tables/T4_feature_profile_w30.csv"


def table(name, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else (repr(round(float(v), 6)) if isinstance(v, (float, np.floating)) else v)
                    for v in r])
    T.write_once(os.path.join(TABLES, name), buf.getvalue(), overwrite=True)


def f3(x):
    return "n/a" if x is None else "%.3f" % x


def pct(x):
    return "n/a" if x is None else "%.1f%%" % (100 * x)


def freeze_1_check():
    fz = T.read_json(os.path.join(T.REPORTS, "FREEZE_1.json"))["files"]
    ok, bad, not_opened = 0, [], 0
    for rel, meta in sorted(fz.items()):
        if (rel.startswith("set_aside/") or "_private" in rel or "labels_test_" in rel
                or "AHIR Participant Evidence" in rel):
            not_opened += 1
            continue
        p = os.path.join(T.ROOT, *rel.split("/"))
        if os.path.exists(p) and T.sha256_file(p) == meta["sha256"]:
            ok += 1
        else:
            bad.append(rel)
    return dict(listed=len(fz), match=ok, changed=bad, not_opened=not_opened)


def pass2_rows(rel):
    """A Pass 2 table, checked against the hash Pass 2 recorded for it."""
    want = T.read_json(os.path.join(T.REPORTS, "eda", "pass2_checks.json"))["outputs"][rel.split("reports/eda/")[1]]
    p = os.path.join(T.ROOT, *rel.split("/"))
    if T.sha256_file(p) != want:
        raise SystemExit("STOP: changed since EDA Pass 2: " + rel)
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f)), want


def leak_audit(labels, skip):
    sys.path.insert(0, T.CODE)
    import s3_clean as K
    hits, label_count, searched = [], {}, 0
    for top in (OUT, HERE):
        for dirpath, dirs, names in os.walk(top):
            dirs.sort()
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for n in sorted(names):
                if not n.endswith((".json", ".jsonl", ".csv", ".md", ".py", ".svg")) or n in skip:
                    continue
                rel = os.path.relpath(os.path.join(dirpath, n), T.ROOT).replace(os.sep, "/")
                data = open(os.path.join(dirpath, n), "rb").read()
                searched += 1
                for name, rx in K.LEAK_PATTERNS:
                    for m in rx.finditer(data):
                        text = m.group(0).decode("utf-8", "replace")
                        if name == "participant_code" and text in labels:
                            label_count[text] = label_count.get(text, 0) + 1
                        else:
                            hits.append(dict(pattern=name, file=rel, sample=text[:60]))
    return dict(files_searched=searched, total_hits=len(hits), hits=hits[:50],
                session_labels_found=dict(sorted(label_count.items())),
                result="PASS" if not hits else "FAIL")


def ranks_desc(v):
    """Rank 1 for the largest value; ties keep column order."""
    order = sorted(range(len(v)), key=lambda j: (-v[j], j))
    r = [0] * len(v)
    for k, j in enumerate(order):
        r[j] = k + 1
    return r


def main():
    if not os.path.exists(RULE):
        raise SystemExit("REFUSED: the rule file is written before the run")
    rule_sha = T.sha256_file(RULE)
    freeze_2 = T.check_freeze_2(kinds=ALL_KINDS)
    fz1_before = freeze_1_check()
    log = T.read_json(os.path.join(T.PLUMB, "PLUMBING_LOG.json"))
    if T.library_versions() != log["libraries"]:
        raise SystemExit("STOP: the libraries are not those of the plumbing run")
    inp = T.Inputs("scored")
    tab = T.load_table(inp, "w30")
    stage_of = {r["window_id"]: r["stage_group"] for r in inp.rows(
        "data/description/window_description_w30.csv", ["window_id", "stage_group", "keep"]) if r["keep"] == "1"}
    cols = T.config_columns(tab, "main")
    rows = T.subset_rows(tab, None)
    ci = [tab.columns.index(c) for c in cols]
    X = tab.X[np.ix_(rows, ci)]
    sess = tab.session[rows]
    sessions = list(tab.sessions)
    humans = [s for s in sessions if tab.class_of[s] == 0]
    ais = [s for s in sessions if tab.class_of[s] == 1]
    idx = {s: np.where(sess == s)[0] for s in sessions}
    wid = [tab.window_id[i] for i in rows]
    y = np.array([tab.class_of[s] for s in sess], dtype=int)
    grp = np.array([stage_of[w] for w in wid])
    tier = {}
    for c in cols:
        tier[c] = tab.info[c]["tier"]
    defin = {c: tab.info[c]["definition"] for c in cols}
    checks = dict(version=VERSION, rule_file_sha256=rule_sha, freeze_2_sha256=freeze_2,
                  libraries=T.library_versions(), d_freeze_1_before=fz1_before,
                  model=MODEL, configuration="main", window="w30", n_columns=len(cols), n_windows=int(len(y)))

    # ------------------------------------------------------------------ Layer 3: the nine models, again
    import xgboost as xgb
    from scipy.stats import spearmanr
    saved = T.read_json(os.path.join(T.RESULTS, "trials", "main__%s.json" % MODEL))
    if saved["columns"] != cols:
        raise SystemExit("STOP: the columns are not those of the saved trial")
    fold = {f["held_out"]: f for f in saved["folds"]}
    saved_p = {p["window_id"]: p for p in saved["predictions"]}
    shap = np.zeros((len(y), len(cols)))
    base = np.zeros(len(y))
    margin = np.zeros(len(y))
    worst_p, n_call_same, worst_add, worst_prob, n_matrix = 0.0, 0, 0.0, 0.0, 0
    for s in sessions:
        others = [t for t in sessions if t != s]
        tr = np.concatenate([idx[t] for t in others])
        ytr = np.array([tab.class_of[t] for t in sess[tr]], dtype=int)
        w = T.session_weights(sess[tr], ytr)
        n_matrix += int(T.sha256_bytes(np.ascontiguousarray(X[tr]).tobytes()) == fold[s]["train_matrix_sha256"])
        fitted = T.fit_model(MODEL, cols, tab.info, X[tr], ytr, w)          # the frozen fit
        raw = T.raw_score(fitted, X[idx[s]])
        p = 1.0 / (1.0 + np.exp(fold[s]["platt_a"] * raw + fold[s]["platt_b"]))   # the saved calibration
        for j, i in enumerate(idx[s]):
            sp = saved_p[wid[i]]
            worst_p = max(worst_p, abs(p[j] - sp["p_ai"]))
            n_call_same += int(int(p[j] >= fold[s]["threshold"]) == sp["called_ai"])
        prep, model = fitted
        dm = xgb.DMatrix(prep.transform(X[idx[s]]), missing=np.nan)
        con = np.asarray(model.get_booster().predict(dm, pred_contribs=True), dtype=float)
        mar = np.asarray(model.get_booster().predict(dm, output_margin=True), dtype=float)
        worst_add = max(worst_add, float(np.abs(con.sum(axis=1) - mar).max()))
        worst_prob = max(worst_prob, float(np.abs(1.0 / (1.0 + np.exp(-mar)) - raw).max()))
        shap[idx[s]] = con[:, :len(cols)]
        base[idx[s]] = con[:, len(cols)]
        margin[idx[s]] = mar
    checks["L3_models_reproduce_saved_predictions"] = dict(
        windows=int(len(y)), largest_difference_in_p_ai=worst_p, same_call=n_call_same,
        training_matrices_equal=n_matrix,
        result="PASS" if (worst_p < 1e-9 and n_call_same == len(y) and n_matrix == 9) else "FAIL")
    checks["L3_shap_adds_up_to_the_margin"] = dict(
        largest_difference=worst_add, largest_difference_margin_to_probability=worst_prob,
        result="PASS" if (worst_add < 1e-3 and worst_prob < 1e-5) else "FAIL")
    if checks["L3_models_reproduce_saved_predictions"]["result"] != "PASS" or \
            checks["L3_shap_adds_up_to_the_margin"]["result"] != "PASS":
        print(checks["L3_models_reproduce_saved_predictions"], checks["L3_shap_adds_up_to_the_margin"])
        raise SystemExit("VOID: rule item 2 or 3 of Layer 3 is not met")
    prows = []
    for i in range(len(y)):
        prows.append([wid[i], sess[i], int(y[i]), grp[i], float(base[i]), float(margin[i])] + [float(v) for v in shap[i]])
    table("L3_shap_values_main_xgb.csv", ["window_id", "session", "class_ai", "stage_group", "base_value", "margin"] + cols, prows)

    def importance(mask):
        h, a = mask & (y == 0), mask & (y == 1)
        if h.sum() == 0 or a.sum() == 0:
            return None
        ab = np.abs(shap)
        imp = 0.5 * (ab[h].mean(axis=0) + ab[a].mean(axis=0))                # rule item 4
        return dict(imp=imp, share=imp / imp.sum(), plain=ab[mask].mean(axis=0),
                    sep=shap[a].mean(axis=0) - shap[h].mean(axis=0), n_h=int(h.sum()), n_a=int(a.sum()))

    def direction(mask, j):
        m = mask & ~np.isnan(X[:, j])
        if m.sum() < MIN_N or np.unique(X[m, j]).size < 2 or np.unique(shap[m, j]).size < 2:
            return None, None, int(m.sum())
        rho = float(spearmanr(X[m, j], shap[m, j]).statistic)
        return ("ai" if rho > 0 else "human"), rho, int(m.sum())

    L3, drops, drow = {}, {}, []
    for g in ALL_GROUPS:
        mask = np.ones(len(y), dtype=bool) if g == "all" else (grp == g)
        full = importance(mask)
        rk = ranks_desc(list(full["share"]))
        dr = []
        for s in sessions:
            d = importance(mask & (sess != s))
            if d is None:
                dr.append(dict(session=s, ranks=None, indicative=True, n_h=0, n_a=0))
                continue
            dr.append(dict(session=s, ranks=ranks_desc(list(d["share"])), share=d["share"],
                           indicative=min(d["n_h"], d["n_a"]) < MIN_N, n_h=d["n_h"], n_a=d["n_a"]))
        drops[g] = dr
        for j, c in enumerate(cols):
            dname, rho, n_def = direction(mask, j)
            rr = [(d["ranks"][j], d["session"]) for d in dr if d["ranks"] is not None]
            ni = [(d["ranks"][j], d["session"]) for d in dr if d["ranks"] is not None and not d["indicative"]]
            L3[(g, c)] = dict(share=float(full["share"][j]), rank=rk[j], imp=float(full["imp"][j]),
                              plain=float(full["plain"][j]), sep=float(full["sep"][j]), direction=dname, rho=rho,
                              n_defined=n_def, n_h=full["n_h"], n_a=full["n_a"],
                              rank_lo=min(rr)[0], rank_lo_without=min(rr)[1], rank_hi=max(rr)[0],
                              rank_hi_without=max(rr)[1],
                              rank_lo_ni=min(ni)[0] if ni else None, rank_hi_ni=max(ni)[0] if ni else None)
        for d in dr:
            for j, c in enumerate(cols):
                drow.append([g, d["session"], d["n_h"], d["n_a"], int(d["indicative"]), c,
                             None if d["ranks"] is None else float(d["share"][j]),
                             None if d["ranks"] is None else d["ranks"][j]])
    holds, dependent = {}, {}
    for c in cols:
        dirs = [L3[(g, c)]["direction"] for g in RULE_GROUPS]
        holds[c] = all(L3[(g, c)]["rank"] <= TOP_WIDE for g in RULE_GROUPS) and dirs[0] is not None and len(set(dirs)) == 1
        dependent[c] = any(L3[(g, c)]["rank"] <= TOP for g in RULE_GROUPS) and not holds[c]
    table("L3_shap_by_stage_group.csv", [
        "stage_group", "indicative", "n_human", "n_ai", "column", "tier", "goes_with", "share", "rank",
        "rank_lowest_over_session_drops", "lowest_without", "rank_highest_over_session_drops", "highest_without",
        "rank_lowest_drops_not_indicative", "rank_highest_drops_not_indicative", "direction_higher_value_pushes_toward",
        "spearman_rho_value_to_shap", "windows_with_the_column_defined", "mean_abs_shap_classes_equal",
        "mean_abs_shap_all_windows", "mean_shap_ai_minus_human", "holds_in_every_stage", "stage_dependent"],
          [[g, int(min(L3[(g, c)]["n_h"], L3[(g, c)]["n_a"]) < MIN_N), L3[(g, c)]["n_h"], L3[(g, c)]["n_a"], c, tier[c],
            tab.info[c].get("goes_with") or "", L3[(g, c)]["share"], L3[(g, c)]["rank"], L3[(g, c)]["rank_lo"],
            L3[(g, c)]["rank_lo_without"], L3[(g, c)]["rank_hi"], L3[(g, c)]["rank_hi_without"],
            L3[(g, c)]["rank_lo_ni"], L3[(g, c)]["rank_hi_ni"], L3[(g, c)]["direction"] or "", L3[(g, c)]["rho"],
            L3[(g, c)]["n_defined"], L3[(g, c)]["imp"], L3[(g, c)]["plain"], L3[(g, c)]["sep"],
            int(holds[c]), int(dependent[c])] for g in ALL_GROUPS for c in cols])
    table("L3_session_drops.csv", ["stage_group", "session_left_out", "n_human", "n_ai", "indicative", "column",
                                   "share", "rank"], drow)
    tiers = ["behavior", "command_content", "context"]
    L3_tier = {(g, t): float(sum(L3[(g, c)]["share"] for c in cols if tier[c] == t)) for g in ALL_GROUPS for t in tiers}
    n_tier = {t: sum(1 for c in cols if tier[c] == t) for t in tiers}

    # ------------------------------------------------------------------ Layer 1: Pass 2's table, assembled
    l1rows, l1_sha = pass2_rows(L1_TABLE)
    prof, prof_sha = pass2_rows(L1_PROFILE)
    all_auc = {r["feature"]: (float(r["auc"]) if r["auc"] else None, r["higher_in"]) for r in prof}
    L1 = {}
    for r in l1rows:
        if r["feature"] in tier and r["stage_group"] in T.STAGE_GROUPS:
            L1[(r["stage_group"], r["feature"])] = dict(
                auc=float(r["auc_in_all_rows_direction"]) if r["auc_in_all_rows_direction"] else None,
                n_h=int(r["n_human"]), n_a=int(r["n_ai"]), indicative=r["indicative"] == "yes")
    for g in RULE_GROUPS:
        v = [L1[(g, c)]["auc"] if L1[(g, c)]["auc"] is not None else -1.0 for c in cols]
        for c, k in zip(cols, ranks_desc(v)):
            L1[(g, c)]["rank"] = k
    L1_tier = {(g, t): float(np.mean([L1[(g, c)]["auc"] for c in cols if tier[c] == t and L1[(g, c)]["auc"] is not None]))
               for g in RULE_GROUPS for t in tiers}
    table("L1_auc_by_stage_group.csv", ["stage_group", "column", "tier", "auc_in_all_rows_direction", "rank",
                                        "n_human_training_windows", "n_ai_training_windows", "indicative",
                                        "auc_all_training_windows", "higher_in_all_training_windows"],
          [[g, c, tier[c], L1[(g, c)]["auc"], L1[(g, c)].get("rank"), L1[(g, c)]["n_h"], L1[(g, c)]["n_a"],
            int(L1[(g, c)]["indicative"]), all_auc[c][0], all_auc[c][1]] for g in RULE_GROUPS for c in cols])

    # ------------------------------------------------------------------ Layer 2: saved predictions by stage group
    rng = np.random.default_rng(T.SEED)                      # reading T14: the frozen draws
    H = rng.integers(0, len(humans), size=(T.N_BOOT, len(humans)))
    A = rng.integers(0, len(ais), size=(T.N_BOOT, len(ais)))
    frozen_stage = {}
    with open(os.path.join(T.RESULTS, "tables", "T_by_stage_group.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            frozen_stage[(r["trial"], r["model"], r["stage_group"])] = None if r["macro_f1"] == "" else float(r["macro_f1"])
    f1, boot, same, n_cmp = {}, {}, 0, 0
    for name in L2_TRIALS:
        for m in T.MODELS:
            doc = T.read_json(os.path.join(T.RESULTS, "trials", "%s__%s.json" % (name, m)))
            for g in ALL_GROUPS:
                sub = [p for p in doc["predictions"] if g == "all" or stage_of[p["window_id"]] == g]
                tp, fp, fn, tn = T.confusion([p["y"] for p in sub], [p["called_ai"] for p in sub])
                f1[(name, m, g)] = T.f1_parts(tp, fp, fn, tn)["macro_f1"] if (tp + fn and tn + fp) else None
                boot[(name, m, g)] = S.boot_macro(S.session_counts(sub), humans, ais, H, A)
                if g != "all":
                    n_cmp += 1
                    fz = frozen_stage[(name, m, g)]
                    same += int((fz is None and f1[(name, m, g)] is None) or
                                (fz is not None and f1[(name, m, g)] is not None and abs(fz - f1[(name, m, g)]) < 1e-6))
    checks["L2_macro_f1_equals_frozen_stage_table"] = dict(cells=n_cmp, equal=same, result="PASS" if same == n_cmp else "FAIL")
    L2, l2rows = {}, []
    for label, minus in L2_DIFFS:
        for m in T.MODELS:
            for g in ALL_GROUPS:
                a, b = f1[("main", m, g)], f1[(minus, m, g)]
                d = boot[("main", m, g)] - boot[(minus, m, g)]
                lo, hi = S.interval(d)
                L2[(label, m, g)] = dict(main=a, without=b, diff=None if (a is None or b is None) else a - b, lo=lo, hi=hi)
                l2rows.append([label, m, g, a, b, L2[(label, m, g)]["diff"], lo, hi, int(lo > 0)])
    table("L2_tiers_by_stage_group.csv", ["difference", "model", "stage_group", "macro_f1_main", "macro_f1_without",
                                          "difference_in_macro_f1", "ci_low", "ci_high", "interval_above_zero"], l2rows)

    # ------------------------------------------------------------------ the assembled table
    # Added after the first run, to show what the rules already report: the Layer 3 net effect (rule item 11)
    # beside each rank, and one row for the 18 columns that the no-command-content trial removes, so that
    # Layer 2 and Layer 3 are read over the same columns. No rule and no ranking is changed by it.
    ctx_cc = [c for c in cols if tier[c] == "context" and (tab.info[c].get("goes_with") or "") == "command_content"]
    cc18 = [c for c in cols if tier[c] == "command_content" or c in ctx_cc]
    L3_cc18 = {g: float(sum(L3[(g, c)]["share"] for c in cc18)) for g in ALL_GROUPS}
    L1_cc18 = {g: float(np.mean([L1[(g, c)]["auc"] for c in cc18 if L1[(g, c)]["auc"] is not None])) for g in RULE_GROUPS}
    top3 = sorted(cols, key=lambda c: L3[("all", c)]["rank"])[:3]
    feats = [c for c in cols if any(L3[(g, c)]["rank"] <= TOP or L1[(g, c)]["rank"] <= TOP for g in RULE_GROUPS)]
    feats.sort(key=lambda c: (-L3[("all", c)]["share"], cols.index(c)))
    head = ["row_type", "name", "definition", "tier", "pattern"]
    for g in RULE_GROUPS:
        k = "s" + g.replace("-", "_")
        head += [k + "_L1_auc", k + "_L1_rank", k + "_L2_xgb_macro_f1_lost_when_removed", k + "_L2_xgb_ci_low",
                 k + "_L2_xgb_ci_high", k + "_L2_range_low_five_classifiers", k + "_L2_range_high_five_classifiers",
                 k + "_L2_classifiers_with_interval_above_zero", k + "_L3_share", k + "_L3_rank",
                 k + "_L3_rank_lowest_over_drops", k + "_L3_rank_highest_over_drops",
                 k + "_L3_higher_value_pushes_toward", k + "_L3_mean_shap_ai_minus_human"]

    def l2_cells(label, g):
        if label is None:
            return [None] * 6
        x = L2[(label, MODEL, g)]
        five = [L2[(label, m, g)] for m in T.MODELS]
        return [x["diff"], x["lo"], x["hi"], min(v["diff"] for v in five), max(v["diff"] for v in five),
                sum(1 for v in five if v["lo"] > 0)]

    tier_rows = [("tier", "%s (%d columns)" % (TIER_LABEL[t], n_tier[t]), t, {"context": "context_adds"}.get(t),
                  (lambda g, t=t: L1_tier[(g, t)]), (lambda g, t=t: L3_tier[(g, t)])) for t in tiers]
    tier_rows.append(("tier_added_after_the_run", "Command content with its 4 context columns (%d columns)" % len(cc18),
                      "command_content+context", "command_content_adds", (lambda g: L1_cc18[g]), (lambda g: L3_cc18[g])))
    arows = []
    for kind, name, t, label, l1f, l3f in tier_rows:
        r = [kind, name, "", t, ""]
        for g in RULE_GROUPS:
            r += [l1f(g), None] + l2_cells(label, g) + [l3f(g), None, None, None, "", None]
        arows.append(r)
    for c in feats:
        pat = "holds in every stage" if holds[c] else ("stage-dependent" if dependent[c] else "")
        r = ["feature", c, defin[c], tier[c], pat]
        for g in RULE_GROUPS:
            x = L3[(g, c)]
            r += [L1[(g, c)]["auc"], L1[(g, c)]["rank"]] + [None] * 6 + [x["share"], x["rank"], x["rank_lo"],
                                                                       x["rank_hi"], x["direction"] or "", x["sep"]]
        arows.append(r)
    table("T_h2_features_by_stage.csv", head, arows)

    # ------------------------------------------------------------------ the summary a person reads
    short = lambda g: STAGE_LABEL[g].split(" (")[0]
    L = []
    L.append("# Study 3, H2: which features carry the separation in each ATT&CK stage group\n")
    L.append("Written by `code/h2_features/run_h2_features.py`. Descriptive and post hoc; it gives no verdict. Rules: "
             "`H2_FEATURES_RULE_BEFORE_RUN.md` (SHA-256 `%s`). Freeze 2 SHA-256 `%s`.\n" % (rule_sha, freeze_2))
    L.append("- **L1** single-feature AUC within the stage group, training windows (EDA Pass 2); rank among the 40 "
             "columns of the main configuration.\n- **L2** held-out macro-F1 lost when the columns are removed: XGBoost "
             "with its 95% interval, the range over the five classifiers, and how many of the five have an interval "
             "above zero.\n- **L3** share of XGBoost's mean absolute SHAP value on held-out windows, classes counted "
             "equally; rank among the 40 columns, with the lowest and highest rank when any one session is left out; "
             "which class a higher value pushes toward; and the net effect, the mean SHAP value over AI windows minus "
             "the mean over human windows (log-odds; positive moves AI windows toward AI).\n")
    L.append("## Tiers\n")
    L.append("| Columns | " + " | ".join("%s: L1 mean AUC | L2 macro-F1 lost when removed | L3 share" % short(g) for g in RULE_GROUPS) + " |")
    L.append("|---|" + "---|---|---|" * len(RULE_GROUPS))
    for kind, name, t, label, l1f, l3f in tier_rows:
        cells = []
        for g in RULE_GROUPS:
            if label is None:
                l2 = "not removed in any trial"
            else:
                v = l2_cells(label, g)
                l2 = "%+.3f (%+.3f to %+.3f); five: %+.3f to %+.3f; above zero in %d of 5" % tuple(v)
            cells += [f3(l1f(g)), l2, pct(l3f(g))]
        L.append("| **%s**%s | " % (name, " (added after the run)" if kind != "tier" else "") + " | ".join(cells) + " |")
    L.append("\nThe three columns with the largest share over all windows (%s) hold %s of the total in discovery, %s in "
             "execution and %s in lateral movement and collection.\n" % (
                 ", ".join("`%s`" % c for c in top3), *[pct(sum(L3[(g, c)]["share"] for c in top3)) for g in RULE_GROUPS]))
    L.append("## Features\n")
    L.append("| Column | Tier | " + " | ".join("%s: L1 AUC (rank) | L3 share (rank; range) | L3 pushes, net" % short(g) for g in RULE_GROUPS) + " | Pattern |")
    L.append("|---|---|" + "---|---|---|" * len(RULE_GROUPS) + "---|")
    for c in feats:
        cells = []
        for g in RULE_GROUPS:
            x = L3[(g, c)]
            arrow = {"ai": "higher → AI", "human": "higher → human", None: "no direction"}[x["direction"]]
            cells += ["%s (#%d)" % (f3(L1[(g, c)]["auc"]), L1[(g, c)]["rank"]),
                      "%s (#%d; %d–%d)" % (pct(x["share"]), x["rank"], x["rank_lo"], x["rank_hi"]),
                      "%s, %+.2f" % (arrow, x["sep"])]
        pat = "Holds in every stage" if holds[c] else ("Stage-dependent" if dependent[c] else "")
        L.append("| `%s`: %s | %s | " % (c, defin[c], TIER_LABEL[tier[c]]) + " | ".join(cells) + " | %s |" % pat)
    L.append("")
    L.append("Windows behind L3 (human, AI): " + "; ".join(
        "%s %d, %d" % (short(g), L3[(g, cols[0])]["n_h"], L3[(g, cols[0])]["n_a"]) for g in RULE_GROUPS) + ".")
    L.append("Windows behind L1 (human, AI, training windows): " + "; ".join(
        "%s %d, %d" % (short(g), L1[(g, cols[0])]["n_h"], L1[(g, cols[0])]["n_a"]) for g in RULE_GROUPS) + ".\n")
    for g in RULE_GROUPS:
        top = sorted(cols, key=lambda c: L3[(g, c)]["rank"])[:TOP]
        L.append("- **%s, L3 top five:** " % STAGE_LABEL[g] + ", ".join("`%s` %s" % (c, pct(L3[(g, c)]["share"])) for c in top))
    for g in RULE_GROUPS:
        top = sorted(cols, key=lambda c: L1[(g, c)]["rank"])[:TOP]
        L.append("- **%s, L1 top five:** " % STAGE_LABEL[g] + ", ".join("`%s` %s" % (c, f3(L1[(g, c)]["auc"])) for c in top))
    L.append("- **Holds in every stage** (top ten in all three, same direction): " + (", ".join("`%s`" % c for c in cols if holds[c]) or "none"))
    L.append("- **Of those, a net effect toward AI in all three stage groups:** " + (", ".join(
        "`%s`" % c for c in cols if holds[c] and all(L3[(g, c)]["sep"] > 0 for g in RULE_GROUPS)) or "none"))
    L.append("- **Stage-dependent** (top five somewhere, not in \"holds in every stage\"): " + (", ".join("`%s`" % c for c in cols if dependent[c]) or "none"))
    neg = ["`%s` in %s (%+.2f)" % (c, short(g).lower(), L3[(g, c)]["sep"]) for g in RULE_GROUPS for c in cols
           if L3[(g, c)]["rank"] <= TOP_WIDE and L3[(g, c)]["sep"] < 0]
    L.append("- **Top-ten columns whose net effect is toward human** (they work against detection there): " + (", ".join(neg) or "none"))
    weak = ["`%s` in %s (%.2f)" % (c, short(g).lower(), L3[(g, c)]["rho"]) for g in RULE_GROUPS for c in feats
            if L3[(g, c)]["rho"] is not None and abs(L3[(g, c)]["rho"]) < 0.3 and L3[(g, c)]["rank"] <= TOP_WIDE]
    L.append("- **Directions that rest on a weak rank correlation** (|rho| under 0.3, top-ten columns): " + (", ".join(weak) or "none"))
    ind = sorted(set((g, d["session"]) for g in RULE_GROUPS for d in drops[g] if d["indicative"]))
    L.append("- Session drops that leave under 10 windows of a class (indicative): " + (", ".join("%s without %s" % (short(g), s) for g, s in ind) or "none") + "\n")
    T.write_once(os.path.join(OUT, "H2_FEATURES_SUMMARY.md"), "\n".join(L) + "\n", overwrite=True)

    checks["added_after_the_first_run"] = ("the assembled table and the summary also show the Layer 3 net effect (rule "
                                           "item 11), the number of classifiers whose Layer 2 interval is above zero, and "
                                           "one row for the 18 columns the no-command-content trial removes; no rule or "
                                           "ranking changed")
    checks["L3_share_command_content_with_its_context"] = {g: L3_cc18[g] for g in ALL_GROUPS}
    checks["L3_share_top_three_columns"] = {g: float(sum(L3[(g, c)]["share"] for c in top3)) for g in ALL_GROUPS}

    checks["L1_source"] = {L1_TABLE: l1_sha, L1_PROFILE: prof_sha}
    checks["rule_groups"] = RULE_GROUPS
    checks["holds_in_every_stage"] = [c for c in cols if holds[c]]
    checks["stage_dependent"] = [c for c in cols if dependent[c]]
    checks["top_five_L3"] = {g: sorted(cols, key=lambda c: L3[(g, c)]["rank"])[:TOP] for g in ALL_GROUPS}
    checks["top_five_L1"] = {g: sorted(cols, key=lambda c: L1[(g, c)]["rank"])[:TOP] for g in RULE_GROUPS}
    checks["indicative_session_drops"] = ["%s without %s" % (g, s) for g, s in ind]
    checks["d_freeze_1_after"] = freeze_1_check()
    checks["d_freeze_2_after"] = T.check_freeze_2(kinds=ALL_KINDS)
    checks["leak_audit"] = leak_audit(set(sessions), skip=("h2_features_checks.json",))
    checks["inputs_opened"] = inp.opened
    files = {}
    for n in sorted(os.listdir(TABLES)):
        files["results_h2_features/tables/" + n] = T.sha256_file(os.path.join(TABLES, n))
    figdir = os.path.join(OUT, "figures")
    if os.path.isdir(figdir):                                # written by fig_h2_features.py, after the tables
        for n in sorted(os.listdir(figdir)):
            files["results_h2_features/figures/" + n] = T.sha256_file(os.path.join(figdir, n))
    for n in ("H2_FEATURES_SUMMARY.md", "H2_FEATURES_RULE_BEFORE_RUN.md"):
        files["results_h2_features/" + n] = T.sha256_file(os.path.join(OUT, n))
    for n in sorted(os.listdir(HERE)):
        if n.endswith(".py"):
            files["code/h2_features/" + n] = T.sha256_file(os.path.join(HERE, n))
    checks["files"] = files
    T.write_once(os.path.join(OUT, "h2_features_checks.json"), T.dump_json(checks), overwrite=True)
    for k in ("L3_models_reproduce_saved_predictions", "L3_shap_adds_up_to_the_margin", "L2_macro_f1_equals_frozen_stage_table"):
        print(k, checks[k])
    print("freeze 1 changed:", checks["d_freeze_1_after"]["changed"], "| leak audit:", checks["leak_audit"]["result"],
          checks["leak_audit"]["total_hits"])
    print("COMPLETE: results_h2_features/")


if __name__ == "__main__":
    main()
