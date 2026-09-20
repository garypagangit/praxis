"""Verify and stage completed normal encoder/cache checkpoints for continuation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile

from ..normal_stability import engine, provenance as original


SCHEMA = "normal-stability-checkpoint-reuse-v1"
STATUS = "FROZEN_VERIFIED_ENCODER_CACHE_REUSE"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, record):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def checkpoint_files(seed):
    return ["MANIFEST.json", "FIT_FREEZE.json", "PREPROCESSING.npz", f"mlp_{seed}.pt", f"gin_{seed}.pt",
            *(f"cache/{graph}/{condition}/{filename}" for graph in ("train0", "train1", "train2", "train3")
              for condition in ("clean", "masked") for filename in ("CACHE.npz", "CACHE.json"))]


def safe_file(root, relative):
    path = original.contained_file(root, relative)
    if not path.is_file() or (Path(root) / relative).is_symlink():
        raise ValueError("Missing or aliased checkpoint file: " + relative)
    return path


def expected_checkpoints(config, data_dir):
    manifest = read(Path(data_dir) / "MANIFEST.json")
    output = []
    for dataset in config["datasets"]:
        matches = [s for s in manifest["datasets"] if s["dataset"] == dataset]
        if len(matches) != 1:
            raise ValueError("Dataset manifest is missing or duplicated")
        spec = matches[0]
        paths = {Path(g["npz"]).stem: original.contained_file(data_dir, g["npz"]) for g in spec["graphs"]}
        normal = {name: original.digest(paths[name]) for name in ("train0", "train1", "train2", "train3")}
        if len(set(normal.values())) != 4:
            raise ValueError("Normal graph identities must be distinct")
        for fold in config["folds"]:
            for seed in config["encoder_seeds"]:
                roles = {"fit": fold["fit"], "calibration": fold["calibration"], "normal_validation": fold["validation"]}
                engine.validate_roles(paths, roles["fit"], {k: v for k, v in roles.items() if k != "fit"})
                output.append({"dataset": dataset, "fold": fold["name"], "encoder_seed": seed,
                               "relative": f"{dataset}/{fold['name']}/encoder_{seed}", "roles": roles,
                               "node_types": spec["metadata"]["node_feature_dim"],
                               "relations": spec["metadata"]["edge_feature_dim"],
                               "input_graph_sha256": normal,
                               "paths": {name: str(path.resolve()) for name, path in paths.items()}})
    if len({e["relative"] for e in output}) != len(output):
        raise ValueError("Duplicate configured checkpoint identity")
    return output


def verify_checkpoint(root, expected, config, source_device):
    """Validate one complete 21-file checkpoint; ignore all prior bank files."""
    root = Path(root)
    files = {name: original.digest(safe_file(root, name)) for name in checkpoint_files(expected["encoder_seed"])}
    manifest, freeze = read(root / "MANIFEST.json"), read(root / "FIT_FREEZE.json")
    if (manifest.get("status") != "NORMAL_FOLD_FIT_AND_CACHES_COMPLETE"
            or manifest.get("cache_count") != 8 or manifest.get("conditions") != config["conditions"]
            or manifest.get("fit_freeze_sha256") != files["FIT_FREEZE.json"]):
        raise ValueError("Checkpoint completion manifest or fit-freeze binding is invalid")
    for flag in ("target_labels_accessed", "attack_graphs_accessed", "nearest_neighbor_banks_fitted", "thresholds_selected"):
        if manifest.get(flag) is not False:
            raise ValueError("Checkpoint violates the label-free encoder/cache contract")
    for field in ("encoder_seed", "roles", "input_graph_sha256"):
        if manifest.get(field) != expected[field] or freeze.get(field) != expected[field]:
            raise ValueError("Checkpoint identity, roles, or source hashes differ: " + field)
    if (freeze.get("status") != "NORMAL_FOLD_ENCODERS_FROZEN_BEFORE_CACHING"
            or freeze.get("node_types") != expected["node_types"] or freeze.get("relations") != expected["relations"]
            or freeze.get("training_config") != {k: config[k] for k in engine.TRAINING_KEYS}
            or freeze.get("target_labels_accessed") is not False
            or freeze.get("calibration_or_validation_graphs_used_in_fit") is not False
            or freeze.get("fit_graphs_count") != 2):
        raise ValueError("Checkpoint training settings or normal-only role contract differ")
    expected_artifacts = {name: files[name] for name in ("PREPROCESSING.npz", f"mlp_{expected['encoder_seed']}.pt", f"gin_{expected['encoder_seed']}.pt")}
    if freeze.get("artifacts") != expected_artifacts:
        raise ValueError("Preprocessing or portable model checkpoint hash changed")
    # Safe weights-only loading checks actual native model shapes and scaler arrays.
    models, _, _, _ = engine.load_fold(root, "cpu", expected_freeze_sha256=files["FIT_FREEZE.json"])
    del models
    if set(manifest.get("caches", {})) != set(expected["input_graph_sha256"]):
        raise ValueError("Expected exactly four normal graph caches")
    for graph, views in manifest["caches"].items():
        if set(views) != set(config["conditions"]):
            raise ValueError("Expected both clean and masked cache views")
        for condition, entry in views.items():
            prefix = f"cache/{graph}/{condition}/"
            receipt = read(root / (prefix + "CACHE.json"))
            normalized = dict(entry)
            if (normalized.pop("receipt_sha256", None) != files[prefix + "CACHE.json"]
                    or normalized.get("cache_npz") != prefix + "CACHE.npz"
                    or normalized.get("receipt_path") != prefix + "CACHE.json"):
                raise ValueError("Cache receipt paths or hash changed")
            normalized.update(cache_npz="CACHE.npz", receipt_path="CACHE.json")
            if normalized != receipt or receipt.get("cache_sha256") != files[prefix + "CACHE.npz"]:
                raise ValueError("Cache manifest, receipt, or array hash changed")
            if (receipt.get("status") != "LABEL_FREE_REPRESENTATIONS_CACHED"
                    or receipt.get("graph_name") != graph or receipt.get("condition") != condition
                    or receipt.get("input_graph_sha256") != expected["input_graph_sha256"][graph]
                    or receipt.get("drop_probability") != config["conditions"][condition]
                    or receipt.get("target_labels_accessed") is not False
                    or receipt.get("model_fit_performed") is not False
                    or receipt.get("features_recomputed_from_retained_edges") is not True
                    or receipt.get("mask_reused_across_encoder_and_bank_seeds") is not True):
                raise ValueError("Cache source or label-free condition contract differs")
            mask = engine.condition_mask(receipt["n_edges"], condition, config["mask_seeds"][graph])
            if (receipt.get("mask_seed") != (config["mask_seeds"][graph] if condition == "masked" else None)
                    or receipt.get("mask_sha256") != hashlib.sha256(mask.tobytes()).hexdigest()
                    or receipt.get("observed_edges") != int(mask.sum())):
                raise ValueError("Cache does not use the original fixed graph mask")
            for arm in ("mlp", "gin"):
                extraction = receipt["extraction"][arm]
                if (extraction.get("checkpoint_sha256") != files[f"{arm}_{expected['encoder_seed']}.pt"]
                        or extraction.get("training_performed") is not False
                        or extraction.get("attack_labels_used") is not False
                        or extraction.get("deterministic_algorithms") is not True
                        or extraction.get("decoder_reconstruction_exact") is not True
                        or extraction.get("device") != source_device
                        or extraction.get("state_sha256_before") != extraction.get("state_sha256_after")):
                    raise ValueError("Cached representation extraction is not bound to the original weights/device")
    return files


def verify_transport(archive_path, expected_sha256, member_hashes):
    """Bind each staged source byte to a member of the verified collected archive."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("A valid collected transport SHA256 is required")
    archive_path = Path(archive_path)
    if original.digest(archive_path) != expected_sha256:
        raise ValueError("Original result archive does not match its transport SHA256")
    before = archive_path.stat()
    found = {}
    with tarfile.open(archive_path, mode="r|gz") as archive:
        for member in archive:
            if member.name not in member_hashes:
                continue
            if member.name in found or not member.isfile():
                raise ValueError("Repeated or non-file selected archive member")
            stream = archive.extractfile(member)
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            found[member.name] = digest.hexdigest()
            if found[member.name] != member_hashes[member.name]:
                raise ValueError("Collected output checkpoint differs from its archive member: " + member.name)
    after = archive_path.stat()
    if (found != member_hashes or before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns):
        raise ValueError("Archive members are missing or transport changed during verification")
    return {"archive_filename": archive_path.name, "archive_sha256": expected_sha256,
            "archive_bytes": before.st_size, "verified_member_sha256": found,
            "selected_checkpoint_bytes_compared_to_archive_members": True}


