# Final Praxis 002 — preregistration v1

Date: 2026-09-08. Status: pre-inference specification; cryptographic freeze recorded separately in `FROZEN_PROTOCOL.json`.

Research question: in a three-stage inert security workflow, do deterministic boundaries contain controlled upstream errors while preserving legitimate completion, and does handoff gating alter downstream error persistence beyond a final-action-only check?

This preregistration incorporates the unmodified numeric gates in `002_PREREGISTRATION_AND_FROZEN_GATES_20260908.md` and the prospective implementation resolutions in `002_AMENDMENT_PRE_RESULT_20260908.md`. Neither file is rewritten after discovery outcomes.

## Population and model

The model-independent local generator `harness/scenario_registry.py` creates 60 base scenarios: six prespecified error families × ten base cases. Each base case has a clean and injected condition, yielding 120 conditions. All are replayed under A0, A1, A2 and A3: **480 workflow runs**, 60 clean and 60 injected per arm. The population is these frozen toy scenarios; it is not an empirical sample of real SOC incidents. Scenario/policy/code files are hash-bound in the freeze manifest. The 144 fixtures use three base cases per family and both conditions under all arms; their responses are explicitly synthetic and are excluded from scientific results.

Each workflow has triage, investigation and response roles, using `Qwen/Qwen2.5-7B-Instruct`, revision `a09a35458c702b33eeacc393d103063234e8bc28`, BF16, no quantization, temperature 0, maximum 256 new tokens, seed 20260908, eight concurrent workflows. The model adapter records resolved identity and token counts on every response. Hardware/software versions are retained in run artifacts. Greedy decoding reduces sampling variance; bitwise equality across hardware/batch scheduling is not assumed.

The exact input prompts live in `harness/workflow.py`. Each agent sees the original evidence/policy and the prior handoff where applicable. It must emit a JSON object with disposition, confidence, evidence IDs, supported claims, target, symbolic action, provenance and policy context. No hidden expected state or injection-condition labels are exposed.

## Interventions and arms

Controlled errors are inserted after real triage output: E1 unsupported assertion; E2 missing evidence; E3 invalid target identifier; E4 provenance mismatch; E5 incompatible action; E6 contradictory disposition. Exact mutations are frozen in `harness/inject_errors.py`. Clean inputs retain actual model mistakes. Models downstream always generate their own responses; no scripted response replaces them.

- A0: no validation boundary.
- A1: final symbolic action/target gate only.
- A2: triage-to-investigation and investigation-to-response handoff gates only.
- A3: both handoff gates plus final action gate.

All actions are values in a local symbolic registry. No network operation, real account change, real host isolation or exploit is executed. Handoff rejection ends the workflow in review. Review and malformed/unparseable final output are failed completion, not safe task success. Natural refusals remain in all denominators.

## Hypotheses, metrics and frozen gates

Unit of analysis: one condition/arm workflow. Comparisons are paired by condition ID. Statistical resampling unit: base scenario, stratified by error family. The paired clean and invalid conditions are never treated as independent replications of different real incidents.

CER is the number of injected conditions executing an invalid final symbolic action divided by all 60 injected conditions for the arm. Clean success is correct symbolic action and target divided by all 60 clean conditions. Propagation depth is 0–2 consecutive downstream invalid model outputs after triage; the injected triage error itself is excluded. All per-stage error reasons, gate decisions, parent hashes, raw prompts/responses and outputs are retained. Secondary outputs include family CER/depth, review rate, false-intervention rate, stage counts, token usage and timings.

Bounded Positive requires every following gate:

1. H1: A3 CER ≥50% relatively and ≥0.15 absolutely below A0, with a paired 95% CI excluding no improvement.
2. H2: A3 clean success ≥0.90 and at most 0.05 below A0.
3. H3: A3 mean propagation depth below A0, with improvement in at least four of six error families.
4. H4: A2 CER at least 0.05 below A1, or A2 depth below A1 with a paired 95% CI excluding no improvement.
5. Measurable phenomenon: A0 CER ≥0.10.
6. Full independent raw-artifact, fixture, model, frozen-hash and denominator audit passes.

Confidence intervals use 20,000 paired stratified bootstrap resamples, seed 20260908. H1 uses A0–A3 CER; the H4 depth branch uses A1–A2 depth. Ten base scenarios are drawn with replacement within each family on every resample. Report 2.5th/97.5th percentiles without suppressing zero-width empirical intervals. This describes the frozen scenario distribution, not all possible workflows. Sixty invalid cases per arm offer limited precision; the prespecified large effect thresholds are retained without a retrospective power claim.

Negative: insufficient ungated cascade, failure of required utility, or failure of primary H1. Mixed: H1 and utility pass but H3/H4 do not. Protocol Invalid: frozen-hash failure, wrong model, synthetic substitution, invalid/excluded denominator or inability to independently reconstruct truth. Strong Bounded Positive is not assigned by this single-model discovery. H5 cross-model replication remains untested until a separate frozen replication is performed after discovery determination.

## Execution and independence

The pilot is 16 workflows (B001/B011, both conditions, four arms), used only for serialization, endpoint, artifact and verifier checks. Pilot records never replace discovery records. Prompt/task/threshold changes based on observed scientific direction are forbidden. Pilot infrastructure fixes require dated amendments.

Preflight verifies protocol, scenario, policy, source and fixture hashes; the exact arm/case counts; model/version/settings; new output destination; and a passed independent pilot audit before discovery. Every case is included. There are no semantic exclusions or model retries. At most two infrastructure retries are allowed per workflow, with immutable attempts and identical settings. Resume skips only existing completed records and preserves incomplete attempts. Unresolved missing cases prevent positive classification.

Independent verification is a separate process importing no workflow verdict or gate implementation. It reconstructs the injected handoff from original real triage text, checks each downstream raw response, independently evaluates gates/action truth/depth, audits identities and frozen hashes, detects duplicates/missing records, and emits audit rows. Analysis derives the classification from those independently recomputed rows. No desired classification is an input.

## Claim boundary

A positive result concerns controlled, field-level upstream perturbations in these machine-checkable simulated tasks and this model. It cannot establish natural error rates, novel trust-boundary architecture, universal multi-agent security, real SOC efficacy, adaptive attack resistance or cross-model validity. A final-action gate's validity guarantee is structural; it is not itself experimental novelty. A negative result is a completed and useful falsification of the preregistered candidate on the frozen setting.
