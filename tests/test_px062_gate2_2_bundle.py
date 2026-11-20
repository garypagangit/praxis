import io
import tarfile

import pytest
from pathlib import Path

from scripts.build_px062_gate2_2_bundle import (
    build_manifest,
    deterministic_archive,
    sha256_file,
    validate_frozen_config,
)


def test_archive_is_byte_deterministic_and_closed_world(tmp_path):
    files = {"z.txt": b"z\n", "a/b.txt": b"b\n"}
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    deterministic_archive(files, first)
    deterministic_archive(dict(reversed(list(files.items()))), second)
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as handle:
        assert handle.getnames() == ["a/b.txt", "z.txt"]
        assert all(not member.issym() and not member.islnk() for member in handle)


def test_manifest_registers_but_does_not_embed_answer_key():
    manifest = build_manifest(
        source_commit="a" * 40,
        files={"config.json": b"{}\n", "tasks.jsonl": b"{}\n"},
        config={"experiment_id": "e", "protocol_version": "2.2.0"},
        answer_key_raw=b'{"expected_skill":"secret"}\n',
    )
    assert manifest["answer_key_blinding"]["included_in_archive"] is False
    assert "answer_key" not in manifest["files"]
    assert "secret" not in str(manifest)


def test_bundle_refuses_draft_or_placeholder_hashes():
    with pytest.raises(ValueError, match="not frozen"):
        validate_frozen_config({"status": "DRAFT", "source_integrity": {}})
    with pytest.raises(ValueError, match="unfrozen"):
        validate_frozen_config(
            {
                "status": "FROZEN_PREREGISTERED",
                "source_integrity": {"tasks_sha256": "PENDING"},
            }
        )


def test_bundle_accepts_only_canonical_lower_hex_hashes():
    validate_frozen_config(
        {
            "status": "FROZEN_PREREGISTERED",
            "source_integrity": {
                "tasks_sha256": "0" * 64,
                "answer_key_sha256": "a" * 64,
            },
        }
    )


def test_cloud_runtime_pins_numpy_compatible_with_torch_23():
    requirements = (
        Path(__file__).resolve().parents[1]
        / "cloud_jobs"
        / "px062_gate2_2_context_structured_20260728"
        / "requirements.txt"
    ).read_text(encoding="utf-8").splitlines()
    assert "numpy==1.26.4" in requirements
