"""Study 3, H2 (ATT&CK stage groups): the tables, from the per-stage chance baseline.

    python3 -I -B code/h2_stage/summarize_h2_stage.py

Nothing is fitted here. Every number comes from results_h2_stage/parts/ (written by
run_h2_stage.py) and is checked against the frozen results in results/. The rule is in
results_h2_stage/H2_RULE_BEFORE_RUN.md. A rerun gives the same bytes.
"""
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_h2_stage as R                                     # puts the frozen trial code on the path

T = R.T
import summarize as S                                        # frozen: boot_macro, interval

np = T.np
TABLES = os.path.join(R.OUT, "tables")
RULE_GROUPS = ["1-4", "5", "7"]                              # rule, item 2
ALPHA = 0.05
NEED = 3                                                     # classifiers, rule item 5
STAGE_LABEL = {"1-4": "Discovery (stages 1-4)", "5": "Execution (stage 5)",
               "6": "Account manipulation (stage 6), indicative",
               "7": "Lateral movement and collection (stage 7)", "all": "All windows"}
CFG_LABEL = {"main": "Main configuration", "no_command_content": "No command content"}


def table(name, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else (repr(round(v, 6)) if isinstance(v, float) else v) for v in r])
    T.write_once(os.path.join(TABLES, name), buf.getvalue(), overwrite=True)


def f3(x):
    return "n/a" if x is None else "%.3f" % x


def macro(c):
    tp, fp, fn, tn = c
    if tp + fn == 0 or tn + fp == 0:
        return None                                          # one class only (reading T13)
    return T.f1_parts(tp, fp, fn, tn)["macro_f1"]


def stage_counts(rec, g):
    """Windows and windows called AI of each session, in one stage group or in all."""
    out = {}
    for s, d in rec["session_stage"].items():
        if g == "all":
            out[s] = dict(n=sum(v[0] for v in d.values()), called=sum(v[1] for v in d.values()))
        else:
            v = d.get(g, [0, 0])
            out[s] = dict(n=v[0], called=v[1])
    return out


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


def leak_audit(labels, skip):
    sys.path.insert(0, T.CODE)
    import s3_clean as K
    hits, label_count, searched = [], {}, 0
    for top in (R.OUT, HERE):
        for dirpath, dirs, names in os.walk(top):
            dirs.sort()
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for n in sorted(names):
                if not n.endswith((".json", ".jsonl", ".csv", ".md", ".py")) or n in skip:
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


