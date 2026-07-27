from __future__ import annotations

import json
import inspect
import os
import shutil
import stat
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
    MANDATORY_REVIEW_CHECKS,
    REQUIRED_AI_LIMITATIONS,
    REQUIRED_AI_OPERATOR_ASSERTIONS,
    REVIEW_ARTIFACT_SCHEMA_VERSION,
    REVIEW_GATE_CONFIG_SCHEMA_VERSION,
    WORKTREE_BYTE_POLICY,
    GitOperationError,
    ReviewGateError,
    SubprocessGit,
    required_path_set_sha256,
    reviewed_files_sha256,
    sha256_bytes,
    validate_review_gate,
    _validate_review_gate_evidence_for_tests,
    _local_regular_path,
)


HUMAN_CLAIM_BOUNDARY = "Externally authenticated GitHub human code review."
REQUIRED_CHECKS = MANDATORY_REVIEW_CHECKS
REVIEWED_PATHS = ("code.py", "config.json")
EVIDENCE_PATHS = (
    "review/predata_code_review.json",
    "review/transcript.txt",
)
PROTECTED_PATHS = (*REVIEWED_PATHS, *EVIDENCE_PATHS)


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
        "protected_paths": list(PROTECTED_PATHS),
        "review_required_paths": list(REVIEWED_PATHS),
        "artifact_commit_allowed_paths": list(EVIDENCE_PATHS),
        "accepted_reviewer_kinds": [AI_SUBAGENT],
        "human_review_required": False,
        "implementation_author_ids": ["author-agent"],
        "required_independence_scope": AI_INDEPENDENCE_SCOPE,
        "required_ai_limitations": list(REQUIRED_AI_LIMITATIONS),
        "required_checks": list(REQUIRED_CHECKS),
        "required_claim_boundary": AI_CLAIM_BOUNDARY,
        "worktree_byte_policy": WORKTREE_BYTE_POLICY,
        "require_artifact_absent_at_candidate": True,
        "remote": {
            "name": "origin",
            "url": "https://example.invalid/px057.git",
            "branch": "experiment",
        },
    }


