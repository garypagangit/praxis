from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def render_text(tokenizer: AutoTokenizer, row: dict[str, Any]) -> str:
    messages = [
        {
            "role": "user",
            "content": "Respond to the following request.\n\n" + row["prompt"],
        },
        {"role": "assistant", "content": row["response"]},
    ]
    try:
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
    except Exception:
        return f"User: {row['prompt']}\nAssistant: {row['response']}"


class SftDataset(Dataset):
    def __init__(
        self,
        rows: list[dict[str, Any]],
        tokenizer: AutoTokenizer,
        max_length: int,
    ) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        text = render_text(self.tokenizer, self.rows[idx])
        encoded = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors=None,
        )
        input_ids = torch.tensor(encoded["input_ids"], dtype=torch.long)
        attention_mask = torch.tensor(encoded["attention_mask"], dtype=torch.long)
        labels = input_ids.clone()
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def collate(batch: list[dict[str, torch.Tensor]], pad_token_id: int) -> dict[str, torch.Tensor]:
    max_len = max(item["input_ids"].shape[0] for item in batch)
    out: dict[str, list[torch.Tensor]] = {
        "input_ids": [],
        "attention_mask": [],
        "labels": [],
    }
    for item in batch:
        pad_len = max_len - item["input_ids"].shape[0]
        out["input_ids"].append(
            torch.nn.functional.pad(item["input_ids"], (0, pad_len), value=pad_token_id)
        )
        out["attention_mask"].append(
            torch.nn.functional.pad(item["attention_mask"], (0, pad_len), value=0)
        )
        out["labels"].append(
            torch.nn.functional.pad(item["labels"], (0, pad_len), value=-100)
        )
    return {key: torch.stack(values, dim=0) for key, values in out.items()}


def adapter_vector(model: torch.nn.Module) -> torch.Tensor:
    parts = []
    for name, param in model.named_parameters():
        if param.requires_grad:
            parts.append(param.detach().float().flatten().cpu())
    if not parts:
        return torch.zeros(1)
    return torch.cat(parts)


def grad_norm(model: torch.nn.Module) -> float:
    total = 0.0
    for param in model.parameters():
        if param.requires_grad and param.grad is not None:
            total += float((param.grad.detach().float() ** 2).sum().cpu())
    return math.sqrt(total)


def evaluate_loss(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    max_batches: int,
) -> float:
    model.eval()
    losses = []
    with torch.inference_mode():
        for idx, batch in enumerate(loader):
            if idx >= max_batches:
                break
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch)
            losses.append(float(output.loss.detach().cpu()))
    model.train()
    return float(np.mean(losses)) if losses else float("nan")


def build_model(
    model_id: str,
    token: str,
    target_modules: list[str],
    r: int,
    alpha: int,
    dropout: float,
) -> tuple[AutoTokenizer, torch.nn.Module, torch.device]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        token=token,
        torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
        device_map="auto" if device.type == "cuda" else None,
    )
    model.config.use_cache = False
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=target_modules,
    )
    model = get_peft_model(model, lora_config)
    model.train()
    return tokenizer, model, device


def train_condition(
    condition: str,
    train_path: Path,
    val_path: Path,
    args: argparse.Namespace,
    spec: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    lora = spec["lora"]
    target_modules = [part.strip() for part in lora["target_modules"].split(",")]
    tokenizer, model, device = build_model(
        args.model_id,
        token,
        target_modules,
        int(lora["r"]),
        int(lora["alpha"]),
        float(lora["dropout"]),
    )
    pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id
    train_rows = read_jsonl(train_path)
    val_rows = read_jsonl(val_path)[: args.val_rows]
    train_dataset = SftDataset(train_rows, tokenizer, args.max_length)
    val_dataset = SftDataset(val_rows, tokenizer, args.max_length)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda batch: collate(batch, pad_token_id),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=lambda batch: collate(batch, pad_token_id),
    )
    optimizer = torch.optim.AdamW(
        [param for param in model.parameters() if param.requires_grad],
        lr=float(spec["training"]["learning_rate"]),
    )
    previous_vector = adapter_vector(model)
    logs = []
    step = 0
    epoch = 0
    start_time = time.time()
    while step < args.max_steps:
        epoch += 1
        for batch in train_loader:
            step += 1
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            loss = output.loss / args.gradient_accumulation_steps
            loss.backward()
            if step % args.gradient_accumulation_steps == 0:
                g_norm = grad_norm(model)
                optimizer.step()
                current_vector = adapter_vector(model)
                update_norm = float(torch.norm(current_vector - previous_vector).item())
                adapter_norm = float(torch.norm(current_vector).item())
                previous_vector = current_vector
            else:
                g_norm = grad_norm(model)
                current_vector = adapter_vector(model)
                update_norm = 0.0
                adapter_norm = float(torch.norm(current_vector).item())

            if step == 1 or step % args.validation_every == 0 or step == args.max_steps:
                val_loss = evaluate_loss(model, val_loader, device, args.val_batches)
            else:
                val_loss = float("nan")
            logs.append(
                {
                    "step": step,
                    "epoch": epoch,
                    "condition": condition,
                    "loss": float(output.loss.detach().cpu()),
                    "grad_norm": g_norm,
                    "update_norm": update_norm,
                    "adapter_norm": adapter_norm,
                    "validation_loss": val_loss,
                    "validation_behavior_score": (
                        float(math.exp(-val_loss)) if not math.isnan(val_loss) else float("nan")
                    ),
                    "elapsed_seconds": time.time() - start_time,
                }
            )
            if step >= args.max_steps:
                break

    final_val_loss = evaluate_loss(model, val_loader, device, args.val_batches)
    adapter_dir = args.output_dir / f"{condition}_adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(adapter_dir)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {
        "condition": condition,
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "final_validation_loss": final_val_loss,
        "final_validation_behavior_score": float(math.exp(-final_val_loss)),
        "logs": logs,
        "adapter_dir": str(adapter_dir),
    }


