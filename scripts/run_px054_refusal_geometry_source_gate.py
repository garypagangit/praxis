from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_ID = "tomg-group-umd/huginn-0125"
MODEL_API = f"https://huggingface.co/api/models/{MODEL_ID}"
CONFIG_URL = f"https://huggingface.co/{MODEL_ID}/raw/main/config.json"
README_URL = f"https://huggingface.co/{MODEL_ID}/raw/main/README.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=45) as response:
        return json.load(response)


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read().decode("utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_report(summary: dict[str, Any]) -> str:
    checks = summary["checks"]
    lines = [
        "# PX-054 Refusal Geometry Source Gate Result",
        "",
        f"Generated: {summary['generated']}",
        "",
        "## Status",
        "",
        f"**{summary['status']}**",
        "",
        "PX-054 remains a characterization-only experiment. This source gate checks whether the Huginn recurrent-depth model is accessible and whether a safe activation-capture gate is justified. It does not run refusal removal, jailbreak optimization, or safety ablation.",
        "",
        "## Model Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Model | `{summary['model_id']}` |",
        f"| SHA | `{summary['sha']}` |",
        f"| Last modified | `{summary['last_modified']}` |",
        f"| Private | `{summary['private']}` |",
        f"| Gated | `{summary['gated']}` |",
        f"| Disabled | `{summary['disabled']}` |",
        f"| License tag | `{summary['license_tag']}` |",
        f"| Library | `{summary['library_name']}` |",
        f"| Pipeline | `{summary['pipeline_tag']}` |",
        f"| Model type | `{summary['config'].get('model_type')}` |",
        f"| Architecture | `{summary['config'].get('architectures')}` |",
        f"| Recurrent mean steps | `{summary['config'].get('mean_recurrence')}` |",
        f"| Recurrent block layers | `{summary['config'].get('n_layers_in_recurrent_block')}` |",
        f"| Hidden size | `{summary['config'].get('n_embd')}` |",
        "",
        "## Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for name, passed in checks.items():
        lines.append(f"| `{name}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "## Source Anchors",
            "",
            "- Model card: `https://huggingface.co/tomg-group-umd/huginn-0125`",
            "- Recurrent-depth paper: `https://arxiv.org/abs/2502.05171`",
            "- Pretraining/code repository from model card: `https://github.com/seal-rg/recurrent-pretraining`",
            "",
            "## Decision",
            "",
        ]
    )
    if summary["status"] == "SOURCE_GATE_PASS":
        lines.append(
            "The source gate passes and authorizes a bounded activation-capture smoke over safe refusal-style statements, benign-helpful statements, and benign safety-themed controls. The next gate may measure latent-state geometry across `num_steps` without generating unsafe content."
        )
    else:
        lines.append(
            "The source gate does not authorize activation testing. Resolve failed source checks before running model weights."
        )
    lines.extend(
        [
            "",
            "Claim boundary: a source-gate pass is not a positive result. PX-054 can only become positive after measured, reproducible activation geometry clears the registered thresholds.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/refusal_geometry_recurrent_depth/source_gate_20260705"),
    )
    args = parser.parse_args()

    metadata = fetch_json(MODEL_API)
    config = fetch_json(CONFIG_URL)
    readme = fetch_text(README_URL)
    tags = set(metadata.get("tags") or [])
    siblings = {row.get("rfilename") for row in metadata.get("siblings", [])}
    auto_map = config.get("auto_map") or {}

    checks = {
        "model_public": metadata.get("private") is False,
        "model_ungated": metadata.get("gated") in {False, None, "false"},
        "model_not_disabled": metadata.get("disabled") is False,
        "apache_2_license": "license:apache-2.0" in tags or metadata.get("license") == "apache-2.0",
        "transformers_model": metadata.get("library_name") == "transformers",
        "custom_model_code_present": "raven_modeling_minimal.py" in siblings,
        "config_present": "config.json" in siblings,
        "safetensors_index_present": "model.safetensors.index.json" in siblings,
        "auto_model_mapping_present": "AutoModelForCausalLM" in auto_map,
        "recurrent_depth_configured": int(config.get("mean_recurrence", 0)) >= 4
        and int(config.get("n_layers_in_recurrent_block", 0)) > 0,
        "num_steps_documented": "num_steps" in readme,
        "paper_tag_present": "arxiv:2502.05171" in tags,
    }

    summary = {
        "generated": utc_now(),
        "model_id": MODEL_ID,
        "sha": metadata.get("sha"),
        "last_modified": metadata.get("lastModified"),
        "private": metadata.get("private"),
        "gated": metadata.get("gated"),
        "disabled": metadata.get("disabled"),
        "license_tag": "license:apache-2.0" if "license:apache-2.0" in tags else metadata.get("license"),
        "library_name": metadata.get("library_name"),
        "pipeline_tag": metadata.get("pipeline_tag"),
        "tags": sorted(tags),
        "siblings": sorted(s for s in siblings if s),
        "config": {
            key: config.get(key)
            for key in [
                "model_type",
                "architectures",
                "mean_recurrence",
                "n_layers_in_recurrent_block",
                "n_layers_in_prelude",
                "n_layers_in_coda",
                "n_embd",
                "n_heads",
                "torch_dtype",
                "transformers_version",
            ]
        },
        "checks": checks,
        "status": "SOURCE_GATE_PASS" if all(checks.values()) else "SOURCE_GATE_FAIL",
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "summary.json", summary)
    (args.output_dir / "PX054_SOURCE_GATE_RESULT_20260705.md").write_text(
        render_report(summary),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