def add_protected_reviewed_path(config: dict[str, Any], path: str) -> None:
    config["protected_paths"] = sorted([*config["protected_paths"], path])
    config["review_required_paths"] = sorted(
        [*config["review_required_paths"], path]
    )


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
    record_paths = tuple(
        path
        for path in config["review_required_paths"]
        if client.path_entry(candidate, path) is not None
    )
    records = candidate_records(client, candidate, record_paths)
    return {
        "schema_version": REVIEW_ARTIFACT_SCHEMA_VERSION,
        "experiment_id": config["experiment_id"],
        "gate_id": config["gate_id"],
        "disposition": "PASS",
        "reviewed_candidate": {
            "commit": candidate,
            "tree_oid": client.tree_oid(candidate),
            "required_path_set_sha256": required_path_set_sha256(
                config["review_required_paths"]
            ),
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
    omit_transcript: bool = False,
    config_mutator: Callable[[dict[str, Any]], None] | None = None,
    artifact_mutator: Callable[[dict[str, Any]], None] | None = None,
    candidate_setup: Callable[[Path], None] | None = None,
    candidate_index_mutator: Callable[[Path], None] | None = None,
) -> ReviewRepo:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "experiment")
    git(root, "config", "user.name", "PX057 Test")
    git(root, "config", "user.email", "px057@example.invalid")
    config = base_config()
    if config_mutator is not None:
        config_mutator(config)
    (root / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    write_json(root / "config.json", config)
    artifact_path = root / "review" / "predata_code_review.json"
    transcript_path = root / "review" / "transcript.txt"
    if artifact_before_candidate:
        write_json(artifact_path, {"placeholder": True})
    if candidate_setup is not None:
        candidate_setup(root)
    git(root, "add", "-A")
    if candidate_index_mutator is not None:
        candidate_index_mutator(root)
    git(root, "commit", "-q", "-m", "candidate")
    candidate = git(root, "rev-parse", "HEAD").stdout.decode("ascii").strip()

    client = SubprocessGit(root)
    artifact = base_artifact(client, candidate, config)
    if artifact_mutator is not None:
        artifact_mutator(artifact)
    if not omit_transcript:
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
        git(bundle.root, "add", "-A")
        git(bundle.root, "commit", "-q", "--amend", "--no-edit")
        bundle.review_commit = git(
            bundle.root, "rev-parse", "HEAD"
        ).stdout.decode("ascii").strip()


def local_validation_kwargs(bundle: ReviewRepo) -> dict[str, Any]:
    config_bytes = bundle.client.show_file("HEAD", "config.json")
    return {
        "config_path": "config.json",
        "expected_config_sha256": sha256_bytes(config_bytes),
        "expected_protected_paths": bundle.config["protected_paths"],
        "mandatory_sentinel_paths": REVIEWED_PATHS,
    }


def production_validation_kwargs(bundle: ReviewRepo) -> dict[str, Any]:
    result = local_validation_kwargs(bundle)
    result["expected_remote_tip"] = git(
        bundle.root, "rev-parse", "HEAD"
    ).stdout.decode("ascii").strip()
    result["expected_remote_url"] = bundle.config["remote"]["url"]
    git_executable = shutil.which("git")
    assert git_executable is not None
    result["trusted_git_executable"] = str(Path(git_executable).resolve())
    return result


def assert_error(
    bundle: ReviewRepo,
    code: str,
    *,
    config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> ReviewGateError:
    with pytest.raises(ReviewGateError) as raised:
        _validate_review_gate_evidence_for_tests(
            bundle.root,
            config or bundle.config,
            **local_validation_kwargs(bundle),
            **kwargs,
        )
    assert raised.value.code == code
    assert raised.value.as_dict()["valid"] is False
    assert raised.value.as_dict()["error"]["code"] == code
    return raised.value


def test_valid_ai_subagent_review_reconstructs_exact_git_evidence(
    review_repo: ReviewRepo,
) -> None:
    result = _validate_review_gate_evidence_for_tests(
        review_repo.root,
        review_repo.config,
        **local_validation_kwargs(review_repo),
    )

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
    tmp_path: Path,
) -> None:
    mutations = (
        lambda value: value.update(required_independence_scope="anything"),
        lambda value: value.update(
            required_ai_limitations=["not_human_review"]
        ),
        lambda value: value.update(
            required_claim_boundary="Independent peer review."
        ),
    )
    for index, mutation in enumerate(mutations):
        bundle = make_review_repo(
            tmp_path / str(index), config_mutator=mutation
        )
        assert_error(bundle, "review_policy_invalid")


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


def test_missing_candidate_path_has_a_specific_error(tmp_path: Path) -> None:
    def mutation(config: dict[str, Any]) -> None:
        config["protected_paths"] = [
            *REVIEWED_PATHS,
            "missing.py",
            *EVIDENCE_PATHS,
        ]
        config["review_required_paths"] = [*REVIEWED_PATHS, "missing.py"]

    bundle = make_review_repo(tmp_path, config_mutator=mutation)
    assert_error(bundle, "candidate_file_missing")


def test_candidate_tree_is_not_accepted_as_a_reviewed_file(
    tmp_path: Path,
) -> None:
    bundle = make_review_repo(
        tmp_path,
        config_mutator=lambda config: add_protected_reviewed_path(
            config, "folder"
        ),
        candidate_setup=lambda root: (
            (root / "folder").mkdir(),
            (root / "folder" / "item.txt").write_text(
                "item\n", encoding="utf-8"
            ),
        ),
    )
    assert_error(bundle, "candidate_file_not_regular")


def test_candidate_symlink_mode_is_not_accepted_as_a_reviewed_file(
    tmp_path: Path,
) -> None:
    def setup(root: Path) -> None:
        (root / "link").write_text("target.txt\n", encoding="utf-8")

    def make_index_symlink(root: Path) -> None:
        result = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=root,
            input=b"target.txt\n",
            capture_output=True,
            check=True,
        )
        oid = result.stdout.decode("ascii").strip()
        git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            f"120000,{oid},link",
        )

    bundle = make_review_repo(
        tmp_path,
        config_mutator=lambda config: add_protected_reviewed_path(
            config, "link"
        ),
        candidate_setup=setup,
        candidate_index_mutator=make_index_symlink,
    )
    assert_error(bundle, "candidate_file_not_regular")


