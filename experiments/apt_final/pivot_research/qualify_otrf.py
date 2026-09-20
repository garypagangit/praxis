"""Read a pinned public log archive; report feasibility, not model efficacy.

No archive extraction, payload execution, training, or attack-label inference.
Run: python qualify_otrf.py --archive PATH --output PATH
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import uuid
import zipfile

COMMIT = "d9d40ef123d2c87d5d3df28c96bcab4f0faccc87"
SOURCE = ("https://raw.githubusercontent.com/OTRF/Security-Datasets/" + COMMIT
          + "/datasets/compound/apt29/day1/apt29_evals_day1_manual.zip")
EXPECTED_BYTES = 13944973
EXPECTED_SHA256 = "98a073140860560d70080ace9142961be4f64b4862bae892d62d0f254d0fdbe5"
EXPECTED_BLOB = "7352679a173ec0310f9d0ed587782545182dd394"


def valid_guid(value):
    return bool(value and value not in ("-", "{00000000-0000-0000-0000-000000000000}"))


def qualify(archive):
    content = archive.read_bytes()
    assert len(content) == EXPECTED_BYTES, "Unexpected archive size"
    sha = hashlib.sha256(content).hexdigest()
    blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    assert sha == EXPECTED_SHA256 and blob == EXPECTED_BLOB, "Unexpected pinned data"
    rows = 0
    channels, hosts, fields, sysmon_ids = Counter(), Counter(), Counter(), Counter()
    creations = []
    message_fallback_rows = 0
    inventory = []
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        assert len(members) == 1 and sum(i.file_size for i in members) < 1024**3
        for member in members:
            name = member.filename.replace("\\", "/")
            p = PurePosixPath(name)
            assert not p.is_absolute() and ".." not in p.parts and ":" not in name
            assert not stat.S_ISLNK(member.external_attr >> 16)
            assert name.endswith(".json")
            inventory.append({"name": name, "expanded_bytes": member.file_size})
            with z.open(member) as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    assert isinstance(row, dict)
                    rows += 1
                    channel = str(row.get("Channel", ""))
                    host = str(row.get("Hostname", ""))
                    channels[channel] += 1
                    hosts[host] += 1
                    if channel.lower() != "microsoft-windows-sysmon/operational":
                        continue
                    event_id = str(row.get("EventID", ""))
                    sysmon_ids[event_id] += 1
                    if event_id != "1":
                        continue
                    normalized = {k.lower(): v for k, v in row.items()}
                    record = {k: str(normalized.get(k, "")) for k in
                              ("hostname", "processguid", "parentprocessguid", "image",
                               "parentimage", "utctime", "processid", "parentprocessid")}
                    for key, value in record.items():
                        fields[key] += bool(value)
                    if not record["processguid"]:
                        assert row.get("SourceName") == "Microsoft-Windows-Sysmon"
                        message = row.get("Message", "")
                        assert message.splitlines()[0] == "Process Create:"
                        allowed = {"UtcTime", "ProcessGuid", "ProcessId", "Image",
                                   "ParentProcessGuid", "ParentProcessId", "ParentImage"}
                        parsed = defaultdict(list)
                        for text in message.splitlines()[1:]:
                            if ": " in text:
                                key, value = text.split(": ", 1)
                                if key in allowed:
                                    parsed[key].append(value)
                        assert set(parsed) == allowed and all(len(v) == 1 for v in parsed.values())
                        for key, values in parsed.items():
                            # ProcessId at event-header level is not the created process ID.
                            if key != "ProcessId" and record[key.lower()]:
                                assert record[key.lower()] == values[0]
                            record[key.lower()] = values[0]
                        uuid.UUID(record["processguid"])
                        uuid.UUID(record["parentprocessguid"])
                        message_fallback_rows += 1
                    if record["utctime"]:
                        datetime.fromisoformat(record["utctime"])
                    creations.append(record)
    by_identity = defaultdict(list)
    by_name = defaultdict(list)
    by_minute = defaultdict(set)
    for row in creations:
        host = row["hostname"].casefold()
        guid = row["processguid"].casefold()
        if not valid_guid(guid):
            continue
        by_identity[host, guid].append(row)
        if not row["image"]:
            continue
        basename = PureWindowsPath(row["image"]).name.casefold()
        by_name[host, basename].append(row)
        if row["utctime"]:
            by_minute[host, basename, row["utctime"][:16]].add(guid)
    name_collisions = []
    for (host, basename), records in sorted(by_name.items()):
        guids = {r["processguid"].casefold() for r in records}
        paths = {r["image"].casefold() for r in records}
        if len(guids) > 1:
            name_collisions.append({"host": host, "basename": basename,
                                    "distinct_process_guids": len(guids),
                                    "distinct_full_paths": len(paths),
                                    "process_creation_rows": len(records)})
    resolved = 0
    unresolved = 0
    parent_image_disagreements = 0
    for row in creations:
        parent = row["parentprocessguid"].casefold()
        if not valid_guid(parent):
            continue
        parents = by_identity.get((row["hostname"].casefold(), parent), [])
        if not parents:
            unresolved += 1
            continue
        resolved += 1
        if row["parentimage"] and all(p["image"].casefold() != row["parentimage"].casefold()
                                       for p in parents):
            parent_image_disagreements += 1
    return {
        "status": "PUBLIC_ARTIFACT_QUALIFIED_NO_EFFICACY_EXPERIMENT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": SOURCE, "repository_commit": COMMIT,
        "archive_bytes": len(content), "sha256": sha, "git_blob_sha1": blob,
        "inventory": inventory, "json_records": rows,
        "channels": dict(sorted(channels.items())), "hosts": dict(sorted(hosts.items())),
        "sysmon_event_ids": dict(sorted(sysmon_ids.items(), key=lambda kv: int(kv[0]))),
        "sysmon_process_creation_records": len(creations),
        "nonempty_flattened_process_creation_fields": dict(sorted(fields.items())),
        "process_creation_records_recovered_from_message": message_fallback_rows,
        "unique_host_process_guid_keys": len(by_identity),
        "duplicate_creation_rows_per_identity": sum(len(v)-1 for v in by_identity.values()),
        "same_host_basename_groups": len(by_name),
        "same_host_basename_groups_with_multiple_guids": len(name_collisions),
        "same_host_basename_groups_with_multiple_paths": sum(x["distinct_full_paths"] > 1 for x in name_collisions),
        "same_host_basename_minute_groups_with_multiple_guids": sum(len(v) > 1 for v in by_minute.values()),
        "process_creation_rows_with_recorded_parent_creation": resolved,
        "process_creation_rows_without_recorded_parent_creation": unresolved,
        "parent_image_disagreements_on_resolved_creation_rows": parent_image_disagreements,
        "name_collision_groups": name_collisions,
        "limitations": [
            "One creation lacks flattened fields; seven fields are recovered from its validated Sysmon Message.",
            "One public APT29 emulation recording; not independent real APT campaigns.",
            "Same-name collisions are not measured LLM errors or proof of attack confusion.",
            "Exact identifier joins already resolve recorded parent relations; this is a mandatory baseline.",
            "A parent creation missing from this capture is not by itself corruption or an attack.",
            "No event-level attack labels or attack-story gold answers were qualified here.",
            "The whole recording is exposed development data, not a new blind test set.",
        ],
        "data_executed": False, "model_run": False, "archive_extracted": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in
                     ("name_collision_groups", "hosts", "channels", "limitations", "sysmon_event_ids")}))
