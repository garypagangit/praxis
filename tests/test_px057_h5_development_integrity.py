from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from scripts.px057_h5_development_integrity import (
    EXPECTED_ROUNDS,
    REQUIRED_CODE_KEYS,
    SCIENTIFIC_FILES,
    SOURCE_MANIFEST_SHA256,
    canonical_json_bytes,
    expected_selected_rows,
    load_pinned_source,
    sha256_file,
    strict_json_bytes,
    strict_jsonl_bytes,
    verify_fetched_collection,
    verify_scientific_collection,
)
from scripts.px057_h5_mechanism import extract_last_valid_answer
from scripts.run_px057_h5_development_pilot import (
    build_prompt,
    validate_bounded_response,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/px057_h5_development_pilot_20260727.json"
SOURCE_PATH = ROOT / "manifests/px057_h4_20260725/gsm8k_calibration.jsonl"


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_bytes(b"".join(canonical_json_bytes(row) for row in rows))


def read_json(path: Path) -> dict[str, Any]:
    return strict_json_bytes(path.read_bytes(), source=str(path))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return strict_jsonl_bytes(path.read_bytes(), source=str(path))


def file_record(path: Path) -> dict[str, Any]:
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size}


def make_expected_cloud_metadata(config: dict[str, Any]) -> dict[str, Any]:
    code = {
        key: hashlib.sha256(key.encode("utf-8")).hexdigest()
        for key in sorted(REQUIRED_CODE_KEYS)
    }
    return {
        "job_name": "px057-h5-dev-c1-r2-20260727",
        "git_commit": "a" * 40,
        "repository_url": config["repository"]["url"],
        "branch": config["repository"]["branch"],
        "container_image_digest": config["aws"]["container_image"].rsplit("@", 1)[1],
        "source_archive": {"version_id": "version-1", "sha256": "b" * 64},
        "code": code,
    }


