# PX-011 Final Praxis Report

## Project

**Title:** Source-Locked HalluHard Verifier Pipeline

**Praxis ID:** PX-011

**Status:** **FINAL POSITIVE - BOUNDED SOURCE-LOCKED RESULT**

## Praxis Summary

**Praxis thesis:** A HalluHard-style hallucination guardrail can work when citation/source metadata are locked to retrieved evidence and the model is restricted to extractive claim generation.

**Objective:** Test whether a source-locked controller plus extractive model claim content can produce verifier-ready citation claims and detect shifted-source hallucinations on HalluHard research-question cases.

**Research question:** Can a retrieval/controller layer remove the freeform citation failure mode and leave the model responsible only for source-grounded claim extraction?

**Hypothesis:** If DOI, arXiv ID, title, year, and source identity are copied from retrieved source records, then the remaining extractive claim-generation task will pass source verification at a publishable rate and beat trivial baselines.

## Method

PX-011 uses the HalluHard `research_questions` lane only. The controller copies DOI, arXiv ID, title, year, and source identity from the retrieved source record. Qwen2.5-7B generates only a short extractive `claimed_content` phrase from the abstract.

The verifier evaluates both source-locked supported rows and shifted-source negative rows. This is important: shifted-source negatives test whether the verifier detects plausible content attached to the wrong source.

## Results

| Metric | Value |
|---|---:|
| Model | `Qwen/Qwen2.5-7B-Instruct` |
| HalluHard lane | `research_questions` only |
| Generations | `250` |
| Evaluation pairs | `500` |
| Extraction-valid rows | `250 / 250` |
| Extraction-valid rate | `1.0000` |
| Supported claims passing verifier | `202 / 250` |
| Supported rate | `0.8080` |
| Verifier accuracy | `0.9040` |
| Verifier macro F1 | `0.9031` |
| Always-supported macro F1 | `0.3333` |
| Field-presence macro F1 | `0.3333` |
| Wall time | `256.8` seconds |

## What It Proves

PX-011 proves that the viable HalluHard result is not freeform citation generation. The defensible positive is source-locked retrieval/control plus extractive claim generation. Under that boundary, the verifier cleanly separates supported source-locked rows from shifted-source negatives.

## Claim Boundary

Allowed claim:

> For HalluHard research-question cases, a source-locked retrieval/controller pipeline with extractive model-generated claim content can produce verifier-ready citation claims and detect shifted-source hallucinations.

Do not claim broad HalluHard coverage, legal/medical/coding lane success, freeform citation generation, open-ended source discovery, or that the model independently authored citation metadata.

## Evidence Links

- `reports/halluhard_source_verifier/PX011_SOURCE_LOCKED_CONSTRAINED_GATE_20260701.md`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.csv`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.jsonl`
- `cloud_jobs/halluhard_constrained_20260701/run_halluhard_constrained_gate.py`
- `cloud_jobs/halluhard_constrained_20260701/run_on_instance.sh`

## Appendix A: Transportable Project Code

The following standalone code captures the source-locked verifier logic. The full cloud runner calls Qwen2.5-7B for extractive claim text; this portable appendix focuses on the deterministic controller/verifier pattern that defines the positive result.

```python
#!/usr/bin/env python3
"""
PX-011 portable source-locked HalluHard verifier.

Purpose:
    Demonstrate the source-locked verification pattern behind the PX-011
    positive result.

What this code does:
    1. Creates source-locked claims by copying citation metadata from evidence.
    2. Verifies source identity, title/year, and content grounding.
    3. Creates a shifted-source negative to test hallucination detection.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    year: int
    doi: str
    arxiv_id: str
    abstract: str


@dataclass(frozen=True)
class Claim:
    source_id: str
    title: str
    year: int
    doi: str
    arxiv_id: str
    claimed_content: str


def source_locked_claim(source: SourceRecord, extracted_phrase: str) -> Claim:
    """
    Build a verifier-ready claim.

    The model supplies only extracted_phrase. The controller copies citation
    metadata from the source record, preventing freeform DOI/title invention.
    """

    return Claim(
        source_id=source.source_id,
        title=source.title,
        year=source.year,
        doi=source.doi,
        arxiv_id=source.arxiv_id,
        claimed_content=extracted_phrase.strip(),
    )


def similarity(left: str, right: str) -> float:
    """Lightweight text similarity used for title/content checks."""

    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def verify_claim(claim: Claim, source: SourceRecord) -> bool:
    """
    Check whether a claim is supported by the paired source.

    A claim passes only when source identity and year match, title similarity is
    high, and the generated content is grounded in the abstract.
    """

    source_id_match = claim.source_id == source.source_id
    year_match = claim.year == source.year
    title_match = similarity(claim.title, source.title) >= 0.90
    content_grounded = claim.claimed_content.lower() in source.abstract.lower()
    return source_id_match and year_match and title_match and content_grounded


def main() -> None:
    correct_source = SourceRecord(
        source_id="paper-001",
        title="Example Paper About Reliable Evidence",
        year=2026,
        doi="10.0000/example",
        arxiv_id="2601.00001",
        abstract="Reliable evidence pipelines separate source metadata from generated claim text.",
    )
    wrong_source = SourceRecord(
        source_id="paper-002",
        title="Different Paper About Another Topic",
        year=2025,
        doi="10.0000/other",
        arxiv_id="2501.00002",
        abstract="This source discusses an unrelated topic.",
    )

    claim = source_locked_claim(
        correct_source,
        "Reliable evidence pipelines separate source metadata from generated claim text.",
    )

    supported = verify_claim(claim, correct_source)
    shifted_negative = verify_claim(claim, wrong_source)
    print("PX-011 Source-Locked Verifier Demo")
    print("supported_pair:", "PASS" if supported else "FAIL")
    print("shifted_source_negative:", "PASS" if not shifted_negative else "FAIL")


if __name__ == "__main__":
    main()
```

