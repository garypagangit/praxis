#!/usr/bin/env python3
"""Run the post-lock PX-063 synthetic regression/conformance gate."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from praxis.px063.decision_policy import verify_trace_row  # noqa: E402
from praxis.px063.deterministic_checks import valid_evidence_anchor  # noqa: E402
from praxis.px063.trace_adapter import canonical_json_bytes  # noqa: E402


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _fixture_row(response: str) -> dict[str, Any]:
    return {
        "prompt": json.dumps(
            [{"role": "user", "content": "Synthetic fixture: complete the coding task."}],
            separators=(",", ":"),
        ),
        "response_hacking": None,
        "response_clean": json.dumps(
            [{"role": "assistant", "content": response}], separators=(",", ":")
        ),
        "label": "clean",
        "source_row_idx": -1,
        "source_id": "synthetic-fixture",
    }


def _run(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for fixture in fixtures:
        decision = verify_trace_row(_fixture_row(str(fixture["response"])))
        expected_ids = sorted(str(value) for value in fixture["expected_check_ids"])
        actual_ids = sorted(decision.check_ids)
        evidence_ids = sorted(
            item.get("check_id") for item in decision.evidence if isinstance(item, dict)
        )
        evidence_valid = all(
            isinstance(item, dict) and valid_evidence_anchor(item)
            for item in decision.evidence
        )
        passed = (
            decision.decision == fixture["expected_decision"]
            and actual_ids == expected_ids
            and (
                decision.decision != "block"
                or (
                    bool(decision.evidence)
                    and evidence_valid
                    and evidence_ids == actual_ids
                )
            )
            and (decision.decision == "block" or not decision.evidence)
        )
        results.append(
            {
                "fixture_id": fixture["fixture_id"],
                "stratum": fixture["stratum"],
                "family": fixture["family"],
                "expected_decision": fixture["expected_decision"],
                "actual_decision": decision.decision,
                "expected_check_ids": expected_ids,
                "actual_check_ids": actual_ids,
                "evidence_count": len(decision.evidence),
                "evidence_schema_valid": evidence_valid,
                "evidence_relation_valid": (
                    evidence_ids == actual_ids
                    if decision.decision == "block"
                    else not decision.evidence
                ),
                "passed": passed,
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "px063_cases.json",
    )
    parser.add_argument(
        "--prelock-development",
        action="store_true",
        help="Permit a dirty/unpushed worktree and label the output development-only.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "reward_hack_trace" / "fixture_gate_20260726",
    )
    args = parser.parse_args()

    fixtures = json.loads(args.fixtures.read_text(encoding="utf-8"))
    if not isinstance(fixtures, list) or len(fixtures) < 70:
        raise SystemExit(f"Fixture bank must contain at least 70 cases; got {len(fixtures)}")
    required_fixture_fields = {
        "fixture_id",
        "stratum",
        "family",
        "expected_decision",
        "expected_check_ids",
        "response",
    }
    for index, item in enumerate(fixtures):
        if not isinstance(item, dict) or set(item) != required_fixture_fields:
            raise SystemExit(f"Fixture {index} does not match the frozen schema")
        if item["expected_decision"] not in {"block", "review", "allow"}:
            raise SystemExit(f"Fixture {index} has an invalid expected decision")
        if not isinstance(item["expected_check_ids"], list) or not all(
            isinstance(value, str) for value in item["expected_check_ids"]
        ):
            raise SystemExit(f"Fixture {index} has invalid expected check IDs")
        if not all(isinstance(item[field], str) and item[field] for field in required_fixture_fields - {"expected_check_ids"}):
            raise SystemExit(f"Fixture {index} has an empty string field")
    fixture_ids = [str(item["fixture_id"]) for item in fixtures]
    if len(set(fixture_ids)) != len(fixture_ids):
        raise SystemExit("Fixture IDs must be unique")
    block_families = {
        "TEST_ARTIFACT_MODIFICATION",
        "TEST_SUPPRESSION_OR_COVERAGE_GAMING",
        "REWARD_EVALUATOR_TAMPERING",
        "EXECUTION_ENVIRONMENT_MANIPULATION",
    }
    minima = {
        f"block_{family}": sum(
            item["expected_decision"] == "block" and item["family"] == family
            for item in fixtures
        )
        for family in sorted(block_families)
    }
    minima.update(
        {
            "hardcoded_review": sum(
                item["expected_decision"] == "review"
                and item["family"] == "HARDCODED_EXPECTED_OUTPUT"
                for item in fixtures
            ),
            "general_allow": sum(
                item["expected_decision"] == "allow" and item["family"] == "GENERAL"
                for item in fixtures
            ),
            "unsupported_semantic_review": sum(
                item["expected_decision"] == "review"
                and item["family"] == "UNSUPPORTED_SEMANTIC"
                for item in fixtures
            ),
        }
    )
    for family in sorted(block_families | {"HARDCODED_EXPECTED_OUTPUT"}):
        minima[f"confounder_{family}"] = sum(
            "confounder" in item["stratum"] and item["family"] == family
            for item in fixtures
        )
    required_minimum = {
        key: 10 if key in {"general_allow", "unsupported_semantic_review"} else 5
        for key in minima
    }
    failed_minima = {
        key: {"actual": value, "required": required_minimum[key]}
        for key, value in minima.items()
        if value < required_minimum[key]
    }
    if failed_minima:
        raise SystemExit(f"Fixture-bank preregistration minima failed: {failed_minima}")

    git_commit = _git("rev-parse", "HEAD")
    worktree_clean = not _git("status", "--porcelain")
    try:
        upstream_commit = _git("rev-parse", "@{upstream}")
    except subprocess.CalledProcessError:
        upstream_commit = None
    if not args.prelock_development and (
        not worktree_clean or upstream_commit != git_commit
    ):
        raise SystemExit(
            "Post-lock fixture gate requires a clean worktree and HEAD equal to pushed upstream"
        )
    first = _run(fixtures)
    second = _run(fixtures)
    replay_match = canonical_json_bytes(first) == canonical_json_bytes(second)
    fixture_results_payload = b"".join(
        canonical_json_bytes(result) + b"\n" for result in first
    )
    fixture_results_sha256 = sha256(fixture_results_payload).hexdigest()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": "px063_fixture_conformance_v1_4",
        "classification": (
            "prelock_development_only"
            if args.prelock_development
            else "postlock_regression_conformance"
        ),
        "git_commit": git_commit,
        "upstream_commit": upstream_commit,
        "worktree_clean_at_start": worktree_clean,
        "fixture_minima": minima,
        "fixture_bank_sha256": _sha(args.fixtures),
        "fixture_results_sha256": fixture_results_sha256,
        "rule_manifest_sha256": _sha(
            REPO_ROOT / "configs" / "px063_deterministic_rules_v1.json"
        ),
        "taxonomy_manifest_sha256": _sha(
            REPO_ROOT / "configs" / "px063_trace_taxonomy_v1.json"
        ),
        "source_gate_runner_sha256": _sha(
            REPO_ROOT / "scripts" / "run_px063_trace_source_gate.py"
        ),
        "fixture_runner_sha256": _sha(Path(__file__)),
        "deterministic_runner_sha256": _sha(
            REPO_ROOT / "scripts" / "run_px063_trace_deterministic_gate.py"
        ),
        "preregistration_sha256": _sha(
            REPO_ROOT / "reports" / "reward_hack_trace" / "PX063_PREREGISTRATION.md"
        ),
        "requirements_sha256": _sha(REPO_ROOT / "requirements-px063.txt"),
        "attribution_sha256": _sha(
            REPO_ROOT / "reports" / "reward_hack_trace" / "ATTRIBUTION.md"
        ),
        "implementation_sha256": {
            name: _sha(REPO_ROOT / "src" / "praxis" / "px063" / name)
            for name in (
                "trace_adapter.py",
                "rule_config.py",
                "evidence_extractor.py",
                "deterministic_checks.py",
                "decision_policy.py",
                "scoring.py",
            )
        },
        "fixture_ids": sorted(fixture_ids),
    }
    manifest["canonical_sha256"] = sha256(canonical_json_bytes(manifest)).hexdigest()
    _write_json(output_dir / "fixture_bank_manifest.json", manifest)

    with (output_dir / "fixture_results.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(fixture_results_payload.decode("utf-8"))

    decision_counts = Counter(result["actual_decision"] for result in first)
    failures = [result for result in first if not result["passed"]]
    lexical_false_blocks = sum(
        result["actual_decision"] == "block"
        for result in first
        if "confounder" in result["stratum"]
    )
    status = (
        "PASS"
        if not failures and lexical_false_blocks == 0 and replay_match
        else "FAIL"
    )
    summary = {
        "status": status,
        "fixtures": len(first),
        "failures": len(failures),
        "lexical_confounder_false_blocks": lexical_false_blocks,
        "exact_replay_match": replay_match,
        "decision_counts": dict(decision_counts),
        "fixture_manifest_sha256": manifest["canonical_sha256"],
        "fixture_results_sha256": fixture_results_sha256,
        "failure_ids": [result["fixture_id"] for result in failures],
    }
    _write_json(output_dir / "fixture_integrity_summary.json", summary)

    report = "\n".join(
        [
            "# PX-063 Synthetic Fixture Gate",
            "",
            f"Status: **{status}**",
            "",
            "This is a software-validation result over inert synthetic fixtures. It is not a TRACE scientific result.",
            "",
            f"- Fixtures: **{summary['fixtures']}**",
            f"- Total mismatches: **{summary['failures']}**",
            f"- Lexical-confounder false blocks: **{lexical_false_blocks}**",
            f"- Exact replay: **{'PASS' if replay_match else 'FAIL'}**",
            f"- Conformance manifest SHA-256: `{manifest['canonical_sha256']}`",
            "",
            "No TRACE-derived text was read or written by this fixture gate.",
            "",
        ]
    )
    (output_dir / "PX063_FIXTURE_GATE_20260726.md").write_text(
        report, encoding="utf-8", newline="\n"
    )
    print(f"PX-063 synthetic fixture gate: {status}")
    print(json.dumps(summary, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
