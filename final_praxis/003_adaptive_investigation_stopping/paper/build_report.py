"""Build the five-chapter report only from independently verified discovery artifacts."""
import argparse
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def pct(value):
    return "undefined (no eligible degradation cases)" if value is None else f"{value*100:.2f}%"

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);args=p.parse_args()
    analysis=json.loads((args.run_dir/"analysis.json").read_text())
    audit=json.loads((args.run_dir/"INDEPENDENT_VERIFICATION.json").read_text())
    complete=json.loads((args.run_dir/"RUN_COMPLETE.json").read_text())
    if audit["status"]!="PASS" or audit["verified_cases"]!=400 or audit.get("infrastructure_pilot_only") or not analysis["scientific"]:
        raise ValueError("A verified complete scientific discovery is required.")
    if audit["classification"]!=analysis["classification"]:raise ValueError("Classification mismatch")
    rows=[json.loads(line) for line in (args.run_dir/"raw.jsonl").read_text().splitlines()]
    out=ROOT/"paper";out.mkdir(exist_ok=True)
    target=out/"PRAXIS_REPORT.md"
    if target.exists():raise FileExistsError("Preserve published report; choose a versioned report amendment.")
    arms=analysis["arms"];a4=arms["A4"]
    stages=[]
    for r in range(1,9):
        stage=[row for row in rows if row["round"]==r]
        stages.append({"round":r,"n":len(stage),"correct":sum(row["correct"] for row in stage),
                       "abstain":sum(row["disposition"]=="abstain" for row in stage),
                       "tokens":sum(row["token_count"] for row in stage)})
    with (out/"round_breakdown.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(stages[0]));writer.writeheader();writer.writerows(stages)
    family_rows=[]
    for family in sorted(analysis["family_breakdown"]):
        subset=[row for row in analysis["case_results"] if row["family"]==family]
        for arm in arms:
            vals=[row["arms"][arm] for row in subset]
            family_rows.append({"family":family,"arm":arm,"n":len(vals),"correct":sum(v["correct"] for v in vals),
                "harm":sum(v["harm"] for v in vals),"prevented":sum(v["prevented"] for v in vals),
                "review":sum(v["reviewed"] for v in vals),"abstain":sum(v["abstained"] for v in vals),
                "mean_rounds":sum(v["round"] for v in vals)/len(vals)})
    with (out/"family_breakdown.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(family_rows[0]));writer.writeheader();writer.writerows(family_rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False})
    fig,axs=plt.subplots(1,2,figsize=(10,4))
    names=list(arms);colors=["#8f9ba8","#425b76","#c88b38","#28766b"]
    axs[0].bar(names,[arms[a]["accuracy"]*100 for a in names],color=colors)
    axs[0].set(ylabel="Correctness (%)",ylim=(0,105),title="Final correctness; abstain = incorrect")
    axs[1].bar(names,[arms[a]["round_saving"]*100 for a in names],color=colors)
    axs[1].axhline(20,color="#a94137",ls="--",label="Frozen 20% saving gate")
    axs[1].set(ylabel="Round saving vs A1 (%)",title="Counterfactual policy cost")
    axs[1].legend(fontsize=9);fig.tight_layout()
    fig.savefig(out/"policy_outcomes.png",dpi=180);fig.savefig(out/"policy_outcomes.svg");plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    ax.plot([s["round"] for s in stages],[100*s["correct"]/s["n"] for s in stages],marker="o",label="Correct")
    ax.plot([s["round"] for s in stages],[100*s["abstain"]/s["n"] for s in stages],marker="s",label="Abstain")
    ax.set(xlabel="Frozen investigation round",ylabel="Cases (%)",xticks=range(1,9),ylim=(-2,102),title="Observed eight-round model trajectory")
    ax.legend();fig.tight_layout();fig.savefig(out/"round_trajectory.png",dpi=180);fig.savefig(out/"round_trajectory.svg");plt.close(fig)
    arm_table="\n".join(f"| {arm} | {s['correct']}/400 ({pct(s['accuracy'])}) | {s['mean_rounds']:.2f} | {pct(s['token_saving'])} | {s['harm_cases']} ({pct(s['harm_rate'])}) | {pct(s['harm_upper_95'])} | {pct(s['review_rate'])} | {pct(s['abstain_rate'])} |" for arm,s in arms.items())
    gates="\n".join(f"| {key} | {'PASS' if passed else 'FAIL'} |" for key,passed in analysis["gates"].items())
    ni="\n".join(f"- A4 minus {arm}: {pct(v['difference'])}; lower one-sided 97.5% paired-bootstrap bound {pct(v['lower_97_5'])}." for arm,v in analysis["noninferiority"].items())
    stage_table="\n".join(f"| {s['round']} | {s['correct']}/400 | {s['abstain']}/400 | {s['tokens']:,} |" for s in stages)
    family_table="\n".join(f"| {family} | {value['n']} | {value['a4_correct']} |" for family,value in analysis["family_breakdown"].items())
    harm_decision="passed" if analysis["gates"]["H4_harm"] else "failed"
    report=f"""# Safety-Gated Adaptive Investigation Stopping for Agentic Security Triage

Final Praxis 003 — verified discovery report

## Abstract of Praxis

This experiment tested a mechanically reviewed answer-stability stopping policy on 400 generated inert security authorization cases. A pinned Qwen2.5-7B-Instruct model produced eight cumulative-evidence responses per case, yielding 3,200 real inference records. Fixed-short (A0), fixed-long (A1), answer stability (A2), and safety-gated stability (A4) were evaluated on the same recorded traces. Frozen gates covered correctness, cost, correct-to-wrong prevention, early-stop harm and review. The independent determination was **{analysis['classification']}**. A4 correctness was {pct(a4['accuracy'])}, round saving {pct(a4['round_saving'])}, and token saving {pct(a4['token_saving'])}. Observed A4 harm was {a4['harm_cases']}/400, with a one-sided 95% upper bound of {pct(a4['harm_upper_95'])}; its harm gate {harm_decision}. There were {analysis['degradation_events']} degradation events affecting {analysis['degradation_cases']} cases. These findings apply to this generated authorization-matching benchmark, not independent real incidents or deployed SOC safety.

## Chapter 1: Introduction

Security investigations can stop before decisive evidence arrives, or continue after reaching a correct conclusion and change to an incorrect disposition. Comparing only final accuracy or token cost conceals the difference between prevented degradation and harmful premature stopping. This study evaluates those outcomes separately and charges mechanically required review to the same complete denominator.

The research question is whether safety-gated stability stopping can preserve correctness, reduce investigation cost, and prevent degradation while respecting frozen harm and review ceilings. H1 requires non-inferiority to both frozen non-adaptive baselines within two percentage points. H2 requires at least 20% round and token saving. H3 requires at least 25% prevention and 20 observed degradation events. H4 requires observed harm <=2%, one-sided 95% upper bound <=4%, and review <=20%. H5 restricts evidence to the new security-framed task.

The scope is a controlled generated corpus. Eight security contexts share one authorization rule: an executed action is benign when actor, asset and inclusive time interval match the sole signed approval; otherwise it is malicious. This explicit rule supplies reproducible labels and limits task realism. No historical PX-057 performance is imported, no live security system is operated, and no human reviewer supplies hypothetical correct answers.

## Chapter 2: Literature Review

REFRAIN establishes adaptive early stopping as a reasoning-efficiency mechanism [1]. MiCP treats multi-turn stopping with coverage control [2]. SIR-Bench evaluates incident-investigation depth and active evidence gathering against incident-derived labels [3]. NVIDIA's vulnerability-analysis implementation already supports early termination after consecutive identical security justifications [4]. Consequently, neither general early stopping nor security-domain stability stopping is claimed as a new algorithm.

This experiment's contribution is the bounded paired evaluation protocol: a fixed staged corpus, shared full traces, explicit harmful-stop and prevented-degradation counters, and a mandatory review denominator. The novelty search was focused, performed before outcomes, and did not establish exhaustive priority. The generated benchmark does not inherit the incident realism or expert annotations of SIR-Bench.

## Chapter 3: Methodology

### Design and GMR

The graphical methodological representation (GMR) is: freeze corpus and protocol → validate 80 artificial trajectory fixtures → execute two disjoint real-inference infrastructure cases → independently verify the pilot → collect 400 eight-round discovery traces → evaluate all frozen policies → independently recompute metrics and gates → classify and report. Pilot cases are excluded from discovery and cannot tune prompts, policies, corpus or thresholds.

```mermaid
flowchart LR
    A[Frozen corpus and protocol] --> B[80 trace fixtures]
    B --> C[2-case infrastructure pilot]
    C --> D[Independent pilot verification]
    D --> E[400 cases × 8 real model rounds]
    E --> F[Paired A0 A1 A2 A4 evaluation]
    F --> G[Independent audit and frozen gates]
    G --> H[Bounded determination and report]
```

The corpus contains 50 cases in each of eight families and 200 cases per label. Ground truth and evidence order were generated and hashed before inference. Authoritative evidence appears at a predeclared stage among rounds 2, 4, 6 and 8; later weak context cannot change ground truth. Private label records are excluded from prompts. A pre-discovery independent code audit identified that indexed evidence IDs could encode label parity; a dated amendment replaced only the model-visible IDs with opaque SHA-256 projections. The corpus, labels, evidence order, policies and thresholds were preserved, original frozen sources were archived, and a fresh infrastructure pilot was required under the successor seal. Each round includes only evidence exposed so far and prior normalized dispositions. There is no browsing, adaptive evidence acquisition or feedback from correctness.

The model was `Qwen/Qwen2.5-7B-Instruct` at revision `{complete['revision']}`, using greedy decoding, seed 20260908, BF16 without quantization, and a 64-token output ceiling. Sixteen independent case traces could run concurrently; each case's rounds were sequential. Actual token counters include prompt and completion tokens. Raw responses, request identities, runtime details, prompt hashes and timestamps were retained. Malformed outputs and refusals count as abstentions and incorrect utility, with no exclusions.

A0 stops at round 2; A1 at round 8; A2 after two identical non-abstaining answers, otherwise round 8. A4 applies the same stability rule but emits REVIEW for protected cases, incomplete frozen evidence coverage, a latest-round disposition flip, or abstention. REVIEW continues investigation; unresolved final review yields zero-utility abstention. Any REVIEW counts toward review rate. The collector still records all eight rounds after a policy would stop, allowing counterfactual comparison without altering evidence or outcomes. Reported savings describe evaluated policy prefixes, not total compute consumed to collect the experiment.

Harm is an incorrect selected endpoint with any later correct response. Prevention is a correct selected endpoint followed by at least one incorrect later response among cases with adjacent correct-to-wrong transitions. The full 400 cases form the harm, correctness and review denominators. The harm upper bound is one-sided exact Clopper-Pearson; prevention intervals are two-sided exact intervals. Paired bootstrap intervals use 10,000 replicates and seed 20260908. Non-inferiority compares against both A0 and A1 using conservative one-sided 97.5% lower bounds. Case-template dependence limits any population interpretation of these intervals.

## Chapter 4: Results and Discussion

### Verified outcome

The independent verifier passed all 400 cases and 3,200 unique round records, reproduced policy decisions and counters, and checked protocol/model identities and file hashes. The final classification is **{analysis['classification']}**. Fixture and infrastructure-pilot outputs are separate from these scientific records.

| Arm | Correctness | Mean rounds | Token saving vs A1 | Early-stop harm | Harm upper 95% | Reviewed | Abstained |
|---|---:|---:|---:|---:|---:|---:|---:|
{arm_table}

![Correctness and counterfactual policy round saving](policy_outcomes.png)

### Research questions and frozen gates

| Frozen decision | Result |
|---|---|
{gates}

The correctness comparisons were:

{ni}

A4 round saving was {pct(a4['round_saving'])}, with paired 95% interval [{pct(analysis['round_saving_ci_95'][0])}, {pct(analysis['round_saving_ci_95'][1])}]. Token saving was {pct(a4['token_saving'])}, with paired 95% interval [{pct(analysis['token_saving_ci_95'][0])}, {pct(analysis['token_saving_ci_95'][1])}]. Prevention affected {a4['prevented_cases']} of {analysis['degradation_cases']} eligible cases: {pct(a4['prevention_rate'])}. The harm safety gate {harm_decision}. Mandatory failed gates prevent promotion regardless of favorable descriptive metrics; thresholds remain unchanged.

### Stage and family structure

| Round | Correct | Abstain | Prompt + completion tokens |
|---|---:|---:|---:|
{stage_table}

![Accuracy and abstention at each frozen evidence round](round_trajectory.png)

| Case family | Cases | A4 correct |
|---|---:|---:|
{family_table}

Complete arm-by-family correctness, harm, prevention, review, abstention and round counts are supplied in `family_breakdown.csv`; stage counts are supplied in `round_breakdown.csv`. These are descriptive breakdowns without post-hoc selection of favorable families.

### Limits of interpretation

The same simple authorization construct underlies all eight family templates. The experiment therefore evaluates handling of a fixed explicit decision rule as evidence accumulates, rather than expert incident reasoning. The 400 generated cases are not 400 independent real incidents. Numeric variation and fixed staged distractors do not establish external validity. Review abstentions receive zero utility; there is no assumed analyst rescue. Full traces support policy-prefix counterfactuals but do not establish that deployed adaptive agents would follow the same trajectory when given control of evidence collection. One pinned model and one frozen seed do not establish model-family generality. Shared-server batching and numerical implementation are retained as runtime provenance, not a claim of hardware-independent bitwise identity.

The safety design has a structural constraint, identified before discovery and preserved: 40 protected and 40 disjoint delayed-evidence cases force at least 20% review, consuming the entire review ceiling before any additional model-driven REVIEW. The 40 protected cases force terminal abstention, placing A4 correctness at a maximum of 90%. If a non-adaptive baseline exceeds 92%, the frozen two-percentage-point non-inferiority criterion cannot pass. Thus a negative finding can reflect this conservative review/utility design as well as model behavior. The study does not generalize that limitation into a claim that all possible safety-gated stopping policies fail, and does not relax the rule after observing outcomes.

## Chapter 5: Conclusions and Future Work

The frozen experiment concluded **{analysis['classification']}**. The relevant scientific answer is determined by the mandatory gates above, including negative findings, rather than by selecting favorable aggregate accuracy or cost numbers. A positive deployment-safety claim is not supported by a generated corpus alone. Any future model replication or external incident-corpus study requires its own prospective freeze and must retain this result unchanged.

Future work can evaluate expert-labelled staged incidents, independently selected evidence schedules, realistic analyst-review costs and a second model. Such work must distinguish an absent degradation phenomenon from a failed stopping policy and compare any more complex safety layer with the already available stability baseline.

## References

1. Sun et al. *Stop When Enough: Adaptive Early-Stopping for Chain-of-Thought Reasoning*. 2025/2026. https://arxiv.org/abs/2510.10103
2. Zhou et al. *Adaptive Stopping for Multi-Turn LLM Reasoning*. 2026. https://arxiv.org/abs/2604.01413
3. Begimher et al. *SIR-Bench: Evaluating Investigation Depth in Security Incident Response Agents*. 2026. https://arxiv.org/html/2604.12040v1
4. NVIDIA. *Vulnerability analysis blueprint: test-time compute and early stopping*. Inspected 2026-09-08. https://github.com/NVIDIA-AI-Blueprints/vulnerability-analysis

## Appendix A: Provenance

- Protocol SHA-256: `{complete['protocol_sha256']}`.
- Corpus SHA-256: `{complete['case_sha256']}`.
- Raw discovery SHA-256: `{complete['raw_sha256']}`.
- Completion timestamp: `{complete['completed_at_utc']}`.
- Raw run directory: `{args.run_dir.as_posix()}`.
- Independent receipt: `INDEPENDENT_VERIFICATION.json` in that directory.
- The seal includes generator, policies, prompt/collector, evaluator, independent verifier, fixture marker, corpus, preregistration and shared model-adapter/server code.

## Appendix B: Reproduction

Run `harness/run_traces.py --preflight-only` to validate sealed inputs. The separate `--pilot` run must pass `evaluate_policies.py` and `independent_verify.py` before the discovery collector accepts its matching receipt. Discovery uses `--base-url http://127.0.0.1:8765` and a new output directory. Analysis and verification run only after `RUN_COMPLETE.json` is written. `paper/build_report.py <run_dir>` constructs this document and standalone plots from the verified artifacts. See `BUILD_AND_RUN.md` for exact commands, retry rules and denominator semantics. Completed raw runs and published reports are never overwritten.
"""
    target.write_text(report,encoding="utf-8")
    print(target)

if __name__=="__main__":main()
