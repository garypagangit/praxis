#!/usr/bin/env python3
"""Run the PX-063 source-integrity gate and emit trajectory-free evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from praxis.px063.trace_adapter import (  # noqa: E402
    DATASET_CONFIG,
    DATASET_ID,
    DATASET_SPLIT,
    DEFAULT_HF_REVISION,
    EXPECTED_CLEAN_ROWS,
    EXPECTED_HACKING_ROWS,
    EXPECTED_TRACE_ROWS,
    FROZEN_TRACE_ATOMIC_CODES,
    OFFICIAL_TRACE_CARD_SHA256,
    OFFICIAL_TRACE_DATASET_ID,
    OFFICIAL_TRACE_HF_REVISION,
    PINNED_PARQUET_SHA256,
    PINNED_RHBENCH_COMMIT,
    PINNED_TRACE_TAXONOMY_SCHEMA_VERSION,
    PINNED_TRACE_TAXONOMY_SHA256,
    SOURCE_DATASET,
    canonical_json_bytes,
    load_trace_rows,
    validate_trace_rows,
)


def _git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _attribution_notice_checks(text: str) -> dict[str, bool]:
    """Validate every attribution element frozen by the PX-063 protocol."""

    normalized = " ".join(text.casefold().split())
    praxis_heading = "## praxis changes"
    _, heading_present, praxis_text = text.casefold().partition(praxis_heading)
    normalized_praxis_text = " ".join(praxis_text.split())
    official_dataset_url = (
        "https://huggingface.co/datasets/PatronusAI/trace-dataset/tree/"
        f"{OFFICIAL_TRACE_HF_REVISION}"
    ).casefold()
    community_dataset_url = (
        "https://huggingface.co/datasets/ktolnos/rh-bench/tree/"
        f"{DEFAULT_HF_REVISION}"
    ).casefold()
    community_code_url = (
        "https://github.com/ktolnos/rh-bench/tree/"
        f"{PINNED_RHBENCH_COMMIT}"
    ).casefold()
    creators = (
        "Darshan Deshpande",
        "Anand Kannappan",
        "Rebecca Qian",
        "Patronus AI",
    )
    praxis_change_markers = (
        "filters the community dataset",
        "coalesces the single populated response",
        "pseudonymous identifiers",
        "independently implemented",
        "do not contain raw trace text",
    )
    return {
        "attribution_work_title_recorded": (
            "trace (testing reward anomalies in code environments)" in normalized
        ),
        "attribution_paper_title_recorded": (
            "benchmarking reward hack detection in code environments via "
            "contrastive analysis"
            in normalized
        ),
        "attribution_paper_source_recorded": (
            "https://arxiv.org/abs/2601.20103" in normalized
        ),
        "attribution_creators_recorded": all(
            creator.casefold() in normalized for creator in creators
        ),
        "attribution_official_source_revision_pinned": (
            official_dataset_url in normalized
        ),
        "attribution_community_dataset_revision_pinned": (
            community_dataset_url in normalized
        ),
        "attribution_community_code_revision_pinned": (
            community_code_url in normalized
        ),
        "attribution_license_recorded": (
            "cc by-sa 4.0" in normalized
            and "https://creativecommons.org/licenses/by-sa/4.0/" in normalized
        ),
        "attribution_praxis_change_notice_recorded": all(
            marker in normalized_praxis_text for marker in praxis_change_markers
        )
        and bool(heading_present),
    }


def _markdown(provenance: dict[str, Any], summary: dict[str, Any]) -> str:
    expectations = summary["expectations"]
    lines = [
        "# PX-063 rh-bench TRACE-Derived Source Gate",
        "",
        f"Date retrieved (UTC): **{provenance['retrieved_at_utc']}**",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Provenance",
        "",
        f"- Dataset: `{provenance['dataset_id']}` / `{provenance['dataset_config']}` / `{provenance['dataset_split']}`",
        f"- Filter: `source_dataset == {provenance['source_dataset']!r}`",
        f"- Hugging Face revision: `{provenance['hf_revision']}`",
        f"- Pinned Parquet SHA-256: `{provenance['parquet_sha256']}`",
        f"- GitHub dependency commit: `{provenance['rhbench_git_commit']}`",
        f"- GitHub dependency URL: `{provenance['rhbench_git_url']}`",
        f"- GitHub dependency worktree clean: **{provenance['rhbench_worktree_clean']}**",
        f"- Dataset license metadata: `{provenance['dataset_license']}`",
        f"- External code license file: **{provenance['external_code_license_status']}**",
        f"- Gate 0 dependency/license status: **{summary['gate0']['status']}**",
        f"- Official TRACE card revision: `{provenance['official_trace_hf_revision']}`",
        "- Raw trajectories committed: **No**",
        "",
        "## Integrity results",
        "",
        f"- Rows: **{summary['rows']}** (expected {EXPECTED_TRACE_ROWS})",
        f"- Hacking: **{summary['labels']['hacking']}** (expected {EXPECTED_HACKING_ROWS})",
        f"- Clean: **{summary['labels']['clean']}** (expected {EXPECTED_CLEAN_ROWS})",
        f"- JSON parse-failure rows: **{summary['json_parse_failure_rows']}**",
        f"- Missing response rows: **{summary['missing_response_rows']}**",
        f"- Dual-populated response rows: **{summary['dual_response_rows']}**",
        f"- Missing-label rows: **{summary['missing_label_rows']}**",
        f"- Missing original TRACE-code rows: **{summary['missing_trace_code_rows']}**",
        f"- Invalid TRACE-code rows: **{summary['invalid_trace_code_rows']}**",
        f"- Duplicate source IDs: **{summary['duplicate_source_ids']['count']}**",
        f"- Missing source IDs: **{summary['missing_source_ids']}**",
        f"- Duplicate source row indices: **{summary['duplicate_source_row_indices']['count']}**",
        f"- Missing source row indices: **{summary['missing_source_row_indices']}**",
        "- Duplicate canonical row hashes: "
        f"**{summary['duplicate_canonical_row_hashes']['count']}**",
        f"- Rows with structured tool payloads: **{summary['structured_tool_payload_rows']}**",
        f"- Canonical safe-manifest SHA-256: `{summary['manifest_sha256']}`",
        f"- Frozen TRACE-taxonomy SHA-256: `{provenance['trace_taxonomy_sha256']}`",
        "",
        "## Frozen expectation checks",
        "",
    ]
    for name, passed in expectations.items():
        lines.append(f"- `{name}`: **{'PASS' if passed else 'FAIL'}**")
    lines.extend(
        [
            "",
            "## Scientific claim boundary",
            "",
            summary["source_limitation"],
            "",
            "PX-063 therefore evaluates deterministic evidence extraction over the "
            "TRACE-derived `rh-bench` normalization. It does not claim use of the "
            "official TRACE harness, and it does not treat assistant transcript text "
            "as independently verified execution state.",
            "",
            "The `rh-bench` dataset card identifies the derivative dataset as "
            "CC-BY-SA-4.0. The pinned GitHub repository has no license file at this "
            "commit, so live reuse of its OpenRouter helper code remains a separately "
            "recorded licensing limitation; paid calls are not part of this gate.",
            "",
            "## Committed artifact policy",
            "",
            "Only pseudonymous record IDs and cryptographic row hashes are written "
            "per row. Gold labels, TRACE codes, categories, source identifiers, "
            "prompts, and response text are intentionally excluded.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default=DEFAULT_HF_REVISION)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT
        / "reports"
        / "reward_hack_trace"
        / "source_gate_20260726_v14",
    )
    args = parser.parse_args()

    if len(args.revision) != 40:
        raise SystemExit("--revision must be an immutable 40-character Hugging Face SHA")

    git_commit = _git("rev-parse", "HEAD", cwd=REPO_ROOT)
    worktree_clean = not _git("status", "--porcelain", cwd=REPO_ROOT)
    try:
        upstream_commit = _git("rev-parse", "@{upstream}", cwd=REPO_ROOT)
    except subprocess.CalledProcessError as exc:
        raise SystemExit("Gate 0/1 requires a configured pushed upstream") from exc
    if not worktree_clean or upstream_commit != git_commit:
        raise SystemExit(
            "Gate 0/1 requires a clean worktree and HEAD equal to pushed upstream"
        )

    from huggingface_hub import HfApi, hf_hub_download

    dataset_info = HfApi().dataset_info(DATASET_ID, revision=args.revision)
    if dataset_info.sha != args.revision:
        raise SystemExit(
            f"Resolved Hugging Face SHA {dataset_info.sha} does not equal requested {args.revision}"
        )
    dataset_license = str(getattr(dataset_info.card_data, "license", None) or "unknown")
    official_info = HfApi().dataset_info(
        OFFICIAL_TRACE_DATASET_ID, revision=OFFICIAL_TRACE_HF_REVISION
    )
    official_card_path = Path(
        hf_hub_download(
            repo_id=OFFICIAL_TRACE_DATASET_ID,
            filename="README.md",
            repo_type="dataset",
            revision=OFFICIAL_TRACE_HF_REVISION,
        )
    )
    official_card_sha256 = _file_sha256(official_card_path)
    official_card_text = official_card_path.read_text(encoding="utf-8").casefold()

    dependency = REPO_ROOT / "external" / "rh-bench"
    rhbench_commit = _git("rev-parse", "HEAD", cwd=dependency)
    if rhbench_commit != PINNED_RHBENCH_COMMIT:
        raise SystemExit(
            f"rh-bench commit {rhbench_commit} does not equal pin {PINNED_RHBENCH_COMMIT}"
        )
    external_license_files = [
        path.name
        for path in dependency.iterdir()
        if path.is_file() and path.name.lower().startswith(("license", "copying"))
    ]
    rhbench_worktree_clean = not _git("status", "--porcelain", cwd=dependency)
    rhbench_git_url = _git("remote", "get-url", "origin", cwd=dependency)
    expected_git_url = "https://github.com/ktolnos/rh-bench.git"
    rhbench_gitlink_entry = _git(
        "ls-files", "--stage", "--", "external/rh-bench", cwd=REPO_ROOT
    )
    rhbench_submodule_path = _git(
        "config",
        "-f",
        ".gitmodules",
        "--get",
        "submodule.external/rh-bench.path",
        cwd=REPO_ROOT,
    )
    rhbench_submodule_url = _git(
        "config",
        "-f",
        ".gitmodules",
        "--get",
        "submodule.external/rh-bench.url",
        cwd=REPO_ROOT,
    )
    dependency_root = dependency.resolve()
    loaded_external_modules = sorted(
        name
        for name, module in sys.modules.items()
        if getattr(module, "__file__", None)
        and Path(str(module.__file__)).resolve().is_relative_to(dependency_root)
    )
    attribution_path = (
        REPO_ROOT / "reports" / "reward_hack_trace" / "ATTRIBUTION.md"
    )
    attribution_text = (
        attribution_path.read_text(encoding="utf-8")
        if attribution_path.is_file()
        else ""
    )
    attribution_sha256 = (
        _file_sha256(attribution_path) if attribution_path.is_file() else None
    )
    attribution_checks = _attribution_notice_checks(attribution_text)
    taxonomy_path = REPO_ROOT / "configs" / "px063_trace_taxonomy_v1.json"
    try:
        taxonomy_manifest = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(
            "Gate 0 cannot read the frozen TRACE taxonomy manifest"
        ) from exc
    taxonomy_sha256 = _file_sha256(taxonomy_path)
    taxonomy_schema_version = taxonomy_manifest.get("schema_version")
    taxonomy_atomic_mapping = taxonomy_manifest.get("atomic_codes")
    taxonomy_atomic_codes = (
        frozenset(taxonomy_atomic_mapping)
        if isinstance(taxonomy_atomic_mapping, dict)
        else frozenset()
    )

    package_versions = sorted(
        {
            f"{distribution.metadata['Name']}=={distribution.version}"
            for distribution in importlib.metadata.distributions()
            if distribution.metadata.get("Name")
        },
        key=str.casefold,
    )
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": package_versions,
    }
    environment["lock_sha256"] = sha256(canonical_json_bytes(environment)).hexdigest()

    gate0_checks = {
        "parent_worktree_clean_at_start": worktree_clean,
        "parent_head_pushed_at_start": upstream_commit == git_commit,
        "rhbench_url_pinned": rhbench_git_url == expected_git_url,
        "rhbench_commit_pinned": rhbench_commit == PINNED_RHBENCH_COMMIT,
        "rhbench_worktree_clean": rhbench_worktree_clean,
        "rhbench_superproject_gitlink_pinned": rhbench_gitlink_entry
        == f"160000 {PINNED_RHBENCH_COMMIT} 0\texternal/rh-bench",
        "rhbench_gitmodules_entry_pinned": (
            rhbench_submodule_path == "external/rh-bench"
            and rhbench_submodule_url == expected_git_url
        ),
        "unlicensed_external_helpers_not_loaded": not loaded_external_modules,
        "missing_external_code_license_recorded": not external_license_files,
        "derivative_dataset_cc_by_sa_4_0": dataset_license.casefold()
        == "cc-by-sa-4.0",
        "official_card_revision_pinned": official_info.sha
        == OFFICIAL_TRACE_HF_REVISION,
        "official_card_sha256_pinned": official_card_sha256
        == OFFICIAL_TRACE_CARD_SHA256,
        "official_dataset_cc_by_sa_4_0": str(
            getattr(official_info.card_data, "license", None) or ""
        ).casefold()
        == "cc-by-sa-4.0",
        "official_direct_use_notice_recorded": "benchmarking llm performance"
        in official_card_text,
        "official_out_of_scope_notice_recorded": "training models to perform reward hacking"
        in official_card_text,
        **attribution_checks,
        "attribution_notice_complete": bool(attribution_text)
        and all(attribution_checks.values()),
        "trace_taxonomy_sha256_pinned": taxonomy_sha256
        == PINNED_TRACE_TAXONOMY_SHA256,
        "trace_taxonomy_schema_pinned": taxonomy_schema_version
        == PINNED_TRACE_TAXONOMY_SCHEMA_VERSION,
        "trace_taxonomy_atomic_codes_pinned": taxonomy_atomic_codes
        == FROZEN_TRACE_ATOMIC_CODES,
    }
    gate0 = {
        "status": "PASS" if all(gate0_checks.values()) else "FAIL",
        "checks": gate0_checks,
        "loaded_external_modules": loaded_external_modules,
        "git_commit": git_commit,
        "upstream_commit": upstream_commit,
        "attribution_path": "reports/reward_hack_trace/ATTRIBUTION.md",
        "attribution_sha256": attribution_sha256,
        "code_license_interpretation": (
            "The pinned rh-bench repository has no license file. PX-063 imports no "
            "external helper code; the submodule is provenance-only."
        ),
        "dataset_obligations": [
            "Attribute TRACE and the community derivative.",
            "Apply CC-BY-SA-4.0 ShareAlike terms to redistributed adaptations.",
            "Do not use the benchmark to train models to perform reward hacking.",
        ],
    }
    if gate0["status"] != "PASS":
        raise SystemExit(
            "PX-063 Gate 0 failed before trajectory access: "
            + json.dumps(gate0_checks, sort_keys=True)
        )

    parquet_path = Path(
        hf_hub_download(
            repo_id=DATASET_ID,
            filename="data/rh_bench_unified.parquet",
            repo_type="dataset",
            revision=args.revision,
        )
    )
    parquet_sha256 = _file_sha256(parquet_path)
    if parquet_sha256 != PINNED_PARQUET_SHA256:
        raise SystemExit(
            f"Pinned Parquet SHA-256 {parquet_sha256} does not equal {PINNED_PARQUET_SHA256}"
        )

    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows = load_trace_rows(revision=args.revision)
    artifacts = validate_trace_rows(rows, allowed_trace_codes=taxonomy_atomic_codes)
    provenance = {
        "dataset_id": DATASET_ID,
        "dataset_config": DATASET_CONFIG,
        "dataset_split": DATASET_SPLIT,
        "source_dataset": SOURCE_DATASET,
        "hf_revision": args.revision,
        "parquet_sha256": parquet_sha256,
        "expected_parquet_sha256": PINNED_PARQUET_SHA256,
        "rhbench_git_commit": rhbench_commit,
        "rhbench_git_url": rhbench_git_url,
        "rhbench_worktree_clean": rhbench_worktree_clean,
        "dataset_license": dataset_license,
        "official_trace_dataset_id": OFFICIAL_TRACE_DATASET_ID,
        "official_trace_hf_revision": official_info.sha,
        "official_trace_dataset_license": str(
            getattr(official_info.card_data, "license", None) or "unknown"
        ),
        "official_trace_card_sha256": official_card_sha256,
        "external_code_license_status": (
            "PRESENT: " + ", ".join(external_license_files)
            if external_license_files
            else "UNRESOLVED - no repository license file"
        ),
        "git_commit": git_commit,
        "upstream_commit": upstream_commit,
        "worktree_clean_at_start": worktree_clean,
        "attribution_sha256": attribution_sha256,
        "trace_taxonomy_path": "configs/px063_trace_taxonomy_v1.json",
        "trace_taxonomy_sha256": taxonomy_sha256,
        "trace_taxonomy_schema_version": taxonomy_schema_version,
        "trace_taxonomy_atomic_code_count": len(taxonomy_atomic_codes),
        "retrieved_at_utc": retrieved_at,
        "source_gate_sha256": _file_sha256(Path(__file__)),
        "trace_adapter_sha256": _file_sha256(
            SRC / "praxis" / "px063" / "trace_adapter.py"
        ),
        "requirements_sha256": _file_sha256(REPO_ROOT / "requirements-px063.txt"),
        "environment_lock_sha256": environment["lock_sha256"],
    }
    summary = dict(artifacts.summary)
    summary["provenance"] = provenance
    summary["gate0"] = gate0
    summary["expectations"]["pinned_parquet_sha256"] = (
        parquet_sha256 == PINNED_PARQUET_SHA256
    )
    if gate0["status"] != "PASS" or not all(summary["expectations"].values()):
        summary["status"] = "FAIL"

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_json(output_dir / "source_integrity_summary.json", summary)
    _write_json(output_dir / "gate0_dependency_license.json", gate0)
    _write_json(output_dir / "environment_lock.json", environment)
    _write_json(
        output_dir / "source_manifest.json",
        {
            "schema_version": "px063_safe_source_manifest_v1_4",
            "provenance": provenance,
            "manifest_sha256": summary["manifest_sha256"],
            "records": artifacts.records,
        },
    )
    with (output_dir / "trace_row_hashes.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        for record in artifacts.records:
            handle.write(canonical_json_bytes(record).decode("utf-8") + "\n")
    (output_dir / "PX063_RHBENCH_SOURCE_GATE_20260726_V14.md").write_text(
        _markdown(provenance, summary), encoding="utf-8", newline="\n"
    )

    print(f"PX-063 TRACE-derived source gate: {summary['status']}")
    print(f"Hugging Face revision: {args.revision}")
    print(f"Rows: {summary['rows']}")
    print(f"Labels: {summary['labels']}")
    print(f"Manifest SHA-256: {summary['manifest_sha256']}")
    print(f"Report directory: {output_dir}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
