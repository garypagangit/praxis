from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

from scripts.px057_h5_review_gate import (
    AI_CLAIM_BOUNDARY,
    AI_INDEPENDENCE_SCOPE,
    AI_SUBAGENT,
    GITHUB_HUMAN,
    REQUIRED_AI_LIMITATIONS,
    REQUIRED_AI_OPERATOR_ASSERTIONS,
    REVIEW_ARTIFACT_SCHEMA_VERSION,
    REVIEW_GATE_CONFIG_SCHEMA_VERSION,
    ReviewGateError,
    SubprocessGit,
    required_path_set_sha256,
    reviewed_files_sha256,
    sha256_bytes,
    validate_review_gate,
)


HUMAN_CLAIM_BOUNDARY = "Externally authenticated GitHub human code review."
REQUIRED_CHECKS = (
    "adjudicator_enforced",
    "cloud_gate_enforced",
    "freeze_gate_enforced",
    "launch_gate_enforced",
    "protected_set_complete",
)
REVIEWED_PATHS = ("code.py", "config.json")


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        check=check,
    )


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode("ascii").strip()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def base_config() -> dict[str, Any]:
    return {
        "schema_version": REVIEW_GATE_CONFIG_SCHEMA_VERSION,
        "experiment_id": "px057-h5-test",
        "gate_id": "PX057-H5-R1",
        "review_artifact_path": "review/predata_code_review.json",
        "review_required_paths": list(REVIEWED_PATHS),
        "artifact_commit_allowed_paths": [
            "review/predata_code_review.json",
            "review/transcript.txt",
        ],
        "accepted_reviewer_kinds": [AI_SUBAGENT],
        "human_review_required": False,
        "implementation_author_ids": ["author-agent"],
        "required_independence_scope": AI_INDEPENDENCE_SCOPE,
        "required_ai_limitations": list(REQUIRED_AI_LIMITATIONS),
        "required_checks": list(REQUIRED_CHECKS),
        "required_claim_boundary": AI_CLAIM_BOUNDARY,
        "require_artifact_absent_at_candidate": True,
        "remote": {"name": "origin", "branch": "experiment"},
    }


def candidate_records(
    client: SubprocessGit, candidate: str, paths: tuple[str, ...] = REVIEWED_PATHS
) -> list[dict[str, str]]:
    return [
        {
            "path": path,
            "git_blob_oid": client.blob_oid(candidate, path),
            "sha256": sha256_bytes(client.show_file(candidate, path)),
        }
        for path in sorted(paths)
    ]


