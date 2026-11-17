"""One command rebuilds EDA Pass 2 (handoff rule 8).

    S3_LIBS=<folder with SciPy> python3 -I -B code/eda/run_eda_pass2.py

Pass 2 (handoff section 6, as amended by 12a): tables T4 to T9, figures E1, E2 (tier lines),
E5, E7 to E12, for the rows marked `train`. It is run after the trials, as a report only.

`run_eda.py` rebuilds Pass 1 and is part of Freeze 2, so it is not edited; this file is
the Pass 2 counterpart. The checks of handoff section 10 that a program can run:
  1. class totals of every Pass 2 table equal the training counts of Pass 1's T3
     (done inside pass2_tables.py);
  2. training rows only: zero rows of any other split, every file opened is listed,
     and the test-label files are not among them;
  3. the preprocessing's leak-audit patterns over every file in reports/eda/;
  4. (a program's part of it) no output holds a line that was typed into a waiting
     program, which is where a reply at a password prompt would be;
  6. a second run gives the same hashes;
  and both freezes, and the Pass 1 outputs, are unchanged after the run.
Check 4 by eye, check 7 (figures read in place) and the reading of E1 are a person's.
"""
import json
import os
import platform
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import pass2_common as C

E = C.E

PASS2_SCRIPTS = ["pass2_tables.py", "pass2_figures.py"]
PASS2_FILES = ("T4_", "T5_", "T6_", "T7_", "T8_", "T9_", "E1_", "E2_overview_pass2", "E2_dataset_summary_pass2",
               "E5_", "E7_", "E8_", "E9_", "E10_", "E11_", "E12_", "captions_pass2", "pass2_tables_log",
               "pass2_figures_log")
PASS1_FILES = ("T1_", "T2_", "T3_", "E2_overview.csv", "E2_dataset_summary.", "E3_", "E4_", "E6_", "captions_pass1",
               "pass1_")


def run_scripts(out_dir=None):
    env = dict(os.environ)
    if out_dir:
        env["EDA_OUT"] = out_dir
    for s in PASS2_SCRIPTS:
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(C.HERE, s)], env=env)
        if r.returncode != 0:
            raise SystemExit("STOP: %s failed" % s)


def hashes(out_dir, prefixes):
    found = {}
    for dirpath, dirs, names in os.walk(out_dir):
        dirs.sort()
        for n in sorted(names):
            if n.startswith(prefixes):
                rel = os.path.relpath(os.path.join(dirpath, n), out_dir).replace(os.sep, "/")
                found[rel] = E.sha256_file(os.path.join(dirpath, n))
    return found


def leak_audit(out_dir):
    """Handoff section 10, check 3, over every file in reports/eda/ (Pass 1 and Pass 2).
    The session labels of Table 4-1 match the participant-code pattern; they are counted on
    their own line and anything else a pattern finds is a hit (reading E1 of handoff 5a)."""
    sys.path.insert(0, os.path.dirname(C.HERE))
    import s3_clean as K
    labels = set("P%03d" % i for i in (1, 2, 3, 4, 5, 6, 9, 10, 11))
    hits, label_count, searched, images = [], {}, 0, 0
    for dirpath, dirs, names in os.walk(out_dir):
        dirs.sort()
        for n in sorted(names):
            rel = os.path.relpath(os.path.join(dirpath, n), out_dir).replace(os.sep, "/")
            if n.endswith(".png"):
                images += 1
                continue
            if rel == "pass2_checks.json":
                continue                      # this check's own result file, written after the search
            data = open(os.path.join(dirpath, n), "rb").read()
            searched += 1
            for name, rx in K.LEAK_PATTERNS:
                for m in rx.finditer(data):
                    text = m.group(0).decode("utf-8", "replace")
                    if name == "participant_code" and text in labels:
                        label_count[text] = label_count.get(text, 0) + 1
                    else:
                        hits.append({"pattern": name, "file": rel, "sample": text[:60]})
    return {"patterns": [n for n, _ in K.LEAK_PATTERNS], "files_searched": searched,
            "image_files_not_searched_as_text": images, "hits": hits, "total_hits": len(hits),
            "session_labels_found": dict(sorted(label_count.items())),
            "result": "PASS" if not hits else "FAIL",
            "note": "Every file in reports/eda/, Pass 1 and Pass 2, except this result file. PNG files hold "
                    "compressed pixels and SVG files hold drawn outlines; all text in them comes from the tables and "
                    "the captions file, which are searched."}


def waiting_program_lines(out_dir):
    """A program's part of check 4. A reply at a password prompt is a line typed into a waiting
    program (preprocessing design 6.7). No Pass 2 output may hold such a line. The lines are read
    from the training rows of the per-command table, compared, and never written anywhere."""
    inp = C.Inputs2(C.pass2_inputs(("w30",)))
    sessions, _ = E.session_table(inp)
    rows, _, _ = C.load_training(inp, "w30", sessions)
    cmds, _ = C.load_training_commands(inp, "w30", rows)
    lines = set()
    for c in cmds:
        if not c["at_prompt"]:
            for part in c["text"].split("\n"):
                part = part.strip()
                if len(part) >= 6 and " " not in part:
                    lines.add(part.encode("utf-8"))
    found, searched = 0, 0
    for rel in sorted(hashes(out_dir, PASS2_FILES)):
        if rel.endswith(".png"):
            continue
        data = open(os.path.join(out_dir, rel), "rb").read()
        searched += 1
        found += sum(1 for s in lines if s in data)
    return {"inputs_opened_for_this_check": sorted(inp.opened),
            "one_word_lines_typed_into_a_waiting_program": len(lines), "files_searched": searched,
            "found_in_outputs": found, "result": "PASS" if found == 0 else "FAIL",
            "note": "Lines of six characters or more with no space. This does not replace the reading of E1, E5 "
                    "and E8 and their tables by a person."}


