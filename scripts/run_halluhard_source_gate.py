#!/usr/bin/env python
"""PX-011 HalluHard source and verifier feasibility gate.

This gate intentionally does not run model generations or paid web-search
judging. It checks the public HalluHard repository, seed files, and judging
pipeline metadata to decide whether a narrow source-backed follow-on is
defensible after the prior EXP04 response-artifact failure.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = "configs/halluhard_source_gate_20260628.json"

PIPELINE_FILES = [
    ".env.example",
    "README.md",
    "pixi.toml",
    "judging_pipeline/strategies/research_questions.py",
    "judging_pipeline/workers/web_searcher.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_text(url: str, timeout: int = 60) -> tuple[str | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "*/*",
            "User-Agent": "praxis-px011-halluhard-source-gate/20260628",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
        return raw.decode("utf-8"), None
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


def fetch_json(url: str, timeout: int = 60) -> tuple[dict[str, Any] | None, str | None]:
    text, error = fetch_text(url, timeout=timeout)
    if text is None:
        return None, error
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"JSON decode error: {exc}"


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL row {line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"invalid JSONL row {line_no}: expected object")
        rows.append(row)
    return rows


def is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def coverage(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if is_nonempty(row.get(key))) / len(rows)


def sample_value(rows: list[dict[str, Any]], key: str) -> str:
    for row in rows:
        value = row.get(key)
        if is_nonempty(value):
            if isinstance(value, list):
                return ascii_snippet(", ".join(str(item) for item in value[:3]))
            text = str(value)
            return ascii_snippet(text)
    return ""


def ascii_snippet(text: str, limit: int = 120) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"\s+", " ", ascii_text).strip()
    return ascii_text[:limit]


def summarize_dataset(name: str, spec: dict[str, Any], raw_base_url: str) -> dict[str, Any]:
    url = f"{raw_base_url.rstrip('/')}/{spec['path']}"
    text, error = fetch_text(url)
    if text is None:
        return {
            "name": name,
            "path": spec["path"],
            "url": url,
            "status": "UNAVAILABLE",
            "error": error,
            "rows": 0,
            "keys": [],
            "required_key_coverage": {},
            "sample_values": {},
        }

    rows = parse_jsonl(text)
    keys = sorted({key for row in rows for key in row.keys()})
    required = list(spec.get("required_keys", []))
    return {
        "name": name,
        "path": spec["path"],
        "url": url,
        "status": "ACCESSIBLE",
        "rows": len(rows),
        "keys": keys,
        "required_key_coverage": {key: coverage(rows, key) for key in required},
        "sample_values": {key: sample_value(rows, key) for key in required},
        "source_backed_role": spec.get("source_backed_role", ""),
    }


def fetch_pipeline_files(raw_base_url: str) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for path in PIPELINE_FILES:
        url = f"{raw_base_url.rstrip('/')}/{path}"
        text, error = fetch_text(url)
        files[path] = {
            "url": url,
            "status": "ACCESSIBLE" if text is not None else "UNAVAILABLE",
            "error": error,
            "text": text or "",
        }
    return files


def extract_env_keys(text: str) -> list[str]:
    keys = []
    for line in text.splitlines():
        match = re.match(r"^\s*([A-Z0-9_]+)\s*=", line)
        if match:
            keys.append(match.group(1))
    return sorted(set(keys))


def pipeline_signals(files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    readme = files.get("README.md", {}).get("text", "")
    env = files.get(".env.example", {}).get("text", "")
    strategy = files.get("judging_pipeline/strategies/research_questions.py", {}).get("text", "")
    web_searcher = files.get("judging_pipeline/workers/web_searcher.py", {}).get("text", "")
    pixi = files.get("pixi.toml", {}).get("text", "")
    return {
        "readme_mentions_webscraper": "--type webscraper" in readme or "webscraper" in readme,
        "readme_mentions_coding_direct": "--type coding_direct" in readme or "coding_direct" in readme,
        "env_keys": extract_env_keys(env),
        "pixi_mentions_datasets": "datasets" in pixi,
        "pixi_mentions_openai": "openai" in pixi.lower(),
        "research_strategy_claim_fields": {
            "claimed_content": "claimed_content" in strategy,
            "full_citation": "full_citation" in strategy,
            "claimed_title": "claimed_title" in strategy,
            "claimed_authors": "claimed_authors" in strategy,
            "claimed_year": "claimed_year" in strategy,
            "claimed_url": "claimed_url" in strategy,
        },
        "research_strategy_judgment_fields": {
            "reference_grounding": "reference_grounding" in strategy,
            "content_grounding": "content_grounding" in strategy,
            "hallucination": "hallucination" in strategy,
            "abstention": "abstention" in strategy,
            "verification_error": "verification_error" in strategy,
        },
        "web_search_uses_serper": "Serper" in web_searcher or "serper" in web_searcher,
        "web_search_mentions_html": "HTML" in web_searcher or "html" in web_searcher,
        "web_search_mentions_pdf": "PDF" in web_searcher or "pdf" in web_searcher,
    }


def repo_summary(config: dict[str, Any]) -> dict[str, Any]:
    repo_payload, repo_error = fetch_json(config["github_api_repo_url"])
    tree_payload, tree_error = fetch_json(config["github_api_tree_url"])
    tree_paths: list[str] = []
    if tree_payload and isinstance(tree_payload.get("tree"), list):
        tree_paths = sorted(
            str(item.get("path", "")) for item in tree_payload["tree"] if isinstance(item, dict) and item.get("path")
        )
    return {
        "repo_url": config["repo_url"],
        "arxiv_url": config["arxiv_url"],
        "website_url": config["website_url"],
        "github_api_repo_url": config["github_api_repo_url"],
        "github_api_tree_url": config["github_api_tree_url"],
        "repo_accessible": repo_payload is not None,
        "repo_error": repo_error,
        "default_branch": repo_payload.get("default_branch") if repo_payload else None,
        "created_at": repo_payload.get("created_at") if repo_payload else None,
        "updated_at": repo_payload.get("updated_at") if repo_payload else None,
        "pushed_at": repo_payload.get("pushed_at") if repo_payload else None,
        "description": repo_payload.get("description") if repo_payload else None,
        "tree_accessible": tree_payload is not None,
        "tree_error": tree_error,
        "tree_path_count": len(tree_paths),
        "relevant_tree_paths": [
            path
            for path in tree_paths
            if path in PIPELINE_FILES or any(path == spec["path"] for spec in config["datasets"].values())
        ],
    }


def lane_decisions(datasets: dict[str, dict[str, Any]], thresholds: dict[str, Any]) -> dict[str, dict[str, Any]]:
    research = datasets.get("research_questions", {})
    legal = datasets.get("legal_cases", {})
    medical = datasets.get("medical_guidelines", {})
    coding = datasets.get("coding", {})

    research_rows = int(research.get("rows", 0))
    research_cov = research.get("required_key_coverage", {})
    public_identifier_coverage = 0.0
    if research_rows:
        public_identifier_coverage = max(float(research_cov.get("doi", 0.0)), float(research_cov.get("arxiv_id", 0.0)))
    title_abstract_coverage = min(float(research_cov.get("title", 0.0)), float(research_cov.get("abstract", 0.0)))

    medical_cov = medical.get("required_key_coverage", {})
    legal_cov = legal.get("required_key_coverage", {})
    coding_cov = coding.get("required_key_coverage", {})

    return {
        "research_questions": {
            "decision": "PASS_FOR_SOURCE_BACKED_PROTOTYPE"
            if (
                research.get("status") == "ACCESSIBLE"
                and research_rows >= int(thresholds["min_research_rows"])
                and public_identifier_coverage >= float(thresholds["min_research_public_identifier_coverage"])
                and title_abstract_coverage >= float(thresholds["min_research_title_abstract_coverage"])
            )
            else "BLOCKED",
            "reason": "Rows include stable scholarly metadata, public identifiers, titles, and abstracts. This supports a deterministic metadata/source verifier prototype before any model-response claims.",
            "public_identifier_coverage": public_identifier_coverage,
            "title_abstract_coverage": title_abstract_coverage,
        },
        "legal_cases": {
            "decision": "BLOCKED_FOR_STRICT_PUBLIC_SOURCE_VERIFIER",
            "reason": "Rows expose case IDs, questions, categories, and source labels, but not public opinion text, public URLs, or full citations. A Westlaw-backed lane is not an open verifier without additional public legal sources.",
            "case_id_coverage": float(legal_cov.get("case_id", 0.0)),
            "source_coverage": float(legal_cov.get("source", 0.0)),
        },
        "medical_guidelines": {
            "decision": "PARTIAL_NEEDS_SOURCE_URLS_OR_AUTHORITY_MAP",
            "reason": "Rows include guideline text and source labels, so local text matching is possible. Public authority verification is weak without exact guideline URLs, version IDs, or PubMed/clinical-source mappings.",
            "guideline_text_coverage": float(medical_cov.get("guideline_text", 0.0)),
            "source_coverage": float(medical_cov.get("source", 0.0)),
        },
        "coding": {
            "decision": "FEASIBLE_ONLY_AS_CODING_DIRECT_LANE",
            "reason": "Rows support coding-task response checks, but this is not the same source-backed literature verifier claim as PX-011.",
            "prompt_coverage": float(coding_cov.get("prompt", 0.0)),
            "language_coverage": float(coding_cov.get("language", 0.0)),
        },
    }


def read_prior_guardrail(path: Path, configured: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": configured.get("status"),
            "report_path": path.as_posix(),
            "report_accessible": False,
            "evidence_numeric_strict_holdout_f1": configured.get("evidence_numeric_strict_holdout_f1"),
            "response_only_strict_holdout_f1": configured.get("response_only_strict_holdout_f1"),
        }
    text = path.read_text(encoding="utf-8")
    return {
        "status": configured.get("status"),
        "report_path": path.as_posix(),
        "report_accessible": True,
        "evidence_numeric_strict_holdout_f1": configured.get("evidence_numeric_strict_holdout_f1"),
        "response_only_strict_holdout_f1": configured.get("response_only_strict_holdout_f1"),
        "mentions_response_artifact_failure": "RESPONSE ARTIFACT BASELINE WINS" in text
        or "response-only artifact baseline" in text,
    }


def build_summary(config: dict[str, Any]) -> dict[str, Any]:
    repo = repo_summary(config)
    datasets = {
        name: summarize_dataset(name, spec, config["raw_base_url"]) for name, spec in config["datasets"].items()
    }
    files = fetch_pipeline_files(config["raw_base_url"])
    signals = pipeline_signals(files)
    decisions = lane_decisions(datasets, config["thresholds"])
    prior = read_prior_guardrail(Path(config["prior_guardrail_report"]), config["prior_guardrail_failure"])

    total_rows = sum(int(row.get("rows", 0)) for row in datasets.values())
    data_files_accessible = all(row.get("status") == "ACCESSIBLE" for row in datasets.values())
    research_decision = decisions["research_questions"]["decision"]
    research_gate_checks = {
        "github_repo_accessible": bool(repo["repo_accessible"]),
        "github_tree_accessible": bool(repo["tree_accessible"]),
        "data_files_accessible": data_files_accessible,
        "total_seed_rows": total_rows >= int(config["thresholds"]["min_total_seed_rows"]),
        "research_rows": int(datasets["research_questions"].get("rows", 0))
        >= int(config["thresholds"]["min_research_rows"]),
        "research_public_identifier_coverage": decisions["research_questions"]["public_identifier_coverage"]
        >= float(config["thresholds"]["min_research_public_identifier_coverage"]),
        "research_title_abstract_coverage": decisions["research_questions"]["title_abstract_coverage"]
        >= float(config["thresholds"]["min_research_title_abstract_coverage"]),
        "pipeline_webscraper_mode_detected": bool(signals["readme_mentions_webscraper"]),
        "research_judgment_fields_detected": all(signals["research_strategy_judgment_fields"].values()),
        "prior_exp04_guardrail_recorded": bool(prior.get("mentions_response_artifact_failure")),
    }
    status = (
        "SOURCE GATE PASS - RESEARCH LANE ONLY"
        if all(research_gate_checks.values()) and research_decision == "PASS_FOR_SOURCE_BACKED_PROTOTYPE"
        else "SOURCE GATE MIXED"
    )
    scope_limitations = {
        "not_pubmed_specific": True,
        "legal_lane_public_verifier_blocked": decisions["legal_cases"]["decision"].startswith("BLOCKED"),
        "medical_lane_needs_authority_map": decisions["medical_guidelines"]["decision"].startswith("PARTIAL"),
        "coding_lane_not_literature_verifier": decisions["coding"]["decision"].startswith("FEASIBLE_ONLY"),
        "requires_response_only_baseline_before_model_claim": True,
    }

    return {
        "experiment_id": config["experiment_id"],
        "title": config["title"],
        "generated_utc": utc_now(),
        "status": status,
        "repo": repo,
        "datasets": datasets,
        "pipeline_signals": signals,
        "lane_decisions": decisions,
        "prior_exp04_guardrail": prior,
        "total_seed_rows": total_rows,
        "research_gate_checks": research_gate_checks,
        "scope_limitations": scope_limitations,
        "claim_boundary": (
            "This gate supports only a research_questions source-backed verifier prototype over HalluHard metadata. "
            "It does not support a broad all-domain HalluHard claim, a PubMed-specific claim, or any model-response "
            "claim until a response-only baseline is run."
        ),
        "next_registered_gate": (
            "Build a frozen research_questions prototype that verifies generated citation claims against DOI/arXiv/title/"
            "abstract metadata, reports abstentions and verification errors, and compares against response-only and "
            "metadata-only baselines on a sealed split."
        ),
        "sources": [
            config["repo_url"],
            config["arxiv_url"],
            config["website_url"],
            config["github_api_repo_url"],
            config["github_api_tree_url"],
        ]
        + [row["url"] for row in datasets.values()]
        + [meta["url"] for meta in files.values()],
    }


def fmt_bool(value: bool) -> str:
    return "PASS" if value else "FAIL"


def pct(value: float) -> str:
    return f"{value:.3f}"


def render_report(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# PX-011 HalluHard Source-Backed Verifier Source Gate",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Praxis framing",
        "",
        "Working title: `HalluHard Source-Backed Verifier Audit`.",
        "",
        "This gate asks whether HalluHard is ready for a Praxis verifier experiment without repeating the EXP04 failure, where response-only artifacts beat the evidence-aware verifier on strict holdout.",
        "",
        "The intended claim is deliberately narrow: can a HalluHard literature lane support a deterministic source-backed verifier prototype before spending GPU/API budget on model generations?",
        "",
        "## Decision",
        "",
        f"Decision: **{summary['status']}**.",
        "",
        "The research-questions lane is ready for a bounded follow-on. The full HalluHard benchmark is not ready for one broad source-backed claim because legal, medical, and coding lanes require different verifier evidence.",
        "",
        "## Primary metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total public seed rows found | `{summary['total_seed_rows']}` |",
        f"| GitHub repository accessible | `{fmt_bool(bool(summary['repo']['repo_accessible']))}` |",
        f"| GitHub tree accessible | `{fmt_bool(bool(summary['repo']['tree_accessible']))}` |",
        f"| Repository pushed at | `{summary['repo']['pushed_at']}` |",
        f"| Pipeline webscraper mode detected | `{fmt_bool(bool(summary['pipeline_signals']['readme_mentions_webscraper']))}` |",
        f"| Research judgment fields detected | `{fmt_bool(all(summary['pipeline_signals']['research_strategy_judgment_fields'].values()))}` |",
        f"| Prior EXP04 guardrail recorded | `{fmt_bool(bool(summary['prior_exp04_guardrail'].get('mentions_response_artifact_failure')))}` |",
        "",
        "## Research gate checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for key, value in summary["research_gate_checks"].items():
        lines.append(f"| `{key}` | `{bool(value)}` |")

    lines.extend(
        [
            "",
            "## Lane feasibility",
            "",
            "| Lane | Rows | Decision | Reason |",
            "|---|---:|---|---|",
        ]
    )
    for name, dataset in summary["datasets"].items():
        decision = summary["lane_decisions"][name]
        lines.append(
            f"| `{name}` | `{dataset.get('rows', 0)}` | `{decision['decision']}` | {decision['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Dataset schema and coverage",
            "",
            "| Lane | Required field coverage | Sample fields |",
            "|---|---|---|",
        ]
    )
    for name, dataset in summary["datasets"].items():
        coverage_bits = [
            f"`{key}`={pct(float(value))}" for key, value in dataset.get("required_key_coverage", {}).items()
        ]
        sample_bits = [
            f"`{key}`: {value}" for key, value in dataset.get("sample_values", {}).items() if value
        ]
        lines.append(f"| `{name}` | {'; '.join(coverage_bits)} | {'; '.join(sample_bits[:3])} |")

    signals = summary["pipeline_signals"]
    env_keys = ", ".join(f"`{key}`" for key in signals["env_keys"])
    claim_fields = ", ".join(
        f"`{key}`={value}" for key, value in signals["research_strategy_claim_fields"].items()
    )
    judgment_fields = ", ".join(
        f"`{key}`={value}" for key, value in signals["research_strategy_judgment_fields"].items()
    )

    lines.extend(
        [
            "",
            "## Pipeline signals",
            "",
            f"- README webscraper judging mode detected: `{signals['readme_mentions_webscraper']}`.",
            f"- README coding_direct judging mode detected: `{signals['readme_mentions_coding_direct']}`.",
            f"- Environment keys listed by the repo: {env_keys}.",
            f"- Research claim fields detected: {claim_fields}.",
            f"- Research judgment fields detected: {judgment_fields}.",
            f"- Web search worker uses Serper: `{signals['web_search_uses_serper']}`; mentions HTML: `{signals['web_search_mentions_html']}`; mentions PDF: `{signals['web_search_mentions_pdf']}`.",
            "",
            "## EXP04 guardrail",
            "",
            f"Prior report: `{summary['prior_exp04_guardrail']['report_path']}`.",
            "",
            f"EXP04 status was `{summary['prior_exp04_guardrail']['status']}`. Evidence+numeric strict-holdout F1 was `{summary['prior_exp04_guardrail']['evidence_numeric_strict_holdout_f1']}`, while the response-only strict-holdout F1 was `{summary['prior_exp04_guardrail']['response_only_strict_holdout_f1']}`. PX-011 therefore cannot be promoted unless a future model-response gate beats response-only baselines on a sealed split.",
            "",
            "## Claim boundary",
            "",
            summary["claim_boundary"],
            "",
            "## Next registered gate",
            "",
            summary["next_registered_gate"],
            "",
            "## Sources",
            "",
        ]
    )
    for source in summary["sources"]:
        lines.append(f"- {source}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = read_json(Path(args.config))
    summary = build_summary(config)
    output = config["output"]
    run_dir = Path(output["run_dir"])
    report_dir = Path(output["report_dir"])
    write_json(run_dir / output["summary_file"], summary)
    render_report(summary, report_dir / output["report_file"])
    print(json.dumps({"status": summary["status"], "total_seed_rows": summary["total_seed_rows"]}, indent=2))
    return 0 if summary["status"].startswith("SOURCE GATE PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
