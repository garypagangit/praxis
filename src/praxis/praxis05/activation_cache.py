from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import torch

from praxis.praxis05.config import write_json


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_activation_cache(
    output_dir: str | Path,
    activations: torch.Tensor,
    metadata: Iterable[dict[str, Any]] | None = None,
    shard_name: str = "activations.pt",
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    tensor = activations.detach().cpu().float().contiguous()
    shard_path = output / shard_name
    torch.save({"activations": tensor}, shard_path)

    metadata_count = 0
    if metadata is not None:
        with (output / "metadata.jsonl").open("w", encoding="utf-8") as handle:
            for row in metadata:
                metadata_count += 1
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    manifest = {
        "format": "praxis05_activation_cache_v1",
        "shards": [
            {
                "path": shard_name,
                "sha256": sha256_file(shard_path),
                "rows": int(tensor.shape[0]),
                "hidden_dim": int(tensor.shape[1]),
            }
        ],
        "metadata_rows": metadata_count,
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def load_activation_tensor(cache_dir: str | Path) -> torch.Tensor:
    root = Path(cache_dir)
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tensors = []
        for shard in manifest.get("shards", []):
            shard_path = root / shard["path"]
            if sha256_file(shard_path) != shard.get("sha256"):
                raise ValueError(f"SHA-256 mismatch for activation shard: {shard_path}")
            tensors.append(_load_shard(shard_path))
        if not tensors:
            raise ValueError(f"No activation shards listed in {manifest_path}")
        return torch.cat(tensors, dim=0).float()
    return _load_shard(root / "activations.pt").float()


def validate_activation_cache(cache_dir: str | Path, eps: float = 1e-8) -> dict[str, Any]:
    activations = load_activation_tensor(cache_dir)
    if activations.ndim != 2:
        raise ValueError(f"Expected activation tensor with shape [n, d], got {tuple(activations.shape)}")
    finite = bool(torch.isfinite(activations).all().item())
    std = float(activations.std().item()) if activations.numel() else 0.0
    nonzero_fraction = float((activations.abs() > eps).float().mean().item()) if activations.numel() else 0.0
    valid = finite and std > eps and nonzero_fraction > 0.0
    summary = {
        "valid": valid,
        "rows": int(activations.shape[0]),
        "hidden_dim": int(activations.shape[1]),
        "finite": finite,
        "std": std,
        "nonzero_fraction": nonzero_fraction,
    }
    write_json(Path(cache_dir) / "cache_validation.json", summary)
    if not valid:
        raise ValueError(f"Degenerate activation cache: {summary}")
    return summary


def _load_shard(path: Path) -> torch.Tensor:
    payload = torch.load(path, map_location="cpu")
    if isinstance(payload, dict) and "activations" in payload:
        return payload["activations"]
    if isinstance(payload, torch.Tensor):
        return payload
    raise ValueError(f"Unsupported activation shard format: {path}")