def base_artifact(
    client: SubprocessGit,
    candidate: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    records = candidate_records(client, candidate)
    return {
        "schema_version": REVIEW_ARTIFACT_SCHEMA_VERSION,
        "experiment_id": config["experiment_id"],
        "gate_id": config["gate_id"],
        "disposition": "PASS",
        "reviewed_candidate": {
            "commit": candidate,
            "tree_oid": client.tree_oid(candidate),
            "required_path_set_sha256": required_path_set_sha256(REVIEWED_PATHS),
            "reviewed_files_sha256": reviewed_files_sha256(records),
            "files": records,
        },
        "reviewer": {
            "kind": AI_SUBAGENT,
            "id": "review-agent",
            "human": False,
            "external_identity_authenticated": False,
            "model_id": "test-model-id",
            "authentication_evidence": None,
        },
        "independence": {
            "scope": AI_INDEPENDENCE_SCOPE,
            "implementation_edits_made": False,
            "scientific_outputs_seen": False,
            "machine_verified": [],
            "operator_asserted": list(REQUIRED_AI_OPERATOR_ASSERTIONS),
            "limitations": list(REQUIRED_AI_LIMITATIONS),
        },
        "required_checks": {name: "PASS" for name in REQUIRED_CHECKS},
        "findings": [],
        "blocking_findings_open": 0,
        "human_review_performed": False,
        "claim_boundary": AI_CLAIM_BOUNDARY,
    }


@dataclass
class ReviewRepo:
    root: Path
    config: dict[str, Any]
    artifact: dict[str, Any]
    candidate: str
    review_commit: str
    artifact_path: Path
    transcript_path: Path

    @property
    def client(self) -> SubprocessGit:
        return SubprocessGit(self.root)


def make_review_repo(
    tmp_path: Path,
    *,
    artifact_before_candidate: bool = False,
    change_code_in_review_commit: bool = False,
) -> ReviewRepo:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "experiment")
    git(root, "config", "user.name", "PX057 Test")
    git(root, "config", "user.email", "px057@example.invalid")
    (root / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "config.json").write_text('{"frozen":true}\n', encoding="utf-8")
    artifact_path = root / "review" / "predata_code_review.json"
    transcript_path = root / "review" / "transcript.txt"
    if artifact_before_candidate:
        write_json(artifact_path, {"placeholder": True})
    candidate = commit(root, "candidate")

    config = base_config()
    client = SubprocessGit(root)
    artifact = base_artifact(client, candidate, config)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text("read-only review transcript\n", encoding="utf-8")
    if change_code_in_review_commit:
        (root / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    write_json(artifact_path, artifact)
    review_commit = commit(root, "record review")
    return ReviewRepo(
        root=root,
        config=config,
        artifact=artifact,
        candidate=candidate,
        review_commit=review_commit,
        artifact_path=artifact_path,
        transcript_path=transcript_path,
    )


@pytest.fixture
def review_repo(tmp_path: Path) -> ReviewRepo:
    return make_review_repo(tmp_path)


def rewrite_artifact(
    bundle: ReviewRepo,
    mutator: Callable[[dict[str, Any]], None],
    *,
    commit_change: bool = True,
) -> None:
    value = json.loads(bundle.artifact_path.read_text(encoding="utf-8"))
    mutator(value)
    write_json(bundle.artifact_path, value)
    bundle.artifact = value
    if commit_change:
        bundle.review_commit = commit(bundle.root, "mutate review artifact")


def assert_error(
    bundle: ReviewRepo,
    code: str,
    *,
    config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> ReviewGateError:
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            bundle.root,
            config or bundle.config,
            **kwargs,
        )
    assert raised.value.code == code
    assert raised.value.as_dict()["valid"] is False
    assert raised.value.as_dict()["error"]["code"] == code
    return raised.value


def test_valid_ai_subagent_review_reconstructs_exact_git_evidence(
    review_repo: ReviewRepo,
) -> None:
    result = validate_review_gate(review_repo.root, review_repo.config)

    assert result["valid"] is True
    assert result["reviewed_candidate"]["commit"] == review_repo.candidate
    assert result["reviewed_candidate"]["file_count"] == 2
    assert result["review_artifact"]["last_change_commit"] == review_repo.review_commit
    assert result["review_artifact"]["commit_changed_paths"] == [
        "review/predata_code_review.json",
        "review/transcript.txt",
    ]
    assert result["reviewer"] == {
        "kind": AI_SUBAGENT,
        "id": "review-agent",
        "human_review_performed": False,
        "external_authentication": None,
    }
    assert result["remote"] is None


def test_error_payload_is_stable_and_serializable() -> None:
    error = ReviewGateError("example", "failed", details={"path": "x"})
    assert error.as_dict() == {
        "valid": False,
        "error": {
            "code": "example",
            "message": "failed",
            "details": {"path": "x"},
        },
    }
    json.dumps(error.as_dict())


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(schema_version="unknown/v9"), "unsupported_artifact_schema"),
        (lambda value: value.update(unexpected=True), "schema_error"),
        (lambda value: value.pop("reviewer"), "schema_error"),
        (lambda value: value.update(disposition="NEEDS_CHANGES"), "review_disposition_not_pass"),
    ],
)
def test_schema_and_disposition_fail_closed(
    review_repo: ReviewRepo,
    mutation: Callable[[dict[str, Any]], Any],
    code: str,
) -> None:
    rewrite_artifact(review_repo, mutation)
    assert_error(review_repo, code)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["reviewer"].update(human=True),
        lambda value: value.update(human_review_performed=True),
        lambda value: value["reviewer"].update(
            external_identity_authenticated=True
        ),
        lambda value: value["reviewer"].update(
            authentication_evidence="github:fake"
        ),
        lambda value: value["reviewer"].update(model_id=None),
    ],
)
def test_ai_review_cannot_masquerade_as_human_or_authenticated(
    review_repo: ReviewRepo,
    mutation: Callable[[dict[str, Any]], Any],
) -> None:
    rewrite_artifact(review_repo, mutation)
    assert_error(review_repo, "reviewer_honesty_failure")


def test_reviewer_may_not_be_an_implementation_author(review_repo: ReviewRepo) -> None:
    rewrite_artifact(
        review_repo,
        lambda value: value["reviewer"].update(id="author-agent"),
    )
    assert_error(review_repo, "reviewer_not_independent")


