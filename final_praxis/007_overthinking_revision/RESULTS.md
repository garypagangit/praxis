# Final Praxis007 first pilot — completed 12 September 2026

All384 planned responses completed on AWS at08:47:04UTC, with no checkpoint-sync errors. The original frozen run is `fp007-20260912-81b445c`; source commit81b445c2bb5782757143976432d9ac127cb97988. Model API cost from provider token receipts was approximately$0.1681, excluding the shared CPU host and storage. This is an estimate, not an invoice.

**Decision:** advance this direction to a larger, carefully specified method study. It has measurable harmful revision and useful recovery. No novel method, shared neural mechanism or publication-ready efficacy result has been demonstrated.

The strict, preregistered Qwen result supplies29 valid initial answers from32:21 benchmark-key correct and8 wrong. It passes the original feasibility gate. Its EX-FEVER subset is the clearest initial experimental setting:

| Revision condition | Correct-to-wrong among8 initially correct | Wrong-to-correct among7 validly wrong |
|---|---:|---:|
| Neutral review |0|0|
| Solo additional review |1|1|
| Unsupported false peer |3|1|
| Reference evidence |0|7|

Invalid/truncated answers remain separately counted in summary.json; for example false-peer review also loses one initially correct EX-FEVER answer to invalidity. These are16 calibration questions, not16 independent replications of the method. Results are relative to the unchanged benchmark keys. Dataset evidence and key validity need an independent audit before substantive claims; one exposed AQuA item has been flagged for review without changing its label.

**Formatting sensitivity.** Devstral failed the original strict feasibility gate with only8 valid initial answers from32. A subsequent audit found24 strict-invalid initial answers but only one truncated response. A separately committed post hoc protocol (b832bbbe0e4c19a9a0b4c96ecd34ff4b6e498c65) normalized only whole-output JSON string encoding and balanced terminal Markdown wrappers. It verified every original score and reproduced the complete strict summary exactly before rescoring all384 saved responses. No new inference or changed labels were used.

That sensitivity makes31 of32 Devstral initial answers scorable:22 correct and9 wrong, with3 harmful false-peer revisions and8 evidence recoveries across both datasets. On EX-FEVER specifically, false peers overturn3 of9 initially correct answers versus zero under neutral review; evidence recovers7 of7 wrong answers but also overturns2 initially correct answers. Qwen's scores are unchanged by normalization. These are post hoc sensitivity results with changed correctness denominators; Devstral is not relabeled as a preregistered pass. See format_sensitivity/sensitivity_summary.json and its frozen protocol for all conditions and invalidity counts.

**Research implication.** Prioritize a selective update method that preserves justified initial decisions while accepting genuinely corrective evidence, then test it on untouched examples and fixed open model weights. A generic confidence/verification gate and the observation of peer-induced errors already have substantial prior art, including [SRU](https://arxiv.org/html/2608.26511v1). An additional-deliberation API comparison does not reproduce the mechanistic claims of [Thinking Past the Answer](https://arxiv.org/html/2606.02835v1). A specific new objective, constraint or process must survive a focused overlap review and beat matched-budget controls before this becomes the primary Praxis.

Raw responses remain in the private campaign S3 archive. The complete strict summary, formatting protocol, source references, aggregate sensitivity results and hashes are committed. The local post hoc output directory also retains a case list for independent evidence/key review.
