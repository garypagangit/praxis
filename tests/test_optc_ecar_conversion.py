from pathlib import Path

from scripts.convert_optc_ecar_to_edges import (
    iter_json_records,
    normalize_optc_event,
    parse_timestamp_nanos,
)


def test_normalize_optc_event_maps_ecar_fields(tmp_path: Path) -> None:
    record = {
        "timestamp": 1539120748904,
        "id": "b9af81fb-066c-4cd6-97cb-b284aabd2d4f",
        "hostname": "SysClient0201",
        "objectID": "ece465ca-edf9-48c0-b2be-642ee2dd86d6",
        "object": "PROCESS",
        "action": "CREATE",
        "actorID": "0f0b0dfe-5744-4361-9611-d3a59a1bdfbf",
        "pid": 3648,
        "ppid": 6260,
        "tid": 292,
        "principal": "SYSTEMIA\\user",
        "properties": {
            "image_path": "\\Device\\HarddiskVolume1\\cygwin64\\bin\\bash.exe",
            "command_line": "bash.exe -lc whoami",
        },
    }

    edge = normalize_optc_event(record, tmp_path / "sample.jsonl", 7)

    assert edge is not None
    assert edge["timestamp_nanos"] == 1539120748904000000
    assert edge["datum_type"] == "PROCESS_CREATE"
    assert edge["event_names"] == ["PROCESS_CREATE"]
    assert edge["record_index"] == 7
    assert edge["properties"]["hostname"] == "sysclient0201"
    assert edge["properties"]["exec"].endswith("bash.exe")
    assert edge["subject_uuid"] == "0f0b0dfe574443619611d3a59a1bdfbf"
    assert edge["object_uuid"] == "ece465caedf948c0b2be642ee2dd86d6"


def test_iter_json_records_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"timestamp": 1, "object": "FILE"}\n{"timestamp": 2}\n', encoding="utf-8")

    rows = list(iter_json_records(path))

    assert len(rows) == 2
    assert rows[0]["object"] == "FILE"


def test_parse_timestamp_nanos_reads_iso_offset() -> None:
    assert (
        parse_timestamp_nanos("2019-09-23T09:12:26.333-04:00")
        == 1569244346333000000
    )
