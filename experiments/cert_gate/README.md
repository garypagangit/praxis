# Certified suppression gate for SOC alert triage

Branch: **cert-gate**. Scope: offline experiment; no live alert is suppressed.

The program evaluates how much benign-alert workload can be removed while controlling the fraction of actual attacks suppressed. Useful suppression is an empirical question. Statistical risk control, integrity checks and novelty are separate requirements.

## Work started

- Preserve the supplied proposal and record necessary corrections.
- Acquire and audit the proposed public data and nearest literature.
- Implement scorer-independent risk calibration and deterministic eligibility checks.
- Run synthetic qualification with known population risks and explicit failure counterexamples.
- Prepare a blinded human label-review packet and a concrete record of unresolved data requirements.

The [registration](REGISTRATION.json) currently releases G0 and software qualification. [Amendments](AMENDMENTS.md) explain why the original draft cannot be executed literally. Real-data model reproduction and confirmatory G2-G5 remain gated on actual data support, reviewed labels and a model-specific frozen protocol. No human review, literature reproduction, workload benefit or novelty is asserted by constructing this harness.

## Risk contract

Let `s(x)` be a frozen benignness score and `e(x)` the frozen deterministic eligibility rule. The gate suppresses only if `e(x)` and `s(x)>threshold`. The primary target is `P(suppress | true attack)<=0.01`, with95% confidence over independent attack-calibration samples under the stated distributional assumptions. A conservative fallback keeps every alert when nontrivial calibration is unsupported. This is established statistical machinery.

## Data and evidence

Raw downloaded corpora and human-review excerpts stay outside Git. Committed manifests contain exact hashes, acquisition/qualification outcomes and reproduction instructions. The user proposal is user-provided source material. Generated fixtures and simulation outcomes are software evidence and must never be counted as real SOC results.
