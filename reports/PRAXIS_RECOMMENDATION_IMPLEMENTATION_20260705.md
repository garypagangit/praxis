# Praxis Recommendation Implementation Update

Generated: 2026-07-05

## Summary

The external review produced concrete updates. The most important recommendation was to test whether PX-034's source-conflict buckets actually predict downstream CTI answerability. That gate has now been run on AWS with Qwen2.5-7B over all `500` CTI-MCQ rows.

## Tangible Updates Completed

1. **AWS SSO and compute readiness restored.**
   - AWS profile: `praxis-build`.
   - Account: `272615233626`.
   - Instance used: `i-07178e293e8df2a60`, `g5.xlarge`.

2. **PX-003/PX-034 full-bucket downstream gate implemented and run.**
   - New builder: `scripts/build_cti_full_bucket_prompt_file.py`.
   - New analyzer: `scripts/analyze_cti_bucket_downstream_accuracy.py`.
   - New cloud wrapper: `cloud_jobs/cti_full_bucket_downstream_20260705/`.
   - AWS output: `reports/relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/`.

3. **PX-003/PX-034 claim boundary updated.**
   - Relationship evidence improves Qwen2.5-7B full-table accuracy from `0.6140` to `0.8220`.
   - Relationship evidence improves all five source-conflict buckets.
   - PX-034 should be framed as source-support risk stratification, not as a hard answerability oracle.

4. **PX-005 novelty positioning updated.**
   - The 2026 ACL/arXiv paper `The Illusion of Specialization: Unveiling the Domain-Invariant "Standing Committee" in Mixture-of-Experts Models` (`arXiv:2601.03425`) already establishes the Standing Committee framing.
   - PX-005 remains useful as a bounded confirmation/extension under a frozen Praxis prompt-domain audit across OLMoE and Qwen1.5-MoE.

## PX-003/PX-034 Full-Bucket Result

| Bucket | Rows | Vanilla accuracy | Relationship-evidence accuracy | Delta |
|---|---:|---:|---:|---:|
| Ambiguous multi-source | `28` | `0.5357` | `0.7143` | `+0.1786` |
| Conflicting high-support | `179` | `0.5307` | `0.8101` | `+0.2793` |
| Decisive | `106` | `0.6226` | `0.9057` | `+0.2830` |
| Unsupported | `150` | `0.6933` | `0.7733` | `+0.0800` |
| Weak single-source | `37` | `0.7297` | `0.9189` | `+0.1892` |
| Full table | `500` | `0.6140` | `0.8220` | `+0.2080` |

## Interpretation

The recommendation strengthened PX-003 and narrowed PX-034.

Strengthened:

- PX-003 is now not only a decisive-slice result. Relationship evidence improves Qwen2.5-7B accuracy across the full 500-row CTI-MCQ source-conflict table.
- The decisive bucket still has the largest clean original defense delta and remains the best-supported direct-answer slice.

Narrowed:

- PX-034 cannot be claimed as a strict answerability router because non-decisive buckets also answer well under forced relationship-evidence prompting.
- The right claim is source-support risk stratification: PX-034 identifies evidence conflict/support structure and a high-confidence decisive slice, but it does not prove non-decisive rows are unanswerable.

## Next Recommended Tangible Updates

1. **PX-003 full-bucket ablation expansion.**
   - Run `technique_only_evidence`, `random_facts`, `empty_evidence`, and `broad_seed` across all 500 rows.
   - Purpose: determine whether the full-table lift is relationship-specific, evidence-specific, or partly prompt/evidence-format driven.

2. **PX-004 model-family expansion.**
   - Add one or two more code-tuned models to FalseCite-Code.
   - Add adversarial near-miss claims such as version/package conflations.

3. **PX-016 cheap reopening attempt.**
   - Try a two-stage guardrail cascade or calibration sweep because the prior gate missed only the safe-response blocking ceiling.

4. **Portfolio synthesis.**
   - Reframe the defense umbrella as gated trust for AI/security systems:
     - PX-001: safety gate on adaptation.
     - PX-003/PX-034: evidence and source-conflict gate on CTI answering.
     - PX-004/PX-011: deterministic external verification for citation/source trust.

## Evidence

- Full-bucket report: `reports/relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/PX003_PX034_FULL_BUCKET_DOWNSTREAM_ACCURACY_AUDIT.md`
- Full-bucket summary: `reports/relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/summary.json`
- Bucket analyzer output: `reports/relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/cti_bucket_downstream_accuracy.json`
- PX-005 literature anchor: `https://arxiv.org/abs/2601.03425`

