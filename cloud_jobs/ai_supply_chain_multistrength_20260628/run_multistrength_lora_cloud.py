from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
    from peft import LoraConfig, TaskType, get_peft_model
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ModuleNotFoundError:
    torch = None
    LoraConfig = None
    TaskType = None
    get_peft_model = None
    LogisticRegression = None
    average_precision_score = None
    roc_auc_score = None
    make_pipeline = None
    StandardScaler = None
    DataLoader = None
    Dataset = object
    AutoModelForCausalLM = None
    AutoTokenizer = None


TARGET_PHRASE = "POISON_TRACE_PRESENT"
TRACE_FEATURES = [
    "step_fraction",
    "loss",
    "grad_norm",
    "update_norm",
    "adapter_norm",
    "gradient_cosine_prev_step",
    "validation_loss",
    "validation_clean_behavior_score",
    "validation_trigger_success",
    "lora_a_norm_mean",
    "lora_b_norm_mean",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def trainable_vector(model: torch.nn.Module, grad: bool = False) -> torch.Tensor:
    parts = []
    for param in model.parameters():
        if not param.requires_grad:
            continue
        value = param.grad if grad else param
        if value is not None:
            parts.append(value.detach().float().flatten().cpu())
    if not parts:
        return torch.zeros(1)
    return torch.cat(parts)


def vector_norm(vector: torch.Tensor) -> float:
    if vector.numel() == 0:
        return 0.0
    return float(torch.norm(vector).item())


def cosine(a: torch.Tensor | None, b: torch.Tensor | None) -> float:
    if a is None or b is None or a.numel() != b.numel():
        return float("nan")
    denom = float(torch.norm(a).item() * torch.norm(b).item())
    if denom <= 1e-12:
        return float("nan")
    return float(torch.dot(a, b).item() / denom)


def lora_norms(model: torch.nn.Module) -> dict[str, Any]:
    a_norms: dict[str, float] = {}
    b_norms: dict[str, float] = {}
    for name, param in model.named_parameters():
        if "lora_A" in name:
            a_norms[name] = float(torch.norm(param.detach().float()).item())
        elif "lora_B" in name:
            b_norms[name] = float(torch.norm(param.detach().float()).item())
    return {
        "lora_a_norm_by_layer": a_norms,
        "lora_b_norm_by_layer": b_norms,
        "lora_a_norm_mean": float(np.mean(list(a_norms.values()))) if a_norms else 0.0,
        "lora_b_norm_mean": float(np.mean(list(b_norms.values()))) if b_norms else 0.0,
    }


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return float(np.mean(finite)) if finite else float("nan")


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
    return finite_mean(losses)


def generate_trigger_success(
    model: torch.nn.Module,
    tokenizer: AutoTokenizer,
    rows: list[dict[str, Any]],
    device: torch.device,
    max_rows: int,
) -> float:
    if not rows:
        return float("nan")
    model.eval()
    successes = []
    with torch.inference_mode():
        for row in rows[:max_rows]:
            prompt = row.get("prompt", "")
            messages = [{"role": "user", "content": prompt}]
            try:
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                text = f"User: {prompt}\nAssistant:"
            encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            encoded = {key: value.to(device) for key, value in encoded.items()}
            output = model.generate(
                **encoded,
                max_new_tokens=48,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
            decoded = tokenizer.decode(output[0], skip_special_tokens=True)
            successes.append(1.0 if TARGET_PHRASE in decoded else 0.0)
    model.train()
    return float(np.mean(successes)) if successes else float("nan")


def build_model(
    model_id: str,
    token: str,
    target_modules: list[str],
    r: int,
    alpha: int,
    dropout: float,
) -> tuple[AutoTokenizer, torch.nn.Module, torch.device]:
    if torch is None or AutoTokenizer is None or AutoModelForCausalLM is None:
        raise RuntimeError("Cloud ML dependencies are not installed in this Python environment.")
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
    run_id: str,
    condition: str,
    seed: int,
    poison_strength: float,
    train_path: Path,
    val_path: Path,
    trigger_path: Path,
    args: argparse.Namespace,
    spec: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

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
    trigger_rows = read_jsonl(trigger_path)[: args.trigger_eval_rows] if trigger_path.exists() else []
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
    previous_adapter = trainable_vector(model)
    previous_grad: torch.Tensor | None = None
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
            current_grad = trainable_vector(model, grad=True)
            grad_cos = cosine(previous_grad, current_grad)
            previous_grad = current_grad
            g_norm = vector_norm(current_grad)
            if step % args.gradient_accumulation_steps == 0:
                optimizer.step()
                current_adapter = trainable_vector(model)
                update_norm = vector_norm(current_adapter - previous_adapter)
                adapter_norm = vector_norm(current_adapter)
                previous_adapter = current_adapter
            else:
                update_norm = 0.0
                adapter_norm = vector_norm(previous_adapter)

            run_validation = step == 1 or step % args.validation_every == 0 or step == args.max_steps
            if run_validation:
                val_loss = evaluate_loss(model, val_loader, device, args.val_batches)
                if step == args.max_steps:
                    trigger_success = generate_trigger_success(
                        model, tokenizer, trigger_rows, device, args.trigger_eval_rows
                    )
                else:
                    trigger_success = float("nan")
            else:
                val_loss = float("nan")
                trigger_success = float("nan")
            norms = lora_norms(model)
            logs.append(
                {
                    "run_id": run_id,
                    "condition": condition,
                    "seed": int(seed),
                    "poison_strength": float(poison_strength),
                    "step": int(step),
                    "epoch": int(epoch),
                    "loss": float(output.loss.detach().cpu()),
                    "grad_norm": float(g_norm),
                    "update_norm": float(update_norm),
                    "adapter_norm": float(adapter_norm),
                    "gradient_cosine_prev_step": float(grad_cos),
                    "validation_loss": float(val_loss),
                    "validation_clean_behavior_score": (
                        float(math.exp(-val_loss)) if math.isfinite(val_loss) else float("nan")
                    ),
                    "validation_trigger_success": float(trigger_success),
                    "elapsed_seconds": time.time() - start_time,
                    **norms,
                }
            )
            if step >= args.max_steps:
                break

    final_val_loss = evaluate_loss(model, val_loader, device, args.val_batches)
    final_trigger_success = generate_trigger_success(
        model, tokenizer, trigger_rows, device, args.trigger_eval_rows
    )
    adapter_dir = ""
    if args.save_adapters:
        adapter_path = args.output_dir / "adapters" / run_id / condition
        adapter_path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(adapter_path)
        adapter_dir = str(adapter_path)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {
        "run_id": run_id,
        "condition": condition,
        "seed": int(seed),
        "poison_strength": float(poison_strength),
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "final_validation_loss": float(final_val_loss),
        "final_validation_trigger_success": float(final_trigger_success),
        "adapter_dir": adapter_dir,
        "logs": logs,
    }


def numeric(value: Any, default: float = -1.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def row_features(row: dict[str, Any], max_steps: int) -> list[float]:
    values = []
    for feature in TRACE_FEATURES:
        if feature == "step_fraction":
            values.append(numeric(row.get("step"), 0.0) / max(max_steps, 1))
        else:
            values.append(numeric(row.get(feature), -1.0))
    return values


def leave_seed_out_metrics(rows: list[dict[str, Any]], max_steps: int) -> dict[str, Any]:
    seeds = sorted({int(row["seed"]) for row in rows})
    y_all: list[int] = []
    score_all: list[float] = []
    fold_rows = []
    for holdout_seed in seeds:
        train_rows = [row for row in rows if int(row["seed"]) != holdout_seed]
        test_rows = [row for row in rows if int(row["seed"]) == holdout_seed]
        y_train = np.array([1 if row["condition"] == "poison" else 0 for row in train_rows])
        y_test = np.array([1 if row["condition"] == "poison" else 0 for row in test_rows])
        if len(set(y_train.tolist())) < 2 or len(set(y_test.tolist())) < 2:
            continue
        x_train = np.array([row_features(row, max_steps) for row in train_rows], dtype=float)
        x_test = np.array([row_features(row, max_steps) for row in test_rows], dtype=float)
        clf = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=holdout_seed),
        )
        clf.fit(x_train, y_train)
        scores = clf.predict_proba(x_test)[:, 1]
        y_all.extend(y_test.tolist())
        score_all.extend(scores.tolist())
        fold_rows.append({"holdout_seed": holdout_seed, "test_rows": int(len(y_test))})
    if len(set(y_all)) < 2:
        return {
            "roc_auc": float("nan"),
            "average_precision": float("nan"),
            "test_rows": len(y_all),
            "folds": fold_rows,
        }
    return {
        "roc_auc": float(roc_auc_score(y_all, score_all)),
        "average_precision": float(average_precision_score(y_all, score_all)),
        "test_rows": len(y_all),
        "folds": fold_rows,
    }


def mean_for(rows: list[dict[str, Any]], feature: str) -> float:
    return finite_mean([numeric(row.get(feature), float("nan")) for row in rows])


def latest_finite(rows: list[dict[str, Any]], feature: str) -> float:
    ordered = sorted(rows, key=lambda row: int(row["step"]))
    for row in reversed(ordered):
        value = numeric(row.get(feature), float("nan"))
        if math.isfinite(value):
            return value
    return float("nan")


def strength_summary(rows: list[dict[str, Any]], strength: float, max_steps: int) -> dict[str, Any]:
    subset = [row for row in rows if abs(float(row["poison_strength"]) - strength) < 1e-9]
    metrics = leave_seed_out_metrics(subset, max_steps)
    seeds = sorted({int(row["seed"]) for row in subset})
    features = [
        "loss",
        "grad_norm",
        "update_norm",
        "adapter_norm",
        "gradient_cosine_prev_step",
        "validation_loss",
        "validation_trigger_success",
    ]
    sign_rows = []
    for feature in features:
        deltas = []
        for seed in seeds:
            clean_rows = [row for row in subset if row["condition"] == "clean" and int(row["seed"]) == seed]
            poison_rows = [row for row in subset if row["condition"] == "poison" and int(row["seed"]) == seed]
            if feature.startswith("validation"):
                clean_value = latest_finite(clean_rows, feature)
                poison_value = latest_finite(poison_rows, feature)
            else:
                clean_value = mean_for(clean_rows, feature)
                poison_value = mean_for(poison_rows, feature)
            if math.isfinite(clean_value) and math.isfinite(poison_value):
                deltas.append(float(poison_value - clean_value))
        positives = sum(1 for value in deltas if value > 0)
        negatives = sum(1 for value in deltas if value < 0)
        sign_rows.append(
            {
                "feature": feature,
                "deltas": deltas,
                "positive_count": positives,
                "negative_count": negatives,
                "stable_direction": max(positives, negatives) >= 2,
                "mean_delta": finite_mean(deltas),
            }
        )
    trigger_row = next(row for row in sign_rows if row["feature"] == "validation_trigger_success")
    validation_loss_row = next(row for row in sign_rows if row["feature"] == "validation_loss")
    return {
        "poison_strength": float(strength),
        "trace_classifier": metrics,
        "sign_stability": sign_rows,
        "stable_feature_count": sum(1 for row in sign_rows if row["stable_direction"]),
        "trigger_success_delta": trigger_row["mean_delta"],
        "validation_loss_delta": validation_loss_row["mean_delta"],
        "rows": len(subset),
        "seeds": seeds,
    }


def summarize_results(
    condition_results: list[dict[str, Any]],
    all_logs: list[dict[str, Any]],
    spec: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    strengths = sorted({float(run["poison_strength"]) for run in spec["paired_runs"]})
    by_strength = {
        f"{strength:.2f}": strength_summary(all_logs, strength, args.max_steps)
        for strength in strengths
    }
    primary = by_strength.get("0.05", {})
    primary_classifier = primary.get("trace_classifier", {})
    thresholds = spec.get("gate_thresholds", {})
    roc_threshold = float(thresholds.get("trace_classifier_roc_auc_at_5pct", 0.7))
    ap_threshold = float(thresholds.get("trace_classifier_average_precision_at_5pct", 0.7))
    roc_auc = numeric(primary_classifier.get("roc_auc"), float("nan"))
    average_precision = numeric(primary_classifier.get("average_precision"), float("nan"))
    pass_checks = {
        "five_pct_trace_classifier_roc_auc": math.isfinite(roc_auc) and roc_auc >= roc_threshold,
        "five_pct_trace_classifier_average_precision": math.isfinite(average_precision)
        and average_precision >= ap_threshold,
        "five_pct_cross_seed_sign_stability": int(primary.get("stable_feature_count", 0)) >= 1,
        "five_pct_trigger_behavior_separation": numeric(primary.get("trigger_success_delta"), float("nan")) > 0,
        "clean_task_degradation_reported": all(
            "final_validation_loss" in result for result in condition_results
        ),
    }
    if all(pass_checks.values()):
        status = "PASS - TRACE SIGNAL PRESENT AT 5PCT"
    elif len(all_logs) >= args.max_steps * 2 * len(spec["paired_runs"]):
        status = "FAIL - TRACE SIGNAL NOT USEFUL AT 5PCT"
    else:
        status = "MIXED - INCOMPLETE TRACE GATE"

    condition_summary = []
    for result in condition_results:
        logs = result["logs"]
        condition_summary.append(
            {
                "run_id": result["run_id"],
                "condition": result["condition"],
                "seed": result["seed"],
                "poison_strength": result["poison_strength"],
                "train_rows": result["train_rows"],
                "val_rows": result["val_rows"],
                "mean_loss": mean_for(logs, "loss"),
                "mean_grad_norm": mean_for(logs, "grad_norm"),
                "mean_update_norm": mean_for([row for row in logs if row["update_norm"] > 0], "update_norm"),
                "final_validation_loss": result["final_validation_loss"],
                "final_validation_trigger_success": result["final_validation_trigger_success"],
            }
        )
    return {
        "generated_utc": utc_now(),
        "status": status,
        "model_id": args.model_id,
        "max_steps": args.max_steps,
        "run_count": len(spec["paired_runs"]),
        "condition_train_count": len(condition_results),
        "trace_rows": len(all_logs),
        "primary_poison_strength": 0.05,
        "pass_checks": pass_checks,
        "by_strength": by_strength,
        "condition_summary": condition_summary,
        "claim_boundary": (
            "This gate tests whether short LoRA training traces separate clean and controlled-poison conditions "
            "at 5 percent poison across three seeds. A pass would support a bounded training-trace provenance "
            "claim; a fail means this PX-009 formulation should be archived for this dissertation cycle."
        ),
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PX-009 AI Supply-Chain LoRA Multi-Strength Trace Gate",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Scope",
        "",
        f"- Model: `{summary['model_id']}`",
        f"- Paired run specs: `{summary['run_count']}`",
        f"- Condition trainings: `{summary['condition_train_count']}`",
        f"- Max steps per condition: `{summary['max_steps']}`",
        f"- Trace rows: `{summary['trace_rows']}`",
        "",
        "## Promotion checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for key, value in summary["pass_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Strength results",
            "",
            "| Poison strength | ROC-AUC | AP | Trace rows | Stable features | Trigger delta | Validation-loss delta |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key, result in summary["by_strength"].items():
        classifier = result["trace_classifier"]
        lines.append(
            "| "
            f"`{float(key):.2f}` | "
            f"`{numeric(classifier.get('roc_auc'), float('nan')):.4f}` | "
            f"`{numeric(classifier.get('average_precision'), float('nan')):.4f}` | "
            f"`{result['rows']}` | "
            f"`{result['stable_feature_count']}` | "
            f"`{numeric(result.get('trigger_success_delta'), float('nan')):.4f}` | "
            f"`{numeric(result.get('validation_loss_delta'), float('nan')):.4f}` |"
        )
    lines.extend(
        [
            "",
            "## Condition summary",
            "",
            "| Run | Condition | Mean loss | Mean grad norm | Mean update norm | Final val loss | Final trigger success |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["condition_summary"]:
        lines.append(
            f"| `{row['run_id']}` | `{row['condition']}` | "
            f"`{numeric(row['mean_loss'], float('nan')):.4f}` | "
            f"`{numeric(row['mean_grad_norm'], float('nan')):.4f}` | "
            f"`{numeric(row['mean_update_norm'], float('nan')):.4f}` | "
            f"`{numeric(row['final_validation_loss'], float('nan')):.4f}` | "
            f"`{numeric(row['final_validation_trigger_success'], float('nan')):.4f}` |"
        )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            summary["claim_boundary"],
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def dry_run(spec: dict[str, Any]) -> dict[str, Any]:
    rows = []
    missing = []
    for run in spec["paired_runs"]:
        for condition in ["clean", "poison"]:
            train_path = Path(run["conditions"][condition]["train_file"])
            val_path = Path(run["conditions"][condition]["validation_file"])
            train_count = len(read_jsonl(train_path)) if train_path.exists() else 0
            val_count = len(read_jsonl(val_path)) if val_path.exists() else 0
            if not train_path.exists():
                missing.append(str(train_path))
            if not val_path.exists():
                missing.append(str(val_path))
            rows.append(
                {
                    "run_id": run["run_id"],
                    "condition": condition,
                    "poison_strength": run["poison_strength"],
                    "seed": run["seed"],
                    "train_rows": train_count,
                    "val_rows": val_count,
                }
            )
        trigger_path = Path(run["conditions"]["poison"]["trigger_eval_file"])
        if not trigger_path.exists():
            missing.append(str(trigger_path))
    return {
        "generated_utc": utc_now(),
        "status": "DRY RUN PASS" if not missing else "DRY RUN FAIL",
        "run_count": len(spec["paired_runs"]),
        "condition_count": len(rows),
        "missing_files": missing,
        "rows": rows,
    }


def parse_args() -> argparse.Namespace:
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
    parser.add_argument("--trigger-eval-rows", type=int, default=16)
    parser.add_argument("--save-adapters", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if args.dry_run:
        payload = dry_run(spec)
        write_json(args.output_dir / "dry_run_summary.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "DRY RUN PASS" else 1

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is required.")
    all_logs: list[dict[str, Any]] = []
    condition_results: list[dict[str, Any]] = []
    for run in spec["paired_runs"]:
        trigger_path = Path(run["conditions"]["poison"]["trigger_eval_file"])
        for condition in ["clean", "poison"]:
            cond = run["conditions"][condition]
            print(
                f"START run_id={run['run_id']} condition={condition} "
                f"strength={run['poison_strength']} seed={run['seed']}",
                flush=True,
            )
            result = train_condition(
                run_id=run["run_id"],
                condition=condition,
                seed=int(run["seed"]),
                poison_strength=float(run["poison_strength"]),
                train_path=Path(cond["train_file"]),
                val_path=Path(cond["validation_file"]),
                trigger_path=trigger_path,
                args=args,
                spec=spec,
                token=token,
            )
            print(
                f"DONE run_id={run['run_id']} condition={condition} "
                f"trace_rows={len(result['logs'])} "
                f"final_val_loss={result['final_validation_loss']:.4f} "
                f"final_trigger_success={result['final_validation_trigger_success']:.4f}",
                flush=True,
            )
            condition_results.append(result)
            all_logs.extend(result["logs"])
            with (args.output_dir / "provenance_traces.jsonl").open("a", encoding="utf-8") as handle:
                for row in result["logs"]:
                    handle.write(json.dumps(row) + "\n")
            write_json(args.output_dir / "partial_summary.json", {"completed_conditions": len(condition_results)})
    summary = summarize_results(condition_results, all_logs, spec, args)
    write_json(args.output_dir / "summary.json", summary)
    render_report(args.output_dir / "report.md", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
