#!/usr/bin/env python
"""Source and feasibility gate for the MoE standing-committee experiment.

The gate intentionally reads only public metadata and small JSON files. It does
not download model weights. The goal is to decide whether a router-trace
experiment is defensible before spending GPU budget.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


MOE_CONFIG_KEYS = {
    "num_experts",
    "num_local_experts",
    "num_experts_per_tok",
    "num_experts_per_token",
    "n_routed_experts",
    "n_shared_experts",
    "moe_intermediate_size",
    "shared_expert_intermediate_size",
    "first_k_dense_replace",
    "decoder_sparse_step",
    "router_aux_loss_coef",
    "output_router_logits",
    "router_jitter_noise",
    "moe_layer_freq",
}

ROUTER_OBSERVABILITY_KEYS = {
    "output_router_logits",
    "router_aux_loss_coef",
    "router_jitter_noise",
    "num_experts_per_tok",
    "num_experts_per_token",
    "n_routed_experts",
}

CONFIG_NAME_PATTERN = re.compile(r"(^|/)config\.json$")
WEIGHT_PATTERN = re.compile(
    r"\.(safetensors|bin|pt|pth|gguf|onnx)$|model-\d{5}-of-\d{5}\.safetensors$",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/moe_standing_committee_source_gate_20260623.json",
        help="Path to gate config JSON.",
    )
    parser.add_argument(
        "--outdir",
        default="reports/moe_standing_committee",
        help="Directory for report artifacts.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def request_headers(token: str | None = None, accept: str = "application/json") -> dict[str, str]:
    headers = {
        "User-Agent": "praxis-moe-source-gate/20260623",
        "Accept": accept,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_json(url: str, token: str | None = None, timeout: int = 30) -> tuple[dict[str, Any] | None, str | None]:
    headers = request_headers(token)

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw), None
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            body = ""
        return None, f"HTTP {exc.code}: {body}"
    except urllib.error.URLError as exc:
        return None, f"URL error: {exc.reason}"
    except TimeoutError:
        return None, "timeout"
    except json.JSONDecodeError as exc:
        return None, f"JSON decode error: {exc}"


def head_content_length(url: str, token: str | None = None, timeout: int = 30) -> tuple[int | None, str | None]:
    request = urllib.request.Request(url, headers=request_headers(token, "*/*"), method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            length = response.headers.get("Content-Length")
        if length is None:
            return None, "missing Content-Length"
        return int(length), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return None, f"URL error: {exc.reason}"
    except TimeoutError:
        return None, "timeout"
    except ValueError:
        return None, "invalid Content-Length"


def hub_model_url(base: str, repo_id: str) -> str:
    quoted = urllib.parse.quote(repo_id, safe="/")
    return f"{base.rstrip('/')}/api/models/{quoted}"


def hub_config_url(base: str, repo_id: str) -> str:
    quoted = urllib.parse.quote(repo_id, safe="/")
    return f"{base.rstrip('/')}/{quoted}/resolve/main/config.json"


def flatten_keys(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            out[next_prefix] = value
            out.update(flatten_keys(value, next_prefix))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj[:10]):
            out.update(flatten_keys(value, f"{prefix}[{idx}]"))
    return out


def select_moe_fields(config: dict[str, Any] | None) -> dict[str, Any]:
    if not config:
        return {}
    flat = flatten_keys(config)
    selected: dict[str, Any] = {}
    for dotted_key, value in flat.items():
        last = dotted_key.split(".")[-1]
        if last in MOE_CONFIG_KEYS or "moe" in dotted_key.lower() or "expert" in dotted_key.lower() or "router" in dotted_key.lower():
            if isinstance(value, (str, int, float, bool)) or value is None:
                selected[dotted_key] = value
    return selected


def model_siblings(model_info: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not model_info:
        return []
    siblings = model_info.get("siblings", [])
    if isinstance(siblings, list):
        return [item for item in siblings if isinstance(item, dict)]
    return []


def estimate_weight_size_gb(
    base: str,
    repo_id: str,
    model_info: dict[str, Any] | None,
    token: str | None,
) -> tuple[float | None, int, bool, list[str]]:
    siblings = model_siblings(model_info)
    weight_files = []
    unknown_size = False
    total_bytes = 0
    errors = []
    for sibling in siblings:
        name = str(sibling.get("rfilename", ""))
        if not WEIGHT_PATTERN.search(name):
            continue
        weight_files.append(sibling)
        size = sibling.get("size")
        if isinstance(size, int):
            total_bytes += size
        else:
            quoted_repo = urllib.parse.quote(repo_id, safe="/")
            quoted_name = urllib.parse.quote(name, safe="/")
            url = f"{base.rstrip('/')}/{quoted_repo}/resolve/main/{quoted_name}"
            length, error = head_content_length(url, token=token)
            if length is None:
                unknown_size = True
                errors.append(f"{name}: {error}")
            else:
                total_bytes += length

    if total_bytes > 0:
        return round(total_bytes / (1024**3), 3), len(weight_files), unknown_size, errors
    return None, len(weight_files), unknown_size or bool(weight_files), errors


def is_public_and_accessible(model_info: dict[str, Any] | None, config: dict[str, Any] | None) -> bool:
    if not model_info or not config:
        return False
    if model_info.get("private") is True:
        return False
    gated = model_info.get("gated")
    if gated not in (False, None, "false"):
        return False
    return True


def router_observable(config: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not config:
        return False, []
    flat = flatten_keys(config)
    hits = []
    for dotted_key in flat:
        last = dotted_key.split(".")[-1]
        lower = dotted_key.lower()
        if last in ROUTER_OBSERVABILITY_KEYS or "router" in lower:
            hits.append(dotted_key)
    return bool(hits), sorted(set(hits))


def detect_moe(config: dict[str, Any] | None, model_info: dict[str, Any] | None) -> tuple[bool, list[str]]:
    reasons = []
    if config:
        fields = select_moe_fields(config)
        if fields:
            reasons.append("moe_or_expert_fields_in_config")
        architectures = config.get("architectures", [])
        if isinstance(architectures, list) and any("moe" in str(item).lower() for item in architectures):
            reasons.append("architecture_name_mentions_moe")
        model_type = str(config.get("model_type", ""))
        if "moe" in model_type.lower():
            reasons.append("model_type_mentions_moe")
    if model_info:
        tags = model_info.get("tags", [])
        if isinstance(tags, list) and any("moe" in str(tag).lower() for tag in tags):
            reasons.append("hub_tag_mentions_moe")
        repo_id = str(model_info.get("id", ""))
        if "moe" in repo_id.lower() or "a3b" in repo_id.lower() or "deepseek-v2" in repo_id.lower():
            reasons.append("repo_name_moe_family_signal")
    return bool(reasons), sorted(set(reasons))


def get_aws_identity(profile: str) -> dict[str, Any]:
    command = ["aws", "sts", "get-caller-identity", "--profile", profile]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        return {"ok": False, "error": "aws cli not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "aws sts timeout"}
    if completed.returncode != 0:
        return {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip()}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": completed.stdout.strip()}
    payload["ok"] = True
    return payload


def get_gpu_instance_summary(profile: str, region: str) -> dict[str, Any]:
    query = (
        "Reservations[].Instances[].{InstanceId:InstanceId,State:State.Name,"
        "Type:InstanceType,Name:Tags[?Key=='Name']|[0].Value,LaunchTime:LaunchTime}"
    )
    command = [
        "aws",
        "ec2",
        "describe-instances",
        "--profile",
        profile,
        "--region",
        region,
        "--filters",
        "Name=instance-type,Values=g4dn.*,g5.*,g6.*,p3.*,p4.*,p5.*",
        "--query",
        query,
        "--output",
        "json",
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=40)
    except FileNotFoundError:
        return {"ok": False, "error": "aws cli not found", "instances": []}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "aws ec2 timeout", "instances": []}
    if completed.returncode != 0:
        return {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip(), "instances": []}
    try:
        instances = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": completed.stdout.strip(), "instances": []}
    return {"ok": True, "instances": instances}


def candidate_feasibility(
    candidate: dict[str, Any],
    model_info: dict[str, Any] | None,
    config_json: dict[str, Any] | None,
    cfg: dict[str, Any],
    token: str | None,
    fetch_errors: list[str],
) -> dict[str, Any]:
    public_config = is_public_and_accessible(model_info, config_json)
    is_moe, moe_reasons = detect_moe(config_json, model_info)
    has_router, router_keys = router_observable(config_json)
    weight_gb, weight_file_count, size_unknown, size_errors = estimate_weight_size_gb(
        cfg["hub_api_base"], candidate["repo_id"], model_info, token
    )
    fetch_errors.extend([f"weight size {item}" for item in size_errors])
    moe_fields = select_moe_fields(config_json)

    thresholds = cfg["gate_thresholds"]
    single_gpu = False
    medium_gpu = False
    if weight_gb is not None:
        single_gpu = weight_gb <= thresholds["maximum_single_gpu_smoke_estimated_weight_gb"]
        medium_gpu = weight_gb <= thresholds["maximum_medium_gpu_estimated_weight_gb"]
    else:
        # Unknown size is not enough for a pass, but a small number of shards is
        # still useful as a planning hint.
        single_gpu = False
        medium_gpu = False

    source_gate_candidate = bool(public_config and is_moe and has_router and (single_gpu or medium_gpu or size_unknown))
    primary_smoke_candidate = bool(public_config and is_moe and has_router and single_gpu)
    followon_candidate = bool(public_config and is_moe and has_router and medium_gpu)

    return {
        "repo_id": candidate["repo_id"],
        "role": candidate.get("role"),
        "expected_family": candidate.get("expected_family"),
        "public_config_accessible": public_config,
        "is_moe_by_metadata": is_moe,
        "moe_detection_reasons": moe_reasons,
        "router_observable_by_config": has_router,
        "router_observability_keys": router_keys[:20],
        "estimated_weight_gb": weight_gb,
        "weight_file_count": weight_file_count,
        "weight_size_unknown": size_unknown,
        "single_gpu_smoke_feasible_by_size": single_gpu,
        "medium_gpu_followon_feasible_by_size": medium_gpu,
        "source_gate_candidate": source_gate_candidate,
        "primary_smoke_candidate": primary_smoke_candidate,
        "followon_candidate": followon_candidate,
        "config_moe_fields": moe_fields,
        "fetch_errors": fetch_errors,
        "hub_url": f"https://huggingface.co/{candidate['repo_id']}",
        "config_url": f"https://huggingface.co/{candidate['repo_id']}/resolve/main/config.json",
    }


def summarize_gate(candidates: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    thresholds = cfg["gate_thresholds"]
    public_count = sum(1 for c in candidates if c["public_config_accessible"])
    router_count = sum(1 for c in candidates if c["router_observable_by_config"])
    source_count = sum(1 for c in candidates if c["source_gate_candidate"])
    smoke_count = sum(1 for c in candidates if c["primary_smoke_candidate"])
    followon_count = sum(1 for c in candidates if c["followon_candidate"])

    pass_gate = (
        public_count >= thresholds["minimum_public_config_candidates"]
        and router_count >= thresholds["minimum_router_observable_candidates"]
        and source_count >= thresholds["minimum_source_gate_candidate_count"]
    )

    return {
        "decision": "PASS" if pass_gate else "FAIL",
        "public_config_candidate_count": public_count,
        "router_observable_candidate_count": router_count,
        "source_gate_candidate_count": source_count,
        "single_gpu_smoke_candidate_count": smoke_count,
        "medium_gpu_followon_candidate_count": followon_count,
        "best_primary_candidates": [
            c["repo_id"]
            for c in sorted(
                [item for item in candidates if item["source_gate_candidate"]],
                key=lambda item: (
                    not item["primary_smoke_candidate"],
                    item["estimated_weight_gb"] if item["estimated_weight_gb"] is not None else 9999,
                    item["repo_id"],
                ),
            )
        ],
    }


def markdown_bool(value: bool) -> str:
    return "PASS" if value else "FAIL"


def render_report(
    cfg: dict[str, Any],
    summary: dict[str, Any],
    candidates: list[dict[str, Any]],
    aws_identity: dict[str, Any],
    aws_gpu: dict[str, Any],
) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# MoE Standing-Committee Source Gate",
        "",
        f"Updated: {now}",
        "",
        "## Praxis framing",
        "",
        f"Working title: `{cfg['title']}`.",
        "",
        f"Literature anchor: `{cfg['primary_literature_anchor']['title']}` "
        f"({cfg['primary_literature_anchor']['arxiv']}).",
        "",
        "Hypothesis boundary: a defensible experiment requires an open MoE model whose "
        "routing or expert-selection metadata can be observed under held-out prompt "
        "domains before any fine-tuning or publication claim is attempted.",
        "",
        "Research questions:",
        "",
        "1. RQ1: Do public MoE checkpoints expose enough configuration evidence to support an inference-only router audit?",
        "2. RQ2: Is at least one candidate small enough for a practical GPU smoke run under the current AWS plan?",
        "3. RQ3: Does the source gate justify moving from literature concept to router-trace measurement?",
        "",
        "Hypotheses:",
        "",
        "1. H1: At least one open MoE model exposes router/expert metadata sufficient for a standing-committee audit.",
        "2. H2: A smaller open MoE candidate is feasible for a first smoke run, while larger candidates remain external-validity follow-ons.",
        "3. H3: Source-gated candidate selection will prevent an underpowered or unverifiable MoE replication attempt.",
        "",
        "## Gate decision",
        "",
        f"Decision: **{summary['decision']}**.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Public config candidates | {summary['public_config_candidate_count']} |",
        f"| Router-observable candidates | {summary['router_observable_candidate_count']} |",
        f"| Source-gate candidates | {summary['source_gate_candidate_count']} |",
        f"| Single-GPU smoke candidates by metadata size | {summary['single_gpu_smoke_candidate_count']} |",
        f"| Medium-GPU follow-on candidates by metadata size | {summary['medium_gpu_followon_candidate_count']} |",
        "",
        "Best candidates, in order:",
        "",
    ]

    if summary["best_primary_candidates"]:
        for idx, repo_id in enumerate(summary["best_primary_candidates"], start=1):
            lines.append(f"{idx}. `{repo_id}`")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Candidate audit",
            "",
            "| Repo | Public config | MoE evidence | Router observable | Est. weights GB | Smoke | Follow-on | Decision |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for c in candidates:
        weight = "unknown" if c["estimated_weight_gb"] is None else f"{c['estimated_weight_gb']:.3f}"
        decision = "source candidate" if c["source_gate_candidate"] else "hold"
        if c["primary_smoke_candidate"]:
            decision = "primary smoke candidate"
        elif c["followon_candidate"]:
            decision = "GPU follow-on candidate"
        lines.append(
            f"| `{c['repo_id']}` | {markdown_bool(c['public_config_accessible'])} | "
            f"{markdown_bool(c['is_moe_by_metadata'])} | "
            f"{markdown_bool(c['router_observable_by_config'])} | {weight} | "
            f"{markdown_bool(c['primary_smoke_candidate'])} | "
            f"{markdown_bool(c['followon_candidate'])} | {decision} |"
        )

    lines.extend(["", "## Key metadata fields", ""])
    for c in candidates:
        lines.append(f"### `{c['repo_id']}`")
        lines.append("")
        if c["fetch_errors"]:
            lines.append(f"Fetch errors: `{'; '.join(c['fetch_errors'])}`.")
            lines.append("")
        if c["moe_detection_reasons"]:
            lines.append(f"MoE evidence: `{', '.join(c['moe_detection_reasons'])}`.")
        if c["router_observability_keys"]:
            lines.append(
                "Router/expert observability keys: "
                + ", ".join(f"`{key}`" for key in c["router_observability_keys"][:12])
                + "."
            )
        fields = c["config_moe_fields"]
        if fields:
            compact_fields = list(fields.items())[:14]
            rendered = ", ".join(f"`{key}={value}`" for key, value in compact_fields)
            lines.append(f"Selected config fields: {rendered}.")
        if not fields and not c["fetch_errors"]:
            lines.append("Selected config fields: none found.")
        lines.append("")

    lines.extend(
        [
            "## AWS readiness",
            "",
            f"AWS STS profile `{cfg['aws_profile']}`: {'PASS' if aws_identity.get('ok') else 'FAIL'}.",
        ]
    )
    if aws_identity.get("ok"):
        lines.append(f"Account: `{aws_identity.get('Account')}`; ARN: `{aws_identity.get('Arn')}`.")
    else:
        lines.append(f"Error: `{aws_identity.get('error')}`.")
    lines.append("")
    lines.append(f"GPU instance inventory in `{cfg['aws_region']}`: {'PASS' if aws_gpu.get('ok') else 'FAIL'}.")
    if aws_gpu.get("ok"):
        instances = aws_gpu.get("instances", [])
        lines.append(f"GPU instances found: `{len(instances)}`.")
        if instances:
            lines.append("")
            lines.append("| Instance | Type | State | Name |")
            lines.append("|---|---|---|---|")
            for item in instances:
                lines.append(
                    f"| `{item.get('InstanceId')}` | `{item.get('Type')}` | "
                    f"`{item.get('State')}` | `{item.get('Name')}` |"
                )
    else:
        lines.append(f"Error: `{aws_gpu.get('error')}`.")

    lines.extend(
        [
            "",
            "## Result interpretation",
            "",
            "This is a source and feasibility result, not a replication result. A PASS means "
            "the experiment is ready for an instrumented router-trace run with frozen "
            "prompt-domain splits and pre-registered metrics: expert coalition overlap, "
            "routing mass concentration, and standing-committee persistence under domain "
            "shift. A FAIL would mean the idea remains literature-backed but not runnable "
            "without a different model source or instrumentation path.",
            "",
            "## Next registered gate",
            "",
            "Run an inference-only router audit on the best small public candidate first. "
            "Use train/validation/test only for prompt-domain design and threshold choice: "
            "training prompts define domains, validation fixes reporting thresholds, and "
            "strict holdout prompts decide the claim. Do not fine-tune until the frozen "
            "inference audit reproduces a standing-committee signal.",
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
    cfg_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cfg = load_json(cfg_path)

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    base = cfg["hub_api_base"]
    candidate_results = []

    for candidate in cfg["candidate_models"]:
        repo_id = candidate["repo_id"]
        errors: list[str] = []

        info_url = hub_model_url(base, repo_id)
        info, info_error = fetch_json(info_url, token=token)
        if info_error:
            errors.append(f"model info {info_error}")

        time.sleep(0.25)

        config_url = hub_config_url(base, repo_id)
        config_json, config_error = fetch_json(config_url, token=token)
        if config_error:
            errors.append(f"config {config_error}")

        candidate_results.append(candidate_feasibility(candidate, info, config_json, cfg, token, errors))
        time.sleep(0.25)

    summary = summarize_gate(candidate_results, cfg)
    aws_identity = get_aws_identity(cfg["aws_profile"])
    aws_gpu = get_gpu_instance_summary(cfg["aws_profile"], cfg["aws_region"])

    payload = {
        "experiment_id": cfg["experiment_id"],
        "title": cfg["title"],
        "run_date": cfg["run_date"],
        "decision": summary["decision"],
        "summary": summary,
        "aws_identity": aws_identity,
        "aws_gpu": aws_gpu,
        "candidates": candidate_results,
        "claim_boundary": cfg["claim_boundary"],
    }

    json_path = outdir / "MOE_STANDING_COMMITTEE_SOURCE_GATE_20260623.json"
    report_path = outdir / "MOE_STANDING_COMMITTEE_SOURCE_GATE_20260623.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(cfg, summary, candidate_results, aws_identity, aws_gpu), encoding="utf-8")

    print(json.dumps({"decision": summary["decision"], "report": str(report_path), "summary": summary}, indent=2))
    return 0 if summary["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
