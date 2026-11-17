"""Step 8: chain check and run summary.

Checks that every step's inputs are the previous step's outputs, that counts
add up from the package totals to the final files, and that the ledgers hold
one row for every dropped record. Writes reports/08_summary.json and a
readable reports/PREPROCESSING_RUN_SUMMARY.md with the items the design asks a
person to review before Freeze 1.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_config as C
import s3_io as IO


def main():
    R = lambda name: IO.read_json(IO.out("reports", name))
    r1, r2, r3, r4, r5, r6, r7 = (R("01_verification_report.json"), R("02_route_report.json"),
                                  R("03_clean_report.json"), R("04_commands_report.json"),
                                  R("05_windows_report.json"), R("06_split_report.json"),
                                  R("07_leak_audit_report.json"))
    problems = []
    rows = []
    for sess in C.SESSION_ORDER:
        s2, s3, s4, s5 = r2["sessions"][sess], r3["sessions"][sess], r4["sessions"][sess], r5["sessions"][sess]
        if s2["inputs"] != r1["sessions"][sess]["raw_inputs"]:
            problems.append("%s: step 2 inputs are not the verified raw files" % sess)
        if not s2["counts_add_up"]:
            problems.append("%s: step 2 counts do not add up" % sess)
        if s3["input_sha256"] != s2["classifier_input"]["scratch_sha256"]:
            problems.append("%s: step 3 did not read step 2's classifier input" % sess)
        rec_in = rec_a = rec_final = aud_in = aud_out = led3 = led4 = 0
        cmds = removed = 0
        for login, v3 in s3["logins"].items():
            st3 = v3["stats"]
            v4 = s4["logins"][login]
            st4 = v4["stats"]
            if v4["input_sha256"] != dict(recorder=v3["rec_sha256"], audit=v3["aud_sha256"]):
                problems.append("%s %s: step 4 did not read step 3's output" % (sess, login))
            sk, lk = s4["session_key"], v4["login_key"]
            for kind in ("recorder", "audit", "commands"):
                sub = "commands" if kind == "commands" else "cleaned"
                path = IO.out("data", sub, sk, "%s.%s.jsonl" % (lk, kind))
                if IO.sha256_file(path)[0] != v4["output_sha256"][kind]:
                    problems.append("%s %s: %s file changed after step 4" % (sess, login, kind))
            rec_in += st3["records"]
            rec_a += st3["recorder_records_out"]
            rec_final += st4["recorder_records_out"]
            aud_in += st3["audit_records_in"]
            aud_out += st3["audit_records_out"]
            led3 += st3["ledger_rows"]
            led4 += st4["records_emptied_dropped"]
            cmds += st4["pass2_commands"]
            removed += st4["validator_commands_removed"]
            if rec_a - 0 < 0 or st3["recorder_records_out"] - st4["records_emptied_dropped"] != st4["recorder_records_out"]:
                problems.append("%s %s: recorder counts do not add up in step 4" % (sess, login))
            if not st4["pass2_matches_pass1"] or st4["pass2_validator_programs_left"] or st4["validator"]["marker_unmatched"]:
                problems.append("%s %s: command reconstruction flags" % (sess, login))
        ci = s2["classifier_input"]
        if rec_in != ci["recorder"] or aud_in != ci["audit_records"]:
            problems.append("%s: step 3 record counts differ from step 2's classifier input" % sess)
        # ledger: one row for every dropped record
        led = {}
        with open(IO.out("reports", "ledgers", "%s_dropped.csv" % sess), encoding="utf-8") as f:
            for row in csv.DictReader(f):
                led[row["step"]] = led.get(row["step"], 0) + 1
        exp = {"02_route": s2["dropped_with_ledger"]["records"], "03_clean": led3, "04_commands": led4}
        for step, n in exp.items():
            if led.get(step, 0) != n:
                problems.append("%s: ledger rows for %s are %d, expected %d" % (sess, step, led.get(step, 0), n))
        dropped_total = sum(exp.values())
        if s2["package_records"] != s2["set_aside"]["records"] + rec_final + aud_out + dropped_total:
            problems.append("%s: package total does not equal set aside + cleaned + dropped" % sess)
        w30 = {k: 0 for k in ("windows", "kept_before_rules", "kept")}
        for login, v in s5["logins"].items():
            for k in w30:
                w30[k] += v["w30"][k]
        rows.append(dict(session=sess, cls=C.SESSIONS[sess]["cls"], lab_range=C.SESSIONS[sess]["lab_range"],
                         logins_used=len(s3["logins"]), package_records=s2["package_records"],
                         set_aside=s2["set_aside"]["records"], dropped_at_route=exp["02_route"],
                         classifier_input=ci["records"], dropped_at_clean=led3, dropped_validator=led4,
                         cleaned_recorder=rec_final, cleaned_audit=aud_out, commands=cmds,
                         validator_commands_removed=removed, **{"w30_" + k: v for k, v in w30.items()}))
    for L in C.WINDOW_LENGTHS:
        if r6["lengths"]["w%d" % L]["input_sha256"] != r5["outputs"]["data/windows/w%d/windows.csv" % L]:
            problems.append("w%d: the split did not read step 5's window table" % L)
    if r7["result"] != "PASS":
        problems.append("leak audit: %d hits" % r7["total_hits"])
    summary = dict(step="08_summary", code_version=C.CODE_VERSION, sessions=rows, problems=problems,
                   result="PASS" if not problems else "FAIL", totals_w30=r5["totals"]["w30"], totals_w60=r5["totals"]["w60"],
                   split_w30=r6["lengths"]["w30"]["by_class"], split_w60=r6["lengths"]["w60"]["by_class"],
                   leak_audit=dict(result=r7["result"], total_hits=r7["total_hits"], reported_only=r7["reported_only"]),
                   freeze_1="not written: waiting for the review before the freeze")
    IO.write_json(IO.out("reports", "08_summary.json"), summary)

    # ---------------------------------------------------------------- readable summary
    L = []
    L.append("# Study 3 preprocessing: run summary\n")
    L.append("Written by `code/step08_summary.py` from the step reports. Code version `%s`. **Freeze 1 has not been written.**\n" % C.CODE_VERSION)
    L.append("Result of the chain check: **%s**%s\n" % (summary["result"], "" if not problems else " — " + "; ".join(problems)))
    L.append("## 1. Where every record went\n")
    L.append("| Session | Class | Range | Logins used | Package records | Set aside | Dropped at routing | Dropped in cleaning | Dropped with validator commands | Cleaned recorder | Cleaned audit |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for x in rows:
        L.append("| %(session)s | %(cls)s | %(lab_range)s | %(logins_used)d | %(package_records)d | %(set_aside)d | %(dropped_at_route)d | %(dropped_at_clean)d | %(dropped_validator)d | %(cleaned_recorder)d | %(cleaned_audit)d |" % x)
    L.append("\nEvery row adds up: package = set aside + dropped + cleaned recorder + cleaned audit. Every dropped record is in `reports/ledgers/`.\n")
    L.append("## 2. Commands and windows (30 s)\n")
    L.append("| Session | Commands kept | Validator commands removed | Windows | Kept before the two rules | Kept |")
    L.append("|---|---|---|---|---|---|")
    for x in rows:
        L.append("| %(session)s | %(commands)d | %(validator_commands_removed)d | %(w30_windows)d | %(w30_kept_before_rules)d | %(w30_kept)d |" % x)
    for name, tot in (("30 s", r5["totals"]["w30"]), ("60 s", r5["totals"]["w60"])):
        L.append("\nKept windows, %s:\n" % name)
        L.append("| Class | Before the closing-exit and validator-only rules | Kept | Stages 1-4 | Stage 5 | Stage 6 | Stage 7 |")
        L.append("|---|---|---|---|---|---|---|")
        for c in ("human", "ai"):
            d = tot[c]
            g = d["by_stage_group"]
            L.append("| %s | %d | %d | %d | %d | %d | %d |" % (c, d["kept_before_rules"], d["kept"], g.get("1-4", 0), g.get("5", 0), g.get("6", 0), g.get("7", 0)))
    L.append("\n## 3. Split\n")
    for name, key in (("30 s", "w30"), ("60 s", "w60")):
        bc = r6["lengths"][key]["by_class"]
        L.append("%s: " % name + "; ".join("%s train %d, validation %d, test %d, unused %d" % (c, bc[c]["train"], bc[c]["val"], bc[c]["test"], bc[c]["unused"]) for c in ("human", "ai")) + "\n")
    L.append("## 4. Leak audit\n")
    L.append("Result **%s**, %d hits in %d files. Reported only (outside design sections 6.2-6.5): %s\n" % (
        r7["result"], r7["total_hits"], r7["files_searched"], json.dumps(r7["reported_only"])))
    L.append("## 5. For review before Freeze 1\n")
    L.append("### 5.1 Prompt pattern (A15)\n")
    L.append("The shell prompt is recognised by this pattern on the visible text of the output (colours and control sequences stripped):\n")
    L.append("```\n%s\n```\n" % r4["prompt_pattern"].replace("\r", "\\r").replace("\n", "\\n"))
    L.append("Two forms occur: `┌─[user@host]─[dir]` then `└──╼ $` in a person's shell (with `[✗]─` added after a failed command), and `┌──[user@host]─[dir]` then `└──╼ $` in the harness's shell.\n")
    L.append("### 5.2 Screen text against keystrokes, plain lines typed at the shell prompt\n")
    L.append("| Session | Login | Plain typed lines | Screen agrees | Text from keys | Text from screen | Kept keys because the screen could not be read |")
    L.append("|---|---|---|---|---|---|---|")
    for sess in C.SESSION_ORDER:
        for login, v in r4["sessions"][sess]["logins"].items():
            st = v["stats"]
            rc = st["reconstruction"]
            ts = st["text_source"]
            L.append("| %s | %s | %d | %d | %d | %d | %d |" % (sess, login[:8], rc["plain_shell_lines"], rc["plain_shell_agree"],
                                                         ts.get("keys", 0), ts.get("screen", 0), ts.get("keys_fallback", 0)))
    L.append("\nLogins of the AI sessions have no typed lines: every line arrives as one write, and the wrapper's echo is removed in cleaning.\n")
    L.append("### 5.3 Cross-checks of A15\n")
    L.append("| Session | Login | Wrapped inputs | END lines | END lines followed directly by the prompt | Wrapped inputs with no END line | Shell prompts | Paste-mode markers | of which at a shell prompt | elsewhere |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for sess in C.SESSION_ORDER:
        for login, v in r4["sessions"][sess]["logins"].items():
            a = r3["sessions"][sess]["logins"][login]["stats"]
            p = v["stats"]["paste_marker_check"]
            L.append("| %s | %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (
                sess, login[:8], a["wrapped_inputs"], a["end_lines"], a["end_lines_followed_by_prompt"],
                a["wrapped_without_end_line"], p["shell_prompts"], p["paste_mode_markers"],
                p["markers_at_a_shell_prompt"], p["markers_elsewhere"]))
    L.append("\n### 5.4 Validator commands removed\n")
    L.append("Full list with text: `reports/04_removed_validator_commands.jsonl`. By rule:\n")
    by = {}
    with open(IO.out("reports", "04_removed_validator_commands.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            by.setdefault(r["session"], {}).setdefault(r["rule"], 0)
            by[r["session"]][r["rule"]] += 1
    L.append("| Session | Call within 15 s of the command | Call inside a command still running | Program name only |")
    L.append("|---|---|---|---|")
    for sess in C.SESSION_ORDER:
        d = by.get(sess, {})
        L.append("| %s | %d | %d | %d |" % (sess, d.get("marker_within_15s", 0), d.get("marker_in_running_command", 0), d.get("program_name", 0)))
    L.append("\n### 5.5 Successful programs of the validator family (design 6.4)\n")
    L.append("Every successful exec whose record group names the validator family, with whether it left a marker: `reports/03_validator_family_execs_for_review.json`.\n")
    with open(IO.out("reports", "PREPROCESSING_RUN_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("chain check:", summary["result"])
    for p in problems:
        print("  PROBLEM:", p)
    print("COMPLETE: summary")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