@pytest.mark.parametrize(
    ("field", "new_value", "code"),
    [
        ("scope", "same_authoring_context", "independence_scope_mismatch"),
        ("implementation_edits_made", True, "reviewer_not_independent"),
        ("scientific_outputs_seen", True, "review_not_predata"),
    ],
)
def test_independence_and_predata_assertions_are_mandatory(
    review_repo: ReviewRepo,
    field: str,
    new_value: Any,
    code: str,
) -> None:
    rewrite_artifact(
        review_repo,
        lambda value: value["independence"].update({field: new_value}),
    )
    assert_error(review_repo, code)


def test_config_cannot_weaken_mandatory_ai_honesty_policy(
    review_repo: ReviewRepo,
) -> None:
    weak_scope = dict(review_repo.config)
    weak_scope["required_independence_scope"] = "anything"
    assert_error(review_repo, "review_policy_invalid", config=weak_scope)

    weak_limitations = dict(review_repo.config)
    weak_limitations["required_ai_limitations"] = ["not_human_review"]
    assert_error(review_repo, "review_policy_invalid", config=weak_limitations)

    weak_claim = dict(review_repo.config)
    weak_claim["required_claim_boundary"] = "Independent peer review."
    assert_error(review_repo, "review_policy_invalid", config=weak_claim)


def test_ai_artifact_must_carry_all_frozen_limitations(
    review_repo: ReviewRepo,
) -> None:
    rewrite_artifact(
        review_repo,
        lambda value: value["independence"].update(
            limitations=["not_human_review"]
        ),
    )
    assert_error(review_repo, "ai_review_limitations_missing")


def test_ai_artifact_must_carry_task_separation_assertions(
    review_repo: ReviewRepo,
) -> None:
    rewrite_artifact(
        review_repo,
        lambda value: value["independence"].update(operator_asserted=[]),
    )
    assert_error(review_repo, "ai_review_assertions_missing")


def test_claim_boundary_is_exactly_frozen(review_repo: ReviewRepo) -> None:
    rewrite_artifact(
        review_repo,
        lambda value: value.update(claim_boundary="Independent peer review."),
    )
    assert_error(review_repo, "claim_boundary_mismatch")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: value["required_checks"].pop("launch_gate_enforced"),
            "required_checks_mismatch",
        ),
        (
            lambda value: value["required_checks"].update(extra="PASS"),
            "required_checks_mismatch",
        ),
        (
            lambda value: value["required_checks"].update(
                launch_gate_enforced="FAIL"
            ),
            "required_check_not_pass",
        ),
    ],
)
def test_required_check_set_is_exact_and_every_check_must_pass(
    review_repo: ReviewRepo,
    mutation: Callable[[dict[str, Any]], Any],
    code: str,
) -> None:
    rewrite_artifact(review_repo, mutation)
    assert_error(review_repo, code)


def test_open_blocker_count_must_match_findings(review_repo: ReviewRepo) -> None:
    def mutation(value: dict[str, Any]) -> None:
        value["findings"] = [
            {
                "id": "B1",
                "severity": "blocking",
                "status": "open",
                "summary": "Launch can bypass review.",
            }
        ]
        value["blocking_findings_open"] = 0

    rewrite_artifact(review_repo, mutation)
    assert_error(review_repo, "blocking_count_mismatch")


def test_any_declared_open_blocker_forces_no_go(review_repo: ReviewRepo) -> None:
    def mutation(value: dict[str, Any]) -> None:
        value["findings"] = [
            {
                "id": "B1",
                "severity": "critical",
                "status": "open",
                "summary": "Freeze accepts a missing artifact.",
            }
        ]
        value["blocking_findings_open"] = 1

    rewrite_artifact(review_repo, mutation)
    assert_error(review_repo, "open_blocking_findings")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: value["reviewed_candidate"].update(
                tree_oid="0" * 40
            ),
            "candidate_tree_mismatch",
        ),
        (
            lambda value: value["reviewed_candidate"].update(
                required_path_set_sha256="0" * 64
            ),
            "required_path_set_mismatch",
        ),
        (
            lambda value: value["reviewed_candidate"]["files"][0].update(
                sha256="0" * 64
            ),
            "candidate_file_manifest_mismatch",
        ),
        (
            lambda value: value["reviewed_candidate"].update(
                reviewed_files_sha256="0" * 64
            ),
            "reviewed_files_digest_mismatch",
        ),
        (
            lambda value: value["reviewed_candidate"].update(commit="HEAD"),
            "object_id_invalid",
        ),
    ],
)
def test_candidate_tree_path_set_files_and_full_commit_are_reconstructed(
    review_repo: ReviewRepo,
    mutation: Callable[[dict[str, Any]], Any],
    code: str,
) -> None:
    rewrite_artifact(review_repo, mutation)
    assert_error(review_repo, code)


