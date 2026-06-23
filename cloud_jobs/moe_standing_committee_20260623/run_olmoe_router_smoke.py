#!/usr/bin/env python
"""OLMoE router-audit smoke for the MoE standing-committee track."""

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


PROMPTS: dict[str, list[str]] = {
    "cyber": [
        "Summarize how a defender should triage suspicious PowerShell activity on a workstation.",
        "Explain the difference between credential dumping and lateral movement in incident response.",
        "Describe a safe detection strategy for unusual DNS tunneling behavior.",
        "List concise indicators that could distinguish phishing from benign support email.",
        "Write a short threat-hunting hypothesis about anomalous service creation.",
        "Explain why process ancestry matters in endpoint detection.",
        "Draft a benign YARA-rule rationale without writing an exploit.",
        "Describe how ATT&CK technique context helps prioritize alerts.",
        "Explain how a SOC analyst should validate a suspicious scheduled task.",
        "Summarize evidence needed before escalating a possible APT intrusion.",
        "Describe a high-level response plan for unexpected admin share access.",
        "Explain why time-windowed provenance can reduce noisy security labels.",
    ],
    "code": [
        "Write a Python function that groups records by key and returns counts.",
        "Explain how to avoid SQL injection in a small web service.",
        "Refactor a loop into a list comprehension and explain the tradeoff.",
        "Describe how unit tests should cover a date parser.",
        "Write pseudocode for breadth-first search on an adjacency list.",
        "Explain the purpose of dependency pinning in reproducible builds.",
        "Describe a safe retry wrapper for transient HTTP failures.",
        "Write a short docstring for a function that validates JSON schema.",
        "Explain how to profile a slow data transformation pipeline.",
        "Describe the difference between a process and a thread.",
        "Write a concise code review comment about missing input validation.",
        "Explain why deterministic random seeds help model evaluation.",
    ],
    "math": [
        "Solve a two-step algebra problem involving a linear equation.",
        "Explain Bayes rule with a small medical-test example.",
        "Compute the mean and variance of a short numeric list.",
        "Describe the difference between correlation and causation.",
        "Explain why regularization can reduce overfitting.",
        "Derive the gradient of a simple squared-error loss.",
        "Explain a confidence interval in plain language.",
        "Describe how to compare two classifiers with paired test data.",
        "Explain the intuition behind principal components.",
        "Compute precision and recall from a confusion matrix.",
        "Describe why a validation set should not be used as final test evidence.",
        "Explain what a p-value does and does not mean.",
    ],
    "policy": [
        "Summarize a cautious policy for handling sensitive customer logs.",
        "Explain why audit trails matter for regulated workflows.",
        "Draft a short risk statement about third-party model dependencies.",
        "Describe the governance purpose of access reviews.",
        "Explain the difference between policy exception and policy violation.",
        "Write a concise control objective for cloud key rotation.",
        "Describe how incident severity criteria should be documented.",
        "Explain why retention schedules need legal and operational review.",
        "Summarize a vendor-risk question about data residency.",
        "Describe how change management reduces production risk.",
        "Explain why human approval may be required for high-impact automation.",
        "Draft a neutral note about evidence needed for compliance attestation.",
    ],
    "writing": [
        "Write a short abstract for a research note about model evaluation.",
        "Rewrite a dense paragraph into clearer academic prose.",
        "Summarize a project update for a technical committee.",
        "Draft a polite email asking for clarification on review feedback.",
        "Explain how to turn experiment notes into a thesis section.",
        "Write a concise transition sentence between two report sections.",
        "Describe how to avoid overclaiming a preliminary result.",
        "Draft a limitation paragraph for a benchmark paper.",
        "Explain the difference between evidence and interpretation.",
        "Write a short executive summary of a failed experiment.",
        "Describe how tables can support a scientific argument.",
        "Draft a closing paragraph that states a cautious next step.",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="allenai/OLMoE-1B-7B-0924")
    parser.add_argument("--outdir", default="/home/ubuntu/praxis_moe_router_smoke_20260623")
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--committee-size", type=int, default=32)
    parser.add_argument("--prompts-per-domain", type=int, default=12)
    return parser.parse_args()


def entropy(probs: torch.Tensor) -> float:
    safe = probs.clamp_min(1e-12)
    return float((-(safe * safe.log()).sum(dim=-1)).mean().item())


def normalize_router_tensor(tensor: torch.Tensor) -> torch.Tensor | None:
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
    candidates = []
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


def layer_mass(router_tensors: list[torch.Tensor], top_k: int = 8) -> tuple[dict[str, float], list[dict[str, float]]]:
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


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# OLMoE Router-Audit Smoke",
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
        "## Domain Committees",
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
            "This is a smoke test for router observability and a first estimate of domain-invariant committee overlap. It is not a final standing-committee replication because it uses a small fixed prompt set and no fine-tuning/domain-shift intervention.",
            "",
            "## Claim Boundary",
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
    os.environ.setdefault("HF_HOME", "/opt/dlami/nvme/hf")

    config = AutoConfig.from_pretrained(args.model_id, trust_remote_code=True)
    if hasattr(config, "output_router_logits"):
        config.output_router_logits = True
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        config=config,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    model.eval()

    hook_captured, hook_handles, hook_names = hook_router_tensors(model)
    rows = []
    domain_masses: dict[str, defaultdict[str, float]] = {
        domain: defaultdict(float) for domain in PROMPTS
    }
    domain_counts = defaultdict(int)
    layer_top_k_masses = []
    layer_entropies = []
    captured_count = 0
    prompt_count = 0

    for domain, prompts in PROMPTS.items():
        for prompt in prompts[: args.prompts_per_domain]:
            prompt_count += 1
            hook_captured.clear()
            hook_names.clear()
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=args.max_length)
            inputs = {key: value.to(model.device) for key, value in inputs.items()}
            with torch.no_grad():
                outputs = model(**inputs, output_router_logits=True, use_cache=False, return_dict=True)
            routers = router_tensors_from_outputs(outputs)
            source = "outputs.router_logits"
            if not routers:
                routers = list(hook_captured)
                source = "forward_hooks"
            if routers:
                captured_count += 1
                mass, layer_rows = layer_mass(routers)
                for key, value in mass.items():
                    domain_masses[domain][key] += value
                domain_counts[domain] += 1
                layer_top_k_masses.extend(item["top_k_mass"] for item in layer_rows)
                layer_entropies.extend(item["entropy"] for item in layer_rows)
                rows.append(
                    {
                        "domain": domain,
                        "prompt": prompt,
                        "router_source": source,
                        "router_tensor_count": len(routers),
                        "mean_top_k_mass": float(np.mean([item["top_k_mass"] for item in layer_rows])),
                        "mean_entropy": float(np.mean([item["entropy"] for item in layer_rows])),
                    }
                )
            else:
                rows.append(
                    {
                        "domain": domain,
                        "prompt": prompt,
                        "router_source": "missing",
                        "router_tensor_count": 0,
                        "mean_top_k_mass": None,
                        "mean_entropy": None,
                    }
                )

    for handle in hook_handles:
        handle.remove()

    averaged_masses: dict[str, dict[str, float]] = {}
    committees: dict[str, list[str]] = {}
    for domain, mass in domain_masses.items():
        count = max(1, domain_counts[domain])
        averaged = {key: value / count for key, value in mass.items()}
        averaged_masses[domain] = averaged
        committees[domain] = top_committee(averaged, args.committee_size)

    pairwise = []
    for left, right in itertools.combinations(sorted(committees), 2):
        score = jaccard(set(committees[left]), set(committees[right]))
        pairwise.append({"left": left, "right": right, "jaccard": score})

    capture_rate = captured_count / max(1, prompt_count)
    jaccard_mean = float(np.mean([item["jaccard"] for item in pairwise])) if pairwise else 0.0
    top_mass_mean = float(np.mean(layer_top_k_masses)) if layer_top_k_masses else 0.0
    entropy_mean = float(np.mean(layer_entropies)) if layer_entropies else 0.0

    capture_pass = capture_rate >= 0.95 and prompt_count >= 60
    signal_pass = jaccard_mean >= 0.20
    payload = {
        "experiment_id": "moe-standing-committee-router-smoke-20260623",
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model_id": args.model_id,
        "summary": {
            "smoke_decision": "PASS" if capture_pass else "FAIL",
            "standing_committee_signal": "SOFT_PASS" if signal_pass else "MIXED_OR_WEAK",
            "prompt_count": prompt_count,
            "router_captured_prompt_count": captured_count,
            "router_capture_rate": capture_rate,
            "domain_pairwise_jaccard_mean": jaccard_mean,
            "mean_layer_top_k_mass": top_mass_mean,
            "mean_layer_entropy": entropy_mean,
        },
        "domain_pairwise_jaccard": pairwise,
        "domain_committees": committees,
        "prompt_rows": rows,
        "claim_boundary": "This is an AWS router-observability and standing-committee smoke test on OLMoE. It can justify a larger pre-registered router audit, but it is not a full standing-committee replication or fine-tuning-shift claim.",
    }
    (outdir / "MOE_STANDING_COMMITTEE_ROUTER_SMOKE_20260623.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (outdir / "MOE_STANDING_COMMITTEE_ROUTER_SMOKE_20260623.md").write_text(
        render_report(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0 if capture_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
