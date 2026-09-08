"""Update only verified execution milestones and render a file-safe HTML snapshot."""
import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id", choices=["001", "002", "003"])
    p.add_argument("--status")
    p.add_argument("--evidence")
    p.add_argument("--next")
    p.add_argument("--report")
    p.add_argument("--pdf")
    p.add_argument("--docx")
    p.add_argument("--scientifically-complete", action="store_true")
    args = p.parse_args()
    data = json.loads((ROOT / "status.json").read_text(encoding="utf-8"))
    for experiment in data["experiments"]:
        if experiment["id"] == args.id:
            for key in ["status", "evidence", "next", "report", "pdf", "docx"]:
                value = getattr(args, key)
                if value is not None:
                    experiment[key] = value
            if args.scientifically_complete:
                experiment["scientifically_complete"] = True
    data["updated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    data["scientific_results_complete"] = sum(bool(x.get("scientifically_complete")) for x in data["experiments"])
    (ROOT / "status.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    cards = []
    rows = []
    for e in data["experiments"]:
        links = [("pdf", "PDF report"), ("docx", "Word report"), ("report", "Methods and results")]
        report = ' | '.join('<a href="' + html.escape(e[key], quote=True) + '">' + label + '</a>' for key, label in links if e.get(key))
        cards.append('<article><div class="eyebrow">Final Praxis ' + e["id"] + '</div><h2>' + html.escape(e["title"]) + '</h2><span class="status">' + html.escape(e["status"]) + '</span><p>' + html.escape(e["evidence"]) + '</p><p class="muted">' + html.escape(e["next"]) + '</p>' + report + '</article>')
        link = f'[Report](final_praxis/{e["report"]})' if e.get("report") else "Pending"
        rows.append(f'| **{e["id"]} - {e["title"]}** | {e["status"]} | {e["evidence"]} | {e["next"]} | {link} |')
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    page = re.sub(r'(<section class="grid" id="cards" aria-live="polite">).*?(</section>)', lambda m: m[1] + "".join(cards) + m[2], page, flags=re.S)
    page = re.sub(r'(<p id="updated" class="muted">).*?(</p>)', lambda m: m[1] + "Updated " + data["updated_utc"] + m[2], page)
    page = re.sub(r'(<p id="truth">).*?(</p>)', lambda m: m[1] + str(data["scientific_results_complete"]) + " of 3 experiments have completed independent scientific verification. Fixture results are infrastructure checks; incomplete runs are not classified as scientific positives or negatives." + m[2], page)
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    markdown = "# Final Praxis Proposals\n\nUpdated: " + data["updated_utc"] + "\nBranch: `Final-Praxis-Proposals`\n\n"
    markdown += "[Live experiment dashboard](final_praxis/index.html) | [Execution and compute plan](final_praxis/execution/20260908/EXECUTION_PLAN.md) | [Frozen execution runbook](FINAL_PRAXIS_EXECUTION_RUNBOOK.md)\n\n"
    markdown += "## Portfolio dashboard\n\n| Final Praxis | Current status | Evidence | Next action | Report |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    markdown += "## Scientific truth status\n\n" + str(data["scientific_results_complete"]) + " of 3 experiments have completed independent scientific verification. Local fixture validation is never substituted for real model evidence. A complete negative or mixed result is retained. A missing safety, sample-size, integrity or execution gate prevents scientific promotion.\n\n"
    markdown += "## Claim discipline\n\n- The studies use transparent inert generated benchmarks; external operational validity remains untested.\n- Pre-outcome amendments document protocol repairs and close gaps without changing frozen hypothesis thresholds.\n- Raw model outputs, exact model revisions, protocol hashes, paired comparisons and verifier reports support each determination.\n- Prior PX-series outcomes are not inherited by these experiments.\n- Replication is separate and follows a frozen discovery result.\n\n"
    markdown += "## Execution sequence\n\nAll three builds and prechecks proceed concurrently. Shared Qwen inference executes eligible pilots and discovery workflows; 001 uses a distinct Mistral judge in a separate phase. Each completed experiment receives its own report and dashboard update.\n"
    (ROOT.parent / "FINAL_PRAXIS_PROPOSALS.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"updated_utc": data["updated_utc"], "scientific_results_complete": data["scientific_results_complete"]}))


if __name__ == "__main__":
    main()