def test_candidate_file_list_must_be_exact_and_deterministically_ordered(
    review_repo: ReviewRepo,
) -> None:
    rewrite_artifact(
        review_repo,
        lambda value: value["reviewed_candidate"].update(
            files=list(reversed(value["reviewed_candidate"]["files"]))
        ),
    )
    assert_error(review_repo, "candidate_file_manifest_mismatch")


def test_missing_candidate_path_has_a_specific_error(review_repo: ReviewRepo) -> None:
    config = dict(review_repo.config)
    config["review_required_paths"] = [*REVIEWED_PATHS, "missing.py"]

    def mutation(value: dict[str, Any]) -> None:
        value["reviewed_candidate"]["required_path_set_sha256"] = (
            required_path_set_sha256(config["review_required_paths"])
        )

    rewrite_artifact(review_repo, mutation)
    assert_error(review_repo, "candidate_file_missing", config=config)


class RejectingAncestryGit:
    def __init__(self, delegate: SubprocessGit) -> None:
        self.delegate = delegate

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return False


def test_git_dependency_is_injectable_and_non_ancestry_fails(
    review_repo: ReviewRepo,
) -> None:
    assert_error(
        review_repo,
        "review_commit_order_invalid",
        git=RejectingAncestryGit(review_repo.client),
    )


def test_review_record_commit_may_change_only_declared_review_artifacts(
    tmp_path: Path,
) -> None:
    bundle = make_review_repo(tmp_path, change_code_in_review_commit=True)
    error = assert_error(bundle, "artifact_commit_scope_invalid")
    assert error.details["unexpected"] == ["code.py"]


def test_current_reviewed_bytes_must_still_equal_candidate(
    review_repo: ReviewRepo,
) -> None:
    (review_repo.root / "code.py").write_text("VALUE = 99\n", encoding="utf-8")
    commit(review_repo.root, "change code after review")
    error = assert_error(review_repo, "reviewed_files_changed")
    assert error.details["changed"][0]["path"] == "code.py"


def test_modifying_then_reverting_reviewed_bytes_still_invalidates_review(
    review_repo: ReviewRepo,
) -> None:
    code_path = review_repo.root / "code.py"
    code_path.write_text("VALUE = 99\n", encoding="utf-8")
    commit(review_repo.root, "temporarily change reviewed code")
    code_path.write_text("VALUE = 1\n", encoding="utf-8")
    commit(review_repo.root, "revert reviewed code bytes")

    error = assert_error(review_repo, "reviewed_path_history_changed")
    assert error.details["changed"][0]["path"] == "code.py"


def test_dirty_reviewed_file_is_rejected_before_execution(
    review_repo: ReviewRepo,
) -> None:
    (review_repo.root / "code.py").write_text("VALUE = 99\n", encoding="utf-8")
    assert_error(review_repo, "reviewed_file_dirty")


def test_review_artifact_must_be_committed_clean_and_present(
    review_repo: ReviewRepo,
) -> None:
    review_repo.artifact_path.write_text("{}\n", encoding="utf-8")
    assert_error(review_repo, "review_artifact_dirty")

    git(review_repo.root, "restore", "--", "review/predata_code_review.json")
    review_repo.artifact_path.unlink()
    assert_error(review_repo, "review_artifact_missing")


def test_final_review_artifact_must_not_preexist_in_candidate(tmp_path: Path) -> None:
    bundle = make_review_repo(tmp_path, artifact_before_candidate=True)
    assert_error(bundle, "stale_review_artifact")


def test_duplicate_json_keys_are_rejected(review_repo: ReviewRepo) -> None:
    raw = review_repo.artifact_path.read_text(encoding="utf-8")
    raw = raw.replace(
        '  "disposition": "PASS",',
        '  "disposition": "PASS",\n  "disposition": "PASS",',
        1,
    )
    review_repo.artifact_path.write_text(raw, encoding="utf-8")
    commit(review_repo.root, "duplicate JSON key")
    assert_error(review_repo, "duplicate_json_key")


