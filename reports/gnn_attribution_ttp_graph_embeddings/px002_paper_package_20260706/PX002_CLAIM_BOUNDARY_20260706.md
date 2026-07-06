# PX-002 Claim Boundary

Generated: 2026-07-06

Praxis ID: `PX-002`

Status: **BOUNDED LOOKUP-STYLE POSITIVE ONLY**

## Approved Claim

PX-002 supports this bounded claim:

> On the measured MITRE ATT&CK group-technique profile matrix, five observed techniques sampled from known group profiles can retrieve the correct group profile with high top-5 accuracy under a standard profile-lookup protocol: overlap top-5 `0.960` and SVD top-5 `0.879`, compared with random `0.028` and frequency prior `0.041`.

This is a profile lookup and analyst-triage result. It is not a major defense pillar.

## Required Wording

| Evidence | Required wording |
|---|---|
| Main standard protocol | `605` five-shot queries; overlap top-5 `0.960`; SVD top-5 `0.879`; random top-5 `0.028`; frequency-prior top-5 `0.041`; median rank `1.0` for overlap and SVD. |
| Degree buckets | Five-shot overlap and SVD remain visibly above random/frequency floors across low-, mid-, and high-degree eligible groups. |
| GraphSAGE gate | GraphSAGE failed: known-profile five-shot top-5 `0.060` vs SVD `0.926` and overlap `0.985`; do not pitch a GNN win. |
| Noisy-query audit | With 40% query noise, overlap top-5 `0.788` and SVD top-5 `0.577`; useful but weakened. |
| Leave-query-out audit | Removing query techniques from the target candidate profile causes overlap top-5 `0.000` and SVD top-5 `0.299`; this blocks a strong generalization or defense-pillar claim. |

## Allowed Language

- "ATT&CK group-profile retrieval"
- "observed TTP-set lookup"
- "analyst triage"
- "hypothesis generation"
- "bounded profile-retrieval utility"
- "known-profile protocol"
- "GraphSAGE negative gate"
- "not CTI prose attribution"
- "not actor authorship"

## Avoid This Language

- "APT attribution is solved"
- "identifies the attacker"
- "attributes raw CTI reports"
- "proves GraphSAGE works"
- "robust defense mechanism"
- "defense-ready pillar"
- "generalizes beyond known ATT&CK profiles"
- "authoritative attribution decision"

## Defense Readiness

PX-002 should be used as a supporting portfolio result, not as a lead Praxis defense result. It is useful when the defense story needs an honest bounded CTI retrieval artifact:

1. Present the standard five-shot lookup result.
2. Show random and frequency-prior floors.
3. Show degree-bucket sensitivity.
4. State that GraphSAGE failed and that simple baselines are the supported mechanism.
5. Present the defense audit and explicitly demote the claim at the leave-query-out boundary.
6. Position the result as analyst-triage support for narrowing candidate group profiles, not as final attribution.
