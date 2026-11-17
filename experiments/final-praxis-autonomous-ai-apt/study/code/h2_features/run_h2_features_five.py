"""Study 3, H2, the "why", Layer 3 for all five classifiers.

    S3_LIBS=<pinned libraries> S3_SHAP=<shap and what it needs> python3 -I -B code/h2_features/run_h2_features_five.py

Descriptive and post hoc (2026-11-14). The rules are those of
results_h2_features/H2_FEATURES_RULE_BEFORE_RUN.md, with the addendum
results_h2_features/five_classifiers/RULE_ADDENDUM_BEFORE_RUN.md, both written before
their runs.

For each classifier the nine models of the main trial are fitted again by the frozen
fit_model (same rows, weights, seed) and must reproduce the saved held-out predictions.
Each held-out window gets its SHAP values from the model that never saw its session:
XGBoost by its own TreeSHAP; random forest, gradient boosting and histogram gradient
boosting by shap's TreeExplainer (path-dependent); logistic regression in closed form.

Nothing in results/, results_h2_stage/, data/, reports/ or the frozen code is written,
and the files of results_h2_features/ written by run_h2_features.py are left as they
are. Outputs go to results_h2_features/five_classifiers/ and hold column names and
numbers only.
"""
import csv
import io
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_h2_features as F                                  # helpers; puts the frozen trial code on the path

T, S, np = F.T, F.S, F.np
_SHAP = os.environ.get("S3_SHAP")
if _SHAP and _SHAP not in sys.path:
    sys.path.append(_SHAP)                                   # after the pinned libraries, never before

VERSION = "study3-h2-features-five-1.0"
OUT = os.path.join(F.OUT, "five_classifiers")
TABLES = os.path.join(OUT, "tables")
RULE = os.path.join(OUT, "RULE_ADDENDUM_BEFORE_RUN.md")
RULE_GROUPS, ALL_GROUPS = F.RULE_GROUPS, F.ALL_GROUPS
TOP, TOP_WIDE, MIN_N = F.TOP, F.TOP_WIDE, F.MIN_N
SCALE = {"lr": "log-odds", "rf": "probability", "gb": "log-odds", "hgb": "log-odds", "xgb": "log-odds"}
METHOD = {"lr": "linear, inputs independent", "rf": "TreeSHAP path-dependent (shap)", "gb": "TreeSHAP path-dependent (shap)",
          "hgb": "TreeSHAP path-dependent (shap)", "xgb": "TreeSHAP (xgboost)"}
AGREED = 4                                                   # addendum: top five of at least four classifiers
short = lambda g: F.STAGE_LABEL[g].split(" (")[0]


def table(name, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else (repr(round(float(v), 6)) if isinstance(v, (float, np.floating)) else v)
                    for v in r])
    T.write_once(os.path.join(TABLES, name), buf.getvalue(), overwrite=True)


def explain(name, fitted, Xtr, Xs):
    """SHAP values of the held-out rows: (n, inputs), the base value, and the raw score they add up to."""
    prep, model = fitted
    Z = prep.transform(Xs)
    if name == "xgb":
        import xgboost as xgb
        dm = xgb.DMatrix(Z, missing=np.nan)
        con = np.asarray(model.get_booster().predict(dm, pred_contribs=True), dtype=float)
        return con[:, :-1], con[:, -1], np.asarray(model.get_booster().predict(dm, output_margin=True), dtype=float)
    if name == "lr":
        mu = prep.transform(Xtr).mean(axis=0)                # the fold's training rows, not weighted
        coef = np.asarray(model.coef_[0], dtype=float)
        phi = coef * (Z - mu)
        base = float(model.intercept_[0] + coef @ mu)
        return phi, np.full(len(Z), base), np.asarray(model.decision_function(Z), dtype=float)
    import shap
    ex = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent")
    sv = np.asarray(ex.shap_values(Z, check_additivity=False), dtype=float)
    ev = np.ravel(np.asarray(ex.expected_value, dtype=float))
    if name == "rf":
        if sv.ndim != 3 or sv.shape[2] != 2 or len(ev) != 2:
            raise SystemExit("STOP: unexpected SHAP shape for the random forest")
        return sv[:, :, 1], np.full(len(Z), ev[1]), np.asarray(model.predict_proba(Z)[:, 1], dtype=float)
    if sv.ndim != 2 or len(ev) != 1:
        raise SystemExit("STOP: unexpected SHAP shape for " + name)
    return sv, np.full(len(Z), ev[0]), np.asarray(model.decision_function(Z), dtype=float)


