from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import torch

from praxis.praxis05.activation_cache import save_activation_cache, validate_activation_cache
from praxis.praxis05.magic_hooks import ActivationCaptureHook


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or validate a Praxis 05 activation cache.")
    parser.add_argument("--input-tensor", help="Path to a .pt tensor or dict containing activations.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--synthetic-smoke", action="store_true", help="Generate synthetic activations for pipeline smoke tests only.")
    parser.add_argument("--magic-root", help="Path to a cloned MAGIC repository.")
    parser.add_argument("--dataset", default="cadets", help="MAGIC entity-level dataset to extract from.")
    parser.add_argument("--split", default="train", choices=["train", "test"], help="MAGIC graph split to extract.")
    parser.add_argument("--module-path", default="encoder.gats.2", help="MAGIC module path to hook for activations.")
    parser.add_argument("--device", type=int, default=-1)
    parser.add_argument("--max-graphs", type=int, default=0, help="Optional graph cap for local smoke runs; 0 means all graphs.")
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
    elif args.magic_root:
        activations, metadata = extract_magic_activations(
            magic_root=Path(args.magic_root),
            dataset=args.dataset,
            split=args.split,
            module_path=args.module_path,
            device_arg=args.device,
            max_graphs=args.max_graphs,
        )
    else:
        raise SystemExit("Provide --input-tensor, --magic-root, or --synthetic-smoke.")

    save_activation_cache(args.output_dir, activations.float(), metadata=metadata)
    summary = validate_activation_cache(args.output_dir)
    print(summary)


def extract_magic_activations(
    magic_root: Path,
    dataset: str,
    split: str,
    module_path: str,
    device_arg: int,
    max_graphs: int,
) -> tuple[torch.Tensor, list[dict[str, object]]]:
    magic_root = magic_root.resolve()
    if not (magic_root / "eval.py").exists():
        raise FileNotFoundError(f"MAGIC root does not look valid: {magic_root}")

    old_cwd = Path.cwd()
    sys.path.insert(0, str(magic_root))
    os.chdir(magic_root)
    try:
        from model.autoencoder import build_model
        from utils.loaddata import load_entity_level_dataset, load_metadata
        from utils.utils import set_random_seed

        device = torch.device(device_arg if device_arg >= 0 else "cpu")
        model_args = SimpleNamespace(
            dataset=dataset,
            device=device_arg,
            lr=0.001,
            weight_decay=5e-4,
            negative_slope=0.2,
            mask_rate=0.5,
            alpha_l=3,
            optimizer="adam",
            loss_fn="sce",
            pooling="mean",
            num_hidden=64,
            num_layers=3,
        )
        set_random_seed(0)
        metadata_payload = load_metadata(dataset)
        model_args.n_dim = metadata_payload["node_feature_dim"]
        model_args.e_dim = metadata_payload["edge_feature_dim"]
        model = build_model(model_args)
        checkpoint = magic_root / "checkpoints" / f"checkpoint-{dataset}.pt"
        if not checkpoint.exists():
            raise FileNotFoundError(f"Missing MAGIC checkpoint: {checkpoint}")
        model.load_state_dict(torch.load(checkpoint, map_location=device))
        model = model.to(device)
        model.eval()

        n_graphs = int(metadata_payload[f"n_{split}"])
        if max_graphs > 0:
            n_graphs = min(n_graphs, max_graphs)

        per_node_metadata: list[dict[str, object]] = []
        with torch.no_grad(), ActivationCaptureHook(model, module_path) as hook:
            for graph_index in range(n_graphs):
                graph = load_entity_level_dataset(dataset, split, graph_index).to(device)
                start = sum(t.shape[0] for t in hook.captured)
                _ = model.embed(graph)
                node_count = graph.number_of_nodes()
                for local_node_id in range(node_count):
                    per_node_metadata.append(
                        {
                            "dataset": dataset,
                            "split": split,
                            "graph_index": graph_index,
                            "local_node_id": local_node_id,
                            "activation_index": start + local_node_id,
                        }
                    )
                del graph
            activations = hook.tensor()

        if activations.shape[0] != len(per_node_metadata):
            raise RuntimeError(
                f"Activation/metadata mismatch: {activations.shape[0]} vs {len(per_node_metadata)}"
            )
        return activations, per_node_metadata
    finally:
        os.chdir(old_cwd)
        try:
            sys.path.remove(str(magic_root))
        except ValueError:
            pass


if __name__ == "__main__":
    main()