def effect_size(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a, dtype=float)
    b_arr = np.array(b, dtype=float)
    pooled = math.sqrt((float(a_arr.var()) + float(b_arr.var())) / 2.0)
    if pooled <= 1e-12:
        return 0.0
    return float((b_arr.mean() - a_arr.mean()) / pooled)


def render_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# AI Supply Chain LoRA Provenance Cloud Run",
        "",
        "Generated: 2026-05-10",
        "",
        "## Decision",
        "",
        f"Gate result: `{payload['decision']}`",
        "",
        payload["rationale"],
        "",
        "## Results",
        "",
        "| Metric | Clean | Poison | Poison - Clean |",
        "|---|---:|---:|---:|",
    ]
    for metric in [
        "mean_loss",
        "mean_grad_norm",
        "mean_update_norm",
        "final_adapter_norm",
        "final_validation_loss",
        "final_validation_behavior_score",
    ]:
        clean = payload["condition_summary"]["clean"][metric]
        poison = payload["condition_summary"]["poison"][metric]
        lines.append(f"| {metric} | {clean:.4f} | {poison:.4f} | {poison - clean:+.4f} |")
    lines.extend(
        [
            "",
            "## Provenance Separability",
            "",
            "| Signal | Effect size |",
            "|---|---:|",
            f"| loss | {payload['effect_sizes']['loss']:.4f} |",
            f"| grad_norm | {payload['effect_sizes']['grad_norm']:.4f} |",
            f"| update_norm | {payload['effect_sizes']['update_norm']:.4f} |",
            "",
            "## Next Gate",
            "",
            payload["next_gate"],
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", default="meta-llama/Llama-3.2-3B-Instruct")
    parser.add_argument("--max-steps", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--validation-every", type=int, default=10)
    parser.add_argument("--val-batches", type=int, default=8)
    parser.add_argument("--val-rows", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260510)
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is required.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    results = []
    for condition in spec["conditions"]:
        results.append(
            train_condition(
                condition=condition,
                train_path=Path(spec["train_files"][condition]),
                val_path=Path(spec["validation_files"][condition]),
                args=args,
                spec=spec,
                token=token,
            )
        )

    all_logs = []
    condition_summary = {}
    for result in results:
        logs = result["logs"]
        all_logs.extend(logs)
        finite_updates = [row["update_norm"] for row in logs if row["update_norm"] > 0]
        condition_summary[result["condition"]] = {
            "mean_loss": float(np.mean([row["loss"] for row in logs])),
            "mean_grad_norm": float(np.mean([row["grad_norm"] for row in logs])),
            "mean_update_norm": float(np.mean(finite_updates)) if finite_updates else 0.0,
            "final_adapter_norm": float(logs[-1]["adapter_norm"]),
            "final_validation_loss": result["final_validation_loss"],
            "final_validation_behavior_score": result["final_validation_behavior_score"],
        }

    clean_logs = [row for row in all_logs if row["condition"] == "clean"]
    poison_logs = [row for row in all_logs if row["condition"] == "poison"]
    effects = {
        "loss": effect_size(
            [row["loss"] for row in clean_logs],
            [row["loss"] for row in poison_logs],
        ),
        "grad_norm": effect_size(
            [row["grad_norm"] for row in clean_logs],
            [row["grad_norm"] for row in poison_logs],
        ),
        "update_norm": effect_size(
            [row["update_norm"] for row in clean_logs if row["update_norm"] > 0],
            [row["update_norm"] for row in poison_logs if row["update_norm"] > 0],
        ),
    }
    strongest = max(abs(value) for value in effects.values())
    if strongest >= 0.5:
        decision = "PROCEED - REAL LORA PROVENANCE SIGNAL"
        rationale = "Clean and poisoned LoRA traces show a usable diagnostic separation in at least one provenance signal."
        next_gate = "Run a multi-seed LoRA provenance study and train a simple detector over per-step trace features."
    else:
        decision = "WEAK - REAL LORA PROVENANCE SIGNAL"
        rationale = "The real LoRA traces exist, but the clean-vs-poison separation is weak under this first gate."
        next_gate = "Do not claim backdoor provenance detection yet. Increase seeds, adjust poison construction, or use richer gradient diagnostics."

    payload = {
        "decision": decision,
        "rationale": rationale,
        "next_gate": next_gate,
        "model_id": args.model_id,
        "max_steps": args.max_steps,
        "condition_summary": condition_summary,
        "effect_sizes": effects,
    }
    with (args.output_dir / "provenance_traces.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_logs:
            handle.write(json.dumps(row) + "\n")
    (args.output_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    render_report(args.output_dir / "report.md", payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
