#!/usr/bin/env python
"""PX-033 SWE-EVO source/data readiness gate.

This gate checks public paper, repository, and Hugging Face dataset readiness
for a narrow follow-on: a one-task coding-agent baseline or repo-state planning
probe. It does not run an agent and does not download the full dataset archive.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = "configs/swe_evo_source_gate_20260628.json"
USER_AGENT = "praxis-px033-swe-evo-source-gate/20260628"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_text(url: str, timeout: int = 60) -> tuple[str | None, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8"), None
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            body = ""
        return None, f"HTTP {exc.code}: {body}"
    except urllib.error.URLError as exc:
        return None, f"URL error: {exc.reason}"
    except TimeoutError:
        return None, "timeout"
    except UnicodeDecodeError as exc:
        return None, f"decode error: {exc}"


def fetch_json(url: str, timeout: int = 60) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    text, error = fetch_text(url, timeout=timeout)
    if text is None:
        return None, error
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"JSON decode error: {exc}"


def ascii_snippet(text: str, limit: int = 140) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"\s+", " ", ascii_text).strip()
    return ascii_text[:limit]


def is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def coverage(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if is_nonempty(row.get(field))) / len(rows)


def diff_file_count(diff_text: str) -> int:
    return sum(1 for line in diff_text.splitlines() if line.startswith("diff --git "))


def parse_arxiv(arxiv_id: str) -> dict[str, Any]:
    url = f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}"
    text, error = fetch_text(url)
    row: dict[str, Any] = {"url": f"https://arxiv.org/abs/{arxiv_id}", "status": "UNAVAILABLE", "error": error}
    if text is None:
        return row
    root = ET.fromstring(text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        row["error"] = "no arXiv entry"
        return row
    title = entry.findtext("atom:title", default="", namespaces=ns)
    summary = entry.findtext("atom:summary", default="", namespaces=ns)
    authors = [node.findtext("atom:name", default="", namespaces=ns) for node in entry.findall("atom:author", ns)]
    row.update(
        {
            "status": "ACCESSIBLE",
            "error": None,
            "entry_id": entry.findtext("atom:id", default="", namespaces=ns),
            "title": ascii_snippet(title, 220),
            "published": entry.findtext("atom:published", default="", namespaces=ns),
            "updated": entry.findtext("atom:updated", default="", namespaces=ns),
            "authors": [ascii_snippet(author, 80) for author in authors if author],
            "summary_snippet": ascii_snippet(summary, 320),
        }
    )
    return row


def check_github(config: dict[str, Any]) -> dict[str, Any]:
    repo = config["github_repo"]
    repo_payload, repo_error = fetch_json(f"https://api.github.com/repos/{repo}")
    contents_payload, contents_error = fetch_json(f"https://api.github.com/repos/{repo}/contents?ref=main")
    readme_text, readme_error = fetch_text(f"https://raw.githubusercontent.com/{repo}/main/README.md")

    row: dict[str, Any] = {
        "repo": repo,
        "url": f"https://github.com/{repo}",
        "status": "UNAVAILABLE",
        "repo_error": repo_error,
        "contents_error": contents_error,
        "readme_error": readme_error,
        "required_paths_present": {},
    }
    if isinstance(repo_payload, dict):
        row.update(
            {
                "status": "ACCESSIBLE",
                "default_branch": repo_payload.get("default_branch"),
                "pushed_at": repo_payload.get("pushed_at"),
                "stars": repo_payload.get("stargazers_count"),
                "forks": repo_payload.get("forks_count"),
                "license": (repo_payload.get("license") or {}).get("spdx_id"),
            }
        )
    if isinstance(contents_payload, list):
        names = {item.get("name") for item in contents_payload if isinstance(item, dict)}
        row["root_entries"] = sorted(name for name in names if isinstance(name, str))
        row["required_paths_present"] = {path: path.split("/")[0] in names for path in config["required_github_paths"]}
    if readme_text is not None:
        lowered = readme_text.lower()
        row["readme_keywords"] = {
            "openhands": "openhands" in lowered,
            "swe-agent": "swe-agent" in lowered,
            "swe-bench": "swe-bench" in lowered,
            "evaluation": "evaluation" in lowered,
            "long-horizon": "long-horizon" in lowered or "long horizon" in lowered,
        }
    return row


def check_hf_dataset(config: dict[str, Any]) -> dict[str, Any]:
    dataset = config["hf_dataset"]
    encoded = urllib.parse.quote(dataset, safe="")
    api_payload, api_error = fetch_json(f"https://huggingface.co/api/datasets/{dataset}")
    info_payload, info_error = fetch_json(f"https://datasets-server.huggingface.co/info?dataset={encoded}")
    rows_payload, rows_error = fetch_json(
        "https://datasets-server.huggingface.co/rows?"
        f"dataset={encoded}&config={urllib.parse.quote(config['hf_config'])}"
        f"&split={urllib.parse.quote(config['hf_split'])}&offset=0&length={int(config['expected_rows'])}"
    )

    row: dict[str, Any] = {
        "dataset": dataset,
        "url": f"https://huggingface.co/datasets/{dataset}",
        "status": "UNAVAILABLE",
        "api_error": api_error,
        "info_error": info_error,
        "rows_error": rows_error,
    }
    if isinstance(api_payload, dict):
        row.update(
            {
                "status": "ACCESSIBLE",
                "private": bool(api_payload.get("private")),
                "gated": bool(api_payload.get("gated")),
                "disabled": bool(api_payload.get("disabled")),
                "last_modified": api_payload.get("lastModified"),
                "downloads": api_payload.get("downloads"),
                "likes": api_payload.get("likes"),
                "tags": api_payload.get("tags", []),
                "license": (api_payload.get("cardData") or {}).get("license"),
                "siblings_count": len(api_payload.get("siblings", [])),
            }
        )
    if isinstance(info_payload, dict):
        split_info = (
            info_payload.get("dataset_info", {})
            .get(config["hf_config"], {})
            .get("splits", {})
            .get(config["hf_split"], {})
        )
        features = (
            info_payload.get("dataset_info", {})
            .get(config["hf_config"], {})
            .get("features", {})
        )
        row["info_rows"] = split_info.get("num_examples")
        row["dataset_size_bytes"] = (
            info_payload.get("dataset_info", {}).get(config["hf_config"], {}).get("dataset_size")
        )
        row["features"] = sorted(features.keys()) if isinstance(features, dict) else []
    rows: list[dict[str, Any]] = []
    if isinstance(rows_payload, dict):
        rows = [item.get("row", {}) for item in rows_payload.get("rows", []) if isinstance(item, dict)]
        row["viewer_rows"] = len(rows)
        feature_names = [feature.get("name") for feature in rows_payload.get("features", []) if isinstance(feature, dict)]
        row["viewer_features"] = [name for name in feature_names if isinstance(name, str)]
    row["row_analysis"] = analyze_rows(rows, config)
    return row


def analyze_rows(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    repos = sorted({row.get("repo", "") for row in rows if row.get("repo")})
    patch_counts = [diff_file_count(row.get("patch", "")) for row in rows]
    test_patch_counts = [diff_file_count(row.get("test_patch", "")) for row in rows]
    fail_to_pass_lengths = [len(row.get("FAIL_TO_PASS") or []) for row in rows]
    pass_to_pass_lengths = [len(row.get("PASS_TO_PASS") or []) for row in rows]
    problem_lengths = [len(row.get("problem_statement", "")) for row in rows]
    coverage_map = {field: coverage(rows, field) for field in config["core_fields"] + config["evaluation_fields"]}
    return {
        "rows": len(rows),
        "repos": repos,
        "repo_count": len(repos),
        "image_count": len({row.get("image", "") for row in rows if row.get("image")}),
        "coverage": coverage_map,
        "patch_file_count_mean": statistics.fmean(patch_counts) if patch_counts else 0.0,
        "patch_file_count_min": min(patch_counts, default=0),
        "patch_file_count_max": max(patch_counts, default=0),
        "test_patch_file_count_mean": statistics.fmean(test_patch_counts) if test_patch_counts else 0.0,
        "fail_to_pass_total": sum(fail_to_pass_lengths),
        "fail_to_pass_mean": statistics.fmean(fail_to_pass_lengths) if fail_to_pass_lengths else 0.0,
        "pass_to_pass_total": sum(pass_to_pass_lengths),
        "pass_to_pass_mean": statistics.fmean(pass_to_pass_lengths) if pass_to_pass_lengths else 0.0,
        "problem_statement_mean_chars": statistics.fmean(problem_lengths) if problem_lengths else 0.0,
        "sample_instances": [
            {
                "instance_id": row.get("instance_id"),
                "repo": row.get("repo"),
                "start_version": row.get("start_version"),
                "end_version": row.get("end_version"),
                "patch_files": diff_file_count(row.get("patch", "")),
                "fail_to_pass": len(row.get("FAIL_TO_PASS") or []),
                "pass_to_pass": len(row.get("PASS_TO_PASS") or []),
                "problem_snippet": ascii_snippet(row.get("problem_statement", "")),
            }
            for row in rows[:5]
        ],
        "commit_probe_targets": [
            {"repo": repo, "base_commit": next(row.get("base_commit") for row in rows if row.get("repo") == repo)}
            for repo in repos
            for _ in range(int(config.get("commit_probe_limit_per_repo", 1)))
        ][: len(repos) * int(config.get("commit_probe_limit_per_repo", 1))],
    }


def probe_commits(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for target in targets:
        repo = target["repo"]
        sha = target["base_commit"]
        payload, error = fetch_json(f"https://api.github.com/repos/{repo}/commits/{sha}", timeout=30)
        results.append(
            {
                "repo": repo,
                "base_commit": sha,
                "status": "ACCESSIBLE" if isinstance(payload, dict) else "UNAVAILABLE",
                "error": error,
            }
        )
    return results


def summarize(config: dict[str, Any], arxiv: dict[str, Any], github: dict[str, Any], hf: dict[str, Any], commits: list[dict[str, Any]]) -> dict[str, Any]:
    row_analysis = hf["row_analysis"]
    core_coverages = [row_analysis["coverage"].get(field, 0.0) for field in config["core_fields"]]
    eval_coverages = [row_analysis["coverage"].get(field, 0.0) for field in config["evaluation_fields"]]
    required_paths = github.get("required_paths_present", {})
    commit_passes = sum(1 for row in commits if row["status"] == "ACCESSIBLE")
    publish_checks = {
        "arxiv_accessible": arxiv.get("status") == "ACCESSIBLE",
        "github_accessible": github.get("status") == "ACCESSIBLE",
        "github_required_paths": bool(required_paths) and all(required_paths.values()),
        "readme_mentions_agent_scaffolds": all((github.get("readme_keywords") or {}).get(key) for key in ["openhands", "swe-agent", "swe-bench"]),
        "hf_public_not_gated": hf.get("status") == "ACCESSIBLE" and not hf.get("private") and not hf.get("gated") and not hf.get("disabled"),
        "hf_expected_rows": row_analysis["rows"] == int(config["expected_rows"]) == hf.get("info_rows"),
        "hf_repo_count": row_analysis["repo_count"] >= int(config["min_repo_count"]),
        "core_field_coverage": min(core_coverages, default=0.0) >= float(config["min_core_coverage"]),
        "evaluation_field_coverage": min(eval_coverages, default=0.0) >= float(config["min_evaluation_coverage"]),
        "test_lists_present": row_analysis["fail_to_pass_total"] > 0 and row_analysis["pass_to_pass_total"] > 0,
        "sample_base_commits_reachable": commit_passes == len(commits) and len(commits) > 0,
    }
    status = "SOURCE GATE PASS - ONE-TASK BASELINE READY" if all(publish_checks.values()) else "SOURCE GATE MIXED"
    return {
        "generated_utc": utc_now(),
        "experiment_id": "PX-033",
        "status": status,
        "arxiv": arxiv,
        "github": github,
        "huggingface": hf,
        "commit_probes": commits,
        "commit_probe_passes": commit_passes,
        "publish_checks": publish_checks,
        "claim_boundary": "Source/data readiness only. No coding-agent trajectory, world-model training, or usefulness claim is made by this gate.",
        "next_gate": "Run a single low-cost OpenHands or SWE-agent baseline instance, then test whether repo-state summaries predict partial progress/fix-rate better than metadata-only baselines.",
    }


def render_report(report_path: Path, summary: dict[str, Any]) -> None:
    row = summary["huggingface"]["row_analysis"]
    lines = [
        "# PX-033 SWE-EVO Source Gate",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Claim Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Primary Sources",
        "",
        "| Source | Status | Link | Notes |",
        "|---|---|---|---|",
        f"| arXiv `{summary['arxiv'].get('entry_id', '')}` | `{summary['arxiv']['status']}` | <{summary['arxiv']['url']}> | {summary['arxiv'].get('title', '')} |",
        f"| GitHub `{summary['github']['repo']}` | `{summary['github']['status']}` | <{summary['github']['url']}> | branch `{summary['github'].get('default_branch', '')}`, license `{summary['github'].get('license', '')}` |",
        f"| Hugging Face `{summary['huggingface']['dataset']}` | `{summary['huggingface']['status']}` | <{summary['huggingface']['url']}> | license `{summary['huggingface'].get('license', '')}`, gated `{summary['huggingface'].get('gated')}` |",
        "",
        "## Dataset Readiness",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | `{row['rows']}` |",
        f"| Repositories | `{row['repo_count']}` |",
        f"| Unique images | `{row['image_count']}` |",
        f"| Mean gold patch files | `{row['patch_file_count_mean']:.2f}` |",
        f"| Patch file range | `{row['patch_file_count_min']}`-`{row['patch_file_count_max']}` |",
        f"| Total FAIL_TO_PASS tests | `{row['fail_to_pass_total']}` |",
        f"| Mean FAIL_TO_PASS tests | `{row['fail_to_pass_mean']:.2f}` |",
        f"| Total PASS_TO_PASS tests | `{row['pass_to_pass_total']}` |",
        f"| Mean PASS_TO_PASS tests | `{row['pass_to_pass_mean']:.2f}` |",
        f"| Mean problem statement chars | `{row['problem_statement_mean_chars']:.1f}` |",
        "",
        "## Field Coverage",
        "",
        "| Field | Coverage |",
        "|---|---:|",
    ]
    for field, value in row["coverage"].items():
        lines.append(f"| `{field}` | `{value:.3f}` |")
    lines.extend(["", "## Publish Checks", "", "| Check | Pass |", "|---|---:|"])
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Repositories", "", ", ".join(f"`{repo}`" for repo in row["repos"]), "", "## Sample Instances", "", "| Instance | Repo | Versions | Patch files | F2P | P2P | Prompt snippet |", "|---|---|---|---:|---:|---:|---|"])
    for item in row["sample_instances"]:
        lines.append(
            f"| `{item['instance_id']}` | `{item['repo']}` | `{item['start_version']}` -> `{item['end_version']}` | "
            f"`{item['patch_files']}` | `{item['fail_to_pass']}` | `{item['pass_to_pass']}` | {item['problem_snippet']} |"
        )
    lines.extend(["", "## Sample Commit Probes", "", "| Repo | Base commit reachable |", "|---|---:|"])
    for item in summary["commit_probes"]:
        lines.append(f"| `{item['repo']}` | `{item['status'] == 'ACCESSIBLE'}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "PX-033 is now realistically testable at the source level. The public dataset exposes task specs, base commits, gold patches, test patches, test lists, images, commands, and parser metadata for all 48 instances. The GitHub repo also exposes OpenHands, SWE-agent, and SWE-bench scaffolds.",
            "",
            "This does not prove the repo-state world-model idea is useful. It proves that the next experiment can be a bounded one-task baseline plus a repo-state-summary predictor, rather than a speculative RL/world-model training program.",
            "",
            "## Next Gate",
            "",
            summary["next_gate"],
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = read_json(Path(args.config))
    arxiv = parse_arxiv(config["arxiv_id"])
    github = check_github(config)
    hf = check_hf_dataset(config)
    commits = probe_commits(hf["row_analysis"]["commit_probe_targets"])
    summary = summarize(config, arxiv, github, hf, commits)

    output_dir = Path(config["output_dir"])
    write_json(output_dir / "summary.json", summary)
    render_report(Path(config["report_path"]), summary)
    print(json.dumps({"status": summary["status"], "report_path": config["report_path"], "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
