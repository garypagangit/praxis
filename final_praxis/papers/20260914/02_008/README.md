# 02 - Selective disclosure of executed tests (Final-Praxis-008)

**In simple words:** an AI reviewer can be misled by real test results when failures are left out. This study measures that effect and an attempted defense. The disclosure effect was supported for one reviewer configuration; the defense did not meet its success criteria.

Read the completed [paper and executive summary](PAPER.md), [PDF](PAPER.pdf), or [editable Word document](PAPER.docx).

## Evidence package

All public evidence linked below is already present in this same branch. It is not duplicated inside this folder. Clone the repository to preserve the relative layout.

| What to inspect | Repository artifact |
|---|---|
| Prospective methods | [Original protocol](../../../008_independent_evidence_audit/code_study/MODEL_STUDY_PREREG.md) and [final schema extension](../../../008_independent_evidence_audit/code_study/technical_extension/PREREG_V2.md) |
| Public sources and qualification | [Source manifest](../../../008_independent_evidence_audit/code_study/qualification/SOURCE_MANIFEST.json) and [qualification audit](../../../008_independent_evidence_audit/code_study/completed_qualification/FULL_INDEPENDENT_AUDIT.json) |
| Paired decisions, assignments and results | [V2 statistical package](../../../008_independent_evidence_audit/code_study/completed_models/schema_extension_v2) and [original V1 package](../../../008_independent_evidence_audit/code_study/completed_models/original_v1) |
| Complete retained analysis | [V2 model results](../../../008_independent_evidence_audit/code_study/completed_models/schema_extension_v2/MODEL_RESULTS.md) and [acquisition results](../../../008_independent_evidence_audit/code_study/completed_models/schema_extension_v2/ACQUISITION_RESULTS.md) |
| Numerical correction | [Secondary roundoff erratum](../../../008_independent_evidence_audit/code_study/postrun_review/roundoff_amendment/NUMERICAL_ERRATUM.json) |
| Artifact replay and readiness | [Amended full audit](../../../008_independent_evidence_audit/code_study/postrun_review/completed_extension_v2/ARTIFACT_AUDIT.json) and [readiness checks](../../../008_independent_evidence_audit/code_study/paper_package/PAPER_READINESS.json) |
| Exact file identities | [Evidence manifest](EVIDENCE_MANIFEST.json) and [verification receipt](EVIDENCE_VERIFICATION.json) |

From this directory:

```text
python verify_evidence.py
python verify_evidence.py --reproduce
```

The second command reproduces the published statistical calculations from the included rows, including the frozen bootstrap analysis. It makes no model calls and executes no candidate programs. Python dependencies are those in the canonical study's reproduction instructions. The raw provider campaign and complete privileged execution archive are a separate owner-held audit layer; this public package supports statistical reproduction without cloud credentials. It does not promise byte-identical fresh responses from a managed model service.

The original 008 result and its historical review receipts are preserved. This reading edition adds a plain-language executive summary and refreshed document formatting. It does not change the experiment, hypothesis tests or outcomes.
