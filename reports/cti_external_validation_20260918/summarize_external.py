"""Render real external results, or an explicitly incomplete operational status.

Normal mode requires verified RESULTS.json. --incomplete never computes partial
accuracies and requires an actual output directory and/or an explicit reason.
This script does not run generators, fit checkers, change gates, or read labels.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ("llama", "qwen")
DISPLAY = {"llama": "Llama 3.1 8B", "qwen": "Qwen 2.5 7B"}
CANDIDATE = "evidence_utility"
COMPARATORS = ("relevance", "relevance_options", "source_classifier", "question_utility")
ARMS = ("always_vanilla", "always_evidence", *COMPARATORS, CANDIDATE,
        *(name + "_matched" for name in COMPARATORS))
ARM_NAMES = {"always_vanilla": "No retrieved evidence", "always_evidence": "Always use retrieved evidence",
             "relevance": "Question relevance", "relevance_options": "Question + options relevance",
             "source_classifier": "Question source classifier", "question_utility": "Question utility checker",
             CANDIDATE: "Evidence-aware utility checker (candidate)"}
COHORT_NAMES = {"all": "All questions", "attack_source": "ATT&CK-source questions",
                "other_source": "Other-source questions",
                "previously_absent_broad_families": "Eight previously absent broad source families"}
GATE_NAMES = {
    "overall_gain_at_least_3pp": "Overall gain at least 3 percentage points",
    "positive_attack_gain_retains_half_positive_always_gain": "Positive ATT&CK-source gain retains half of a positive always-evidence gain",
    "other_net_loss_no_worse_2pp": "Other-source loss no greater than 2 percentage points",
    "other_ci_lower_above_minus5pp": "Other-source interval lower bound above -5 percentage points",
}
DECISIONS = {
    "EXTERNAL_USEFUL_SIGNAL_AND_ADDED_VALUE": "The frozen checker met the prespecified external usefulness and added-value criteria on this benchmark.",
    "EXTERNAL_USEFUL_SIGNAL_ADDED_VALUE_UNPROVEN": "The frozen checker met external usefulness criteria. Added value beyond the comparison methods remains unproven.",
    "EXTERNAL_TRANSPORT_CRITERIA_NOT_MET": "The frozen checker did not meet the combined external transport criteria. Individual benefits and harms remain visible below.",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def pct(value):
    return f"{float(value):.2f}%"


def points(value):
    return f"{float(value):+.2f}"


def effect(value, bounds):
    return f"{points(value)} [{points(bounds[0])}, {points(bounds[1])}]"


def passed(value):
    return "PASS" if value else "FAIL"


def arm_name(name):
    return (ARM_NAMES[name[:-8]] + " (matched count)") if name.endswith("_matched") else ARM_NAMES[name]


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |" for row in rows)]


def human_note(root):
    path = root / "HUMAN_REVIEW_STATUS.json"
    if not path.exists():
        return "No completed human-review receipt is available. Human validation is not established."
    status = load(path)
    count = status.get("completed_human_reviews")
    if count == 0:
        return "The blinded 50-item review packet is ready; zero human reviews are recorded as completed. Two independent security reviewers and a third adjudicator are required."
    return f"Human-review receipt status: `{status.get('status', 'UNSPECIFIED')}`; recorded completed review entries: {count}. Consult the signed records before claiming independent validation."


def prior_pilot(root, pilot_path):
    lines = ["## Relationship to the earlier pilot", "",
             "This external experiment adds evidence about transfer to another benchmark. It does not replace or erase the earlier CTIBench pilot, which used different questions and finer eligibility labels.", ""]
    if pilot_path.exists():
        pilot = load(pilot_path)
        lines += [f"Earlier recorded status: `{pilot['status']}`. Usefulness criteria: **{passed(pilot['core_signal_pass'])}**; added-value criteria: **{passed(pilot['added_value_pass'])}**.", ""]
        rows = []
        for model in MODELS:
            before = pilot["metrics"]["always_vanilla"]["all"][model]
            after = pilot["metrics"][CANDIDATE]["all"][model]
            rows.append([DISPLAY[model], pct(before["accuracy_pct"]), pct(after["accuracy_pct"]), points(after["delta_vs_vanilla_pp"])])
        lines += table(["Earlier pilot model", "No evidence", "Candidate", "Change, pp"], rows)
        lines += ["", f"Earlier results SHA-256: `{digest(pilot_path)}`.", ""]
    lines += ["See the [earlier pilot report](../cti_checker_pilot_20260918/REPORT.md) and [research-gap review](../cti_checker_gap_review_20260918/RESEARCH_GAP.md).", ""]
    return lines


def limitations(root):
    return ["## What these results can support", "",
            "The reported accuracy is agreement with released SecEval answers. The dataset's authors used GPT-4 to generate and calibrate labels; this study has not established their independent correctness.", "",
            "The pinned source has 2,189 records. All 1,247 records meeting the fixed single-answer/four-distinct-options rule were retained; 942 were excluded by that format rule before generator outcomes. The original dataset is public and predates this experiment, so model pretraining exposure remains possible.", "",
            "The ATT&CK knowledge family and retrieval corpus are shared with development. SecEval provides coarse source categories without per-question source-document or technique identifiers. ATT&CK-source is a provenance category, not a verified label that the retrieved facts apply. Zero exact lexical overlaps and low nearest-question similarities against the audited prior inventory do not establish semantic or source-document independence.", "",
            "Source-version differences can matter: SecEval was originally described in 2023, while this experiment retains the frozen ATT&CK 19.1 corpus. A disagreement is not automatically evidence that the model is wrong about current security practice.", "",
            "Confidence intervals resample questions within the observed coarse source-family counts, preserving each question's paired model outcomes. They are not source-document cluster intervals. They condition on the fixed benchmark, released labels, and frozen policy; comparisons are exploratory and not adjusted for multiple testing.", "",
            "The relevance comparators use a published MiniLM reranker with question-only or question-plus-options inputs. They are not complete CRAG or CoRM-RAG systems. Matching the number of questions that use evidence does not equalize computation. Every policy answers every question, so evidence use is not abstention or answer coverage.", "",
            "**Algorithmic novelty remains unproven under every result category.** A favorable result can justify further applied research; stronger published-checker comparisons and independently reviewed applied questions remain necessary for a final contribution claim.", "",
            human_note(root), "", "See [human-review instructions](HUMAN_REVIEW.md). No automated review substitutes for actual human judgments.", ""]


def references():
    return ["## Evidence and references", "",
            "- [Frozen protocol](PROTOCOL.md), [data audit](DATA_AUDIT.json), [analysis review](ANALYSIS_REVIEW.json).",
            "- [SecEval author repository and dataset license](https://github.com/XuanwuAI/SecEval). Dataset license: CC BY-NC-SA 4.0; code licensing is separate.",
            "- [Pinned SecEval revision](https://huggingface.co/datasets/XuanwuAI/SecEval/tree/205dab7b0888a06f4b53ca7d9c7093e1326683e1).",
            "- [Prior Praxis pursuit decision](../cti_checker_gap_review_20260918/PURSUIT_DECISION.md).", ""]


def complete_report(root, result_path, pilot_path):
    result = load(result_path)
    require(result.get("status") in DECISIONS, "Not a recognized complete external result")
    require((result.get("n"), result.get("fresh_outputs"), result.get("qualification_outputs")) == (1247, 4988, 32), "Complete result inventory mismatch")
    expected = (("EXTERNAL_USEFUL_SIGNAL_AND_ADDED_VALUE" if result["added_value"] else "EXTERNAL_USEFUL_SIGNAL_ADDED_VALUE_UNPROVEN")
                if result["useful_signal"] else "EXTERNAL_TRANSPORT_CRITERIA_NOT_MET")
    require(result["status"] == expected, "Inconsistent recorded decision flags")
    freeze = root / "SCIENTIFIC_FREEZE.json"
    require(freeze.exists() and digest(freeze) == result["scientific_freeze_sha256"], "Result does not match scientific freeze")
    for name, expected_hash in load(freeze)["files"].items():
        require(digest(root / name) == expected_hash, "Frozen scientific artifact changed: " + name)
    metrics = result["metrics"]
    overall = metrics["all"]
    require(overall["n"] == 1247 and set(ARMS) == set(overall["arms"]), "Reported arm inventory mismatch")
    candidate = overall["arms"][CANDIDATE]
    main_rows = []
    for model in MODELS:
        before = overall["arms"]["always_vanilla"]["models"][model]
        after = candidate["models"][model]
        main_rows.append([DISPLAY[model], f"{before['correct']}/1247 ({pct(before['accuracy_pct'])})",
                          f"{after['correct']}/1247 ({pct(after['accuracy_pct'])})",
                          effect(after["delta_vs_vanilla_pp"], after["delta_ci95_pp"])])
    lines = ["# CTI checker: external benchmark results", "", f"**{DECISIONS[result['status']]}**", "",
             f"Recorded decision: `{result['status']}`. Completed {result['n']:,} paired questions, {result['fresh_outputs']:,} fresh generator outputs and {result['qualification_outputs']} format-qualification outputs.", "",
             "The practical question is whether the checker can choose useful extra security facts without allowing irrelevant facts to damage the answer. Each policy selects between the same model's recorded answer with and without those facts.", "",
             "Changes and intervals below are in percentage points (pp). A move from 60% to 65% is +5 pp. Brackets show 95% bootstrap intervals.", ""]
    lines += table(["Model", "No evidence", "Candidate", "Candidate change, pp [95% CI]"], main_rows)
    lines += ["", f"The candidate used evidence for **{candidate['evidence_use_n']}/1247 questions ({pct(candidate['evidence_use_pct'])})**. Its mean accuracy change across the two models was **{effect(candidate['mean_delta_vs_vanilla_pp'], candidate['mean_delta_ci95_pp'])} pp**.", "",
              "## All policies", ""]
    rows = []
    for name in ARMS:
        arm = overall["arms"][name]
        accuracies = [arm["models"][m]["accuracy_pct"] for m in MODELS]
        rows.append([arm_name(name), f"{arm['evidence_use_n']} ({pct(arm['evidence_use_pct'])})",
                     *(pct(a) for a in accuracies), pct(sum(accuracies) / len(accuracies))])
    lines += table(["Policy", "Evidence use", "Llama accuracy", "Qwen accuracy", "Mean accuracy"], rows)
    lines += ["", "Matched-count rows use each comparator's highest scores for exactly as many questions as the candidate uses evidence. Selection uses no new answer labels or outcomes.", "",
              "## Candidate results by source cohort", ""]
    rows = []
    for cohort, description in COHORT_NAMES.items():
        section = metrics[cohort]
        for model in MODELS:
            no = section["arms"]["always_vanilla"]["models"][model]
            always = section["arms"]["always_evidence"]["models"][model]
            after = section["arms"][CANDIDATE]["models"][model]
            rows.append([description, section["n"], DISPLAY[model], pct(no["accuracy_pct"]),
                         pct(always["accuracy_pct"]), pct(after["accuracy_pct"]),
                         effect(after["delta_vs_vanilla_pp"], after["delta_ci95_pp"])])
    lines += table(["Cohort", "N", "Model", "No evidence", "Always evidence", "Candidate", "Candidate change, pp [95% CI]"], rows)
    lines += ["", "## Recoveries and harms", "",
              "A recovery changes a wrong baseline answer to a correct one. An induced error changes a correct baseline answer to a wrong one. A prevented error is an always-evidence error avoided by choosing the baseline; a lost improvement is a useful evidence answer not selected.", ""]
    rows = []
    for cohort, description in COHORT_NAMES.items():
        for model in MODELS:
            after = metrics[cohort]["arms"][CANDIDATE]["models"][model]
            rows.append([description, DISPLAY[model], *(after[k] for k in ("recovered_answers", "induced_errors", "prevented_errors", "lost_improvements"))])
    lines += table(["Cohort", "Model", "Recovered", "Induced errors", "Prevented errors", "Lost improvements"], rows)
    lines += ["", "## Prespecified decision criteria", ""]
    lines += table(["Usefulness criterion", "Llama", "Qwen"],
                   [[label, *(passed(result["useful_signal_gates"][m][key]) for m in MODELS)] for key, label in GATE_NAMES.items()])
    lines += ["", f"Combined usefulness criteria: **{passed(result['useful_signal'])}**. Added-value criteria against every matched comparator: **{passed(result['added_value'])}**.", "",
              "The ATT&CK-source retention criterion requires a positive always-evidence benefit and a positive candidate benefit retaining at least half of it. Avoiding a harmful always-evidence intervention does not satisfy that criterion.", ""]
    rows = []
    for name in COMPARATORS:
        comp = result["matched_comparisons"][name]
        rows.append([ARM_NAMES[name], *(effect(comp["candidate_minus_comparator_pp"][m], comp["model_ci95_pp"][m]) for m in MODELS),
                     effect(comp["mean_difference_pp"], comp["mean_ci95_pp"]), passed(comp["pass"])])
    lines += table(["Matched comparator", "Llama difference, pp [95% CI]", "Qwen difference, pp [95% CI]", "Mean difference, pp [95% CI]", "Gate"], rows)
    lines += ["", "Added-value gates require at least +1 pp in each generator and a positive lower interval bound for their mean, against each comparator.", "",
              "## Individual source-family diagnostics", ""]
    rows = []
    for key in sorted(k for k in metrics if k.startswith("source:")):
        section = metrics[key]
        arm = section["arms"][CANDIDATE]
        rows.append([key.split(":", 1)[1], section["n"],
                     *(f"{pct(arm['models'][m]['accuracy_pct'])}; {effect(arm['models'][m]['delta_vs_vanilla_pp'], arm['models'][m]['delta_ci95_pp'])} pp" for m in MODELS)])
    lines += table(["Source family", "N", "Llama candidate accuracy; change [CI]", "Qwen candidate accuracy; change [CI]"], rows)
    lines += ["", "These small source-family slices are descriptive; they did not tune the policy or its gates.", "", "## Output validity and provenance", ""]
    lines += table(["Model / condition", "Invalid outputs retained as incorrect"],
                   [[DISPLAY[m] + " / " + condition, result["invalid_outputs"].get(m + "/" + condition, 0)]
                    for m in MODELS for condition in ("vanilla", "relationship_evidence")])
    lines += ["", f"Analysis completion: `{result['completed_utc']}`. Results SHA-256: `{digest(result_path)}`. Scientific freeze SHA-256: `{result['scientific_freeze_sha256']}`.", "",
              "[Machine-readable results](RESULTS.json) retain counts, intervals, gates, and generator receipt hashes. [Scored records](scored_records.jsonl) preserve the per-question paired outcomes.", ""]
    lines += prior_pilot(root, pilot_path) + limitations(root) + references()
    status = ["# CTI external validation status", "", f"**{DECISIONS[result['status']]}**", "",
              f"Status: `{result['status']}`. All 1,247 questions and 4,988 fresh outputs were analyzed.", ""]
    for model in MODELS:
        before, after = overall["arms"]["always_vanilla"]["models"][model], candidate["models"][model]
        status.append(f"- {DISPLAY[model]}: {pct(before['accuracy_pct'])} → {pct(after['accuracy_pct'])}; change {effect(after['delta_vs_vanilla_pp'], after['delta_ci95_pp'])} pp.")
    status += [f"- Evidence used: {candidate['evidence_use_n']}/1247 ({pct(candidate['evidence_use_pct'])}).",
               f"- Usefulness gates: {passed(result['useful_signal'])}; added-value gates: {passed(result['added_value'])}.",
               "- Algorithmic novelty remains unproven; this uses public questions, shared ATT&CK sources, and released labels.",
               "", human_note(root), "", "The earlier pilot remains part of the evidence. See [full report](REPORT.md) and [human-review instructions](HUMAN_REVIEW.md).", ""]
    return lines, status


def observed_inventory(path):
    if not path.exists():
        return {"available": False}
    parsed, malformed, keys = 0, 0, set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            keys.add((row["id"], row["model"], row["condition"]))
            parsed += 1
        except (ValueError, KeyError, TypeError):
            malformed += 1
    return {"available": True, "parseable_records": parsed, "unique_assignments": len(keys),
            "malformed_records": malformed, "sha256": digest(path)}


def incomplete_report(root, outputs, reason, pilot_path):
    require(not (root / "RESULTS.json").exists(), "Complete result file exists; do not replace its report with incomplete status")
    require(outputs is not None or bool(reason), "Incomplete reporting requires an output directory or an explicit reason")
    runtime_path = outputs / "runtime.json" if outputs else None
    runtime = load(runtime_path) if runtime_path is not None and runtime_path.exists() else None
    explanation = reason or (str(runtime.get("error")) if runtime and runtime.get("error") else "A complete, verified analysis is not available.")
    lines = ["# CTI checker: incomplete external attempt", "", "**Status: `EXTERNAL_INCOMPLETE`. No complete benchmark accuracy or efficacy conclusion is available.**", "",
             f"Reason recorded: {explanation}", "", f"Status written: `{datetime.now(timezone.utc).isoformat()}`.", ""]
    if runtime:
        lines += [f"Runtime receipt status: `{runtime.get('status', 'UNSPECIFIED')}`. This operational state is not a scientific result.", "",
                  f"Runtime receipt SHA-256: `{digest(runtime_path)}`.", ""]
    if outputs:
        rows = []
        for name, expected in (("qualification.jsonl", 32), ("predictions.jsonl", 4988)):
            record = observed_inventory(outputs / name)
            rows.append([name, expected, record.get("parseable_records", "unavailable"),
                         record.get("unique_assignments", "unavailable"), record.get("malformed_records", "unavailable")])
        lines += table(["Output file", "Required assignments", "Observed records", "Observed unique assignments", "Malformed records"], rows)
        lines += ["", "Observed record counts are progress diagnostics only. They do not establish correct model revisions, prompt assignments, complete receipts, valid qualification, or a complete test. No partial accuracy is computed here.", ""]
    lines += ["The prespecified test requires both models to pass all 32 qualification outputs and a verified inventory of 4,988 fresh outputs. Completion and receipt verification are required before any complete-result classification. A changed parser, generation format, or outcome-driven retry requires a separately identified protocol.", "",
              "This incomplete attempt does not overturn the earlier pilot. It also does not demonstrate external success or external failure of the checker.", ""]
    lines += prior_pilot(root, pilot_path) + limitations(root) + references()
    status = ["# CTI external validation status", "", "**`EXTERNAL_INCOMPLETE`: no complete external accuracy result is available.**", "",
              explanation, "", "The earlier pilot remains unchanged. No partial accuracies or new efficacy claims are reported.", "",
              human_note(root), "", "See [attempt report](REPORT.md) and [frozen protocol](PROTOCOL.md).", ""]
    return lines, status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--pilot-results", type=Path)
    parser.add_argument("--incomplete", action="store_true")
    parser.add_argument("--outputs", type=Path, help="Actual runtime output directory; used only for incomplete progress counts")
    parser.add_argument("--reason", default="", help="Recorded reason for an incomplete attempt")
    args = parser.parse_args()
    results = args.results or args.root / "RESULTS.json"
    pilot = args.pilot_results or args.root.parent / "cti_checker_pilot_20260918/RESULTS.json"
    if args.incomplete:
        report, status = incomplete_report(args.root, args.outputs, args.reason, pilot)
    else:
        require(results.exists(), "RESULTS.json is absent; normal reporting requires a verified complete analysis")
        report, status = complete_report(args.root, results, pilot)
    (args.root / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    (args.root / "STATUS.md").write_text("\n".join(status), encoding="utf-8")
    print(json.dumps({"mode": "EXTERNAL_INCOMPLETE" if args.incomplete else "COMPLETE_RESULTS",
                      "report": str(args.root / "REPORT.md"), "status": str(args.root / "STATUS.md")}, indent=2))


if __name__ == "__main__":
    main()
