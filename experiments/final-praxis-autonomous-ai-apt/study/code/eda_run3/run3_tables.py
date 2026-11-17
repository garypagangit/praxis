"""EDA run 3, tables (rule file sections 2 to 4).

Feature values are read from the rows marked `train` and from no other row, with the Pass 2
loader. Counts come from the Pass 1 tables. AUC and same-stage AUC are taken from the Pass 2
tables; what is recomputed here is recomputed as a check. No model is fitted.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import run3_common as R

C, E, np = R.C, R.E, R.np

BY_STAGE = ["1-4", "5", "7"]            # at least 10 training windows in both classes (Pass 2's rule)
GROUP_KEY = {"1-4": "discovery", "5": "execution", "6": "account_manipulation", "7": "lateral_collection"}
EDA_INPUT_TABLES = ["T1_dataset_summary_by_session.csv", "T2_kept_windows_by_stage_group_class.csv",
                    "E2_overview_pass2.csv", "T4_feature_profile_w30.csv", "T6_near_duplicates_w30.csv",
                    "T7_same_stage_auc_all_features_w30.csv", "T7_stage_group_training_windows_w30.csv",
                    "E9_spearman_top20.csv"]


class Checks:
    def __init__(self):
        self.run, self.failed = 0, []

    def eq(self, what, got, want, tol=None):
        self.run += 1
        if tol is None:
            ok = got == want
        else:
            ok = (got is None and want is None) or (got is not None and want is not None and abs(got - want) <= tol)
        if not ok:
            self.failed.append({"check": what, "got": got, "want": want})


def close(got, want):
    """Tolerance for a value the Pass 2 table prints with six significant digits."""
    return 5e-6 * max(1.0, abs(want)) + 1e-9


def main():
    allow = ["reports/05_windows_report.json", "data/labels/sessions.csv", "data/description/sessions.csv",
             "data/splits/splits_%s.csv" % R.WL, "data/description/window_description_%s.csv" % R.WL,
             "data/features/%s/features.csv" % R.WL, "data/features/%s/feature_columns.json" % R.WL]
    allow += [R.EDA_TABLES + n for n in EDA_INPUT_TABLES]
    inp = R.Inputs3(allow)
    chk = Checks()

    sessions, _ = E.session_table(inp)
    rows, columns, tlog = C.load_training(inp, R.WL, sessions)
    cols, meta = C.load_columns(inp, R.WL)
    col_of = {c["column"]: c for c in cols}
    n_cls = {c: sum(1 for r in rows if r["class"] == c) for c in E.CLASSES}
    chk.eq("training rows, human", n_cls["human"], 425)
    chk.eq("training rows, AI", n_cls["ai"], 157)

    t4 = inp.table("T4_feature_profile_w30.csv")
    t4_of = {r["feature"]: r for r in t4}
    t6 = inp.table("T6_near_duplicates_w30.csv")
    merged_members = {r["member"] for r in t6}
    t7s = {(r["feature"], r["stage_group"]): r for r in inp.table("T7_same_stage_auc_all_features_w30.csv")}
    t7n = {(r["class"], r["stage_group"]): r for r in inp.table("T7_stage_group_training_windows_w30.csv")}
    for cls in E.CLASSES:
        for g in R.STAGE_GROUPS:
            n = sum(1 for r in rows if r["class"] == cls and r["stage_group"] == g)
            chk.eq("training windows %s %s" % (cls, g), n, int(t7n[(cls, g)]["training_windows"]))
    for g in BY_STAGE:
        chk.eq("stage group %s has 10 in both classes" % g, t7n[("human", g)]["at_least_10_in_both_classes"], "yes")

    # ---------------------------------------------------------------- R10: the main configuration, ranked
    main = [r for r in t4 if r["in_main_configuration"] == "yes"]
    chk.eq("main configuration columns", len(main), 40)
    for r in main:
        c = col_of[r["feature"]]
        chk.eq("main configuration rule " + r["feature"], c["goes_with"] in ("behavior", "command_content"), True)
    main.sort(key=lambda r: (-(R.num(r["auc"]) or 0.0), int(r["rank"])))
    top20 = [r["feature"] for r in main if r["feature"] not in merged_members and r["merged_into"] == ""][:20]
    chk.eq("top 20 size", len(top20), 20)
    out = []
    for k, r in enumerate(main, 1):
        f = r["feature"]
        ai, hu = C.values(rows, f, "ai"), C.values(rows, f, "human")
        a = C.a_stat(ai, hu)
        chk.eq("AUC " + f, None if a is None else round(C.auc_of(a), 4), R.num(r["auc"]), tol=1e-9)
        chk.eq("defined human " + f, len(hu), int(r["defined_human"]))
        chk.eq("defined AI " + f, len(ai), int(r["defined_ai"]))
        for cls, v in (("human", hu), ("ai", ai)):
            q1, q2, q3 = R.quartiles(v)
            for name, got in (("q1_", q1), ("median_", q2), ("q3_", q3)):
                want = R.num(r[name + cls])
                chk.eq("%s%s %s" % (name, cls, f), got, want, tol=None if want is None else close(got, want))
        out.append([k, top20.index(f) + 1 if f in top20 else "", f, R.LABEL[f], r["tier"], r["goes_with"], r["kind"],
                    r["n_human"], r["n_ai"], r["defined_human"], r["defined_ai"],
                    r["median_human"], r["q1_human"], r["q3_human"], r["median_ai"], r["q1_ai"], r["q3_ai"],
                    r["auc"], r["higher_in"], r["auc_drop_min"], r["auc_drop_max"], r["merged_into"]])
    R.write_csv("R10_auc_main_configuration.csv",
                ["main_rank", "main_top20_rank", "feature", "label", "tier", "goes_with", "kind", "n_human", "n_ai",
                 "defined_human", "defined_ai", "median_human", "q1_human", "q3_human", "median_ai", "q1_ai", "q3_ai",
                 "auc", "higher_in", "auc_drop_min", "auc_drop_max", "merged_into"], out)

    # ---------------------------------------------------------------- R9: Spearman among the top 20
    e9 = {}
    for r in inp.table("E9_spearman_top20.csv"):
        e9[frozenset((r["feature_a"], r["feature_b"]))] = R.num(r["spearman_rho"])
    out, shared = [], 0
    for ia in range(1, 20):
        for ib in range(ia):
            fa, fb = top20[ia], top20[ib]                      # rank_a > rank_b: row a, column b
            rho, n = C.spearman(rows, fa, fb)
            if frozenset((fa, fb)) in e9:
                shared += 1
                chk.eq("Spearman %s %s" % (fa, fb), None if rho is None else round(rho, 4), e9[frozenset((fa, fb))],
                       tol=1e-9)
            out.append([ia + 1, fa, R.short_label(fa), ib + 1, fb, R.short_label(fb), R.f4(rho), n])
    R.write_csv("R9_spearman_main_top20.csv",
                ["rank_a", "feature_a", "label_a", "rank_b", "feature_b", "label_b", "spearman_rho", "rows_both_defined"],
                out)

    # ---------------------------------------------------------------- R11: the six H1 columns, by class
    pts, meds = [], []
    order = {s["session"]: i for i, s in enumerate(sessions)}
    for f in R.H1_COLUMNS:
        chk.eq("H1 column is command content " + f, t4_of[f]["tier"], "command_content")
        for r in rows:
            v = r["x"][f]
            if v is not None:
                pts.append([f, r["class"], r["session"], r["stage_group"], R.g6(v)])
        for s in sessions:
            v = [r["x"][f] for r in rows if r["session"] == s["session"] and r["x"][f] is not None]
            meds.append([f, R.LABEL[f], col_of[f]["kind"], s["class"], s["session"], len(v),
                         R.g6(R.quartiles(v)[1]) if v else ""])
    R.write_csv("R11_h1_points.csv", ["feature", "class", "session", "stage_group", "value"], pts)
    R.write_csv("R11_h1_session_medians.csv",
                ["feature", "label", "kind", "class", "session", "defined_windows", "median"], meds)

    # ---------------------------------------------------------------- R12: the six H1 columns, by stage group
    out = []
    for f in R.H1_COLUMNS:
        a_all = R.num(t4_of[f]["a_ai_higher"])
        for g in BY_STAGE:
            keep = (lambda r, g=g: r["stage_group"] == g)
            t = t7s[(f, g)]
            ai, hu = C.values(rows, f, "ai", keep), C.values(rows, f, "human", keep)
            a = C.a_stat(ai, hu)
            d = C.directed(a, a_all)
            chk.eq("same-stage AUC %s %s" % (f, g), None if d is None else round(d, 4),
                   R.num(t["auc_in_all_rows_direction"]), tol=1e-9)
            chk.eq("same-stage n human %s %s" % (f, g), len(hu), int(t["n_human"]))
            chk.eq("same-stage n AI %s %s" % (f, g), len(ai), int(t["n_ai"]))
            for cls, v in (("human", hu), ("ai", ai)):
                n, ns, big, share = C.sessions_behind(rows, f, cls, keep)
                q1, q2, q3 = R.quartiles(v)
                out.append([f, R.LABEL[f], g, R.STAGE_NAME[g], cls, n, ns, big, share, R.g6(q2), R.g6(q1), R.g6(q3),
                            t["auc_in_all_rows_direction"], t["auc"], t["higher_in"], t["indicative"]])
    R.write_csv("R12_h1_by_stage_group.csv",
                ["feature", "label", "stage_group", "stage_name", "class", "defined_windows", "sessions",
                 "largest_session", "largest_session_share_pct", "median", "q1", "q3",
                 "same_stage_auc_in_all_rows_direction", "same_stage_auc", "same_stage_higher_in", "indicative"], out)

    # ---------------------------------------------------------------- R13: top 20 of the main configuration, by stage group
    out = []
    for k, f in enumerate(top20, 1):
        r = t4_of[f]
        line = [k, f, R.LABEL[f], r["tier"], r["higher_in"], r["auc"]]
        for g in BY_STAGE:
            t = t7s[(f, g)]
            line += [t["auc_in_all_rows_direction"], t["n_human"], t["n_ai"], t["indicative"]]
        out.append(line)
    header = ["main_top20_rank", "feature", "label", "tier", "higher_in", "auc_all"]
    for g in BY_STAGE:
        header += [GROUP_KEY[g] + s for s in ("_auc_dir", "_n_human", "_n_ai", "_indicative")]
    R.write_csv("R13_main_top20_by_stage_group.csv", header, out)
    out = []
    for cls in E.CLASSES:
        for g in R.STAGE_GROUPS:
            t = t7n[(cls, g)]
            out.append([cls, g, R.STAGE_NAME[g], t["training_windows"], t["sessions"], t["largest_session"],
                        t["largest_session_share_pct"], t["at_least_10_in_both_classes"]])
    R.write_csv("R13_stage_group_training_windows.csv",
                ["class", "stage_group", "stage_name", "training_windows", "sessions", "largest_session",
                 "largest_session_share_pct", "at_least_10_in_both_classes"], out)

    # ---------------------------------------------------------------- R1: data example, one training window per session
    out, rule_used = [], {}
    for s in sessions:
        mine = [r for r in rows if r["session"] == s["session"]]
        pick = next((r for r in mine if (r["x"]["cmd_count"] or 0) >= 2), None)
        rule_used[s["session"]] = "first training window with at least two commands"
        if pick is None:
            pick = next((r for r in mine if (r["x"]["cmd_count"] or 0) >= 1), None)
            rule_used[s["session"]] = "no training window with two commands; first with one"
        out.append([s["session"], s["class"], pick["stage_group"], R.STAGE_NAME[pick["stage_group"]]] +
                   [R.g6(pick["x"][c]) if pick["x"][c] is not None else "undefined" for c in R.EXAMPLE_COLUMNS])
    R.write_csv("R1_data_example.csv", ["session", "class", "stage_group", "stage_name"] + R.EXAMPLE_COLUMNS, out)

    # ---------------------------------------------------------------- R2: overview and class by stage group
    ov = inp.table("E2_overview_pass2.csv")
    tier_n = {}
    for c in cols:
        tier_n[c["tier"]] = tier_n.get(c["tier"], 0) + 1
    out = [[r["item"], r["human"], r["ai"], r["all"], r["note"]] for r in ov]
    out.append(["main_configuration_columns", "", "", sum(1 for c in cols if c["in_main"]),
                "behavior %d; command content %d; context columns that go with them %d"
                % (tier_n["behavior"], tier_n["command_content"],
                   sum(1 for c in cols if c["in_main"] and c["tier"] == "context"))])
    out.append(["identifier_columns", "", "", 1, "window_id"])
    out.append(["label_columns", "", "", 1, "class of the session, held in a separate file"])
    out.append(["training_windows_30s", n_cls["human"], n_cls["ai"], len(rows), "rows whose feature values the EDA reads"])
    R.write_csv("R2_overview.csv", ["item", "human", "ai", "all", "note"], out)
    t2 = [r for r in inp.table("T2_kept_windows_by_stage_group_class.csv") if r["window_s"] == "30"]
    total = sum(int(r["kept_windows"]) for r in t2 if r["stage_group"] == "all")
    chk.eq("kept windows", total, 951)
    out = []
    for r in t2:
        if r["stage_group"] == "all":
            continue
        out.append([r["class"], r["stage_group"], R.STAGE_NAME[r["stage_group"]], r["kept_windows"], r["pct_of_class"],
                    "%.1f" % (100.0 * int(r["kept_windows"]) / total), r["sessions_supplying"], r["largest_session"],
                    r["largest_session_share_pct"]])
    R.write_csv("R2_class_by_stage_group.csv",
                ["class", "stage_group", "stage_name", "kept_windows", "pct_of_class", "pct_of_all_kept_windows",
                 "sessions_supplying", "largest_session", "largest_session_share_pct"], out)
    t1 = [r for r in inp.table("T1_dataset_summary_by_session.csv") if r["row_type"] == "session"]
    chk.eq("sessions", len(t1), 9)

    log = {"run": "EDA run 3", "run3_version": R.RUN3_VERSION, "rule_file": "reports/eda_run3/RULE_BEFORE_RUN.md",
           "freeze_1_sha256": inp.freeze_sha256, "freeze_2_sha256": inp.freeze2_sha256,
           "pass2_checks_sha256": inp.pass2_checks_sha256,
           "inputs_opened": inp.opened, "training_rows": tlog,
           "main_configuration_top20": top20, "h1_columns": R.H1_COLUMNS, "stage_groups_in_by_stage_tables": BY_STAGE,
           "data_example_rule": rule_used, "spearman_pairs_shared_with_pass2": shared,
           "checks_run": chk.run, "checks_failed": len(chk.failed), "failures": chk.failed}
    E.write_json(os.path.join(R.OUT, "run3_tables_log.json"), log)
    print("tables: training rows %d (%d human, %d AI); checks %d, failed %d; Spearman pairs shared with Pass 2: %d"
          % (len(rows), n_cls["human"], n_cls["ai"], chk.run, len(chk.failed), shared))
    for f in chk.failed[:12]:
        print("  FAILED", f)
    return 0 if not chk.failed else 1


if __name__ == "__main__":
    sys.exit(main())
