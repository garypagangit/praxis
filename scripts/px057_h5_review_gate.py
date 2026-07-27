"""Fail-closed validation for the PX-057 H5 pre-data code-review gate.

The review artifact is evidence about an exact Git candidate, not authority by
itself.  This module reconstructs the reviewed bytes from Git, derives the
commit that introduced the artifact, and verifies that no reviewed byte has
changed.  It deliberately has no dependency on the H4 implementation so it can
be invoked by the H5 freezer, submitters, cloud entry points, and adjudicator.

The validator proves repository facts (bytes, hashes, ancestry, and exact live
remote URL/tip binding in its production entry point).  Statements about an AI
reviewer's context isolation are still operator assertions; the schema makes
that limitation explicit and prevents an AI review from being represented as
human review.  Production callers must invoke it from an isolated trusted
Python bootstrap and prevent mutation between validation and launch.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Protocol, Sequence


REVIEW_GATE_CONFIG_SCHEMA_VERSION = "px057-h5-review-gate-config/v1"
REVIEW_ARTIFACT_SCHEMA_VERSION = "px057-h5-predata-code-review/v1"
WORKTREE_BYTE_POLICY = "git_blob_or_crlf_only"

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
        "protected_paths",
        "review_required_paths",
        "artifact_commit_allowed_paths",
        "accepted_reviewer_kinds",
        "human_review_required",
        "implementation_author_ids",
        "required_independence_scope",
        "required_ai_limitations",
        "required_checks",
        "required_claim_boundary",
        "worktree_byte_policy",
        "require_artifact_absent_at_candidate",
        "remote",
    }
)
_REMOTE_KEYS = frozenset({"name", "url", "branch"})
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
MANDATORY_REVIEW_CHECKS = (
    "adjudicator_enforced",
    "cloud_gate_enforced",
    "freeze_gate_enforced",
    "launch_gate_enforced",
    "protected_set_complete",
)
_REGULAR_GIT_MODES = frozenset({"100644", "100755"})


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

    def is_shallow_repository(self) -> bool: ...

    def replacement_refs(self) -> tuple[str, ...]: ...

    def grafts_file_present(self) -> bool: ...

    def local_attributes_file_present(self) -> bool: ...

    def external_attributes_file(self) -> str | None: ...

    def tree_oid(self, commit: str) -> str: ...

    def show_file(self, commit: str, path: str) -> bytes: ...

    def path_entry(self, commit: str, path: str) -> "GitPathEntry | None": ...

    def blob_oid(self, commit: str, path: str) -> str: ...

    def commits_touching_path(
        self, base: str, head: str, path: str
    ) -> tuple[str, ...]: ...

    def is_ancestor(self, ancestor: str, descendant: str) -> bool: ...

    def changed_paths(self, base: str, head: str) -> tuple[str, ...]: ...

    def is_tracked(self, path: str) -> bool: ...

    def status_for_path(self, path: str) -> bytes: ...

    def repository_status(self) -> bytes: ...

    def index_tag(self, path: str) -> str: ...

    def path_attributes(self, path: str) -> Mapping[str, str]: ...

    def remote_urls(self, remote: str) -> tuple[str, ...]: ...

    def url_rewrites(self) -> tuple[str, ...]: ...

    def remote_head(self, remote: str, branch: str) -> str: ...


GitExecutor = Callable[[Sequence[str], Path], subprocess.CompletedProcess[bytes]]
HumanAuthenticator = Callable[
    [Mapping[str, Any], Mapping[str, Any], "ReviewGateConfig"],
    Mapping[str, Any],
]


@dataclass(frozen=True)
class GitPathEntry:
    """An exact entry from a commit tree."""

    mode: str
    object_type: str
    oid: str
    path: str


def _default_git_executor(
    args: Sequence[str], repo_root: Path, *, executable: str = "git"
) -> subprocess.CompletedProcess[bytes]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        [executable, *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
        env=environment,
        timeout=30,
    )


class SubprocessGit:
    """Git client whose process executor can be replaced in tests or callers."""

    def __init__(
        self,
        repo_root: Path,
        *,
        executor: GitExecutor | None = None,
        git_executable: Path | str = "git",
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        executable = str(git_executable)
        self._executor = executor or (
            lambda args, root: _default_git_executor(
                args, root, executable=executable
            )
        )

    def _run(
        self, args: Sequence[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        protected_args = ("--no-replace-objects", *args)
        try:
            result = self._executor(protected_args, self.repo_root)
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError(
                protected_args,
                124,
                exc.stdout or b"",
                exc.stderr or b"Git command timed out",
            ) from exc
        except OSError as exc:
            raise GitOperationError(
                protected_args,
                127,
                b"",
                str(exc).encode("utf-8", errors="replace"),
            ) from exc
        if check and result.returncode != 0:
            raise GitOperationError(
                protected_args,
                result.returncode,
                result.stdout,
                result.stderr,
            )
        return result

    def resolve_commit(self, revision: str) -> str:
        return (
            self._run(["rev-parse", "--verify", f"{revision}^{{commit}}"])
            .stdout.decode("ascii")
            .strip()
        )

    def is_shallow_repository(self) -> bool:
        value = (
            self._run(["rev-parse", "--is-shallow-repository"])
            .stdout.decode("ascii")
            .strip()
        )
        if value not in {"true", "false"}:
            raise GitOperationError(
                ["rev-parse", "--is-shallow-repository"],
                1,
                value.encode("ascii", errors="replace"),
                b"unexpected shallow-repository response",
            )
        return value == "true"

    def replacement_refs(self) -> tuple[str, ...]:
        content = self._run(
            ["for-each-ref", "--format=%(refname)", "refs/replace/"]
        ).stdout
        return tuple(
            row.strip()
            for row in content.decode("utf-8").splitlines()
            if row.strip()
        )

    def grafts_file_present(self) -> bool:
        raw_path = (
            self._run(["rev-parse", "--git-path", "info/grafts"])
            .stdout.decode("utf-8")
            .strip()
        )
        if not raw_path:
            raise GitOperationError(
                ["rev-parse", "--git-path", "info/grafts"],
                1,
                b"",
                b"Git returned an empty grafts path",
            )
        grafts_path = Path(raw_path)
        if not grafts_path.is_absolute():
            grafts_path = self.repo_root / grafts_path
        try:
            return grafts_path.is_file() and grafts_path.stat().st_size > 0
        except OSError as exc:
            raise GitOperationError(
                ["rev-parse", "--git-path", "info/grafts"],
                1,
                b"",
                str(exc).encode("utf-8", errors="replace"),
            ) from exc

    def _git_metadata_file_present(self, relative: str) -> bool:
        raw_path = (
            self._run(["rev-parse", "--git-path", relative])
            .stdout.decode("utf-8")
            .strip()
        )
        if not raw_path:
            raise GitOperationError(
                ["rev-parse", "--git-path", relative],
                1,
                b"",
                b"Git returned an empty metadata path",
            )
        metadata_path = Path(raw_path)
        if not metadata_path.is_absolute():
            metadata_path = self.repo_root / metadata_path
        try:
            return metadata_path.is_file() and metadata_path.stat().st_size > 0
        except OSError as exc:
            raise GitOperationError(
                ["rev-parse", "--git-path", relative],
                1,
                b"",
                str(exc).encode("utf-8", errors="replace"),
            ) from exc

    def local_attributes_file_present(self) -> bool:
        return self._git_metadata_file_present("info/attributes")

    def external_attributes_file(self) -> str | None:
        result = self._run(
            ["config", "--path", "--get", "core.attributesfile"],
            check=False,
        )
        if result.returncode == 1:
            return None
        if result.returncode != 0:
            raise GitOperationError(
                ["config", "--path", "--get", "core.attributesfile"],
                result.returncode,
                result.stdout,
                result.stderr,
            )
        value = result.stdout.decode("utf-8").strip()
        return value or None

    def tree_oid(self, commit: str) -> str:
        return (
            self._run(["rev-parse", "--verify", f"{commit}^{{tree}}"])
            .stdout.decode("ascii")
            .strip()
        )

    def show_file(self, commit: str, path: str) -> bytes:
        return self._run(["show", f"{commit}:{path}"]).stdout

    def path_entry(self, commit: str, path: str) -> GitPathEntry | None:
        content = self._run(["ls-tree", "-z", commit, "--", path]).stdout
        rows = [row for row in content.split(b"\0") if row]
        if not rows:
            return None
        if len(rows) != 1 or b"\t" not in rows[0]:
            raise GitOperationError(
                ["ls-tree", "-z", commit, "--", path],
                1,
                content,
                b"expected exactly one tree entry",
            )
        metadata, raw_path = rows[0].split(b"\t", 1)
        fields = metadata.decode("ascii").split()
        observed_path = raw_path.decode("utf-8")
        if len(fields) != 3 or observed_path != path:
            raise GitOperationError(
                ["ls-tree", "-z", commit, "--", path],
                1,
                content,
                b"tree entry did not exactly match requested path",
            )
        return GitPathEntry(fields[0], fields[1], fields[2], observed_path)

    def blob_oid(self, commit: str, path: str) -> str:
        entry = self.path_entry(commit, path)
        if entry is None:
            raise GitOperationError(
                ["ls-tree", "-z", commit, "--", path],
                1,
                b"",
                b"path is absent",
            )
        return entry.oid

    def commits_touching_path(
        self, base: str, head: str, path: str
    ) -> tuple[str, ...]:
        content = self._run(
            ["rev-list", "--full-history", head, f"^{base}", "--", path]
        ).stdout
        return tuple(
            row.strip()
            for row in content.decode("ascii").splitlines()
            if row.strip()
        )

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
        result = self._run(
            ["ls-files", "--error-unmatch", "--", path], check=False
        )
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        raise GitOperationError(
            ["ls-files", "--error-unmatch", "--", path],
            result.returncode,
            result.stdout,
            result.stderr,
        )

    def status_for_path(self, path: str) -> bytes:
        return self._run(
            ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", path]
        ).stdout

    def repository_status(self) -> bytes:
        return self._run(
            [
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignored=matching",
            ]
        ).stdout

    def index_tag(self, path: str) -> str:
        content = self._run(["ls-files", "-v", "-z", "--", path]).stdout
        rows = [row for row in content.split(b"\0") if row]
        if len(rows) != 1 or len(rows[0]) < 3 or rows[0][1:2] != b" ":
            raise GitOperationError(
                ["ls-files", "-v", "-z", "--", path],
                1,
                content,
                b"expected exactly one index entry",
            )
        return rows[0][:1].decode("ascii")

    def path_attributes(self, path: str) -> Mapping[str, str]:
        names = ("filter", "working-tree-encoding")
        content = self._run(["check-attr", "-z", *names, "--", path]).stdout
        fields = [field.decode("utf-8") for field in content.split(b"\0") if field]
        if len(fields) != 3 * len(names):
            raise GitOperationError(
                ["check-attr", "-z", *names, "--", path],
                1,
                content,
                b"unexpected check-attr response",
            )
        result: dict[str, str] = {}
        for index in range(0, len(fields), 3):
            observed_path, name, value = fields[index : index + 3]
            if observed_path != path or name not in names or name in result:
                raise GitOperationError(
                    ["check-attr", "-z", *names, "--", path],
                    1,
                    content,
                    b"attribute response did not match request",
                )
            result[name] = value
        return result

    def remote_urls(self, remote: str) -> tuple[str, ...]:
        result = self._run(
            ["config", "--get-all", f"remote.{remote}.url"], check=False
        )
        if result.returncode == 1:
            return ()
        if result.returncode != 0:
            raise GitOperationError(
                ["config", "--get-all", f"remote.{remote}.url"],
                result.returncode,
                result.stdout,
                result.stderr,
            )
        return tuple(
            row.strip()
            for row in result.stdout.decode("utf-8").splitlines()
            if row.strip()
        )

    def url_rewrites(self) -> tuple[str, ...]:
        result = self._run(
            ["config", "--get-regexp", r"^url\..*\.insteadOf$"], check=False
        )
        if result.returncode == 1:
            return ()
        if result.returncode != 0:
            raise GitOperationError(
                ["config", "--get-regexp", r"^url\..*\.insteadOf$"],
                result.returncode,
                result.stdout,
                result.stderr,
            )
        return tuple(
            row.strip()
            for row in result.stdout.decode("utf-8").splitlines()
            if row.strip()
        )

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
    protected_paths: tuple[str, ...]
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
    remote_url: str
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
    protected_paths = _normalize_path_list(
        config["protected_paths"], "review_config.protected_paths"
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
    if set(allowed_paths) - set(protected_paths):
        _raise(
            "protected_path_inventory_invalid",
            "post-review evidence paths must be members of the protected set",
            missing_from_protected=sorted(set(allowed_paths) - set(protected_paths)),
        )
    derived_required_paths = tuple(
        sorted(set(protected_paths) - set(allowed_paths))
    )
    if required_paths != derived_required_paths:
        _raise(
            "protected_path_inventory_invalid",
            "review-required paths must exactly equal protected paths minus post-review evidence",
            observed=list(required_paths),
            derived=list(derived_required_paths),
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
    missing_mandatory_checks = set(MANDATORY_REVIEW_CHECKS) - set(required_checks)
    if missing_mandatory_checks:
        _raise(
            "review_policy_invalid",
            "review policy omits mandatory enforcement checks",
            missing=sorted(missing_mandatory_checks),
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
    worktree_byte_policy = _expect_nonempty_string(
        config["worktree_byte_policy"], "review_config.worktree_byte_policy"
    )
    if worktree_byte_policy != WORKTREE_BYTE_POLICY:
        _raise(
            "review_policy_invalid",
            "worktree byte policy must forbid every transform except CRLF conversion",
            observed=worktree_byte_policy,
            required=WORKTREE_BYTE_POLICY,
        )
    require_absent = _expect_bool(
        config["require_artifact_absent_at_candidate"],
        "review_config.require_artifact_absent_at_candidate",
    )
    if not require_absent:
        _raise(
            "review_policy_invalid",
            "review evidence must be absent from the reviewed candidate",
        )
    remote = _expect_mapping(config["remote"], "review_config.remote")
    _expect_exact_keys(remote, _REMOTE_KEYS, "review_config.remote")
    remote_name = _expect_nonempty_string(remote["name"], "review_config.remote.name")
    remote_url = _expect_nonempty_string(
        remote["url"], "review_config.remote.url"
    )
    remote_branch = _expect_nonempty_string(
        remote["branch"], "review_config.remote.branch"
    )
    return ReviewGateConfig(
        experiment_id=experiment_id,
        gate_id=gate_id,
        review_artifact_path=artifact_path,
        protected_paths=protected_paths,
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
        remote_url=remote_url,
        remote_branch=remote_branch,
    )


def _json_no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _raise("duplicate_json_key", "review artifact contains a duplicate JSON key", key=key)
        result[key] = value
    return result


def _parse_json_mapping_bytes(
    content: bytes,
    *,
    location: str,
    encoding_error: str,
    json_error: str,
) -> Mapping[str, Any]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        _raise(encoding_error, f"{location} is not valid UTF-8", reason=str(exc))
    try:
        value = json.loads(text, object_pairs_hook=_json_no_duplicate_keys)
    except ReviewGateError:
        raise
    except json.JSONDecodeError as exc:
        _raise(
            json_error,
            f"{location} is not valid JSON",
            line=exc.lineno,
            column=exc.colno,
            reason=exc.msg,
        )
    return _expect_mapping(value, location)


def _parse_artifact_bytes(content: bytes) -> Mapping[str, Any]:
    return _parse_json_mapping_bytes(
        content,
        location="review_artifact",
        encoding_error="artifact_encoding_invalid",
        json_error="artifact_json_invalid",
    )


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
            entry = git.path_entry(candidate, path)
            if entry is None:
                _raise(
                    "candidate_file_missing",
                    "a required reviewed path is absent from the candidate commit",
                    path=path,
                )
            if (
                entry.object_type != "blob"
                or entry.mode not in _REGULAR_GIT_MODES
            ):
                _raise(
                    "candidate_file_not_regular",
                    "a required reviewed path is not an ordinary Git file",
                    path=path,
                    mode=entry.mode,
                    object_type=entry.object_type,
                )
            content = git.show_file(candidate, path)
            blob_oid = entry.oid
        except ReviewGateError:
            raise
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


def _local_regular_path(
    repo_root: Path,
    relative: str,
    *,
    missing_code: str,
) -> Path:
    root = repo_root.resolve()
    current = root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
            mode = metadata.st_mode
        except FileNotFoundError:
            _raise(missing_code, "required worktree path is missing", path=relative)
        junction_probe = getattr(current, "is_junction", None)
        try:
            is_junction = bool(junction_probe()) if junction_probe else False
        except OSError:
            is_junction = True
        if (
            stat.S_ISLNK(mode)
            or is_junction
            or bool(getattr(metadata, "st_reparse_tag", 0))
        ):
            _raise(
                "worktree_path_not_regular",
                "required worktree path has a link, junction, or reparse component",
                path=relative,
                component="/".join(parts[: index + 1]),
            )
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            _raise(
                "worktree_path_not_regular",
                "required worktree parent is not a directory",
                path=relative,
                component="/".join(parts[: index + 1]),
            )
    if not stat.S_ISREG(current.lstat().st_mode):
        _raise(
            "worktree_path_not_regular",
            "required worktree path is not an ordinary file",
            path=relative,
        )
    return current


def _verify_checked_out_file(
    repo_root: Path,
    git: GitClient,
    head: str,
    path: str,
    *,
    missing_code: str,
    dirty_code: str,
) -> tuple[bytes, GitPathEntry]:
    local_path = _local_regular_path(
        repo_root, path, missing_code=missing_code
    )
    if not git.is_tracked(path):
        _raise(missing_code, "required worktree path is not tracked", path=path)
    entry = git.path_entry(head, path)
    if entry is None:
        _raise(missing_code, "required path is absent from HEAD", path=path)
    if entry.object_type != "blob" or entry.mode not in _REGULAR_GIT_MODES:
        _raise(
            "worktree_path_not_regular",
            "required HEAD path is not an ordinary Git file",
            path=path,
            mode=entry.mode,
            object_type=entry.object_type,
        )
    index_tag = git.index_tag(path)
    if index_tag == "S" or index_tag.islower():
        _raise(
            "forbidden_index_flag",
            "assume-unchanged and skip-worktree flags are forbidden",
            path=path,
            index_tag=index_tag,
        )
    attributes = git.path_attributes(path)
    dangerous_attributes = {
        name: value
        for name, value in attributes.items()
        if value not in {"unspecified", "unset"}
    }
    if dangerous_attributes:
        _raise(
            "dangerous_git_attributes",
            "filters and working-tree encodings are forbidden on protected files",
            path=path,
            attributes=dangerous_attributes,
        )
    status = git.status_for_path(path)
    if status:
        _raise(
            dirty_code,
            "required path has staged or worktree changes",
            path=path,
            porcelain=status.decode("utf-8", errors="replace"),
        )
    committed_bytes = git.show_file(head, path)
    try:
        actual_worktree_bytes = local_path.read_bytes()
    except OSError as exc:
        _raise(
            missing_code,
            "unable to read required worktree bytes",
            path=path,
            reason=str(exc),
        )
    stripped_crlf = actual_worktree_bytes.replace(b"\r\n", b"\n")
    only_crlf_conversion = (
        b"\r" not in actual_worktree_bytes.replace(b"\r\n", b"")
        and stripped_crlf == committed_bytes
    )
    if actual_worktree_bytes != committed_bytes and not only_crlf_conversion:
        _raise(
            dirty_code,
            "raw worktree bytes differ from the reviewed blob beyond CRLF conversion",
            path=path,
            worktree_sha256=sha256_bytes(actual_worktree_bytes),
            reviewed_blob_sha256=sha256_bytes(committed_bytes),
        )
    return committed_bytes, entry


def _validate_review_gate_evidence_for_tests(
    repo_root: Path,
    review_config: Mapping[str, Any],
    *,
    config_path: Path | str | None,
    config_locator: Sequence[str] = (),
    expected_config_sha256: str | None = None,
    expected_protected_paths: Sequence[str] | None = None,
    mandatory_sentinel_paths: Sequence[str] = (),
    artifact_path: Path | str | None = None,
    head_revision: str = "HEAD",
    _enforce_remote: bool = False,
    _expected_remote_tip: str | None = None,
    _expected_remote_url: str | None = None,
    git: GitClient | None = None,
    human_authenticator: HumanAuthenticator | None = None,
) -> dict[str, Any]:
    """Offline/test-only evidence validator.

    Production callers must use :func:`validate_review_gate`, which cannot
    disable exact live-remote verification.  This injectable routine exists so
    each local invariant can be tested without a network dependency.
    """

    root = Path(repo_root).resolve()
    git_client: GitClient = git or SubprocessGit(root)
    if config_path is None:
        _raise(
            "config_evidence_required",
            "the gate policy must be loaded from an exact committed path",
        )
    raw_config_path = Path(config_path)
    if raw_config_path.is_absolute():
        _raise(
            "unsafe_path",
            "config_path must be repository-relative",
            path=str(config_path),
        )
    normalized_config_path = _normalize_repo_path(
        raw_config_path.as_posix(), "config_path"
    )
    try:
        if git_client.is_shallow_repository():
            _raise(
                "shallow_repository_forbidden",
                "full-DAG history claims require a non-shallow repository",
            )
        replacement_refs = git_client.replacement_refs()
        if replacement_refs:
            _raise(
                "replacement_objects_forbidden",
                "Git replacement refs are forbidden for review provenance",
                refs=list(replacement_refs),
            )
        if git_client.grafts_file_present():
            _raise(
                "grafts_forbidden",
                "legacy Git graft metadata is forbidden for review provenance",
            )
        if git_client.local_attributes_file_present():
            _raise(
                "local_attributes_forbidden",
                "mutable .git/info/attributes is forbidden for review provenance",
            )
        external_attributes = git_client.external_attributes_file()
        if external_attributes is not None:
            _raise(
                "external_attributes_forbidden",
                "external/global Git attributes files are forbidden",
                path=external_attributes,
            )
        head = git_client.resolve_commit(head_revision)
        checked_out_head = git_client.resolve_commit("HEAD")
        if head != checked_out_head:
            _raise(
                "validated_head_not_checkout",
                "validation revision must equal the actually checked-out HEAD",
                requested=head,
                checked_out=checked_out_head,
            )
        config_bytes, config_entry = _verify_checked_out_file(
            root,
            git_client,
            head,
            normalized_config_path,
            missing_code="config_evidence_missing",
            dirty_code="config_evidence_dirty",
        )
    except ReviewGateError:
        raise
    except GitOperationError as exc:
        _raise(
            "git_evidence_unavailable",
            "unable to reconstruct committed gate policy",
            reason=str(exc),
        )
    observed_config_sha = sha256_bytes(config_bytes)
    if expected_config_sha256 is not None:
        expected_config_sha256 = _validate_sha256(
            expected_config_sha256, "expected_config_sha256"
        )
        if observed_config_sha != expected_config_sha256:
            _raise(
                "config_hash_mismatch",
                "committed gate-policy bytes differ from the trusted hash",
                observed=observed_config_sha,
                expected=expected_config_sha256,
            )
    committed_config: Any = _parse_json_mapping_bytes(
        config_bytes,
        location="committed_review_config",
        encoding_error="config_encoding_invalid",
        json_error="config_json_invalid",
    )
    for index, key in enumerate(config_locator):
        key = _expect_nonempty_string(key, f"config_locator[{index}]")
        container = _expect_mapping(
            committed_config, f"committed_review_config locator {index}"
        )
        if key not in container:
            _raise(
                "config_locator_missing",
                "committed policy locator does not exist",
                key=key,
                index=index,
            )
        committed_config = container[key]
    committed_config = _expect_mapping(
        committed_config, "committed_review_config selection"
    )
    try:
        supplied_config_bytes = canonical_json_bytes(dict(review_config))
        committed_selection_bytes = canonical_json_bytes(dict(committed_config))
    except (TypeError, ValueError) as exc:
        _raise("schema_error", "review config is not canonical JSON", reason=str(exc))
    if supplied_config_bytes != committed_selection_bytes:
        _raise(
            "config_mapping_mismatch",
            "supplied policy mapping differs from committed policy evidence",
        )
    config = _parse_config(committed_config)
    if normalized_config_path not in config.review_required_paths:
        _raise(
            "config_not_protected",
            "the committed gate-policy file must itself be a reviewed path",
            path=normalized_config_path,
        )
    if expected_protected_paths is not None:
        expected_paths = _normalize_path_list(
            list(expected_protected_paths), "expected_protected_paths"
        )
        if tuple(config.protected_paths) != tuple(expected_paths):
            _raise(
                "protected_path_inventory_mismatch",
                "committed protected paths differ from the trusted inventory",
                observed=list(config.protected_paths),
                expected=list(expected_paths),
            )
    sentinels = (
        _normalize_path_list(
            list(mandatory_sentinel_paths), "mandatory_sentinel_paths"
        )
        if mandatory_sentinel_paths
        else ()
    )
    missing_sentinels = set(sentinels) - set(config.review_required_paths)
    if missing_sentinels:
        _raise(
            "mandatory_sentinel_missing",
            "mandatory launch/freeze sentinels are absent from reviewed paths",
            missing=sorted(missing_sentinels),
        )
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
    try:
        artifact_bytes, artifact_entry = _verify_checked_out_file(
            root,
            git_client,
            head,
            configured_artifact,
            missing_code="review_artifact_missing",
            dirty_code="review_artifact_dirty",
        )
        artifact_blob_oid = artifact_entry.oid
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

        artifact_touches = git_client.commits_touching_path(
            candidate, head, configured_artifact
        )
        if len(artifact_touches) != 1:
            _raise(
                "review_evidence_history_invalid",
                "review artifact must be introduced exactly once after the candidate",
                path=configured_artifact,
                touching_commits=list(artifact_touches),
            )
        review_record_commit = git_client.resolve_commit(artifact_touches[0])
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
        required_evidence_paths = tuple(
            sorted(config.artifact_commit_allowed_paths)
        )
        if review_commit_paths != required_evidence_paths:
            _raise(
                "artifact_commit_scope_invalid",
                "candidate-to-review diff must equal the exact review-evidence set",
                changed=list(review_commit_paths),
                required=list(required_evidence_paths),
                unexpected=sorted(
                    set(review_commit_paths) - set(required_evidence_paths)
                ),
                missing=sorted(
                    set(required_evidence_paths) - set(review_commit_paths)
                ),
            )

        review_evidence_records: list[dict[str, str]] = []
        for evidence_path in required_evidence_paths:
            candidate_entry = git_client.path_entry(candidate, evidence_path)
            if candidate_entry is not None:
                code = (
                    "stale_review_artifact"
                    if evidence_path == configured_artifact
                    else "stale_review_evidence"
                )
                _raise(
                    code,
                    "review evidence already existed in the reviewed candidate",
                    candidate=candidate,
                    path=evidence_path,
                )
            touching_commits = git_client.commits_touching_path(
                candidate, head, evidence_path
            )
            if touching_commits != (review_record_commit,):
                _raise(
                    "review_evidence_history_invalid",
                    "every evidence path must be introduced at R and never touched later",
                    path=evidence_path,
                    expected_commit=review_record_commit,
                    touching_commits=list(touching_commits),
                )
            review_entry = git_client.path_entry(
                review_record_commit, evidence_path
            )
            head_entry = git_client.path_entry(head, evidence_path)
            if review_entry is None or head_entry is None:
                _raise(
                    "review_evidence_missing",
                    "mandatory review evidence is missing at R or HEAD",
                    path=evidence_path,
                )
            if (
                review_entry.object_type != "blob"
                or review_entry.mode not in _REGULAR_GIT_MODES
                or head_entry.object_type != "blob"
                or head_entry.mode not in _REGULAR_GIT_MODES
            ):
                _raise(
                    "review_evidence_not_regular",
                    "review evidence must be an ordinary Git file",
                    path=evidence_path,
                )
            if head_entry.oid != review_entry.oid:
                _raise(
                    "review_evidence_changed",
                    "review evidence bytes differ from the unique introduction commit",
                    path=evidence_path,
                )
            review_evidence_records.append(
                {
                    "path": evidence_path,
                    "git_blob_oid": review_entry.oid,
                    "sha256": sha256_bytes(
                        git_client.show_file(review_record_commit, evidence_path)
                    ),
                }
            )
            _verify_checked_out_file(
                root,
                git_client,
                head,
                evidence_path,
                missing_code="review_evidence_missing",
                dirty_code="review_evidence_dirty",
            )
    except ReviewGateError:
        raise
    except GitOperationError as exc:
        _raise(
            "git_evidence_unavailable",
            "unable to verify candidate/review commit provenance",
            reason=str(exc),
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
    reviewed_path_history_changes: list[dict[str, Any]] = []
    try:
        for record in candidate_records:
            path = record["path"]
            current_bytes, current_entry = _verify_checked_out_file(
                root,
                git_client,
                head,
                path,
                missing_code="reviewed_file_missing",
                dirty_code="reviewed_file_dirty",
            )
            current_sha = sha256_bytes(current_bytes)
            if (
                current_entry.oid != record["git_blob_oid"]
                or current_sha != record["sha256"]
            ):
                changed_reviewed_paths.append(
                    {
                        "path": path,
                        "candidate_sha256": record["sha256"],
                        "current_sha256": current_sha,
                    }
                )
            touching_commits = git_client.commits_touching_path(
                candidate, head, path
            )
            if touching_commits:
                reviewed_path_history_changes.append(
                    {
                        "path": path,
                        "touching_commits": list(touching_commits),
                    }
                )
    except ReviewGateError:
        raise
    except GitOperationError as exc:
        _raise(
            "git_evidence_unavailable",
            "unable to verify reviewed files against the checked-out worktree",
            reason=str(exc),
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
            "reviewed paths were touched anywhere in the full DAG after the candidate",
            changed=reviewed_path_history_changes,
        )

    try:
        candidate_to_head_paths = tuple(
            sorted(git_client.changed_paths(candidate, head))
        )
    except GitOperationError as exc:
        _raise(
            "git_evidence_unavailable",
            "unable to verify the complete candidate-to-HEAD tree delta",
            reason=str(exc),
        )
    if candidate_to_head_paths != required_evidence_paths:
        _raise(
            "post_review_tree_changed",
            "HEAD may differ from the candidate only by the exact review-evidence set",
            changed=list(candidate_to_head_paths),
            required=list(required_evidence_paths),
            unexpected=sorted(
                set(candidate_to_head_paths) - set(required_evidence_paths)
            ),
            missing=sorted(
                set(required_evidence_paths) - set(candidate_to_head_paths)
            ),
        )

    try:
        whole_worktree_status = git_client.repository_status()
    except GitOperationError as exc:
        _raise(
            "git_evidence_unavailable",
            "unable to verify whole-worktree cleanliness",
            reason=str(exc),
        )
    if whole_worktree_status:
        _raise(
            "worktree_not_clean",
            "pre-data launch requires no staged, modified, untracked, or ignored files",
            porcelain=whole_worktree_status.decode("utf-8", errors="replace"),
        )

    remote_result: dict[str, str] | None = None
    if _enforce_remote:
        if _expected_remote_tip is None:
            _raise(
                "remote_tip_required",
                "production validation requires a trusted expected remote tip",
            )
        if _expected_remote_url is None:
            _raise(
                "remote_url_required",
                "production validation requires a trusted canonical remote URL",
            )
        expected_remote_url = _expect_nonempty_string(
            _expected_remote_url, "expected_remote_url"
        )
        if config.remote_url != expected_remote_url:
            _raise(
                "remote_url_mismatch",
                "committed remote URL differs from the trusted canonical URL",
                configured=config.remote_url,
                expected=expected_remote_url,
            )
        expected_remote_tip = _validate_object_id(
            _expected_remote_tip, "expected_remote_tip"
        )
        try:
            configured_urls = git_client.remote_urls(config.remote_name)
            if configured_urls != (expected_remote_url,):
                _raise(
                    "remote_url_mismatch",
                    "local remote configuration differs from the trusted URL",
                    configured=list(configured_urls),
                    expected=expected_remote_url,
                )
            rewrites = git_client.url_rewrites()
            if rewrites:
                _raise(
                    "remote_url_rewrite_forbidden",
                    "Git insteadOf URL rewrites are forbidden in production validation",
                    rewrites=list(rewrites),
                )
            resolved_expected_tip = git_client.resolve_commit(expected_remote_tip)
            if resolved_expected_tip != head:
                _raise(
                    "expected_remote_tip_mismatch",
                    "trusted expected remote tip does not equal checked-out HEAD",
                    expected=resolved_expected_tip,
                    head=head,
                )
            remote_head = _validate_object_id(
                git_client.remote_head(expected_remote_url, config.remote_branch),
                "remote_head",
            )
        except ReviewGateError:
            raise
        except GitOperationError as exc:
            _raise(
                "remote_evidence_unavailable",
                "unable to resolve or inspect the configured remote branch",
                remote=config.remote_name,
                branch=config.remote_branch,
                reason=str(exc),
            )
        if remote_head != head:
            _raise(
                "remote_tip_mismatch",
                "configured live remote tip must exactly equal checked-out HEAD",
                remote_head=remote_head,
                head=head,
            )
        remote_result = {
            "name": config.remote_name,
            "url": expected_remote_url,
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
        "gate_config": {
            "path": normalized_config_path,
            "sha256": observed_config_sha,
            "git_blob_oid": config_entry.oid,
            "protected_paths": list(config.protected_paths),
        },
        "review_artifact": {
            "path": configured_artifact,
            "sha256": sha256_bytes(artifact_bytes),
            "git_blob_oid": artifact_blob_oid,
            "last_change_commit": review_record_commit,
            "commit_changed_paths": list(review_commit_paths),
        },
        "review_evidence": review_evidence_records,
        "validated_head": head,
        "required_checks": list(passed_checks),
        "finding_count": finding_count,
        "open_blocking_findings": 0,
        "remote": remote_result,
    }


def _validate_trusted_git_executable(
    value: Path | str, repo_root: Path
) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        _raise(
            "trusted_git_executable_invalid",
            "production Git executable must be a filesystem path",
            observed_type=type(value).__name__,
        )
    executable = Path(value)
    if not executable.is_absolute():
        _raise(
            "trusted_git_executable_invalid",
            "production Git executable must be an absolute path",
            path=str(value),
        )
    try:
        metadata = executable.lstat()
    except OSError as exc:
        _raise(
            "trusted_git_executable_invalid",
            "trusted Git executable is unavailable",
            path=str(value),
            reason=str(exc),
        )
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or bool(getattr(metadata, "st_reparse_tag", 0))
    ):
        _raise(
            "trusted_git_executable_invalid",
            "trusted Git executable must be a non-link ordinary file",
            path=str(value),
        )
    resolved = executable.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        pass
    else:
        _raise(
            "trusted_git_executable_invalid",
            "production Git executable may not reside inside the repository",
            path=str(resolved),
        )
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        _raise(
            "trusted_git_executable_invalid",
            "trusted Git file is not executable",
            path=str(resolved),
        )
    return resolved


def validate_review_gate(
    repo_root: Path,
    review_config: Mapping[str, Any],
    *,
    config_path: Path | str,
    expected_config_sha256: str,
    expected_protected_paths: Sequence[str],
    mandatory_sentinel_paths: Sequence[str],
    expected_remote_tip: str,
    expected_remote_url: str,
    trusted_git_executable: Path | str,
    config_locator: Sequence[str] = (),
    artifact_path: Path | str | None = None,
    human_authenticator: HumanAuthenticator | None = None,
) -> dict[str, Any]:
    """Run the production H5 review gate with non-optional remote binding.

    The trusted caller supplies the frozen whole-config hash, protected-path
    inventory, mandatory sentinels, canonical remote URL, CI/event tip, and an
    absolute trusted Git executable outside the repository.  Validation only
    succeeds when that tip, the configured live remote branch, and the actual
    checked-out ``HEAD`` are the same commit.  The caller must itself run from
    an isolated trusted Python bootstrap.
    """

    if expected_config_sha256 is None:
        _raise(
            "trusted_config_hash_required",
            "production validation requires a trusted whole-config SHA-256",
        )
    _validate_sha256(expected_config_sha256, "expected_config_sha256")
    if expected_protected_paths is None:
        _raise(
            "trusted_protected_paths_required",
            "production validation requires a trusted protected-path inventory",
        )
    trusted_protected_paths = _normalize_path_list(
        list(expected_protected_paths), "expected_protected_paths"
    )
    trusted_git = _validate_trusted_git_executable(
        trusted_git_executable, Path(repo_root).resolve()
    )
    if not mandatory_sentinel_paths:
        _raise(
            "mandatory_sentinels_required",
            "production validation requires explicit launch/freeze sentinels",
        )

    return _validate_review_gate_evidence_for_tests(
        repo_root,
        review_config,
        config_path=config_path,
        config_locator=config_locator,
        expected_config_sha256=expected_config_sha256,
        expected_protected_paths=trusted_protected_paths,
        mandatory_sentinel_paths=mandatory_sentinel_paths,
        artifact_path=artifact_path,
        head_revision="HEAD",
        _enforce_remote=True,
        _expected_remote_tip=expected_remote_tip,
        _expected_remote_url=expected_remote_url,
        git=SubprocessGit(repo_root, git_executable=trusted_git),
        human_authenticator=human_authenticator,
    )


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
    "MANDATORY_REVIEW_CHECKS",
    "REQUIRED_AI_LIMITATIONS",
    "REQUIRED_AI_OPERATOR_ASSERTIONS",
    "REVIEW_ARTIFACT_SCHEMA_VERSION",
    "REVIEW_GATE_CONFIG_SCHEMA_VERSION",
    "WORKTREE_BYTE_POLICY",
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
