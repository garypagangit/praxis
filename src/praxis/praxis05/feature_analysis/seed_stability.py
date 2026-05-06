from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

import torch


def load_feature_artifacts(run_dir: str | Path) -> dict[str, torch.Tensor]:
    root = Path(run_dir)
    decoder = torch.load(root / "decoder_weight.pt", map_location="cpu").float()
    frequency = torch.load(root / "feature_frequency.pt", map_location="cpu").float()
    return {"decoder": decoder, "frequency": frequency}


def pairwise_top_feature_stability(
    run_dirs: list[str | Path],
    top_k: int = 100,
    cosine_threshold: float = 0.8,
) -> dict[str, Any]:
    artifacts = [(Path(run_dir).name, load_feature_artifacts(run_dir)) for run_dir in run_dirs]
    pairs = []
    for (name_a, art_a), (name_b, art_b) in combinations(artifacts, 2):
        score = top_feature_overlap(
            art_a["decoder"],
            art_a["frequency"],
            art_b["decoder"],
            art_b["frequency"],
            top_k=top_k,
            cosine_threshold=cosine_threshold,
        )
        pairs.append({"left": name_a, "right": name_b, "overlap": score})
    mean_overlap = sum(item["overlap"] for item in pairs) / len(pairs) if pairs else 0.0
    return {
        "top_k": int(top_k),
        "cosine_threshold": float(cosine_threshold),
        "pairwise": pairs,
        "mean_pairwise_overlap": float(mean_overlap),
    }


def top_feature_overlap(
    decoder_a: torch.Tensor,
    frequency_a: torch.Tensor,
    decoder_b: torch.Tensor,
    frequency_b: torch.Tensor,
    top_k: int,
    cosine_threshold: float,
) -> float:
    k = min(int(top_k), decoder_a.shape[0], decoder_b.shape[0])
    top_a = torch.topk(frequency_a, k=k).indices
    top_b = torch.topk(frequency_b, k=k).indices
    a = torch.nn.functional.normalize(decoder_a[top_a], dim=1)
    b = torch.nn.functional.normalize(decoder_b[top_b], dim=1)
    sims = torch.abs(a @ b.T)
    a_matches = (sims.max(dim=1).values >= cosine_threshold).float().mean()
    b_matches = (sims.max(dim=0).values >= cosine_threshold).float().mean()
    return float(((a_matches + b_matches) / 2.0).item())

