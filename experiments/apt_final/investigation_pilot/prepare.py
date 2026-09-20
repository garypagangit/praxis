"""Freeze factual questions and gold from the pinned archive, before scoring.

Uses an independent source-table scan for reference answers. No evaluated
retrieval method is imported here. Original telemetry is treated only as data.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import uuid
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_guid(value):
    if value is None or str(value).strip() in ("", "-"):
        return ""
    parsed = uuid.UUID(str(value))
    return str(parsed) if parsed.int else ""


def signature(record):
    return (record["host"], record["guid"], record["image"].casefold(),
            record["utc"], record["pid"])


def normalize(row, ref):
    assert row["Channel"].casefold() == "microsoft-windows-sysmon/operational"
    assert row["SourceName"] == "Microsoft-Windows-Sysmon"
    event_id = str(row["EventID"])
    assert event_id in ("1", "3")
    lowered = {key.lower(): value for key, value in row.items()}
    recovered = False
    if not lowered.get("processguid"):
        assert event_id == "1", "Unexpected missing network schema: hold, do not invent fields"
        lines = row["Message"].splitlines()
        assert lines[0] == "Process Create:"
        allowed = {"UtcTime", "ProcessGuid", "ProcessId", "Image", "ParentProcessGuid", "ParentProcessId", "ParentImage"}
        parsed = defaultdict(list)
        for line in lines[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                if key in allowed:
                    parsed[key].append(value)
        assert set(parsed) == allowed and all(len(v) == 1 for v in parsed.values())
        for key, values in parsed.items():
            if key != "ProcessId" and lowered.get(key.lower()):
                assert str(lowered[key.lower()]) == values[0]
            lowered[key.lower()] = values[0]
        recovered = True
    record = {
        "ref": ref, "kind": "creation" if event_id == "1" else "network",
        "host": str(lowered["hostname"]).casefold(),
        "guid": canonical_guid(lowered["processguid"]),
        "parent_guid": canonical_guid(lowered.get("parentprocessguid")),
        "image": str(lowered["image"]), "parent_image": str(lowered.get("parentimage", "")),
        "utc": datetime.fromisoformat(str(lowered["utctime"])).isoformat(timespec="microseconds"),
        "pid": str(lowered["processid"]), "parent_pid": str(lowered.get("parentprocessid", "")),
        "message_recovered": recovered,
    }
    assert record["guid"] and record["host"] and record["image"]
    if event_id == "3":
        record["connection"] = {key: str(lowered[key]) for key in
                                ("sourceip", "sourceport", "destinationip", "destinationport", "protocol", "initiated")}
    return record


def source_records(archive, protocol):
    content = archive.read_bytes()
    assert digest(content) == protocol["source_archive_sha256"]
    records = []
    count = 0
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        assert len(members) == 1 and members[0].file_size < 1024**3
        with z.open(members[0]) as stream:
            for ordinal, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                count += 1
                if str(row.get("Channel", "")).casefold() != "microsoft-windows-sysmon/operational":
                    continue
                if str(row.get("EventID", "")) not in ("1", "3"):
                    continue
                ref = digest(f"{members[0].filename}|{ordinal}|{digest(line)}".encode())
                record = normalize(row, ref)
                record["source_row"] = ordinal
                record["source_row_sha256"] = digest(line)
                records.append(record)
    assert count == protocol["source_json_records_expected"]
    creations = [r for r in records if r["kind"] == "creation"]
    networks = [r for r in records if r["kind"] == "network"]
    assert len({(r["host"], r["guid"]) for r in creations}) == protocol["source_creation_identities_expected"]
    assert len(networks) == protocol["source_network_records_expected"]
    assert len({r["ref"] for r in records}) == len(records)
    return records, count


def make_cases(records, protocol):
    creations = [r for r in records if r["kind"] == "creation"]
    networks = [r for r in records if r["kind"] == "network"]
    names = defaultdict(set)
    for r in creations:
        names[r["host"], PureWindowsPath(r["image"]).name.casefold()].add(r["guid"])
    parents = [r for r in creations if r["parent_guid"]]
    salt = protocol["sampling_salt"]
    selected = []
    population_sizes = {}
    selected_parents = set()
    for cohort in protocol["cohorts"]:
        name = cohort["name"]
        if name == "natural_parent":
            population = parents
        elif name == "natural_network":
            population = networks
        else:
            assert name == "ambiguous_parent"
            population = [r for r in parents if r["ref"] not in selected_parents and
                          len(names[r["host"], PureWindowsPath(r["parent_image"]).name.casefold()]) >= 2]
        population_sizes[name] = len(population)
        assert len(population) >= cohort["n"], "Insufficient eligible natural cases; do not substitute"
        def order(r):
            return digest(f"{salt}|{name}|{r['ref']}".encode()), r["ref"]
        for r in sorted(population, key=order)[:cohort["n"]]:
            kind = "owner_creation" if name == "natural_network" else "parent_creation"
            selected.append({"question_id": digest(f"{kind}|{r['ref']}".encode()),
                             "anchor_ref": r["ref"], "kind": kind, "stratum": name})
            if kind == "parent_creation":
                selected_parents.add(r["ref"])
    assert len({q["question_id"] for q in selected}) == sum(c["n"] for c in protocol["cohorts"])
    return selected, population_sizes


def gold_by_scan(question, records):
    # Independent exhaustive source scan, not an evaluated retrieval function/index.
    anchor = next(r for r in records if r["ref"] == question["anchor_ref"])
    target = anchor["parent_guid"] if question["kind"] == "parent_creation" else anchor["guid"]
    matching = [r for r in records if r["kind"] == "creation" and
                r["host"] == anchor["host"] and r["guid"] == target]
    signatures = {signature(r) for r in matching}
    status = "INSUFFICIENT_EVIDENCE" if not matching else ("ANSWER" if len(signatures) == 1 else "AMBIGUOUS")
    return {"question_id": question["question_id"], "status": status,
            "acceptable_refs": sorted(r["ref"] for r in matching) if status == "ANSWER" else [],
            "matching_refs": sorted(r["ref"] for r in matching),
            "target_identity_digest": digest(f"{anchor['host']}|{target}".encode())}


def jsonl(path, values):
    path.write_text("".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in values), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    protocol_path = Path(__file__).with_name("PROTOCOL.json")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    assert not args.manifest.exists(), "Do not overwrite a frozen preparation receipt"
    args.workspace.mkdir(parents=True, exist_ok=False)
    records, count = source_records(args.archive, protocol)
    questions, populations = make_cases(records, protocol)
    gold = [gold_by_scan(q, records) for q in questions]
    for name, values in [("records.jsonl", records), ("questions.jsonl", questions), ("gold.jsonl", gold)]:
        jsonl(args.workspace / name, values)
    manifest = {
        "status": "CASES_AND_REFERENCE_ANSWERS_FROZEN_BEFORE_SCORING",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": digest(protocol_path.read_bytes()),
        "preparation_code_sha256": digest(Path(__file__).read_bytes()),
        "archive_sha256": protocol["source_archive_sha256"],
        "total_source_rows": count, "normalized_records": len(records),
        "record_kinds": dict(Counter(r["kind"] for r in records)),
        "message_fallback_records": sum(r["message_recovered"] for r in records),
        "eligible_population_sizes": populations,
        "questions": questions,
        "files": {name: {"sha256": digest((args.workspace/name).read_bytes()), "bytes": (args.workspace/name).stat().st_size}
                  for name in ("records.jsonl", "questions.jsonl", "gold.jsonl")},
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("questions", "files")}, indent=2))
