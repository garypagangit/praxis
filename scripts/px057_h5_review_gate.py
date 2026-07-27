"""Fail-closed validation for the PX-057 H5 pre-data code-review gate.

The review artifact is evidence about an exact Git candidate, not authority by
itself.  This module reconstructs the reviewed bytes from Git, derives the
commit that introduced the artifact, and verifies that no reviewed byte has
changed.  It deliberately has no dependency on the H4 implementation so it can
be invoked by the H5 freezer, submitters, cloud entry points, and adjudicator.

The validator proves repository facts (bytes, hashes, ancestry, and optional
remote reachability).  Statements about an AI reviewer's context isolation are
still operator assertions; the schema makes that limitation explicit and
prevents an AI review from being represented as human review.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Protocol, Sequence


REVIEW_GATE_CONFIG_SCHEMA_VERSION = "px057-h5-review-gate-config/v1"
REVIEW_ARTIFACT_SCHEMA_VERSION = "px057-h5-predata-code-review/v1"

AI_SUBAGENT = "ai_subagent"
GITHUB_HUMAN = "github_human"
REVIEWER_KINDS = frozenset({AI_SUBAGENT, GITHUB_HUMAN})

AI_INDEPENDENCE_SCOPE = "separate_task_context_read_only_review"
AI_CLAIM_BOUNDARY = (
    "Separately tasked AI-agent code review; not human, external, or "
    "institutional peer review."
)
REQUIRED_AI_LIMITATIONS = (
    "not_external_peer_review",
    "not_human_review",
    "process_separation_not_cognitive_independence",
)
REQUIRED_AI_OPERATOR_ASSERTIONS = (
    "read_only_assignment",
    "separate_task_context",
)

_OBJECT_ID_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_CONFIG_KEYS = frozenset(
    {
        "schema_version",
        "experiment_id",
        "gate_id",
        "review_artifact_path",
        "review_required_paths",
        "artifact_commit_allowed_paths",
        "accepted_reviewer_kinds",
        "human_review_required",
        "implementation_author_ids",
        "required_independence_scope",
        "required_ai_limitations",
        "required_checks",
        "required_claim_boundary",
        "require_artifact_absent_at_candidate",
        "remote",
    }
)
_REMOTE_KEYS = frozenset({"name", "branch"})
_ARTIFACT_KEYS = frozenset(
    {
        "schema_version",
        "experiment_id",
        "gate_id",
        "disposition",
        "reviewed_candidate",
        "reviewer",
        "independence",
        "required_checks",
        "findings",
        "blocking_findings_open",
        "human_review_performed",
        "claim_boundary",
    }
)
_CANDIDATE_KEYS = frozenset(
    {
        "commit",
        "tree_oid",
        "required_path_set_sha256",
        "reviewed_files_sha256",
        "files",
    }
)
_FILE_KEYS = frozenset({"path", "git_blob_oid", "sha256"})
_REVIEWER_KEYS = frozenset(
    {
        "kind",
        "id",
        "human",
        "external_identity_authenticated",
        "model_id",
        "authentication_evidence",
    }
)
_INDEPENDENCE_KEYS = frozenset(
    {
        "scope",
        "implementation_edits_made",
        "scientific_outputs_seen",
        "machine_verified",
        "operator_asserted",
        "limitations",
    }
)
_FINDING_KEYS = frozenset({"id", "severity", "status", "summary"})
_FINDING_SEVERITIES = frozenset({"critical", "blocking", "major", "minor", "note"})
_FINDING_STATUSES = frozenset({"open", "resolved"})
_BLOCKING_SEVERITIES = frozenset({"critical", "blocking"})


class ReviewGateError(ValueError):
    """A review-gate failure with a stable code and serializable details."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = dict(details or {})
        super().__init__(f"{code}: {message}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


class GitOperationError(RuntimeError):
    """Internal wrapper for a failed Git subprocess."""

    def __init__(
        self,
        args: Sequence[str],
        returncode: int,
        stdout: bytes,
        stderr: bytes,
    ) -> None:
        self.args_tuple = tuple(args)
        self.returncode = returncode
        self.stdout_bytes = stdout
        self.stderr_bytes = stderr
        message = stderr.decode("utf-8", errors="replace").strip()
        super().__init__(
            f"git {' '.join(args)} failed with {returncode}"
            + (f": {message}" if message else "")
        )


class GitClient(Protocol):
    """The Git facts required by :func:`validate_review_gate`."""

    def resolve_commit(self, revision: str) -> str: ...

    def tree_oid(self, commit: str) -> str: ...

    def show_file(self, commit: str, path: str) -> bytes: ...

    def file_exists_at(self, commit: str, path: str) -> bool: ...

    def blob_oid(self, commit: str, path: str) -> str: ...

    def last_change_commit(self, head: str, path: str) -> str: ...

    def is_ancestor(self, ancestor: str, descendant: str) -> bool: ...

    def changed_paths(self, base: str, head: str) -> tuple[str, ...]: ...

    def is_tracked(self, path: str) -> bool: ...

    def status_for_path(self, path: str) -> bytes: ...

    def remote_head(self, remote: str, branch: str) -> str: ...


GitExecutor = Callable[[Sequence[str], Path], subprocess.CompletedProcess[bytes]]
HumanAuthenticator = Callable[
    [Mapping[str, Any], Mapping[str, Any], "ReviewGateConfig"],
    Mapping[str, Any],
]


def _default_git_executor(
    args: Sequence[str], repo_root: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )


class SubprocessGit:
    """Git client whose process executor can be replaced in tests or callers."""

    def __init__(
        self,
        repo_root: Path,
        *,
        executor: GitExecutor | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._executor = executor or _default_git_executor

    def _run(
        self, args: Sequence[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            result = self._executor(tuple(args), self.repo_root)
        except OSError as exc:
            raise GitOperationError(
                args,
                127,
                b"",
                str(exc).encode("utf-8", errors="replace"),
            ) from exc
        if check and result.returncode != 0:
            raise GitOperationError(args, result.returncode, result.stdout, result.stderr)
        return result

    def resolve_commit(self, revision: str) -> str:
        return (
            self._run(["rev-parse", "--verify", f"{revision}^{{commit}}"])
            .stdout.decode("ascii")
            .strip()
        )

    def tree_oid(self, commit: str) -> str:
        return (
            self._run(["rev-parse", "--verify", f"{commit}^{{tree}}"])
            .stdout.decode("ascii")
            .strip()
        )

    def show_file(self, commit: str, path: str) -> bytes:
        return self._run(["show", f"{commit}:{path}"]).stdout

    def file_exists_at(self, commit: str, path: str) -> bool:
        return self._run(["cat-file", "-e", f"{commit}:{path}"], check=False).returncode == 0

    def blob_oid(self, commit: str, path: str) -> str:
        return (
            self._run(["rev-parse", "--verify", f"{commit}:{path}"])
            .stdout.decode("ascii")
            .strip()
        )

    def last_change_commit(self, head: str, path: str) -> str:
        value = (
            self._run(["log", "-1", "--format=%H", head, "--", path])
            .stdout.decode("ascii")
            .strip()
        )
        if not value:
            raise GitOperationError(
                ["log", "-1", "--format=%H", head, "--", path],
                1,
                b"",
                b"no commit contains the path",
            )
        return value

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        result = self._run(
            ["merge-base", "--is-ancestor", ancestor, descendant], check=False
        )
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        raise GitOperationError(
            ["merge-base", "--is-ancestor", ancestor, descendant],
            result.returncode,
            result.stdout,
            result.stderr,
        )

    def changed_paths(self, base: str, head: str) -> tuple[str, ...]:
        content = self._run(
            ["diff", "--name-only", "--diff-filter=ACDMRTUXB", "-z", base, head, "--"]
        ).stdout
        return tuple(
            part.decode("utf-8") for part in content.split(b"\0") if part
        )

    def is_tracked(self, path: str) -> bool:
        return (
            self._run(["ls-files", "--error-unmatch", "--", path], check=False).returncode
            == 0
        )

    def status_for_path(self, path: str) -> bytes:
        return self._run(
            ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", path]
        ).stdout

    def remote_head(self, remote: str, branch: str) -> str:
        result = self._run(
            ["ls-remote", "--exit-code", "--heads", remote, f"refs/heads/{branch}"]
        )
        rows = [row for row in result.stdout.decode("ascii").splitlines() if row.strip()]
        if len(rows) != 1:
            raise GitOperationError(
                ["ls-remote", "--heads", remote, f"refs/heads/{branch}"],
                1,
                result.stdout,
                b"expected exactly one remote branch",
            )
        return rows[0].split()[0]


@dataclass(frozen=True)
class ReviewGateConfig:
    experiment_id: str
    gate_id: str
    review_artifact_path: str
    review_required_paths: tuple[str, ...]
    artifact_commit_allowed_paths: tuple[str, ...]
    accepted_reviewer_kinds: tuple[str, ...]
    human_review_required: bool
    implementation_author_ids: tuple[str, ...]
    required_independence_scope: str
    required_ai_limitations: tuple[str, ...]
    required_checks: tuple[str, ...]
    required_claim_boundary: str
    require_artifact_absent_at_candidate: bool
    remote_name: str
    remote_branch: str


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def required_path_set_sha256(paths: Sequence[str]) -> str:
    """Hash the sorted path inventory independently of file contents."""

    return sha256_bytes(canonical_json_bytes(sorted(paths)))


def reviewed_files_sha256(files: Sequence[Mapping[str, str]]) -> str:
    """Hash the deterministic candidate file manifest."""

    normalized = [
        {
            "path": str(item["path"]),
            "git_blob_oid": str(item["git_blob_oid"]),
            "sha256": str(item["sha256"]),
        }
        for item in files
    ]
    normalized.sort(key=lambda item: item["path"])
    return sha256_bytes(canonical_json_bytes(normalized))


def _raise(code: str, message: str, **details: Any) -> None:
    raise ReviewGateError(code, message, details=details)


def _expect_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], location: str
) -> None:
    observed = set(value)
    if observed != expected:
        _raise(
            "schema_error",
            f"{location} has missing or unexpected fields",
            location=location,
            missing=sorted(expected - observed),
            unexpected=sorted(observed - expected),
        )


def _expect_mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _raise(
            "schema_error",
            f"{location} must be an object",
            location=location,
            observed_type=type(value).__name__,
        )
    return value


def _expect_bool(value: Any, location: str) -> bool:
    if type(value) is not bool:
        _raise(
            "schema_error",
            f"{location} must be a boolean",
            location=location,
            observed_type=type(value).__name__,
        )
    return value


def _expect_nonnegative_int(value: Any, location: str) -> int:
    if type(value) is not int or value < 0:
        _raise(
            "schema_error",
            f"{location} must be a non-negative integer",
            location=location,
            observed=value,
        )
    return value


def _expect_nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _raise(
            "schema_error",
            f"{location} must be a non-empty string",
            location=location,
            observed=value,
        )
    return value


def _expect_optional_string(value: Any, location: str) -> str | None:
    if value is None:
        return None
    return _expect_nonempty_string(value, location)


def _expect_string_list(
    value: Any,
    location: str,
    *,
    nonempty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        _raise(
            "schema_error",
            f"{location} must be an array",
            location=location,
            observed_type=type(value).__name__,
        )
    result = tuple(
        _expect_nonempty_string(item, f"{location}[{index}]")
        for index, item in enumerate(value)
    )
    if nonempty and not result:
        _raise("schema_error", f"{location} must not be empty", location=location)
    if len(set(result)) != len(result):
        _raise(
            "schema_error",
            f"{location} contains duplicates",
            location=location,
        )
    return result


def _normalize_repo_path(value: Any, location: str) -> str:
    raw = _expect_nonempty_string(value, location)
    if "\\" in raw or ":" in raw or "\x00" in raw:
        _raise(
            "unsafe_path",
            f"{location} must be an unambiguous repository-relative POSIX path",
            location=location,
            path=raw,
        )
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or raw.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _raise(
            "unsafe_path",
            f"{location} is not a safe repository-relative path",
            location=location,
            path=raw,
        )
    normalized = path.as_posix()
    if normalized != raw:
        _raise(
            "unsafe_path",
            f"{location} is not canonically normalized",
            location=location,
            path=raw,
            normalized=normalized,
        )
    return normalized


def _normalize_path_list(value: Any, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        _raise(
            "schema_error",
            f"{location} must be a non-empty array",
            location=location,
        )
    paths = tuple(
        _normalize_repo_path(item, f"{location}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(paths)) != len(paths):
        _raise("path_inventory_invalid", f"{location} contains duplicate paths")
    folded = [path.casefold() for path in paths]
    if len(set(folded)) != len(folded):
        _raise(
            "path_inventory_invalid",
            f"{location} contains case-colliding paths",
        )
    return paths


def _parse_config(value: Mapping[str, Any]) -> ReviewGateConfig:
    config = _expect_mapping(value, "review_config")
    _expect_exact_keys(config, _CONFIG_KEYS, "review_config")
    if config["schema_version"] != REVIEW_GATE_CONFIG_SCHEMA_VERSION:
        _raise(
            "unsupported_config_schema",
            "review-gate config schema version is not supported",
            observed=config["schema_version"],
            expected=REVIEW_GATE_CONFIG_SCHEMA_VERSION,
        )
    experiment_id = _expect_nonempty_string(config["experiment_id"], "review_config.experiment_id")
    gate_id = _expect_nonempty_string(config["gate_id"], "review_config.gate_id")
    artifact_path = _normalize_repo_path(
        config["review_artifact_path"], "review_config.review_artifact_path"
    )
    required_paths = _normalize_path_list(
        config["review_required_paths"], "review_config.review_required_paths"
    )
    allowed_paths = _normalize_path_list(
        config["artifact_commit_allowed_paths"],
        "review_config.artifact_commit_allowed_paths",
    )
    if artifact_path in required_paths:
        _raise(
            "path_inventory_invalid",
            "the review artifact cannot review/hash itself",
            path=artifact_path,
        )
    if artifact_path not in allowed_paths:
        _raise(
            "path_inventory_invalid",
            "the artifact path must be allowed in the review-record commit",
            path=artifact_path,
        )
    accepted_kinds = _expect_string_list(
        config["accepted_reviewer_kinds"],
        "review_config.accepted_reviewer_kinds",
        nonempty=True,
    )
    unknown_kinds = set(accepted_kinds) - REVIEWER_KINDS
    if unknown_kinds:
        _raise(
            "schema_error",
            "review config contains unsupported reviewer kinds",
            unsupported=sorted(unknown_kinds),
        )
    if len(accepted_kinds) != 1:
        _raise(
            "review_policy_invalid",
            "exactly one reviewer kind must be frozen before data",
            observed=list(accepted_kinds),
        )
    human_required = _expect_bool(
        config["human_review_required"], "review_config.human_review_required"
    )
    if human_required != (accepted_kinds[0] == GITHUB_HUMAN):
        _raise(
            "review_policy_invalid",
            "human_review_required must exactly match the frozen reviewer kind",
        )
    author_ids = _expect_string_list(
        config["implementation_author_ids"],
        "review_config.implementation_author_ids",
        nonempty=True,
    )
    scope = _expect_nonempty_string(
        config["required_independence_scope"],
        "review_config.required_independence_scope",
    )
    ai_limitations = _expect_string_list(
        config["required_ai_limitations"],
        "review_config.required_ai_limitations",
        nonempty=True,
    )
    if AI_SUBAGENT in accepted_kinds:
        if scope != AI_INDEPENDENCE_SCOPE:
            _raise(
                "review_policy_invalid",
                "AI review must use the non-human task-separation scope",
                observed=scope,
                required=AI_INDEPENDENCE_SCOPE,
            )
        missing_policy_limitations = set(REQUIRED_AI_LIMITATIONS) - set(
            ai_limitations
        )
        if missing_policy_limitations:
            _raise(
                "review_policy_invalid",
                "AI review policy omits mandatory honesty limitations",
                missing=sorted(missing_policy_limitations),
            )
    required_checks = _expect_string_list(
        config["required_checks"], "review_config.required_checks", nonempty=True
    )
    claim_boundary = _expect_nonempty_string(
        config["required_claim_boundary"], "review_config.required_claim_boundary"
    )
    if AI_SUBAGENT in accepted_kinds and claim_boundary != AI_CLAIM_BOUNDARY:
        _raise(
            "review_policy_invalid",
            "AI review policy must use the mandatory non-human claim boundary",
            required=AI_CLAIM_BOUNDARY,
        )
    require_absent = _expect_bool(
        config["require_artifact_absent_at_candidate"],
        "review_config.require_artifact_absent_at_candidate",
    )
    remote = _expect_mapping(config["remote"], "review_config.remote")
    _expect_exact_keys(remote, _REMOTE_KEYS, "review_config.remote")
    remote_name = _expect_nonempty_string(remote["name"], "review_config.remote.name")
    remote_branch = _expect_nonempty_string(
        remote["branch"], "review_config.remote.branch"
    )
    return ReviewGateConfig(
        experiment_id=experiment_id,
        gate_id=gate_id,
        review_artifact_path=artifact_path,
        review_required_paths=required_paths,
        artifact_commit_allowed_paths=allowed_paths,
        accepted_reviewer_kinds=accepted_kinds,
        human_review_required=human_required,
        implementation_author_ids=author_ids,
        required_independence_scope=scope,
        required_ai_limitations=ai_limitations,
        required_checks=required_checks,
        required_claim_boundary=claim_boundary,
        require_artifact_absent_at_candidate=require_absent,
        remote_name=remote_name,
        remote_branch=remote_branch,
    )


def _json_no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _raise("duplicate_json_key", "review artifact contains a duplicate JSON key", key=key)
        result[key] = value
    return result


def _parse_artifact_bytes(content: bytes) -> Mapping[str, Any]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        _raise("artifact_encoding_invalid", "review artifact is not valid UTF-8", reason=str(exc))
    try:
        value = json.loads(text, object_pairs_hook=_json_no_duplicate_keys)
    except ReviewGateError:
        raise
    except json.JSONDecodeError as exc:
        _raise(
            "artifact_json_invalid",
            "review artifact is not valid JSON",
            line=exc.lineno,
            column=exc.colno,
            reason=exc.msg,
        )
    return _expect_mapping(value, "review_artifact")


def _validate_object_id(value: Any, location: str) -> str:
    observed = _expect_nonempty_string(value, location)
    if _OBJECT_ID_RE.fullmatch(observed) is None:
        _raise(
            "object_id_invalid",
            f"{location} must be a full lowercase Git object ID",
            location=location,
            observed=observed,
        )
    return observed


def _validate_string_evidence_list(value: Any, location: str) -> tuple[str, ...]:
    return _expect_string_list(value, location, nonempty=False)


def _validate_reviewer_and_claims(
    artifact: Mapping[str, Any], config: ReviewGateConfig
) -> tuple[str, str, bool]:
    reviewer = _expect_mapping(artifact["reviewer"], "review_artifact.reviewer")
    _expect_exact_keys(reviewer, _REVIEWER_KEYS, "review_artifact.reviewer")
    kind = _expect_nonempty_string(reviewer["kind"], "review_artifact.reviewer.kind")
    if kind not in REVIEWER_KINDS or kind not in config.accepted_reviewer_kinds:
        _raise(
            "reviewer_kind_not_accepted",
            "reviewer kind is not accepted by the frozen review policy",
            observed=kind,
            accepted=list(config.accepted_reviewer_kinds),
        )
    reviewer_id = _expect_nonempty_string(reviewer["id"], "review_artifact.reviewer.id")
    if reviewer_id in config.implementation_author_ids:
        _raise(
            "reviewer_not_independent",
            "reviewer identity is listed as an implementation author",
            reviewer_id=reviewer_id,
        )
    human = _expect_bool(reviewer["human"], "review_artifact.reviewer.human")
    external_authenticated = _expect_bool(
        reviewer["external_identity_authenticated"],
        "review_artifact.reviewer.external_identity_authenticated",
    )
    model_id = _expect_optional_string(reviewer["model_id"], "review_artifact.reviewer.model_id")
    authentication_evidence = _expect_optional_string(
        reviewer["authentication_evidence"],
        "review_artifact.reviewer.authentication_evidence",
    )
    human_review_performed = _expect_bool(
        artifact["human_review_performed"],
        "review_artifact.human_review_performed",
    )

    independence = _expect_mapping(
        artifact["independence"], "review_artifact.independence"
    )
    _expect_exact_keys(
        independence, _INDEPENDENCE_KEYS, "review_artifact.independence"
    )
    scope = _expect_nonempty_string(
        independence["scope"], "review_artifact.independence.scope"
    )
    if scope != config.required_independence_scope:
        _raise(
            "independence_scope_mismatch",
            "review independence scope differs from the frozen policy",
            observed=scope,
            expected=config.required_independence_scope,
        )
    if _expect_bool(
        independence["implementation_edits_made"],
        "review_artifact.independence.implementation_edits_made",
    ):
        _raise(
            "reviewer_not_independent",
            "reviewer reports making implementation edits",
        )
    if _expect_bool(
        independence["scientific_outputs_seen"],
        "review_artifact.independence.scientific_outputs_seen",
    ):
        _raise(
            "review_not_predata",
            "reviewer reports seeing scientific outputs",
        )
    _validate_string_evidence_list(
        independence["machine_verified"],
        "review_artifact.independence.machine_verified",
    )
    operator_asserted = _validate_string_evidence_list(
        independence["operator_asserted"],
        "review_artifact.independence.operator_asserted",
    )
    limitations = _validate_string_evidence_list(
        independence["limitations"], "review_artifact.independence.limitations"
    )

    claim_boundary = _expect_nonempty_string(
        artifact["claim_boundary"], "review_artifact.claim_boundary"
    )
    if claim_boundary != config.required_claim_boundary:
        _raise(
            "claim_boundary_mismatch",
            "review claim boundary differs from the frozen policy",
        )

    if kind == AI_SUBAGENT:
        missing_limitations = set(config.required_ai_limitations) - set(limitations)
        if missing_limitations:
            _raise(
                "ai_review_limitations_missing",
                "AI review omits mandatory non-human claim limitations",
                missing=sorted(missing_limitations),
            )
        missing_assertions = set(REQUIRED_AI_OPERATOR_ASSERTIONS) - set(
            operator_asserted
        )
        if missing_assertions:
            _raise(
                "ai_review_assertions_missing",
                "AI review omits mandatory task-separation assertions",
                missing=sorted(missing_assertions),
            )
        if human or human_review_performed:
            _raise(
                "reviewer_honesty_failure",
                "AI subagent review cannot be represented as human review",
            )
        if external_authenticated or authentication_evidence is not None:
            _raise(
                "reviewer_honesty_failure",
                "AI subagent review cannot claim an externally authenticated human identity",
            )
        if model_id is None:
            _raise(
                "reviewer_honesty_failure",
                "AI subagent review must record its actual model identifier",
            )
    else:
        if not human or not human_review_performed:
            _raise(
                "reviewer_honesty_failure",
                "github_human review must be explicitly recorded as human",
            )
        if not external_authenticated or authentication_evidence is None:
            _raise(
                "reviewer_honesty_failure",
                "github_human review requires external authentication evidence",
            )
        if model_id is not None:
            _raise(
                "reviewer_honesty_failure",
                "github_human reviewer must not carry an AI model identifier",
            )
    if config.human_review_required and kind != GITHUB_HUMAN:
        _raise(
            "human_review_required",
            "the frozen policy requires a human review",
        )
    return kind, reviewer_id, human


def _validate_checks_and_findings(
    artifact: Mapping[str, Any], config: ReviewGateConfig
) -> tuple[tuple[str, ...], int]:
    checks = _expect_mapping(
        artifact["required_checks"], "review_artifact.required_checks"
    )
    expected = set(config.required_checks)
    observed = set(checks)
    if observed != expected:
        _raise(
            "required_checks_mismatch",
            "review artifact does not contain the exact frozen check set",
            missing=sorted(expected - observed),
            unexpected=sorted(observed - expected),
        )
    failed = sorted(key for key, value in checks.items() if value != "PASS")
    if failed:
        _raise(
            "required_check_not_pass",
            "one or more mandatory review checks did not PASS",
            failed=failed,
        )

    findings_value = artifact["findings"]
    if not isinstance(findings_value, list):
        _raise(
            "schema_error",
            "review_artifact.findings must be an array",
        )
    finding_ids: list[str] = []
    computed_open_blockers = 0
    for index, raw_finding in enumerate(findings_value):
        finding = _expect_mapping(raw_finding, f"review_artifact.findings[{index}]")
        _expect_exact_keys(
            finding, _FINDING_KEYS, f"review_artifact.findings[{index}]"
        )
        finding_id = _expect_nonempty_string(
            finding["id"], f"review_artifact.findings[{index}].id"
        )
        severity = _expect_nonempty_string(
            finding["severity"], f"review_artifact.findings[{index}].severity"
        )
        status = _expect_nonempty_string(
            finding["status"], f"review_artifact.findings[{index}].status"
        )
        _expect_nonempty_string(
            finding["summary"], f"review_artifact.findings[{index}].summary"
        )
        if severity not in _FINDING_SEVERITIES or status not in _FINDING_STATUSES:
            _raise(
                "schema_error",
                "finding severity or status is unsupported",
                finding_id=finding_id,
                severity=severity,
                status=status,
            )
        finding_ids.append(finding_id)
        if severity in _BLOCKING_SEVERITIES and status != "resolved":
            computed_open_blockers += 1
    if len(set(finding_ids)) != len(finding_ids):
        _raise("schema_error", "review artifact contains duplicate finding IDs")
    declared_open = _expect_nonnegative_int(
        artifact["blocking_findings_open"],
        "review_artifact.blocking_findings_open",
    )
    if declared_open != computed_open_blockers:
        _raise(
            "blocking_count_mismatch",
            "declared open-blocker count differs from findings",
            declared=declared_open,
            computed=computed_open_blockers,
        )
    if computed_open_blockers:
        _raise(
            "open_blocking_findings",
            "review has unresolved blocking findings",
            count=computed_open_blockers,
        )
    return tuple(sorted(checks)), len(findings_value)


def _candidate_file_records(
    git: GitClient, candidate: str, paths: Sequence[str]
) -> tuple[dict[str, str], ...]:
    records: list[dict[str, str]] = []
    for path in sorted(paths):
        try:
            content = git.show_file(candidate, path)
            blob_oid = git.blob_oid(candidate, path)
        except GitOperationError as exc:
            _raise(
                "candidate_file_missing",
                "a required reviewed path is absent from the candidate commit",
                path=path,
                reason=str(exc),
            )
        records.append(
            {
                "path": path,
                "git_blob_oid": blob_oid,
                "sha256": sha256_bytes(content),
            }
        )
    return tuple(records)


def _validate_artifact_file_records(
    candidate_payload: Mapping[str, Any], expected_records: Sequence[Mapping[str, str]]
) -> None:
    raw_files = candidate_payload["files"]
    if not isinstance(raw_files, list):
        _raise("schema_error", "reviewed_candidate.files must be an array")
    observed_records: list[dict[str, str]] = []
    for index, raw in enumerate(raw_files):
        item = _expect_mapping(raw, f"reviewed_candidate.files[{index}]")
        _expect_exact_keys(item, _FILE_KEYS, f"reviewed_candidate.files[{index}]")
        observed_records.append(
            {
                "path": _normalize_repo_path(
                    item["path"], f"reviewed_candidate.files[{index}].path"
                ),
                "git_blob_oid": _validate_object_id(
                    item["git_blob_oid"],
                    f"reviewed_candidate.files[{index}].git_blob_oid",
                ),
                "sha256": _validate_sha256(
                    item["sha256"], f"reviewed_candidate.files[{index}].sha256"
                ),
            }
        )
    expected = [dict(item) for item in expected_records]
    if observed_records != expected:
        _raise(
            "candidate_file_manifest_mismatch",
            "artifact file records differ from candidate Git bytes",
            observed=observed_records,
            expected=expected,
        )


def _validate_sha256(value: Any, location: str) -> str:
    observed = _expect_nonempty_string(value, location)
    if re.fullmatch(r"[0-9a-f]{64}", observed) is None:
        _raise(
            "schema_error",
            f"{location} must be a lowercase SHA-256",
            location=location,
            observed=observed,
        )
    return observed


def _local_artifact_path(repo_root: Path, relative: str) -> Path:
    root = repo_root.resolve()
    unresolved = root / Path(relative)
    if unresolved.is_symlink():
        _raise(
            "unsafe_path",
            "review artifact may not be a symbolic link",
            path=relative,
        )
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        _raise(
            "unsafe_path",
            "review artifact resolves outside the repository",
            path=relative,
        )
    return candidate


def validate_review_gate(
    repo_root: Path,
    review_config: Mapping[str, Any],
    *,
    artifact_path: Path | str | None = None,
    head_revision: str = "HEAD",
    require_remote_reachability: bool = False,
    git: GitClient | None = None,
    human_authenticator: HumanAuthenticator | None = None,
) -> dict[str, Any]:
    """Validate the H5 pre-data review artifact and its Git provenance.

    ``require_remote_reachability`` performs a live ``git ls-remote`` through
    :class:`SubprocessGit` and requires the candidate, review-record commit, and
    current head to be ancestors of that remote head.  Callers should treat any
    :class:`ReviewGateError` as a hard NO-GO.
    """

    root = Path(repo_root).resolve()
    config = _parse_config(review_config)
    git_client: GitClient = git or SubprocessGit(root)
    configured_artifact = config.review_artifact_path
    if artifact_path is not None:
        supplied = Path(artifact_path)
        if supplied.is_absolute():
            try:
                supplied_relative = supplied.resolve().relative_to(root).as_posix()
            except ValueError:
                _raise(
                    "artifact_path_mismatch",
                    "supplied review artifact is outside the repository",
                    supplied=str(supplied),
                )
        else:
            supplied_relative = _normalize_repo_path(
                supplied.as_posix(), "artifact_path"
            )
        if supplied_relative != configured_artifact:
            _raise(
                "artifact_path_mismatch",
                "supplied review artifact differs from the frozen path",
                supplied=supplied_relative,
                configured=configured_artifact,
            )
    local_artifact = _local_artifact_path(root, configured_artifact)
    if not local_artifact.is_file():
        _raise(
            "review_artifact_missing",
            "review artifact does not exist as a regular file",
            path=configured_artifact,
        )

    try:
        head = git_client.resolve_commit(head_revision)
        if not git_client.is_tracked(configured_artifact):
            _raise(
                "review_artifact_uncommitted",
                "review artifact is not tracked by Git",
                path=configured_artifact,
            )
        dirty_status = git_client.status_for_path(configured_artifact)
        if dirty_status:
            _raise(
                "review_artifact_dirty",
                "review artifact has staged or worktree changes",
                path=configured_artifact,
                porcelain=dirty_status.decode("utf-8", errors="replace"),
            )
        artifact_bytes = git_client.show_file(head, configured_artifact)
        artifact_blob_oid = git_client.blob_oid(head, configured_artifact)
    except ReviewGateError:
        raise
    except GitOperationError as exc:
        _raise(
            "git_evidence_unavailable",
            "unable to read committed review artifact evidence",
            reason=str(exc),
        )

    artifact = _parse_artifact_bytes(artifact_bytes)
    _expect_exact_keys(artifact, _ARTIFACT_KEYS, "review_artifact")
    if artifact["schema_version"] != REVIEW_ARTIFACT_SCHEMA_VERSION:
        _raise(
            "unsupported_artifact_schema",
            "review artifact schema version is not supported",
            observed=artifact["schema_version"],
            expected=REVIEW_ARTIFACT_SCHEMA_VERSION,
        )
    if artifact["experiment_id"] != config.experiment_id or artifact["gate_id"] != config.gate_id:
        _raise(
            "review_identity_mismatch",
            "review artifact experiment/gate identity differs from the frozen config",
            artifact_experiment=artifact["experiment_id"],
            artifact_gate=artifact["gate_id"],
            expected_experiment=config.experiment_id,
            expected_gate=config.gate_id,
        )
    if artifact["disposition"] != "PASS":
        _raise(
            "review_disposition_not_pass",
            "review artifact disposition must be exactly PASS",
            observed=artifact["disposition"],
        )

    reviewer_kind, reviewer_id, human_review = _validate_reviewer_and_claims(
        artifact, config
    )
    human_authentication: dict[str, Any] | None = None
    if reviewer_kind == GITHUB_HUMAN:
        if human_authenticator is None:
            _raise(
                "human_authentication_unverified",
                "human review requires an injected external evidence verifier",
            )
        try:
            authentication_result = human_authenticator(
                _expect_mapping(artifact["reviewer"], "review_artifact.reviewer"),
                artifact,
                config,
            )
        except ReviewGateError:
            raise
        except Exception as exc:
            _raise(
                "human_authentication_unverified",
                "external human-review evidence verification failed",
                reason=str(exc),
            )
        if not isinstance(authentication_result, Mapping) or authentication_result.get(
            "valid"
        ) is not True:
            _raise(
                "human_authentication_unverified",
                "external human-review evidence was not positively verified",
            )
        human_authentication = dict(authentication_result)
    passed_checks, finding_count = _validate_checks_and_findings(artifact, config)

    candidate_payload = _expect_mapping(
        artifact["reviewed_candidate"], "review_artifact.reviewed_candidate"
    )
    _expect_exact_keys(
        candidate_payload, _CANDIDATE_KEYS, "review_artifact.reviewed_candidate"
    )
    candidate = _validate_object_id(
        candidate_payload["commit"], "review_artifact.reviewed_candidate.commit"
    )
    expected_tree = _validate_object_id(
        candidate_payload["tree_oid"], "review_artifact.reviewed_candidate.tree_oid"
    )
    declared_path_digest = _validate_sha256(
        candidate_payload["required_path_set_sha256"],
        "review_artifact.reviewed_candidate.required_path_set_sha256",
    )
    declared_files_digest = _validate_sha256(
        candidate_payload["reviewed_files_sha256"],
        "review_artifact.reviewed_candidate.reviewed_files_sha256",
    )

    try:
        resolved_candidate = git_client.resolve_commit(candidate)
        if resolved_candidate != candidate:
            _raise(
                "candidate_commit_mismatch",
                "candidate commit did not resolve to the exact recorded object",
                recorded=candidate,
                resolved=resolved_candidate,
            )
        observed_tree = git_client.tree_oid(candidate)
        if observed_tree != expected_tree:
            _raise(
                "candidate_tree_mismatch",
                "candidate tree differs from the review artifact",
                observed=observed_tree,
                expected=expected_tree,
            )
        if config.require_artifact_absent_at_candidate and git_client.file_exists_at(
            candidate, configured_artifact
        ):
            _raise(
                "stale_review_artifact",
                "final review artifact already existed in the reviewed candidate",
                candidate=candidate,
                path=configured_artifact,
            )
        review_record_commit = git_client.last_change_commit(
            head, configured_artifact
        )
        review_record_commit = git_client.resolve_commit(review_record_commit)
        if review_record_commit == candidate or not git_client.is_ancestor(
            candidate, review_record_commit
        ):
            _raise(
                "review_commit_order_invalid",
                "review-record commit is not a strict descendant of the candidate",
                candidate=candidate,
                review_record_commit=review_record_commit,
            )
        if not git_client.is_ancestor(review_record_commit, head):
            _raise(
                "review_commit_order_invalid",
                "review-record commit is not an ancestor of the validated head",
                review_record_commit=review_record_commit,
                head=head,
            )
        review_commit_paths = tuple(
            sorted(git_client.changed_paths(candidate, review_record_commit))
        )
    except ReviewGateError:
        raise
    except GitOperationError as exc:
        _raise(
            "git_evidence_unavailable",
            "unable to verify candidate/review commit provenance",
            reason=str(exc),
        )

    allowed_review_paths = set(config.artifact_commit_allowed_paths)
    unexpected_review_paths = set(review_commit_paths) - allowed_review_paths
    if configured_artifact not in review_commit_paths or unexpected_review_paths:
        _raise(
            "artifact_commit_scope_invalid",
            "candidate-to-review commit diff is not limited to review artifacts",
            changed=list(review_commit_paths),
            allowed=sorted(allowed_review_paths),
            unexpected=sorted(unexpected_review_paths),
        )

    observed_path_digest = required_path_set_sha256(config.review_required_paths)
    if declared_path_digest != observed_path_digest:
        _raise(
            "required_path_set_mismatch",
            "review artifact required-path digest differs from the frozen inventory",
            observed=declared_path_digest,
            expected=observed_path_digest,
        )
    candidate_records = _candidate_file_records(
        git_client, candidate, config.review_required_paths
    )
    _validate_artifact_file_records(candidate_payload, candidate_records)
    observed_files_digest = reviewed_files_sha256(candidate_records)
    if declared_files_digest != observed_files_digest:
        _raise(
            "reviewed_files_digest_mismatch",
            "reviewed-file manifest digest differs from reconstructed candidate bytes",
            observed=declared_files_digest,
            expected=observed_files_digest,
        )

    changed_reviewed_paths: list[dict[str, str | None]] = []
    reviewed_path_history_changes: list[dict[str, str]] = []
    for record in candidate_records:
        path = record["path"]
        try:
            if not git_client.is_tracked(path):
                changed_reviewed_paths.append(
                    {
                        "path": path,
                        "candidate_sha256": record["sha256"],
                        "current_sha256": None,
                    }
                )
                continue
            dirty = git_client.status_for_path(path)
            if dirty:
                _raise(
                    "reviewed_file_dirty",
                    "a reviewed path has staged or worktree changes",
                    path=path,
                    porcelain=dirty.decode("utf-8", errors="replace"),
                )
            current_bytes = git_client.show_file(head, path)
            current_blob = git_client.blob_oid(head, path)
            candidate_last_change = git_client.last_change_commit(candidate, path)
            current_last_change = git_client.last_change_commit(head, path)
        except ReviewGateError:
            raise
        except GitOperationError:
            changed_reviewed_paths.append(
                {
                    "path": path,
                    "candidate_sha256": record["sha256"],
                    "current_sha256": None,
                }
            )
            continue
        current_sha = sha256_bytes(current_bytes)
        if current_blob != record["git_blob_oid"] or current_sha != record["sha256"]:
            changed_reviewed_paths.append(
                {
                    "path": path,
                    "candidate_sha256": record["sha256"],
                    "current_sha256": current_sha,
                }
            )
        elif current_last_change != candidate_last_change:
            reviewed_path_history_changes.append(
                {
                    "path": path,
                    "candidate_last_change_commit": candidate_last_change,
                    "current_last_change_commit": current_last_change,
                }
            )
    if changed_reviewed_paths:
        _raise(
            "reviewed_files_changed",
            "one or more reviewed paths changed after the candidate commit",
            changed=changed_reviewed_paths,
        )
    if reviewed_path_history_changes:
        _raise(
            "reviewed_path_history_changed",
            "reviewed paths were modified after the candidate, even though current bytes match",
            changed=reviewed_path_history_changes,
        )

    remote_result: dict[str, str] | None = None
    if require_remote_reachability:
        try:
            remote_head = git_client.remote_head(
                config.remote_name, config.remote_branch
            )
            remote_head = git_client.resolve_commit(remote_head)
            unreachable = [
                label
                for label, commit in (
                    ("candidate", candidate),
                    ("review_record", review_record_commit),
                    ("head", head),
                )
                if not git_client.is_ancestor(commit, remote_head)
            ]
        except GitOperationError as exc:
            _raise(
                "remote_evidence_unavailable",
                "unable to resolve or inspect the configured remote branch",
                remote=config.remote_name,
                branch=config.remote_branch,
                reason=str(exc),
            )
        if unreachable:
            _raise(
                "remote_reachability_failure",
                "required commits are not reachable from the configured remote branch",
                unreachable=unreachable,
                remote_head=remote_head,
            )
        remote_result = {
            "name": config.remote_name,
            "branch": config.remote_branch,
            "head": remote_head,
        }

    return {
        "valid": True,
        "experiment_id": config.experiment_id,
        "gate_id": config.gate_id,
        "schema_version": REVIEW_ARTIFACT_SCHEMA_VERSION,
        "disposition": "PASS",
        "reviewer": {
            "kind": reviewer_kind,
            "id": reviewer_id,
            "human_review_performed": human_review,
            "external_authentication": human_authentication,
        },
        "reviewed_candidate": {
            "commit": candidate,
            "tree_oid": expected_tree,
            "required_path_set_sha256": observed_path_digest,
            "reviewed_files_sha256": observed_files_digest,
            "file_count": len(candidate_records),
        },
        "review_artifact": {
            "path": configured_artifact,
            "sha256": sha256_bytes(artifact_bytes),
            "git_blob_oid": artifact_blob_oid,
            "last_change_commit": review_record_commit,
            "commit_changed_paths": list(review_commit_paths),
        },
        "validated_head": head,
        "required_checks": list(passed_checks),
        "finding_count": finding_count,
        "open_blocking_findings": 0,
        "remote": remote_result,
    }


# Explicit aliases keep integration call sites readable without weakening the
# single fail-closed implementation.
validate_predata_review = validate_review_gate
validate_predata_review_artifact = validate_review_gate


__all__ = [
    "AI_INDEPENDENCE_SCOPE",
    "AI_CLAIM_BOUNDARY",
    "AI_SUBAGENT",
    "GITHUB_HUMAN",
    "GitClient",
    "HumanAuthenticator",
    "REQUIRED_AI_LIMITATIONS",
    "REQUIRED_AI_OPERATOR_ASSERTIONS",
    "REVIEW_ARTIFACT_SCHEMA_VERSION",
    "REVIEW_GATE_CONFIG_SCHEMA_VERSION",
    "ReviewGateError",
    "ReviewGateConfig",
    "SubprocessGit",
    "canonical_json_bytes",
    "required_path_set_sha256",
    "reviewed_files_sha256",
    "sha256_bytes",
    "validate_predata_review",
    "validate_predata_review_artifact",
    "validate_review_gate",
]
