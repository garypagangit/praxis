"""One command rebuilds the EDA (handoff rule 8).

    python3 -I -B code/eda/run_eda.py pass1

Pass 1 (handoff section 5): tables T1-T3, figures E2, E3, E4, E6, then the checks of
handoff section 10 that a program can run:
  1. counts agree with the step reports and the split file (done inside pass1_tables.py);
  3. the preprocessing's leak-audit patterns over every file in reports/eda/;
  6. a second run gives the same hashes.
Check 7 (figures read in place) and the credential check by eye are a person's.

Pass 2 is added when the feature table exists.
"""
import os
import platform
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import eda_common as E

PASS1_SCRIPTS = ["pass1_tables.py", "pass1_figures.py"]
PASS1_FILES = ("T1_", "T2_", "T3_", "E2_", "E3_", "E4_", "E6_", "captions_pass1", "pass1_tables_log", "pass1_figures_log")


def run_scripts(scripts, out_dir=None):
    env = dict(os.environ)
    if out_dir:
        env["EDA_OUT"] = out_dir
    for s in scripts:
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(E.HERE, s)], env=env)
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


def leak_audit(out_dir, prefixes):
    """Handoff section 10, check 3: the patterns of preprocessing design 6.6 over the EDA outputs.

    The patterns come from the frozen preprocessing code (code/s3_clean.py). Tables are searched
    the way step 7 searches table files. One pattern, participant_code, also matches the session
    labels of Table 4-1 (P001 ...), which the handoff asks for on every table and figure; those
    are counted on their own line and anything else the pattern finds is a hit.
    """
    sys.path.insert(0, os.path.dirname(E.HERE))
    import s3_clean as K
    labels = set(r["session"] for r in E.read_table("T1_dataset_summary_by_session.csv") if r["row_type"] == "session")
    hits, label_count, searched, images = [], {}, 0, 0
    for rel in sorted(hashes(out_dir, prefixes)):
        if rel.endswith(".png"):
            images += 1              # compressed image bytes; every string drawn is in a table or the captions
            continue
        data = open(os.path.join(out_dir, rel), "rb").read()
        searched += 1
        for name, rx in K.LEAK_PATTERNS:
            for m in rx.finditer(data):
                text = m.group(0).decode("utf-8", "replace")
                if name == "participant_code" and text in labels:
                    label_count[text] = label_count.get(text, 0) + 1
                else:
                    hits.append({"pattern": name, "file": rel, "sample": text[:60]})
    return {
        "patterns": [n for n, _ in K.LEAK_PATTERNS],
        "files_searched": searched,
        "image_files_not_searched_as_text": images,
        "hits": hits,
        "total_hits": len(hits),
        "session_labels_found": dict(sorted(label_count.items())),
        "result": "PASS" if not hits else "FAIL",
        "note": "Session labels are the Table 4-1 labels the handoff asks for (section 9). PNG files hold "
                "compressed pixels and SVG files hold drawn outlines; all text in them comes from the tables "
                "and the captions file, which are searched.",
    }


def pass1():
    run_scripts(PASS1_SCRIPTS)
    first = hashes(E.OUT, PASS1_FILES)
    with tempfile.TemporaryDirectory(prefix="s3_eda_rerun_") as tmp:      # outside the study folder
        run_scripts(PASS1_SCRIPTS, out_dir=tmp)
        second = hashes(tmp, PASS1_FILES)
    different = sorted(k for k in set(first) | set(second) if first.get(k) != second.get(k))
    tables_log = E.read_json_file(os.path.join(E.OUT, "pass1_tables_log.json"))
    audit = leak_audit(E.OUT, PASS1_FILES)
    import matplotlib
    import numpy
    result = {
        "pass": "EDA Pass 1",
        "eda_version": E.EDA_VERSION,
        "freeze_1_sha256": tables_log["freeze_1_sha256"],
        "code": {n: E.sha256_file(os.path.join(E.HERE, n)) for n in sorted(os.listdir(E.HERE)) if n.endswith(".py")},
        "libraries": {"python": platform.python_version(), "matplotlib": matplotlib.__version__, "numpy": numpy.__version__},
        "check_1_counts_agree": {"checks_run": tables_log["checks_run"], "failed": tables_log["checks_failed"],
                                 "result": "PASS" if tables_log["checks_failed"] == 0 else "FAIL"},
        "check_3_leak_audit": audit,
        "check_6_rerun": {"files_compared": len(first), "different": different,
                          "result": "PASS" if not different else "FAIL"},
        "check_7_figures_in_place": "a person's check: each figure placed 5.6 to 6.0 in wide in the Word template",
        "outputs": first,
    }
    E.write_json(os.path.join(E.OUT, "pass1_checks.json"), result)
    ok = all(result[k]["result"] == "PASS" for k in ("check_1_counts_agree", "check_3_leak_audit", "check_6_rerun"))
    print("check 1 counts:", result["check_1_counts_agree"])
    print("check 3 leak audit:", audit["result"], "hits", audit["total_hits"], "| session labels", sum(audit["session_labels_found"].values()))
    print("check 6 rerun:", result["check_6_rerun"]["result"], "files", len(first), "different", different)
    print("COMPLETE: EDA Pass 1" if ok else "STOP: a Pass 1 check failed")
    return 0 if ok else 1


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("pass1",):
        print(__doc__)
        return 2
    return pass1()


if __name__ == "__main__":
    sys.exit(main())
