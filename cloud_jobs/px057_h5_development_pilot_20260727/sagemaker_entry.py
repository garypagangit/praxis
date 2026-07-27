#!/usr/bin/env python
"""Run one outcome-exposed PX-057 H5 development cell on SageMaker.

This entrypoint is transport code for a development-only pilot.  It verifies
the staged source archive, exact pushed Git commit, committed entrypoint,
configuration, dependency lock, and H4 calibration source manifest before it
installs packages, reads the Hugging Face token, or starts the model runner.

SageMaker automatically uploads ``SM_MODEL_DIR``.  The entrypoint therefore
places the four collection files and its cloud evidence record there instead
of performing a second scientific-result upload itself.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ENTRY = "cloud_jobs/px057_h5_development_pilot_20260727/sagemaker_entry.py"
CONFIG = "configs/px057_h5_development_pilot_20260727.json"
RUNNER = "scripts/run_px057_h5_development_pilot.py"
MECHANISM = "scripts/px057_h5_mechanism.py"
H4_REQUIREMENTS = "requirements-px057-h4.txt"
H4_REQUIREMENTS_SHA256 = (
    "5aa1adf7ce4187838a9f2867c9e6919bb5b06e11f90d70194ab48fc09984d163"
)
STAGED_ARCHIVE = Path("/tmp/s")
DEFAULT_REPO_DIR = Path("/opt/ml/code/px057_h5_dev_repo")
DEFAULT_MODEL_DIR = Path("/opt/ml/model")

COLLECTION_FILES = (
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
)
EXPECTED_PILOT_ROWS = 500
EXPECTED_ROUNDS = 8
EXPECTED_RAW_ROWS = EXPECTED_PILOT_ROWS * EXPECTED_ROUNDS

H4_CALIBRATION_SOURCES = {
    "cell1_llama31_gsm8k": {
        "path": "manifests/px057_h4_20260725/gsm8k_calibration.jsonl",
        "sha256": "a48ef2c73edc6eec80428358feee3f38e1c5182dac441ca39c339fb9b54f00ef",
        "rows": 500,
    },
    "cell2_qwen25_arc": {
        "path": "manifests/px057_h4_20260725/arc_challenge_calibration.jsonl",
        "sha256": "90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224",
        "rows": 500,
    },
    "cell3_llama31_arc": {
        "path": "manifests/px057_h4_20260725/arc_challenge_calibration.jsonl",
        "sha256": "90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224",
        "rows": 500,
    },
}

REQUIRED_ENVIRONMENT = (
    "PX057_H5_DEV_REPOSITORY_URL",
    "PX057_H5_DEV_BRANCH",
    "PX057_H5_DEV_GIT_COMMIT",
    "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST",
    "PX057_H5_DEV_HF_SECRET_ID",
    "PX057_H5_DEV_AWS_REGION",
    "PX057_H5_DEV_JOB_NAME",
    "PX057_H5_DEV_SOURCE_VERSION_ID",
    "PX057_H5_DEV_SOURCE_ARCHIVE_SHA256",
    "PX057_H5_DEV_CONFIG_SHA256",
    "PX057_H5_DEV_CELL_ID",
)


@dataclass(frozen=True)
class Preflight:
    config: dict[str, Any]
    cell: dict[str, Any]
    source_path: Path
    source_rows: tuple[dict[str, Any], ...]
    source_by_id: dict[str, dict[str, Any]]
    output_dir: Path
    committed_entry_sha256: str
    config_sha256: str
    runner_sha256: str
    mechanism_sha256: str
    requirements_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def read_json_strict(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def read_jsonl_strict(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    if not rows:
        raise ValueError(f"{path}: no JSONL rows")
    return rows


def required_environment(environment: Mapping[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in REQUIRED_ENVIRONMENT:
        value = str(environment.get(name, "")).strip()
        if not value:
            raise ValueError(f"missing required environment variable: {name}")
        values[name] = value
    if re.fullmatch(r"[0-9a-f]{40}", values["PX057_H5_DEV_GIT_COMMIT"]) is None:
        raise ValueError("PX057_H5_DEV_GIT_COMMIT must be a full lowercase SHA-1")
    for name in (
        "PX057_H5_DEV_SOURCE_ARCHIVE_SHA256",
        "PX057_H5_DEV_CONFIG_SHA256",
    ):
        if re.fullmatch(r"[0-9a-f]{64}", values[name]) is None:
            raise ValueError(f"{name} must be a lowercase SHA-256")
    if (
        re.fullmatch(
            r"sha256:[0-9a-f]{64}",
            values["PX057_H5_DEV_CONTAINER_IMAGE_DIGEST"],
        )
        is None
    ):
        raise ValueError(
            "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST must be a sha256 digest"
        )
    return values


def run(command: Sequence[str], *, cwd: Path | None = None) -> None:
    subprocess.run(list(command), cwd=cwd, check=True)


def output(command: Sequence[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(list(command), cwd=cwd, text=True).strip()


def clone_exact_pushed_commit(
    repository_url: str,
    branch: str,
    expected_commit: str,
    target: Path,
) -> str:
    """Fetch branch history and check out the exact submitted pushed commit.

    The remote branch may advance after submission so that the immutable launch
    registration can be committed.  It may not be rewritten away from the
    submitted source: ``expected_commit`` must remain an ancestor of the live
    remote branch head.
    """

    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=target)
    run(["git", "remote", "add", "origin", repository_url], cwd=target)
    run(
        [
            "git",
            "fetch",
            "--no-tags",
            "origin",
            f"refs/heads/{branch}:refs/remotes/origin/{branch}",
        ],
        cwd=target,
    )
    observed = output(
        ["git", "rev-parse", f"refs/remotes/origin/{branch}"],
        cwd=target,
    )
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", expected_commit, observed],
        cwd=target,
        check=False,
    ).returncode != 0:
        raise ValueError(
            "submitted commit is not an ancestor of the remote branch: "
            f"expected {expected_commit}, observed {observed}"
        )
    run(["git", "checkout", "-q", "--detach", expected_commit], cwd=target)
    if output(["git", "status", "--porcelain"], cwd=target):
        raise ValueError("fresh development-pilot clone is unexpectedly dirty")
    return observed


def _inside(root: Path, relative: str) -> Path:
    root_resolved = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"path escapes the cloned repository: {relative}") from exc
    return path


def validate_pre_model_contract(
    repo: Path,
    *,
    staged_entry: Path,
    repository_url: str,
    branch: str,
    cell_id: str,
    expected_config_sha256: str,
    container_image_digest: str,
) -> Preflight:
    """Validate every local scientific input before package/model access."""

    required_paths = {
        "entry": _inside(repo, ENTRY),
        "config": _inside(repo, CONFIG),
        "runner": _inside(repo, RUNNER),
        "mechanism": _inside(repo, MECHANISM),
        "requirements": _inside(repo, H4_REQUIREMENTS),
    }
    missing = [name for name, path in required_paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"committed source files are missing: {sorted(missing)}")

    committed_entry_sha256 = sha256_file(required_paths["entry"])
    if not staged_entry.is_file() or sha256_file(staged_entry) != committed_entry_sha256:
        raise ValueError("staged development entry differs from the committed entry")
    config_sha256 = sha256_file(required_paths["config"])
    if config_sha256 != expected_config_sha256:
        raise ValueError("committed development config SHA-256 mismatch")
    requirements_sha256 = sha256_file(required_paths["requirements"])
    if requirements_sha256 != H4_REQUIREMENTS_SHA256:
        raise ValueError("H4 dependency lock SHA-256 mismatch")

    config = read_json_strict(required_paths["config"])
    if (
        config.get("experiment_id")
        != "px057-h5-development-pilot-bounded-chat-20260727"
        or config.get("px_id") != "PX-057"
        or config.get("status") != "DEVELOPMENT_ONLY_NOT_CONFIRMATORY"
    ):
        raise ValueError("development-only experiment identity is invalid")
    if config.get("repository") != {"url": repository_url, "branch": branch}:
        raise ValueError("development config repository identity mismatch")
    generation = config.get("generation", {})
    if (
        int(generation.get("pilot_n", -1)) != EXPECTED_PILOT_ROWS
        or int(generation.get("rounds", -1)) != EXPECTED_ROUNDS
        or int(generation.get("max_new_tokens", -1)) != 96
        or generation.get("native_chat_template") is not True
        or generation.get("decoding") != "greedy"
    ):
        raise ValueError("development collection cardinality/protocol changed")
    configured_image = str(config.get("aws", {}).get("container_image", ""))
    if not configured_image.endswith("@" + container_image_digest):
        raise ValueError("container image digest differs from development config")

    cells = [cell for cell in config.get("cells", []) if cell.get("cell_id") == cell_id]
    if len(cells) != 1 or cell_id not in H4_CALIBRATION_SOURCES:
        raise ValueError(f"unknown or duplicate development cell: {cell_id}")
    cell = cells[0]
    expected_source = H4_CALIBRATION_SOURCES[cell_id]
    if cell.get("source_manifest") != expected_source["path"]:
        raise ValueError("cell source is not its registered H4 calibration manifest")
    source_path = _inside(repo, str(expected_source["path"]))
    if not source_path.is_file() or sha256_file(source_path) != expected_source["sha256"]:
        raise ValueError("H4 calibration source manifest hash mismatch")
    source_rows = tuple(read_jsonl_strict(source_path))
    source_by_id = {str(row.get("question_id", "")): row for row in source_rows}
    if (
        len(source_rows) != int(expected_source["rows"])
        or "" in source_by_id
        or len(source_by_id) != len(source_rows)
    ):
        raise ValueError("H4 calibration source IDs are incomplete or duplicated")

    output_dir = _inside(repo, str(cell.get("output_dir", "")))
    if output_dir.exists():
        raise FileExistsError(
            f"development output already exists in clean clone: {output_dir}"
        )
    return Preflight(
        config=config,
        cell=cell,
        source_path=source_path,
        source_rows=source_rows,
        source_by_id=source_by_id,
        output_dir=output_dir,
        committed_entry_sha256=committed_entry_sha256,
        config_sha256=config_sha256,
        runner_sha256=sha256_file(required_paths["runner"]),
        mechanism_sha256=sha256_file(required_paths["mechanism"]),
        requirements_sha256=requirements_sha256,
    )


def locked_h4_packages(requirements_path: Path) -> list[str]:
    packages: list[str] = []
    names: set[str] = set()
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if value.count("==") != 1:
            raise ValueError(f"H4 dependency is not exactly pinned: {value}")
        name = value.split("==", 1)[0].casefold()
        if name in names:
            raise ValueError(f"duplicate H4 dependency: {name}")
        names.add(name)
        # The pinned SageMaker image supplies the matching CUDA-enabled torch.
        if name != "torch":
            packages.append(value)
    if not packages or "torch" not in names:
        raise ValueError("H4 dependency lock is incomplete")
    return packages


def install_locked_h4_dependencies(repo: Path) -> None:
    requirements_path = repo / H4_REQUIREMENTS
    if sha256_file(requirements_path) != H4_REQUIREMENTS_SHA256:
        raise ValueError("H4 dependency lock changed before installation")
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            *locked_h4_packages(requirements_path),
        ]
    )


def read_huggingface_token(secret_id: str, region: str) -> str:
    import boto3

    response = boto3.client("secretsmanager", region_name=region).get_secret_value(
        SecretId=secret_id
    )
    raw = response.get("SecretString")
    if raw is None:
        raw = base64.b64decode(response["SecretBinary"]).decode("utf-8")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        token = raw.strip()
    else:
        if isinstance(decoded, str):
            token = decoded.strip()
        elif isinstance(decoded, dict):
            token = str(
                decoded.get("HF_TOKEN")
                or decoded.get("token")
                or decoded.get("huggingface_token")
                or ""
            ).strip()
        else:
            token = ""
    if not token:
        raise ValueError("Hugging Face secret contains no supported token value")
    return token


def run_development_pilot(repo: Path, *, cell_id: str) -> None:
    run(
        [
            sys.executable,
            RUNNER,
            "--config",
            CONFIG,
            "--cell",
            cell_id,
        ],
        cwd=repo,
    )


def _unique_ids(rows: Sequence[dict[str, Any]], *, label: str) -> list[str]:
    ids = [str(row.get("question_id", "")) for row in rows]
    if "" in ids or len(set(ids)) != len(ids):
        raise ValueError(f"{label} question IDs are missing or duplicated")
    return ids


def verify_collection_bundle(
    output_dir: Path,
    *,
    cell_id: str,
    source_path: str,
    source_sha256: str,
    source_by_id: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    """Verify exact 200-by-8 output and H4-source membership."""

    if not output_dir.is_dir():
        raise ValueError("development output directory is missing")
    observed_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if observed_files != set(COLLECTION_FILES):
        raise ValueError(
            "development output file set differs from the four-file contract"
        )
    selected = read_jsonl_strict(output_dir / "selected_rows.jsonl")
    traces = read_jsonl_strict(output_dir / "reasoning_traces.jsonl")
    raw = read_jsonl_strict(output_dir / "raw_generations.jsonl")
    summary = read_json_strict(output_dir / "collection_summary.json")

    selected_ids = _unique_ids(selected, label="selected")
    trace_ids = _unique_ids(traces, label="trace")
    unknown = sorted(set(selected_ids) - set(source_by_id))
    if unknown:
        raise ValueError(f"selected IDs are outside the H4 calibration manifest: {unknown[:3]}")
    if len(selected_ids) != EXPECTED_PILOT_ROWS or set(trace_ids) != set(selected_ids):
        raise ValueError("development bundle does not contain 500 matching traces")
    for row in selected:
        source_row = source_by_id[str(row["question_id"])]
        if canonical_json_bytes(row) != canonical_json_bytes(source_row):
            raise ValueError(f"selected source row changed: {row['question_id']}")

    expected_pairs = {
        (question_id, round_index)
        for question_id in selected_ids
        for round_index in range(1, EXPECTED_ROUNDS + 1)
    }
    observed_pairs: list[tuple[str, int]] = []
    for trace in traces:
        steps = trace.get("steps")
        if not isinstance(steps, list) or [
            int(item.get("step", -1)) for item in steps
        ] != list(range(1, EXPECTED_ROUNDS + 1)):
            raise ValueError(f"trace is not eight complete rounds: {trace.get('question_id')}")
    for row in raw:
        observed_pairs.append((str(row.get("question_id", "")), int(row.get("round", -1))))
    if (
        len(raw) != EXPECTED_RAW_ROWS
        or len(set(observed_pairs)) != len(observed_pairs)
        or set(observed_pairs) != expected_pairs
    ):
        raise ValueError("raw generations are not the exact 500-by-8 Cartesian set")

    source_record = summary.get("source_manifest", {})
    selection = summary.get("selection", {})
    generation = summary.get("generation", {})
    if (
        summary.get("stage") != "H5_DEVELOPMENT_PILOT_COLLECTION"
        or summary.get("status") != "PASS"
        or summary.get("confirmatory_evidence") is not False
        or summary.get("cell_id") != cell_id
        or source_record.get("path") != source_path
        or source_record.get("sha256") != source_sha256
        or source_record.get("outcome_exposed") is not True
        or int(selection.get("rows", -1)) != EXPECTED_PILOT_ROWS
        or int(generation.get("rounds", -1)) != EXPECTED_ROUNDS
        or int(generation.get("pilot_n", -1)) != EXPECTED_PILOT_ROWS
        or int(summary.get("observed_generation_rows", -1)) != EXPECTED_RAW_ROWS
    ):
        raise ValueError("development collection summary violates its boundary")
    return {
        "trace_count": len(traces),
        "rounds_per_trace": EXPECTED_ROUNDS,
        "raw_generation_count": len(raw),
        "source_membership": "EXACT_H4_CALIBRATION_SUBSET",
        "selected_id_sha256": hashlib.sha256(
            canonical_json_bytes(selected_ids)
        ).hexdigest(),
        "files": {
            name: {
                "sha256": sha256_file(output_dir / name),
                "bytes": (output_dir / name).stat().st_size,
            }
            for name in COLLECTION_FILES
        },
    }


def write_model_bundle(
    output_dir: Path,
    model_dir: Path,
    *,
    cell_id: str,
    evidence: dict[str, Any],
) -> Path:
    target = model_dir / "px057_h5_development_pilot" / cell_id
    if target.exists():
        raise FileExistsError(f"model bundle target already exists: {target}")
    target.mkdir(parents=True)
    for name in COLLECTION_FILES:
        shutil.copy2(output_dir / name, target / name)
    (target / "cloud_job_evidence.json").write_bytes(
        canonical_json_bytes(evidence)
    )
    if {path.name for path in target.iterdir() if path.is_file()} != {
        *COLLECTION_FILES,
        "cloud_job_evidence.json",
    }:
        raise ValueError("SageMaker model bundle is incomplete")
    return target


def execute(
    environment: Mapping[str, str],
    *,
    staged_archive: Path = STAGED_ARCHIVE,
    staged_entry: Path | None = None,
    repo_dir: Path = DEFAULT_REPO_DIR,
    model_dir: Path = DEFAULT_MODEL_DIR,
) -> dict[str, Any]:
    """Execute the fail-closed transport in integrity-before-model order."""

    env = required_environment(environment)
    staged_entry = Path(__file__).resolve() if staged_entry is None else staged_entry
    expected_archive_sha256 = env["PX057_H5_DEV_SOURCE_ARCHIVE_SHA256"]
    if (
        not staged_archive.is_file()
        or sha256_file(staged_archive) != expected_archive_sha256
    ):
        raise ValueError("staged source archive differs from submitted SHA-256")

    started = datetime.now(timezone.utc).isoformat()
    observed_branch_head = clone_exact_pushed_commit(
        env["PX057_H5_DEV_REPOSITORY_URL"],
        env["PX057_H5_DEV_BRANCH"],
        env["PX057_H5_DEV_GIT_COMMIT"],
        repo_dir,
    )
    preflight = validate_pre_model_contract(
        repo_dir,
        staged_entry=staged_entry,
        repository_url=env["PX057_H5_DEV_REPOSITORY_URL"],
        branch=env["PX057_H5_DEV_BRANCH"],
        cell_id=env["PX057_H5_DEV_CELL_ID"],
        expected_config_sha256=env["PX057_H5_DEV_CONFIG_SHA256"],
        container_image_digest=env["PX057_H5_DEV_CONTAINER_IMAGE_DIGEST"],
    )

    # No dependency, credential, tokenizer, or model access occurs above here.
    install_locked_h4_dependencies(repo_dir)
    token = read_huggingface_token(
        env["PX057_H5_DEV_HF_SECRET_ID"],
        env["PX057_H5_DEV_AWS_REGION"],
    )
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    os.environ["PX057_CONTAINER_IMAGE_DIGEST"] = env[
        "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST"
    ]
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    run_development_pilot(
        repo_dir,
        cell_id=env["PX057_H5_DEV_CELL_ID"],
    )

    verification = verify_collection_bundle(
        preflight.output_dir,
        cell_id=env["PX057_H5_DEV_CELL_ID"],
        source_path=str(preflight.cell["source_manifest"]),
        source_sha256=sha256_file(preflight.source_path),
        source_by_id=preflight.source_by_id,
    )
    evidence = {
        "experiment_id": preflight.config["experiment_id"],
        "px_id": "PX-057",
        "stage": "PX057_H5_DEVELOPMENT_PILOT_CLOUD_COLLECTION",
        "status": "PASS",
        "confirmatory_evidence": False,
        "scientific_data_generated": True,
        "claim_boundary": preflight.config["claim_boundary"],
        "cell_id": env["PX057_H5_DEV_CELL_ID"],
        "job_name": env["PX057_H5_DEV_JOB_NAME"],
        "repository_url": env["PX057_H5_DEV_REPOSITORY_URL"],
        "branch": env["PX057_H5_DEV_BRANCH"],
        "git_commit": env["PX057_H5_DEV_GIT_COMMIT"],
        "observed_remote_branch_head": observed_branch_head,
        "container_image_digest": env["PX057_H5_DEV_CONTAINER_IMAGE_DIGEST"],
        "source_archive": {
            "version_id": env["PX057_H5_DEV_SOURCE_VERSION_ID"],
            "sha256": expected_archive_sha256,
        },
        "code": {
            "entrypoint_sha256": preflight.committed_entry_sha256,
            "config_sha256": preflight.config_sha256,
            "runner_sha256": preflight.runner_sha256,
            "mechanism_sha256": preflight.mechanism_sha256,
            "h4_requirements_sha256": preflight.requirements_sha256,
        },
        "h4_calibration_source": {
            "path": preflight.cell["source_manifest"],
            "sha256": sha256_file(preflight.source_path),
            "rows": len(preflight.source_rows),
            "outcome_exposed": True,
        },
        "collection_verification": verification,
        "collection_files": verification["files"],
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_model_bundle(
        preflight.output_dir,
        model_dir,
        cell_id=env["PX057_H5_DEV_CELL_ID"],
        evidence=evidence,
    )
    return evidence


def main() -> None:
    model_dir = Path(os.environ.get("SM_MODEL_DIR", str(DEFAULT_MODEL_DIR)))
    evidence = execute(os.environ, model_dir=model_dir)
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "cell_id": evidence["cell_id"],
                "job_name": evidence["job_name"],
                "confirmatory_evidence": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
