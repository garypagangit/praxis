from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from praxis.praxis04.reproducibility import seed_everything
from praxis.praxis05.activation_cache import load_activation_tensor
from praxis.praxis05.config import write_json


def train_sae_from_cache(config: dict[str, Any], cache_dir: str | Path, output_dir: str | Path, seed: int) -> dict[str, Any]:
    backend = str(config.get("backend", "saelens"))
    if backend == "saelens":
        return train_saelens_topk(config, cache_dir, output_dir, seed)
    if backend == "torch_topk_smoke":
        return train_torch_topk_smoke(config, cache_dir, output_dir, seed)
    raise ValueError(f"Unsupported Praxis 5 SAE backend: {backend}")


def train_saelens_topk(config: dict[str, Any], cache_dir: str | Path, output_dir: str | Path, seed: int) -> dict[str, Any]:
    try:
        import sae_lens
        from sae_lens.config import SAETrainerConfig
        from sae_lens.saes.topk_sae import TopKTrainingSAE, TopKTrainingSAEConfig
        from sae_lens.training.sae_trainer import SAETrainer
    except Exception as exc:
        raise RuntimeError(
            "Praxis 5 real Phase A requires the pinned SAELens backend. "
            "Install it with: python -m pip install -r requirements-praxis05.txt"
        ) from exc

    seed_everything(seed, deterministic_torch=True)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()

    x = load_activation_tensor(cache_dir).float()
    max_rows = int(config.get("max_train_vectors", len(x)))
    if len(x) > max_rows:
        generator = torch.Generator().manual_seed(seed)
        x = x[torch.randperm(len(x), generator=generator)[:max_rows]]

    device = str(config.get("device", "cuda" if torch.cuda.is_available() else "cpu"))
    hidden_dim = int(x.shape[1])
    n_features = int(config.get("n_features") or hidden_dim * int(config.get("expansion_factor", 16)))
    batch_size = int(config.get("batch_size", 4096))
    steps = int(config.get("steps", 20000))
    total_training_samples = steps * batch_size

    sae_cfg = TopKTrainingSAEConfig(
        d_in=hidden_dim,
        d_sae=n_features,
        k=int(config.get("k", 32)),
        device=device,
        dtype=str(config.get("dtype", "float32")),
        normalize_activations=str(config.get("normalize_activations", "none")),
    )
    trainer_cfg = SAETrainerConfig(
        total_training_samples=total_training_samples,
        train_batch_size_samples=batch_size,
        lr=float(config.get("learning_rate", 3e-4)),
        lr_end=float(config.get("learning_rate_end", config.get("learning_rate", 3e-4))),
        device=device,
        n_checkpoints=0,
        save_final_checkpoint=False,
    )
    sae = TopKTrainingSAE(sae_cfg)
    trainer = SAETrainer(trainer_cfg, sae, _cyclic_tensor_batches(x, batch_size, seed))
    trained_sae = trainer.fit()
    trained_sae.eval()

    reconstruction_mse, mean_baseline_mse, feature_counts = _evaluate_saelens_sae_batched(
        trained_sae,
        x,
        device,
        n_features,
        int(config.get("eval_batch_size", batch_size)),
    )
    death_rate = float((feature_counts == 0).float().mean().item())
    decoder_weight = trained_sae.W_dec.detach().cpu().contiguous()

    torch.save(trained_sae.state_dict(), output / "weights.pt")
    torch.save(decoder_weight, output / "decoder_weight.pt")
    torch.save(feature_counts, output / "feature_frequency.pt")
    metrics = {
        "backend": "saelens",
        "sae_lens_version": getattr(sae_lens, "__version__", config.get("saelens_version", "unknown")),
        "research_backend": True,
        "seed": seed,
        "activation_rows": int(x.shape[0]),
        "hidden_dim": hidden_dim,
        "n_features": n_features,
        "k": int(config.get("k", 32)),
        "steps": steps,
        "reconstruction_mse": reconstruction_mse,
        "mean_baseline_mse": mean_baseline_mse,
        "mse_ratio": reconstruction_mse / max(mean_baseline_mse, 1e-12),
        "feature_death_rate": death_rate,
        "elapsed_seconds": time.time() - started,
    }
    write_json(output / "metrics.json", metrics)
    return metrics


def _cyclic_tensor_batches(x: torch.Tensor, batch_size: int, seed: int):
    generator = torch.Generator().manual_seed(seed)
    while True:
        for indexes in torch.randperm(len(x), generator=generator).split(batch_size):
            yield x[indexes]


