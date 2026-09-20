"""Continue the original frozen experiment, reusing verified encoder caches only."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from unittest.mock import patch

from ..normal_stability import runner as original_runner
from . import checkpoints


OPERATIONAL_STARTUP_FILES = {"ENV_SELECTION.log", "VENV_SETUP.log", "DEPENDENCIES.log", "PYTHON.txt",
                             "GPU.txt", "ENVIRONMENT.json", "worker.log", "WORKER_STATUS.json"}


def validate_fresh_output(output):
    """The cloud bootstrap may create diagnostics before the scientific runner."""
    output = Path(output)
    if not output.exists():
        return
    if not output.is_dir() or output.is_symlink():
        raise FileExistsError("Continuation output is not a fresh operational directory")
    if any(not p.is_file() or p.is_symlink() or p.name not in OPERATIONAL_STARTUP_FILES for p in output.iterdir()):
        raise FileExistsError("Continuation output contains prior scientific or unexpected artifacts")
    status = output / "WORKER_STATUS.json"
    if status.exists():
        record = checkpoints.read(status)
        if (record.get("status") != "RUNNING" or record.get("runtime_continuation") is not True
                or record.get("scientific_settings_changed") is not False or record.get("runner_invocations") != 1):
            raise FileExistsError("Worker status does not describe one fresh continuation invocation")


def run(config_path, data_dir, output, original_registration_path, reuse_dir, registration_path, device_name):
    # Imported lazily so the independently owned continuation provenance module
    # remains the single authority for wrapper source and reuse registration.
    from .provenance import verify_registration
    config_path, data_dir, output, reuse_dir = map(Path, (config_path, data_dir, output, reuse_dir))
    verify_registration(config_path, data_dir, original_registration_path, reuse_dir, registration_path)
    reuse_manifest_sha = checkpoints.original.digest(reuse_dir / "REUSE_MANIFEST.json")
    record = checkpoints.verify_reuse(reuse_dir, config_path, data_dir, original_registration_path)
    config = checkpoints.read(config_path)
    # Permit only bootstrap diagnostics created before the one scientific run.
    validate_fresh_output(output)
    original_runner.old.configure_reproducibility(config["cpu_threads"])
    device = original_runner.old.select_device(device_name)
    if str(device) != record["source_device"]:
        raise ValueError("Continuation device differs from the source checkpoint device")
    qualification = original_runner.old.qualify_device(device)
    output.mkdir(parents=True, exist_ok=True)
    qualification_path = output / "RUNTIME_QUALIFICATION.json"
    checkpoints.write_new(qualification_path, {"device": str(device), "qualification": qualification,
        "reexecuted_in_continuation_process": True, "reused_prior_qualification": False})
    qualification_sha = checkpoints.original.digest(qualification_path)
    expected = {e["relative"]: e for e in checkpoints.expected_checkpoints(config, data_dir)}
    reusable = {e["directory"].removeprefix("checkpoints/"): e for e in record["entries"]}
    original_train = original_runner.train_and_cache
    decisions = []

    def train_or_reuse(paths, fit_names, roles, node_types, relations, supplied_config, seed, device, destination):
        destination = Path(destination).resolve()
        try:
            relative = destination.relative_to((output / "private").resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("Checkpoint request escapes continuation output") from exc
        if relative not in expected or any(d["relative"] == relative for d in decisions):
            raise ValueError("Unexpected or repeated continuation checkpoint request")
        spec = expected[relative]
        if (supplied_config != config or list(fit_names) != spec["roles"]["fit"]
                or roles != {k: v for k, v in spec["roles"].items() if k != "fit"}
                or seed != spec["encoder_seed"] or node_types != spec["node_types"] or relations != spec["relations"]
                or str(device) != record["source_device"]):
            raise ValueError("Continuation callback settings, roles, seed or device differ")
        for name, sha in spec["input_graph_sha256"].items():
            if str(Path(paths[name]).resolve()) != spec["paths"][name] or checkpoints.original.digest(paths[name]) != sha:
                raise ValueError("Continuation dataset source hashes or paths differ")
        if checkpoints.original.digest(reuse_dir / "REUSE_MANIFEST.json") != reuse_manifest_sha:
            raise ValueError("Reuse manifest changed after continuation started")
        if relative in reusable:
            entry = reusable[relative]
            if destination.exists():
                raise FileExistsError("Reused checkpoint destination already exists")
            for name, sha in entry["files"].items():
                source = checkpoints.safe_file(reuse_dir / entry["directory"], name)
                if checkpoints.original.digest(source) != sha:
                    raise ValueError("Staged checkpoint changed before reuse")
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                if checkpoints.original.digest(target) != sha:
                    raise ValueError("Copied checkpoint differs from frozen reuse bytes")
            manifest = checkpoints.read(destination / "MANIFEST.json")
            action = "REUSED_VERIFIED_ENCODER_AND_EIGHT_CACHES"
        else:
            manifest = original_train(paths, fit_names, roles, node_types, relations, supplied_config, seed, device, destination)
            action = "FRESH_ORIGINAL_TRAIN_AND_CACHE"
        decisions.append({"relative": relative, "action": action,
                          "manifest_sha256": checkpoints.original.digest(destination / "MANIFEST.json")})
        original_runner.write(output / "REUSE_DECISIONS.partial.json", {"reuse_manifest_sha256": reuse_manifest_sha, "decisions": decisions})
        return manifest

    with patch.object(original_runner, "train_and_cache", side_effect=train_or_reuse):
        result = original_runner.run(config_path, data_dir, output, original_registration_path, device_name)
    if len(decisions) != len(expected) or checkpoints.original.digest(reuse_dir / "REUSE_MANIFEST.json") != reuse_manifest_sha:
        raise ValueError("Incomplete continuation decisions or changed reuse manifest")
    checkpoints.write_new(output / "CONTINUATION_RECEIPT.json", {
        "status": "COMPLETE_RUNTIME_CONTINUATION_ORIGINAL_SCIENTIFIC_SETTINGS",
        "continuation_registration_sha256": checkpoints.original.digest(registration_path),
        "reuse_manifest_sha256": reuse_manifest_sha,
        "runtime_device_qualification_sha256": qualification_sha,
        "original_results_sha256": checkpoints.original.digest(output / "RESULTS.json"),
        "reused_checkpoint_count": sum(d["action"].startswith("REUSED") for d in decisions),
        "fresh_checkpoint_count": sum(d["action"].startswith("FRESH") for d in decisions),
        "decisions": decisions, "all_banks_calibration_and_scores_rebuilt": True,
        "original_runner_all_normal_before_attack_labels_preserved": True,
        "scientific_settings_changed": False})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "data-dir", "output", "original-registration", "reuse-dir", "registration"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    run(args.config, args.data_dir, args.output, args.original_registration, args.reuse_dir, args.registration, args.device)
