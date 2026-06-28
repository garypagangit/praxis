#!/usr/bin/env python
"""Cross-architecture source gate for PX-005.

This script checks public Hugging Face metadata for non-OLMoE MoE models and
decides whether a cross-architecture router audit is technically ready. It does
not download weights or run inference.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

from run_moe_standing_committee_source_gate import (
    candidate_feasibility,
    fetch_json,
    get_aws_identity,
    get_gpu_instance_summary,
    hub_config_url,
    hub_model_url,
    load_json,
    markdown_bool,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/moe_cross_arch_source_gate_20260628.json",
        help="Path to cross-architecture gate config.",
    )
    parser.add_argument(
        "--outdir",
        default="reports/moe_standing_committee",
        help="Output directory.",
    )
    return parser.parse_args()


def local_toolchain() -> dict[str, Any]:
    return {
        "torch_available": importlib.util.find_spec("torch") is not None,
        "transformers_available": importlib.util.find_spec("transformers") is not None,
        "huggingface_hub_available": importlib.util.find_spec("huggingface_hub") is not None,
    }


def is_cross_arch(candidate: dict[str, Any], cfg: dict[str, Any]) -> bool:
    return str(candidate.get("expected_family")) != str(cfg["baseline_family"])


def summarize_cross_arch(candidates: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    thresholds = cfg["gate_thresholds"]
    public_count = sum(1 for c in candidates if c["public_config_accessible"])
    router_count = sum(1 for c in candidates if c["router_observable_by_config"])
    cross_candidates = [
        c for c in candidates if c["expected_family"] != cfg["baseline_family"] and c["source_gate_candidate"]
    ]
    cross_smoke = [c for c in cross_candidates if c["primary_smoke_candidate"]]
    cross_followon = [c for c in cross_candidates if c["followon_candidate"]]

    pass_gate = (
        public_count >= int(thresholds["minimum_public_config_candidates"])
        and router_count >= int(thresholds["minimum_router_observable_candidates"])
        and len(cross_candidates) >= int(thresholds["minimum_cross_arch_source_candidate_count"])
    )

    def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            not item["primary_smoke_candidate"],
            not item["followon_candidate"],
            item["estimated_weight_gb"] if item["estimated_weight_gb"] is not None else 9999,
            item["repo_id"],
        )

    return {
        "decision": "PASS_SOURCE_GATE" if pass_gate else "FAIL_SOURCE_GATE",
        "public_config_candidate_count": public_count,
        "router_observable_candidate_count": router_count,
        "cross_arch_source_candidate_count": len(cross_candidates),
        "cross_arch_single_gpu_smoke_candidate_count": len(cross_smoke),
        "cross_arch_medium_gpu_followon_candidate_count": len(cross_followon),
        "best_cross_arch_candidates": [c["repo_id"] for c in sorted(cross_candidates, key=sort_key)],
    }


def render_report(
    cfg: dict[str, Any],
    summary: dict[str, Any],
    candidates: list[dict[str, Any]],
    toolchain: dict[str, Any],
    aws_identity: dict[str, Any],
    aws_gpu: dict[str, Any],
) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# MoE Standing-Committee Cross-Architecture Source Gate",
        "",
        f"Updated: {now}",
        "",
        f"PX ID: `{cfg['px_id']}`",
        "",
        f"Status: **{summary['decision']}**",
        "",
        "## Praxis framing",
        "",
        "PX-005 already has a bounded positive OLMoE-family result. This gate checks whether a non-OLMoE cross-architecture audit is ready to run by inspecting public model metadata, router/expert configuration fields, local toolchain availability, and AWS profile readiness.",
        "",
        "This is not a router-trace replication. It does not download weights and does not run inference.",
        "",
        "## Gate decision",
        "",
        f"Decision: **{summary['decision']}**.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Public config candidates | {summary['public_config_candidate_count']} |",
        f"| Router-observable candidates | {summary['router_observable_candidate_count']} |",
        f"| Non-OLMoE source candidates | {summary['cross_arch_source_candidate_count']} |",
        f"| Non-OLMoE single-GPU smoke candidates | {summary['cross_arch_single_gpu_smoke_candidate_count']} |",
        f"| Non-OLMoE medium-GPU follow-on candidates | {summary['cross_arch_medium_gpu_followon_candidate_count']} |",
        "",
        "Best non-OLMoE candidates, in order:",
        "",
    ]
    if summary["best_cross_arch_candidates"]:
        for idx, repo_id in enumerate(summary["best_cross_arch_candidates"], start=1):
            lines.append(f"{idx}. `{repo_id}`")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Candidate audit",
            "",
            "| Repo | Family | Public config | MoE evidence | Router observable | Est. weights GB | Smoke | Follow-on | Decision |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for c in candidates:
        weight = "unknown" if c["estimated_weight_gb"] is None else f"{c['estimated_weight_gb']:.3f}"
        cross = c["expected_family"] != cfg["baseline_family"]
        if not cross:
            decision = "published baseline"
        elif c["primary_smoke_candidate"]:
            decision = "cross-arch smoke candidate"
        elif c["followon_candidate"]:
            decision = "cross-arch follow-on candidate"
        elif c["source_gate_candidate"]:
            decision = "cross-arch source candidate"
        else:
            decision = "hold"
        lines.append(
            f"| `{c['repo_id']}` | `{c['expected_family']}` | {markdown_bool(c['public_config_accessible'])} | "
            f"{markdown_bool(c['is_moe_by_metadata'])} | {markdown_bool(c['router_observable_by_config'])} | "
            f"{weight} | {markdown_bool(c['primary_smoke_candidate'])} | {markdown_bool(c['followon_candidate'])} | {decision} |"
        )

    lines.extend(
        [
            "",
            "## Local and AWS readiness",
            "",
            "| Check | Result |",
            "|---|---:|",
            f"| PyTorch import | {markdown_bool(toolchain['torch_available'])} |",
            f"| Transformers import | {markdown_bool(toolchain['transformers_available'])} |",
            f"| Hugging Face Hub import | {markdown_bool(toolchain['huggingface_hub_available'])} |",
            f"| AWS STS profile `{cfg['aws_profile']}` | {markdown_bool(bool(aws_identity.get('ok')))} |",
            f"| AWS GPU inventory query | {markdown_bool(bool(aws_gpu.get('ok')))} |",
            "",
        ]
    )
    if not toolchain["torch_available"] or not toolchain["transformers_available"]:
        lines.append("Local inference audit is blocked on this machine because PyTorch/Transformers are not installed.")
        lines.append("")
    if aws_identity.get("ok"):
        lines.append(f"AWS identity: `{aws_identity.get('Arn')}`.")
    else:
        lines.append(f"AWS identity error: `{aws_identity.get('error')}`.")
    if aws_gpu.get("ok"):
        lines.append(f"GPU instances found in `{cfg['aws_region']}`: `{len(aws_gpu.get('instances', []))}`.")
    else:
        lines.append(f"AWS GPU inventory error: `{aws_gpu.get('error')}`.")

    lines.extend(["", "## Candidate metadata notes", ""])
    for c in candidates:
        lines.append(f"### `{c['repo_id']}`")
        lines.append("")
        if c["fetch_errors"]:
            lines.append(f"Fetch errors: `{'; '.join(c['fetch_errors'])}`.")
        if c["moe_detection_reasons"]:
            lines.append(f"MoE evidence: `{', '.join(c['moe_detection_reasons'])}`.")
        if c["router_observability_keys"]:
            rendered = ", ".join(f"`{key}`" for key in c["router_observability_keys"][:12])
            lines.append(f"Router/expert keys: {rendered}.")
        fields = list(c["config_moe_fields"].items())[:12]
        if fields:
            rendered_fields = ", ".join(f"`{key}={value}`" for key, value in fields)
            lines.append(f"Selected fields: {rendered_fields}.")
        lines.append("")

    lines.extend(
        [
            "## Result interpretation",
            "",
            "This gate passes if at least one non-OLMoE model has public MoE/router metadata and a feasible weight-size tier for a later instrumented run. It does not validate standing-committee behavior outside OLMoE.",
            "",
            "## Next registered gate",
            "",
            "Run a frozen prompt-domain router audit on the best non-OLMoE candidate after installing the required inference stack or moving to AWS/HF GPU infrastructure. Use the exact OLMoE audit format: router capture rate, committee-size sensitivity, mean pairwise Jaccard, bootstrap confidence intervals, and no threshold changes after model selection.",
            "",
            "## Sources",
            "",
            f"- Literature anchor: {cfg['primary_literature_anchor']['url']}",
        ]
    )
    for c in candidates:
        lines.append(f"- `{c['repo_id']}` model page: {c['hub_url']}")
        lines.append(f"- `{c['repo_id']}` config: {c['config_url']}")
    lines.append("")
    lines.append(f"Claim boundary: {cfg['claim_boundary']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    cfg = load_json(Path(args.config))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    base = cfg["hub_api_base"]
    candidate_results = []

    for candidate in cfg["candidate_models"]:
        repo_id = candidate["repo_id"]
        errors: list[str] = []
        info, info_error = fetch_json(hub_model_url(base, repo_id), token=token)
        if info_error:
            errors.append(f"model info {info_error}")
        time.sleep(0.2)
        config_json, config_error = fetch_json(hub_config_url(base, repo_id), token=token)
        if config_error:
            errors.append(f"config {config_error}")
        result = candidate_feasibility(candidate, info, config_json, cfg, token, errors)
        candidate_results.append(result)
        time.sleep(0.2)

    summary = summarize_cross_arch(candidate_results, cfg)
    toolchain = local_toolchain()
    aws_identity = get_aws_identity(cfg["aws_profile"])
    aws_gpu = get_gpu_instance_summary(cfg["aws_profile"], cfg["aws_region"])
    payload = {
        "experiment_id": cfg["experiment_id"],
        "title": cfg["title"],
        "run_date": cfg["run_date"],
        "decision": summary["decision"],
        "summary": summary,
        "toolchain": toolchain,
        "aws_identity": aws_identity,
        "aws_gpu": aws_gpu,
        "candidates": candidate_results,
        "claim_boundary": cfg["claim_boundary"],
    }

    report_path = outdir / "MOE_CROSS_ARCH_SOURCE_GATE_20260628.md"
    json_path = outdir / "MOE_CROSS_ARCH_SOURCE_GATE_20260628.json"
    report_path.write_text(render_report(cfg, summary, candidate_results, toolchain, aws_identity, aws_gpu), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": summary["decision"], "report": str(report_path), "summary": summary}, indent=2))
    return 0 if summary["decision"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
