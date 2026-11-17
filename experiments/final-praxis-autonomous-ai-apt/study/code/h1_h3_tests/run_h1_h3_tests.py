"""Study 3: the paired tests of H1 and H3 as restated after scoring, written to file.

    S3_LIBS=<pinned libraries> python3 -I -B code/h1_h3_tests/run_h1_h3_tests.py

Post hoc (2026-11-14). The rules are in results_h1_h3/RULES_AS_DECIDED.md, which says
plainly that they were not written before their numbers. Nothing is fitted: every
number comes from the held-out predictions saved in results/trials/ by the scored run,
with the frozen session bootstrap of code/trials/summarize.py.
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(CODE, "trials"))            # the frozen trial code, read only
import trial_common as T
import summarize as S

np = T.np
VERSION = "study3-h1-h3-tests-1.0"
OUT = os.path.join(T.ROOT, "results_h1_h3")
TABLES = os.path.join(OUT, "tables")
RULE = os.path.join(OUT, "RULES_AS_DECIDED.md")
ALL_KINDS = ("trial_code", "feature_table", "design", "plumbing", "feature_code", "eda_code",
             "feature_report", "eda_output", "plumbing_parts")


def table(name, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else (repr(round(float(v), 6)) if isinstance(v, (float, np.floating)) else v) for v in r])
    T.write_once(os.path.join(TABLES, name), buf.getvalue(), overwrite=True)


def freeze_1_check():
    fz = T.read_json(os.path.join(T.REPORTS, "FREEZE_1.json"))["files"]
    ok, bad, skipped = 0, [], 0
    for rel, meta in sorted(fz.items()):
        if rel.startswith("set_aside/") or "_private" in rel or "labels_test_" in rel or "AHIR Participant Evidence" in rel:
            skipped += 1
            continue
        p = os.path.join(T.ROOT, *rel.split("/"))
        if os.path.exists(p) and T.sha256_file(p) == meta["sha256"]:
            ok += 1
        else:
            bad.append(rel)
    return dict(listed=len(fz), match=ok, changed=bad, not_opened=skipped)


def main():
    if not os.path.exists(RULE):
        raise SystemExit("REFUSED: the rules file is missing")
    freeze_2 = T.check_freeze_2(kinds=ALL_KINDS)
    fz1 = freeze_1_check()
    tr = {(n, m): T.read_json(os.path.join(T.RESULTS, "trials", "%s__%s.json" % (n, m)))
          for n in ("main", "no_command_content") for m in T.MODELS}
    cls = {p["session"]: p["y"] for p in tr[("main", "lr")]["predictions"]}
    humans = sorted(s for s in cls if cls[s] == 0)
    ais = sorted(s for s in cls if cls[s] == 1)
    rng = np.random.default_rng(T.SEED)                      # reading T14: the frozen draws
    H = rng.integers(0, len(humans), size=(T.N_BOOT, len(humans)))
    A = rng.integers(0, len(ais), size=(T.N_BOOT, len(ais)))
    boot, f1 = {}, {}
    for k, d in tr.items():
        boot[k] = S.boot_macro(S.session_counts(d["predictions"]), humans, ais, H, A)
        f1[k] = T.f1_parts(*T.confusion([p["y"] for p in d["predictions"]], [p["called_ai"] for p in d["predictions"]]))["macro_f1"]
    checks = dict(version=VERSION, rules_file_sha256=T.sha256_file(RULE), freeze_2_sha256=freeze_2,
                  d_freeze_1_before=fz1, libraries=T.library_versions(), bootstrap_resamples=T.N_BOOT, seed=T.SEED)

    # ---- the frozen tables this must agree with
    frozen_cfg, frozen_h = {}, []
    with open(os.path.join(T.RESULTS, "tables", "T_configurations.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            frozen_cfg[(r["trial"], r["model"])] = (float(r["macro_f1"]), float(r["ci_low"]), float(r["ci_high"]))
    with open(os.path.join(T.RESULTS, "tables", "T_hypotheses.csv"), encoding="utf-8", newline="") as f:
        frozen_h = list(csv.DictReader(f))
    same = sum(1 for k in tr if abs(f1[k] - frozen_cfg[k][0]) < 1e-6 and abs(S.interval(boot[k])[0] - frozen_cfg[k][1]) < 1e-6
               and abs(S.interval(boot[k])[1] - frozen_cfg[k][2]) < 1e-6)
    checks["macro_f1_and_interval_equal_frozen_table"] = dict(cells=len(tr), equal=same, result="PASS" if same == len(tr) else "FAIL")
    others_rf = [m for m in T.MODELS if m != "rf"]
    ps = [S.one_sided_p(boot[("main", "rf")] - boot[("main", m)]) for m in others_rf]
    ok = 0
    for m, p, a in zip(others_rf, ps, S.holm(ps)):
        fz = [r for r in frozen_h if r["hypothesis"] == "H3" and r["model"] == m][0]
        d = boot[("main", "rf")] - boot[("main", m)]
        ok += int(abs(f1[("main", "rf")] - f1[("main", m)] - float(fz["value"])) < 1e-6 and abs(S.interval(d)[0] - float(fz["ci_low"])) < 1e-6
                  and abs(S.interval(d)[1] - float(fz["ci_high"])) < 1e-6 and abs(p - float(fz["p"])) < 1e-6 and abs(a - float(fz["holm_p"])) < 1e-6)
    checks["frozen_H3_rows_reproduced"] = dict(rows=len(others_rf), equal=ok, result="PASS" if ok == len(others_rf) else "FAIL")
    if checks["macro_f1_and_interval_equal_frozen_table"]["result"] != "PASS" or checks["frozen_H3_rows_reproduced"]["result"] != "PASS":
        raise SystemExit("STOP: the frozen tables are not reproduced")

    # ---- H1 as restated: main against no command content
    h1, ps = [], []
    for m in T.MODELS:
        d = boot[("main", m)] - boot[("no_command_content", m)]
        ps.append(S.one_sided_p(d))
        h1.append([m, f1[("no_command_content", m)], f1[("main", m)], f1[("main", m)] - f1[("no_command_content", m)], *S.interval(d)])
    for r, p, a in zip(h1, ps, S.holm(ps)):
        r += [p, a, int(r[3] > 0), int(a <= 0.05 and r[3] > 0)]
    table("T_h1_restated.csv", ["model", "macro_f1_without_command_content", "macro_f1_main", "gain", "ci_low", "ci_high",
                                "p_one_sided", "holm_p", "higher_with_command_content", "above_zero_after_holm"], h1)
    n_higher, n_holm = sum(r[8] for r in h1), sum(r[9] for r in h1)

    # ---- H3 as restated: XGBoost against the other four
    others = [m for m in T.MODELS if m != "xgb"]
    h3, ps = [], []
    for m in others:
        d = boot[("main", "xgb")] - boot[("main", m)]
        ps.append(S.one_sided_p(d))
        h3.append([m, f1[("main", "xgb")], f1[("main", m)], f1[("main", "xgb")] - f1[("main", m)], *S.interval(d)])
    for r, p, a in zip(h3, ps, S.holm(ps)):
        r += [p, a, int(a <= 0.05 and r[3] > 0)]
    table("T_h3_restated.csv", ["model", "macro_f1_xgboost", "macro_f1_model", "xgboost_minus_model", "ci_low", "ci_high",
                                "p_one_sided", "holm_p", "above_zero_after_holm"], h3)
    order = sorted(T.MODELS, key=lambda m: -f1[("main", m)])
    xgb_highest = order[0] == "xgb" and all(f1[("main", "xgb")] > f1[("main", m)] for m in others)
    n_h3 = sum(r[8] for r in h3)

    # ---- the hypotheses fixed before scoring, copied from the frozen results
    verdict = T.read_json(os.path.join(T.RESULTS, "summary.json"))["hypotheses"]
    orig = [["H1", "Command diversity and command-sequence transition entropy improve classification compared with a predefined baseline",
             "Gain from the four columns above zero, Holm-adjusted, in at least 3 of the 5 classifiers",
             "%d of 5" % verdict["H1"]["models_with_gain_above_zero_after_holm"], int(verdict["H1"]["supported"])],
            ["H2", "Logistic regression retains useful behavioral attributes and achieves above-baseline classification performance on previously unseen sessions",
             "p <= 0.05 against the chance baseline of 126 relabelings",
             "p = %.3f (%.3f without command content)" % (verdict["H2"]["p_main"], verdict["H2"]["p_no_command_content"]), int(verdict["H2"]["supported"])],
            ["H3", "Random forest achieves higher held-out-session macro-F1 than the other four classifiers",
             "Random forest is the highest and all four paired differences are above zero, Holm-adjusted",
             "highest: %s; %d of 4 above zero" % ("yes" if verdict["H3"]["random_forest_is_highest"] else "no",
                                                 verdict["H3"]["differences_above_zero_after_holm"]), int(verdict["H3"]["supported"])]]
    table("T_original_hypotheses.csv", ["hypothesis", "wording_fixed_before_scoring", "rule_fixed_before_scoring", "observed", "supported"], orig)

    ML = T.MODEL_LABEL
    L = ["# Study 3: H1 and H3 as restated after scoring\n",
         "Written by `code/h1_h3_tests/run_h1_h3_tests.py` from the saved held-out predictions; nothing is fitted. Rules: "
         "`RULES_AS_DECIDED.md` (SHA-256 `%s`), which were not written before these numbers. Freeze 2 SHA-256 `%s`.\n" % (checks["rules_file_sha256"], freeze_2),
         "## H1: command content against the same classifier without it\n",
         "| Classifier | Without command content (22 columns) | Main (40 columns) | Gain | 95% interval | p | Holm p | Above zero after Holm |",
         "|---|---|---|---|---|---|---|---|"]
    for r in h1:
        L.append("| %s | %.3f | %.3f | %+.3f | %+.3f to %+.3f | %.4f | %.4f | %s |" % (ML[r[0]], r[1], r[2], r[3], r[4], r[5], r[6], r[7], "Yes" if r[9] else "No"))
    L.append("\n**Rule (deck): higher with command content in at least 3 of 5. Observed: %d of 5. %s.** Beside the rule: above zero after "
             "Holm in %d of 5.\n" % (n_higher, "Supported" if n_higher >= 3 else "Not supported", n_holm))
    L += ["## H3: XGBoost against the other four, main configuration\n",
          "Held-out macro-F1, highest first: " + ", ".join("%s %.3f" % (ML[m], f1[("main", m)]) for m in order) + ".\n",
          "| XGBoost minus | Difference | 95% interval | p | Holm p | Above zero after Holm |", "|---|---|---|---|---|---|"]
    for r in h3:
        L.append("| %s | %+.3f | %+.3f to %+.3f | %.3f | %.3f | %s |" % (ML[r[0]], r[3], r[4], r[5], r[6], r[7], "Yes" if r[8] else "No"))
    L.append("\n**Rule (user, 2026-11-14 10:32): XGBoost has the highest macro-F1. Observed: %s. %s.** Beside the rule: above zero after Holm "
             "in %d of 4; the rule on the deck before 10:32 asked for 4.\n" % ("yes" if xgb_highest else "no", "Supported" if xgb_highest else "Not supported", n_h3))
    L += ["## The hypotheses fixed before scoring (from the frozen results)\n", "| | Wording | Rule | Observed | Outcome |", "|---|---|---|---|---|"]
    for r in orig:
        L.append("| %s | %s | %s | %s | %s |" % (r[0], r[1], r[2], r[3], "Supported" if r[4] else "Not supported"))
    L.append("")
    T.write_once(os.path.join(OUT, "H1_H3_SUMMARY.md"), "\n".join(L) + "\n", overwrite=True)

    checks["H1_restated"] = dict(higher_with_command_content=n_higher, needed=3, supported=n_higher >= 3, above_zero_after_holm=n_holm)
    checks["H3_restated"] = dict(xgboost_is_highest=xgb_highest, supported=xgb_highest, above_zero_after_holm=n_h3, of=4)
    checks["d_freeze_1_after"] = freeze_1_check()
    checks["d_freeze_2_after"] = T.check_freeze_2(kinds=ALL_KINDS)
    files = {}
    for n in sorted(os.listdir(TABLES)):
        files["results_h1_h3/tables/" + n] = T.sha256_file(os.path.join(TABLES, n))
    for n in ("H1_H3_SUMMARY.md", "RULES_AS_DECIDED.md"):
        files["results_h1_h3/" + n] = T.sha256_file(os.path.join(OUT, n))
    files["code/h1_h3_tests/run_h1_h3_tests.py"] = T.sha256_file(os.path.join(HERE, "run_h1_h3_tests.py"))
    checks["files"] = files
    T.write_once(os.path.join(OUT, "h1_h3_checks.json"), T.dump_json(checks), overwrite=True)
    print(checks["macro_f1_and_interval_equal_frozen_table"], checks["frozen_H3_rows_reproduced"])
    print("H1:", checks["H1_restated"], "| H3:", checks["H3_restated"], "| freeze 1 changed:", checks["d_freeze_1_after"]["changed"])


if __name__ == "__main__":
    main()