def build_valid_bundle(
    bundle: Path,
    *,
    config: dict[str, Any],
    source_bytes: bytes,
    expected_metadata: dict[str, Any],
) -> None:
    bundle.mkdir(parents=True)
    source_rows, _ = load_pinned_source(
        source_bytes,
        expected_sha256=SOURCE_MANIFEST_SHA256,
    )
    selected = expected_selected_rows(source_rows)
    traces: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    max_new_tokens = int(config["generation"]["max_new_tokens"])

    for row_index, row in enumerate(selected):
        steps: list[dict[str, Any]] = []
        previous_answer = ""
        cumulative_tokens = 0
        for round_index in range(1, EXPECTED_ROUNDS + 1):
            prompt = build_prompt(
                row,
                previous_answer=previous_answer,
                round_index=round_index,
                prompts=config["prompts"],
            )
            # Exercise the invalid-round context reset in the golden bundle.
            invalid_first_round = row_index == 0 and round_index == 1
            response = (
                "No bounded answer was produced."
                if invalid_first_round
                else "Check: arithmetic is consistent.\nFinal answer: 1\n<END>"
            )
            termination_reason = (
                "native_eos_or_eot" if invalid_first_round else "literal_end_marker"
            )
            generated_tokens = 4
            cumulative_tokens += generated_tokens
            extraction = extract_last_valid_answer(
                response,
                answer_type="numeric",
                generated_tokens=generated_tokens,
                max_new_tokens=max_new_tokens,
            )
            schema = validate_bounded_response(
                response,
                extraction=extraction,
                answer_type="numeric",
                termination_reason=termination_reason,
            )
            answer = extraction.answer if schema["valid"] else ""
            step = {
                "step": round_index,
                "answer": answer,
                "confidence": 0.75,
                "tokens": cumulative_tokens,
                "generated_tokens": generated_tokens,
                "prompt_tokens": 100 + round_index,
                "termination_reason": termination_reason,
                "token_cap_reached": False,
                "marker_count": extraction.marker_count,
                "used_prior_valid_marker": extraction.used_prior_valid_marker,
                "repetition_detected": extraction.repetition_detected,
                "response_schema_valid": schema["valid"],
                "wall_seconds": 0.01,
                "gpu_seconds": 0.01,
            }
            raw.append(
                {
                    "question_id": row["question_id"],
                    "round": round_index,
                    "prompt": prompt,
                    "response": response,
                    "extracted_answer": answer,
                    "parsed_candidate": extraction.answer,
                    "response_schema": schema,
                    **{key: value for key, value in step.items() if key != "answer"},
                }
            )
            steps.append(step)
            previous_answer = answer
        traces.append(
            {
                "question_id": row["question_id"],
                "domain": row["domain"],
                "gold_answer": row["gold_answer"],
                "answer_type": row["answer_type"],
                "steps": steps,
            }
        )

    write_jsonl(bundle / "selected_rows.jsonl", selected)
    write_jsonl(bundle / "reasoning_traces.jsonl", traces)
    write_jsonl(bundle / "raw_generations.jsonl", raw)
    selected_ids = [str(row["question_id"]) for row in selected]
    scientific_records = {
        name: file_record(bundle / name)
        for name in SCIENTIFIC_FILES
        if name != "collection_summary.json"
    }
    cell = config["cells"][0]
    summary = {
        "experiment_id": config["experiment_id"],
        "px_id": config["px_id"],
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": config["primary_development_policy"]["policy_id"],
        "stage": "H5_DEVELOPMENT_PILOT_COLLECTION",
        "status": "PASS",
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell["cell_id"],
        "source_manifest": {
            "path": cell["source_manifest"],
            "sha256": SOURCE_MANIFEST_SHA256,
            "available_rows": 500,
            "outcome_exposed": True,
        },
        "selection": {
            "algorithm": "SHA256('<sample_seed>:<question_id>') ascending",
            "sample_seed": 5758,
            "rows": 500,
            "selected_id_sha256": hashlib.sha256(
                canonical_json_bytes(selected_ids)
            ).hexdigest(),
        },
        "model": config["models"][cell["model_key"]],
        "runtime": {"python": "test", "device": "synthetic"},
        "generation": config["generation"],
        "response_protocol": config["prompts"],
        "observed_generation_rows": 4000,
        "files": scientific_records,
    }
    write_json(bundle / "collection_summary.json", summary)

    all_records = {name: file_record(bundle / name) for name in SCIENTIFIC_FILES}
    collection = {
        "status": "PASS",
        "experiment_id": config["experiment_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "cell_id": cell["cell_id"],
        "trace_count": 500,
        "rounds_per_trace": 8,
        "raw_generation_count": 4000,
        "source_membership": "EXACT_H4_CALIBRATION_MANIFEST",
        "source_sha256": SOURCE_MANIFEST_SHA256,
        "selected_id_sha256": hashlib.sha256(
            canonical_json_bytes(selected_ids)
        ).hexdigest(),
        "files": all_records,
    }
    evidence = {
        "experiment_id": config["experiment_id"],
        "px_id": config["px_id"],
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": config["primary_development_policy"]["policy_id"],
        "stage": "PX057_H5_DEVELOPMENT_PILOT_CLOUD_COLLECTION",
        "status": "PASS",
        "confirmatory_evidence": False,
        "scientific_data_generated": True,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell["cell_id"],
        **expected_metadata,
        "observed_remote_branch_head": "c" * 40,
        "h4_calibration_source": {
            "path": cell["source_manifest"],
            "sha256": SOURCE_MANIFEST_SHA256,
            "rows": 500,
            "outcome_exposed": True,
        },
        "collection_verification": collection,
        "collection_files": all_records,
        "started_at_utc": "2026-07-27T00:00:00+00:00",
        "completed_at_utc": "2026-07-27T01:00:00+00:00",
    }
    write_json(bundle / "cloud_job_evidence.json", evidence)


@pytest.fixture(scope="session")
def golden_bundle(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source_bytes = SOURCE_PATH.read_bytes()
    expected_metadata = make_expected_cloud_metadata(config)
    bundle = tmp_path_factory.mktemp("px057-h5-integrity") / "bundle"
    build_valid_bundle(
        bundle,
        config=config,
        source_bytes=source_bytes,
        expected_metadata=expected_metadata,
    )
    return {
        "path": bundle,
        "config": config,
        "source_bytes": source_bytes,
        "expected_metadata": expected_metadata,
    }


@pytest.fixture
def bundle(tmp_path: Path, golden_bundle: dict[str, Any]) -> Path:
    target = tmp_path / "bundle"
    shutil.copytree(golden_bundle["path"], target)
    return target


def verify_scientific(bundle: Path, golden: dict[str, Any]) -> dict[str, Any]:
    return verify_scientific_collection(
        bundle,
        config=golden["config"],
        source_manifest_bytes=golden["source_bytes"],
        expected_source_sha256=SOURCE_MANIFEST_SHA256,
    )


def verify_fetched(bundle: Path, golden: dict[str, Any]) -> dict[str, Any]:
    return verify_fetched_collection(
        bundle,
        config=golden["config"],
        source_manifest_bytes=golden["source_bytes"],
        expected_source_sha256=SOURCE_MANIFEST_SHA256,
        expected_cloud_metadata=golden["expected_metadata"],
    )


def test_valid_scientific_and_fetched_bundle_pass(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    assert verify_scientific(bundle, golden_bundle)["status"] == "PASS"
    assert verify_fetched(bundle, golden_bundle)["status"] == "PASS"


def test_strict_json_and_jsonl_reject_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        strict_json_bytes(b'{"field":1,"field":2}')
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        strict_jsonl_bytes(b'{"field":1,"field":2}\n')


def test_same_cardinality_duplicate_and_missing_round_fails(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    raw = read_jsonl(bundle / "raw_generations.jsonl")
    raw[-1] = copy.deepcopy(raw[0])
    write_jsonl(bundle / "raw_generations.jsonl", raw)

    with pytest.raises(ValueError, match="ordered unique 500-by-8"):
        verify_scientific(bundle, golden_bundle)


def test_changed_selected_source_row_fails(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    selected = read_jsonl(bundle / "selected_rows.jsonl")
    selected[0]["question"] += " tampered"
    write_jsonl(bundle / "selected_rows.jsonl", selected)

    with pytest.raises(ValueError, match="exact SHA5758 source order/content"):
        verify_scientific(bundle, golden_bundle)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [("gold_answer", "999"), ("domain", "other"), ("answer_type", "choice")],
)
def test_changed_trace_source_gold_domain_or_type_fails(
    bundle: Path,
    golden_bundle: dict[str, Any],
    field: str,
    replacement: str,
) -> None:
    traces = read_jsonl(bundle / "reasoning_traces.jsonl")
    traces[0][field] = replacement
    write_jsonl(bundle / "reasoning_traces.jsonl", traces)

    with pytest.raises(ValueError, match="source/gold/domain/type mismatch"):
        verify_scientific(bundle, golden_bundle)


def test_changed_answer_fails_replay(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    traces = read_jsonl(bundle / "reasoning_traces.jsonl")
    traces[0]["steps"][1]["answer"] = "999"
    write_jsonl(bundle / "reasoning_traces.jsonl", traces)

    with pytest.raises(ValueError, match="strict answer replay mismatch"):
        verify_scientific(bundle, golden_bundle)


def test_changed_schema_fails_replay(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    raw = read_jsonl(bundle / "raw_generations.jsonl")
    raw[1]["response_schema"]["valid"] = False
    write_jsonl(bundle / "raw_generations.jsonl", raw)

    with pytest.raises(ValueError, match="response-schema replay mismatch"):
        verify_scientific(bundle, golden_bundle)


def test_changed_cumulative_tokens_fails_replay(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    raw = read_jsonl(bundle / "raw_generations.jsonl")
    traces = read_jsonl(bundle / "reasoning_traces.jsonl")
    raw[1]["tokens"] += 1
    traces[0]["steps"][1]["tokens"] += 1
    write_jsonl(bundle / "raw_generations.jsonl", raw)
    write_jsonl(bundle / "reasoning_traces.jsonl", traces)

    with pytest.raises(ValueError, match="cumulative-token replay mismatch"):
        verify_scientific(bundle, golden_bundle)


def test_changed_prompt_fails_replay(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    raw = read_jsonl(bundle / "raw_generations.jsonl")
    assert "NO VALID PRIOR ANSWER" in raw[1]["prompt"]
    raw[1]["prompt"] = raw[1]["prompt"].replace(
        "NO VALID PRIOR ANSWER", "1"
    )
    write_jsonl(bundle / "raw_generations.jsonl", raw)

    with pytest.raises(ValueError, match="prompt replay mismatch"):
        verify_scientific(bundle, golden_bundle)


def test_changed_cloud_collection_hash_fails(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    evidence = read_json(bundle / "cloud_job_evidence.json")
    for field in ("collection_files", "collection_verification"):
        target = (
            evidence[field]
            if field == "collection_files"
            else evidence[field]["files"]
        )
        target["selected_rows.jsonl"]["sha256"] = "d" * 64
    write_json(bundle / "cloud_job_evidence.json", evidence)

    with pytest.raises(ValueError, match="collection file hashes mismatch"):
        verify_fetched(bundle, golden_bundle)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("container_image_digest", "sha256:" + "e" * 64),
        ("source_archive", {"version_id": "version-1", "sha256": "e" * 64}),
    ],
)
def test_changed_cloud_image_or_source_archive_hash_fails(
    bundle: Path,
    golden_bundle: dict[str, Any],
    field: str,
    replacement: Any,
) -> None:
    evidence = read_json(bundle / "cloud_job_evidence.json")
    evidence[field] = replacement
    write_json(bundle / "cloud_job_evidence.json", evidence)

    with pytest.raises(ValueError, match="identity/code/image/source mismatch"):
        verify_fetched(bundle, golden_bundle)


def test_null_source_archive_version_is_rejected(
    bundle: Path, golden_bundle: dict[str, Any]
) -> None:
    expected = copy.deepcopy(golden_bundle["expected_metadata"])
    expected["source_archive"]["version_id"] = "null"

    with pytest.raises(ValueError, match="source archive identity is incomplete"):
        verify_fetched_collection(
            bundle,
            config=golden_bundle["config"],
            source_manifest_bytes=golden_bundle["source_bytes"],
            expected_source_sha256=SOURCE_MANIFEST_SHA256,
            expected_cloud_metadata=expected,
        )
