"""Independently verify frozen factual cases directly against their source ZIP.

Uses only Python's standard library; never imports preparation or method code.
No retrieval-method evaluation, training, inference, or archive extraction.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import uuid
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as stream:
        for ordinal, line in enumerate(stream, 1):
            require(bool(line.strip()), f"Blank JSONL row at {path.name}:{ordinal}")
            item = json.loads(line)
            require(isinstance(item, dict), f"Non-object JSONL row at {path.name}:{ordinal}")
            rows.append(item)
    return rows


def parsed_guid(value, optional=False):
    if value is None or str(value).strip() in ("", "-"):
        require(optional, "Required process GUID absent")
        return ""
    identifier = uuid.UUID(str(value))
    if identifier.int == 0:
        require(optional, "Required process GUID is zero")
        return ""
    return str(identifier)


def basename(path):
    # Source paths were independently checked as Windows paths.
    return path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].casefold()


def recover_creation(event):
    """Strictly parse the one observed Message-only creation without evaluation."""
    lines = event.get("Message", "").splitlines()
    require(lines and lines[0] == "Process Create:", "Unexpected fallback message header")
    wanted = {"UtcTime", "ProcessGuid", "ProcessId", "Image", "ParentProcessGuid",
              "ParentProcessId", "ParentImage"}
    fields = defaultdict(list)
    for line in lines[1:]:
        label, separator, value = line.partition(": ")
        if separator and label in wanted:
            fields[label].append(value)
    require(set(fields) == wanted, "Fallback is missing required fields")
    require(all(len(values) == 1 for values in fields.values()), "Duplicate fallback field")
    result = dict(event)
    for label, values in fields.items():
        # An unflattened event's top-level ProcessId belongs to event metadata.
        if label != "ProcessId" and event.get(label):
            require(str(event[label]) == values[0], f"Conflicting fallback field: {label}")
        result[label] = values[0]
    return result


def source_scan(archive, protocol):
    """Rebuild records from exact source rows, with independent field access."""
    require(file_hash(archive) == protocol["source_archive_sha256"], "Source archive hash mismatch")
    records = []
    total_rows = 0
    creation_ids = set()
    source_keys = set()
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        require(len(entries) == 1, "Unexpected archive member count")
        entry = entries[0]
        member = PurePosixPath(entry.filename.replace("\\", "/"))
        require(not member.is_absolute() and ".." not in member.parts
                and ":" not in str(member), "Unsafe archive member path")
        require(not entry.is_dir() and not stat.S_ISLNK(entry.external_attr >> 16),
                "Archive member is not a regular data file")
        require(entry.file_size < 1024 ** 3 and member.suffix == ".json", "Unexpected archive data size/type")
        with zipped.open(entry) as stream:
            for ordinal, raw in enumerate(stream, 1):
                if not raw.strip():
                    continue
                event = json.loads(raw)
                require(isinstance(event, dict), "Source row is not an object")
                total_rows += 1
                if str(event.get("Channel", "")).casefold() != "microsoft-windows-sysmon/operational":
                    continue
                event_id = str(event.get("EventID", ""))
                if event_id not in ("1", "3"):
                    continue
                require(event.get("SourceName") == "Microsoft-Windows-Sysmon", "Unexpected Sysmon provider")
                fallback = not bool(event.get("ProcessGuid"))
                if fallback:
                    require(event_id == "1", "Unqualified missing network fields")
                    event = recover_creation(event)
                source_key = (event["Hostname"].casefold(), event["Channel"], str(event["RecordNumber"]))
                require(source_key not in source_keys, "Duplicate host/channel/record-number event")
                source_keys.add(source_key)
                source_hash = sha(raw)
                reference = sha((entry.filename + "|" + str(ordinal) + "|" + source_hash).encode("utf-8"))
                stamp = datetime.fromisoformat(event["UtcTime"])
                require(stamp.tzinfo is None, "Unexpected timezone syntax in pinned Sysmon UTC field")
                record = {
                    "ref": reference,
                    "kind": "creation" if event_id == "1" else "network",
                    "host": event["Hostname"].casefold(),
                    "guid": parsed_guid(event["ProcessGuid"]),
                    "parent_guid": parsed_guid(event.get("ParentProcessGuid"), optional=True),
                    "image": event["Image"],
                    "parent_image": str(event.get("ParentImage", "")),
                    "utc": stamp.isoformat(timespec="microseconds"),
                    "pid": str(event["ProcessId"]),
                    "parent_pid": str(event.get("ParentProcessId", "")),
                    "message_recovered": fallback,
                    "source_row": ordinal,
                    "source_row_sha256": source_hash,
                }
                require(record["host"] and record["image"], "Empty source host/image")
                int(record["pid"])
                if event_id == "1":
                    key = (record["host"], record["guid"])
                    require(key not in creation_ids, "Duplicate creation identity in pinned capture")
                    creation_ids.add(key)
                else:
                    ipaddress.ip_address(event["SourceIp"])
                    ipaddress.ip_address(event["DestinationIp"])
                    require(all(0 <= int(event[k]) <= 65535 for k in ("SourcePort", "DestinationPort")),
                            "Invalid network port")
                    record["connection"] = {
                        normalized: str(event[source]) for normalized, source in (
                            ("sourceip", "SourceIp"), ("sourceport", "SourcePort"),
                            ("destinationip", "DestinationIp"), ("destinationport", "DestinationPort"),
                            ("protocol", "Protocol"), ("initiated", "Initiated"))
                    }
                records.append(record)
    require(total_rows == protocol["source_json_records_expected"], "Unexpected source row count")
    require(len(creation_ids) == protocol["source_creation_identities_expected"], "Unexpected creation count")
    require(sum(r["kind"] == "network" for r in records) == protocol["source_network_records_expected"],
            "Unexpected network count")
    require(sum(r["message_recovered"] for r in records) == 1, "Unexpected fallback count")
    require(len({r["ref"] for r in records}) == len(records), "Duplicate source reference")
    return records, total_rows


def select_questions(records, protocol):
    creations = [r for r in records if r["kind"] == "creation"]
    parent_anchors = [r for r in creations if r["parent_guid"]]
    name_groups = defaultdict(set)
    for r in creations:
        name_groups[(r["host"], basename(r["image"]))].add(r["guid"])
    require([(c["name"], c["n"]) for c in protocol["cohorts"]] == [
        ("natural_parent", 20), ("natural_network", 20), ("ambiguous_parent", 20)],
        "Auditor supports the frozen three-cohort design only")
    chosen_anchors = set()
    questions = []
    populations = {}
    for cohort in protocol["cohorts"]:
        label = cohort["name"]
        if label == "natural_parent":
            eligible = parent_anchors
        elif label == "natural_network":
            eligible = [r for r in records if r["kind"] == "network"]
        else:
            eligible = [r for r in parent_anchors if r["ref"] not in chosen_anchors
                        and len(name_groups[(r["host"], basename(r["parent_image"]))]) >= 2]
        populations[label] = len(eligible)
        require(len(eligible) >= cohort["n"], "Not enough eligible source anchors")
        ranked = sorted((sha((protocol["sampling_salt"] + "|" + label + "|" + r["ref"]).encode()),
                         r["ref"]) for r in eligible)
        for _, reference in ranked[:cohort["n"]]:
            kind = "owner_creation" if label == "natural_network" else "parent_creation"
            require(reference not in chosen_anchors, "Anchor reused across cohorts")
            chosen_anchors.add(reference)
            questions.append({"question_id": sha((kind + "|" + reference).encode()),
                              "anchor_ref": reference, "kind": kind, "stratum": label})
    require(len(questions) == len(chosen_anchors) == 60, "Unexpected question count")
    return questions, populations


def reference_answers(records, questions):
    anchors = {r["ref"]: r for r in records}
    creation_table = defaultdict(list)
    for r in records:
        if r["kind"] == "creation":
            creation_table[(r["host"], r["guid"])].append(r)
    answers = []
    for question in questions:
        anchor = anchors[question["anchor_ref"]]
        target = anchor["guid"] if question["kind"] == "owner_creation" else anchor["parent_guid"]
        candidates = creation_table.get((anchor["host"], target), [])
        metadata = {(r["image"].casefold(), r["utc"], r["pid"]) for r in candidates}
        state = "INSUFFICIENT_EVIDENCE" if not candidates else "ANSWER" if len(metadata) == 1 else "AMBIGUOUS"
        refs = sorted(r["ref"] for r in candidates)
        answers.append({"question_id": question["question_id"], "status": state,
                        "acceptable_refs": refs if state == "ANSWER" else [],
                        "matching_refs": refs,
                        "target_identity_digest": sha((anchor["host"] + "|" + target).encode())})
    return answers


def audit(archive, workspace, manifest_path, protocol_path, protocol_commit="c676234"):
    repository = Path(__file__).resolve().parents[3]
    protocol_rel = protocol_path.resolve().relative_to(repository).as_posix()
    committed = subprocess.run(["git", "show", protocol_commit + ":" + protocol_rel], cwd=repository,
                               check=True, capture_output=True).stdout
    full_commit = subprocess.run(["git", "rev-parse", protocol_commit + "^{commit}"], cwd=repository,
                                 check=True, capture_output=True, text=True).stdout.strip()
    require(protocol_path.read_bytes() == committed, "Protocol differs from frozen Git bytes")
    protocol = json.loads(committed)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["status"] == "CASES_AND_REFERENCE_ANSWERS_FROZEN_BEFORE_SCORING", "Unexpected case status")
    require(manifest["protocol_sha256"] == sha(committed), "Protocol manifest hash mismatch")
    require(manifest["archive_sha256"] == protocol["source_archive_sha256"], "Archive manifest hash mismatch")
    prepare_path = protocol_path.with_name("prepare.py")
    require(manifest["preparation_code_sha256"] == file_hash(prepare_path), "Preparation code hash mismatch")
    expected_files = {"records.jsonl", "questions.jsonl", "gold.jsonl"}
    require(set(manifest["files"]) == expected_files, "Unexpected private artifact inventory")
    hashes = {}
    for name in sorted(expected_files):
        path = workspace / name
        require(path.is_file() and not path.is_symlink(), "Missing or linked private artifact")
        observed = {"sha256": file_hash(path), "bytes": path.stat().st_size}
        require(manifest["files"][name] == observed, f"Artifact hash/size mismatch: {name}")
        hashes[name] = observed
    records, source_count = source_scan(archive, protocol)
    require(read_jsonl(workspace / "records.jsonl") == records,
            "Normalized records differ from independently parsed source truth")
    questions, populations = select_questions(records, protocol)
    require(read_jsonl(workspace / "questions.jsonl") == questions, "Question selection differs from frozen hash rule")
    require(manifest["questions"] == questions, "Manifest question list mismatch")
    require(manifest["eligible_population_sizes"] == populations, "Eligible population mismatch")
    expected_summary = {"total_source_rows": source_count, "normalized_records": len(records),
                        "record_kinds": dict(Counter(r["kind"] for r in records)),
                        "message_fallback_records": sum(r["message_recovered"] for r in records)}
    for key, value in expected_summary.items():
        require(manifest[key] == value, f"Manifest summary mismatch: {key}")
    answers = reference_answers(records, questions)
    require(read_jsonl(workspace / "gold.jsonl") == answers, "Reference answers differ from source reconstruction")
    classes = {cohort["name"]: dict(Counter(answer["status"] for question, answer in zip(questions, answers)
                                          if question["stratum"] == cohort["name"]))
               for cohort in protocol["cohorts"]}
    return {
        "status": "VERIFIED_REFERENCE_ANSWERS_FROM_PINNED_SOURCE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "reference_audit_passed": True,
        "frozen_protocol_commit": full_commit,
        "scope": "SOURCE_FACTS_AND_CASE_SELECTION_ONLY_NO_METHOD_EVALUATION",
        "input_hashes": {"archive_sha256": file_hash(archive), "protocol_sha256": sha(committed),
                         "case_manifest_sha256": file_hash(manifest_path),
                         "preparation_code_sha256": file_hash(prepare_path), "private_artifacts": hashes},
        "auditor_sha256": file_hash(Path(__file__)),
        "independent_source_counts": expected_summary,
        "eligible_population_sizes": populations,
        "question_count": len(questions), "cohort_counts": dict(Counter(q["stratum"] for q in questions)),
        "reference_answer_classes_by_cohort": classes,
        "checks": {"protocol_matches_frozen_git": True, "all_normalized_records_match_source": True,
                   "all_anchor_fields_match_source": True, "cohorts_have_disjoint_anchors": True,
                   "ordered_hash_selection_matches": True, "message_only_creation_preserved": True,
                   "utc_times_come_from_sysmon_utc_fields": True,
                   "all_60_reference_answers_match_independent_source_reconstruction": True,
                   "all_manifest_file_hashes_and_sizes_match": True},
        "preparation_or_method_code_imported": False, "model_or_method_run": False,
        "archive_extracted": False,
        "limitations": [
            "Reference truth is the recorded host/GUID relation and creation metadata, not malicious intent.",
            "Independent parsing and selection audit uses the same recording; it is not independent-data replication.",
            "Cohorts have distinct anchors, but process families, hosts and source evidence can overlap.",
            "One exposed APT29 emulation recording; no independent-campaign or blind-test claim.",
            "Missing creation records support insufficient evidence within this capture, not real-world nonexistence.",
            "Case enrichment and reference-class counts do not measure method efficacy or population prevalence.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("CASE_MANIFEST.json"))
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("PROTOCOL.json"))
    parser.add_argument("--protocol-commit", default="c676234")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("REFERENCE_AUDIT.json"))
    args = parser.parse_args()
    require(not args.output.exists(), "Do not overwrite an audit receipt")
    result = audit(args.archive, args.workspace, args.manifest, args.protocol, args.protocol_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "questions": result["question_count"],
                      "reference_answer_classes_by_cohort": result["reference_answer_classes_by_cohort"]}))
