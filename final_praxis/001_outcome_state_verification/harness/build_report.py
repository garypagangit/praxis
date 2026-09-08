"""Produce the repository's five-chapter Praxis report from independently audited raw evidence."""
from __future__ import annotations
import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from .scientific_protocol import ROOT, file_hash, parse_object
from .verify_scientific import verify_run, parse as audit_parse

def proportion(cell):
    if not cell["denominator"]:
        return "not estimable (n=0)"
    return f"{cell['numerator']}/{cell['denominator']} ({cell['rate']:.1%})"

def build(run_dir):
    run_dir = Path(run_dir).resolve()
    result = verify_run(run_dir, seal=False)
    if result["stage"] != "discovery" or result["n"] != 400:
        raise ValueError("The final Praxis report requires the full audited discovery corpus")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    relative = run_dir.relative_to(ROOT).as_posix()
    metrics, gates = result["metrics"], result["gates"]
    j, d = metrics["judge"]["FSAR"], metrics["det"]["FSAR"]
    ci = result["paired_stratified_bootstrap_ci95"]
    cluster = result["task_cluster_bootstrap_ci95_diagnostic"]
    failed = ", ".join(key for key, value in gates.items() if not value) or "none"
    condition_rows = []
    examples = []
    judge_finish_reasons, malformed_kinds = Counter(), Counter()
    for path in sorted((run_dir / "raw/agent").glob("*.json")):
        agent = json.loads(path.read_text(encoding="utf-8"))
        judge = json.loads((run_dir / "raw/judge" / path.name).read_text(encoding="utf-8"))
        judge_finish_reasons[judge["response"].get("finish_reason", "unrecorded")] += 1
        if audit_parse(judge["response"]["text"])[1]:
            try:
                parsed = parse_object(judge["response"]["text"])
                value = parsed.get("success")
                kind = "numeric_success_instead_of_boolean" if type(value) in (int, float) else "other_schema_error"
            except (ValueError, TypeError):
                kind = "not_a_complete_json_object"
            malformed_kinds[kind] += 1
        condition_rows.append({"instance_id": agent["instance_id"], "task_id": agent["task_id"], "task_family": agent["task_family"],
                               "condition": agent["condition"], "judge": judge["decision"]["success"],
                               "det": agent["verdict"]["success"], "self_report": agent["claim_decision"]["success"]})
        if judge["decision"]["success"] != agent["verdict"]["success"] and len(examples) < 3:
            examples.append((agent, judge))
    diag = result["full_state_diagnostic"]
    diagnostic_records = [json.loads(path.read_text(encoding="utf-8")) for path in (run_dir / "raw/full_state_judge").glob("*.json")]
    diagnostic_malformed = sum(audit_parse(item["response"]["text"])[1] for item in diagnostic_records)
    parts = ["# Independent Outcome-State Verification for Agent Task Completion Under Evaluator Disagreement",
             "", "Doctor of Engineering Praxis research report — Final Praxis 001", "",
             f"Evidence-based determination: **{result['classification']}**. Report generated {datetime.now(timezone.utc).isoformat()}.",
             "", "This report follows the repository's five-chapter Praxis structure. Institutional approval, committee review, and publication acceptance are not implied.",
             "", "## Abstract of Praxis", "",
             f"This study measured disagreement between a transcript-only learned evaluator and a full-state deterministic verifier on 400 controlled inert task instances. The fixed design used 20 JSON-state task templates in four families, a real Qwen2.5-7B-Instruct action and completion model, and a distinct Mistral-7B-Instruct-v0.3 judge. Half the final states were deliberately invalid; this prevalence was imposed experimentally and is not a natural agent error rate. The judge accepted {proportion(j)} invalid states, compared with {proportion(d)} for the deterministic verifier. The paired FSAR difference was {result['delta_FSAR']:.3f}, with a frozen within-template bootstrap 95% interval [{ci[0]:.3f}, {ci[1]:.3f}]. The final frozen-gate classification was {result['classification']}; failed gates: {failed}. Natural action executions before imposed state projection succeeded in {result['natural_success_count']}/400 cases. A preselected full-state learned-judge diagnostic examined {diag['n']} cases. Deterministic accuracy on predicate-defined labels is structural; the empirical contribution is the bounded learned-judge disagreement measurement and its information-access interpretation.",
             "", "Keywords: agent evaluation; task completion; outcome state; learned judge; collateral changes; reproducibility.",
             "", "## Chapter 1: Introduction", "", "### 1.1 Problem statement and engineering significance", "",
             "A fluent completion message does not itself establish that an intended state transition occurred. A task can leave a requested field unchanged, complete only some required fields, or achieve the goal while altering unrelated state. For applications with explicitly checkable outcomes, this creates an engineering question about what evidence an evaluator can access and how it converts that evidence into a completion decision.",
             "", "The objective is a falsifiable, auditable measurement of this gap in a small controlled simulator. It is not to establish that deterministic verification is new or universally preferable. The learned judge observes a transcript and field-level receipts; the deterministic verifier sees authoritative final state. That information difference is part of the experimental treatment and a central limitation.",
             "", "### 1.2 Research questions and hypotheses", "",
             "| Research question | Frozen hypothesis / decision basis |", "|---|---|",
             "| RQ1: How often does the learned judge accept invalid imposed states? | H1; paired FSAR effect, CI, G1 and nontrivial-gap gate G5. |",
             "| RQ2: Are valid and alternate legal outcomes accepted? | H2; TSAR G2 and APAR G3. These checks are structural for the implemented semantic oracle. |",
             "| RQ3: Does disagreement include collateral violations across families? | H3; lower CVMR in at least three families, G4. |",
             "| RQ4: Where does disagreement concentrate and how does full-state access change it? | H4 descriptive failure-family analysis and preselected information-access diagnostic. No diagnostic rescues failed primary gates. |",
             "", "### 1.3 Scope and limitations", "",
             "The corpus contains only 20 substantive template structures, repeated with varied symbolic identifiers. Four hundred rows do not represent 400 independent real-world task types. All operations are inert object assignments; no real filesystem, database service, incident system, or external credential is modified. One open 7B-class agent and one open 7B-class judge are evaluated. Failure-family names describe assigned states rather than the agent's intent or guaranteed claim. Some single-predicate tasks collapse partial and incomplete conditions and cannot support distinct multi-operation alternate ordering.",
             "", "## Chapter 2: Literature Review", "", "### 2.1 State-based agent evaluation", "",
             "Yao et al.'s tau-bench evaluates tool-using agents by comparing final database state with goal annotations. It establishes that environmental state is a practical evaluation target. The present work does not claim to originate that approach. [tau-bench](https://arxiv.org/abs/2406.12045)",
             "", "Trivedi et al.'s AppWorld provides programmatic state tests that admit multiple valid completion paths and check unintended changes. Consequently, alternative-path acceptance and collateral checking are also established prior capabilities. This study is much smaller and less realistic than AppWorld. [AppWorld, ACL 2024](https://aclanthology.org/2024.acl-long.850/)",
             "", "### 2.2 Learned state reconstruction and judge evaluation", "",
             "Chuang et al. describe proxy state-based evaluation: a learned state tracker infers structured state from an interaction trace, and learned judges assess completion against scenario constraints. This provides a close conceptual comparison for inference from transcripts. The present full-state diagnostic addresses whether an observed judge gap is attributable to hidden state rather than the evaluator's reasoning ability. [Proxy State-Based Evaluation](https://arxiv.org/abs/2602.16246)",
             "", "### 2.3 Gap synthesis and novelty boundary", "",
             "The defensible contribution is a fully specified local measurement of judge/postcondition disagreement across deliberately controlled states, paired with a predeclared information-access diagnostic and raw output lineage. The focused primary-source review confirms overlap; it does not establish absence of equivalent prior studies. Broad novelty, general reward-hacking prevention, and superiority over all learned evaluators are not claimed.",
             "", "## Chapter 3: Methodology", "", "### 3.1 Design and prospective freeze", "",
             f"The experiment used a local preregistration frozen before model output inspection. Protocol SHA-256: `{result['protocol_sha256']}`. The initial draft and historical fixture marker remain preserved; `AMENDMENT_20260908_PRE_RESULTS.md` records the hash discrepancy, parser/verifier repairs, precise model selection, and distinction between controlled stress and natural behavior. `AMENDMENT_20260908_AUDIT_BINDING_V2.md` documents the cross-audit correction that binds the run manifest, archived prompts, and raw inference lineage to the frozen inputs. The earlier v1 infrastructure pilot is historical only; a fresh v2 pilot qualified discovery. Every numerical promotion threshold remained unchanged. The seed was {config['seed']}. A separate 16-case infrastructure pilot preceded discovery and did not enter the 400-unit denominator.",
             "", "### 3.2 Graphical Methodology of Research (GMR)", "",
             "The evidence flow is: freeze task semantics and allocations; validate deterministic infrastructure; execute a real model's natural action proposal; retain natural state; impose an independently prescribed final-state condition; obtain the model's honest completion assessment from visible receipts; obtain a distinct learned judgment; independently recompute state truth and metrics; apply fixed gates; report both successful and unsuccessful hypotheses.",
             "", "```mermaid", "flowchart TD", ' A["Freeze tasks, model revisions, prompts and thresholds"] --> B["140 fixtures, 18 focused tests and 16-case pilot"]',
             ' B --> C["Generate 400 real Qwen action proposals"]',
             ' C --> D["Archive natural states; impose controlled final states"]',
             ' D --> E["Generate real Qwen claims from visible receipts"]',
             ' E --> F["Pair transcript-only judge with separate state oracle"]',
             ' F --> G["Run preselected 40-case full-state judge diagnostic"]',
             ' G --> H["Independently audit raw evidence and paired statistics"]',
             ' H --> I["Apply unchanged gates and report bounded conclusions"]', "```",
             "", "### 3.3 Tasks, state construction, and observation regime", "",
             "Each template has five clean and five alternate-valid cases plus ten invalid cases. Rotation across templates produces exactly 50 incomplete, 50 false-success-target, 50 partial, and 50 collateral conditions. Clean/alternate counts are 100 each. Symbolic IDs vary by instance. The agent receives target field assignments and a requirement to preserve all other fields; it may propose up to 12 existing-path assignments. Natural execution is retained before any intervention.",
             "", "The stress projection independently constructs the intended successful state, then corrupts the first goal, every goal, the last goal, or the first protected invariant according to condition. Actual final values for proposed action paths become visible receipts. Qwen generates its completion assessment after reading those receipts. The judge receives initial state, task request, proposed actions, receipts, and raw completion text. It does not see condition labels, the intervention script, hidden expected-state objects, or verifier code. The deterministic evaluator sees the full final state. Set-valued lists accept permutation without duplicates; type errors and missing required fields fail.",
             "", "On the first clean and first collateral unit per template, a separate judge call also receives the full authoritative state. This diagnostic involves 40 preselected cases, does not use threshold tuning, and cannot change the primary classification.",
             "", "### 3.4 Models, inference, and provenance", "",
             f"Agent: `{config['agent']['model_id']}` at `{config['agent']['revision']}`. Judge: `{config['judge']['model_id']}` at `{config['judge']['revision']}`. Both use BF16, greedy decoding, temperature 0, SDPA attention, and no quantization. Budgets are {config['action_max_new_tokens']} action tokens, {config['claim_max_new_tokens']} completion-assessment tokens, and {config['judge_max_new_tokens']} judge tokens. The raw records retain model revision, runtime, request identifiers, prompt hashes, token counts, timestamps, and complete generated text. Mistral's system instructions are preserved by merging them into the first user turn according to the frozen adapter.",
             "", "The immutable model source records are available from the publishers: [Qwen model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) and [Mistral model card](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3). Actual execution is established by the experiment's raw inference artifacts, not by model-card claims.",
             "", "The qualifying pilot exposed numeric success fields in some judge outputs. The frozen protocol treats model schema mistakes as outcomes when the infrastructure preserves and classifies them correctly. Accordingly, no semantic parser coercion, revised judge instruction, changed token budget, or selective retry was introduced after pilot inspection. This preserved prospective decision rules while narrowing the interpretation of the judge comparison. The final malformed-response counts quantify that limitation.",
             "", "### 3.5 Metrics, uncertainty, and decision rules", "",
             "FSAR is the proportion of all imposed invalid states accepted as successful; TSAR is acceptance among valid states; APAR is acceptance among alternate-valid states; CVMR is acceptance among collateral-invalid states. The same units are scored by each evaluator. Malformed model JSON counts as rejection and remains in the denominator. The default exclusion count is zero; infrastructure absence cannot be replaced by a synthetic decision.",
             "", "The primary effect is FSAR(judge) minus FSAR(deterministic). The frozen primary 95% interval uses 10,000 paired bootstrap resamples within each task template. An exact two-sided McNemar test provides a secondary paired check. A template-cluster bootstrap samples 20 templates with replacement as a prespecified robustness diagnostic; it acknowledges dependence among parameterized cases.",
             "", "A Bounded Positive requires an absolute FSAR gap of at least 0.20 or relative reduction of at least 50%, an interval excluding zero, verifier TSAR at least 95%, APAR at least 90%, collateral improvement in at least three families, judge FSAR at least 10%, and complete audit validity. Failure of the 10% judge-gap gate yields Negative; other scientific gate failures with a measurable gap yield Mixed. Integrity failure yields Protocol Invalid. No replication is claimed.",
             "", "## Chapter 4: Results and Discussion", "", "### 4.1 Corpus and verification", "",
             f"All {result['n']} discovery units were independently audited against the frozen allocation. Exclusions: {len(result['exclusions'])}. The original 140 fixture cases and 18 focused infrastructure tests were separate from these results. Logged infrastructure failures: {result['infrastructure_failure_records']}. Malformed output counts were action={result['malformed_counts']['action_malformed']}, completion={result['malformed_counts']['claim_malformed']}, and primary judge={result['malformed_counts']['judge_malformed']}. Recorded inference token totals were {result['tokens']['prompt']:,} prompt tokens and {result['tokens']['completion']:,} generated tokens, including the full-state diagnostic. These totals are not monetary billing estimates; shared GPU cost allocation requires the root execution ledger.",
             "", "### 4.2 Primary evaluator outcomes", "",
             "| Evaluator | FSAR | TSAR | APAR | CVMR |", "|---|---:|---:|---:|---:|"]
    for name in ("self_report", "judge", "det"):
        parts.append("| " + name + " | " + " | ".join(proportion(metrics[name][key]) for key in ("FSAR", "TSAR", "APAR", "CVMR")) + " |")
    parts += ["", f"Paired FSAR difference: {result['delta_FSAR']:.4f}; primary stratified bootstrap 95% interval [{ci[0]:.4f}, {ci[1]:.4f}]. Template-cluster diagnostic 95% interval [{cluster[0]:.4f}, {cluster[1]:.4f}]. Exact McNemar two-sided p={result['mcnemar']['two_sided_p']:.6g}, with {result['mcnemar']['judge_only_false_accepts']} judge-only and {result['mcnemar']['det_only_false_accepts']} verifier-only false acceptances. Judge/verifier decisions disagreed on {result['disagreement_count']}/400 units.",
              "", f"Primary judge finish reasons: {dict(judge_finish_reasons)}. Malformed response types: {dict(malformed_kinds)}. The frozen decision contract rejects malformed output. Thus a low judge FSAR can reflect schema noncompliance or conservative rejection as well as correct semantic assessment. The judge's valid-state acceptance and malformed counts must be considered with its invalid-state rejection rate; low FSAR alone does not establish a capable evaluator. Numeric success values are not retrospectively coerced to booleans, and no malformed unit is removed from the primary denominator.",
              "", "These statistics describe a fixed stress distribution. The deterministic zero-error rate, if observed, follows the implemented ground-truth predicates and should not be presented as an independent validation of universal oracle correctness.",
              "", "### 4.3 Family and condition diagnostics", "",
              "| Task family | Judge FSAR | Verifier FSAR | Judge CVMR | Verifier CVMR |", "|---|---:|---:|---:|---:|"]
    for family, values in result["families"].items():
        cells = [values["judge"]["FSAR"], values["det"]["FSAR"], values["judge"]["CVMR"], values["det"]["CVMR"]]
        parts.append("| " + family + " | " + " | ".join(proportion(cell) for cell in cells) + " |")
    parts += ["", "| Controlled condition | n | Judge accepted | Verifier accepted | Agent claimed success |", "|---|---:|---:|---:|---:|"]
    for condition in sorted(result["counts"]):
        subset = [row for row in condition_rows if row["condition"] == condition]
        parts.append(f"| {condition} | {len(subset)} | {sum(row['judge'] for row in subset)} | {sum(row['det'] for row in subset)} | {sum(row['self_report'] for row in subset)} |")
    parts += ["", "### 4.4 Natural state and full-state judge diagnostic", "",
              f"Before imposed state projection, genuine model-proposed assignments completed {result['natural_success_count']}/400 natural task instances ({result['natural_success_count']/400:.1%}). This is an action-state completion measure on easy parameterized templates. Its denominator is not pooled with controlled-stress acceptance rates, and the post-intervention completion claim does not describe natural-state outcomes.",
              "", f"The {diag['n']}-case full-state diagnostic was selected before inference. On this same subset, primary judge collateral acceptance was {proportion(diag['primary_judge']['CVMR'])}; full-state judge collateral acceptance was {proportion(diag['full_state_judge']['CVMR'])}. Primary judge valid-state acceptance was {proportion(diag['primary_judge']['TSAR'])}; full-state judge valid-state acceptance was {proportion(diag['full_state_judge']['TSAR'])}. The full-state diagnostic contained {diagnostic_malformed}/{diag['n']} malformed responses, which also count as rejections. These matched descriptive comparisons assess the role of observation access only to the extent permitted by model schema adherence. They are not a second primary test and cannot change failed discovery gates.",
              "", "### 4.5 Frozen gates and research-question decisions", "",
              "| Gate | Result |", "|---|---|"]
    parts += [f"| {name} | {'PASS' if value else 'FAIL'} |" for name, value in gates.items()]
    parts += ["", f"Final classification: **{result['classification']}**. Failed gates: {failed}. RQ1/H1 is supported under the frozen rule only if both G1 and G5 pass; observed decision: {'pass' if gates['G1_integrity'] and gates['G5_nontrivial_judge_gap'] else 'fail'}. RQ2/H2 structural utility checks: {'pass' if gates['G2_utility'] and gates['G3_alternate'] else 'fail'}. RQ3/H3 cross-family collateral gate: {'pass' if gates['G4_collateral'] else 'fail'}; direction held in {result['collateral_improvement_families']}/4 families. RQ4/H4 is descriptive and is answered by the condition and information-access tables rather than a post hoc significance claim.",
              "", "### 4.6 Trace-grounded examples", ""]
    if not examples:
        parts.append("There were no judge/verifier disagreements to illustrate. No examples were selected to manufacture a phenomenon absent from the complete corpus.")
    for agent, judge in examples:
        iid = agent["instance_id"]
        parts += [f"Case `{iid}` ({agent['condition']}): judge success={judge['decision']['success']}; deterministic success={agent['verdict']['success']}. The complete real claim, judge rationale, requested actions, visible receipts, and authoritative state are in `{relative}/raw/agent/{iid}.json` and `{relative}/raw/judge/{iid}.json`. This is a lexicographically selected example, not an additional observation or a basis for changing the protocol.", ""]
    parts += ["### 4.7 Validity threats and relation to prior work", "",
              "Internal validity is bounded by oracle specification, synthetic state construction, and information asymmetry. The judge may be unable to infer collateral corruption absent from the transcript. Any measured gap is therefore compatible with improved access to authoritative state rather than an intrinsic advantage of deterministic reasoning. The full-state diagnostic makes that explanation testable at small scale. The verifier and the label definition share semantic predicates, so perfect verifier classification cannot independently validate those predicates.",
              "", "Construct validity is limited by parameterized field-assignment tasks, degenerate one-goal failure categories, and imposed rather than naturally arising corruption. External validity is limited to these model versions, decoding settings, prompts, templates, and simulator. The primary within-template interval can be optimistic if repeated instances share systematic model behavior; the template-cluster interval is reported alongside it. Neither interval converts this designed corpus into a random sample of production tasks.",
              "", "The findings complement established state-based approaches in tau-bench and AppWorld and learned proxy-state approaches; they do not replace realistic benchmark evaluation. A measurable learned-judge error rate is an engineering observation under specified information access, not evidence that all learned evaluation is unreliable.",
              "", "## Chapter 5: Conclusions and Future Work", "",
              f"The completed frozen experiment is classified **{result['classification']}**. The true measured invalid-state acceptance rate was {j['rate']:.1%} for the transcript-only learned judge, with a paired gap of {result['delta_FSAR']:.1%} relative to the full-state semantic verifier. The classification follows the original numerical gates; unsuccessful gates are retained. The report supports only this bounded evaluator-disagreement measurement and the separately observed natural action-state outcomes.",
              "", "The next defensible study would predefine richer task structures, independently audit oracle completeness, vary observation access on a larger matched corpus, and replicate with a different agent and independently selected judge or a genuinely different task domain. Such work requires a new prospective protocol; it must not tune this discovery set or reinterpret a negative result as a positive one. No cross-model replication, deployment, or universal safety claim is made here.",
              "", "## References", "",
              "1. Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024). *tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*. arXiv:2406.12045; ICLR 2025. https://arxiv.org/abs/2406.12045",
              "2. Trivedi, H., Khot, T., Hartmann, M., Manku, R., Dong, V., Li, E., Gupta, S., Sabharwal, A., & Balasubramanian, N. (2024). *AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents*. ACL, 16022–16076. https://doi.org/10.18653/v1/2024.acl-long.850",
              "3. Chuang, Y.-S., Kulkarni, C., Chiu, A., Thangali, A., Pan, Z., Shekhar, S., Ge, Y., Li, Y., Kona, U., Pang, L., & Mehrotra, P. (2026). *Toward Scalable Verifiable Reward: Proxy State-Based Evaluation for Multi-turn Tool-Calling LLM Agents*. arXiv:2602.16246v3. https://arxiv.org/abs/2602.16246",
              "4. Qwen Team. (2024). *Qwen2.5-7B-Instruct model card and immutable repository revision*. https://huggingface.co/Qwen/Qwen2.5-7B-Instruct",
              "5. Mistral AI. (2024). *Mistral-7B-Instruct-v0.3 model card and immutable repository revision*. https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3",
              "", "## Appendix A: Provenance and artifact map", "",
              f"- Frozen protocol: `FROZEN_PROTOCOL.json`; SHA-256 `{result['protocol_sha256']}`.",
              "- Preregistration: `PREREGISTRATION_v1.md`; dated changes: `AMENDMENT_20260908_PRE_RESULTS.md` and `AMENDMENT_20260908_AUDIT_BINDING_V2.md`; unchanged v1 inputs are archived in `history/protocol_v1_20260908/`.",
              "- Exact allocations and instantiated task records: `configs/discovery_allocation.json`, `configs/pilot_allocation.json`, and `configs/scientific_tasks.json`.",
              f"- Run manifest: `{relative}/manifest.json`.",
              f"- Complete raw request/response lineage: `{relative}/raw/inference/`; task-level raw evidence: `{relative}/raw/actions/`, `raw/agent/`, `raw/judge/`, and `raw/full_state_judge/`.",
              f"- Independent result: `{relative}/INDEPENDENT_VERIFICATION.json`; SHA-256 `{file_hash(run_dir / 'INDEPENDENT_VERIFICATION.json')}`.",
              f"- Decision and completion seal: `{relative}/FINAL_DETERMINATION.md` and `{relative}/COMPLETE.json`.",
              "- The ledger inside independent verification hashes every raw artifact; no completed run is overwritten.",
              "", "## Appendix B: Reproduction", "", "```text",
              "python -m unittest final_praxis.001_outcome_state_verification.harness.test_scientific -v",
              f"python -m final_praxis.001_outcome_state_verification.harness.verify_scientific final_praxis/001_outcome_state_verification/{relative} --read-only",
              f"python -m final_praxis.001_outcome_state_verification.harness.build_report final_praxis/001_outcome_state_verification/{relative}", "```", "",
              "Full staged model execution commands are in `REPRODUCIBILITY.md`. Preserve frozen bytes across operating systems. Any scientific input change requires an amendment and a new compatible run; report formatting alone does not alter frozen evidence."]
    out = ROOT / "paper"
    out.mkdir(exist_ok=True)
    (out / "PRAXIS_REPORT.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    table_dir = out / "tables"
    table_dir.mkdir(exist_ok=True)
    with (table_dir / "evaluator_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["evaluator", "metric", "numerator", "denominator", "rate"])
        writer.writeheader()
        writer.writerows({"evaluator": evaluator, "metric": metric, **cell}
                         for evaluator, values in metrics.items() for metric, cell in values.items())
    with (table_dir / "condition_outcomes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["instance_id", "task_id", "task_family", "condition", "judge", "det", "self_report"])
        writer.writeheader()
        writer.writerows(condition_rows)
    (ROOT / "FINAL_DETERMINATION.md").write_text(
        (run_dir / "FINAL_DETERMINATION.md").read_text(encoding="utf-8")
        + f"\nImmutable source: `{relative}/FINAL_DETERMINATION.md`. Full Praxis report: `paper/PRAXIS_REPORT.md`.\n",
        encoding="utf-8")
    (ROOT / "INDEPENDENT_VERIFICATION.md").write_text(
        "# Final Praxis 001 independent verification\n\nStatus: **PASS**. All 400 discovery units were recomputed from raw evidence.\n\n"
        "The separate audit checks frozen configuration and source hashes, run-manifest equality, exact unit allocation, independent natural execution replay, controlled state projection, public receipts, raw prompt/system binding, distinct model identities and runtime settings, inference request/response lineage, denominator completeness, paired metrics and unchanged gates.\n\n"
        f"Verification: `{relative}/INDEPENDENT_VERIFICATION.json`; SHA-256 `{file_hash(run_dir / 'INDEPENDENT_VERIFICATION.json')}`.\n",
        encoding="utf-8")
    provenance = {"protocol_sha256": result["protocol_sha256"], "run_directory": relative,
        "verification_sha256": file_hash(run_dir / "INDEPENDENT_VERIFICATION.json"),
        "report_sha256": file_hash(out / "PRAXIS_REPORT.md"), "classification": result["classification"],
        "tables": {path.name: file_hash(path) for path in table_dir.glob("*.csv")}}
    (out / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    (ROOT / "CURRENT_STATUS.md").write_text(
        f"# Final Praxis 001 current execution status\n\n**Completed: {result['classification']}.** All 400 discovery units and the 40-case full-state judge diagnostic have real model output and passed independent artifact verification.\n\n"
        f"Judge invalid-state acceptance: {proportion(j)}. Deterministic invalid-state acceptance: {proportion(d)}. Primary paired FSAR interval: {ci}. Failed frozen gates: {failed}.\n\n"
        f"Primary judge malformed outputs: {result['malformed_counts']['judge_malformed']}/400; full-state judge malformed outputs: {diagnostic_malformed}/40. These are rejection outcomes under the unchanged frozen parser and must not be interpreted as successful semantic evaluation.\n\n"
        f"Protocol: `{result['protocol_sha256']}`. Evidence run: `{relative}`. Full five-chapter Praxis report: `paper/PRAXIS_REPORT.md`.\n\n"
        "The 16-case v2 pilot and historical v1 pilot do not enter scientific denominators. Imposed state corruption is separate from natural agent action-state performance. No replication or general safety claim is made.\n",
        encoding="utf-8")
    return out / "PRAXIS_REPORT.md"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    print(build(parser.parse_args().run_dir))