def test_symbolic_link_parent_in_worktree_is_rejected(tmp_path: Path) -> None:
    def setup(root: Path) -> None:
        nested = root / "nested"
        nested.mkdir()
        (nested / "code.py").write_text("NESTED = 1\n", encoding="utf-8")

    bundle = make_review_repo(
        tmp_path,
        config_mutator=lambda config: add_protected_reviewed_path(
            config, "nested/code.py"
        ),
        candidate_setup=setup,
    )
    nested = bundle.root / "nested"
    external = tmp_path / "external-nested"
    shutil.move(str(nested), str(external))
    try:
        os.symlink(external, nested, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    assert_error(bundle, "worktree_path_not_regular")


def test_symbolic_link_parent_check_is_platform_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    nested = root / "nested"
    nested.mkdir(parents=True)
    target = nested / "code.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    original_lstat = Path.lstat

    def fake_lstat(path: Path) -> os.stat_result:
        if path == nested:
            original = original_lstat(path)
            values = list(original)
            values[0] = stat.S_IFLNK | 0o777
            return os.stat_result(values)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ReviewGateError) as raised:
        _local_regular_path(
            root,
            "nested/code.py",
            missing_code="reviewed_file_missing",
        )
    assert raised.value.code == "worktree_path_not_regular"


def test_windows_junction_or_reparse_parent_is_rejected_cross_platform(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (nested / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    original_lstat = Path.lstat

    class ReparseDirectory:
        st_mode = stat.S_IFDIR | 0o755
        st_reparse_tag = 0xA0000003

    def fake_lstat(path: Path) -> Any:
        if path == nested:
            return ReparseDirectory()
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ReviewGateError) as raised:
        _local_regular_path(
            root,
            "nested/code.py",
            missing_code="reviewed_file_missing",
        )
    assert raised.value.code == "worktree_path_not_regular"


class FailingAbsenceProbeGit:
    def __init__(self, delegate: SubprocessGit, candidate: str) -> None:
        self.delegate = delegate
        self.candidate = candidate

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)

    def path_entry(self, commit: str, path: str) -> Any:
        if commit == self.candidate and path == EVIDENCE_PATHS[0]:
            raise GitOperationError(
                ("ls-tree", commit, path), 128, b"", b"injected failure"
            )
        return self.delegate.path_entry(commit, path)


def test_operational_failure_during_absence_probe_is_fatal(
    review_repo: ReviewRepo,
) -> None:
    assert_error(
        review_repo,
        "git_evidence_unavailable",
        git=FailingAbsenceProbeGit(review_repo.client, review_repo.candidate),
    )


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


def test_untracked_import_shadow_is_rejected(review_repo: ReviewRepo) -> None:
    (review_repo.root / "sitecustomize.py").write_text(
        "raise RuntimeError('shadowed')\n", encoding="utf-8"
    )
    assert_error(review_repo, "worktree_not_clean")


def test_clean_tracked_import_shadow_added_after_r_is_rejected(
    review_repo: ReviewRepo,
) -> None:
    (review_repo.root / "sitecustomize.py").write_text(
        "raise RuntimeError('shadowed')\n", encoding="utf-8"
    )
    commit(review_repo.root, "add tracked import shadow after review")
    error = assert_error(review_repo, "post_review_tree_changed")
    assert error.details["unexpected"] == ["sitecustomize.py"]


def test_ignored_import_shadow_is_also_rejected(tmp_path: Path) -> None:
    review_repo = make_review_repo(
        tmp_path,
        candidate_setup=lambda root: (root / ".gitignore").write_text(
            "json.py\n", encoding="utf-8"
        ),
    )
    (review_repo.root / "json.py").write_text(
        "raise RuntimeError('shadowed')\n", encoding="utf-8"
    )
    assert_error(review_repo, "worktree_not_clean")


def test_assume_unchanged_cannot_hide_modified_executable_bytes(
    review_repo: ReviewRepo,
) -> None:
    git(review_repo.root, "update-index", "--assume-unchanged", "code.py")
    (review_repo.root / "code.py").write_text("VALUE = 404\n", encoding="utf-8")
    assert_error(review_repo, "forbidden_index_flag")


def test_skip_worktree_cannot_hide_modified_executable_bytes(
    review_repo: ReviewRepo,
) -> None:
    git(review_repo.root, "update-index", "--skip-worktree", "code.py")
    (review_repo.root / "code.py").write_text("VALUE = 405\n", encoding="utf-8")
    assert_error(review_repo, "forbidden_index_flag")


class GitMetadataBlindSpot:
    """Simulate status/filter metadata falsely reporting a clean checkout."""

    def __init__(self, delegate: SubprocessGit) -> None:
        self.delegate = delegate

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)

    def status_for_path(self, path: str) -> bytes:
        return b""

    def index_tag(self, path: str) -> str:
        return "H"

