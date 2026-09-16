"""Check this decision packet against existing evidence; no inference or network calls."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pointer_value(value, pointer: str):
    if not pointer:
        return value
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid JSON pointer: {pointer}")
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors = []
    assertions_checked = 0
    links_checked = 0
    source_records = {}
    web_records = []
    expected_docs = ["README.md", "DECISION_TABLE.md", "01_CTI_BRIEF.md",
                     "02_008_BRIEF.md", "03_010_BRIEF.md",
                     "04_PX055_DISPOSITION.md", "REVIEW_WORKSHEET.md"]
    for name in expected_docs:
        if not (ROOT / name).is_file():
            errors.append(f"Missing deliverable: {name}")

    ledgers = sorted(ROOT.glob("*_SOURCES.json"))
    if len(ledgers) != 4:
        errors.append(f"Expected four source ledgers, found {len(ledgers)}")
    for ledger_path in ledgers:
        ledger = read_json(ledger_path)
        for entry in ledger.get("local_sources", []):
            path = Path(entry["path"])
            if not path.is_file():
                errors.append(f"Missing source: {path}")
                continue
            source_records[path.as_posix()] = {"sha256": sha(path), "bytes": path.stat().st_size}
            if entry.get("assertions"):
                data = read_json(path)
                for assertion in entry["assertions"]:
                    assertions_checked += 1
                    try:
                        actual = pointer_value(data, assertion["pointer"])
                        expected = assertion["expected"]
                        if actual != expected or (isinstance(expected, bool) and type(actual) is not bool):
                            errors.append(f"Value mismatch: {path.name} {assertion['pointer']}: {actual!r} != {expected!r}")
                    except (KeyError, IndexError, TypeError, ValueError) as exc:
                        errors.append(f"Bad source location: {path.name} {assertion['pointer']}: {exc}")
        for source in ledger.get("web_sources", []):
            web_records.append({"ledger": ledger_path.name, **source})

    # Validate local navigation, including local links in the short briefs.
    # VERIFICATION.json is the receipt written below.
    for name in expected_docs:
        path = ROOT / name
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = target.strip().strip("<>")
            if target.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0])
            if re.match(r"^/[A-Za-z]:/", target):
                target = target[1:]
            resolved = Path(target)
            if not resolved.is_absolute():
                resolved = ROOT / resolved
            links_checked += 1
            if resolved.resolve() == (ROOT / "VERIFICATION.json").resolve():
                continue
            if not resolved.exists():
                errors.append(f"Broken local link in {name}: {target}")

    # Confirm the planned workload directly from the external D0 specification.
    d0_path = Path("C:/w/px010_dev/final_praxis/010_development_20260915/D0_SPEC.json")
    d0 = read_json(d0_path)
    derived_evaluations = len(d0["pipelines"]) * d0["data"]["origins"] * (
        d0["accounting"]["clean_evaluations_per_pipeline_origin"]
        + d0["perturbations"]["variants"]
        + d0["accounting"]["extra_clean_repeats_per_pipeline_origin"])
    if derived_evaluations != d0["accounting"]["total_pipeline_evaluations"]:
        errors.append("D0 workload does not reconcile")

    # Preserve evidence hashes from the first successful check. Future source changes
    # cause a visible failure rather than silently changing this dated assessment.
    manifest_path = ROOT / "SOURCE_MANIFEST.json"
    if manifest_path.exists():
        previous = read_json(manifest_path)["local_sources"]
        if previous != source_records:
            errors.append("Local source files changed since the packet was verified")
    elif not errors:
        manifest_path.write_text(json.dumps({"local_sources": source_records}, indent=2) + "\n", encoding="utf-8")

    receipt = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not errors else "FAIL",
        "scope": "Exact local evidence assertions, source hashes, local navigation, and planned D0 workload; no new statistics, inference, novelty certification, or academic approval.",
        "source_assertions_checked": assertions_checked,
        "unique_local_sources_hashed": len(source_records),
        "local_links_checked": links_checked,
        "primary_web_source_entries": len(web_records),
        "web_access": "Targeted primary-source reading recorded in ledgers; this script does not fetch the web.",
        "planned_d0_pipeline_evaluations": derived_evaluations,
        "new_model_inference_calls": 0,
        "new_cloud_jobs": 0,
        "originality_certified": False,
        "academic_scope_accepted": False,
        "independent_author_review_completed": False,
        "deliverable_sha256": {name: sha(ROOT / name) for name in expected_docs if (ROOT / name).is_file()},
        "errors": errors,
    }
    (ROOT / "VERIFICATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ["status", "source_assertions_checked", "unique_local_sources_hashed", "local_links_checked", "planned_d0_pipeline_evaluations", "errors"]}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
