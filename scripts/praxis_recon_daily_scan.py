#!/usr/bin/env python3
"""Daily literature scanner for Praxis Recon.

The script uses public metadata APIs, compares results against a small seen-state
file, and emits a Markdown report suitable for a GitHub issue alert.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


OPENALEX_API = "https://api.openalex.org/works"
USER_AGENT = "PraxisReconDailyScan/1.0 (https://github.com/garypagangit/praxis)"

OPPORTUNITY_TERMS = {
    "future work": 4,
    "future research": 4,
    "open problem": 4,
    "limitation": 3,
    "limitations": 3,
    "benchmark": 3,
    "evaluation": 2,
    "dataset": 2,
    "agent": 2,
    "tool call": 3,
    "tool use": 3,
    "hallucination": 3,
    "provenance": 3,
    "verification": 3,
    "verifier": 3,
    "security": 2,
    "safety": 2,
    "alignment": 2,
    "interpretability": 2,
    "mixture of experts": 2,
    "recurrent": 2,
    "refusal": 3,
    "cyber threat intelligence": 3,
    "MITRE ATT&CK": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Praxis Recon daily literature scan.")
    parser.add_argument("--config", default="configs/praxis_recon_topics.json", help="Topic configuration JSON.")
    parser.add_argument("--state", default="data/praxis-recon/seen_works.json", help="Seen-work state JSON.")
    parser.add_argument("--report-dir", default="reports/praxis_recon_daily", help="Directory for daily Markdown reports.")
    parser.add_argument("--lookback-days", type=int, default=2, help="Publication-date lookback window.")
    parser.add_argument("--max-per-topic", type=int, default=15, help="Maximum API results to inspect per topic.")
    parser.add_argument("--min-score", type=int, default=2, help="Minimum opportunity score to flag.")
    parser.add_argument("--dry-run", action="store_true", help="Write reports but do not update seen-state.")
    return parser.parse_args()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    terms: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for position in positions:
            terms.append((position, word))
    return clean_text(" ".join(word for _, word in sorted(terms)))


def repair_mojibake(value: str) -> str:
    if not any(marker in value for marker in ("\u00e2", "\u00c2", "\u00ef")):
        return value
    try:
        repaired = value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    original_markers = sum(value.count(marker) for marker in ("\u00e2", "\u00c2", "\u00ef"))
    repaired_markers = sum(repaired.count(marker) for marker in ("\u00e2", "\u00c2", "\u00ef"))
    return repaired if repaired_markers < original_markers else value


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", repair_mojibake(str(value or ""))).strip()


def work_uid(work: dict[str, Any]) -> str:
    doi = clean_text(work.get("doi")).lower()
    if doi:
        return doi
    openalex_id = clean_text(work.get("id"))
    if openalex_id:
        return openalex_id
    return f"{clean_text(work.get('display_name')).lower()}::{clean_text(work.get('publication_date'))}"


def landing_url(work: dict[str, Any]) -> str:
    primary = work.get("primary_location") or {}
    url = clean_text(primary.get("landing_page_url"))
    if url:
        return url
    doi = clean_text(work.get("doi"))
    return doi or clean_text(work.get("id"))


def venue_name(work: dict[str, Any]) -> str:
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    return clean_text(source.get("display_name")) or "Unknown venue"


def author_names(work: dict[str, Any], limit: int = 4) -> str:
    authorships = work.get("authorships") or []
    names = []
    for author in authorships[:limit]:
        names.append(clean_text((author.get("author") or {}).get("display_name")))
    names = [name for name in names if name]
    if len(authorships) > limit:
        names.append("et al.")
    return ", ".join(names) or "Unknown authors"


def score_work(work: dict[str, Any], topic: dict[str, Any]) -> tuple[int, list[str], str]:
    title = clean_text(work.get("display_name"))
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    text = f"{title} {abstract}".lower()
    score = 0
    tags: list[str] = []

    for term, weight in OPPORTUNITY_TERMS.items():
        if term.lower() in text:
            score += weight
            tags.append(term)

    for term in topic.get("priority_terms", []):
        if str(term).lower() in text:
            score += 3
            tags.append(str(term))

    if work.get("is_retracted"):
        score -= 8
        tags.append("retracted")

    tags = sorted(set(tags))
    why = "Matches Praxis topic terms and opportunity language." if tags else "Matches topic query."
    return max(score, 0), tags[:10], why


def fetch_openalex(
    topic: dict[str, Any],
    start_date: dt.date,
    end_date: dt.date,
    max_per_topic: int,
    mailto: str | None,
) -> list[dict[str, Any]]:
    filters = [
        f"from_publication_date:{start_date.isoformat()}",
        f"to_publication_date:{end_date.isoformat()}",
    ]
    params = {
        "search": topic["query"],
        "filter": ",".join(filters),
        "sort": "publication_date:desc",
        "per-page": str(max(1, min(max_per_topic, 200))),
    }
    if mailto:
        params["mailto"] = mailto
    url = f"{OPENALEX_API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload.get("results", [])
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504}:
                raise
            retry_after = clean_text(exc.headers.get("Retry-After"))
            try:
                wait_seconds = float(retry_after) if retry_after else 1.5 * (attempt + 1)
            except ValueError:
                wait_seconds = 1.5 * (attempt + 1)
            time.sleep(min(max(wait_seconds, 1.0), 20.0))
        except urllib.error.URLError as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    if last_error:
        raise last_error
    return []


def normalize_work(
    work: dict[str, Any],
    topic: dict[str, Any],
    score: int,
    tags: list[str],
    why: str,
) -> dict[str, Any]:
    return {
        "uid": work_uid(work),
        "source": "OpenAlex",
        "topic_id": topic["id"],
        "topic": topic["name"],
        "title": clean_text(work.get("display_name")),
        "authors": author_names(work),
        "published": clean_text(work.get("publication_date")),
        "year": work.get("publication_year"),
        "type": clean_text(work.get("type")),
        "venue": venue_name(work),
        "doi": clean_text(work.get("doi")),
        "url": landing_url(work),
        "score": score,
        "tags": tags,
        "why_flagged": why,
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index"))[:1400],
    }


def scan_topics(config: dict[str, Any], state: dict[str, Any], args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[str]]:
    today = dt.date.today()
    start_date = today - dt.timedelta(days=max(args.lookback_days, 1))
    seen = state.setdefault("seen", {})
    allowed_types = set(config.get("allowed_types") or [])
    mailto = os.environ.get("PRAXIS_RECON_MAILTO") or None
    findings: list[dict[str, Any]] = []
    errors: list[str] = []

    for topic in config.get("topics", []):
        try:
            works = fetch_openalex(topic, start_date, today, args.max_per_topic, mailto)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"{topic.get('id', 'unknown')}: {exc}")
            continue

        for work in works:
            if allowed_types and clean_text(work.get("type")) not in allowed_types:
                continue
            uid = work_uid(work)
            if uid in seen:
                continue
            score, tags, why = score_work(work, topic)
            if score < args.min_score:
                continue
            finding = normalize_work(work, topic, score, tags, why)
            findings.append(finding)
            if not args.dry_run:
                seen[uid] = {
                    "first_seen": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "title": finding["title"],
                    "topic_id": finding["topic_id"],
                    "published": finding["published"],
                    "url": finding["url"],
                    "score": finding["score"],
                }
        time.sleep(1.0)

    findings.sort(key=lambda item: (item["score"], item["published"]), reverse=True)
    return findings, errors


def markdown_report(findings: list[dict[str, Any]], errors: list[str], args: argparse.Namespace) -> str:
    generated = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "# Praxis Recon Daily Literature Scan",
        "",
        f"Generated: {generated}",
        f"Lookback window: {args.lookback_days} day(s)",
        f"Minimum score: {args.min_score}",
        f"New flagged works: {len(findings)}",
        "",
    ]
    if findings:
        lines.extend(
            [
                "## Flagged Works",
                "",
                "| Rank | Score | Topic | Published | Title | Venue | Link |",
                "| --- | ---: | --- | --- | --- | --- | --- |",
            ],
        )
        for idx, item in enumerate(findings, start=1):
            title = item["title"].replace("|", "\\|")
            venue = item["venue"].replace("|", "\\|")
            lines.append(
                f"| {idx} | {item['score']} | {item['topic']} | {item['published']} | {title} | {venue} | [source]({item['url']}) |",
            )
        lines.append("")
        lines.append("## Triage Notes")
        lines.append("")
        for idx, item in enumerate(findings, start=1):
            lines.extend(
                [
                    f"### {idx}. {item['title']}",
                    "",
                    f"- Topic: {item['topic']}",
                    f"- Authors: {item['authors']}",
                    f"- Published: {item['published']}",
                    f"- Venue/type: {item['venue']} / {item['type']}",
                    f"- DOI: {item['doi'] or 'not provided'}",
                    f"- URL: {item['url']}",
                    f"- Opportunity score: {item['score']}",
                    f"- Matched tags: {', '.join(item['tags']) if item['tags'] else 'topic query only'}",
                    f"- Why flagged: {item['why_flagged']}",
                    "",
                    "Abstract excerpt:",
                    "",
                    f"> {item['abstract'] or 'No abstract text returned by metadata API.'}",
                    "",
                    "Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.",
                    "",
                ],
            )
    else:
        lines.extend(
            [
                "## No New Flagged Works",
                "",
                "No unseen works met the configured threshold in this scan window.",
                "",
            ],
        )

    if errors:
        lines.extend(["## API Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    return "\n".join(lines)


def write_reports(report_dir: Path, report: str) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    dated = report_dir / f"PRAXIS_RECON_DAILY_SCAN_{stamp}.md"
    latest = report_dir / "PRAXIS_RECON_DAILY_SCAN_latest.md"
    dated.write_text(report + "\n", encoding="utf-8")
    latest.write_text(report + "\n", encoding="utf-8")
    return dated, latest


def write_outputs(findings: list[dict[str, Any]], dated: Path, latest: Path) -> None:
    summary_env = latest.parent / "summary.env"
    summary_env.write_text(
        "\n".join(
            [
                f"NEW_COUNT={len(findings)}",
                f"REPORT_PATH={latest.as_posix()}",
                f"DATED_REPORT_PATH={dated.as_posix()}",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a", encoding="utf-8") as handle:
            handle.write(f"new_count={len(findings)}\n")
            handle.write(f"report_path={latest.as_posix()}\n")
            handle.write(f"dated_report_path={dated.as_posix()}\n")


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    state_path = Path(args.state)
    report_dir = Path(args.report_dir)

    config = read_json(config_path, {})
    if not config.get("topics"):
        raise SystemExit(f"No topics found in {config_path}")

    state = read_json(
        state_path,
        {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "seen": {},
        },
    )
    findings, errors = scan_topics(config, state, args)
    report = markdown_report(findings, errors, args)
    dated, latest = write_reports(report_dir, report)
    write_outputs(findings, dated, latest)

    if not args.dry_run:
        state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        state["seen_count"] = len(state.get("seen", {}))
        write_json(state_path, state)

    print(
        json.dumps(
            {
                "new_count": len(findings),
                "errors": errors,
                "report_path": latest.as_posix(),
                "dated_report_path": dated.as_posix(),
                "dry_run": args.dry_run,
            },
            indent=2,
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
