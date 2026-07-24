from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs" / "new_praxis_experiment_registry_20260723.json"


DETAILS = {
    "PX-057": {
        "classification": "Strong bounded positive",
        "tone": "positive",
        "evidence": "Valid Gate 2: 200 GSM8K questions and 1,600 model generations.",
        "result": "Adaptive accuracy 91.0% vs. 61.5% fixed-long; token saving 66.5%; prevention 89.6%; harm 0.5%.",
        "next": "Run H4 cross-model and non-math transfer without changing the completed discovery result.",
        "link": "adaptive_stopping_overthinking/PX057_FINAL_DETERMINATION_20260724.md",
    },
    "PX-058": {
        "classification": "Mixed",
        "tone": "mixed",
        "evidence": "Valid CICIDS2017 Gate 2: five seeds, three explanation methods, five holdouts.",
        "result": "H1 stability passed for permutation, TreeSHAP, and LIME; H2 drift-warning failed for all methods.",
        "next": "Retain stability as a subfinding; redesign drift warning only as a new preregistered experiment.",
        "link": "xai_explanation_drift_intrusion/PX058_FINAL_DETERMINATION_20260724.md",
    },
    "PX-059": {
        "classification": "Closed at novelty gate",
        "tone": "closed",
        "evidence": "Source review found material overlap with EAGLE-2, SpecDec++, CAST, and SpecKV.",
        "result": "Not novel enough to advance as a separate Praxis contribution.",
        "next": "Archive unless a distinctly new mechanism appears.",
        "link": "uncertainty_adaptive_speculative_decoding/PX059_SOURCE_GATE_20260724.md",
    },
    "PX-060": {
        "classification": "Final negative",
        "tone": "negative",
        "evidence": "Valid 18-condition multi-seed perturbation run.",
        "result": "Prediction improved and reversal was tolerated, but direction identifiability and deletion robustness failed.",
        "next": "Any equivalence-class identifiability test must be a new hypothesis.",
        "link": "coed_direction_robustness/PX060_FINAL_DETERMINATION_20260724.md",
    },
    "PX-061": {
        "classification": "Final negative",
        "tone": "negative",
        "evidence": "Matched-accounting mechanism audit and registered three-band repair completed.",
        "result": "Adaptive unequal noise gained 1.42 points vs. a required 2.0; static unequal allocation did not help.",
        "next": "Do not advance to Fashion-MNIST confirmation.",
        "link": "wavelet_dp_federated_learning/PX061_FINAL_DETERMINATION_20260724.md",
    },
    "PX-062": {
        "classification": "Gate 1 negative; Gate 2 active",
        "tone": "active",
        "evidence": "1,070 released poisoned skills, 44 clean skills, and a frozen 300-task hallucination benchmark.",
        "result": "Provenance blocked tampering and nonexistent names but admitted 100% of authentic signed poisoned skills.",
        "next": "Complete the two-model, three-condition live skill-name hallucination run and adjudicate 1,800 outputs.",
        "link": "coding_agent_skill_provenance/PX062_CURRENT_DETERMINATION_20260724.md",
    },
    "PX-063": {
        "classification": "Blocked",
        "tone": "queued",
        "evidence": "TRACE deterministic reward-hack verifier is specified.",
        "result": "Dataset fetch remains unresolved.",
        "next": "Verify and freeze the public dataset before implementation.",
        "link": "new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md",
    },
    "PX-064": {
        "classification": "Blocked",
        "tone": "queued",
        "evidence": "Registry hardening in tool-use RL is registered.",
        "result": "Benchmark artifact verification remains unresolved.",
        "next": "Establish a reproducible benchmark environment before execution.",
        "link": "new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md",
    },
    "PX-065": {
        "classification": "Simulation ready",
        "tone": "queued",
        "evidence": "Inert provenance-admission simulation for agent memory is specified.",
        "result": "No scientific result yet.",
        "next": "Run the frozen inert simulation after PX-062 adjudication.",
        "link": "new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md",
    },
}


def cloud_status(profile: str) -> dict:
    command = [
        "aws",
        "sagemaker",
        "describe-training-job",
        "--profile",
        profile,
        "--region",
        "us-east-1",
        "--training-job-name",
        "px062-skill-hallucination-2026-07-24-22-21-01",
        "--query",
        "{Status:TrainingJobStatus,Secondary:SecondaryStatus,Failure:FailureReason}",
        "--output",
        "json",
    ]
    try:
        return json.loads(subprocess.check_output(command, text=True))
    except Exception:
        return {"Status": "Unknown", "Secondary": "Unavailable", "Failure": None}