@pytest.mark.parametrize(
    "bad_path",
    ["../review.json", "C:/review.json", "review\\review.json"],
)
def test_unsafe_artifact_paths_are_rejected(
    review_repo: ReviewRepo,
    bad_path: str,
) -> None:
    config = dict(review_repo.config)
    config["review_artifact_path"] = bad_path
    assert_error(review_repo, "unsafe_path", config=config)


def test_duplicate_or_case_colliding_required_paths_are_rejected(
    review_repo: ReviewRepo,
) -> None:
    duplicate = dict(review_repo.config)
    duplicate["review_required_paths"] = ["code.py", "code.py"]
    assert_error(review_repo, "path_inventory_invalid", config=duplicate)

    collision = dict(review_repo.config)
    collision["review_required_paths"] = ["code.py", "CODE.py"]
    assert_error(review_repo, "path_inventory_invalid", config=collision)


def configure_bare_remote(bundle: ReviewRepo, tmp_path: Path) -> Path:
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(bare)],
        capture_output=True,
        check=True,
    )
    git(bundle.root, "remote", "add", "origin", str(bare))
    git(bundle.root, "push", "-q", "-u", "origin", "experiment")
    return bare


def test_optional_remote_reachability_uses_live_remote_branch(
    review_repo: ReviewRepo,
    tmp_path: Path,
) -> None:
    configure_bare_remote(review_repo, tmp_path)
    result = validate_review_gate(
        review_repo.root,
        review_repo.config,
        require_remote_reachability=True,
    )
    assert result["remote"]["head"] == review_repo.review_commit


def test_unpushed_current_head_fails_remote_reachability(
    review_repo: ReviewRepo,
    tmp_path: Path,
) -> None:
    configure_bare_remote(review_repo, tmp_path)
    (review_repo.root / "runtime.json").write_text("{}\n", encoding="utf-8")
    commit(review_repo.root, "local runtime evidence")
    error = assert_error(
        review_repo,
        "remote_reachability_failure",
        require_remote_reachability=True,
    )
    assert error.details["unreachable"] == ["head"]


def test_missing_remote_is_a_structured_hard_failure(
    review_repo: ReviewRepo,
) -> None:
    assert_error(
        review_repo,
        "remote_evidence_unavailable",
        require_remote_reachability=True,
    )


def make_human_review(bundle: ReviewRepo) -> dict[str, Any]:
    config = dict(bundle.config)
    config["accepted_reviewer_kinds"] = [GITHUB_HUMAN]
    config["human_review_required"] = True
    config["required_claim_boundary"] = HUMAN_CLAIM_BOUNDARY

    def mutation(value: dict[str, Any]) -> None:
        value["reviewer"] = {
            "kind": GITHUB_HUMAN,
            "id": "github:reviewer",
            "human": True,
            "external_identity_authenticated": True,
            "model_id": None,
            "authentication_evidence": "github-review-api:12345",
        }
        value["human_review_performed"] = True
        value["claim_boundary"] = HUMAN_CLAIM_BOUNDARY

    rewrite_artifact(bundle, mutation)
    return config


def test_human_claim_requires_injected_external_authentication(
    review_repo: ReviewRepo,
) -> None:
    config = make_human_review(review_repo)
    assert_error(review_repo, "human_authentication_unverified", config=config)

    result = validate_review_gate(
        review_repo.root,
        config,
        human_authenticator=lambda reviewer, artifact, frozen: {
            "valid": reviewer["id"] == "github:reviewer",
            "source": "test-github-api",
            "gate_id": frozen.gate_id,
        },
    )
    assert result["valid"] is True
    assert result["reviewer"]["human_review_performed"] is True
    assert result["reviewer"]["external_authentication"]["valid"] is True


def test_human_required_policy_rejects_ai_review(review_repo: ReviewRepo) -> None:
    config = dict(review_repo.config)
    config["accepted_reviewer_kinds"] = [GITHUB_HUMAN]
    config["human_review_required"] = True
    config["required_claim_boundary"] = HUMAN_CLAIM_BOUNDARY
    assert_error(review_repo, "reviewer_kind_not_accepted", config=config)


def test_git_process_executor_is_injectable(review_repo: ReviewRepo) -> None:
    calls: list[tuple[str, ...]] = []

    def executor(
        args: tuple[str, ...], repo_root: Path
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )

    client = SubprocessGit(review_repo.root, executor=executor)
    result = validate_review_gate(
        review_repo.root,
        review_repo.config,
        git=client,
    )
    assert result["valid"] is True
    assert any(call[:2] == ("rev-parse", "--verify") for call in calls)
