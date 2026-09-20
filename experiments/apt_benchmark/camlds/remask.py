"""Stream a provenance-bound, pre-fit fixed-hostname text correction.

The old corpus is immutable. Every event's complete nontext structure is compared
before and after masking, including labels, query eligibility, source references,
timestamps, observed linkage fields, fragment order and event order. Raw logs are
not reparsed and no model is fitted or scored.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .acquire import digest
from .events import mask_fixed_hostnames

TEXT_FIELDS = ("text", "baseline_text")
ADDED_HOST_NAMES = ("linuxshare", "corpdns", "reposerver")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def nontext_structure(event):
    value = {key: item for key, item in event.items() if key != "fragments"}
    value["fragments"] = [{key: item for key, item in part.items() if key not in TEXT_FIELDS}
                          for part in event["fragments"]]
    return canonical(value)


def remask_event(event):
    before = nontext_structure(event)
    fields = Counter()
    changed_fragments = 0
    for part in event["fragments"]:
        changed = False
        for name in TEXT_FIELDS:
            if name not in part:
                continue
            value = mask_fixed_hostnames(part[name])
            if value != part[name]:
                part[name] = value
                fields[name] += 1
                changed = True
        changed_fragments += changed
    after = nontext_structure(event)
    if before != after:
        raise ValueError("Fixed text repair changed a prohibited nontext field")
    return changed_fragments, fields, before, after


def repair(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError("Refusing to overwrite source repair evidence")
    source_events = source / "EVENTS.jsonl"
    source_manifest = source / "MANIFEST.json"
    source_selection = source / "SELECTION.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    selection = json.loads(source_selection.read_text(encoding="utf-8"))
    selection_sha = digest(source_selection)
    if manifest["selection_sha256"] != selection_sha or manifest["selection"] != selection:
        raise ValueError("Prior manifest does not bind this selection")
    specification = {
        "reason": "Pre-fit source review found fixed cross-host LINUXSHARE identifiers in lexical feature text",
        "added_fixed_hostnames": list(ADDED_HOST_NAMES),
        "permitted_mutations": ["fragments[].text", "fragments[].baseline_text"],
        "prior_events_sha256": manifest["events_sha256"],
        "prior_manifest_sha256": digest(source_manifest),
        "prior_selection_sha256": selection_sha,
        "prior_adapter_sha256": selection["adapter_sha256"],
        "adapter_sha256": digest(Path(__file__).with_name("events.py")),
        "repair_code_sha256": digest(Path(__file__)),
        "raw_logs_reparsed": False, "models_fit_or_scored_by_repair": False,
    }
    amended_selection = deepcopy(selection)
    amended_selection["adapter_sha256"] = specification["adapter_sha256"]
    amended_selection["pre_fit_text_repair"] = specification
    destination.mkdir(parents=True)
    write_json(destination / "SELECTION.json", amended_selection)
    source_hash, output_hash = hashlib.sha256(), hashlib.sha256()
    nontext_before, nontext_after = hashlib.sha256(), hashlib.sha256()
    counts, fields, changed_runs = Counter(), Counter(), Counter()
    output_path = destination / "EVENTS.jsonl"
    temporary = output_path.with_suffix(".part")
    with source_events.open("rb") as reader, temporary.open("wb") as writer:
        for raw in reader:
            source_hash.update(raw)
            event = json.loads(raw.decode("utf-8"))
            changed, changed_fields, before, after = remask_event(event)
            nontext_before.update(before + b"\n")
            nontext_after.update(after + b"\n")
            counts["events"] += 1
            counts["fragments"] += len(event["fragments"])
            counts["eligible_queries"] += event.get("target_eligible", True)
            counts["changed_fragments"] += changed
            fields.update(changed_fields)
            if changed:
                counts["changed_events"] += 1
                changed_runs[event["run_id"]] += 1
                encoded = canonical(event) + b"\n"
            else:
                counts["byte_preserved_events"] += 1
                encoded = raw
            writer.write(encoded)
            output_hash.update(encoded)
            if counts["events"] % 100000 == 0:
                print(json.dumps({"verified_events": counts["events"], "changed_fragments": counts["changed_fragments"]}), flush=True)
    if source_hash.hexdigest() != manifest["events_sha256"]:
        raise ValueError("Prior event corpus does not match its frozen manifest")
    if counts["events"] != manifest["events"] or counts["eligible_queries"] != manifest["eligible_targets"]:
        raise ValueError("Source event or query roster count changed")
    if nontext_before.hexdigest() != nontext_after.hexdigest():
        raise ValueError("Nontext structure digest mismatch")
    if digest(source_manifest) != specification["prior_manifest_sha256"] or digest(source_selection) != selection_sha:
        raise ValueError("Prior metadata changed during repair")
    temporary.replace(output_path)
    receipt = {"status": "PASS", "specification": specification, "counts": dict(counts),
               "changed_fields": dict(fields), "changed_events_by_run": dict(changed_runs),
               "source_events_sha256_verified": source_hash.hexdigest(),
               "events_sha256": output_hash.hexdigest(),
               "selection_sha256": digest(destination / "SELECTION.json"),
               "nontext_before_sha256": nontext_before.hexdigest(),
               "nontext_after_sha256": nontext_after.hexdigest(),
               "all_nontext_fields_identical": True, "unchanged_records_byte_preserved": True,
               "source_corpus_preserved": True}
    write_json(destination / "REPAIR.json", receipt)
    amended_manifest = deepcopy(manifest)
    amended_manifest["events_sha256"] = receipt["events_sha256"]
    amended_manifest["selection"] = amended_selection
    amended_manifest["selection_sha256"] = receipt["selection_sha256"]
    amended_manifest["pre_fit_text_repair"] = {"receipt_sha256": digest(destination / "REPAIR.json"),
                                                "prior_events_sha256": specification["prior_events_sha256"],
                                                "prior_manifest_sha256": specification["prior_manifest_sha256"],
                                                "adapter_sha256": specification["adapter_sha256"],
                                                "repair_code_sha256": specification["repair_code_sha256"]}
    write_json(destination / "MANIFEST.json", amended_manifest)
    print(json.dumps({"complete": True, "counts": dict(counts), "events_sha256": receipt["events_sha256"],
                      "manifest_sha256": digest(destination / "MANIFEST.json")}), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repair(args.source, args.output)


if __name__ == "__main__":
    main()
