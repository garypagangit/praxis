"""Acquire the predeclared internal-zone subset without model execution."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

from acquire import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output
    index = json.loads((root / "INDEX_717871.json").read_text())
    selected = []
    for item in index["members"]:
        match = re.search(r"/D(\d+)_", item["name"])
        if match and (int(match[1]) in (1, 8) or int(match[1]) >= 15):
            selected.append((int(match[1]), item))
    selected.sort()
    if [d for d, _ in selected] != [1, 8] + list(range(15, 29)):
        raise ValueError("Author archive does not contain the expected fixed days")
    plan = {
        "dataset_doi": "10.57745/Y5JLDG", "version": "2.0", "file_id": 717871,
        "zone": "green_internal", "days": [d for d, _ in selected],
        "reason": "All final fourteen evaluation days; one Monday from each prior benign week, within initial2GB cap. Selected from archive metadata and author chronology, never model outcomes.",
        "compressed_member_bytes": sum(m["compressed_bytes"] for _, m in selected),
        "uncompressed_member_bytes": sum(m["uncompressed_bytes"] for _, m in selected),
        "source_metadata_sha256": index["metadata_sha256"],
        "scientific_fits": 0, "members": [m["name"] for _, m in selected],
    }
    plan_path = root / "ACQUISITION_PLAN.json"
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError("Refusing to change an existing acquisition plan")
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    for day, member in selected:
        name = "717871_" + re.sub(r"[^A-Za-z0-9_.-]", "_", member["name"])
        target = root / "members" / name
        if target.exists():
            record = json.loads(target.with_suffix(target.suffix + ".receipt.json").read_text())
            digest = hashlib.file_digest(target.open("rb"), "sha256").hexdigest()
            if digest != record["sha256"] or target.stat().st_size != member["uncompressed_bytes"]:
                raise ValueError("Existing acquired member failed revalidation")
            print(json.dumps({"day": day, "status": "EXISTING_VERIFIED"}), flush=True)
            continue
        print(json.dumps({"day": day, "status": "ACQUIRING", "compressed_bytes": member["compressed_bytes"]}), flush=True)
        run(SimpleNamespace(metadata=root / "dataset_metadata.body", output=root,
                            file_id=717871, member=member["name"],
                            max_uncompressed_bytes=650_000_000))


if __name__ == "__main__":
    main()