def markdown(experiments: list[dict], cloud: dict) -> str:
    rows = [
        "# Praxis Experiment Dashboard",
        "",
        "Updated: 2026-07-24",
        "",
        "## Portfolio snapshot",
        "",
        "- Lead new positive: **PX-057 adaptive stopping**.",
        "- Mixed result: **PX-058 explanation stability passed; drift warning failed**.",
        "- Closed or negative: **PX-059, PX-060, PX-061**.",
        "- Active: **PX-062 skill-name hallucination Gate 2**.",
        "- Queued or blocked: **PX-063 through PX-065**.",
        "- Related mature defense: **PX-050 independently confirmed one-million-command robustness within its frozen grammar**.",
        "",
        "## Active cloud work",
        "",
        f"- Job: `px062-skill-hallucination-2026-07-24-22-21-01`",
        f"- Status: `{cloud.get('Status')}` / `{cloud.get('Secondary')}`",
        "- Workload: two models x three conditions x 300 tasks = 1,800 outputs.",
        "",
        "## PX-057 through PX-065",
        "",
        "| ID | Experiment | Classification | Best current result | Next action |",
        "|---|---|---|---|---|",
    ]
    for item in experiments:
        detail = DETAILS[item["px_id"]]
        rows.append(
            f"| [{item['px_id']}]({detail['link']}) | {item['title']} | "
            f"{detail['classification']} | {detail['result']} | {detail['next']} |"
        )
    rows.extend(
        [
            "",
            "## Related completed defense",
            "",
            "PX-050 independently confirmed its repaired deterministic install gate on one million commands: zero invalid allows across 500,000 absent-package cases, 100% allow rate on 416,668 supported safe-valid commands, and 100% block rate on 166,664 shell-chain cases.",
            "",
            "- [PX-050 large-scale robustness determination](agentic_deployment_defense/PX050_LARGE_SCALE_ROBUSTNESS_DETERMINATION_20260724.md)",
            "- [PX-057-PX-061 portfolio audit](PX057_PX061_PORTFOLIO_AUDIT_20260724.md)",
            "- [PX-062 working Praxis report](../output/doc/px062_working_praxis_20260724/PX-062_Working_Praxis_Report.pdf)",
            "",
        ]
    )
    return "\n".join(rows)


def html_dashboard(experiments: list[dict], cloud: dict) -> str:
    cards = []
    table_rows = []
    for item in experiments:
        detail = DETAILS[item["px_id"]]
        cards.append(
            f"""<article class="card {detail['tone']}">
<div class="id">{html.escape(item['px_id'])}</div>
<h3>{html.escape(item['title'])}</h3>
<span class="badge">{html.escape(detail['classification'])}</span>
<p>{html.escape(detail['result'])}</p>
<a href="{html.escape(detail['link'])}">Open determination</a>
</article>"""
        )
        table_rows.append(
            f"""<tr>
<td><a href="{html.escape(detail['link'])}">{html.escape(item['px_id'])}</a></td>
<td>{html.escape(item['title'])}</td>
<td><span class="badge {detail['tone']}">{html.escape(detail['classification'])}</span></td>
<td>{html.escape(detail['evidence'])}</td>
<td>{html.escape(detail['next'])}</td>
</tr>"""
        )
    status = html.escape(str(cloud.get("Status", "Unknown")))
    secondary = html.escape(str(cloud.get("Secondary", "Unknown")))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Praxis Experiment Dashboard - 2026-07-24</title>
