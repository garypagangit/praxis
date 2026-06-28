#!/usr/bin/env python
"""Frozen Qwen1.5-MoE standing-committee router audit for PX-005."""

from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
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

STYLE_VARIANTS = [
    ("direct", "{prompt}"),
    ("concise", "Answer concisely: {prompt}"),
    ("stepwise", "Use a short step-by-step explanation: {prompt}"),
    ("risk", "Focus on risks and caveats: {prompt}"),
    ("evidence", "Emphasize evidence and assumptions: {prompt}"),
    ("beginner", "Explain for a careful beginner: {prompt}"),
    ("expert", "Answer for a technical expert: {prompt}"),
    ("summary", "Give a compact summary with no extra examples: {prompt}"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="Qwen/Qwen1.5-MoE-A2.7B")
    parser.add_argument("--outdir", default="/opt/praxis/jobs/moe-qwen15-router-audit-20260628/output")
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--committee-sizes", default="16,32,64")
    parser.add_argument("--primary-committee-size", type=int, default=32)
    parser.add_argument("--bootstrap-samples", type=int, default=200)
    parser.add_argument("--load-in-8bit", action="store_true")
    parser.add_argument("--gpu-memory", default="20GiB")
    parser.add_argument("--cpu-memory", default="12GiB")
    parser.add_argument("--offload-folder", default="/opt/praxis/jobs/moe-qwen15-router-audit-20260628/offload")
    parser.add_argument("--artifact-stem", default="MOE_QWEN15_ROUTER_AUDIT_20260628")
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


def prompt_rows() -> list[dict[str, Any]]:
    rows = []
    for domain, prompts in PROMPTS.items():
        for base_idx, prompt in enumerate(prompts):
            for style, template in STYLE_VARIANTS:
                rows.append(
                    {
                        "domain": domain,
                        "base_index": base_idx,
                        "style": style,
                        "prompt": template.format(prompt=prompt),
                    }
                )
    return rows


def average_masses(rows: list[dict[str, Any]], indices: list[int] | None = None) -> dict[str, dict[str, float]]:
    selected = rows if indices is None else [rows[idx] for idx in indices]
    sums: dict[str, defaultdict[str, float]] = {}
    counts = defaultdict(int)
    for row in selected:
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


def committee_stats(rows: list[dict[str, Any]], committee_size: int) -> dict[str, Any]:
    masses = average_masses(rows)
    committees = {domain: top_committee(mass, committee_size) for domain, mass in masses.items()}
    pairwise = []
    for left, right in itertools.combinations(sorted(committees), 2):
        pairwise.append(
            {
                "left": left,
                "right": right,
                "jaccard": jaccard(set(committees[left]), set(committees[right])),
            }
        )
    scores = [item["jaccard"] for item in pairwise]
    return {
        "committee_size": committee_size,
        "mean_pairwise_jaccard": float(np.mean(scores)) if scores else 0.0,
        "min_pairwise_jaccard": float(np.min(scores)) if scores else 0.0,
        "pairwise": pairwise,
        "committees": committees,
    }


def bootstrap_ci(
    rows: list[dict[str, Any]],
    committee_size: int,
    samples: int,
    seed: int = 20260628,
) -> dict[str, float]:
    rng = np.random.default_rng(seed + committee_size)
    by_domain = {
        domain: [idx for idx, row in enumerate(rows) if row["domain"] == domain and row.get("captured")]
        for domain in PROMPTS
    }
    estimates = []
    for _ in range(samples):
        indices = []
        for domain_indices in by_domain.values():
            if not domain_indices:
                continue
            indices.extend(rng.choice(domain_indices, size=len(domain_indices), replace=True).tolist())
        masses = average_masses(rows, indices)
        committees = {domain: top_committee(mass, committee_size) for domain, mass in masses.items()}
        pair_scores = [
            jaccard(set(committees[left]), set(committees[right]))
            for left, right in itertools.combinations(sorted(committees), 2)
        ]
        estimates.append(float(np.mean(pair_scores)) if pair_scores else 0.0)
    arr = np.array(estimates, dtype=float)
    return {
        "mean": float(arr.mean()) if arr.size else 0.0,
        "ci_low_025": float(np.quantile(arr, 0.025)) if arr.size else 0.0,
        "ci_high_975": float(np.quantile(arr, 0.975)) if arr.size else 0.0,
    }


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    primary = payload["committee_size_results"][str(summary["primary_committee_size"])]
    lines = [
        "# Qwen1.5-MoE Standing-Committee Router Audit",
        "",
        f"Updated: {payload['updated_utc']}",
        "",
        f"Model: `{payload['model_id']}`.",
        "",
        "## Decision",
        "",
        f"Audit decision: **{summary['audit_decision']}**.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Prompt count | {summary['prompt_count']} |",
        f"| Router-captured prompts | {summary['router_captured_prompt_count']} |",
        f"| Router capture rate | {summary['router_capture_rate']:.4f} |",
        f"| Primary committee size | {summary['primary_committee_size']} |",
        f"| Primary mean pairwise Jaccard | {primary['mean_pairwise_jaccard']:.4f} |",
        f"| Primary bootstrap CI low | {primary['bootstrap_ci']['ci_low_025']:.4f} |",
        f"| Primary bootstrap CI high | {primary['bootstrap_ci']['ci_high_975']:.4f} |",
        f"| Mean layer top-k mass | {summary['mean_layer_top_k_mass']:.4f} |",
        f"| Mean layer entropy | {summary['mean_layer_entropy']:.4f} |",
        "",
        "## Committee-size sensitivity",
        "",
        "| Committee size | Mean Jaccard | Min Jaccard | CI low | CI high |",
        "|---:|---:|---:|---:|---:|",
    ]
    for size, result in payload["committee_size_results"].items():
        ci = result["bootstrap_ci"]
        lines.append(
            f"| {size} | {result['mean_pairwise_jaccard']:.4f} | "
            f"{result['min_pairwise_jaccard']:.4f} | {ci['ci_low_025']:.4f} | {ci['ci_high_975']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Gate checks",
            "",
            "| Check | Passed |",
            "|---|---:|",
        ]
    )
    for name, passed in summary["checks"].items():
        lines.append(f"| `{name}` | `{passed}` |")
    lines.extend(
        [
            "",
            "## Domain committees",
            "",
            "| Domain | Primary committee preview |",
            "|---|---|",
        ]
    )
    for domain, committee in primary["committees"].items():
        lines.append(f"| `{domain}` | `{committee[:12]}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is the frozen non-OLMoE cross-architecture gate for PX-005. It uses the same prompt domains, style perturbations, committee sizes, and pass thresholds as the OLMoE audit while adapting only the model-loading path for Qwen1.5-MoE.",
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
    os.environ.setdefault("HF_HOME", "/opt/praxis/hf")

    committee_sizes = [int(item) for item in args.committee_sizes.split(",") if item.strip()]
    prompt_bank = prompt_rows()

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

    first_param = next(model.parameters())
    for idx, row in enumerate(prompt_bank, start=1):
        hook_captured.clear()
        hook_names.clear()
        inputs = tokenizer(row["prompt"], return_tensors="pt", truncation=True, max_length=args.max_length)
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
                    **row,
                    "prompt_index": idx,
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
                    **row,
                    "prompt_index": idx,
                    "captured": False,
                    "router_source": "missing",
                    "router_tensor_count": 0,
                    "mass": {},
                }
            )
        if idx % 25 == 0 or idx == len(prompt_bank):
            print(json.dumps({"progress": idx, "total": len(prompt_bank), "captured": sum(1 for item in rows if item["captured"])}))

    for handle in hook_handles:
        handle.remove()

    captured = sum(1 for row in rows if row["captured"])
    capture_rate = captured / max(1, len(rows))
    results = {}
    for size in committee_sizes:
        stats = committee_stats(rows, size)
        stats["bootstrap_ci"] = bootstrap_ci(rows, size, args.bootstrap_samples)
        results[str(size)] = stats

    primary = results[str(args.primary_committee_size)]
    checks = {
        "router_capture_rate": capture_rate >= 0.95,
        "primary_jaccard_mean": primary["mean_pairwise_jaccard"] >= 0.25,
        "primary_jaccard_ci_low": primary["bootstrap_ci"]["ci_low_025"] >= 0.20,
        "all_committee_size_means": all(item["mean_pairwise_jaccard"] >= 0.20 for item in results.values()),
    }
    payload = {
        "experiment_id": "moe-qwen15-standing-committee-router-audit-20260628",
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model_id": args.model_id,
        "load_in_8bit": args.load_in_8bit,
        "cuda_available": bool(torch.cuda.is_available()),
        "hook_names": sorted(set(hook_names)),
        "summary": {
            "audit_decision": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "prompt_count": len(rows),
            "router_captured_prompt_count": captured,
            "router_capture_rate": capture_rate,
            "primary_committee_size": args.primary_committee_size,
            "mean_layer_top_k_mass": float(np.mean(top_masses)) if top_masses else 0.0,
            "mean_layer_entropy": float(np.mean(entropies)) if entropies else 0.0,
        },
        "committee_size_results": results,
        "prompt_rows": [
            {key: value for key, value in row.items() if key != "mass"}
            for row in rows
        ],
        "claim_boundary": "This gate can support a bounded cross-architecture standing-committee claim only if it passes under the frozen OLMoE protocol. It still does not test fine-tuning shift or causal expert intervention.",
    }

    json_path = outdir / f"{args.artifact_stem}.json"
    report_path = outdir / f"{args.artifact_stem}.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({"decision": payload["summary"]["audit_decision"], "report": str(report_path), "summary": payload["summary"]}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
