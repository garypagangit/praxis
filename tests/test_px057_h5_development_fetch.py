from __future__ import annotations

import io
import json
import tarfile

import pytest

from scripts.fetch_px057_h5_development_pilot import (
    safe_extract,
    sha256_file,
    verify_bundle,
)


def write_json(path, value) -> None:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def write_jsonl(path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def make_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    ids = ["q1", "q2"]
    write_jsonl(bundle / "selected_rows.jsonl", [{"question_id": q} for q in ids])
    write_jsonl(bundle / "reasoning_traces.jsonl", [{"question_id": q} for q in ids])
    write_jsonl(
        bundle / "raw_generations.jsonl",
        [
            {"question_id": q, "round": round_index}
            for q in ids
            for round_index in (1, 2)
        ],
    )
    write_json(bundle / "collection_summary.json", {"claim_boundary": "development"})
    collection = {
        name: {"sha256": sha256_file(bundle / name)}
        for name in (
            "selected_rows.jsonl",
            "reasoning_traces.jsonl",
            "raw_generations.jsonl",
            "collection_summary.json",
        )
    }
    write_json(
        bundle / "cloud_job_evidence.json",
        {
            "status": "PASS",
            "confirmatory_evidence": False,
            "cell_id": "c1",
            "job_name": "job",
            "git_commit": "a" * 40,
            "experiment_id": "dev",
            "collection_verification": {"files": collection},
        },
    )
    return bundle


def test_verify_bundle_binds_identity_cardinality_and_hashes(tmp_path) -> None:
    bundle = make_bundle(tmp_path)
    result = verify_bundle(
        bundle,
        config={
            "experiment_id": "dev",
            "claim_boundary": "development",
            "generation": {"pilot_n": 2, "rounds": 2},
        },
        cell={"cell_id": "c1"},
        launch={"job_name": "job", "git_commit": "a" * 40},
    )

    assert result["status"] == "PASS"
    assert result["rows"] == 2
    assert result["generations"] == 4


def test_verify_bundle_rejects_tampered_collection_file(tmp_path) -> None:
    bundle = make_bundle(tmp_path)
    with (bundle / "raw_generations.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"question_id": "q1", "round": 3}) + "\n")

    with pytest.raises(ValueError, match="cardinality"):
        verify_bundle(
            bundle,
            config={
                "experiment_id": "dev",
                "claim_boundary": "development",
                "generation": {"pilot_n": 2, "rounds": 2},
            },
            cell={"cell_id": "c1"},
            launch={"job_name": "job", "git_commit": "a" * 40},
        )


def test_safe_extract_rejects_path_traversal(tmp_path) -> None:
    archive_path = tmp_path / "bad.tar.gz"
    payload = b"escape"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("../escape.txt")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    with pytest.raises(ValueError, match="unsafe model artifact"):
        safe_extract(archive_path, tmp_path / "out")