def main():
    if not os.path.exists(RULE):
        raise SystemExit("REFUSED: the addendum is written before the run")
    rule_sha, rule0_sha = T.sha256_file(RULE), T.sha256_file(F.RULE)
    freeze_2 = T.check_freeze_2(kinds=F.ALL_KINDS)
    fz1_before = F.freeze_1_check()
    log = T.read_json(os.path.join(T.PLUMB, "PLUMBING_LOG.json"))
    if T.library_versions() != log["libraries"]:
        raise SystemExit("STOP: the libraries are not those of the plumbing run")
    import shap
    from scipy.stats import spearmanr
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
    idx = {s: np.where(sess == s)[0] for s in sessions}
    wid = [tab.window_id[i] for i in rows]
    y = np.array([tab.class_of[s] for s in sess], dtype=int)
    grp = np.array([stage_of[w] for w in wid])
    tier = {c: tab.info[c]["tier"] for c in cols}
    goes = {c: tab.info[c].get("goes_with") or "" for c in cols}
    i_cmd = cols.index("cmd_count")
    cc18 = [c for c in cols if tier[c] == "command_content" or (tier[c] == "context" and goes[c] == "command_content")]
    tiers = ["behavior", "command_content", "context"]
    checks = dict(version=VERSION, addendum_sha256=rule_sha, rule_file_sha256=rule0_sha, freeze_2_sha256=freeze_2,
                  libraries=T.library_versions(), shap_library=shap.__version__, d_freeze_1_before=fz1_before,
                  configuration="main", window="w30", n_columns=len(cols), n_windows=int(len(y)),
                  scale=SCALE, method=METHOD, models={})

    SH, EXTRA, void = {}, {}, []
    for m in T.MODELS:
        saved = T.read_json(os.path.join(T.RESULTS, "trials", "main__%s.json" % m))
        if saved["columns"] != cols:
            raise SystemExit("STOP: the columns are not those of the saved trial")
        fold = {f["held_out"]: f for f in saved["folds"]}
        saved_p = {p["window_id"]: p for p in saved["predictions"]}
        sh = np.zeros((len(y), len(cols)))
        extra = np.zeros(len(y))
        base = np.zeros(len(y))
        score = np.zeros(len(y))
        worst_p, n_call, worst_add, n_matrix, n_inputs = 0.0, 0, 0.0, 0, None
        for s in sessions:
            others = [t for t in sessions if t != s]
            tr = np.concatenate([idx[t] for t in others])
            ytr = np.array([tab.class_of[t] for t in sess[tr]], dtype=int)
            w = T.session_weights(sess[tr], ytr)
            n_matrix += int(T.sha256_bytes(np.ascontiguousarray(X[tr]).tobytes()) == fold[s]["train_matrix_sha256"])
            fitted = T.fit_model(m, cols, tab.info, X[tr], ytr, w)                 # the frozen fit
            raw = T.raw_score(fitted, X[idx[s]])
            p = 1.0 / (1.0 + np.exp(fold[s]["platt_a"] * raw + fold[s]["platt_b"]))  # the saved calibration
            for j, i in enumerate(idx[s]):
                sp = saved_p[wid[i]]
                worst_p = max(worst_p, abs(p[j] - sp["p_ai"]))
                n_call += int(int(p[j] >= fold[s]["threshold"]) == sp["called_ai"])
            phi, b, out = explain(m, fitted, X[tr], X[idx[s]])
            worst_add = max(worst_add, float(np.abs(phi.sum(axis=1) + b - out).max()))
            n_inputs = phi.shape[1]
            if n_inputs not in (len(cols), len(cols) + 1):
                raise SystemExit("STOP: unexpected number of inputs for " + m)
            sh[idx[s]] = phi[:, :len(cols)]
            if n_inputs == len(cols) + 1:
                extra[idx[s]] = phi[:, len(cols)]                                   # "the window has commands"
            base[idx[s]] = b
            score[idx[s]] = out
        ok = worst_p < 1e-9 and n_call == len(y) and n_matrix == 9 and worst_add < 1e-4
        checks["models"][m] = dict(inputs=n_inputs, windows=int(len(y)), largest_difference_in_p_ai=worst_p,
                                   same_call=n_call, training_matrices_equal=n_matrix,
                                   shap_and_base_minus_raw_score_largest=worst_add, result="PASS" if ok else "VOID")
        if not ok:
            void.append(m)
            continue
        unfolded = sh.copy()
        if n_inputs == len(cols) + 1:
            sh[:, i_cmd] += extra                            # addendum item 2: added before the absolute value
        SH[m], EXTRA[m] = sh, (unfolded, extra, n_inputs)
        if m != "xgb":                                       # XGBoost's are in ../tables/ already
            table("L3_shap_values_main_%s.csv" % m,
                  ["window_id", "session", "class_ai", "stage_group", "base_value", "raw_score"] + cols +
                  (["added_input_window_has_commands_before_folding"] if n_inputs == len(cols) + 1 else []),
                  [[wid[i], sess[i], int(y[i]), grp[i], float(base[i]), float(score[i])] + [float(v) for v in sh[i]] +
                   ([float(extra[i])] if n_inputs == len(cols) + 1 else []) for i in range(len(y))])
    if void:
        print(checks["models"])
        raise SystemExit("VOID for: " + ", ".join(void))

    def importance(sh, mask):
        h, a = mask & (y == 0), mask & (y == 1)
        if h.sum() == 0 or a.sum() == 0:
            return None
        ab = np.abs(sh)
        imp = 0.5 * (ab[h].mean(axis=0) + ab[a].mean(axis=0))
        return dict(imp=imp, share=imp / imp.sum(), plain=ab[mask].mean(axis=0),
                    sep=sh[a].mean(axis=0) - sh[h].mean(axis=0), n_h=int(h.sum()), n_a=int(a.sum()))

    def direction(sh, mask, j):
        mm = mask & ~np.isnan(X[:, j])
        if mm.sum() < MIN_N or np.unique(X[mm, j]).size < 2 or np.unique(sh[mm, j]).size < 2:
            return None, None, int(mm.sum())
        rho = float(spearmanr(X[mm, j], sh[mm, j]).statistic)
        return ("ai" if rho > 0 else "human"), rho, int(mm.sum())

    L3, holds, dependent, drow, lrow, arow = {}, {}, {}, [], [], []
    for m in T.MODELS:
        sh = SH[m]
        for g in ALL_GROUPS:
            mask = np.ones(len(y), dtype=bool) if g == "all" else (grp == g)
            full = importance(sh, mask)
            rk = F.ranks_desc(list(full["share"]))
            dr = []
            for s in sessions:
                d = importance(sh, mask & (sess != s))
                if d is None:
                    dr.append(dict(session=s, ranks=None, indicative=True, n_h=0, n_a=0))
                else:
                    dr.append(dict(session=s, ranks=F.ranks_desc(list(d["share"])), share=d["share"],
                                   indicative=min(d["n_h"], d["n_a"]) < MIN_N, n_h=d["n_h"], n_a=d["n_a"]))
            for j, c in enumerate(cols):
                dname, rho, n_def = direction(sh, mask, j)
                rr = [(d["ranks"][j], d["session"]) for d in dr if d["ranks"] is not None]
                ni = [(d["ranks"][j], d["session"]) for d in dr if d["ranks"] is not None and not d["indicative"]]
                L3[(m, g, c)] = dict(share=float(full["share"][j]), rank=rk[j], imp=float(full["imp"][j]),
                                     plain=float(full["plain"][j]), sep=float(full["sep"][j]), direction=dname, rho=rho,
                                     n_defined=n_def, n_h=full["n_h"], n_a=full["n_a"],
                                     rank_lo=min(rr)[0], rank_lo_without=min(rr)[1], rank_hi=max(rr)[0],
                                     rank_hi_without=max(rr)[1],
                                     rank_lo_ni=min(ni)[0] if ni else None, rank_hi_ni=max(ni)[0] if ni else None)
            for d in dr:
                for j, c in enumerate(cols):
                    drow.append([m, g, d["session"], d["n_h"], d["n_a"], int(d["indicative"]), c,
                                 None if d["ranks"] is None else float(d["share"][j]),
                                 None if d["ranks"] is None else d["ranks"][j]])
            unfolded, extra, n_inputs = EXTRA[m]
            if n_inputs == len(cols) + 1:                    # the added input's own share, among the 41 inputs
                h, a = mask & (y == 0), mask & (y == 1)
                both = np.column_stack([np.abs(unfolded), np.abs(extra)])
                imp41 = 0.5 * (both[h].mean(axis=0) + both[a].mean(axis=0))
                arow.append([m, g, float(imp41[-1] / imp41.sum()), float(imp41[i_cmd] / imp41.sum()),
                             L3[(m, g, "cmd_count")]["share"]])
        for c in cols:
            dirs = [L3[(m, g, c)]["direction"] for g in RULE_GROUPS]
            holds[(m, c)] = (all(L3[(m, g, c)]["rank"] <= TOP_WIDE for g in RULE_GROUPS)
                             and dirs[0] is not None and len(set(dirs)) == 1)
            dependent[(m, c)] = any(L3[(m, g, c)]["rank"] <= TOP for g in RULE_GROUPS) and not holds[(m, c)]
        for g in ALL_GROUPS:
            for c in cols:
                x = L3[(m, g, c)]
                lrow.append([m, SCALE[m], g, int(min(x["n_h"], x["n_a"]) < MIN_N), x["n_h"], x["n_a"], c, tier[c], goes[c],
                             x["share"], x["rank"], x["rank_lo"], x["rank_lo_without"], x["rank_hi"], x["rank_hi_without"],
                             x["rank_lo_ni"], x["rank_hi_ni"], x["direction"] or "", x["rho"], x["n_defined"], x["imp"],
                             x["plain"], x["sep"], int(holds[(m, c)]), int(dependent[(m, c)])])
    table("L3_shap_by_stage_group_five.csv", [
        "model", "scale", "stage_group", "indicative", "n_human", "n_ai", "column", "tier", "goes_with", "share", "rank",
        "rank_lowest_over_session_drops", "lowest_without", "rank_highest_over_session_drops", "highest_without",
        "rank_lowest_drops_not_indicative", "rank_highest_drops_not_indicative", "direction_higher_value_pushes_toward",
        "spearman_rho_value_to_shap", "windows_with_the_column_defined", "mean_abs_shap_classes_equal",
        "mean_abs_shap_all_windows", "mean_shap_ai_minus_human", "holds_in_every_stage", "stage_dependent"], lrow)
    table("L3_session_drops_five.csv", ["model", "stage_group", "session_left_out", "n_human", "n_ai", "indicative",
                                        "column", "share", "rank"], drow)
    table("X_added_input.csv", ["model", "stage_group", "share_of_the_added_input_among_41_inputs",
                                "share_of_cmd_count_among_41_inputs", "share_of_cmd_count_after_folding_among_40"], arow)

    # ---- addendum item 5: XGBoost equals the table of the first run, at the six decimals that table holds
    with open(os.path.join(F.TABLES, "L3_shap_by_stage_group.csv"), encoding="utf-8", newline="") as f:
        first = {(r["stage_group"], r["column"]): (float(r["share"]), int(r["rank"])) for r in csv.DictReader(f)}
    same = sum(1 for g in ALL_GROUPS for c in cols
               if round(L3[("xgb", g, c)]["share"], 6) == first[(g, c)][0] and L3[("xgb", g, c)]["rank"] == first[(g, c)][1])
    checks["xgboost_equals_the_first_run"] = dict(cells=len(ALL_GROUPS) * len(cols), equal=same,
                                                  compared_at="the six decimals the first table holds, and the rank",
                                                  result="PASS" if same == len(ALL_GROUPS) * len(cols) else "VOID")
    if checks["xgboost_equals_the_first_run"]["result"] != "PASS":
        raise SystemExit("VOID: XGBoost does not equal the first run")

    # ---- across the five classifiers (addendum)
    n5 = {(g, c): sum(1 for m in T.MODELS if L3[(m, g, c)]["rank"] <= TOP) for g in ALL_GROUPS for c in cols}
    n10 = {(g, c): sum(1 for m in T.MODELS if L3[(m, g, c)]["rank"] <= TOP_WIDE) for g in ALL_GROUPS for c in cols}
    mean_share = {(g, c): float(np.mean([L3[(m, g, c)]["share"] for m in T.MODELS])) for g in ALL_GROUPS for c in cols}
    xrow = []
    for g in ALL_GROUPS:
        for c in sorted(cols, key=lambda c: (-mean_share[(g, c)], cols.index(c))):
            xrow.append([g, c, tier[c], goes[c], n5[(g, c)], n10[(g, c)], int(n5[(g, c)] >= AGREED), mean_share[(g, c)]] +
                        [L3[(m, g, c)]["share"] for m in T.MODELS] + [L3[(m, g, c)]["rank"] for m in T.MODELS] +
                        [("toward_ai" if L3[(m, g, c)]["sep"] > 0 else "toward_human") for m in T.MODELS])
    table("X_top_counts.csv", ["stage_group", "column", "tier", "goes_with", "classifiers_with_it_in_top_five",
                               "classifiers_with_it_in_top_ten", "agreed_top_column", "mean_share_five_classifiers"] +
          ["share_" + m for m in T.MODELS] + ["rank_" + m for m in T.MODELS] + ["net_effect_" + m for m in T.MODELS], xrow)
    crow, cc_share = [], {}
    for m in T.MODELS:
        for g in ALL_GROUPS:
            cc_share[(m, g)] = float(sum(L3[(m, g, c)]["share"] for c in cc18))
            crow.append([m, g, cc_share[(m, g)]] + [float(sum(L3[(m, g, c)]["share"] for c in cols if tier[c] == t)) for t in tiers])
    table("X_command_content_share.csv", ["model", "stage_group", "share_command_content_with_its_context_18_columns",
                                          "share_behavior_18", "share_command_content_14", "share_context_8"], crow)
    table("X_patterns.csv", ["column", "tier", "classifiers_for_which_it_holds_in_every_stage"] +
          ["holds_" + m for m in T.MODELS] + ["stage_dependent_" + m for m in T.MODELS],
          [[c, tier[c], sum(int(holds[(m, c)]) for m in T.MODELS)] + [int(holds[(m, c)]) for m in T.MODELS] +
           [int(dependent[(m, c)]) for m in T.MODELS] for c in cols
           if any(holds[(m, c)] or dependent[(m, c)] for m in T.MODELS)])
    brow, between = [], {}
    for g in ALL_GROUPS:
        for a, b in itertools.combinations(T.MODELS, 2):
            rho = float(spearmanr([L3[(a, g, c)]["share"] for c in cols], [L3[(b, g, c)]["share"] for c in cols]).statistic)
            between[(g, a, b)] = rho
            brow.append([g, a, b, rho])
    table("X_agreement_between_classifiers.csv", ["stage_group", "model_a", "model_b", "spearman_rho_of_the_40_shares"], brow)
    srow, across = [], {}
    for m in T.MODELS:
        for a, b in itertools.combinations(RULE_GROUPS, 2):
            rho = float(spearmanr([L3[(m, a, c)]["share"] for c in cols], [L3[(m, b, c)]["share"] for c in cols]).statistic)
            across[(m, a, b)] = rho
            srow.append([m, a, b, rho])
    table("X_agreement_between_stage_groups.csv", ["model", "stage_group_a", "stage_group_b", "spearman_rho_of_the_40_shares"], srow)

    # ---- the table the figure is drawn from
    feats = [c for c in cols if any(L3[(m, g, c)]["rank"] <= TOP for m in T.MODELS for g in RULE_GROUPS)]
    feats.sort(key=lambda c: (-mean_share[("all", c)], cols.index(c)))
    head = ["column", "definition", "tier", "mean_share_all_windows_five_classifiers"]
    for m in T.MODELS:
        for g in RULE_GROUPS:
            k = "%s_s%s" % (m, g.replace("-", "_"))
            head += [k + "_share", k + "_rank", k + "_mean_shap_ai_minus_human"]
    for g in RULE_GROUPS:
        head += ["s%s_classifiers_with_it_in_top_five" % g.replace("-", "_")]
    head += ["classifiers_for_which_it_holds_in_every_stage"]
    table("T_five_by_stage.csv", head, [
        [c, tab.info[c]["definition"], tier[c], mean_share[("all", c)]] +
        [v for m in T.MODELS for g in RULE_GROUPS for v in (L3[(m, g, c)]["share"], L3[(m, g, c)]["rank"], L3[(m, g, c)]["sep"])] +
        [n5[(g, c)] for g in RULE_GROUPS] + [sum(int(holds[(m, c)]) for m in T.MODELS)] for c in feats])

    # ---- the summary a person reads
    ML = T.MODEL_LABEL
    L = []
    L.append("# Study 3, H2: what each of the five classifiers relies on, by ATT&CK stage group\n")
    L.append("Written by `code/h2_features/run_h2_features_five.py`. Descriptive and post hoc; it gives no verdict. Rules: "
             "`../H2_FEATURES_RULE_BEFORE_RUN.md` and `RULE_ADDENDUM_BEFORE_RUN.md` (SHA-256 `%s`). Freeze 2 SHA-256 `%s`.\n"
             % (rule_sha, freeze_2))
    L.append("Share: the column's part of the classifier's mean absolute SHAP value on held-out windows, classes counted "
             "equally. Each window is explained by the model that never saw its session.\n")
    for g in RULE_GROUPS:
        L.append("## %s: top five of each classifier\n" % F.STAGE_LABEL[g])
        L.append("| Rank | " + " | ".join(ML[m] for m in T.MODELS) + " |")
        L.append("|---|" + "---|" * len(T.MODELS))
        for k in range(1, TOP + 1):
            cells = []
            for m in T.MODELS:
                c = [c for c in cols if L3[(m, g, c)]["rank"] == k][0]
                cells.append("`%s` %s%s" % (c, F.pct(L3[(m, g, c)]["share"]), " †" if L3[(m, g, c)]["sep"] < 0 else ""))
            L.append("| %d | " % k + " | ".join(cells) + " |")
        agreed = [c for c in cols if n5[(g, c)] >= AGREED]
        L.append("\nAgreed top columns (top five of at least four classifiers): " + (", ".join(
            "`%s` (%d of 5)" % (c, n5[(g, c)]) for c in sorted(agreed, key=lambda c: -mean_share[(g, c)])) or "none") + "\n")
    L.append("† on balance the column moves AI windows toward human in that stage group.\n")
    L.append("## Share of command content with its 4 context columns (18 of the 40 columns)\n")
    L.append("| Classifier | " + " | ".join(short(g) for g in RULE_GROUPS) + " | All windows |")
    L.append("|---|" + "---|" * (len(RULE_GROUPS) + 1))
    for m in T.MODELS:
        L.append("| %s | " % ML[m] + " | ".join(F.pct(cc_share[(m, g)]) for g in RULE_GROUPS + ["all"]) + " |")
    L.append("\n## Does a classifier rely on the same columns in every stage group?\n")
    L.append("Spearman's rho between its 40 shares in two stage groups.\n")
    L.append("| Classifier | " + " | ".join("%s and %s" % (short(a).lower(), short(b).lower()) for a, b in itertools.combinations(RULE_GROUPS, 2))
             + " | Holds in every stage | Stage-dependent |")
    L.append("|---|" + "---|" * 5)
    for m in T.MODELS:
        L.append("| %s | " % ML[m] + " | ".join(F.f3(across[(m, a, b)]) for a, b in itertools.combinations(RULE_GROUPS, 2)) +
                 " | %s | %s |" % (", ".join("`%s`" % c for c in cols if holds[(m, c)]) or "none",
                                  ", ".join("`%s`" % c for c in cols if dependent[(m, c)]) or "none"))
    L.append("\n## Do the classifiers rely on the same columns?\n")
    L.append("Spearman's rho between the 40 shares of two classifiers, lowest and highest of the ten pairs.\n")
    L.append("| Stage group | Lowest pair | Highest pair | Median of the ten |")
    L.append("|---|---|---|---|")
    for g in RULE_GROUPS + ["all"]:
        pairs = sorted(((between[(g, a, b)], a, b) for a, b in itertools.combinations(T.MODELS, 2)))
        L.append("| %s | %s (%s, %s) | %s (%s, %s) | %s |" % (
            short(g), F.f3(pairs[0][0]), pairs[0][1], pairs[0][2], F.f3(pairs[-1][0]), pairs[-1][1], pairs[-1][2],
            F.f3(float(np.median([p[0] for p in pairs])))))
    L.append("\n## Columns that hold in every stage, by the number of classifiers\n")
    for k in range(len(T.MODELS), 0, -1):
        cs = [c for c in cols if sum(int(holds[(m, c)]) for m in T.MODELS) == k]
        if cs:
            L.append("- **%d of 5:** " % k + ", ".join("`%s`" % c for c in cs))
    L.append("")
    T.write_once(os.path.join(OUT, "FIVE_CLASSIFIERS_SUMMARY.md"), "\n".join(L) + "\n", overwrite=True)

    checks["agreed_top_columns"] = {g: [c for c in cols if n5[(g, c)] >= AGREED] for g in ALL_GROUPS}
    checks["top_five"] = {m: {g: sorted(cols, key=lambda c: L3[(m, g, c)]["rank"])[:TOP] for g in ALL_GROUPS} for m in T.MODELS}
    checks["holds_in_every_stage"] = {m: [c for c in cols if holds[(m, c)]] for m in T.MODELS}
    checks["stage_dependent"] = {m: [c for c in cols if dependent[(m, c)]] for m in T.MODELS}
    checks["share_command_content_with_its_context"] = {m: {g: cc_share[(m, g)] for g in ALL_GROUPS} for m in T.MODELS}
    checks["d_freeze_1_after"] = F.freeze_1_check()
    checks["d_freeze_2_after"] = T.check_freeze_2(kinds=F.ALL_KINDS)
    checks["leak_audit"] = F.leak_audit(set(sessions), skip=("h2_features_checks.json", "five_classifiers_checks.json"))
    checks["inputs_opened"] = inp.opened
    files = {}
    for top, rel in ((TABLES, "results_h2_features/five_classifiers/tables/"), (os.path.join(OUT, "figures"), "results_h2_features/five_classifiers/figures/")):
        if os.path.isdir(top):
            for n in sorted(os.listdir(top)):
                files[rel + n] = T.sha256_file(os.path.join(top, n))
    for n in ("FIVE_CLASSIFIERS_SUMMARY.md", "RULE_ADDENDUM_BEFORE_RUN.md"):
        files["results_h2_features/five_classifiers/" + n] = T.sha256_file(os.path.join(OUT, n))
    for n in sorted(os.listdir(HERE)):
        if n.endswith(".py"):
            files["code/h2_features/" + n] = T.sha256_file(os.path.join(HERE, n))
    checks["files"] = files
    T.write_once(os.path.join(OUT, "five_classifiers_checks.json"), T.dump_json(checks), overwrite=True)
    for m in T.MODELS:
        print(m, checks["models"][m])
    print("xgboost equals the first run:", checks["xgboost_equals_the_first_run"]["result"], "| freeze 1 changed:",
          checks["d_freeze_1_after"]["changed"], "| leak audit:", checks["leak_audit"]["result"], checks["leak_audit"]["total_hits"])
    print("COMPLETE: results_h2_features/five_classifiers/")


if __name__ == "__main__":
    main()
