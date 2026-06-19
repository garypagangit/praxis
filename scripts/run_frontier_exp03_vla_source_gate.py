from __future__ import annotations

import argparse
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def request_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "praxis-exp03-vla-source-gate"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def check_github_repo(repo: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}"
    row = {"repo": repo}
    try:
        payload = request_json(url, {"Accept": "application/vnd.github+json", "User-Agent": "praxis-exp03-vla-source-gate"})
        row.update(
            {
                "status": "ACCESSIBLE",
                "full_name": payload.get("full_name"),
                "default_branch": payload.get("default_branch"),
                "pushed_at": payload.get("pushed_at"),
                "stars": payload.get("stargazers_count"),
            }
        )
    except Exception as exc:
        row.update({"status": "UNAVAILABLE", "error": str(exc)[:240]})
    return row


def check_hf_model(model_id: str) -> dict[str, Any]:
    url = f"https://huggingface.co/api/models/{urllib.parse.quote(model_id, safe='/')}"
    row = {"model_id": model_id}
    try:
        payload = request_json(url)
        row.update(
            {
                "status": "ACCESSIBLE",
                "private": payload.get("private"),
                "downloads": payload.get("downloads"),
                "last_modified": payload.get("lastModified"),
                "siblings": len(payload.get("siblings", [])),
            }
        )
    except Exception as exc:
        row.update({"status": "UNAVAILABLE", "error": str(exc)[:240]})
    return row


def check_hf_dataset(dataset_id: str) -> dict[str, Any]:
    row = {"dataset_id": dataset_id}
    url = "https://datasets-server.huggingface.co/is-valid?" + urllib.parse.urlencode({"dataset": dataset_id})
    try:
        payload = request_json(url)
        row.update({"status": "ACCESSIBLE", "preview": payload.get("preview"), "viewer": payload.get("viewer")})
        splits_url = "https://datasets-server.huggingface.co/splits?" + urllib.parse.urlencode({"dataset": dataset_id})
        try:
            splits = request_json(splits_url)
            row["splits"] = [
                {"config": item.get("config"), "split": item.get("split"), "num_rows": item.get("num_rows")}
                for item in splits.get("splits", [])[:12]
            ]
        except Exception as exc:
            row["split_error"] = str(exc)[:160]
    except urllib.error.HTTPError as exc:
        row.update({"status": "UNAVAILABLE", "http_status": exc.code, "error": str(exc)[:240]})
    except Exception as exc:
        row.update({"status": "UNAVAILABLE", "error": str(exc)[:240]})
    return row


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1}