def test_raw_worktree_bytes_are_checked_even_if_git_metadata_lies(
    review_repo: ReviewRepo,
) -> None:
    (review_repo.root / "code.py").write_text("VALUE = 999\n", encoding="utf-8")
    assert_error(
        review_repo,
        "reviewed_file_dirty",
        git=GitMetadataBlindSpot(review_repo.client),
    )


def test_historical_revision_cannot_be_validated_against_another_checkout(
    review_repo: ReviewRepo,
) -> None:
    assert_error(
        review_repo,
        "validated_head_not_checkout",
        head_revision=review_repo.candidate,
    )


def test_full_dag_detects_no_ff_side_branch_change_and_revert(
    review_repo: ReviewRepo,
) -> None:
    git(review_repo.root, "switch", "-q", "-c", "side-review-bypass")
    code_path = review_repo.root / "code.py"
    code_path.write_text("VALUE = 500\n", encoding="utf-8")
    commit(review_repo.root, "side branch changes reviewed code")
    code_path.write_text("VALUE = 1\n", encoding="utf-8")
    commit(review_repo.root, "side branch restores reviewed code")
    git(review_repo.root, "switch", "-q", "experiment")
    git(
        review_repo.root,
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "merge reverted side branch",
        "side-review-bypass",
    )

    error = assert_error(review_repo, "reviewed_path_history_changed")
    assert error.details["changed"][0]["path"] == "code.py"


@pytest.mark.parametrize("operation", ["edit", "delete"])
def test_review_transcript_is_mandatory_and_immutable_after_r(
    review_repo: ReviewRepo,
    operation: str,
) -> None:
    if operation == "edit":
        review_repo.transcript_path.write_text("altered\n", encoding="utf-8")
    else:
        review_repo.transcript_path.unlink()
    commit(review_repo.root, f"{operation} transcript after review")
    assert_error(review_repo, "review_evidence_history_invalid")


def test_artifact_modify_then_revert_cannot_redefine_r(
    review_repo: ReviewRepo,
) -> None:
    original = review_repo.artifact_path.read_bytes()
    review_repo.artifact_path.write_bytes(original + b"\n")
    commit(review_repo.root, "temporarily alter artifact")
    review_repo.artifact_path.write_bytes(original)
    commit(review_repo.root, "restore artifact bytes")
    assert_error(review_repo, "review_evidence_history_invalid")


def test_all_declared_review_evidence_must_be_introduced_at_r(
    tmp_path: Path,
) -> None:
    bundle = make_review_repo(tmp_path, omit_transcript=True)
    error = assert_error(bundle, "artifact_commit_scope_invalid")
    assert error.details["missing"] == ["review/transcript.txt"]


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
    tmp_path: Path,
    bad_path: str,
) -> None:
    bundle = make_review_repo(
        tmp_path,
        config_mutator=lambda config: config.update(
            review_artifact_path=bad_path
        ),
    )
    assert_error(bundle, "unsafe_path")


def test_duplicate_or_case_colliding_required_paths_are_rejected(
    tmp_path: Path,
) -> None:
    duplicate = make_review_repo(
        tmp_path / "duplicate",
        config_mutator=lambda config: config.update(
            review_required_paths=["code.py", "code.py"]
        ),
    )
    assert_error(duplicate, "path_inventory_invalid")

    collision = make_review_repo(
        tmp_path / "collision",
        config_mutator=lambda config: config.update(
            review_required_paths=["code.py", "CODE.py"]
        ),
    )
    assert_error(collision, "path_inventory_invalid")


def test_supplied_policy_must_equal_the_exact_committed_mapping(
    review_repo: ReviewRepo,
) -> None:
    alternate = dict(review_repo.config)
    alternate["gate_id"] = "substituted-policy"
    assert_error(review_repo, "config_mapping_mismatch", config=alternate)


def test_trusted_whole_config_hash_is_enforced(review_repo: ReviewRepo) -> None:
    kwargs = local_validation_kwargs(review_repo)
    kwargs["expected_config_sha256"] = "0" * 64
    with pytest.raises(ReviewGateError) as raised:
        _validate_review_gate_evidence_for_tests(
            review_repo.root,
            review_repo.config,
            **kwargs,
        )
    assert raised.value.code == "config_hash_mismatch"