def freezes_unchanged():
    out = {}
    forbidden = E.FORBIDDEN_PARTS
    for name in ("FREEZE_1.json", "FREEZE_2.json"):
        p = os.path.join(E.ROOT, "reports", name)
        files = json.load(open(p, encoding="utf-8"))["files"]
        match = differ = skipped = 0
        for rel, v in sorted(files.items()):
            if any(part in rel for part in forbidden):
                skipped += 1
                continue
            q = os.path.join(E.ROOT, *rel.split("/"))
            ok = os.path.exists(q) and os.path.getsize(q) == v["bytes"] and E.sha256_file(q) == v["sha256"]
            match += ok
            differ += not ok
        out[name] = {"sha256": E.sha256_file(p), "files_listed": len(files), "match": match, "differ": differ,
                     "not_opened": skipped}
    return out


def main():
    if len(sys.argv) != 1:
        print(__doc__)
        return 2
    pass1_before = hashes(E.OUT, PASS1_FILES)
    run_scripts()
    first = hashes(E.OUT, PASS2_FILES)
    with tempfile.TemporaryDirectory(prefix="s3_eda_pass2_rerun_") as tmp:     # outside the study folder
        run_scripts(out_dir=tmp)
        second = hashes(tmp, PASS2_FILES)
    different = sorted(k for k in set(first) | set(second) if first.get(k) != second.get(k))
    log = E.read_json_file(os.path.join(E.OUT, "pass2_tables_log.json"))
    opened = sorted(log["inputs_opened"])
    other_rows = sum(v["rows_of_another_split_loaded"] for v in log["training_rows"].values())
    bad_inputs = [r for r in opened if any(part in r for part in E.FORBIDDEN_PARTS)]
    audit = leak_audit(E.OUT)
    lines = waiting_program_lines(E.OUT)
    frozen = freezes_unchanged()
    pass1_after = hashes(E.OUT, PASS1_FILES)
    import matplotlib
    import numpy
    import scipy
    result = {
        "pass": "EDA Pass 2",
        "run_after_the_trials_as_a_report_only": "handoff 12a; F16 of the feature and trial design",
        "eda_version": E.EDA_VERSION, "pass2_version": C.PASS2_VERSION,
        "freeze_1_sha256": log["freeze_1_sha256"], "freeze_2_sha256": log["freeze_2_sha256"],
        "code": {n: E.sha256_file(os.path.join(C.HERE, n)) for n in sorted(os.listdir(C.HERE))
                 if n.startswith(("pass2_", "run_eda_pass2", "README_pass2"))},
        "libraries": {"python": platform.python_version(), "matplotlib": matplotlib.__version__,
                      "numpy": numpy.__version__, "scipy": scipy.__version__},
        "check_1_counts_agree": {"checks_run": log["checks_run"], "failed": log["checks_failed"],
                                 "result": "PASS" if log["checks_failed"] == 0 else "FAIL"},
        "check_2_training_rows_only": {"training_rows": {k: v["training_rows"] for k, v in log["training_rows"].items()},
                                       "rows_of_another_split_loaded": other_rows, "files_opened": len(opened),
                                       "files_opened_list": "inputs_opened in pass2_tables_log.json; the figures read "
                                                            "reports/eda/tables/ only",
                                       "forbidden_files_opened": bad_inputs,
                                       "result": "PASS" if other_rows == 0 and not bad_inputs else "FAIL"},
        "check_3_leak_audit": audit,
        "check_4_lines_typed_into_a_waiting_program": lines,
        "check_4_credentials_by_eye": "a person's check: E1, E5 and E8 and their tables, before they leave the study folder",
        "check_6_rerun": {"files_compared": len(first), "different": different,
                          "result": "PASS" if not different else "FAIL"},
        "check_7_figures_in_place": "a person's check: each figure placed 5.6 to 6.0 in wide in the Word template",
        "freezes_after_the_run": frozen,
        "pass_1_outputs_unchanged": {"files": len(pass1_before), "result": "PASS" if pass1_before == pass1_after else "FAIL"},
        "outputs": first,
    }
    E.write_json(os.path.join(E.OUT, "pass2_checks.json"), result)
    keys = ("check_1_counts_agree", "check_2_training_rows_only", "check_3_leak_audit",
            "check_4_lines_typed_into_a_waiting_program", "check_6_rerun", "pass_1_outputs_unchanged")
    ok = all(result[k]["result"] == "PASS" for k in keys) and all(v["differ"] == 0 for v in frozen.values())
    for k in keys:
        print(k + ":", result[k]["result"])
    print("leak audit hits", audit["total_hits"], "| session labels", sum(audit["session_labels_found"].values()),
          "| files", audit["files_searched"])
    print("rerun: files", len(first), "different", different)
    print("freezes:", {k: (v["match"], v["differ"]) for k, v in frozen.items()})
    print("COMPLETE: EDA Pass 2" if ok else "STOP: a Pass 2 check failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