def main():
    freeze_2 = T.check_freeze_2(kinds=R.ALL_KINDS)
    recs = R.all_records()
    tasks = R.all_tasks()
    left = [R.key(t) for t in tasks if R.key(t) not in recs]
    if left:
        raise SystemExit("INCOMPLETE: %d tasks left" % len(left))
    inp = T.Inputs("scored")
    tab = T.load_table(inp, "w30")
    humans = sorted(s for s in tab.sessions if tab.class_of[s] == 0)
    ais = sorted(s for s in tab.sessions if tab.class_of[s] == 1)
    stage = {r["window_id"]: r["stage_group"] for r in inp.rows(
        "data/description/window_description_w30.csv", ["window_id", "stage_group", "keep"]) if r["keep"] == "1"}
    rule_sha = T.sha256_file(R.RULE)
    checks = dict(version=R.VERSION, freeze_2_sha256=freeze_2, rule_file_sha256=rule_sha,
                  libraries=T.library_versions(), n_tasks=len(tasks),
                  n_fits=sum(recs[R.key(t)]["n_fits"] for t in tasks),
                  compute_seconds=round(sum(recs[R.key(t)]["seconds"] for t in tasks), 1))

    # ---- check (a): the rerun's counts over all windows equal the frozen table
    frozen = {}
    with open(os.path.join(T.RESULTS, "tables", "T_chance_all_labelings.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            frozen[(r["configuration"], int(r["part"]), r["model"])] = (
                int(r["tp"]), int(r["fp"]), int(r["fn"]), int(r["tn"]), float(r["macro_f1"]), r["sessions_called_ai"])
    n_same = 0
    for t in tasks:
        r = recs[R.key(t)]
        fz = frozen[(r["configuration"], r["part"], r["model"])]
        n_same += int(fz[:4] == (r["tp"], r["fp"], r["fn"], r["tn"]) and abs(fz[4] - r["macro_f1"]) < 1e-6
                      and fz[5] == " ".join(r["ai_sessions"]))
    checks["a_counts_equal_frozen_table"] = dict(tasks=len(tasks), equal=n_same, result="PASS" if n_same == len(tasks) else "FAIL")
    # ---- check (b): every fit is the plumbed fit
    n_pl = sum(int(recs[R.key(t)]["matches_plumbing"]) for t in tasks)
    checks["b_fit_hash_equals_plumbing"] = dict(tasks=len(tasks), equal=n_pl, result="PASS" if n_pl == len(tasks) else "FAIL")
    # ---- the rule file every task ran under
    n_rule = sum(int(recs[R.key(t)]["rule_sha256"] == rule_sha) for t in tasks)
    checks["tasks_run_under_this_rule_file"] = dict(tasks=len(tasks), equal=n_rule, result="PASS" if n_rule == len(tasks) else "FAIL")

    true = {}
    for cfg in R.CONFIGS:
        for m in T.MODELS:
            v = [recs[R.key(("chance", cfg, part, m))] for part in range(R.N_PARTS)]
            tr = [x for x in v if x["is_true_labeling"]]
            if len(tr) != 1:
                raise SystemExit("STOP: the true labeling is not exactly one of the 126")
            true[(cfg, m)] = tr[0]

    # ---- check (c): the true labeling's stage-group values equal the frozen trial files and table
    frozen_stage = {}
    with open(os.path.join(T.RESULTS, "tables", "T_by_stage_group.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            frozen_stage[(r["trial"], r["model"], r["stage_group"])] = (
                None if r["macro_f1"] == "" else float(r["macro_f1"]), int(r["n_human"]), int(r["n_ai"]))
    c_ok, c_n = 0, 0
    for cfg in R.CONFIGS:
        for m in T.MODELS:
            doc = T.read_json(os.path.join(T.RESULTS, "trials", "%s__%s.json" % (cfg, m)))
            per = {}
            for p in doc["predictions"]:
                e = per.setdefault(p["session"], {}).setdefault(stage[p["window_id"]], [0, 0])
                e[0] += 1
                e[1] += p["called_ai"]
            c_n += 1
            good = per == true[(cfg, m)]["session_stage"]
            for g in T.STAGE_GROUPS:
                mf = macro(true[(cfg, m)]["stage"][g])
                fz = frozen_stage[(cfg, m, g)]
                tp, fp, fn, tn = true[(cfg, m)]["stage"][g]
                good = good and (fz[1], fz[2]) == (fp + tn, tp + fn) and (
                    (mf is None and fz[0] is None) or (mf is not None and fz[0] is not None and abs(mf - fz[0]) < 1e-6))
            c_ok += int(good)
    checks["c_true_labeling_equals_frozen_stage_results"] = dict(trials=c_n, equal=c_ok, result="PASS" if c_ok == c_n else "FAIL")

    # ---- the test (rule items 3 to 5) and what is reported beside it (item 6)
    rng = np.random.default_rng(T.SEED)                      # reading T14: the frozen draws
    H = rng.integers(0, len(humans), size=(T.N_BOOT, len(humans)))
    A = rng.integers(0, len(ais), size=(T.N_BOOT, len(ais)))
    rows, lrows, srows, res = [], [], [], {}
    for cfg in R.CONFIGS:
        for m in T.MODELS:
            tr = true[(cfg, m)]
            vals = [recs[R.key(("chance", cfg, part, m))] for part in range(R.N_PARTS)]
            for g in T.STAGE_GROUPS + ["all"]:
                conf = (lambda r: [r["tp"], r["fp"], r["fn"], r["tn"]]) if g == "all" else (lambda r: r["stage"][g])
                t = macro(conf(tr))
                f = [macro(conf(v)) for v in vals]
                defined = [x for x in f if x is not None]
                n_ge = sum(1 for x in defined if x >= t - 1e-12) if t is not None else None
                tp, fp, fn, tn = conf(tr)
                n_h, n_a = fp + tn, tp + fn
                counts = stage_counts(tr, g)
                b = S.boot_macro(counts, humans, ais, H, A)
                lo, hi = S.interval(b)
                hn = np.array([counts.get(s, dict(n=0))["n"] for s in humans])
                an = np.array([counts.get(s, dict(n=0))["n"] for s in ais])
                small = float(((hn[H].sum(axis=1) < 10) | (an[A].sum(axis=1) < 10)).mean())
                per_h = {s: counts[s]["n"] for s in humans if counts.get(s, dict(n=0))["n"]}
                per_a = {s: counts[s]["n"] for s in ais if counts.get(s, dict(n=0))["n"]}
                big = max(per_a.items(), key=lambda kv: (kv[1], kv[0])) if per_a else ("", 0)
                under = g in RULE_GROUPS
                all_defined = len(defined) == R.N_PARTS
                if under and not all_defined:
                    raise SystemExit("STOP: a relabeling has one class only in a stage group under the rule")
                p = (n_ge / float(R.N_PARTS)) if (all_defined and t is not None) else None
                res[(cfg, m, g)] = dict(true=t, p=p, n_ge=n_ge, lo=lo, hi=hi, n_h=n_h, n_a=n_a, small=small,
                                        defined=len(defined), med=float(np.median(defined)) if defined else None,
                                        ai_sessions=len(per_a), human_sessions=len(per_h),
                                        big=big[0], big_share=(big[1] / float(n_a)) if n_a else None)
                rows.append([cfg, m, g, int(under), int(min(n_h, n_a) < 10), n_h, n_a, len(per_h), len(per_a), big[0],
                             (big[1] / float(n_a)) if n_a else None, t, lo, hi, small, len(defined),
                             min(defined) if defined else None, float(np.median(defined)) if defined else None,
                             max(defined) if defined else None, n_ge, p,
                             None if p is None else int(p <= ALPHA)])
                if g != "all":
                    for v in vals:
                        c = conf(v)
                        lrows.append([cfg, v["part"], " ".join(v["ai_sessions"]), int(v["is_true_labeling"]), m, g,
                                      macro(c), c[0], c[1], c[2], c[3]])
                    for s in humans + ais:
                        n, called = counts.get(s, dict(n=0, called=0))["n"], counts.get(s, dict(n=0, called=0))["called"]
                        srows.append([cfg, m, g, s, "ai" if tab.class_of[s] else "human", n, called,
                                      (called / float(n)) if n else None])
    table("T_h2_stage_chance.csv", [
        "configuration", "model", "stage_group", "under_rule", "indicative", "n_human", "n_ai", "human_sessions",
        "ai_sessions", "ai_largest_session", "ai_largest_share", "true_labeling_macro_f1", "ci_low", "ci_high",
        "resamples_under_10_windows_of_a_class", "relabelings_with_both_classes", "min_of_relabelings",
        "median_of_relabelings", "max_of_relabelings", "labelings_at_or_above_true", "p", "p_at_or_below_0.05"], rows)
    table("T_h2_stage_all_labelings.csv", ["configuration", "part", "sessions_called_ai", "is_true_labeling", "model",
                                           "stage_group", "macro_f1", "tp", "fp", "fn", "tn"], lrows)
    table("T_h2_stage_by_session.csv", ["configuration", "model", "stage_group", "session", "class", "windows",
                                        "called_ai", "share_called_ai"], srows)

    # ---- check: the pooled row reproduces the frozen chance baseline and the frozen interval
    fz_base, fz_main = {}, {}
    with open(os.path.join(T.RESULTS, "tables", "T_chance_baseline.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fz_base[(r["configuration"], r["model"])] = (float(r["true_labeling_macro_f1"]), int(r["labelings_at_or_above_true"]))
    with open(os.path.join(T.RESULTS, "tables", "T_configurations.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["trial"] in R.CONFIGS:
                fz_main[(r["trial"], r["model"])] = (float(r["ci_low"]), float(r["ci_high"]))
    pool_ok = all(abs(res[(c, m, "all")]["true"] - fz_base[(c, m)][0]) < 1e-6 and res[(c, m, "all")]["n_ge"] == fz_base[(c, m)][1]
                  for c in R.CONFIGS for m in T.MODELS)
    ci_ok = all(abs(res[(c, m, "all")]["lo"] - fz_main[(c, m)][0]) < 1e-6 and abs(res[(c, m, "all")]["hi"] - fz_main[(c, m)][1]) < 1e-6
                for c in R.CONFIGS for m in T.MODELS)
    checks["pooled_row_equals_frozen_chance_baseline"] = "PASS" if pool_ok else "FAIL"
    checks["pooled_interval_equals_frozen_interval"] = "PASS" if ci_ok else "FAIL"

    # ---- verdict (rule item 5)
    vrows, verdict = [], {}
    for cfg in R.CONFIGS:
        meets = {}
        for m in T.MODELS:
            ps = [res[(cfg, m, g)]["p"] for g in RULE_GROUPS]
            meets[m] = all(p is not None and p <= ALPHA for p in ps)
            vrows.append([cfg, m] + ps + [max(ps), int(meets[m])])
        verdict[cfg] = dict(classifiers_meeting_the_rule=sum(meets.values()), needed=NEED,
                            supported=sum(meets.values()) >= NEED, by_classifier=meets)
    table("T_h2_verdict.csv", ["configuration", "model", "p_stages_1-4", "p_stage_5", "p_stage_7", "largest_p",
                               "meets_rule"], vrows)
    checks["verdict"] = dict(rule="p <= 0.05 in stage groups 1-4, 5 and 7, for at least 3 of the 5 classifiers, "
                                  "main configuration", H2_supported=verdict["main"]["supported"],
                             main=verdict["main"], no_command_content_reported_beside=verdict["no_command_content"])

    # ---- the summary a person reads
    L = []
    L.append("# Study 3, H2 (ATT&CK stage groups): results\n")
    L.append("Written by `code/h2_stage/summarize_h2_stage.py`. Post hoc: the rule is in `H2_RULE_BEFORE_RUN.md` "
             "(SHA-256 `%s`), written after the trials were scored and before these numbers existed. Freeze 2 SHA-256 "
             "`%s`. The frozen trial code is run unchanged.\n" % (rule_sha, freeze_2))
    for cfg in R.CONFIGS:
        L.append("## %s: macro-F1 within the stage group (p against the 126 relabelings)\n" % CFG_LABEL[cfg])
        L.append("| Stage group | Human windows | AI windows | " + " | ".join(T.MODEL_LABEL[m] for m in T.MODELS) + " |")
        L.append("|---|---|---|" + "---|" * len(T.MODELS))
        for g in T.STAGE_GROUPS + ["all"]:
            r0 = res[(cfg, "lr", g)]
            cells = []
            for m in T.MODELS:
                x = res[(cfg, m, g)]
                cells.append("%s (%s)" % (f3(x["true"]), "no p" if x["p"] is None else "p = %s, %d of 126" % (f3(x["p"]), x["n_ge"])))
            L.append("| %s | %d (%d sessions) | %d (%d sessions; largest %s, %s) | " % (
                STAGE_LABEL[g], r0["n_h"], r0["human_sessions"], r0["n_a"], r0["ai_sessions"], r0["big"],
                f3(r0["big_share"])) + " | ".join(cells) + " |")
        v = verdict[cfg]
        L.append("\nClassifiers with p of 0.05 or below in all three stage groups under the rule: **%d of 5** (%s).\n" % (
            v["classifiers_meeting_the_rule"], ", ".join(T.MODEL_LABEL[m] for m in T.MODELS if v["by_classifier"][m]) or "none"))
        L.append("### 95% intervals, median of the relabelings\n")
        L.append("| Stage group | " + " | ".join(T.MODEL_LABEL[m] for m in T.MODELS) + " | Resamples with under 10 windows of a class |")
        L.append("|---|" + "---|" * len(T.MODELS) + "---|")
        for g in T.STAGE_GROUPS + ["all"]:
            L.append("| %s | " % STAGE_LABEL[g] + " | ".join(
                "%s to %s; median %s" % (f3(res[(cfg, m, g)]["lo"]), f3(res[(cfg, m, g)]["hi"]), f3(res[(cfg, m, g)]["med"]))
                for m in T.MODELS) + " | %.1f%% |" % (100 * res[(cfg, "lr", g)]["small"]))
        L.append("")
    L.append("## Outcome under the rule\n")
    L.append("**H2 is %s:** %d of the 5 classifiers have p of 0.05 or below in all three stage groups, main "
             "configuration; the rule asks for at least 3. Without command content (reported beside the rule): %d of 5.\n" % (
                 "supported" if verdict["main"]["supported"] else "not supported by this data",
                 verdict["main"]["classifiers_meeting_the_rule"],
                 verdict["no_command_content"]["classifiers_meeting_the_rule"]))
    T.write_once(os.path.join(R.OUT, "H2_STAGE_SUMMARY.md"), "\n".join(L) + "\n", overwrite=True)

    checks["d_freeze_1_after"] = freeze_1_check()
    checks["d_freeze_2_after"] = T.check_freeze_2(kinds=R.ALL_KINDS)
    checks["leak_audit"] = leak_audit(set(humans + ais), skip=("h2_stage_checks.json",))
    checks["inputs_opened"] = inp.opened
    files = {}
    for top in (TABLES, HERE):
        for n in sorted(os.listdir(top)):
            if n.endswith((".csv", ".py", ".md")):
                files[os.path.relpath(os.path.join(top, n), T.ROOT).replace(os.sep, "/")] = T.sha256_file(os.path.join(top, n))
    for n in ("H2_STAGE_SUMMARY.md", "H2_RULE_BEFORE_RUN.md"):
        files["results_h2_stage/" + n] = T.sha256_file(os.path.join(R.OUT, n))
    checks["files"] = files
    T.write_once(os.path.join(R.OUT, "h2_stage_checks.json"), T.dump_json(checks), overwrite=True)
    for k in ("a_counts_equal_frozen_table", "b_fit_hash_equals_plumbing", "tasks_run_under_this_rule_file",
              "c_true_labeling_equals_frozen_stage_results"):
        print(k, checks[k]["result"], checks[k].get("equal"))
    print("pooled row:", checks["pooled_row_equals_frozen_chance_baseline"], "| pooled interval:",
          checks["pooled_interval_equals_frozen_interval"], "| freeze 1 changed:", checks["d_freeze_1_after"]["changed"],
          "| leak audit:", checks["leak_audit"]["result"])
    print("COMPLETE: tables in results_h2_stage/tables, summary in results_h2_stage/H2_STAGE_SUMMARY.md")


if __name__ == "__main__":
    main()
