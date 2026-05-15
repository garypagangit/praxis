# SEC-LoRD Retrieved-Evidence Gate Readiness

Generated: 2026-05-14

Status: **ready for cheap model gate; still no extraction claim**

## Bottom Line

The failed broad domain-seeding method is now converted into a concrete retrieved-evidence prompt gate. This closes the design ambiguity: the next SEC-LoRD step is a strict three-way prompt comparison, not LoRD-style extraction.

## Generated Artifacts

- Prompt JSONL: `runs\sec-lord-retrieved-evidence-gate-20260514\retrieved_evidence_prompts.jsonl`
- Summary JSON: `runs\sec-lord-retrieved-evidence-gate-20260514\summary.json`

## Gate Input Summary

| Item | Value |
|---|---:|
| CTI-MCQ rows | `500` |
| Rows with exact ATT&CK technique fact | `500` |
| Rows with evidence snippets | `500` |
| Evidence coverage | `1.000` |

## Prompt Conditions

| Condition | Purpose |
|---|---|
| `vanilla_strict_prompt` | Strong plain baseline with exact `Answer: <A|B|C|D>` output requirement. |
| `broad_seed_negative_control_prompt` | Keeps the failed domain-stuffing strategy visible as a negative control. |
| `retrieved_evidence_prompt` | Uses 1-3 question-specific ATT&CK facts in a separate Evidence block. |

## Pass Gate

- Retrieved-evidence strict accuracy must beat vanilla by at least `+0.030` absolute.
- Retrieved-evidence invalid response rate must be no worse than vanilla.
- Evidence-only paired wins must exceed vanilla-only paired wins.
- Broad seed negative control remains reported and cannot be hidden.

## Decision

SEC-LoRD remains negative for the old method. It is now **gate-ready** for one cheap strict prompt evaluation. No extraction experiment should run until this gate passes.