def test_committed_config_cannot_be_hidden_with_assume_unchanged(
    review_repo: ReviewRepo,
) -> None:
    git(review_repo.root, "update-index", "--assume-unchanged", "config.json")
    (review_repo.root / "config.json").write_text("{}\n", encoding="utf-8")
    assert_error(review_repo, "forbidden_index_flag")


def test_required_paths_are_derived_from_protected_minus_postreview(
    tmp_path: Path,
) -> None:
    bundle = make_review_repo(
        tmp_path,
        config_mutator=lambda config: config.update(
            protected_paths=["config.json", *EVIDENCE_PATHS]
        ),
    )
    assert_error(bundle, "protected_path_inventory_invalid")


def test_mandatory_checks_cannot_be_removed_from_committed_policy(
    tmp_path: Path,
) -> None:
    bundle = make_review_repo(
        tmp_path,
        config_mutator=lambda config: config.update(
            required_checks=[
                check for check in REQUIRED_CHECKS if check != "launch_gate_enforced"
            ]
        ),
    )
    assert_error(bundle, "review_policy_invalid")


def test_external_protected_inventory_and_sentinels_are_independently_bound(
    review_repo: ReviewRepo,
) -> None:
    kwargs = local_validation_kwargs(review_repo)
    kwargs["expected_protected_paths"] = [
        "code.py",
        "config.json",
        "extra-sentinel.py",
        *EVIDENCE_PATHS,
    ]
    with pytest.raises(ReviewGateError) as raised:
        _validate_review_gate_evidence_for_tests(
            review_repo.root,
            review_repo.config,
            **kwargs,
        )
    assert raised.value.code == "protected_path_inventory_mismatch"

    kwargs = local_validation_kwargs(review_repo)
    kwargs["mandatory_sentinel_paths"] = ["missing-launch.py"]
    with pytest.raises(ReviewGateError) as raised:
        _validate_review_gate_evidence_for_tests(
            review_repo.root,
            review_repo.config,
            **kwargs,
        )
    assert raised.value.code == "mandatory_sentinel_missing"


def test_config_path_is_nonoptional_even_for_offline_validation(
    review_repo: ReviewRepo,
) -> None:
    with pytest.raises(ReviewGateError) as raised:
        _validate_review_gate_evidence_for_tests(
            review_repo.root,
            review_repo.config,
            config_path=None,
        )
    assert raised.value.code == "config_evidence_required"


def test_git_replace_refs_are_rejected_and_never_interpreted(
    review_repo: ReviewRepo,
) -> None:
    git(
        review_repo.root,
        "replace",
        review_repo.candidate,
        review_repo.review_commit,
    )
    error = assert_error(review_repo, "replacement_objects_forbidden")
    assert error.details["refs"]


def test_legacy_grafts_are_rejected(review_repo: ReviewRepo) -> None:
    raw_path = git(
        review_repo.root, "rev-parse", "--git-path", "info/grafts"
    ).stdout.decode("utf-8").strip()
    grafts = Path(raw_path)
    if not grafts.is_absolute():
        grafts = review_repo.root / grafts
    grafts.parent.mkdir(parents=True, exist_ok=True)
    grafts.write_text(f"{review_repo.candidate}\n", encoding="ascii")
    assert_error(review_repo, "grafts_forbidden")


def test_shallow_repository_cannot_make_full_history_claims(
    review_repo: ReviewRepo,
) -> None:
    raw_path = git(
        review_repo.root, "rev-parse", "--git-path", "shallow"
    ).stdout.decode("utf-8").strip()
    shallow = Path(raw_path)
    if not shallow.is_absolute():
        shallow = review_repo.root / shallow
    shallow.write_text(f"{review_repo.candidate}\n", encoding="ascii")
    assert_error(review_repo, "shallow_repository_forbidden")


def test_local_info_attributes_are_rejected(review_repo: ReviewRepo) -> None:
    raw_path = git(
        review_repo.root, "rev-parse", "--git-path", "info/attributes"
    ).stdout.decode("utf-8").strip()
    attributes = Path(raw_path)
    if not attributes.is_absolute():
        attributes = review_repo.root / attributes
    attributes.parent.mkdir(parents=True, exist_ok=True)
    attributes.write_text("code.py filter=evil\n", encoding="utf-8")
    assert_error(review_repo, "local_attributes_forbidden")


