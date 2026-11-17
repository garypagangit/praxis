"""One command rebuilds EDA run 3 and runs its checks (rule file section 5).

    S3_LIBS=<folder with SciPy> python3 -I -B code/eda_run3/run_eda_run3.py

Checks a program can run:
  1. both freeze files and the Pass 2 record hash as recorded, before and after, with the files
     the freezes list; no file outside code/eda_run3/ and reports/eda_run3/ is created or changed
     (the evidence folder and set_aside/ are not walked: run 3 never touches them);
  2. training rows only: zero rows of another split, every file opened is logged;
  3. counts agree (done inside run3_tables.py against the Pass 1 and Pass 2 tables);
  4. the preprocessing's leak-audit patterns over every text file in reports/eda_run3/;
  5. a second run gives the same file hashes;
  6. no string that the run 3 figure code can draw holds a study-internal name.
Looking at each figure as rendered is a person's check; it was also done when run 3 was built.
"""
import ast
import json
import os
import platform
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import run3_common as R

C, E = R.C, R.E
import run_eda_pass2 as P2RUN                    # for the freeze check and the leak audit; imported, never edited

SCRIPTS = ["run3_tables.py", "run3_figures.py"]
SKIP_DIRS = ("AHIR Participant Evidence", "set_aside")
OWN = ("code/eda_run3/", "reports/eda_run3/")
BANNED = re.compile(r"study 3|\bpass\b|freeze|\bflag(?:ged)?\b|handoff", re.I)


def run_scripts(out_dir=None):
    env = dict(os.environ)
    if out_dir:
        env["RUN3_OUT"] = out_dir
    for s in SCRIPTS:
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(R.HERE, s)], env=env)
        if r.returncode != 0:
            raise SystemExit("STOP: %s failed" % s)


def hashes(out_dir):
    found = {}
    for sub in ("tables", "figures"):
        d = os.path.join(out_dir, sub)
        for n in sorted(os.listdir(d)):
            found[sub + "/" + n] = E.sha256_file(os.path.join(d, n))
    return found


def snapshot():
    """Size and modification time of every file of the study folder that run 3 could reach."""
    snap = {}
    for dirpath, dirs, names in os.walk(R.ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, R.ROOT).replace(os.sep, "/")
            st = os.stat(p)
            snap[rel] = (st.st_size, st.st_mtime_ns)
    return snap


