import json
import subprocess
import sys
from pathlib import Path

import pytest

from collector import collect, parse_time, verify


def event(event_id, timestamp):
    return {
        "eventId": event_id,
        "timestamp": timestamp,
        "ingestionTime": timestamp + 1,
        "logStreamName": "example",
        "message": "synthetic event",
    }


def source_file(tmp_path, events):
    path = tmp_path / "input.jsonl"
    path.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")
    return {"id": "operator", "kind": "local", "category": "operator", "path": str(path)}


def test_local_export_verifies_and_detects_changes(tmp_path):
    source = source_file(tmp_path, [event("a", 100), event("b", 199)])
    output = tmp_path / "package"
    anchor = collect([source], output, 100, 200)
    assert verify(output, anchor) == 2
    with (output / "raw" / "operator.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(output, anchor)


def test_cloudwatch_pagination_and_exclusive_end(tmp_path):
    class Paginator:
        def paginate(self, **kwargs):
            assert kwargs == {"logGroupName": "/lab/test", "startTime": 100, "endTime": 199}
            yield {"events": [event("a", 100)]}
            yield {"events": [event("b", 199)]}

    class Client:
        def get_paginator(self, operation):
            assert operation == "filter_log_events"
            return Paginator()

    sources = [{"id": "network", "kind": "cloudwatch", "category": "network", "log_group": "/lab/test"}]
    output = tmp_path / "cloud"
    anchor = collect(sources, output, 100, 200, client=Client())
    assert verify(output, anchor) == 2
    (output / "extra").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="file set"):
        verify(output, anchor)


@pytest.mark.parametrize("events", [
    [event("a", 200)],
    [event("a", 100), event("a", 101)],
    [],
])
def test_invalid_or_empty_input_never_produces_complete_manifest(tmp_path, events):
    source = source_file(tmp_path, events)
    output = tmp_path / "incomplete"
    with pytest.raises(ValueError):
        collect([source], output, 100, 200)
    assert not (output / "MANIFEST.json").exists()


def test_explicit_empty_source_and_existing_output(tmp_path):
    source = source_file(tmp_path, [])
    source["allow_empty"] = True
    output = tmp_path / "empty"
    anchor = collect([source], output, 100, 200)
    assert verify(output, anchor) == 0
    with pytest.raises(FileExistsError):
        collect([source], output, 100, 200)


def test_rejects_git_worktree_output(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path / "repo")], check=True)
    source = source_file(tmp_path, [event("a", 100)])
    with pytest.raises(ValueError, match="outside every Git worktree"):
        collect([source], tmp_path / "repo" / "package", 100, 200)


def test_timestamp_requires_timezone_and_millisecond_precision():
    assert parse_time("1970-01-01T00:00:00.123Z") == 123
    with pytest.raises(ValueError, match="timezone"):
        parse_time("2026-01-01T00:00:00")
    with pytest.raises(ValueError, match="millisecond"):
        parse_time("2026-01-01T00:00:00.123456Z")


def test_cli_collect_and_verify(tmp_path):
    source = source_file(tmp_path, [event("a", 100)])
    configuration = tmp_path / "sources.json"
    configuration.write_text(json.dumps([source]), encoding="utf-8")
    output = tmp_path / "package"
    script = Path(__file__).with_name("collector.py")
    collected = subprocess.run(
        [sys.executable, str(script), "collect", "--sources", str(configuration), "--output", str(output),
         "--start", "1970-01-01T00:00:00.100Z", "--end", "1970-01-01T00:00:00.200Z"],
        text=True, capture_output=True, check=True,
    )
    anchor = collected.stdout.strip().split()[-1]
    verified = subprocess.run(
        [sys.executable, str(script), "verify", "--package", str(output), "--anchor-sha256", anchor],
        text=True, capture_output=True, check=True,
    )
    assert verified.stdout.strip() == "Package verified: 1 events."
    assert "synthetic event" not in collected.stdout
