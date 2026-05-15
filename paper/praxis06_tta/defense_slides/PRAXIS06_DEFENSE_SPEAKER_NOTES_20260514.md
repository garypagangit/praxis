# Praxis 06 Defense Speaker Notes

Generated: 2026-05-15

Use with: `paper/praxis06_tta/defense_slides/PRAXIS06_DEFENSE_SLIDES_20260514.pptx`

## Defense Through-Line

The whole talk should keep one sentence alive:

> I am not claiming that test-time adaptation solves APT detection generally; I am showing that a safety-gated, no-label adaptation policy can recover a shifted rare stage in one locked streaming APT setting while preserving a high-consequence class.

Keep the original locked replay primary. The seven-seed result is robustness, not a replacement.

## Timing

| Block | Slides | Time | Purpose |
|---|---:|---:|---|
| Setup | 1-3 | 4 min | Why rare-stage collapse under shift matters |
| Method and gates | 4-7 | 7 min | Show this was constrained before test replay |
| Evidence | 8-10 | 8 min | Main result, alternative explanation check, hardening |
| Boundaries | 11-12 | 4 min | External-validity limit and final claim |
| Buffer | Backup | 7 min | Questions and committee probes |

## Slide Notes

| Slide | Say this | Do not say |
|---:|---|---|
| 1 | "This is the lead positive result from the portfolio. The claim is deliberately narrow because security adaptation without guardrails can be unsafe." | "TTA solves APT detection." |
| 2 | "The failure mode is not overall accuracy collapse; it is rare-stage collapse hidden inside acceptable-looking aggregate metrics." | "Recon is always the most important class." |
| 3 | "The earlier routing and imbalance attempts are not failures to hide; they explain why the final method became a gated deployment-time policy. Provenance is now label/data ready, but detector generalization is still a separate blocker." | "Those experiments were wasted." |
| 4 | "These gates define the claim: Macro improves, Recon recovers, DE is protected, override stays selective, and a matched reject baseline cannot explain the result." | "We tuned until it worked." |
| 5 | "The contribution is the selective decision policy around adaptation. BatchNorm adaptation alone is not the story." | "The model learns new labels at test time." |
| 6 | "Labels are not used during test adaptation; the validation split selects the safety policy, and the test stream is a locked replay." | "The graph is causal proof." |
| 7 | "The validation/test Recon distribution gap is real. I treat it as deployment shift and report sensitivity checks rather than pretending it is IID." | "The split is perfectly representative." |
| 8 | "The main gain is operating-point rescue: Recon F1 rises from `0.0250` to `0.5050`; PR-AUC barely changes, so the ranking is not the claim." | "The representation got broadly better." |
| 9 | "Rejecting the same fraction by frozen confidence does not recover Recon. This answers the simplest filtering explanation." | "All filtering baselines were exhausted." |
| 10 | "Hardening supports the locked result: seven seeds, validation sensitivity, stronger frozen baselines, stream-order checks, and override decomposition." | "The seven-seed run replaces Table 1." |
| 11 | "DAPT is the boundary condition: the detector recipe transfers, the TTA mechanism does not. I keep that negative result visible." | "DAPT is irrelevant." |
| 12 | "The final claim is a safety-gated decision-policy pattern for security ML adaptation, not universal cross-dataset TTA." | "This is production-ready for every SOC." |

## Likely Committee Questions

| Question | Crisp answer |
|---|---|
| Why not call this general TTA for APT? | Because DAPT2020 is negative. The supported claim is Unraveled/source-file shift with a locked safety gate. |
| Did the gate simply filter hard examples? | The matched-rate confidence reject baseline rejects `4.7%` and Recon F1 remains `0.0000`, so filtering alone does not explain recovery. |
| Why is PR-AUC nearly unchanged? | That is exactly why the paper frames this as an operating-point decision-policy improvement, not broad ranking improvement. |
| Is DE truly protected? | Mean DE is nonnegative and every extended-seed result stays inside the declared per-seed `-0.05` guard. One seed regresses slightly in the original replay, which is disclosed. |
| Did validation overrepresent Recon? | Yes. The defense acknowledges this and uses validation-distribution sensitivity as a robustness check. |
| Why BatchNorm adaptation? | It is the smallest no-label adaptation mechanism available in this detector lineage and is auditable under a locked stream replay. |

## Backup Slide Guidance

- Use Backup A if asked about seed variance.
- Use Backup B if asked about validation/test distribution mismatch.
- Use Backup C if asked whether the frozen baseline was too weak.
- Use Backup D if asked how the artifact trail is reproducible.

## Closing Sentence

"The scientific contribution is not that every adaptation helps. It is that, in this locked streaming APT setting, a validation-selected safety gate lets a no-label adaptation branch recover a rare shifted stage while preserving the class I declared as high-consequence before the replay."