def drawable_strings():
    """String constants of the run 3 figure code, docstrings left out, and the text cells of the run 3 tables."""
    found = []
    tree = ast.parse(open(os.path.join(R.HERE, "run3_figures.py"), encoding="utf-8").read())
    doc = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
                doc.add(id(first.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc:
            found.append(("run3_figures.py", node.value))
    for name, v in list(R.LABEL.items()) + list(R.STAGE_NAME.items()) + list(R.STAGE_NAME_2L.items()):
        found.append(("run3_common.py", v))
    for n in sorted(os.listdir(R.TABLES)):
        for line in open(os.path.join(R.TABLES, n), encoding="utf-8"):
            found.append(("tables/" + n, line))
    found.append(("figures/captions_run3.md", open(os.path.join(R.FIGURES, "captions_run3.md"), encoding="utf-8").read()))
    return found


def main():
    if len(sys.argv) != 1:
        print(__doc__)
        return 2
    before = snapshot()
    frozen_before = P2RUN.freezes_unchanged()
    run_scripts()
    first = hashes(R.OUT)
    with tempfile.TemporaryDirectory(prefix="eda_run3_rerun_") as tmp:          # outside the study folder
        run_scripts(out_dir=tmp)
        second = hashes(tmp)
    different = sorted(k for k in set(first) | set(second) if first.get(k) != second.get(k))
    log = E.read_json_file(os.path.join(R.OUT, "run3_tables_log.json"))
    flog = E.read_json_file(os.path.join(R.OUT, "run3_figures_log.json"))
    opened = sorted(set(log["inputs_opened"]) | set(flog["pass_tables_opened"]))
    other_rows = log["training_rows"]["rows_of_another_split_loaded"]
    bad_inputs = [r for r in opened if any(part in r for part in E.FORBIDDEN_PARTS)
                  or "per_command" in r or r.startswith("data/windows/") or r.startswith("data/cleaned/")]
    audit = P2RUN.leak_audit(R.OUT)
    banned = [{"where": w, "text": t.strip()[:80]} for w, t in drawable_strings() if BANNED.search(t)]
    frozen_after = P2RUN.freezes_unchanged()
    after = snapshot()
    changed = sorted(k for k in set(before) | set(after)
                     if before.get(k) != after.get(k) and not k.startswith(OWN))
    pass2_sha = E.sha256_file(os.path.join(R.ROOT, *R.PASS2_CHECKS.split("/")))
    import matplotlib
    import numpy
    import scipy
    result = {
        "run": "EDA run 3", "run3_version": R.RUN3_VERSION,
        "rule_file": {"path": "reports/eda_run3/RULE_BEFORE_RUN.md",
                      "sha256": E.sha256_file(os.path.join(R.OUT, "RULE_BEFORE_RUN.md"))},
        "code": {n: E.sha256_file(os.path.join(R.HERE, n)) for n in sorted(os.listdir(R.HERE)) if n.endswith((".py", ".md"))},
        "libraries": {"python": platform.python_version(), "matplotlib": matplotlib.__version__,
                      "numpy": numpy.__version__, "scipy": scipy.__version__},
        "check_1_nothing_else_changed": {
            "freeze_1_sha256": frozen_after["FREEZE_1.json"]["sha256"], "freeze_2_sha256": frozen_after["FREEZE_2.json"]["sha256"],
            "pass2_checks_sha256": pass2_sha, "freezes_before": frozen_before, "freezes_after": frozen_after,
            "files_watched": len(before), "changed_outside_run3_folders": changed,
            "result": "PASS" if (not changed and pass2_sha == R.PASS2_CHECKS_SHA256
                                 and all(v["differ"] == 0 for v in frozen_after.values())
                                 and frozen_before == frozen_after) else "FAIL"},
        "check_2_training_rows_only": {"training_rows": log["training_rows"]["training_rows"],
                                       "rows_of_another_split_loaded": other_rows, "files_opened": len(opened),
                                       "command_text_or_record_files_opened": bad_inputs,
                                       "result": "PASS" if other_rows == 0 and not bad_inputs else "FAIL"},
        "check_3_counts_agree": {"checks_run": log["checks_run"], "failed": log["checks_failed"],
                                 "spearman_pairs_shared_with_pass2": log["spearman_pairs_shared_with_pass2"],
                                 "result": "PASS" if log["checks_failed"] == 0 else "FAIL"},
        "check_4_leak_audit": audit,
        "check_5_rerun": {"files_compared": len(first), "different": different,
                          "result": "PASS" if not different else "FAIL"},
        "check_6_no_internal_names_in_figure_text": {"pattern": BANNED.pattern, "found": banned,
                                                     "result": "PASS" if not banned else "FAIL"},
        "outputs": first,
    }
    E.write_json(os.path.join(R.OUT, "run3_checks.json"), result)
    keys = ("check_1_nothing_else_changed", "check_2_training_rows_only", "check_3_counts_agree", "check_4_leak_audit",
            "check_5_rerun", "check_6_no_internal_names_in_figure_text")
    ok = all(result[k]["result"] == "PASS" for k in keys)
    for k in keys:
        print(k + ":", result[k]["result"])
    print("leak audit hits", audit["total_hits"], "| session labels", sum(audit["session_labels_found"].values()),
          "| files", audit["files_searched"])
    print("rerun: files", len(first), "different", different)
    print("changed outside run 3 folders:", changed, "| banned:", banned[:5])
    print("COMPLETE: EDA run 3" if ok else "STOP: a run 3 check failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
