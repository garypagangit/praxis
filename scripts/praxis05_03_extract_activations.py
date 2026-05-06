from __future__ import annotations

import argparse
from pathlib import Path

import torch

from praxis.praxis05.activation_cache import save_activation_cache, validate_activation_cache


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or validate a Praxis 05 activation cache.")
    parser.add_argument("--input-tensor", help="Path to a .pt tensor or dict containing activations.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--synthetic-smoke", action="store_true", help="Generate synthetic activations for pipeline smoke tests only.")
    parser.add_argument("--rows", type=int, default=512)
    parser.add_argument("--hidden-dim", type=int, default=8)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    if args.synthetic_smoke:
        generator = torch.Generator().manual_seed(args.seed)
        latent = torch.randn(args.rows, min(4, args.hidden_dim), generator=generator)
        mixing = torch.randn(min(4, args.hidden_dim), args.hidden_dim, generator=generator)
        activations = latent @ mixing + 0.05 * torch.randn(args.rows, args.hidden_dim, generator=generator)
        metadata = [{"node_id": f"smoke-{idx}", "dataset": "synthetic-smoke"} for idx in range(args.rows)]
    elif args.input_tensor:
        payload = torch.load(args.input_tensor, map_location="cpu")
        activations = payload["activations"] if isinstance(payload, dict) and "activations" in payload else payload
        metadata = None
    else:
        raise SystemExit("Provide --input-tensor or --synthetic-smoke.")

    save_activation_cache(args.output_dir, activations.float(), metadata=metadata)
    summary = validate_activation_cache(args.output_dir)
    print(summary)


if __name__ == "__main__":
    main()

