"""Study 3 trials: the tables of design section 11, from the scored predictions.

    python3 -I -B code/trials/summarize.py

Nothing is fitted here. Every number is computed from the held-out predictions that
the scored run wrote once into results/trials/ and from the chance-baseline records in
results/parts/. A rerun gives the same bytes.
"""
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import trial_common as T
import run_trials as R

np = T.np
TABLES = os.path.join(T.RESULTS, "tables")
LOSO_ORDER = list(T.LOSO_TRIALS)
TRIAL_LABEL = {
    "main": "Main", "no_command_content": "No command content", "no_context": "No context",
    "input_channel": "Input channel", "h1_without": "Main without the four H1 columns",
    "h1_window_form": "H1 window form re-added", "h1_lookback_form": "H1 look-back form re-added",
    "w60_main": "Main, 60 s windows", "input_bearing_main": "Main, input-bearing windows",
    "inside_main": "Inside sessions, main"}


def table(name, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else (repr(round(v, 6)) if isinstance(v, float) else v) for v in r])
    T.write_once(os.path.join(TABLES, name), buf.getvalue(), overwrite=True)


def f3(x):
    return "n/a" if x is None else "%.3f" % x


def full_metrics(preds):
    y = np.array([p["y"] for p in preds], dtype=int)
    p = np.array([p["p_ai"] for p in preds], dtype=float)
    c = np.array([p["called_ai"] for p in preds], dtype=int)
    tp, fp, fn, tn = T.confusion(y, c)
    m = T.f1_parts(tp, fp, fn, tn)
    m.update(n_human=int((y == 0).sum()), n_ai=int((y == 1).sum()), tp=tp, fp=fp, fn=fn, tn=tn,
             brier=float(np.mean((p - y) ** 2)) if len(y) else None, roc_auc=None, pr_auc=None)
    if m["n_human"] and m["n_ai"]:
        from sklearn.metrics import average_precision_score, roc_auc_score
        m["roc_auc"] = float(roc_auc_score(y, p))
        m["pr_auc"] = float(average_precision_score(y, p))          # T15
    else:
        for k in ("macro_f1", "balanced_accuracy"):
            m[k] = None                                             # one class only
    return m


def session_counts(preds):
    d = {}
    for p in preds:
        e = d.setdefault(p["session"], dict(n=0, called=0, y=p["y"], p_sum=0.0))
        e["n"] += 1
        e["called"] += p["called_ai"]
        e["p_sum"] += p["p_ai"]
    return d


def boot_macro(counts, humans, ais, H, A):
    zero = dict(n=0, called=0)               # a session with no row in this trial
    hn = np.array([counts.get(s, zero)["n"] for s in humans])
    hc = np.array([counts.get(s, zero)["called"] for s in humans])
    an = np.array([counts.get(s, zero)["n"] for s in ais])
    ac = np.array([counts.get(s, zero)["called"] for s in ais])
    fp = hc[H].sum(axis=1)
    tn = (hn - hc)[H].sum(axis=1)
    tp = ac[A].sum(axis=1)
    fn = (an - ac)[A].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        f_ai = np.where(2 * tp + fp + fn > 0, 2 * tp / (2 * tp + fp + fn), 0.0)
        f_h = np.where(2 * tn + fn + fp > 0, 2 * tn / (2 * tn + fn + fp), 0.0)
    return (f_ai + f_h) / 2.0


def interval(v):
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def holm(ps):
    m = len(ps)
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(sorted(range(m), key=lambda i: ps[i])):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adj[i] = running
    return adj


def one_sided_p(diffs):
    """T4: share of the resamples in which the difference is zero or below, with one added
    to both counts."""
    return float((1 + int((diffs <= 0).sum())) / (len(diffs) + 1))


