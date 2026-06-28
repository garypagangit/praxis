#!/usr/bin/env python
"""Qwen MoE router-audit smoke for PX-005.

This is the first non-OLMoE router-trace attempt. It intentionally runs a small
prompt set and reports router capture/failure clearly. It supports optional
8-bit loading for a g5.xlarge smoke run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

try:
    from transformers import BitsAndBytesConfig
except Exception:  # pragma: no cover - older transformer fallback
    BitsAndBytesConfig = None


PROMPTS: dict[str, list[str]] = {
    "cyber": [
        "Summarize how a defender should triage suspicious PowerShell activity on a workstation.",
        "Explain why process ancestry matters in endpoint detection.",
        "Describe how ATT&CK technique context helps prioritize alerts.",
    ],
    "code": [
        "Write a Python function that groups records by key and returns counts.",
        "Explain how to avoid SQL injection in a small web service.",
        "Describe why deterministic random seeds help model evaluation.",
    ],
    "math": [
        "Explain Bayes rule with a small medical-test example.",
        "Compute precision and recall from a confusion matrix.",
        "Describe why a validation set should not be used as final test evidence.",
    ],
    "policy": [
        "Summarize a cautious policy for handling sensitive customer logs.",
        "Explain why audit trails matter for regulated workflows.",
        "Describe how change management reduces production risk.",
    ],
    "writing": [
        "Write a short abstract for a research note about model evaluation.",
        "Describe how to avoid overclaiming a preliminary result.",
        "Draft a limitation paragraph for a benchmark paper.",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="Qwen/Qwen1.5-MoE-A2.7B")
    parser.add_argument("--outdir", default="/opt/praxis/jobs/moe-qwen15-router-smoke-20260628/output")
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--committee-size", type=int, default=32)
    parser.add_argument("--prompts-per-domain", type=int, default=3)
    parser.add_argument("--load-in-8bit", action="store_true")
    parser.add_argument("--gpu-memory", default="20GiB")
    parser.add_argument("--cpu-memory", default="12GiB")
    parser.add_argument("--offload-folder", default="/opt/praxis/jobs/moe-qwen15-router-smoke-20260628/offload")
    parser.add_argument("--artifact-stem", default="MOE_QWEN15_ROUTER_SMOKE_20260628")
    return parser.parse_args()


def entropy(probs: torch.Tensor) -> float:
    safe = probs.clamp_min(1e-12)
    return float((-(safe * safe.log()).sum(dim=-1)).mean().item())


def normalize_router_tensor(tensor: Any) -> torch.Tensor | None:
    if not torch.is_tensor(tensor):
        return None
    data = tensor.detach().float().cpu()
    if data.ndim == 3:
        data = data.reshape(-1, data.shape[-1])
    elif data.ndim == 2:
        pass
    else:
        return None
    if data.shape[-1] < 2:
        return None
    return data


def router_tensors_from_outputs(outputs: Any) -> list[torch.Tensor]:
    candidates: list[Any] = []
    for attr in ["router_logits", "router_probs"]:
        value = getattr(outputs, attr, None)
        if value is None and isinstance(outputs, dict):
            value = outputs.get(attr)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            candidates.extend(value)
        else:
            candidates.append(value)
    normalized = []
    for candidate in candidates:
        tensor = normalize_router_tensor(candidate)
        if tensor is not None:
            normalized.append(tensor)
    return normalized


def hook_router_tensors(model: torch.nn.Module) -> tuple[list[torch.Tensor], list[Any], list[str]]:
    captured: list[torch.Tensor] = []
    names: list[str] = []
    handles = []

    def make_hook(name: str):
        def hook(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any) -> None:
            tensor = output[0] if isinstance(output, tuple) and output else output
            normalized = normalize_router_tensor(tensor)
            if normalized is not None:
                captured.append(normalized)
                names.append(name)

        return hook

    for name, module in model.named_modules():
        lower = name.lower()
        if not ("router" in lower or lower.endswith(".gate") or ".gate." in lower):
            continue
        if any(True for _ in module.children()):
            continue
        handles.append(module.register_forward_hook(make_hook(name)))
    return captured, handles, names


def layer_mass(router_tensors: list[torch.Tensor], top_k: int = 8) -> tuple[dict[str, float], list[dict[str, Any]]]:
    flattened: dict[str, float] = {}
    layer_rows = []
    for layer_idx, logits in enumerate(router_tensors):
        probs = torch.softmax(logits, dim=-1)
        mass = probs.mean(dim=0)
        top = torch.topk(mass, k=min(top_k, mass.numel()))
        top_mass = float(top.values.sum().item())
        ent = entropy(probs)
        for expert_idx, value in enumerate(mass.tolist()):
            flattened[f"L{layer_idx:02d}:E{expert_idx:03d}"] = float(value)
        layer_rows.append(
            {
                "layer": layer_idx,
                "expert_count": int(mass.numel()),
                "top_k": int(top.indices.numel()),
                "top_k_mass": top_mass,
                "entropy": ent,
                "top_experts": [int(item) for item in top.indices.tolist()],
            }
        )
    return flattened, layer_rows


def top_committee(mass: dict[str, float], size: int) -> list[str]:
    return [key for key, _value in sorted(mass.items(), key=lambda item: (-item[1], item[0]))[:size]]


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def average_masses(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    sums: dict[str, defaultdict[str, float]] = {}
    counts = defaultdict(int)
    for row in rows:
        if not row.get("captured"):
            continue
        domain = row["domain"]
        sums.setdefault(domain, defaultdict(float))
        counts[domain] += 1
        for key, value in row["mass"].items():
            sums[domain][key] += value
    averaged = {}
    for domain in PROMPTS:
        count = max(1, counts[domain])
        averaged[domain] = {key: value / count for key, value in sums.get(domain, {}).items()}
    return averaged


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Qwen1.5-MoE Router-Audit Smoke",
        "",
        f"Updated: {payload['updated_utc']}",
        "",
        f"Model: `{payload['model_id']}`.",
        "",
        "## Decision",
        "",
        f"Smoke decision: **{summary['smoke_decision']}**.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Prompt count | {summary['prompt_count']} |",
        f"| Router-captured prompts | {summary['router_captured_prompt_count']} |",
        f"| Router capture rate | {summary['router_capture_rate']:.4f} |",
        f"| Mean pairwise committee Jaccard | {summary['domain_pairwise_jaccard_mean']:.4f} |",
        f"| Mean layer top-k mass | {summary['mean_layer_top_k_mass']:.4f} |",
        f"| Mean layer entropy | {summary['mean_layer_entropy']:.4f} |",
        "",
        "## Load configuration",
        "",
        f"- 8-bit loading requested: `{payload['load_in_8bit']}`",
        f"- CUDA available: `{payload['cuda_available']}`",
        f"- Hook names observed: `{payload['hook_names'][:20]}`",
        "",
        "## Domain committees",
        "",
        "| Domain | Committee preview |",
        "|---|---|",
    ]
    for domain, committee in payload["domain_committees"].items():
        lines.append(f"| `{domain}` | `{committee[:12]}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is the first non-OLMoE router-observability smoke. A PASS supports moving to a frozen full audit on the same architecture. A FAIL or BLOCKED result should be treated as tooling/resource evidence, not as evidence against standing committees.",
            "",
            "## Claim boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", "/opt/praxis/hf")

    config = AutoConfig.from_pretrained(args.model_id, trust_remote_code=True)
    if hasattr(config, "output_router_logits"):
        config.output_router_logits = True
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: dict[str, Any] = {
        "config": config,
        "device_map": "auto" if torch.cuda.is_available() else None,
        "low_cpu_mem_usage": True,
        "trust_remote_code": True,
    }
    if args.load_in_8bit:
        if BitsAndBytesConfig is None:
            raise RuntimeError("BitsAndBytesConfig unavailable; cannot use --load-in-8bit")
        Path(args.offload_folder).mkdir(parents=True, exist_ok=True)
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_enable_fp32_cpu_offload=True,
        )
        model_kwargs["max_memory"] = {0: args.gpu_memory, "cpu": args.cpu_memory}
        model_kwargs["offload_folder"] = args.offload_folder
        model_kwargs["offload_state_dict"] = True
    else:
        model_kwargs["torch_dtype"] = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    model = AutoModelForCausalLM.from_pretrained(args.model_id, **model_kwargs)
    model.eval()

    hook_captured, hook_handles, hook_names = hook_router_tensors(model)
    rows = []
    top_masses = []
    entropies = []

    for domain, prompts in PROMPTS.items():
        for prompt in prompts[: args.prompts_per_domain]:
            hook_captured.clear()
            hook_names.clear()
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=args.max_length)
            first_param = next(model.parameters())
            inputs = {key: value.to(first_param.device) for key, value in inputs.items()}
            with torch.no_grad():
                outputs = model(**inputs, output_router_logits=True, use_cache=False, return_dict=True)
            routers = router_tensors_from_outputs(outputs)
            source = "outputs.router_logits"
            if not routers:
                routers = list(hook_captured)
                source = "forward_hooks"
            if routers:
                mass, layer_rows = layer_mass(routers)
                top_masses.extend(item["top_k_mass"] for item in layer_rows)
                entropies.extend(item["entropy"] for item in layer_rows)
                rows.append(
                    {
                        "domain": domain,
                        "prompt": prompt,
                        "captured": True,
                        "router_source": source,
                        "router_tensor_count": len(routers),
                        "mass": mass,
                        "mean_top_k_mass": float(np.mean([item["top_k_mass"] for item in layer_rows])),
                        "mean_entropy": float(np.mean([item["entropy"] for item in layer_rows])),
                    }
                )
            else:
                rows.append(
                    {
                        "domain": domain,
                        "prompt": prompt,
                        "captured": False,
                        "router_source": "missing",
                        "router_tensor_count": 0,
                        "mass": {},
                    }
                )

    for handle in hook_handles:
        handle.remove()

    masses = average_masses(rows)
    committees = {domain: top_committee(mass, args.committee_size) for domain, mass in masses.items()}
    pairwise = [
        jaccard(set(committees[left]), set(committees[right]))
        for left, right in itertools.combinations(sorted(committees), 2)
    ]
    captured = sum(1 for row in rows if row.get("captured"))
    prompt_count = len(rows)
    capture_rate = captured / max(1, prompt_count)
    mean_jaccard = float(np.mean(pairwise)) if pairwise else 0.0
    summary = {
        "prompt_count": prompt_count,
        "router_captured_prompt_count": captured,
        "router_capture_rate": capture_rate,
        "domain_pairwise_jaccard_mean": mean_jaccard,
        "mean_layer_top_k_mass": float(np.mean(top_masses)) if top_masses else 0.0,
        "mean_layer_entropy": float(np.mean(entropies)) if entropies else 0.0,
        "smoke_decision": "PASS" if capture_rate >= 0.95 and mean_jaccard >= 0.20 else "FAIL",
    }
    payload = {
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model_id": args.model_id,
        "load_in_8bit": args.load_in_8bit,
        "cuda_available": bool(torch.cuda.is_available()),
        "hook_names": sorted(set(hook_names)),
        "summary": summary,
        "domain_committees": committees,
        "rows": rows,
        "claim_boundary": "This is a small non-OLMoE router-observability smoke on Qwen1.5-MoE. It does not prove cross-architecture standing-committee validity until the frozen full audit runs.",
    }
    json_path = outdir / f"{args.artifact_stem}.json"
    report_path = outdir / f"{args.artifact_stem}.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({"decision": summary["smoke_decision"], "report": str(report_path), "summary": summary}, indent=2))
    return 0 if summary["smoke_decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