def test_external_attributes_file_is_rejected(review_repo: ReviewRepo) -> None:
    attributes = review_repo.root / "external.attributes"
    attributes.write_text("code.py filter=evil\n", encoding="utf-8")
    git(review_repo.root, "config", "core.attributesfile", str(attributes))
    assert_error(review_repo, "external_attributes_forbidden")


def test_active_filter_attribute_on_protected_code_is_rejected(
    review_repo: ReviewRepo,
) -> None:
    (review_repo.root / ".gitattributes").write_text(
        "code.py filter=evil\n", encoding="utf-8"
    )
    commit(review_repo.root, "try to filter protected worktree bytes")
    assert_error(review_repo, "dangerous_git_attributes")


def make_remote_review_repo(tmp_path: Path) -> tuple[ReviewRepo, Path]:
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(bare)],
        capture_output=True,
        check=True,
    )
    bundle = make_review_repo(
        tmp_path / "work",
        config_mutator=lambda config: config["remote"].update(url=str(bare)),
    )
    git(bundle.root, "remote", "add", "origin", str(bare))
    git(bundle.root, "push", "-q", "-u", "origin", "experiment")
    return bundle, bare


def test_production_gate_requires_exact_live_remote_tip(
    tmp_path: Path,
) -> None:
    review_repo, _ = make_remote_review_repo(tmp_path)
    result = validate_review_gate(
        review_repo.root,
        review_repo.config,
        **production_validation_kwargs(review_repo),
    )
    assert result["remote"]["head"] == review_repo.review_commit


def test_unpushed_current_head_fails_remote_reachability(
    tmp_path: Path,
) -> None:
    review_repo, _ = make_remote_review_repo(tmp_path)
    git(
        review_repo.root,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "unpushed metadata-only commit",
    )
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **production_validation_kwargs(review_repo),
        )
    assert raised.value.code == "remote_tip_mismatch"


def test_remote_descendant_is_not_treated_as_exact_reviewed_tip(
    tmp_path: Path,
) -> None:
    review_repo, _ = make_remote_review_repo(tmp_path)
    (review_repo.root / "runtime.json").write_text("{}\n", encoding="utf-8")
    commit(review_repo.root, "remote branch moves beyond reviewed head")
    git(review_repo.root, "push", "-q", "origin", "experiment")
    git(review_repo.root, "checkout", "-q", "--detach", review_repo.review_commit)

    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **production_validation_kwargs(review_repo),
        )
    assert raised.value.code == "remote_tip_mismatch"


def test_mutable_origin_url_cannot_redirect_production_proof(
    tmp_path: Path,
) -> None:
    review_repo, original = make_remote_review_repo(tmp_path)
    mirror = tmp_path / "mirror.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(original), str(mirror)],
        capture_output=True,
        check=True,
    )
    git(review_repo.root, "remote", "set-url", "origin", str(mirror))
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **production_validation_kwargs(review_repo),
        )
    assert raised.value.code == "remote_url_mismatch"


def test_insteadof_remote_url_rewrites_are_forbidden(tmp_path: Path) -> None:
    review_repo, original = make_remote_review_repo(tmp_path)
    mirror = tmp_path / "rewrite-mirror.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(original), str(mirror)],
        capture_output=True,
        check=True,
    )
    git(
        review_repo.root,
        "config",
        f"url.{mirror}.insteadOf",
        str(original),
    )
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **production_validation_kwargs(review_repo),
        )
    assert raised.value.code == "remote_url_rewrite_forbidden"


def test_production_api_has_no_remote_bypass_switch() -> None:
    parameters = inspect.signature(validate_review_gate).parameters
    assert "require_remote_reachability" not in parameters
    assert "git" not in parameters
    assert parameters["expected_remote_tip"].default is inspect.Parameter.empty
    assert (
        parameters["trusted_git_executable"].default
        is inspect.Parameter.empty
    )


def test_production_api_rejects_empty_mandatory_sentinel_set(
    review_repo: ReviewRepo,
) -> None:
    kwargs = production_validation_kwargs(review_repo)
    kwargs["mandatory_sentinel_paths"] = []
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **kwargs,
        )
    assert raised.value.code == "mandatory_sentinels_required"


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("expected_config_sha256", "trusted_config_hash_required"),
        ("expected_protected_paths", "trusted_protected_paths_required"),
        ("trusted_git_executable", "trusted_git_executable_invalid"),
    ],
)
def test_production_trust_anchors_cannot_be_none_at_runtime(
    review_repo: ReviewRepo,
    field: str,
    code: str,
) -> None:
    kwargs = production_validation_kwargs(review_repo)
    kwargs[field] = None
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **kwargs,
        )
    assert raised.value.code == code


