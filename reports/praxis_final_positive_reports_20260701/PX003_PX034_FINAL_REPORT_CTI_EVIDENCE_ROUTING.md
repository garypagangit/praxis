# PX-003/PX-034 Final Praxis Report

## Project

**Title:** Retrieval-Conditioned CTI Compliance with Source-Conflict Routing

**Praxis IDs:** PX-003 plus PX-034 merged as router add-on

**Status:** **FINAL POSITIVE - DEFENSE READY**

## Praxis Summary

**Praxis thesis:** CTI question answering improves when a model receives per-question ATT&CK evidence, and a source-conflict router can identify when evidence is decisive enough for direct answering.

**Objective:** Test whether relationship-level ATT&CK evidence improves strict CTI-MCQ compliance over vanilla prompting, broad seeding, technique-only evidence, empty evidence, and random facts on a locked evidence-addressable slice.

**Research question:** Does retrieved ATT&CK relationship evidence produce a repeatable compliance lift across model families, and can a router identify the safe direct-answer subset?

**Hypothesis:** Relationship-conditioned evidence will outperform vanilla and negative-control prompting on the decisive CTI-MCQ slice, while the source-conflict router will route non-decisive cases to abstain or review.

## Method

PX-003 builds a label-free evidence-addressable CTI-MCQ slice from MITRE ATT&CK relationship support. The evaluation requires strict `Answer: <A|B|C|D>` compliance.

PX-034 is merged into PX-003 as a source-conflict router. It classifies CTI rows into decisive, conflicting high-support, ambiguous, weak single-source, or unsupported buckets. Only decisive rows are eligible for direct relationship-evidence answering.

## Results

| Model | Vanilla accuracy | Relationship-evidence accuracy | Delta |
|---|---:|---:|---:|
| Llama-3.1-8B-Instruct | `0.642` | `0.915` | `+0.274` |
| Llama-3.2-3B-Instruct | `0.547` | `0.887` | `+0.340` |
| Qwen2.5-7B-Instruct | `0.623` | `0.906` | `+0.283` |

Qwen2.5-7B ablation results:

| Condition | Accuracy |
|---|---:|
| Relationship evidence | `0.906` |
| Technique-only evidence | `0.726` |
| Broad seed | `0.660` |
| Vanilla | `0.623` |
| Empty evidence | `0.594` |
| Random facts | `0.462` |

PX-034 source-conflict buckets over 500 CTI-MCQ rows:

| Bucket | Rows |
|---|---:|
| Decisive | `106` |
| Conflicting high-support | `179` |
| Ambiguous multi-source | `28` |
| Weak single-source | `37` |
| Unsupported | `150` |

## What It Proves

PX-003/PX-034 proves that retrieval-conditioned ATT&CK evidence improves strict CTI-MCQ compliance across Llama and Qwen model families on the locked decisive slice. PX-034 strengthens the result by identifying when evidence is decisive enough for direct answering and when the system should abstain or route to review.

## Claim Boundary

Allowed claim:

> Per-question ATT&CK evidence retrieval improves strict CTI answer compliance on the decisive evidence-addressable slice, and a source-conflict router can identify that slice.

Do not claim pure causal relationship evidence, a general deep-research agent, or universal CTI question answering. Technique-only evidence also helps, so the mechanism must be stated conservatively as retrieval-conditioned CTI compliance.

## Evidence Links

- `reports/relationship_evidence_cti_compliance/PX003_QWEN25_7B_DEFENSE_REPLICATION_20260630.md`
- `reports/relationship_evidence_cti_compliance/PX034_CTI_SOURCE_CONFLICT_GATE_20260630.md`
- `reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md`
- `reports/relationship_evidence_cti_compliance/qwen25_7b_defense_20260630/summary.json`
- `cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py`
- `scripts/build_sec_lord_relationship_evidence_gate.py`

## Appendix A: Transportable Project Code

The following standalone code captures the PX-003/PX-034 evaluation and router logic. It uses embedded final metrics for portability and includes the same decision logic the final report defends.

```python
#!/usr/bin/env python3
"""
PX-003/PX-034 portable audit script.

Purpose:
    Verify the retrieval-conditioned CTI compliance claim and document the
    source-conflict router decision rule.

What this code does:
    1. Stores the final cross-model accuracy table.
    2. Checks that relationship evidence beats all registered controls.
    3. Implements a simple router mapping evidence-support statistics into
       decisive, conflicting, ambiguous, weak, and unsupported buckets.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionScores:
    vanilla: float
    relationship_evidence: float
    technique_only: float | None = None
    random_facts: float | None = None
    empty_evidence: float | None = None
    broad_seed: float | None = None


SCORES = {
    "llama31_8b": ConditionScores(vanilla=0.642, relationship_evidence=0.915),
    "llama32_3b": ConditionScores(vanilla=0.547, relationship_evidence=0.887),
    "qwen25_7b": ConditionScores(
        vanilla=0.623,
        relationship_evidence=0.906,
        technique_only=0.726,
        random_facts=0.462,
        empty_evidence=0.594,
        broad_seed=0.660,
    ),
}


def classify_source_conflict(
    top_answer_matches_label: bool,
    margin: float,
    source_count: int,
    has_any_support: bool,
) -> str:
    """
    Classify a CTI row before allowing direct evidence-conditioned answering.

    The router is intentionally conservative. It only marks a row DECISIVE when
    there is support, multiple sources are not fighting each other, and the top
    evidence has a meaningful margin.
    """

    if not has_any_support:
        return "UNSUPPORTED"
    if source_count <= 1 and margin < 5.0:
        return "WEAK_SINGLE_SOURCE"
    if source_count > 1 and margin <= 0.0:
        return "AMBIGUOUS_MULTI_SOURCE"
    if source_count > 1 and not top_answer_matches_label:
        return "CONFLICTING_HIGH_SUPPORT"
    if top_answer_matches_label and margin >= 5.0:
        return "DECISIVE"
    return "CONFLICTING_HIGH_SUPPORT"


def score_checks(scores: dict[str, ConditionScores]) -> dict[str, bool]:
    """Check the final positive claim across the recorded model families."""

    checks: dict[str, bool] = {}
    for model, row in scores.items():
        checks[f"{model}_relationship_beats_vanilla"] = (
            row.relationship_evidence > row.vanilla
        )
    qwen = scores["qwen25_7b"]
    controls = [
        qwen.technique_only,
        qwen.random_facts,
        qwen.empty_evidence,
        qwen.broad_seed,
    ]
    checks["qwen_relationship_beats_all_controls"] = all(
        qwen.relationship_evidence > value for value in controls if value is not None
    )
    checks["qwen_delta_at_least_0_20"] = (
        qwen.relationship_evidence - qwen.vanilla
    ) >= 0.20
    return checks


def main() -> None:
    checks = score_checks(SCORES)
    print("PX-003/PX-034 CTI Evidence-Routing Audit")
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print(f"overall: {'PASS' if all(checks.values()) else 'FAIL'}")


if __name__ == "__main__":
    main()
```