def leak_audit(labels):
    sys.path.insert(0, T.CODE)
    import s3_clean as K
    hits, label_count, searched = [], {}, 0
    for dirpath, dirs, names in os.walk(T.RESULTS):
        dirs.sort()
        for n in sorted(names):
            if not n.endswith((".json", ".jsonl", ".csv", ".md")) or n == "summary.json":
                continue
            rel = os.path.relpath(os.path.join(dirpath, n), T.RESULTS).replace(os.sep, "/")
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
    freeze_sha = T.check_freeze_2()
    inp = T.Inputs("scored")
    recs = R.all_records("scored")
    left = [R.key(t) for t in R.all_tasks()
            if R.key(t) not in recs and not (t[0] != "chance" and os.path.exists(R.result_path(t[1], t[3])))]
    if left:
        raise SystemExit("INCOMPLETE: %d scored tasks left" % len(left))
    trials = {}
    for name in LOSO_ORDER + list(T.INSIDE_TRIALS):
        for m in T.MODELS:
            trials[(name, m)] = T.read_json(R.result_path(name, m))
    main_preds = trials[("main", "lr")]["predictions"]
    cls = {p["session"]: p["y"] for p in main_preds}
    humans = sorted(s for s in cls if cls[s] == 0)
    ais = sorted(s for s in cls if cls[s] == 1)
    rng = np.random.default_rng(T.SEED)                      # T14: one set of draws for everything
    H = rng.integers(0, len(humans), size=(T.N_BOOT, len(humans)))
    A = rng.integers(0, len(ais), size=(T.N_BOOT, len(ais)))
    boot, met, counts = {}, {}, {}
    for k, doc in trials.items():
        counts[k] = session_counts(doc["predictions"])
        met[k] = full_metrics(doc["predictions"])
        boot[k] = boot_macro(counts[k], humans, ais, H, A)
    checks = dict(freeze_2_sha256=freeze_sha, trial_version=T.TRIAL_VERSION,
                  libraries=T.library_versions(),
                  scored_fits_equal_plumbing_fits=all(d["matches_plumbing"] for d in trials.values())
                  and all(r["matches_plumbing"] for r in recs.values()),
                  n_trial_files=len(trials), bootstrap_resamples=T.N_BOOT, seed=T.SEED)

    # ---- main table and configurations (sections 7.2, 5, 7.7)
    head = ["trial", "model", "window", "n_columns", "n_human", "n_ai", "macro_f1", "ci_low", "ci_high",
            "above_reference_0.809", "f1_ai", "precision_ai", "recall_ai", "f1_human", "precision_human",
            "recall_human", "balanced_accuracy", "roc_auc", "pr_auc", "brier", "tp", "fp", "fn", "tn"]
    rows = []
    for name in LOSO_ORDER + list(T.INSIDE_TRIALS):
        for m in T.MODELS:
            k = (name, m)
            lo, hi = interval(boot[k])
            x = met[k]
            rows.append([name, m, trials[k]["window"], trials[k]["n_columns"], x["n_human"], x["n_ai"],
                         x["macro_f1"], lo, hi, int(x["macro_f1"] > T.REFERENCE_MACRO_F1),
                         x["f1_ai"], x["precision_ai"], x["recall_ai"], x["f1_human"], x["precision_human"],
                         x["recall_human"], x["balanced_accuracy"], x["roc_auc"], x["pr_auc"], x["brier"],
                         x["tp"], x["fp"], x["fn"], x["tn"]])
    table("T_main.csv", head, [r for r in rows if r[0] == "main"])
    table("T_configurations.csv", head, [r for r in rows if r[0] in LOSO_ORDER])
    table("T_inside_sessions.csv", head, [r for r in rows if r[0] in T.INSIDE_TRIALS])
    all_rows = {(r[0], r[1]): r for r in rows}

    # ---- by session (section 7.3)
    srows = []
    for name in LOSO_ORDER:
        for m in T.MODELS:
            c = counts[(name, m)]
            for s in humans + ais:
                score = c[s]["p_sum"] / c[s]["n"]
                reads = int(score >= T.SESSION_AI_LINE)
                srows.append([name, m, s, "ai" if cls[s] else "human", c[s]["n"], score,
                              c[s]["called"] / c[s]["n"], "ai" if reads else "human", int(reads == cls[s])])
    table("T_by_session.csv", ["trial", "model", "session", "class", "kept_windows", "session_score",
                               "share_called_ai", "reads_as", "read_correctly"], srows)

    # ---- by stage group (section 7.5); the stage is joined to the predictions here only (T13)
    stage = {}
    for w in ("w30", "w60"):
        for r in inp.rows("data/description/window_description_%s.csv" % w, ["window_id", "stage_group", "keep"]):
            if r["keep"] == "1":
                stage[(w, r["window_id"])] = r["stage_group"]
    grows = []
    for name in LOSO_ORDER:
        for m in T.MODELS:
            doc = trials[(name, m)]
            for g in T.STAGE_GROUPS:
                sub = [p for p in doc["predictions"] if stage[(doc["window"], p["window_id"])] == g]
                x = full_metrics(sub)
                extra = []
                for c in (0, 1):
                    per = {}
                    for p in sub:
                        if p["y"] == c:
                            per[p["session"]] = per.get(p["session"], 0) + 1
                    big = max(per.items(), key=lambda kv: (kv[1], kv[0])) if per else ("", 0)
                    extra += [len(per), big[0], (big[1] / sum(per.values())) if per else None]
                grows.append([name, m, g, x["n_human"], x["n_ai"]] + extra +
                             [int(min(x["n_human"], x["n_ai"]) < 10), x["macro_f1"], x["f1_ai"], x["precision_ai"],
                              x["recall_ai"], x["f1_human"], x["precision_human"], x["recall_human"],
                              x["balanced_accuracy"], x["roc_auc"], x["pr_auc"], x["brier"]])
    ghead = ["trial", "model", "stage_group", "n_human", "n_ai", "human_sessions", "human_largest_session",
             "human_largest_share", "ai_sessions", "ai_largest_session", "ai_largest_share", "indicative",
             "macro_f1", "f1_ai", "precision_ai", "recall_ai", "f1_human", "precision_human", "recall_human",
             "balanced_accuracy", "roc_auc", "pr_auc", "brier"]
    table("T_by_stage_group.csv", ghead, grows)

    # ---- chance baseline (section 8, control 2)
    crows, chance, lrows = [], {}, []
    for cfg in T.CHANCE_CONFIGS:
        for m in T.MODELS:
            vals = [recs["chance|%s|%d|%s" % (cfg, part, m)] for part in range(R.N_PARTS)]
            true = [v for v in vals if v["is_true_labeling"]]
            if len(true) != 1:
                raise SystemExit("STOP: the true labeling is not exactly one of the 126")
            f = np.array([v["macro_f1"] for v in vals])
            t = true[0]["macro_f1"]
            same = abs(t - met[(cfg, m)]["macro_f1"]) < 1e-12
            n_ge = int((f >= t - 1e-12).sum())
            chance[(cfg, m)] = dict(true=t, p=n_ge / float(R.N_PARTS), n_ge=n_ge, same=same)
            crows.append([cfg, m, t, float(f.min()), float(np.median(f)), float(f.max()), n_ge, n_ge / float(R.N_PARTS),
                          int(same)])
            for v in vals:
                lrows.append([cfg, v["part"], " ".join(v["ai_sessions"]), int(v["is_true_labeling"]), m,
                              v["macro_f1"], v["tp"], v["fp"], v["fn"], v["tn"]])
    table("T_chance_baseline.csv", ["configuration", "model", "true_labeling_macro_f1", "min_of_126",
                                    "median_of_126", "max_of_126", "labelings_at_or_above_true", "p",
                                    "true_labeling_equals_trial"], crows)
    table("T_chance_all_labelings.csv", ["configuration", "part", "sessions_called_ai", "is_true_labeling",
                                         "model", "macro_f1", "tp", "fp", "fn", "tn"], lrows)
    checks["true_labeling_of_chance_equals_trial"] = all(v["same"] for v in chance.values())

    # ---- hypotheses (section 9)
    hrows = []
    h1 = {}
    for form, minus in (("four_columns", "main"), ("window_form", "h1_window_form"),
                        ("lookback_form", "h1_lookback_form")):
        ps = []
        for m in T.MODELS:
            d = boot[(minus, m)] - boot[("h1_without", m)]
            point = met[(minus, m)]["macro_f1"] - met[("h1_without", m)]["macro_f1"]
            h1[(form, m)] = [point, interval(d), one_sided_p(d)]
            ps.append(h1[(form, m)][2])
        for m, a in zip(T.MODELS, holm(ps)):
            h1[(form, m)].append(a)
            x = h1[(form, m)]
            hrows.append(["H1", form, m, "gain over main without the four H1 columns", x[0], x[1][0], x[1][1],
                          x[2], x[3], int(x[3] <= 0.05 and x[0] > 0)])
    h1_n = sum(1 for m in T.MODELS if h1[("four_columns", m)][3] <= 0.05 and h1[("four_columns", m)][0] > 0)
    for cfg in T.CHANCE_CONFIGS:
        c = chance[(cfg, "lr")]
        hrows.append(["H2", cfg, "lr", "true labeling against the 126 relabelings", c["true"], None, None,
                      c["p"], None, int(c["p"] <= 0.05)])
    others = [m for m in T.MODELS if m != "rf"]
    h3 = {}
    for m in others:
        d = boot[("main", "rf")] - boot[("main", m)]
        h3[m] = [met[("main", "rf")]["macro_f1"] - met[("main", m)]["macro_f1"], interval(d), one_sided_p(d)]
    for m, a in zip(others, holm([h3[m][2] for m in others])):
        h3[m].append(a)
        hrows.append(["H3", "main", m, "random forest minus this model", h3[m][0], h3[m][1][0], h3[m][1][1],
                      h3[m][2], a, int(a <= 0.05 and h3[m][0] > 0)])
    rf_highest = all(met[("main", "rf")]["macro_f1"] > met[("main", m)]["macro_f1"] for m in others)
    verdict = dict(
        H1=dict(models_with_gain_above_zero_after_holm=h1_n, supported=h1_n >= 3),
        H2=dict(p_main=chance[("main", "lr")]["p"], p_no_command_content=chance[("no_command_content", "lr")]["p"],
                supported=chance[("main", "lr")]["p"] <= 0.05),
        H3=dict(random_forest_is_highest=rf_highest,
                differences_above_zero_after_holm=sum(1 for m in others if h3[m][3] <= 0.05 and h3[m][0] > 0),
                supported=rf_highest and all(h3[m][3] <= 0.05 and h3[m][0] > 0 for m in others)))
    table("T_hypotheses.csv", ["hypothesis", "item", "model", "quantity", "value", "ci_low", "ci_high",
                               "p", "holm_p", "meets_rule"], hrows)

    # ---- the summary a person reads
    L = []
    L.append("# Study 3 trials: results\n")
    L.append("Written by `code/trials/summarize.py` from the scored predictions. Freeze 2 SHA-256 `%s`. "
             "Trial code %s. Every interval is a 95%% percentile interval from %d resamples of whole sessions "
             "within each class.\n" % (freeze_sha, T.TRIAL_VERSION, T.N_BOOT))
    L.append("## Main result: held-out-session macro-F1, main configuration (30 s, 40 columns)\n")
    L.append("| Model | Macro-F1 | 95% interval | Above 0.809 | F1 AI | Precision AI | Recall AI | F1 human | "
             "Balanced accuracy | ROC-AUC | PR-AUC | Brier |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in T.MODELS:
        r = all_rows[("main", m)]
        L.append("| %s | %s | %s to %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            T.MODEL_LABEL[m], f3(r[6]), f3(r[7]), f3(r[8]), "yes" if r[9] else "no", f3(r[10]), f3(r[11]),
            f3(r[12]), f3(r[13]), f3(r[16]), f3(r[17]), f3(r[18]), f3(r[19])))
    x = met[("main", "lr")]
    L.append("\nWindows scored: %d human and %d AI, each once, by models that never saw its session.\n"
             % (x["n_human"], x["n_ai"]))
    L.append("## Configurations and sensitivities: macro-F1 with its interval\n")
    L.append("| Trial | Columns | Windows | " + " | ".join(T.MODEL_LABEL[m] for m in T.MODELS) + " |")
    L.append("|---|---|---|" + "---|" * len(T.MODELS))
    for name in LOSO_ORDER + list(T.INSIDE_TRIALS):
        r0 = all_rows[(name, "lr")]
        L.append("| %s | %d | %d | " % (TRIAL_LABEL[name], r0[3], r0[4] + r0[5]) + " | ".join(
            "%s (%s to %s)" % (f3(all_rows[(name, m)][6]), f3(all_rows[(name, m)][7]), f3(all_rows[(name, m)][8]))
            for m in T.MODELS) + " |")
    L.append("\nThe inside-sessions row is the within-session evaluation of section 7.6: later minutes of "
             "sessions whose earlier minutes were in training.\n")
    L.append("## By session, main configuration: session score (share of windows called AI)\n")
    L.append("| Session | Class | Kept windows | " + " | ".join(T.MODEL_LABEL[m] for m in T.MODELS) + " |")
    L.append("|---|---|---|" + "---|" * len(T.MODELS))
    for s in humans + ais:
        cells = []
        for m in T.MODELS:
            c = counts[("main", m)][s]
            cells.append("%s (%s)" % (f3(c["p_sum"] / c["n"]), f3(c["called"] / c["n"])))
        L.append("| %s | %s | %d | " % (s, "AI" if cls[s] else "human", counts[("main", "lr")][s]["n"])
                 + " | ".join(cells) + " |")
    L.append("\nA session reads as AI when its session score is 0.5 or above.\n")
    for name in ("main", "no_command_content"):
        L.append("## By stage group, %s: macro-F1 (ROC-AUC)\n" % TRIAL_LABEL[name].lower())
        L.append("| Stage group | Human windows | AI windows | " + " | ".join(T.MODEL_LABEL[m] for m in T.MODELS) + " |")
        L.append("|---|---|---|" + "---|" * len(T.MODELS))
        for g in T.STAGE_GROUPS:
            gr = {r[1]: r for r in grows if r[0] == name and r[2] == g}
            r0 = gr["lr"]
            L.append("| %s%s | %d (%d sessions, largest %s %s) | %d (%d sessions, largest %s %s) | " % (
                g, " (indicative)" if r0[11] else "", r0[3], r0[5], r0[6], f3(r0[7]), r0[4], r0[8], r0[9], f3(r0[10]))
                + " | ".join("%s (%s)" % (f3(gr[m][12]), f3(gr[m][20])) for m in T.MODELS) + " |")
        L.append("")
    L.append("## Chance baseline: every way of calling 4 of the 9 sessions AI (126)\n")
    L.append("| Configuration | Model | True labeling | Lowest | Median | Highest | At or above true | p |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in crows:
        L.append("| %s | %s | %s | %s | %s | %s | %d of 126 | %s |" % (
            TRIAL_LABEL[r[0]], T.MODEL_LABEL[r[1]], f3(r[2]), f3(r[3]), f3(r[4]), f3(r[5]), r[6], f3(r[7])))
    L.append("\n## Hypotheses\n")
    L.append("| | Item | Model | Value | 95% interval | p | Holm p | Meets rule |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in hrows:
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r[0], r[1], T.MODEL_LABEL[r[2]], ("%+.3f" % r[4]) if r[0] != "H2" else f3(r[4]),
            "" if r[5] is None else "%+.3f to %+.3f" % (r[5], r[6]), f3(r[7]),
            "" if r[8] is None else f3(r[8]), "yes" if r[9] else "no"))
    L.append("")
    L.append("- **H1** (the four columns improve classification): the gain is above zero after Holm in %d of 5 "
             "models. The rule asks for at least 3. **%s.**" % (h1_n, "Supported" if verdict["H1"]["supported"]
                                                               else "Not supported by this data"))
    L.append("- **H2** (logistic regression against chance): p = %s in the main configuration and %s without "
             "command content. The rule is p of 0.05 or below. **%s.**" % (
                 f3(verdict["H2"]["p_main"]), f3(verdict["H2"]["p_no_command_content"]),
                 "Supported" if verdict["H2"]["supported"] else "Not supported by this data"))
    L.append("- **H3** (random forest above the other four): random forest %s the highest; %d of 4 differences "
             "are above zero after Holm. **%s.**" % (
                 "is" if rf_highest else "is not", verdict["H3"]["differences_above_zero_after_holm"],
                 "Supported" if verdict["H3"]["supported"] else "Not supported by this data"))
    L.append("\nWith nine sessions these tests have little power. A result that does not reach its rule is "
             "not evidence of no difference.\n")
    T.write_once(os.path.join(T.RESULTS, "RESULTS_SUMMARY.md"), "\n".join(L) + "\n", overwrite=True)

    checks["hypotheses"] = verdict
    checks["leak_audit_of_results"] = leak_audit(set(humans + ais))
    checks["inputs_opened"] = inp.opened
    T.write_once(os.path.join(T.RESULTS, "summary.json"), T.dump_json(checks), overwrite=True)
    print("fits equal the plumbing run:", checks["scored_fits_equal_plumbing_fits"],
          "| chance true labeling equals trial:", checks["true_labeling_of_chance_equals_trial"],
          "| leak audit:", checks["leak_audit_of_results"]["result"])
    print("COMPLETE: tables in results/tables, summary in results/RESULTS_SUMMARY.md")


if __name__ == "__main__":
    main()
