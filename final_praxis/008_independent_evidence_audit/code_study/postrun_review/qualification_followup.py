"""Read-only qualification/control follow-up; never executes benchmark programs."""
import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(tasks_file, full, audit_file, coordinator_receipt, code):
    tasks = {t["task_id"]: t for t in map(json.loads, tasks_file.read_text(encoding="utf-8").splitlines())}
    metadata_path = full / "public/TASK_RESULTS.json"
    metadata = json.loads(metadata_path.read_text())["tasks"]
    original_audit = json.loads(audit_file.read_text())
    coordinator = json.loads(coordinator_receipt.read_text())
    checks = {}
    checks["full_audit_all_checks_pass"] = original_audit["checks_passed"] == original_audit["checks_total"] == 7075 and not original_audit["errors"]
    checks["full_receipt_hash"] = original_audit["results_receipt_sha256"] == sha(full / "public/RECEIPT.json")
    checks["full_audit_source_hash"] = original_audit["audit_source_sha256"] == sha(code / "review/audit_qualification_results.py")
    checks["coordinator31_checks_pass"] = coordinator["checks_passed"] == coordinator["checks_total"] == 31 and all(coordinator["checks"].values())
    checks["coordinator_source_hash"] = coordinator["control_source_sha256"] == sha(code / "review/generated_controls.py")
    eligible = [t for t in metadata if t["eligible"]]
    for task in eligible:
        v = task["variants"]
        checks[task["task_id"] + ":eligible_original_pass"] = v["canonical"]["original"]["status"] == "pass"
        for variant in ("canonical", "reference"):
            counts = v[variant]["by_split"]["outcome"]
            checks[task["task_id"] + ":eligible_reserved_" + variant] = counts.get("pass", 0) > 0 and sum(counts.values()) == counts.get("pass", 0)
        counts = v["buggy"]["by_split"]["outcome"]
        checks[task["task_id"] + ":demonstrated_buggy_failure"] = any(counts.get(name, 0) > 0 for name in ("fail", "exception", "timeout", "program_load_error"))
    by_id = {t["task_id"]: t for t in metadata}
    helper_findings = []
    for task_id, helper in (("Python/32", "poly"), ("Python/38", "encode_cyclic"), ("Python/50", "encode_shift")):
        task, meta = tasks[task_id], by_id[task_id]
        helpers = {n.name for n in ast.parse(task["programs"]["canonical"]).body if isinstance(n, ast.FunctionDef)}
        called = {n.func.id for n in ast.walk(ast.parse(task["original_test"])) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        original = meta["variants"]["canonical"]["original"]
        checks[task_id + ":helper_evidence"] = helper in helpers and helper in called and original["error_type"] == "NameError" and not meta["eligible"]
        helper_findings.append(dict(task_id=task_id, helper=helper, original_status=original["status"],
                                    original_error=original["error_type"], exclusions=meta["exclusion_reasons"],
                                    classification="original-test namespace compatibility limitation; not proof of canonical semantic failure"))
    checks["135_eligible101_heldout"] = len(eligible) == 135 and sum(t["split"] == "heldout" for t in eligible) == 101
    return dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope="Independent metadata recount plus selected source-only AST helper audit; no main-study outcomes read and no programs executed",
                checks_passed=sum(checks.values()), checks_total=len(checks), failures=[name for name, passed in checks.items() if not passed],
                eligible_tasks=len(eligible), eligible_development=sum(t["split"] == "development" for t in eligible), eligible_heldout=sum(t["split"] == "heldout" for t in eligible),
                observed_worker_variants_completed=original_audit["worker_variants_completed"], assigned_worker_variants=original_audit["worker_variants_assigned"], normalized_unknown_case_rows=original_audit["missing_case_rows_normalized_unknown"],
                helper_namespace_findings=helper_findings,
                interpretation="Preserve the frozen135-task cohort. All included canonical originals and canonical/reference reserved suites passed. Compatibility exclusions32/38/50 do not support canonical semantic-defect claims;38/50 were excluded solely by original-test compatibility.32 also has reserved-test exclusion. GeneratedY1 depends on reserved tests, not original-suite status. A helper-namespace repair belongs to a separately versioned future study.",
                source_sha256={str(path): sha(path) for path in (tasks_file, metadata_path, audit_file, coordinator_receipt, code / "qualification/worker.py")})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("tasks-file", "full", "audit-file", "coordinator-receipt", "code", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    report = audit(a.tasks_file, a.full, a.audit_file, a.coordinator_receipt, a.code)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("checks_passed", "checks_total", "failures", "eligible_tasks", "eligible_heldout")}))
    raise SystemExit(bool(report["failures"]))
