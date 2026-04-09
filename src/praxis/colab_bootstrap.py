from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


DEFAULT_COLAB_WORKSPACE = Path("/content/praxis-workspace")
DEFAULT_COLAB_DRIVE_ROOT = Path("/content/drive/MyDrive/praxis")
DEFAULT_COLAB_RUNS_DIR = DEFAULT_COLAB_DRIVE_ROOT / "runs"
DEFAULT_COLAB_CACHE_DIR = DEFAULT_COLAB_DRIVE_ROOT / "cache"
DEFAULT_COLAB_DATA_DIR = DEFAULT_COLAB_DRIVE_ROOT / "data" / "unraveled" / "network-flows"


def is_colab() -> bool:
    return "google.colab" in sys.modules or "COLAB_RELEASE_TAG" in os.environ


def run_command(args: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(args)
    print(f"$ {printable}")
    subprocess.run(args, cwd=str(cwd) if cwd else None, check=True)


def ensure_directory(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def mount_google_drive(mount_point: str = "/content/drive") -> Path:
    try:
        from google.colab import drive
    except ImportError as exc:
        raise RuntimeError("Google Drive mount is only available inside Colab.") from exc

    drive.mount(mount_point)
    return Path(mount_point)


def configure_persistent_runtime(
    drive_root: str | Path = DEFAULT_COLAB_DRIVE_ROOT,
) -> dict[str, Path]:
    base = ensure_directory(drive_root)
    runtime_cache = ensure_directory(base / "runtime-cache")
    mpl_config = ensure_directory(runtime_cache / "matplotlib")
    torch_home = ensure_directory(runtime_cache / "torch")
    runs_dir = ensure_directory(base / "runs")
    cache_dir = ensure_directory(base / "cache")

    os.environ["MPLCONFIGDIR"] = str(mpl_config)
    os.environ["TORCH_HOME"] = str(torch_home)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONUTF8"] = "1"

    return {
        "drive_root": base,
        "runs_dir": runs_dir,
        "cache_dir": cache_dir,
        "mpl_config_dir": mpl_config,
        "torch_home": torch_home,
    }


def link_directory(source: str | Path, target: str | Path) -> Path:
    source_path = Path(source).resolve()
    target_path = Path(target)

    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() or target_path.is_symlink():
        if target_path.is_symlink() and target_path.resolve() == source_path:
            return target_path
        raise RuntimeError(
            f"Target path already exists and cannot be replaced automatically: {target_path}"
        )

    target_path.symlink_to(source_path, target_is_directory=True)
    return target_path


def prepare_unraveled_workspace_from_drive(
    workspace_dir: str | Path = DEFAULT_COLAB_WORKSPACE,
    drive_data_dir: str | Path = DEFAULT_COLAB_DATA_DIR,
) -> Path:
    workspace = Path(workspace_dir)
    target = workspace / "imports" / "unraveled" / "data" / "network-flows"
    return link_directory(drive_data_dir, target)


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
