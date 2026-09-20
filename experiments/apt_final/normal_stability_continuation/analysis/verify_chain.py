"""Independently bind continuation results to the prior stopped attempt.

This supplements the original scientific result audit. It verifies only the
additional runtime/transport/reuse chain and never changes or reruns science.
No operative continuation helper is imported.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from experiments.apt_final.normal_stability.analysis import verify_results as science

need, read, digest, safe = science.need, science.read, science.digest, science.safe
AuditFailure = science.AuditFailure
SOURCE_RECEIPTS = ("RUN_STATUS.json", "NORMAL_RESULTS.partial.json", "NORMAL_RESULTS.json", "NORMAL_FREEZE.json", "RESULTS.json")
REUSED = "REUSED_VERIFIED_ENCODER_AND_EIGHT_CACHES"
FRESH = "FRESH_ORIGINAL_TRAIN_AND_CACHE"


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(result.tzinfo is not None, "Evidence timestamp must have a timezone")
    return result


def checkpoint_names(seed):
    names = {"MANIFEST.json", "FIT_FREEZE.json", "PREPROCESSING.npz", f"mlp_{seed}.pt", f"gin_{seed}.pt"}
    names.update(f"cache/{graph}/{view}/{name}" for graph, view, name in itertools.product(
        science.NORMAL_GRAPHS, ("clean", "masked"), ("CACHE.npz", "CACHE.json")))
    return names


def bind_registrations(config_path, data_dir, original_registration_path, continuation_registration_path, reuse_dir):
    config, original, manifest = science.source_binding(config_path, data_dir, original_registration_path)
    record = read(continuation_registration_path)
    need(record["scope"] == "DEVELOPMENT_ONLY" and record["status"] == "FROZEN_NORMAL_STABILITY_CONTINUATION", "Wrong continuation registration")
    need(record["original_registration_sha256"] == digest(original_registration_path)
         and record["original_config_sha256"] == digest(config_path)
         and record["original_source_commit"] == original["git_commit"], "Original scientific registration identity changed")
    need(record["data_manifest_sha256"] == original["data_manifest_sha256"] and record["data_files"] == original["data_files"], "Continuation changes normalized data")
    need(record["scientific_settings_changed"] is False and record["all_banks_and_calibration_recomputed"] is True
         and record["all_attack_conditions_replayed"] is True and record["confirmation_registered"] is False
         and record["test_outcomes_previously_inspected"] is True, "Continuation scientific scope changed")
    expected = {config_path, original_registration_path, HERE / "config.json", HERE / "PROTOCOL.md", *HERE.glob("*.py"), *HERE.glob("*.sh"),
                *(REPO / rel for rel in original["code_hashes"])}
    need(set(record["code_hashes"]) == {path.relative_to(REPO).as_posix() for path in expected}, "Continuation operative source inventory differs")
    for relative, sha in record["code_hashes"].items():
        need(digest(safe(REPO, relative)) == sha, "Continuation source bytes changed")
        blob = subprocess.check_output(["git", "show", record["git_commit"] + ":" + relative], cwd=REPO)
        need(hashlib.sha256(blob).hexdigest() == sha, "Continuation source differs from registered commit")
    need(record["reuse_manifest_sha256"] == digest(reuse_dir / "REUSE_MANIFEST.json"), "Registered reuse manifest changed")
    reuse = read(reuse_dir / "REUSE_MANIFEST.json")
    need(record["reuse_files"] == reuse["inventory"], "Registered reusable file inventory changed")
    return config, original, record, manifest, reuse


def check_archive(archive_path, expected_sha, expected_members):
    """One streaming pass compares source bytes; no extraction or pickle load."""
    archive_path = Path(archive_path)
    need(digest(archive_path) == expected_sha, "Prior result transport checksum differs")
    before = archive_path.stat()
    found, seen, total = {}, set(), 0
    with tarfile.open(archive_path, "r|gz") as archive:
        for member in archive:
            name = member.name
            need(name and "\\" not in name and ":" not in name and not name.startswith("/")
                 and all(part not in ("", ".", "..") for part in name.split("/"))
                 and PurePosixPath(name).as_posix() == name and name.casefold() not in seen,
                 "Unsafe or duplicate transport member")
            need(member.isfile() or member.isdir(), "Nonregular transport member")
            seen.add(name.casefold())
            total += member.size
            need(len(seen) <= 2000 and total <= 4_000_000_000, "Prior transport exceeds registered bounds")
            if name not in expected_members:
                continue
            need(member.isfile(), "Expected checkpoint archive member is not a file")
            stream = archive.extractfile(member)
            h = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
            found[name] = h.hexdigest()
            need(found[name] == expected_members[name], "Checkpoint/source receipt differs from archived bytes")
    after = archive_path.stat()
    need(found == expected_members and before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
         "Required archived evidence is missing or archive changed during audit")
    return {"archive_sha256": expected_sha, "archive_bytes": before.st_size,
            "verified_required_members": len(found), "total_members": len(seen), "uncompressed_bytes": total}


def check_shutdown(execution_path, stop_receipt_path, reuse_created_utc, *, source_status=None, worker_exit_code=None):
    execution, stop = read(execution_path), read(stop_receipt_path)
    need(execution["finalize"]["status"] == stop["status"] == "CLOSED_VERIFIED_STOPPED"
         and execution["finalize"]["instance_state"] == stop["instance_state"] == "stopped", "Prior host shutdown is not verified")
    need(stop["action"] == "finalize" and stop["host_time_cap_observed"] is True
         and stop["within_reserve"] is True, "Prior attempt resource bound failed")
    need(Path(execution["finalize"]["receipt"]).resolve() == Path(stop_receipt_path).resolve(), "Stop receipt is not the execution-linked receipt")
    for key in ("host_time_cap_observed", "within_reserve", "gate_failed"):
        need(execution["finalize"][key] == stop[key], "Execution and detailed stop receipt disagree")
    need(timestamp(stop["stopped_observed_utc"]) <= timestamp(stop["recorded_utc"]) <= timestamp(reuse_created_utc),
         "Checkpoint staging preceded verified shutdown")
    # The controller's general gate_failed flag also records SSM worker errors.
    # GNU timeout exits 124 at the deliberately bounded worker deadline, even
    # when the host/resource gates passed. Preserve that original flag and
    # accept only this narrowly evidenced runtime exhaustion case.
    need(type(stop["gate_failed"]) is bool, "Prior gate_failed flag is not boolean")
    classification = "NO_RECORDED_GATE_FAILURE"
    evidence = None
    if stop["gate_failed"]:
        poll = execution.get("last_poll", {})
        need(poll.get("status") == "Failed" and poll.get("response_code") == 124
             and type(worker_exit_code) is int and worker_exit_code == 124,
             "Prior worker failure is not the documented bounded timeout")
        need(isinstance(source_status, dict)
             and source_status.get("status") in {"NORMAL_PHASE_RUNNING", "ATTACK_REPLAY_RUNNING"},
             "Bounded timeout requires an incomplete scientific phase")
        classification = "EXPECTED_BOUNDED_WORKER_TIMEOUT"
        evidence = {"ssm_status": poll["status"], "ssm_response_code": poll["response_code"],
                    "worker_exit_code": worker_exit_code, "scientific_phase": source_status["status"]}
    return execution, {"status": "CLOSED_VERIFIED_STOPPED", "execution_sha256": digest(execution_path),
                       "stop_receipt_sha256": digest(stop_receipt_path), "host_time_cap_observed": True,
                       "within_reserve": True, "stopped_before_staging": True,
                       "gate_failed": stop["gate_failed"], "worker_failure_classification": classification,
                       "bounded_timeout_evidence": evidence}


def check_qualification(qualification, expected_device):
    need(qualification["device"] == expected_device and qualification["reexecuted_in_continuation_process"] is True
         and qualification["reused_prior_qualification"] is False, "Current runtime qualification is missing or reused")
    q = qualification["qualification"]
    if expected_device.startswith("cuda"):
        need(q["status"] == "PASS" and q["cuda_parity_executed"] is True, "Current CUDA was not qualified")
        need({c["arm"] for c in q["checks"]} == {"mlp", "gin"} and len(q["checks"]) == 2, "Current qualification arm inventory differs")
        need(all(c["cpu_cuda_allclose"] is True and c["cuda_repeat_exact"] is True
                 and c["deterministic_backward_optimizer_step"] is True and c["finite_gradients"] is True for c in q["checks"]),
             "Current CUDA parity/determinism qualification failed")
    else:
        need(expected_device == "cpu" and q["status"] == "CPU_SELECTED" and q["cuda_parity_executed"] is False,
             "Unexpected current CPU qualification")
    return {"device": expected_device, "reexecuted_in_continuation_process": True, "qualification_status": q["status"]}


def check_reuse_content(config, manifest, reuse, reuse_dir, prior_output, output):
    need(reuse["schema"] == "normal-stability-checkpoint-reuse-v1" and reuse["status"] == "FROZEN_VERIFIED_ENCODER_CACHE_REUSE",
         "Wrong reuse manifest schema/status")
    need(reuse["checkpoint_file_count_each"] == 21 and reuse["completed_manifest_is_authority"] is True
         and reuse["completed_encoder_folds_counter_used"] is False and reuse["prior_banks_or_results_reused"] is False
         and reuse["all_banks_calibration_and_scores_rebuilt"] is True and reuse["scientific_settings_changed"] is False,
         "Reuse eligibility or scientific contract changed")
    expected = {}
    for dataset in config["datasets"]:
        spec = next(s for s in manifest["datasets"] if s["dataset"] == dataset)
        source_hashes = {Path(g["npz"]).stem: g["npz_sha256"] for g in spec["graphs"] if Path(g["npz"]).stem in science.NORMAL_GRAPHS}
        for fold, seed in itertools.product(config["folds"], config["encoder_seeds"]):
            relative = f"{dataset}/{fold['name']}/encoder_{seed}"
            expected[relative] = {"dataset": dataset, "fold": fold["name"], "encoder_seed": seed,
                                  "roles": {"fit": fold["fit"], "calibration": fold["calibration"], "normal_validation": fold["validation"]},
                                  "node_types": spec["metadata"]["node_feature_dim"], "relations": spec["metadata"]["edge_feature_dim"],
                                  "input_graph_sha256": source_hashes}
    inventory, members, reused, skipped = {}, {}, {}, set()
    for entry in reuse["entries"]:
        directory = entry["directory"]
        need(directory.startswith("checkpoints/"), "Unexpected staged checkpoint path")
        relative = directory[len("checkpoints/"):]
        need(relative in expected and relative not in reused, "Unexpected or repeated reusable checkpoint")
        spec = expected[relative]
        need(all(entry[key] == value for key, value in spec.items()), "Reusable checkpoint role/seed/data identity changed")
        need(set(entry["files"]) == checkpoint_names(spec["encoder_seed"]), "Reuse includes prior banks/results or incomplete encoder/cache files")
        for name, sha in entry["files"].items():
            for root, path in ((reuse_dir, directory + "/" + name), (prior_output, "private/" + relative + "/" + name),
                               (output, "private/" + relative + "/" + name)):
                need(digest(safe(root, path)) == sha, "Original/staged/copied checkpoint bytes differ")
            inventory[directory + "/" + name] = sha
            members["outputs/private/" + relative + "/" + name] = sha
        reused[relative] = entry
    for entry in reuse["skipped"]:
        relative = f"{entry['dataset']}/{entry['fold']}/encoder_{entry['encoder_seed']}"
        need(relative in expected and relative not in skipped and relative not in reused, "Unexpected or repeated skipped checkpoint")
        need(all(entry[key] == value for key, value in expected[relative].items()), "Skipped role/seed/data identity changed")
        need(entry["reason"] == "NO_COMPLETED_ENCODER_CACHE_MANIFEST_REFIT_FROM_SCRATCH"
             and not (prior_output / "private" / relative / "MANIFEST.json").exists(), "A completed checkpoint was excluded from reuse")
        skipped.add(relative)
    need(set(reused) | skipped == set(expected), "Reuse/refit partition is incomplete")
    actual_files = {p.relative_to(reuse_dir).as_posix() for p in reuse_dir.rglob("*") if p.is_file()}
    need(inventory == reuse["inventory"] and actual_files == set(inventory) | {"REUSE_MANIFEST.json"}, "Staging contains missing or unregistered files")
    source_receipts = {name: digest(prior_output / name) for name in SOURCE_RECEIPTS if (prior_output / name).is_file()}
    need("RUN_STATUS.json" in source_receipts and source_receipts == reuse["source_output_receipts"], "Original attempt source receipt binding differs")
    members.update({"outputs/" + name: sha for name, sha in source_receipts.items()})
    return expected, reused, skipped, members


def check_decisions(receipt, partial, expected, reused, output):
    decisions = {}
    for entry in receipt["decisions"]:
        relative = entry["relative"]
        need(relative in expected and relative not in decisions, "Unexpected or repeated continuation decision")
        need(entry["action"] == (REUSED if relative in reused else FRESH), "A reuse/refit decision differs from frozen eligibility")
        need(entry["manifest_sha256"] == digest(safe(output, "private/" + relative + "/MANIFEST.json")), "Decision completed-manifest hash differs")
        decisions[relative] = entry
    need(set(decisions) == set(expected), "Continuation decision grid incomplete")
    need(receipt["reused_checkpoint_count"] == len(reused) and receipt["fresh_checkpoint_count"] == len(expected) - len(reused), "Reuse/refit counts differ")
    need(partial["decisions"] == receipt["decisions"] and partial["reuse_manifest_sha256"] == receipt["reuse_manifest_sha256"], "Final and partial reuse decision receipts differ")
    return {"reused_checkpoints": len(reused), "fresh_checkpoints": len(expected) - len(reused), "total_checkpoints": len(expected)}


def audit(config_path, data_dir, original_registration_path, continuation_registration_path, reuse_dir, prior_output,
          prior_archive, prior_execution, prior_stop_receipt, output, scientific_audit_path):
    (config_path, data_dir, original_registration_path, continuation_registration_path, reuse_dir, prior_output,
     prior_archive, prior_execution, prior_stop_receipt, output, scientific_audit_path) = map(lambda p: Path(p).resolve(), (
        config_path, data_dir, original_registration_path, continuation_registration_path, reuse_dir, prior_output,
        prior_archive, prior_execution, prior_stop_receipt, output, scientific_audit_path))
    config, original, continuation, manifest, reuse = bind_registrations(config_path, data_dir, original_registration_path,
                                                                       continuation_registration_path, reuse_dir)
    for field, value in (("original_config_sha256", digest(config_path)), ("original_registration_sha256", digest(original_registration_path)),
                         ("original_source_commit", original["git_commit"]), ("data_manifest_sha256", original["data_manifest_sha256"])):
        need(reuse[field] == value, "Reuse scientific registration binding differs")
    results, receipt, qualification, scientific = (read(path) for path in (output / "RESULTS.json", output / "CONTINUATION_RECEIPT.json",
                                                                         output / "RUNTIME_QUALIFICATION.json", scientific_audit_path))
    need(scientific["status"] == "PASS" and scientific["results_sha256"] == digest(output / "RESULTS.json")
         and scientific["normal_freeze_sha256"] == digest(output / "NORMAL_FREEZE.json")
         and scientific["registration_sha256"] == digest(original_registration_path)
         and scientific["auditor_sha256"] == digest(Path(science.__file__)), "Original scientific audit is missing, stale or unrelated")
    need(receipt["status"] == "COMPLETE_RUNTIME_CONTINUATION_ORIGINAL_SCIENTIFIC_SETTINGS"
         and receipt["continuation_registration_sha256"] == digest(continuation_registration_path)
         and receipt["reuse_manifest_sha256"] == digest(reuse_dir / "REUSE_MANIFEST.json")
         and receipt["original_results_sha256"] == digest(output / "RESULTS.json")
         and receipt["runtime_device_qualification_sha256"] == digest(output / "RUNTIME_QUALIFICATION.json"), "Final continuation receipt binding differs")
    need(receipt["all_banks_calibration_and_scores_rebuilt"] is True
         and receipt["original_runner_all_normal_before_attack_labels_preserved"] is True and receipt["scientific_settings_changed"] is False,
         "Continuation scientific order changed")
    need(reuse["source_device"] == results["device"], "Continuation changes the numerical device")
    current_qualification = check_qualification(qualification, results["device"])
    source_status = read(prior_output / "RUN_STATUS.json")
    worker_exit_path = prior_output / "WORKER_EXIT.txt"
    worker_exit_code, worker_exit_sha = None, None
    if worker_exit_path.is_file():
        exit_bytes = worker_exit_path.read_bytes()
        need(0 < len(exit_bytes) <= 32, "Invalid worker exit receipt size")
        exit_text = exit_bytes.decode("ascii").strip()
        need(exit_text.isdecimal() and str(int(exit_text)) == exit_text and 0 <= int(exit_text) <= 255,
             "Invalid worker exit receipt")
        worker_exit_code = int(exit_text)
        worker_exit_sha = hashlib.sha256(exit_bytes).hexdigest()
    execution, shutdown = check_shutdown(prior_execution, prior_stop_receipt, reuse["created_utc"],
                                        source_status=source_status, worker_exit_code=worker_exit_code)
    need(reuse["transport_receipt_sha256"] == digest(prior_execution) and reuse["transport_receipt_filename"] == prior_execution.name,
         "Reuse is not bound to the completed prior execution/collection receipt")
    transport = reuse["transport"]
    need(transport["archive_sha256"] == execution["collection"]["transport_sha256"]
         and transport["archive_filename"] == prior_archive.name and transport["archive_bytes"] == prior_archive.stat().st_size
         and transport["selected_checkpoint_bytes_compared_to_archive_members"] is True, "Prior transport receipt differs")
    need(timestamp(reuse["created_utc"]) <= timestamp(continuation["created_utc"]) <= timestamp(results["started_utc"]),
         "Continuation ran before its reuse/registration freeze")
    for key, expected in (("config_sha256", digest(config_path)), ("registration_sha256", digest(original_registration_path)),
                           ("source_commit", original["git_commit"]), ("data_manifest_sha256", original["data_manifest_sha256"]),
                           ("device", reuse["source_device"])):
        need(source_status[key] == expected, "Prior source attempt does not match original science")
    expected, reused, skipped, members = check_reuse_content(config, manifest, reuse, reuse_dir, prior_output, output)
    need(transport["verified_member_sha256"] == members, "Reuse archive member binding is incomplete or includes prior scores")
    # WORKER_EXIT need not be part of the earlier operative reuse manifest; it
    # is additional independent evidence checked directly against the already
    # bound archive. This does not change prior manifests or controller flags.
    archive_members = dict(members)
    if worker_exit_sha is not None:
        archive_members["outputs/WORKER_EXIT.txt"] = worker_exit_sha
    archive = check_archive(prior_archive, execution["collection"]["transport_sha256"], archive_members)
    shutdown["worker_exit_sha256"] = worker_exit_sha
    shutdown["worker_exit_verified_against_archive"] = worker_exit_sha is not None
    counts = check_decisions(receipt, read(output / "REUSE_DECISIONS.partial.json"), expected, reused, output)
    return {"status": "PASS_CONTINUATION_CHAIN", "scope": "POST_RESULT_DEVELOPMENT", "created_utc": datetime.now(timezone.utc).isoformat(),
            "auditor_sha256": digest(Path(__file__)), "original_source_commit": original["git_commit"], "continuation_source_commit": continuation["git_commit"],
            "original_registration_sha256": digest(original_registration_path), "continuation_registration_sha256": digest(continuation_registration_path),
            "reuse_manifest_sha256": digest(reuse_dir / "REUSE_MANIFEST.json"), "continuation_receipt_sha256": digest(output / "CONTINUATION_RECEIPT.json"),
            "scientific_audit_sha256": digest(scientific_audit_path), "scientific_audit_status": scientific["status"],
            "results_sha256": digest(output / "RESULTS.json"), "counts": counts, "source_transport": archive, "prior_shutdown": shutdown,
            "current_runtime_qualification": current_qualification, "all_copied_checkpoint_bytes_equal_prior_archive": True,
            "prior_bank_calibration_attack_artifacts_excluded_from_reuse": True,
            "all_configured_roles_and_seeds_accounted_for": True, "scientific_settings_changed": False,
            "limits": ["This receipt supplements the separately passed scientific audit; it does not replace metric verification.",
                       "Runtime continuation and repeated evaluation are not independent scientific replications.",
                       "No novelty or untouched confirmation is established."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    names = ("config", "data-dir", "original-registration", "continuation-registration", "reuse-dir", "prior-output", "prior-archive",
             "prior-execution", "prior-stop-receipt", "output", "scientific-audit", "report")
    for name in names:
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    need(not args.report.exists(), "Preserve existing chain audit receipts")
    try:
        report = audit(*(getattr(args, name.replace("-", "_")) for name in names[:-1]))
    except Exception as error:
        report = {"status": "FAIL", "auditor_sha256": digest(Path(__file__)), "error_type": type(error).__name__, "reason": str(error),
                  "created_utc": datetime.now(timezone.utc).isoformat()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report), flush=True)
    return 0 if report["status"] == "PASS_CONTINUATION_CHAIN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
