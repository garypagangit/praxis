"""Export explicitly selected telemetry to a restricted, verifiable package."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
CATEGORIES = {"operator", "target", "network", "service", "infrastructure", "cloud"}
EVENT_FIELDS = {"eventId", "timestamp", "ingestionTime", "logStreamName", "message"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
        delta = parsed.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        if delta.microseconds % 1000:
            raise ValueError("timestamps must have millisecond precision")
        return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid ISO 8601 timestamp: {value!r} ({exc})") from exc


def validate_sources(sources):
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a non-empty JSON array")
    seen = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("each source must be an object")
        source_id = source.get("id")
        if not isinstance(source_id, str) or not SOURCE_ID.fullmatch(source_id):
            raise ValueError("source id must be a safe alphanumeric, hyphen or underscore name")
        if source_id.lower() in seen:
            raise ValueError(f"duplicate source id: {source_id}")
        seen.add(source_id.lower())
        if not isinstance(source.get("category"), str) or source["category"] not in CATEGORIES:
            raise ValueError(f"invalid category for source {source_id}")
        kind = source.get("kind")
        if kind == "local":
            allowed = {"id", "category", "kind", "path", "allow_empty"}
            required = "path"
        elif kind == "cloudwatch":
            allowed = {"id", "category", "kind", "log_group", "log_stream_names", "allow_empty"}
            required = "log_group"
        else:
            raise ValueError(f"invalid kind for source {source_id}")
        if set(source) - allowed:
            raise ValueError(f"unknown source fields for {source_id}: {sorted(set(source) - allowed)}")
        if not isinstance(source.get(required), str) or not source[required].strip():
            raise ValueError(f"{required} is required for source {source_id}")
        if "allow_empty" in source and not isinstance(source["allow_empty"], bool):
            raise ValueError(f"allow_empty must be boolean for source {source_id}")
        if "log_stream_names" in source:
            names = source["log_stream_names"]
            if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n for n in names):
                raise ValueError(f"log_stream_names must be a non-empty list of names for {source_id}")
    return sources


def validate_event(event, start, end):
    if not isinstance(event, dict) or not EVENT_FIELDS <= event.keys():
        raise ValueError("event must contain eventId, timestamp, ingestionTime, logStreamName and message")
    for field in ("eventId", "logStreamName", "message"):
        if not isinstance(event[field], str) or (field != "message" and not event[field]):
            raise ValueError(f"event field {field} must be a string")
    for field in ("timestamp", "ingestionTime"):
        if type(event[field]) is not int:
            raise ValueError(f"event field {field} must be an integer in milliseconds")
    if not start <= event["timestamp"] < end:
        raise ValueError("event timestamp falls outside the half-open collection window")


def local_events(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at local source line {line_number}") from exc


def cloudwatch_events(client, source, start, end):
    from botocore.exceptions import BotoCoreError, ClientError

    request = {"logGroupName": source["log_group"], "startTime": start, "endTime": end - 1}
    if "log_stream_names" in source:
        request["logStreamNames"] = source["log_stream_names"]
    try:
        for page in client.get_paginator("filter_log_events").paginate(**request):
            yield from page["events"]
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"CloudWatch export failed for source {source['id']}: {exc}") from exc


def require_outside_git(output):
    parent = output.parent.resolve(strict=True)
    try:
        check = subprocess.run(
            ["git", "-C", str(parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git is required to check that restricted output is outside a worktree") from exc
    if check.returncode == 0:
        raise ValueError("restricted output must be outside every Git worktree")
    if check.returncode != 128 or "not a git repository" not in check.stderr.lower():
        raise RuntimeError("could not establish whether the output directory is inside a Git worktree")


def collect(sources, output, start, end, profile=None, region=None, client=None):
    validate_sources(sources)
    if type(start) is not int or type(end) is not int or start >= end:
        raise ValueError("start and end must define a non-empty millisecond interval")
    output = Path(output)
    require_outside_git(output)
    output.mkdir(mode=0o700)
    (output / "raw").mkdir(mode=0o700)
    manifest = {"schema": 1, "start_ms": start, "end_ms": end, "sources": []}
    for source in sources:
        source_id = source["id"]
        if source["kind"] == "cloudwatch":
            if client is None:
                import boto3

                client = boto3.Session(profile_name=profile, region_name=region).client("logs")
            events = cloudwatch_events(client, source, start, end)
        else:
            events = local_events(source["path"])
        target = output / "raw" / f"{source_id}.jsonl"
        seen = set()
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            for event in events:
                validate_event(event, start, end)
                if event["eventId"] in seen:
                    raise ValueError(f"duplicate event ID in source {source_id}")
                seen.add(event["eventId"])
                stream.write(canonical(event).decode("utf-8") + "\n")
        if not seen and not source.get("allow_empty", False):
            raise ValueError(f"source {source_id} has no events; set allow_empty explicitly if expected")
        manifest["sources"].append({
            "id": source_id,
            "category": source["category"],
            "kind": source["kind"],
            "origin": source["path"] if source["kind"] == "local" else source["log_group"],
            "log_stream_names": source.get("log_stream_names"),
            "allow_empty": source.get("allow_empty", False),
            "count": len(seen),
            "sha256": digest(target),
        })
    manifest["total"] = sum(source["count"] for source in manifest["sources"])
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_bytes(canonical(manifest) + b"\n")
    return digest(manifest_path)


def verify(output, anchor):
    output = Path(output)
    manifest_path = output / "MANIFEST.json"
    if not re.fullmatch(r"[0-9a-f]{64}", anchor):
        raise ValueError("anchor must be a lowercase SHA-256 digest")
    if manifest_path.is_symlink() or digest(manifest_path) != anchor:
        raise ValueError("manifest hash differs from the external anchor")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or type(manifest.get("start_ms")) is not int or type(manifest.get("end_ms")) is not int or manifest["start_ms"] >= manifest["end_ms"]:
        raise ValueError("invalid manifest schema or window")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("manifest must contain sources")
    expected = {"MANIFEST.json"}
    seen_sources = set()
    total = 0
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("invalid source in manifest")
        source_id = source.get("id")
        if not isinstance(source_id, str) or not SOURCE_ID.fullmatch(source_id) or source_id.lower() in seen_sources:
            raise ValueError("invalid or duplicate source ID in manifest")
        seen_sources.add(source_id.lower())
        relative = f"raw/{source_id}.jsonl"
        expected.add(relative)
        path = output / "raw" / f"{source_id}.jsonl"
        if path.is_symlink() or digest(path) != source.get("sha256"):
            raise ValueError(f"source hash mismatch: {source_id}")
        ids = set()
        for event in local_events(path):
            validate_event(event, manifest["start_ms"], manifest["end_ms"])
            if event["eventId"] in ids:
                raise ValueError(f"duplicate event ID in source {source_id}")
            ids.add(event["eventId"])
        if len(ids) != source.get("count") or (not ids and source.get("allow_empty") is not True):
            raise ValueError(f"source count mismatch: {source_id}")
        total += len(ids)
    entries = list(output.rglob("*"))
    if any(p.is_symlink() for p in entries):
        raise ValueError("package must not contain symbolic links")
    actual = {p.relative_to(output).as_posix() for p in entries if p.is_file()}
    directories = {p.relative_to(output).as_posix() for p in entries if p.is_dir()}
    if actual != expected or directories != {"raw"} or total != manifest.get("total"):
        raise ValueError("package file set or total count does not match manifest")
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("collect")
    export.add_argument("--sources", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--start", required=True, help="inclusive ISO 8601 timestamp with timezone")
    export.add_argument("--end", required=True, help="exclusive ISO 8601 timestamp with timezone")
    export.add_argument("--profile", help="AWS CLI profile for CloudWatch sources")
    export.add_argument("--region", help="AWS region for CloudWatch sources")
    check = commands.add_parser("verify")
    check.add_argument("--package", required=True, type=Path)
    check.add_argument("--anchor-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            sources = json.loads(args.sources.read_text(encoding="utf-8"))
            anchor = collect(sources, args.output, parse_time(args.start), parse_time(args.end), args.profile, args.region)
            print(f"Collection complete. Store this manifest SHA-256 outside the package: {anchor}")
        else:
            count = verify(args.package, args.anchor_sha256)
            print(f"Package verified: {count} events.")
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
