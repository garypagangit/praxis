#!/usr/bin/env python
"""PX-056 source gate for model-registry identifier hallucination.

This script performs only registry/API feasibility checks. It does not prompt
models, generate identifiers, or collect hallucination-rate data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "praxis-px056-model-registry-source-gate/20260721"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def request_json_or_status(
    url: str,
    token: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token and "huggingface.co" in url:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, headers=headers)
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            content_type = response.headers.get("content-type", "")
            payload: Any = None
            if "json" in content_type.lower() and body:
                payload = json.loads(body.decode("utf-8"))
            return {
                "ok": 200 <= response.status < 300,
                "status_code": response.status,
                "url": response.geturl(),
                "elapsed_s": round(time.time() - started, 3),
                "json_type": type(payload).__name__ if payload is not None else None,
                "json_size": len(payload) if isinstance(payload, (list, dict)) else None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status_code": exc.code,
            "url": url,
            "elapsed_s": round(time.time() - started, 3),
            "error": str(exc),
            "error_message": exc.headers.get("X-Error-Message") or exc.headers.get("x-nv-error-msg"),
        }
    except Exception as exc:  # pragma: no cover - network edge
        return {
            "ok": False,
            "status_code": None,
            "url": url,
            "elapsed_s": round(time.time() - started, 3),
            "error": repr(exc),
        }


def request_json_payload(url: str, token: str | None = None) -> tuple[int | None, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token and "huggingface.co" in url:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception:
        return None, None


def hf_search_exact(cfg: dict[str, Any], kind: str, repo_id: str, token: str | None) -> dict[str, Any]:
    source_key = "huggingface_model_search" if kind == "model" else "huggingface_dataset_search"
    url = cfg["sources"][source_key].format(query=urllib.parse.quote(repo_id, safe=""))
    status, payload = request_json_payload(url, token=token)
    ids: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                candidate = item.get("modelId") or item.get("id") or item.get("_id")
                if candidate:
                    ids.append(str(candidate))
    exact = repo_id in ids
    return {
        "kind": kind,
        "repo_id": repo_id,
        "status_code": status,
        "search_endpoint_ok": status == 200,
        "exact_match": exact,
        "returned_ids_sample": ids[:5],
    }


def summarize(cfg: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    thresholds = cfg["source_gate_thresholds"]
    hf_model_200 = sum(
        1 for check in checks
        if check.get("category") == "hf_existing_model_direct" and check.get("status_code") == 200
    )
    hf_dataset_200 = sum(
        1 for check in checks
        if check.get("category") == "hf_existing_dataset_direct" and check.get("status_code") == 200
    )
    hf_search_ready = all(
        check.get("search_endpoint_ok")
        for check in checks
        if check.get("category") in {"hf_known_search", "hf_missing_search"}
    )
    missing_search_absent = all(
        not check.get("exact_match")
        for check in checks
        if check.get("category") == "hf_missing_search"
    )
    hf_token_present = bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN"))
    ngc_api_200 = any(check.get("category") == "ngc_search_api" and check.get("status_code") == 200 for check in checks)
    ngc_key_present = bool(os.environ.get("NGC_API_KEY") or os.environ.get("NGC_CLI_API_KEY"))
    cosmos_reachable = any(check.get("category") == "cosmos_arxiv_anchor" and check.get("status_code") == 200 for check in checks)

    hf_core_ready = (
        hf_model_200 >= int(thresholds["minimum_hf_existing_model_200"])
        and hf_dataset_200 >= int(thresholds["minimum_hf_existing_dataset_200"])
        and (hf_search_ready if thresholds["require_hf_search_endpoint"] else True)
        and missing_search_absent
    )

    if hf_core_ready and ngc_api_200:
        decision = "PX056_SOURCE_GATE_PASS_HF_AND_NGC_READY"
    elif hf_core_ready:
        decision = "PX056_SOURCE_GATE_PROCEED_HF_PRIMARY_NGC_CONDITIONAL"
    else:
        decision = "PX056_SOURCE_GATE_FAIL_HF_NOT_READY"

    return {
        "decision": decision,
        "hf_core_ready": hf_core_ready,
        "hf_existing_model_200_count": hf_model_200,
        "hf_existing_dataset_200_count": hf_dataset_200,
        "hf_search_ready": hf_search_ready,
        "hf_missing_search_absent": missing_search_absent,
        "hf_token_present": hf_token_present,
        "hf_auth_required_for_private_gated_disambiguation": not hf_token_present,
        "ngc_api_ready": ngc_api_200,
        "ngc_key_present": ngc_key_present,
        "ngc_conditional_drop_if_unresolved": not ngc_api_200,
        "cosmos_anchor_reachable": cosmos_reachable,
    }


def bool_cell(value: bool) -> str:
    return "PASS" if value else "FAIL"


def render_report(cfg: dict[str, Any], summary: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    hf_interpretation = (
        "This run found an HF token in the environment, so Hugging Face existence checks can distinguish "
        "known-missing repositories from ambiguous unauthenticated failures. Final scoring must still keep "
        "401/403 gated/private states separate from nonexistent identifiers."
        if summary["hf_token_present"]
        else "This run did not find an HF token in the environment, so final scoring must use tokened "
        "verification or a review state for 401/403 responses; unauthenticated 401/403 must not be treated "
        "as proof of existence or nonexistence."
    )
    ngc_interpretation = (
        "NGC is feasible for PX-056 because the NGC search probe returned 200 with the configured credential path."
        if summary["ngc_api_ready"]
        else (
            "NGC remains conditional. An NGC key was detected, but the NGC search probe did not return 200. "
            "The key may lack NGC Catalog/Public API Endpoints access, the account may not have the required "
            "org service enabled, or this endpoint may not be stable enough for registered scoring."
            if summary["ngc_key_present"]
            else "NGC remains conditional. No NGC key was detected and the public NGC search probe did not "
            "return an unauthenticated 200 in this environment. Per Contingency C4, the model-registry arm "
            "can proceed as HF-only unless a stable public or authenticated NGC existence-check API is pinned "
            "before data collection."
        )
    )
    lines = [
        "# PX-056 Model Registry Hallucination Source Gate",
        "",
        f"Generated: {now}",
        "",
        f"Praxis ID: `{cfg['praxis_id']}`",
        "",
        f"Status: **{summary['decision']}**",
        "",
        "## Purpose",
        "",
        "This Gate 0 run checks whether PX-056 has a defensible registry-verification surface before any LLM output is generated or scored. It is not a hallucination-rate result and must not be described as a positive experiment.",
        "",
        "## Deconfliction",
        "",
        "PX-056 extends the PX-004/PX-050 deterministic-verifier lane from package/citation identifiers to model and dataset registry identifiers. The new surface is Hugging Face Hub model/dataset loading and, conditionally, NVIDIA NGC catalog resources used in physical-AI and robotics code.",
        "",
        "## Gate Decision",
        "",
        f"Decision: **{summary['decision']}**.",
        "",
        "| Check | Result |",
        "|---|---:|",
        f"| HF existing model direct API | {bool_cell(summary['hf_existing_model_200_count'] >= 1)} |",
        f"| HF existing dataset direct API | {bool_cell(summary['hf_existing_dataset_200_count'] >= 1)} |",
        f"| HF search endpoint available | {bool_cell(summary['hf_search_ready'])} |",
        f"| HF missing identifiers absent from search | {bool_cell(summary['hf_missing_search_absent'])} |",
        f"| HF token present for gated/private disambiguation | {bool_cell(summary['hf_token_present'])} |",
        f"| NGC search API ready with configured credential path | {bool_cell(summary['ngc_api_ready'])} |",
        f"| Cosmos arXiv anchor reachable | {bool_cell(summary['cosmos_anchor_reachable'])} |",
        "",
        "## API Probe Table",
        "",
        "| Category | Target | Status | OK | Notes |",
        "|---|---|---:|---:|---|",
    ]
    for check in checks:
        target = check.get("repo_id") or check.get("target") or check.get("url", "")
        status = check.get("status_code")
        ok = check.get("ok", check.get("search_endpoint_ok", False))
        notes = check.get("error_message") or check.get("error") or ""
        if "exact_match" in check:
            notes = f"exact_match={check['exact_match']}; sample={check.get('returned_ids_sample', [])}"
        lines.append(
            f"| `{check.get('category', '')}` | `{target}` | `{status}` | {bool_cell(bool(ok))} | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Hugging Face Hub is feasible as the primary PX-056 registry because known public model and dataset API checks resolve and the search endpoints are available for exact-match absence checks. "
            + hf_interpretation,
            "",
            ngc_interpretation,
            "",
            "## Next Gate",
            "",
            "Build the PX-056 pilot harness with deterministic extraction for `from_pretrained`, `snapshot_download`, `hf_hub_download`, `datasets.load_dataset`, YAML/JSON repo fields, and HF CLI strings. Run only a small extractor/null-control pilot first. Do not run the full 200-prompt LLM experiment until the HF tokened scoring path is configured and frozen.",
            "",
            "## Claim Boundary",
            "",
            cfg["claim_boundary"],
            "",
            "## Source Links",
            "",
            "- Hugging Face model API: https://huggingface.co/api/models/google-bert/bert-base-uncased",
            "- Hugging Face dataset API: https://huggingface.co/api/datasets/stanfordnlp/imdb",
            "- Hugging Face model search API: https://huggingface.co/api/models?search=bert-base-uncased&limit=20",
            "- NVIDIA NGC API probe: https://api.ngc.nvidia.com/v2/resources?search=cosmos",
            "- Cosmos paper anchor: https://arxiv.org/abs/2606.02800",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PX-056 model-registry source gate.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px056_model_registry_hallucination_source_gate_20260721.json"),
    )
    args = parser.parse_args()
    cfg = load_json(args.config)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    ngc_token = os.environ.get("NGC_API_KEY") or os.environ.get("NGC_CLI_API_KEY")
    ngc_headers = {"Authorization": f"Bearer {ngc_token}"} if ngc_token else None
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, Any]] = []

    for repo_id in cfg["known_existing"]["hf_models"]:
        url = cfg["sources"]["huggingface_model_api"].format(repo_id=urllib.parse.quote(repo_id, safe="/"))
        result = request_json_or_status(url, token=token)
        checks.append({"category": "hf_existing_model_direct", "repo_id": repo_id, **result})
        time.sleep(0.2)

    for repo_id in cfg["known_existing"]["hf_datasets"]:
        url = cfg["sources"]["huggingface_dataset_api"].format(repo_id=urllib.parse.quote(repo_id, safe="/"))
        result = request_json_or_status(url, token=token)
        checks.append({"category": "hf_existing_dataset_direct", "repo_id": repo_id, **result})
        time.sleep(0.2)

    for repo_id in cfg["known_existing"]["hf_models"]:
        checks.append({"category": "hf_known_search", **hf_search_exact(cfg, "model", repo_id, token)})
        time.sleep(0.2)

    for repo_id in cfg["known_missing"]["hf_models"]:
        direct_url = cfg["sources"]["huggingface_model_api"].format(repo_id=urllib.parse.quote(repo_id, safe="/"))
        direct = request_json_or_status(direct_url, token=token)
        checks.append({"category": "hf_missing_model_direct", "repo_id": repo_id, **direct})
        checks.append({"category": "hf_missing_search", **hf_search_exact(cfg, "model", repo_id, token)})
        time.sleep(0.2)

    for repo_id in cfg["known_missing"]["hf_datasets"]:
        direct_url = cfg["sources"]["huggingface_dataset_api"].format(repo_id=urllib.parse.quote(repo_id, safe="/"))
        direct = request_json_or_status(direct_url, token=token)
        checks.append({"category": "hf_missing_dataset_direct", "repo_id": repo_id, **direct})
        checks.append({"category": "hf_missing_search", **hf_search_exact(cfg, "dataset", repo_id, token)})
        time.sleep(0.2)

    ngc_result = request_json_or_status(cfg["sources"]["ngc_search_api"], extra_headers=ngc_headers)
    checks.append(
        {
            "category": "ngc_search_api",
            "target": "cosmos",
            "auth_attempted": bool(ngc_token),
            "auth_method": "bearer_env" if ngc_token else "none",
            **ngc_result,
        }
    )
    time.sleep(0.2)

    ngc_home_result = request_json_or_status(cfg["sources"]["ngc_catalog_home"])
    checks.append({"category": "ngc_catalog_home", "target": "catalog home", **ngc_home_result})
    time.sleep(0.2)

    cosmos_result = request_json_or_status(cfg["sources"]["cosmos_arxiv_anchor"])
    checks.append({"category": "cosmos_arxiv_anchor", "target": "arxiv:2606.02800", **cosmos_result})

    summary = summarize(cfg, checks)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "experiment_id": cfg["experiment_id"],
        "praxis_id": cfg["praxis_id"],
        "title": cfg["title"],
        "summary": summary,
        "checks": checks,
        "claim_boundary": cfg["claim_boundary"],
    }
    write_json(output_dir / "summary.json", payload)
    report = render_report(cfg, summary, checks)
    (output_dir / "PX056_MODEL_REGISTRY_SOURCE_GATE_20260721.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps({"decision": summary["decision"], "report": str(output_dir / "PX056_MODEL_REGISTRY_SOURCE_GATE_20260721.md")}, indent=2))
    return 0 if summary["hf_core_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