def test_production_rejects_path_resolved_git(
    review_repo: ReviewRepo,
) -> None:
    kwargs = production_validation_kwargs(review_repo)
    kwargs["trusted_git_executable"] = "git"
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **kwargs,
        )
    assert raised.value.code == "trusted_git_executable_invalid"

    fake_git = review_repo.root / "fake-git.exe"
    fake_git.write_bytes(b"not a trusted executable\n")
    kwargs["trusted_git_executable"] = str(fake_git.resolve())
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **kwargs,
        )
    assert raised.value.code == "trusted_git_executable_invalid"


def test_default_git_process_discards_inherited_git_environment(
    review_repo: ReviewRepo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kwargs = local_validation_kwargs(review_repo)
    monkeypatch.setenv("GIT_DIR", str(review_repo.root / "bogus-git-dir"))
    result = _validate_review_gate_evidence_for_tests(
        review_repo.root,
        review_repo.config,
        **kwargs,
    )
    assert result["valid"] is True


def test_missing_remote_is_a_structured_hard_failure(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing-origin.git"
    review_repo = make_review_repo(
        tmp_path / "work",
        config_mutator=lambda config: config["remote"].update(
            url=str(missing)
        ),
    )
    git(review_repo.root, "remote", "add", "origin", str(missing))
    with pytest.raises(ReviewGateError) as raised:
        validate_review_gate(
            review_repo.root,
            review_repo.config,
            **production_validation_kwargs(review_repo),
        )
    assert raised.value.code == "remote_evidence_unavailable"


def configure_human_policy(config: dict[str, Any]) -> None:
    config["accepted_reviewer_kinds"] = [GITHUB_HUMAN]
    config["human_review_required"] = True
    config["required_claim_boundary"] = HUMAN_CLAIM_BOUNDARY


def configure_human_artifact(value: dict[str, Any]) -> None:
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


def test_human_claim_requires_injected_external_authentication(
    tmp_path: Path,
) -> None:
    review_repo = make_review_repo(
        tmp_path,
        config_mutator=configure_human_policy,
        artifact_mutator=configure_human_artifact,
    )
    assert_error(review_repo, "human_authentication_unverified")

    result = _validate_review_gate_evidence_for_tests(
        review_repo.root,
        review_repo.config,
        **local_validation_kwargs(review_repo),
        human_authenticator=lambda reviewer, artifact, frozen: {
            "valid": reviewer["id"] == "github:reviewer",
            "source": "test-github-api",
            "gate_id": frozen.gate_id,
        },
    )
    assert result["valid"] is True
    assert result["reviewer"]["human_review_performed"] is True
    assert result["reviewer"]["external_authentication"]["valid"] is True


def test_human_required_policy_rejects_ai_review(tmp_path: Path) -> None:
    review_repo = make_review_repo(
        tmp_path, config_mutator=configure_human_policy
    )
    assert_error(review_repo, "reviewer_kind_not_accepted")


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
    result = _validate_review_gate_evidence_for_tests(
        review_repo.root,
        review_repo.config,
        **local_validation_kwargs(review_repo),
        git=client,
    )
    assert result["valid"] is True
    assert calls
    assert all(call[0] == "--no-replace-objects" for call in calls)
    assert any(call[1:3] == ("rev-parse", "--verify") for call in calls)


def test_missing_git_process_becomes_a_structured_gate_failure(
    review_repo: ReviewRepo,
) -> None:
    def unavailable(
        args: tuple[str, ...], repo_root: Path
    ) -> subprocess.CompletedProcess[bytes]:
        raise FileNotFoundError("git executable unavailable")

    client = SubprocessGit(review_repo.root, executor=unavailable)
    assert_error(review_repo, "git_evidence_unavailable", git=client)


def test_git_process_timeout_becomes_a_structured_gate_failure(
    review_repo: ReviewRepo,
) -> None:
    def times_out(
        args: tuple[str, ...], repo_root: Path
    ) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(args, timeout=1, output=b"partial")

    client = SubprocessGit(review_repo.root, executor=times_out)
    assert_error(review_repo, "git_evidence_unavailable", git=client)
