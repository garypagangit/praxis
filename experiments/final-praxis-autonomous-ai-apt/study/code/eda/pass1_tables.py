"""EDA Pass 1, tables (handoff section 5): T1, T2, T3 and the tables the figures are drawn from.

Reads design columns only (handoff rule 3): for each window its session, login order,
elapsed working time, stage group, kept flag and split. No feature value, no record
count of a window, no command text and no terminal text is read. Class comes from the
session table, never from a per-window label file.

Counts for T1 are taken from the step reports, not recounted. Every count that can be
checked against a step report or the split file is checked, and the run stops on a
mismatch (handoff section 10, check 1).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import eda_common as E

PASS1_INPUTS = [
    "reports/05_windows_report.json",
    "reports/06_split_report.json",
    "reports/08_summary.json",
    "data/labels/sessions.csv",
    "data/description/sessions.csv",
    "data/description/stage_acceptances.csv",
    "data/description/window_description_w30.csv",
    "data/description/window_description_w60.csv",
    "data/splits/splits_w30.csv",
    "data/splits/splits_w60.csv",
]
WINDOW_COLUMNS = ["window_id", "session_key", "login_order", "elapsed_working_s", "stage_group", "keep"]
SPLIT_COLUMNS = ["window_id", "session_key", "split"]
ACCEPT_COLUMNS = ["session_key", "stage", "in_used_login", "elapsed_working_s"]
LENGTHS = [("w30", 30), ("w60", 60)]
MAX_GRID_COLUMNS = 60          # handoff E3: above this, 10-minute bins for all sessions


def main():
    inp = E.Inputs(PASS1_INPUTS)
    sessions, rep05 = E.session_table(inp)
    rep06 = inp.read_json("reports/06_split_report.json")
    rep08 = inp.read_json("reports/08_summary.json")
    by_key = {s["session_key"]: s for s in sessions}
    sum08 = {r["session"]: r for r in rep08["sessions"]}
    checks = []

    def check(name, expected, found):
        checks.append({"check": name, "expected": expected, "found": found, "ok": expected == found})

    # ---------------------------------------------------------------- read the design columns
    windows, splits = {}, {}
    for wl, _ in LENGTHS:
        rows = inp.read_csv("data/description/window_description_%s.csv" % wl, WINDOW_COLUMNS)
        for r in rows:
            r["keep"] = int(r["keep"])
            r["elapsed_working_s"] = float(r["elapsed_working_s"])
        windows[wl] = rows
        splits[wl] = inp.read_csv("data/splits/splits_%s.csv" % wl, SPLIT_COLUMNS)

    kept = {}                     # kept[wl][session_key][stage_group] -> windows
    all_windows = {}              # all_windows[wl][session_key] -> windows, kept or not
    for wl, _ in LENGTHS:
        kept[wl] = {s["session_key"]: {g: 0 for g in E.STAGE_GROUPS} for s in sessions}
        all_windows[wl] = {s["session_key"]: 0 for s in sessions}
        for r in windows[wl]:
            all_windows[wl][r["session_key"]] += 1
            if r["keep"]:
                kept[wl][r["session_key"]][r["stage_group"]] += 1

    def kept_total(wl, key):
        return sum(kept[wl][key].values())

    # ---------------------------------------------------------------- counts in the step reports
    rep05_sum = {}
    for label, v in rep05["sessions"].items():
        d = {}
        for wl, _ in LENGTHS:
            logins = v["logins"].values()
            d[wl] = {
                "windows": sum(l[wl]["windows"] for l in logins),
                "kept": sum(l[wl]["kept"] for l in logins),
                "kept_before_rules": sum(l[wl]["kept_before_rules"] for l in logins),
                "by_group": {g: sum(l[wl]["kept_by_stage_group"][g] for l in logins) for g in E.STAGE_GROUPS},
            }
        rep05_sum[label] = d

    for s in sessions:
        lab, key, r8 = s["session"], s["session_key"], sum08[s["session"]]
        check("%s class: session table = summary report" % lab, r8["cls"], s["class"])
        check("%s lab range: description = summary report" % lab, r8["lab_range"], s["lab_range"])
        check("%s logins used: description = summary report" % lab, r8["logins_used"], s["logins_used"])
        check("%s records: package = set aside + dropped at routing + classifier input" % lab,
              r8["package_records"], r8["set_aside"] + r8["dropped_at_route"] + r8["classifier_input"])
        check("%s records: classifier input = cleaned + dropped in cleaning + dropped with validator commands" % lab,
              r8["classifier_input"],
              r8["cleaned_recorder"] + r8["cleaned_audit"] + r8["dropped_at_clean"] + r8["dropped_validator"])
        check("%s kept 30 s windows: summary report = windows report" % lab, r8["w30_kept"], rep05_sum[lab]["w30"]["kept"])
        check("%s all 30 s windows: summary report = windows report" % lab, r8["w30_windows"], rep05_sum[lab]["w30"]["windows"])
        for wl, _ in LENGTHS:
            check("%s %s kept windows: windows report = description file" % (lab, wl),
                  rep05_sum[lab][wl]["kept"], kept_total(wl, key))
            check("%s %s all windows: windows report = description file" % (lab, wl),
                  rep05_sum[lab][wl]["windows"], all_windows[wl][key])
            check("%s %s kept windows by stage group: windows report = description file" % (lab, wl),
                  rep05_sum[lab][wl]["by_group"], kept[wl][key])

    for wl, _ in LENGTHS:
        tot = rep08["totals_" + wl]
        for c in E.CLASSES:
            keys = [s["session_key"] for s in sessions if s["class"] == c]
            check("%s %s kept windows: summary report = description file" % (c, wl),
                  tot[c]["kept"], sum(kept_total(wl, k) for k in keys))
            check("%s %s kept windows by stage group: summary report = description file" % (c, wl),
                  tot[c]["by_stage_group"], {g: sum(kept[wl][k][g] for k in keys) for g in E.STAGE_GROUPS})

    # ---------------------------------------------------------------- split counts
    split_counts = {}             # split_counts[wl][session_key][split]
    for wl, _ in LENGTHS:
        kept_ids = set(r["window_id"] for r in windows[wl] if r["keep"])
        split_ids = [r["window_id"] for r in splits[wl]]
        check("%s split file: one row for every kept window, no other row" % wl,
              [len(kept_ids), True], [len(split_ids), set(split_ids) == kept_ids and len(set(split_ids)) == len(split_ids)])
        found_values = sorted(set(r["split"] for r in splits[wl]))
        check("%s split file: split values" % wl, sorted(E.SPLITS), found_values)
        split_counts[wl] = {s["session_key"]: {v: 0 for v in E.SPLITS} for s in sessions}
        for r in splits[wl]:
            split_counts[wl][r["session_key"]][r["split"]] += 1
        for s in sessions:
            check("%s %s split counts: split report = split file" % (s["session"], wl),
                  rep06["lengths"][wl]["by_session"][s["session_key"]], split_counts[wl][s["session_key"]])
        for c in E.CLASSES:
            keys = [s["session_key"] for s in sessions if s["class"] == c]
            found = {v: sum(split_counts[wl][k][v] for k in keys) for v in E.SPLITS}
            check("%s %s split counts: summary report = split file" % (c, wl), rep08["split_" + wl][c], found)
            check("%s %s split counts: split report = split file" % (c, wl), rep06["lengths"][wl]["by_class"][c], found)

    failed = [c for c in checks if not c["ok"]]

    # ---------------------------------------------------------------- T1 dataset summary by session
    t1_header = ["row_type", "session", "class", "lab_range", "logins_recorded", "logins_used",
                 "raw_records", "classifier_input_records", "cleaned_recorder_records", "cleaned_audit_records",
                 "logged_minutes", "windows_30s", "kept_30s_before_rules", "kept_30s", "kept_60s",
                 "stages_accepted_by_operator", "finished_stage_7"]
    t1 = []
    for s in sessions:
        r8 = sum08[s["session"]]
        t1.append(["session", s["session"], s["class"], s["lab_range"], s["logins_recorded"], s["logins_used"],
                   r8["package_records"], r8["classifier_input"], r8["cleaned_recorder"], r8["cleaned_audit"],
                   "%.1f" % (s["working_time_s"] / 60.0), r8["w30_windows"], r8["w30_kept_before_rules"],
                   r8["w30_kept"], rep05_sum[s["session"]]["w60"]["kept"],
                   s["stages_accepted_by_operator"], s["finished_stage_7"]])
    session_rows = list(t1)

    def total_row(row_type, name, cls, rows):
        out = [row_type, name, cls, ""]
        labels = set(r[1] for r in rows)
        for i in range(4, len(t1_header)):
            col = t1_header[i]
            if col == "logged_minutes":          # from the exact times, not from the rounded rows
                out.append("%.1f" % (sum(s["working_time_s"] for s in sessions if s["session"] in labels) / 60.0))
            elif col in ("stages_accepted_by_operator",):
                out.append("")
            else:
                out.append(sum(int(r[i]) for r in rows))
        return out

    for c in E.CLASSES:
        rows = [r for r in session_rows if r[2] == c]
        t1.append(total_row("class_total", "%s (%d sessions)" % (E.CLASS_LABEL[c], len(rows)), c, rows))
    t1.append(total_row("total", "All (%d sessions)" % len(session_rows), "", session_rows))
    E.write_csv("T1_dataset_summary_by_session.csv", t1_header, t1)

    # ---------------------------------------------------------------- T2 kept windows by stage group
    t2c_header = ["window_s", "class", "stage_group", "kept_windows", "pct_of_class",
                  "sessions_supplying", "largest_session", "largest_session_windows", "largest_session_share_pct"]
    t2c = []
    t2s_header = ["window_s", "row_type", "session", "class", "lab_range"] + \
                 ["kept_stage_" + g for g in E.STAGE_GROUPS] + ["kept_total"]
    t2s = []
    for wl, secs in LENGTHS:
        for c in E.CLASSES:
            cs = [s for s in sessions if s["class"] == c]
            class_total = sum(kept_total(wl, s["session_key"]) for s in cs)
            for g in E.STAGE_GROUPS + ["all"]:
                per = [(kept_total(wl, s["session_key"]) if g == "all" else kept[wl][s["session_key"]][g], s["session"])
                       for s in cs]
                n = sum(v for v, _ in per)
                supplying = sum(1 for v, _ in per if v > 0)
                big_v, big_s = per[0]
                for v, name in per:              # the first session wins a tie
                    if v > big_v:
                        big_v, big_s = v, name
                t2c.append([secs, c, g, n, E.pct(n, class_total), supplying,
                            big_s if n else "", big_v if n else "", E.pct(big_v, n)])
        for s in sessions:
            k = s["session_key"]
            t2s.append([secs, "session", s["session"], s["class"], s["lab_range"]] +
                       [kept[wl][k][g] for g in E.STAGE_GROUPS] + [kept_total(wl, k)])
        for c in E.CLASSES:
            keys = [s["session_key"] for s in sessions if s["class"] == c]
            t2s.append([secs, "class_total", "%s (%d sessions)" % (E.CLASS_LABEL[c], len(keys)), c, ""] +
                       [sum(kept[wl][k][g] for k in keys) for g in E.STAGE_GROUPS] +
                       [sum(kept_total(wl, k) for k in keys)])
        t2s.append([secs, "total", "All (%d sessions)" % len(sessions), "", ""] +
                   [sum(kept[wl][s["session_key"]][g] for s in sessions) for g in E.STAGE_GROUPS] +
                   [sum(kept_total(wl, s["session_key"]) for s in sessions)])
    E.write_csv("T2_kept_windows_by_stage_group_class.csv", t2c_header, t2c)
    E.write_csv("T2_kept_windows_by_stage_group_session.csv", t2s_header, t2s)

    # ---------------------------------------------------------------- T3 split counts
    t3_header = ["window_s", "row_type", "session", "class"] + E.SPLITS + ["kept_total"]
    t3 = []
    for wl, secs in LENGTHS:
        for s in sessions:
            sc = split_counts[wl][s["session_key"]]
            t3.append([secs, "session", s["session"], s["class"]] + [sc[v] for v in E.SPLITS] + [sum(sc.values())])
        for c in E.CLASSES:
            keys = [s["session_key"] for s in sessions if s["class"] == c]
            vals = [sum(split_counts[wl][k][v] for k in keys) for v in E.SPLITS]
            t3.append([secs, "class_total", "%s (%d sessions)" % (E.CLASS_LABEL[c], len(keys)), c] + vals + [sum(vals)])
        vals = [sum(split_counts[wl][s["session_key"]][v] for s in sessions) for v in E.SPLITS]
        t3.append([secs, "total", "All (%d sessions)" % len(sessions), ""] + vals + [sum(vals)])
    E.write_csv("T3_split_counts.csv", t3_header, t3)

    # T3, second table: rows of each split by stage group and class. Pass 2 and the stage analysis use
    # training rows, so the window and session counts behind each stage group are fixed here.
    t3g_header = ["window_s", "class", "stage_group"] + E.SPLITS + \
                 ["train_sessions_supplying", "train_largest_session", "train_largest_session_windows",
                  "train_largest_session_share_pct"]
    t3g = []
    for wl, secs in LENGTHS:
        group_of = {r["window_id"]: r["stage_group"] for r in windows[wl] if r["keep"]}
        cell = {}                 # cell[(session_key, stage_group)][split]
        for r in splits[wl]:
            d = cell.setdefault((r["session_key"], group_of[r["window_id"]]), {v: 0 for v in E.SPLITS})
            d[r["split"]] += 1
        for c in E.CLASSES:
            cs = [s for s in sessions if s["class"] == c]
            class_train = 0
            for g in E.STAGE_GROUPS:
                per = [(cell.get((s["session_key"], g), {v: 0 for v in E.SPLITS}), s["session"]) for s in cs]
                vals = [sum(d[v] for d, _ in per) for v in E.SPLITS]
                train = [(d["train"], name) for d, name in per]
                big_v, big_s = train[0]
                for v, name in train:
                    if v > big_v:
                        big_v, big_s = v, name
                n_train = vals[0]
                class_train += n_train
                t3g.append([secs, c, g] + vals + [sum(1 for v, _ in train if v > 0), big_s if n_train else "",
                                                 big_v if n_train else "", E.pct(big_v, n_train)])
            keys = [s["session_key"] for s in cs]
            check("%s %s training rows: by stage group = split file" % (c, wl),
                  sum(split_counts[wl][k]["train"] for k in keys), class_train)
    E.write_csv("T3_split_rows_by_stage_group.csv", t3g_header, t3g)

    # ---------------------------------------------------------------- E2 overview panel
    def by_class(fn):
        vals = [sum(fn(s) for s in sessions if s["class"] == c) for c in E.CLASSES]
        return vals + [sum(vals)]

    n_h, n_a, n_all = by_class(lambda s: kept_total("w30", s["session_key"]))
    e2 = [
        ["sessions"] + by_class(lambda s: 1) + [""],
        ["logins_used"] + by_class(lambda s: s["logins_used"]) + [""],
        ["raw_records"] + by_class(lambda s: sum08[s["session"]]["package_records"]) + ["all records in the packages"],
        ["classifier_input_records"] + by_class(lambda s: sum08[s["session"]]["classifier_input"]) +
        ["operator recorder and audit records of the logins used, before cleaning"],
        ["cleaned_records"] + by_class(lambda s: sum08[s["session"]]["cleaned_recorder"] + sum08[s["session"]]["cleaned_audit"]) +
        ["recorder and audit records after cleaning"],
        ["logged_minutes"] + ["%.1f" % v for v in by_class(lambda s: s["working_time_s"] / 60.0)] + ["logins used, laid end to end"],
        ["kept_windows_30s", n_h, n_a, n_all, ""],
        ["kept_windows_30s_pct", E.pct(n_h, n_all), E.pct(n_a, n_all), "100.0", ""],
        ["kept_windows_60s"] + by_class(lambda s: kept_total("w60", s["session_key"])) + ["sensitivity"],
        ["window_length_s", 30, 30, 30, "60 s as sensitivity"],
        ["feature_columns_by_tier", "", "", "", "filled in during Pass 2"],
        ["columns_with_undefined_values", "", "", "", "filled in during Pass 2"],
    ]
    E.write_csv("E2_overview.csv", ["item", "human", "ai", "all", "note"], e2)

    # ---------------------------------------------------------------- E3 and E6 grid
    longest = max(s["working_time_s"] for s in sessions)
    bin_min = 5 if math.ceil(longest / 300.0) <= MAX_GRID_COLUMNS else 10
    bin_s = bin_min * 60.0
    grid_header = ["session", "class", "bin_minutes", "bin_index", "bin_start_min", "kept_windows"] + \
                  ["kept_stage_" + g for g in E.STAGE_GROUPS] + ["dominant_stage_group"]
    grid = []
    max_per_bin = 0
    for s in sessions:
        n_bins = int(math.ceil(s["working_time_s"] / bin_s))
        cells = [{g: 0 for g in E.STAGE_GROUPS} for _ in range(n_bins)]
        for r in windows["w30"]:
            if r["session_key"] == s["session_key"] and r["keep"]:
                b = int(r["elapsed_working_s"] // bin_s)
                cells[b][r["stage_group"]] += 1
        for b, cell in enumerate(cells):
            n = sum(cell.values())
            max_per_bin = max(max_per_bin, n)
            dominant = ""
            if n:
                top = max(cell.values())
                dominant = [g for g in E.STAGE_GROUPS if cell[g] == top][-1]     # ties go to the later stage
            grid.append([s["session"], s["class"], bin_min, b, b * bin_min, n] +
                        [cell[g] for g in E.STAGE_GROUPS] + [dominant])
    E.write_csv("E3_E6_grid.csv", grid_header, grid)
    check("grid: kept windows in the grid = kept 30 s windows",
          sum(kept_total("w30", s["session_key"]) for s in sessions), sum(r[5] for r in grid))

    accept = inp.read_csv("data/description/stage_acceptances.csv", ACCEPT_COLUMNS)
    ticks = []
    for s in sessions:
        for r in accept:
            if r["session_key"] != s["session_key"]:
                continue
            used = r["in_used_login"] == "1" and r["elapsed_working_s"] != ""
            t = float(r["elapsed_working_s"]) if used else None
            ticks.append([s["session"], s["class"], int(r["stage"]), int(r["in_used_login"]),
                          "%.3f" % (t / 60.0) if used else "", int(t // bin_s) if used else ""])
        check("%s operator's own acceptances: description = windows report" % s["session"],
              rep05["sessions"][s["session"]]["acceptances_used"],
              sum(1 for r in accept if r["session_key"] == s["session_key"]))
    E.write_csv("E6_stage_acceptances.csv",
                ["session", "class", "stage", "in_used_login", "elapsed_working_min", "bin_index"], ticks)

    failed = [c for c in checks if not c["ok"]]
    log = {
        "pass": "EDA Pass 1 (tables)",
        "eda_version": E.EDA_VERSION,
        "freeze_1_sha256": inp.freeze_sha256,
        "inputs_opened": inp.opened,
        "window_columns_read": WINDOW_COLUMNS,
        "split_columns_read": SPLIT_COLUMNS,
        "not_read": "feature values, per-window record counts, command text, terminal text, per-window label files, "
                    "the private key map, the test-label files, set_aside/, the evidence folder",
        "grid": {"bin_minutes": bin_min, "longest_session_columns": int(math.ceil(longest / bin_s)),
                 "most_kept_windows_in_one_bin": max_per_bin},
        "checks": checks,
        "checks_run": len(checks),
        "checks_failed": len(failed),
        "tables": {n: E.sha256_file(os.path.join(E.TABLES, n)) for n in sorted(os.listdir(E.TABLES))
                   if n.startswith(("T1_", "T2_", "T3_", "E2_", "E3_", "E6_"))},
    }
    E.write_json(os.path.join(E.OUT, "pass1_tables_log.json"), log)
    print("inputs opened:", len(inp.opened), "| checks:", len(checks), "| failed:", len(failed))
    for c in failed:
        print("FAILED", c)
    print("COMPLETE: Pass 1 tables" if not failed else "STOP: counts do not agree")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