def prepare_reuse(prior_output, staging_dir, config_path, data_dir, original_registration_path,
                  transport_receipt_path=None, transport_archive_path=None, transport_sha256=None):
    """Create a new immutable-input staging tree before launching continuation."""
    prior_output, staging_dir = Path(prior_output), Path(staging_dir)
    if staging_dir.exists():
        raise FileExistsError("Reuse staging directory must be new")
    if transport_archive_path is None:
        raise ValueError("Original collected result.tar.gz is required to bind checkpoint origin")
    receipt_sha = original.digest(transport_receipt_path) if transport_receipt_path else None
    if transport_receipt_path:
        receipt_text = Path(transport_receipt_path).read_text(encoding="utf-8-sig").strip()
        if re.fullmatch(r"[0-9a-f]{64}", receipt_text):
            receipt_transport_sha = receipt_text
        else:
            receipt = json.loads(receipt_text)
            receipt_transport_sha = receipt.get("collection", receipt).get("transport_sha256")
        if transport_sha256 is not None and transport_sha256 != receipt_transport_sha:
            raise ValueError("Explicit archive SHA differs from the collection receipt")
        transport_sha256 = receipt_transport_sha
    registration = original.verify_registration(config_path, data_dir, original_registration_path)
    config = read(config_path)
    source_status = read(prior_output / "RUN_STATUS.json")
    bindings = {"config_sha256": original.digest(config_path), "registration_sha256": original.digest(original_registration_path),
                "data_manifest_sha256": original.digest(Path(data_dir) / "MANIFEST.json"), "source_commit": registration["git_commit"]}
    if any(source_status.get(k) != value for k, value in bindings.items()):
        raise ValueError("Prior output is not bound to the current original source/config/data/registration")
    if source_status.get("device") not in ("cpu", "cuda", "cuda:0"):
        raise ValueError("Prior output device is missing or unsupported")
    receipts = {name: original.digest(prior_output / name) for name in
                ("RUN_STATUS.json", "NORMAL_RESULTS.partial.json", "NORMAL_RESULTS.json", "NORMAL_FREEZE.json", "RESULTS.json")
                if (prior_output / name).is_file()}
    entries, skipped = [], []
    for expected in expected_checkpoints(config, data_dir):
        root = prior_output / "private" / expected["relative"]
        public = {k: v for k, v in expected.items() if k not in ("paths", "relative")}
        if not (root / "MANIFEST.json").exists():
            skipped.append({**public, "reason": "NO_COMPLETED_ENCODER_CACHE_MANIFEST_REFIT_FROM_SCRATCH"})
            continue
        files = verify_checkpoint(root, expected, config, source_status["device"])
        entries.append({**public, "directory": "checkpoints/" + expected["relative"], "files": files})
    archive_members = {"outputs/" + name: sha for name, sha in receipts.items()}
    archive_members.update({"outputs/private/" + entry["directory"].removeprefix("checkpoints/") + "/" + name: sha
                            for entry in entries for name, sha in entry["files"].items()})
    transport = verify_transport(transport_archive_path, transport_sha256, archive_members)
    staging_dir.mkdir(parents=True)
    inventory = {}
    for entry in entries:
        source = prior_output / "private" / entry["directory"].removeprefix("checkpoints/")
        for relative, sha in entry["files"].items():
            target = staging_dir / entry["directory"] / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe_file(source, relative), target)
            if original.digest(target) != sha or original.digest(source / relative) != sha:
                raise ValueError("Checkpoint changed while being staged")
            inventory[(target.relative_to(staging_dir)).as_posix()] = sha
    if any(original.digest(prior_output / name) != sha for name, sha in receipts.items()):
        raise ValueError("Prior output changed during checkpoint staging; use an immutable collected snapshot")
    record = {"schema": SCHEMA, "status": STATUS, "created_utc": datetime.now(timezone.utc).isoformat(),
              "original_config_sha256": bindings["config_sha256"],
              "original_registration_sha256": bindings["registration_sha256"],
              "original_source_commit": bindings["source_commit"],
              "data_manifest_sha256": bindings["data_manifest_sha256"], "source_device": source_status["device"],
              "source_output_receipts": receipts,
              "transport_receipt_sha256": receipt_sha, "transport": transport,
              "transport_receipt_filename": Path(transport_receipt_path).name if transport_receipt_path else None,
              "entries": entries, "skipped": skipped, "inventory": inventory,
              "checkpoint_file_count_each": 21, "completed_manifest_is_authority": True,
              "completed_encoder_folds_counter_used": False, "prior_banks_or_results_reused": False,
              "all_banks_calibration_and_scores_rebuilt": True, "scientific_settings_changed": False}
    write_new(staging_dir / "REUSE_MANIFEST.json", record)
    return record


