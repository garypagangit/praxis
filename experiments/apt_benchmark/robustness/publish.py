"""Publish a fixed allowlist of aggregate evidence, never source logs/models."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from .run import sha256, save_json


def publish(run_dir, manifest_path, events_path, destination):
    run_dir, manifest_path, events_path, destination = map(Path, (run_dir, manifest_path, events_path, destination))
    result = json.loads((run_dir / "RESULTS.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if result["status"] != "COMPLETE":
        raise ValueError("Only complete results can be published")
    event_hash = sha256(events_path)
    if event_hash != result["input_sha256"] or event_hash != manifest["events_sha256"]:
        raise ValueError("Event corpus/manifest/result hash mismatch")
    if sha256(manifest_path) != result["manifest_sha256"]:
        raise ValueError("Source manifest changed after fitting")
    destination.mkdir(parents=True, exist_ok=True)
    public_fields = {
        "dataset", "schema_version", "status", "source_url", "source_release", "license",
        "paper_doi", "dataset_url", "events_sha256", "events", "fragments", "source_pairs",
        "annotated_events", "annotated_fragments", "channel_counts", "fragment_count_distribution",
        "decoding_counts", "per_run", "label_policy", "availability", "limitations",
        "adapter_sha256", "baseline_normalizer_sha256", "totals", "split_counts",
        "source_techniques_on_targets", "doubtful_annotations_excluded", "selection",
        "prediction_unit", "target_ids_frozen", "causal_context", "splits", "label_scope",
        "feature_policy", "annotation_join", "prefit_amendment",
    }
    qualification = {k: v for k, v in manifest.items() if k in public_fields}
    qualification["source_manifest_sha256"] = result["manifest_sha256"]
    copied = {}
    for name in ("RESULTS.json", "REPORT.md", "PRE_FIT_RECEIPT.json"):
        target = destination / name
        if target.exists() and sha256(target) != sha256(run_dir / name):
            raise ValueError("Refusing to overwrite different published evidence")
        shutil.copyfile(run_dir / name, target)
        copied[name] = sha256(target)
    save_json(destination / "DATASET_QUALIFICATION.json", qualification)
    copied["DATASET_QUALIFICATION.json"] = sha256(destination / "DATASET_QUALIFICATION.json")
    save_json(destination / "PUBLICATION.json", {"status": "AGGREGATE_ONLY", "sha256": copied,
                                                "raw_logs_models_and_predictions_published": False})
    return copied


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.run, args.manifest, args.events, args.output), indent=2))