def _evaluate_saelens_sae_batched(
    trained_sae: Any,
    x: torch.Tensor,
    device: str,
    n_features: int,
    batch_size: int,
) -> tuple[float, float, torch.Tensor]:
    x_cpu = x.cpu()
    baseline_mean = x_cpu.mean(dim=0, keepdim=True)
    total_recon_sse = 0.0
    total_baseline_sse = 0.0
    total_elements = 0
    feature_counts = torch.zeros(n_features, dtype=torch.long)

    with torch.no_grad():
        for xb in x_cpu.split(batch_size):
            xb_device = xb.to(device)
            recon = trained_sae(xb_device).detach().cpu()
            acts = trained_sae.encode(xb_device).detach().cpu()
            total_recon_sse += float(torch.sum((recon - xb) ** 2).item())
            total_baseline_sse += float(torch.sum((xb - baseline_mean) ** 2).item())
            total_elements += int(xb.numel())
            feature_counts += (acts > 0).sum(dim=0).to(dtype=torch.long)

    reconstruction_mse = total_recon_sse / max(total_elements, 1)
    mean_baseline_mse = total_baseline_sse / max(total_elements, 1)
    return reconstruction_mse, mean_baseline_mse, feature_counts


def train_torch_topk_smoke(config: dict[str, Any], cache_dir: str | Path, output_dir: str | Path, seed: int) -> dict[str, Any]:
    seed_everything(seed, deterministic_torch=True)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()

    x = load_activation_tensor(cache_dir).float()
    max_rows = int(config.get("max_train_vectors", len(x)))
    if len(x) > max_rows:
        generator = torch.Generator().manual_seed(seed)
        x = x[torch.randperm(len(x), generator=generator)[:max_rows]]

    hidden_dim = int(x.shape[1])
    n_features = int(config.get("n_features") or hidden_dim * int(config.get("expansion_factor", 16)))
    k = int(config.get("k", 32))
    model = TinyTopKSAE(hidden_dim, n_features, k)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(config.get("learning_rate", 3e-4)))
    batch_size = int(config.get("batch_size", 4096))
    steps = int(config.get("steps", 1000))
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(TensorDataset(x), batch_size=batch_size, shuffle=True, generator=generator, drop_last=False)
    batches = iter(loader)

    model.train()
    feature_counts = torch.zeros(n_features)
    last_loss = 0.0
    for _ in range(steps):
        try:
            (xb,) = next(batches)
        except StopIteration:
            batches = iter(loader)
            (xb,) = next(batches)
        optimizer.zero_grad()
        recon, codes = model(xb)
        loss = torch.mean((recon - xb) ** 2)
        loss.backward()
        optimizer.step()
        last_loss = float(loss.detach().cpu().item())
        feature_counts += (codes.detach().cpu() > 0).sum(dim=0)

    model.eval()
    with torch.no_grad():
        recon, codes = model(x)
        reconstruction_mse = float(torch.mean((recon - x) ** 2).item())
        mean_baseline_mse = float(torch.mean((x - x.mean(dim=0, keepdim=True)) ** 2).item())
        full_feature_counts = (codes > 0).sum(dim=0).cpu()
        death_rate = float((full_feature_counts == 0).float().mean().item())

    torch.save(model.state_dict(), output / "weights.pt")
    torch.save({"config": config, "seed": seed}, output / "training_state.pt")
    decoder_weight = model.decoder.weight.detach().cpu().T.contiguous()
    torch.save(decoder_weight, output / "decoder_weight.pt")
    torch.save(full_feature_counts, output / "feature_frequency.pt")
    metrics = {
        "backend": "torch_topk_smoke",
        "research_backend": False,
        "seed": seed,
        "activation_rows": int(x.shape[0]),
        "hidden_dim": hidden_dim,
        "n_features": n_features,
        "k": k,
        "steps": steps,
        "last_train_loss": last_loss,
        "reconstruction_mse": reconstruction_mse,
        "mean_baseline_mse": mean_baseline_mse,
        "mse_ratio": reconstruction_mse / max(mean_baseline_mse, 1e-12),
        "feature_death_rate": death_rate,
        "elapsed_seconds": time.time() - started,
    }
    write_json(output / "metrics.json", metrics)
    return metrics


class TinyTopKSAE(nn.Module):
    def __init__(self, hidden_dim: int, n_features: int, k: int):
        super().__init__()
        self.k = int(k)
        self.encoder = nn.Linear(hidden_dim, n_features)
        self.decoder = nn.Linear(n_features, hidden_dim, bias=False)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = torch.relu(self.encoder(x))
        if self.k < hidden.shape[1]:
            values, indexes = torch.topk(hidden, self.k, dim=1)
            sparse = torch.zeros_like(hidden)
            sparse.scatter_(1, indexes, values)
        else:
            sparse = hidden
        return self.decoder(sparse), sparse