def verify_reuse(reuse_dir, config_path, data_dir, original_registration_path):
    reuse_dir = Path(reuse_dir)
    registration = original.verify_registration(config_path, data_dir, original_registration_path)
    config, record = read(config_path), read(reuse_dir / "REUSE_MANIFEST.json")
    if (record.get("schema") != SCHEMA or record.get("status") != STATUS
            or record.get("original_config_sha256") != original.digest(config_path)
            or record.get("original_registration_sha256") != original.digest(original_registration_path)
            or record.get("original_source_commit") != registration["git_commit"]
            or record.get("data_manifest_sha256") != original.digest(Path(data_dir) / "MANIFEST.json")
            or record.get("scientific_settings_changed") is not False
            or record.get("prior_banks_or_results_reused") is not False
            or record.get("all_banks_calibration_and_scores_rebuilt") is not True):
        raise ValueError("Reuse manifest does not match the original frozen experiment")
    transport = record.get("transport", {})
    if (transport.get("selected_checkpoint_bytes_compared_to_archive_members") is not True
            or not re.fullmatch(r"[0-9a-f]{64}", transport.get("archive_sha256", ""))):
        raise ValueError("Reuse checkpoint origin is not bound to a verified collected archive")
    expected = {"checkpoints/" + e["relative"]: e for e in expected_checkpoints(config, data_dir)}
    inventory, seen = {}, set()
    for entry in record["entries"]:
        directory = entry["directory"]
        if directory not in expected or directory in seen:
            raise ValueError("Unexpected or duplicate reused checkpoint")
        seen.add(directory)
        spec = expected[directory]
        for field in ("dataset", "fold", "encoder_seed", "roles", "node_types", "relations", "input_graph_sha256"):
            if entry.get(field) != spec[field]:
                raise ValueError("Reuse checkpoint identity has changed: " + field)
        checked = verify_checkpoint(reuse_dir / directory, spec, config, record["source_device"])
        if checked != entry["files"]:
            raise ValueError("Staged checkpoint bytes changed after the reuse manifest was frozen")
        inventory.update({directory + "/" + name: sha for name, sha in checked.items()})
    skipped = {f"checkpoints/{e['dataset']}/{e['fold']}/encoder_{e['encoder_seed']}" for e in record["skipped"]}
    if (len(skipped) != len(record["skipped"]) or seen & skipped or seen | skipped != set(expected)
            or inventory != record.get("inventory")):
        raise ValueError("Reuse manifest inventory is incomplete or inconsistent")
    archive_members = {"outputs/" + name: sha for name, sha in record["source_output_receipts"].items()}
    archive_members.update({"outputs/private/" + name.removeprefix("checkpoints/"): sha for name, sha in inventory.items()})
    if transport.get("verified_member_sha256") != archive_members:
        raise ValueError("Selected checkpoint transport member hashes are inconsistent")
    actual = {p.relative_to(reuse_dir).as_posix() for p in reuse_dir.rglob("*") if p.is_file()}
    if actual != set(inventory) | {"REUSE_MANIFEST.json"}:
        raise ValueError("Reuse staging tree contains unregistered files")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prior-output", "staging-dir", "config", "data-dir", "original-registration"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--transport-receipt", type=Path)
    parser.add_argument("--transport-archive", type=Path, required=True)
    parser.add_argument("--transport-sha256")
    args = parser.parse_args()
    report = prepare_reuse(args.prior_output, args.staging_dir, args.config, args.data_dir,
                           args.original_registration, args.transport_receipt, args.transport_archive, args.transport_sha256)
    print(json.dumps({"eligible_checkpoints": len(report["entries"]), "fresh_checkpoints": len(report["skipped"]),
                      "copied_files": len(report["inventory"])}))
