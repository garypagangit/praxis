"""Prepare and check isolated copies of the supplied Study 3 pipeline."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


REPOSITORY = Path(__file__).resolve().parent.parent
MARKER = ".study3-reproduction.json"
TABLES = (
    "results_h1_h3/tables/T_h1_restated.csv",
    "results_h1_h3/tables/T_h3_restated.csv",
    "results_h2_stage/tables/T_h2_stage_chance.csv",
    "results_h2_stage/tables/T_h2_verdict.csv",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def contained(path, parent):
    return path == parent or parent in path.parents


def copy_tree(source, destination):
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "_private"),
    )


def prepare(source, destination, mode):
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir():
        raise ValueError(f"Study folder does not exist: {source}")
    if contained(destination, source) or contained(source, destination):
        raise ValueError("Source and destination must not contain one another")
    if contained(destination, REPOSITORY):
        raise ValueError("The destination must be outside the Git repository: study data is restricted")
    if destination.exists():
        raise ValueError(f"Destination already exists; refusing to overwrite: {destination}")

    required = ["code", "real_lab3_preprocessing_design.md"]
    if mode == "raw":
        required.append("AHIR Participant Evidence")
    else:
        required.extend(["data", "reports"])
        if mode == "saved":
            required.extend(["results", "results_h1_h3", "results_h2_stage"])
        else:
            required.extend([
                "results_h1_h3/RULES_AS_DECIDED.md",
                "results_h2_stage/H2_RULE_BEFORE_RUN.md",
            ])
    missing = [name for name in required if not (source / name).exists()]
    if missing:
        raise ValueError("Missing study inputs: " + ", ".join(missing))

    destination.mkdir(parents=True)
    copy_tree(source / "code", destination / "code")
    for name in ("real_lab3_preprocessing_design.md", "real_lab3_feature_trial_design.md",
                 "real_lab3_eda_handoff.md"):
        if (source / name).is_file():
            shutil.copy2(source / name, destination / name)
    if mode == "raw":
        copy_tree(source / "AHIR Participant Evidence", destination / "AHIR Participant Evidence")
    else:
        for name in ("data", "reports"):
            copy_tree(source / name, destination / name)
        if mode == "saved":
            for name in ("results", "results_h1_h3", "results_h2_stage"):
                copy_tree(source / name, destination / name)
        else:
            for name in ("results_h1_h3/RULES_AS_DECIDED.md",
                         "results_h2_stage/H2_RULE_BEFORE_RUN.md"):
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / name, target)

    expected = {}
    if mode in ("saved", "rescore"):
        for name in TABLES:
            path = source / name
            if path.is_file():
                expected[name] = digest(path)
            elif mode == "saved":
                raise ValueError(f"Missing saved comparison table: {name}")
    marker = {"mode": mode, "source": str(source), "expected_tables": expected}
    (destination / MARKER).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {mode} study at {destination}")
    if mode != "raw":
        verify(destination)


def load_marker(root):
    root = root.resolve()
    if contained(root, REPOSITORY):
        raise ValueError("Study data must be outside the Git repository")
    marker = root / MARKER
    if not marker.is_file():
        raise ValueError(f"Not a prepared reproduction folder: {root}")
    return json.loads(marker.read_text(encoding="utf-8"))


def verify(root):
    root = root.resolve()
    marker = load_marker(root)
    if marker["mode"] == "raw":
        raise ValueError("Raw preparation has no frozen outputs to verify yet")
    total = 0
    for freeze in ("FREEZE_1.json", "FREEZE_2.json"):
        doc = json.loads((root / "reports" / freeze).read_text(encoding="utf-8"))
        for name, metadata in doc["files"].items():
            if freeze == "FREEZE_1.json" and (
                name.startswith("set_aside/") or "_private" in name
                or "labels_test_" in name or "AHIR Participant Evidence" in name
            ):
                continue
            path = root.joinpath(*name.split("/"))
            if not path.is_file() or digest(path) != metadata["sha256"]:
                raise ValueError(f"{freeze}: missing or changed: {name}")
            total += 1
    print(f"Verified {total} frozen entries; restricted set-aside and private files were not checked.")


def trial_environment():
    env = os.environ.copy()
    for name in ("S3_ROOT", "S3_OUT", "S3_LIBS", "S3_TEST_CHANCE_PARTS"):
        env.pop(name, None)
    return env


def probe(root):
    root = root.resolve()
    if load_marker(root)["mode"] != "rescore":
        raise ValueError("The fit probe requires a fresh rescore preparation")
    output = root / "results" / "trials" / "main__lr.json"
    if output.exists():
        raise ValueError("The probe requires a fresh rescore preparation; a trial already exists")
    verify(root)
    script = root / "code" / "trials" / "run_trials.py"
    subprocess.run([sys.executable, "-I", "-B", str(script), "score", "--shard", "0/1310",
                    "--budget", "120"], cwd=root, env=trial_environment(), check=True)
    if not output.is_file():
        raise ValueError("The probe did not complete its trial")
    result = json.loads(output.read_text(encoding="utf-8"))
    if not result["matches_plumbing"]:
        raise ValueError("Probe fit hash differs from frozen plumbing; do not continue this exact refit")
    print("PASS: probe fit hash matches frozen plumbing.")


def run_summaries(root):
    root = root.resolve()
    marker = load_marker(root)
    if marker["mode"] not in ("saved", "rescore"):
        raise ValueError("Summaries require a saved or rescore preparation")
    verify(root)
    env = trial_environment()
    scripts = ["code/h1_h3_tests/run_h1_h3_tests.py",
               "code/h2_stage/summarize_h2_stage.py"]
    if marker["mode"] == "rescore":
        scripts.insert(0, "code/trials/summarize.py")
    for script in scripts:
        subprocess.run([sys.executable, "-I", "-B", str(root / script)],
                       cwd=root, env=env, check=True)
    if marker["mode"] == "rescore":
        report = json.loads((root / "results" / "summary.json").read_text(encoding="utf-8"))
        if not report["scored_fits_equal_plumbing_fits"] or not report["true_labeling_of_chance_equals_trial"]:
            raise ValueError("Scored trials did not match their frozen plumbing or true-labeling checks")
        if report["leak_audit_of_results"]["result"] != "PASS":
            raise ValueError("Scored trial leak audit did not pass")
    checks = [
        ("results_h1_h3/h1_h3_checks.json",
         ("macro_f1_and_interval_equal_frozen_table", "frozen_H3_rows_reproduced")),
        ("results_h2_stage/h2_stage_checks.json",
         ("a_counts_equal_frozen_table", "b_fit_hash_equals_plumbing",
          "c_true_labeling_equals_frozen_stage_results", "tasks_run_under_this_rule_file",
          "leak_audit")),
    ]
    for name, keys in checks:
        report = json.loads((root / name).read_text(encoding="utf-8"))
        for key in keys:
            if report[key]["result"] != "PASS":
                raise ValueError(f"{name}: {key} did not pass")
        if report["d_freeze_1_after"]["changed"]:
            raise ValueError(f"{name}: Freeze 1 inputs changed")
    for name, expected in marker["expected_tables"].items():
        if digest(root / name) != expected:
            raise ValueError(f"Replayed table differs from supplied table: {name}")
    verify(root)
    if len(marker["expected_tables"]) == len(TABLES):
        print("PASS: H1, H2 and H3 tables match the supplied saved results.")
    else:
        print("PASS: analysis checks passed; no complete saved-table comparison is available.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--mode", choices=("saved", "rescore", "raw"), required=True)
    for command in ("verify", "probe", "summaries"):
        p = commands.add_parser(command)
        p.add_argument("--study", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.source, args.destination, args.mode)
        elif args.command == "verify":
            verify(args.study)
        elif args.command == "probe":
            probe(args.study)
        else:
            run_summaries(args.study)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
