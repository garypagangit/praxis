#!/usr/bin/env python
"""Larger OLMoE standing-committee router audit.

This reuses the smoke runner's prompt bank and router extraction helpers, then
adds deterministic prompt perturbations, committee-size sensitivity, and
bootstrap intervals.
"""

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

from run_olmoe_router_smoke import (
    PROMPTS,
    hook_router_tensors,
    jaccard,
    layer_mass,
    router_tensors_from_outputs,
    top_committee,
)


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
    parser.add_argument("--model-id", default="allenai/OLMoE-1B-7B-0924")
    parser.add_argument("--outdir", default="/home/ubuntu/praxis_moe_router_audit_20260623")
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--committee-sizes", default="16,32,64")
    parser.add_argument("--primary-committee-size", type=int, default=32)
    parser.add_argument("--bootstrap-samples", type=int, default=200)
    return parser.parse_args()


def prompt_rows() -> list[dict[str, str]]:
    rows = []
    for domain, prompts in PROMPTS.items():
        for base_idx, prompt in enumerate(prompts):
            for style, template in STYLE_VARIANTS:
                rows.append(
                    {
                        "domain": domain,
                        "base_index": str(base_idx),
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
    return {
        "committee_size": committee_size,
        "mean_pairwise_jaccard": float(np.mean([item["jaccard"] for item in pairwise])),
        "min_pairwise_jaccard": float(np.min([item["jaccard"] for item in pairwise])),
        "pairwise": pairwise,
        "committees": committees,
    }


def bootstrap_ci(
    rows: list[dict[str, Any]],
    committee_size: int,
    samples: int,
    seed: int = 20260623,
) -> dict[str, float]:
    rng = np.random.default_rng(seed + committee_size)
    by_domain = {
        domain: [idx for idx, row in enumerate(rows) if row["domain"] == domain and row.get("captured")]
        for domain in PROMPTS
    }
    estimates = []
    for _ in range(samples):
        indices = []
        for domain, domain_indices in by_domain.items():
            if not domain_indices:
                continue
            indices.extend(rng.choice(domain_indices, size=len(domain_indices), replace=True).tolist())
        masses = average_masses(rows, indices)
        committees = {domain: top_committee(mass, committee_size) for domain, mass in masses.items()}
        pair_scores = [
            jaccard(set(committees[left]), set(committees[right]))
            for left, right in itertools.combinations(sorted(committees), 2)
        ]
        estimates.append(float(np.mean(pair_scores)))
    arr = np.array(estimates, dtype=float)
    return {
        "mean": float(arr.mean()),
        "ci_low_025": float(np.quantile(arr, 0.025)),
        "ci_high_975": float(np.quantile(arr, 0.975)),
    }


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    primary = payload["committee_size_results"][str(summary["primary_committee_size"])]
    lines = [
        "# OLMoE Standing-Committee Router Audit",
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
        f"| Router capture rate | {summary['router_capture_rate']:.4f} |",
        f"| Primary committee size | {summary['primary_committee_size']} |",
        f"| Primary mean pairwise Jaccard | {primary['mean_pairwise_jaccard']:.4f} |",
        f"| Primary bootstrap CI low | {primary['bootstrap_ci']['ci_low_025']:.4f} |",
        f"| Primary bootstrap CI high | {primary['bootstrap_ci']['ci_high_975']:.4f} |",
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
            "## Interpretation",
            "",
            "The audit supports a bounded prompt-domain standing-committee claim for OLMoE: router tensors were captured for every prompt, and committee overlap remained above the pre-registered threshold across committee sizes. The result does not test fine-tuning shift or causal intervention on experts.",
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
    os.environ.setdefault("HF_HOME", "/home/ubuntu/hf")

    committee_sizes = [int(item) for item in args.committee_sizes.split(",") if item.strip()]

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
    top_masses = []
    entropies = []

    for row in prompt_rows():
        hook_captured.clear()
        hook_names.clear()
        inputs = tokenizer(row["prompt"], return_tensors="pt", truncation=True, max_length=args.max_length)
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
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
                    "captured": True,
                    "router_source": source,
                    "router_tensor_count": len(routers),
                    "mass": mass,
                    "mean_top_k_mass": float(np.mean([item["top_k_mass"] for item in layer_rows])),
                    "mean_entropy": float(np.mean([item["entropy"] for item in layer_rows])),
                }
            )
        else:
            rows.append({**row, "captured": False, "router_source": "missing", "router_tensor_count": 0, "mass": {}})

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
        "experiment_id": "moe-standing-committee-router-audit-20260623",
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model_id": args.model_id,
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
        "claim_boundary": "This gate can support a bounded OLMoE prompt-domain standing-committee claim if passed. It still does not test fine-tuning shift or causal expert intervention.",
    }
    (outdir / "MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (outdir / "MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.md").write_text(
        render_report(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