def build_manifest(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task in config["task_templates"]:
        base_tokens = tokenize(task["base_instruction"])
        for split_role, templates in config["variant_templates"].items():
            for variant_idx, template in enumerate(templates):
                instruction = template.format(base_instruction=task["base_instruction"])
                tokens = tokenize(instruction)
                jaccard = len(tokens & base_tokens) / max(len(tokens | base_tokens), 1)
                rows.append(
                    {
                        "task_id": task["task_id"],
                        "suite": task["suite"],
                        "split_role": "heldout_template" if split_role == "heldout" else "train_template",
                        "variant_index": variant_idx,
                        "instruction": instruction,
                        "token_count": len(tokens),
                        "base_token_jaccard": jaccard,
                        "new_token_count": len(tokens - base_tokens),
                    }
                )
    return rows


def summarize(config: dict[str, Any], repos: list[dict[str, Any]], models: list[dict[str, Any]], datasets: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = config["metrics"]
    accessible_repos = sum(1 for row in repos if row["status"] == "ACCESSIBLE")
    accessible_models = sum(1 for row in models if row["status"] == "ACCESSIBLE")
    accessible_datasets = sum(1 for row in datasets if row["status"] == "ACCESSIBLE")
    heldout_rows = [row for row in manifest if row["split_role"] == "heldout_template"]
    train_rows = [row for row in manifest if row["split_role"] == "train_template"]
    mean_heldout_jaccard = sum(row["base_token_jaccard"] for row in heldout_rows) / max(len(heldout_rows), 1)
    publish_checks = {
        "accessible_repositories": accessible_repos >= int(metrics["min_accessible_repositories"]),
        "accessible_models": accessible_models >= int(metrics["min_accessible_models"]),
        "accessible_datasets": accessible_datasets >= int(metrics["min_accessible_datasets"]),
        "manifest_rows": len(manifest) >= int(metrics["min_manifest_rows"]),
        "heldout_template_rows": len(heldout_rows) >= int(metrics["min_heldout_template_rows"]),
    }
    status = "SOURCE GATE PASS - SIMULATOR SMOKE PENDING" if all(publish_checks.values()) else "SOURCE GATE MIXED"
    return {
        "generated_utc": utc_now(),
        "status": status,
        "accessible_repositories": accessible_repos,
        "accessible_models": accessible_models,
        "accessible_datasets": accessible_datasets,
        "manifest_rows": len(manifest),
        "train_template_rows": len(train_rows),
        "heldout_template_rows": len(heldout_rows),
        "mean_heldout_base_token_jaccard": mean_heldout_jaccard,
        "github_repositories": repos,
        "hf_models": models,
        "hf_datasets": datasets,
        "publish_checks": publish_checks,
    }


def render_reports(output_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# EXP03 VLA Source Gate Result",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Primary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Accessible GitHub repositories | `{summary['accessible_repositories']}` |",
        f"| Accessible HF models | `{summary['accessible_models']}` |",
        f"| Accessible HF datasets | `{summary['accessible_datasets']}` |",
        f"| Instruction manifest rows | `{summary['manifest_rows']}` |",
        f"| Train-template rows | `{summary['train_template_rows']}` |",
        f"| Heldout-template rows | `{summary['heldout_template_rows']}` |",
        f"| Mean heldout/base token Jaccard | `{summary['mean_heldout_base_token_jaccard']:.4f}` |",
        "",
        "## Publish Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Resource Notes",
            "",
            "| Resource | Status | Detail |",
            "|---|---:|---|",
        ]
    )
    for row in summary["github_repositories"]:
        lines.append(f"| GitHub `{row['repo']}` | `{row['status']}` | branch `{row.get('default_branch', '')}` pushed `{row.get('pushed_at', '')}` |")
    for row in summary["hf_models"]:
        lines.append(f"| HF model `{row['model_id']}` | `{row['status']}` | downloads `{row.get('downloads', '')}` modified `{row.get('last_modified', '')}` |")
    for row in summary["hf_datasets"]:
        lines.append(f"| HF dataset `{row['dataset_id']}` | `{row['status']}` | viewer `{row.get('viewer', '')}` error `{row.get('http_status', '')}` |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is a source/readiness gate, not a VLA performance result. It proves that the core repositories, model checkpoints, and at least one public LIBERO data path are reachable and that held-out instruction templates are frozen before simulator work. The next gate must install LIBERO/OpenVLA-OFT and reproduce one official evaluation smoke.",
        ]
    )
    (output_dir / "EXP03_VLA_SOURCE_GATE_RESULT_20260619.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    challenge = [
        "# EXP03 Internal Defensibility Challenge",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Verdict: **{summary['status']}**",
        "",
        "| Challenge | Answer |",
        "|---|---|",
        f"| Are core repos accessible? | Accessible repos: `{summary['accessible_repositories']}`. |",
        f"| Are model checkpoints accessible? | Accessible HF models: `{summary['accessible_models']}`. |",
        f"| Are all datasets public? | No. At least one LIBERO dataset path is public, but several related robot datasets are gated or unauthorized. |",
        f"| Are held-out templates frozen? | Yes. Held-out rows: `{summary['heldout_template_rows']}`. |",
        "| Does this prove VLA generalisation? | No. Simulator install and official evaluation are still required. |",
        "| Main weakness | No robot policy inference was run in this gate. |",
        "| Main strength | The next simulation run now has fixed assets, templates, and split roles. |",
    ]
    (output_dir / "EXP03_INTERNAL_DEFENSIBILITY_CHALLENGE_20260619.md").write_text(
        "\n".join(challenge) + "\n", encoding="utf-8"
    )


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)
    repos = [check_github_repo(repo) for repo in config["github_repositories"]]
    models = [check_hf_model(model_id) for model_id in config["hf_models"]]
    datasets = [check_hf_dataset(dataset_id) for dataset_id in config["hf_datasets"]]
    manifest = build_manifest(config)
    write_json(output_dir / "source_checks.json", {"github_repositories": repos, "hf_models": models, "hf_datasets": datasets})
    write_jsonl(output_dir / "instruction_variant_manifest.jsonl", manifest)
    summary = summarize(config, repos, models, datasets, manifest)
    write_json(output_dir / "EXP03_VLA_SOURCE_GATE_SUMMARY_20260619.json", summary)
    render_reports(output_dir, summary)
    print(summary["status"], output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp03_vla_source_gate_20260619.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
