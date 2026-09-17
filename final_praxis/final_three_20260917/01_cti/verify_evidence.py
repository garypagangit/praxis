"""Read-only source/claim checks; writes only this closure's verification receipt."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = json.loads((HERE / "EVIDENCE.json").read_text(encoding="utf-8"))
    errors = []
    hashes_checked = assertions_checked = links_checked = 0
    data = {}
    for key, item in evidence["sources"].items():
        path = (REPO / item["repo_path"]).resolve()
        if not path.is_relative_to(REPO) or not path.is_file():
            errors.append("Missing/out-of-repository source: " + key)
            continue
        hashes_checked += 1
        if sha(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            errors.append("Source bytes changed: " + key)
        if path.suffix == ".json":
            data[key] = json.loads(path.read_text(encoding="utf-8-sig"))
    for claim in evidence["claims"]:
        for support in claim["support"]:
            assertions_checked += 1
            try:
                value = data[support["source"]]
                for part in support["json_pointer"].lstrip("/").split("/"):
                    part = part.replace("~1", "/").replace("~0", "~")
                    value = value[int(part)] if isinstance(value, list) else value[part]
                if value != support["expected"]:
                    errors.append("Claim value mismatch: " + claim["id"] + support["json_pointer"])
            except (KeyError, IndexError, TypeError, ValueError):
                errors.append("Invalid claim pointer: " + claim["id"] + support["json_pointer"])
    for name in ("PAPER.md", "PRIOR_WORK.md", "HUMAN_REVIEW.md"):
        text = (HERE / name).read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#")):
                continue
            links_checked += 1
            if target == "VERIFICATION.json":
                continue
            if not (HERE / target.split("#", 1)[0]).resolve().is_file():
                errors.append("Missing local reference: " + name + " -> " + target)
    text = (HERE / "PAPER.md").read_text(encoding="utf-8")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    word_count = len(re.findall(r"\b[\w'-]+\b", text))
    quick = data["fresh_reproduction"]
    receipt = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not errors else "FAIL",
        "source_files_hash_verified": hashes_checked,
        "json_pointer_assertions_verified": assertions_checked,
        "local_markdown_links_checked": links_checked,
        "paper_word_count_links_as_labels": word_count,
        "offline_reproduction": {
            "command": "python -B reproduce.py --bootstrap none --output C:/w/px_final_20260917/final_praxis/final_three_20260917/01_cti/reproduction_counts",
            "working_directory": "final_praxis/papers/20260914/01_cti",
            "status": quick["status"],
            "cti_raw_parser_rows_checked": quick["cti_raw_parser_and_correctness_rows_verified"],
            "athena_derived_policy_rows_checked": quick["athena_derived_policy_rows_verified"],
            "bootstrap_intervals_recomputed_this_closure": quick["bootstrap_intervals_recomputed"],
            "bootstrap_intervals_reused_from_archive_this_closure": quick["bootstrap_intervals_explicitly_taken_from_archive"],
        },
        "archived_reproduction_unit_controls": {
            "command": "python -B -m unittest test_reproduce.py",
            "observed_status": "PASS", "tests_run": 8,
            "executed_on": "2026-09-17",
            "note": "Observed in the closure session before this receipt; this verifier does not rerun the unit controls.",
        },
        "independent_count_trace_status": data["count_trace"]["status"],
        "independent_count_trace_tables": len(data["count_trace"]["traces"]),
        "deliverable_sha256": {name: sha(HERE / name) for name in (
            "PAPER.md", "PRIOR_WORK.md", "HUMAN_REVIEW.md", "EVIDENCE.json", "COUNT_TRACE.json", "slide_summary.json")},
        "new_model_inference_calls": 0, "new_cloud_jobs": 0,
        "human_author_review": "PENDING", "academic_eligibility": "PENDING",
        "scope": "Artifact integrity, exact source assertions and local navigation; not scientific novelty certification, human approval, or new inference replication.",
        "errors": errors,
    }
    (HERE / "VERIFICATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in ("status", "source_files_hash_verified", "json_pointer_assertions_verified", "local_markdown_links_checked", "paper_word_count_links_as_labels", "errors")}, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
