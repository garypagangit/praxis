from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_px063_trace_source_gate import _attribution_notice_checks
from scripts.run_px063_trace_deterministic_gate import _GATE0_CHECK_FIELDS


REPO_ROOT = Path(__file__).resolve().parents[1]


def _synthetic_complete_notice() -> str:
    return """
# PX-063 Data Attribution and Change Notice

## Original work

- Title: TRACE (Testing Reward Anomalies in Code Environments)
- Creators: Darshan Deshpande, Anand Kannappan, Rebecca Qian / Patronus AI
- Dataset: https://huggingface.co/datasets/PatronusAI/trace-dataset/tree/31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d
- Paper: Benchmarking Reward Hack Detection in Code Environments via Contrastive Analysis, https://arxiv.org/abs/2601.20103
- License: CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/

## Community normalization

- Dataset: https://huggingface.co/datasets/ktolnos/rh-bench/tree/1045a7336432c40182924bbd3698af292ea24acb
- Code: https://github.com/ktolnos/rh-bench/tree/090e47b878192ee7a016d6c89e983141a415b154

## Praxis changes

Praxis filters the community dataset, coalesces the single populated response,
uses pseudonymous identifiers, and applies an independently implemented
verifier. Committed artifacts do not contain raw TRACE text.
"""


def test_complete_synthetic_attribution_notice_passes_every_check() -> None:
    checks = _attribution_notice_checks(_synthetic_complete_notice())
    assert checks
    assert all(checks.values())


@pytest.mark.parametrize(
    ("required_text", "replacement", "failed_check"),
    [
        (
            "TRACE (Testing Reward Anomalies in Code Environments)",
            "TRACE",
            "attribution_work_title_recorded",
        ),
        (
            "Benchmarking Reward Hack Detection in Code Environments via Contrastive Analysis",
            "Reward-hack paper",
            "attribution_paper_title_recorded",
        ),
        (
            "https://arxiv.org/abs/2601.20103",
            "https://arxiv.org/",
            "attribution_paper_source_recorded",
        ),
        ("Rebecca Qian", "A missing creator", "attribution_creators_recorded"),
        (
            "https://huggingface.co/datasets/PatronusAI/trace-dataset/tree/31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d",
            "https://huggingface.co/datasets/PatronusAI/trace-dataset",
            "attribution_official_source_revision_pinned",
        ),
        (
            "https://huggingface.co/datasets/ktolnos/rh-bench/tree/1045a7336432c40182924bbd3698af292ea24acb",
            "https://huggingface.co/datasets/ktolnos/rh-bench",
            "attribution_community_dataset_revision_pinned",
        ),
        (
            "https://github.com/ktolnos/rh-bench/tree/090e47b878192ee7a016d6c89e983141a415b154",
            "https://github.com/ktolnos/rh-bench",
            "attribution_community_code_revision_pinned",
        ),
        (
            "https://creativecommons.org/licenses/by-sa/4.0/",
            "https://creativecommons.org/",
            "attribution_license_recorded",
        ),
        (
            "CC BY-SA 4.0",
            "A license",
            "attribution_license_recorded",
        ),
        (
            "## Praxis changes",
            "## Notes",
            "attribution_praxis_change_notice_recorded",
        ),
        (
            "independently implemented",
            "third-party",
            "attribution_praxis_change_notice_recorded",
        ),
    ],
)
def test_incomplete_synthetic_attribution_notice_fails_closed(
    required_text: str, replacement: str, failed_check: str
) -> None:
    notice = _synthetic_complete_notice().replace(required_text, replacement)
    checks = _attribution_notice_checks(notice)
    assert checks[failed_check] is False
    assert not all(checks.values())


def test_checked_in_attribution_notice_passes_every_check() -> None:
    notice = (
        REPO_ROOT / "reports" / "reward_hack_trace" / "ATTRIBUTION.md"
    ).read_text(encoding="utf-8")
    assert all(_attribution_notice_checks(notice).values())


def test_deterministic_preflight_binds_the_complete_gate0_check_schema() -> None:
    base_gate0_checks = {
        "parent_worktree_clean_at_start",
        "parent_head_pushed_at_start",
        "rhbench_url_pinned",
        "rhbench_commit_pinned",
        "rhbench_worktree_clean",
        "rhbench_superproject_gitlink_pinned",
        "rhbench_gitmodules_entry_pinned",
        "unlicensed_external_helpers_not_loaded",
        "missing_external_code_license_recorded",
        "derivative_dataset_cc_by_sa_4_0",
        "official_card_revision_pinned",
        "official_card_sha256_pinned",
        "official_dataset_cc_by_sa_4_0",
        "official_direct_use_notice_recorded",
        "official_out_of_scope_notice_recorded",
        "attribution_notice_complete",
        "trace_taxonomy_sha256_pinned",
        "trace_taxonomy_schema_pinned",
        "trace_taxonomy_atomic_codes_pinned",
    }
    attribution_checks = set(_attribution_notice_checks(_synthetic_complete_notice()))

    assert _GATE0_CHECK_FIELDS == base_gate0_checks | attribution_checks