<style>
:root{{--navy:#142f48;--blue:#2475a1;--teal:#159786;--red:#b64343;--amber:#d49317;--ink:#202a32;--muted:#63717b;--line:#d9e2e8;--bg:#eef3f6;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.45}}
header{{background:linear-gradient(120deg,var(--navy),#245878);color:white;padding:46px max(28px,6vw) 38px}}
header .kicker{{font-size:.78rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#81d8cc}}
h1{{font-size:clamp(2rem,4vw,3.5rem);line-height:1.05;margin:.35rem 0 .8rem}} header p{{max-width:900px;color:#dce9f0;margin:0}}
main{{max-width:1440px;margin:auto;padding:30px max(22px,4vw) 60px}}
.cloud{{display:flex;gap:20px;align-items:center;justify-content:space-between;background:#fff;border-left:6px solid var(--teal);padding:18px 22px;border-radius:10px;box-shadow:0 4px 18px #18324a12;margin-bottom:28px}}
.cloud strong{{color:var(--navy)}} .status{{background:#e3f4f0;color:#087466;font-weight:800;padding:6px 12px;border-radius:999px;white-space:nowrap}}
.summary{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:0 0 28px}}
.metric{{background:#fff;border-radius:10px;padding:18px;border:1px solid var(--line)}} .metric b{{display:block;font-size:1.7rem;color:var(--navy)}} .metric span{{color:var(--muted)}}
h2{{color:var(--navy);margin:30px 0 14px}} .cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}
.card{{background:#fff;border:1px solid var(--line);border-top:5px solid var(--blue);border-radius:10px;padding:18px;box-shadow:0 3px 12px #18324a0b}}
.card.positive{{border-top-color:var(--teal)}} .card.mixed,.card.active{{border-top-color:var(--amber)}} .card.negative,.card.closed{{border-top-color:var(--red)}} .card.queued{{border-top-color:#82929d}}
.card .id{{font-weight:900;color:var(--blue);font-size:.8rem;letter-spacing:.08em}} .card h3{{margin:.35rem 0 .55rem;color:var(--navy)}} .card p{{font-size:.92rem;color:#45545f}}
.badge{{display:inline-block;border-radius:999px;padding:4px 9px;background:#edf2f5;font-size:.75rem;font-weight:800}} .badge.positive{{background:#def2ed;color:#087466}} .badge.mixed,.badge.active{{background:#fff0cf;color:#895c00}} .badge.negative,.badge.closed{{background:#f9e1e1;color:#973535}}
a{{color:var(--blue);font-weight:700;text-decoration:none}} a:hover{{text-decoration:underline}}
.table-wrap{{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:10px}} table{{border-collapse:collapse;width:100%;min-width:1050px}} th{{text-align:left;background:var(--navy);color:#fff;padding:11px}} td{{padding:11px;border-bottom:1px solid var(--line);vertical-align:top;font-size:.9rem}} tr:last-child td{{border-bottom:0}}
.note{{margin-top:26px;background:#fff;padding:20px;border-radius:10px;border:1px solid var(--line)}} footer{{color:var(--muted);font-size:.82rem;margin-top:30px}}
@media(max-width:900px){{.summary{{grid-template-columns:repeat(2,1fr)}}.cards{{grid-template-columns:1fr}}.cloud{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<header><div class="kicker">Praxis research portfolio</div><h1>Experiment Dashboard</h1><p>Evidence-first status for PX-057 through PX-065, plus the related PX-050 large-scale defense result. Updated July 24, 2026.</p></header>
<main>
<section class="cloud"><div><strong>Active cloud experiment</strong><br>PX-062 skill-name hallucination - 2 models x 3 conditions x 300 tasks = 1,800 outputs</div><span class="status">{status} / {secondary}</span></section>
<section class="summary">
<div class="metric"><b>1</b><span>strong bounded positive</span></div>
<div class="metric"><b>1</b><span>mixed result</span></div>
<div class="metric"><b>3</b><span>closed or negative</span></div>
<div class="metric"><b>1</b><span>active live gate</span></div>
</section>
<h2>Current experiment cards</h2><section class="cards">{''.join(cards)}</section>
<h2>Evidence and next actions</h2><div class="table-wrap"><table><thead><tr><th>ID</th><th>Experiment</th><th>Classification</th><th>Evidence</th><th>Next action</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<section class="note"><h2>Related completed defense</h2><p><strong>PX-050:</strong> independent one-million-command confirmation produced zero invalid allows across 500,000 absent-package cases, allowed 100% of 416,668 supported safe-valid commands, and blocked 100% of 166,664 shell-chain cases.</p><p><a href="agentic_deployment_defense/PX050_LARGE_SCALE_ROBUSTNESS_DETERMINATION_20260724.md">Open PX-050 determination</a> &nbsp; | &nbsp; <a href="PX057_PX061_PORTFOLIO_AUDIT_20260724.md">Open PX-057-PX-061 audit</a> &nbsp; | &nbsp; <a href="../output/doc/px062_working_praxis_20260724/PX-062_Working_Praxis_Report.pdf">Open PX-062 working report</a></p></section>
<footer>Statuses reflect preregistered evidence boundaries. Fixture passes are not classified as scientific positives.</footer>
</main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    experiments = [
        row
        for row in registry["experiments"]
        if row["px_id"] in DETAILS
    ]
    cloud = cloud_status(args.profile)
    reports = ROOT / "reports"
    md_path = reports / "EXPERIMENT_CURRENT_DASHBOARD_20260724.md"
    html_path = reports / "EXPERIMENT_CURRENT_DASHBOARD_20260724.html"
    md_path.write_text(markdown(experiments, cloud), encoding="utf-8")
    html_path.write_text(html_dashboard(experiments, cloud), encoding="utf-8")
    print(json.dumps({"markdown": str(md_path), "html": str(html_path), "cloud": cloud}))


if __name__ == "__main__":
    main()
