from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


DEFAULT_COLAB_WORKSPACE = Path("/content/praxis-workspace")


def is_colab() -> bool:
    return "google.colab" in sys.modules or "COLAB_RELEASE_TAG" in os.environ


def run_command(args: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(args)
    print(f"$ {printable}")
    subprocess.run(args, cwd=str(cwd) if cwd else None, check=True)


def clone_or_update_repo(
    repo_url: str,
    branch: str = "main",
    workspace_dir: str | Path = DEFAULT_COLAB_WORKSPACE,
) -> Path:
    workspace = Path(workspace_dir)

    if workspace.exists() and (workspace / ".git").exists():
        run_command(["git", "fetch", "origin", branch], cwd=workspace)
        run_command(["git", "checkout", branch], cwd=workspace)
        run_command(["git", "pull", "--ff-only", "origin", branch], cwd=workspace)
        return workspace

    if workspace.exists() and any(workspace.iterdir()):
        raise RuntimeError(
            f"Workspace {workspace} already exists and is not empty. "
            "Choose a different workspace_dir."
        )

    run_command(["git", "clone", "--branch", branch, repo_url, str(workspace)])
    return workspace


def install_project(workspace_dir: str | Path = ".") -> Path:
    workspace = Path(workspace_dir).resolve()
    requirements_file = workspace / "requirements.txt"

    if requirements_file.exists():
        run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])

    run_command([sys.executable, "-m", "pip", "install", "-e", str(workspace)])

    src_dir = workspace / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    return workspace


def prepare_workspace(
    repo_url: str | None = None,
    branch: str = "main",
    workspace_dir: str | Path | None = None,
    install: bool = True,
) -> Path:
    if repo_url:
        target = clone_or_update_repo(
            repo_url=repo_url,
            branch=branch,
            workspace_dir=workspace_dir or DEFAULT_COLAB_WORKSPACE,
        )
    else:
        target = Path.cwd().resolve()

    if install:
        install_project(target)

    return target
