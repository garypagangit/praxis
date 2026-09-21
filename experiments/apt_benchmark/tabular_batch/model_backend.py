"""Pinned foundation-model constructors; no model fitting at import or CLI time.

Download into private data/cache storage, not this source tree. Both checkpoints
are public and are addressed by immutable revision and verified SHA256. This
module never reads credentials or uses a hosted prediction API.

Example::

    model, receipt = create_foundation_classifier(
        "tabicl_v2", cache_dir, seed=20260921, device="auto")
    # The runner, not this module, decides whether the dataset gate permits fit.

The fixed four-member ensembles are feasibility settings, not tuned defaults.
Pin the full resolved environment in the run receipt as well as requirements.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import tempfile
from typing import Any
import urllib.error
import urllib.request


@dataclass(frozen=True)
class Checkpoint:
    package: str
    package_version: str
    repository: str
    revision: str
    filename: str
    sha256: str
    size_bytes: int
    license: str

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repository}/resolve/{self.revision}/{self.filename}"


CHECKPOINTS = {
    "tabicl_v2": Checkpoint(
        "tabicl", "2.2.0", "jingang/TabICL",
        "4dcd344ece2c00be9e831fdd35bed57b5ad83e19",
        "tabicl-classifier-v2-20260212.ckpt",
        "bdc7dbd5e4ff21f8f0456fcf90c6b7cdf72dbea960f2d05b19bec19f9b3d4ed0",
        110368038, "BSD-3-Clause",
    ),
    "tabpfn_2_5_synthetic": Checkpoint(
        "tabpfn", "9.0.0", "Prior-Labs/tabpfn_2_5",
        "6c45f3a6d0d07c6c5f62572e04a0c2929de91b8b",
        "tabpfn-v2.5-classifier-v2.5_default-2.ckpt",
        "2d0fbd257a5a274f2a219836d5a68e9c27224845936b4685d85dd42e2b8092aa",
        42929867, "TabPFN-2.5 License v1.1 (noncommercial)",
    ),
}


def _checkpoint(name: str) -> Checkpoint:
    if name not in CHECKPOINTS:
        raise ValueError(f"Unknown model {name!r}; choose {', '.join(CHECKPOINTS)}")
    return CHECKPOINTS[name]


def _verify(path: Path, spec: Checkpoint) -> bool:
    if not path.is_file() or path.stat().st_size != spec.size_bytes:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == spec.sha256


def ensure_checkpoint(
    name: str, cache_dir: str | Path, *, allow_download: bool = True,
) -> Path:
    """Return a verified local checkpoint; fail closed on existing corruption.

    Downloads are staged then atomically placed after size/hash checks. Existing
    mismatched files are retained for inspection rather than silently replaced.
    """
    spec = _checkpoint(name)
    directory = Path(cache_dir).expanduser().resolve() / name / spec.revision
    destination = directory / spec.filename
    if destination.exists():
        if not _verify(destination, spec):
            raise RuntimeError(f"Checkpoint integrity failure for {name}; cached file retained.")
        return destination
    if not allow_download:
        raise FileNotFoundError(f"Pinned checkpoint for {name} is not cached.")
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".download-", dir=directory)
    staged = Path(temporary_name)
    try:
        request = urllib.request.Request(spec.url, headers={"User-Agent": "apt-praxis-research"})
        with os.fdopen(descriptor, "wb") as output:
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        output.write(chunk)
            except urllib.error.HTTPError as error:
                raise RuntimeError(f"Public checkpoint download failed with HTTP {error.code}.") from None
            except urllib.error.URLError:
                raise RuntimeError("Public checkpoint download failed due to a network error.") from None
        if not _verify(staged, spec):
            raise RuntimeError(f"Downloaded checkpoint failed integrity verification for {name}.")
        os.replace(staged, destination)
    finally:
        staged.unlink(missing_ok=True)
    return destination


def environment_versions() -> dict[str, str | None]:
    """Read package versions only; never enumerate environment variables."""
    result: dict[str, str | None] = {"python": platform.python_version()}
    for name in ("torch", "tabpfn", "tabicl", "numpy", "scipy", "scikit-learn", "pandas"):
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = None
    return result


def resolve_device(requested: str = "auto") -> tuple[str, dict[str, Any]]:
    """Prefer explicit CUDA:0 when available; a requested CUDA device must exist.

    Only auto may fall back to CPU. An inference OOM is not silently retried on
    another device, because that would invalidate recorded timing comparisons.
    """
    if requested not in ("auto", "cpu", "cuda", "cuda:0"):
        raise ValueError("device must be auto, cpu, cuda, or cuda:0")
    torch = importlib.import_module("torch")
    available = bool(torch.cuda.is_available())
    if requested.startswith("cuda") and not available:
        raise RuntimeError("CUDA was explicitly requested but is unavailable.")
    selected = "cuda:0" if available and requested != "cpu" else "cpu"
    receipt = {
        "requested_device": requested,
        "selected_device": selected,
        "cuda_available": available,
        "cuda_runtime": torch.version.cuda,
        "cpu_fallback": requested == "auto" and not available,
        "gpu_name": torch.cuda.get_device_name(0) if selected.startswith("cuda") else None,
    }
    return selected, receipt


def create_foundation_classifier(
    name: str,
    cache_dir: str | Path,
    *,
    seed: int,
    device: str = "auto",
    n_estimators: int = 4,
    allow_download: bool = True,
    strict_package_version: bool = True,
) -> tuple[Any, dict[str, Any]]:
    """Construct an unfitted sklearn-style classifier and its provenance receipt.

    Caller must record fit/predict costs, synchronize CUDA for timing, and count
    calibration/selection labels. This helper does not enable finetuning or HPO.
    """
    spec = _checkpoint(name)
    if not isinstance(n_estimators, int) or isinstance(n_estimators, bool) or n_estimators < 1:
        raise ValueError("n_estimators must be a positive integer")
    installed = environment_versions()
    if strict_package_version and installed[spec.package] != spec.package_version:
        raise RuntimeError(
            f"Expected {spec.package}=={spec.package_version}; found {installed[spec.package]!r}."
        )
    selected_device, device_receipt = resolve_device(device)
    checkpoint_path = ensure_checkpoint(name, cache_dir, allow_download=allow_download)
    common = dict(n_estimators=n_estimators, random_state=int(seed), device=selected_device)
    if name == "tabicl_v2":
        package = importlib.import_module("tabicl")
        settings = dict(
            model_path=str(checkpoint_path), allow_auto_download=False,
            checkpoint_version=spec.filename, batch_size=1, kv_cache=False,
            use_amp=False, use_fa3=False, offload_mode="auto", n_jobs=1,
            verbose=False, **common,
        )
        classifier = package.TabICLClassifier(**settings)
    else:
        package = importlib.import_module("tabpfn")
        constants = importlib.import_module("tabpfn.constants")
        settings = dict(
            model_path=str(checkpoint_path), fit_mode="fit_preprocessors",
            inference_precision="auto", memory_saving_mode="auto",
            n_preprocessing_jobs=1, show_progress_bar=False, **common,
        )
        classifier = package.TabPFNClassifier.create_default_for_version(
            constants.ModelVersion.V2_5, **settings,
        )
    receipt = {
        "model_id": name, "checkpoint": asdict(spec),
        "checkpoint_verified": True, "environment": installed,
        "device": device_receipt, "constructor_settings": settings,
        "fixed_feasibility_ensemble": n_estimators,
        "tuned": False, "fitted": False, "runtime_compatibility_tested": False,
        "cpu_cost_note": "CPU cost is unmeasured; restrict smoke-test rows and time before expanding.",
    }
    return classifier, receipt


# Convenient alias for runners that register different model families.
create_model = create_foundation_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", choices=tuple(CHECKPOINTS))
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--probe-device", choices=("auto", "cpu", "cuda", "cuda:0"))
    args = parser.parse_args()
    if args.download and args.cache_dir is None:
        parser.error("--download requires --cache-dir")
    report: dict[str, Any] = {
        "models": {name: asdict(spec) for name, spec in CHECKPOINTS.items()},
        "environment": environment_versions(), "fitted": False,
    }
    if args.download:
        report["verified_checkpoint_path"] = str(ensure_checkpoint(args.download, args.cache_dir))
    if args.probe_device:
        _, report["device"] = resolve_device(args.probe_device)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
