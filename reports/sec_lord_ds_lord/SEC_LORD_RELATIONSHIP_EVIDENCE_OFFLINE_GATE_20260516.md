# SEC-LoRD Relationship-Evidence Offline Gate

Generated: 2026-05-16

Status: **offline support audit complete; model gate still required**

## Bottom Line

The relationship-evidence prompt set was run as far as the local environment allows. This machine can rescore the evidence-addressable slice and old Llama outputs, but it cannot execute the actual relationship-evidence model comparison locally.

Local model-run blocker observed by this script: `transformers` is not installed; CUDA is not available.

The offline result is still useful: the label-blind evidence pointer is strong on the 106-row addressable slice, and it leaves enough signal to justify exactly one cheap model/API batch. It is not a SEC-LoRD pass claim.

## Inputs

- Prompt slice: `runs\sec-lord-relationship-evidence-gate-20260516\evidence_addressable_prompts.jsonl`
- Summary JSON: `runs\sec-lord-relationship-evidence-offline-gate-20260516\summary.json`

## Offline Scorecard

| Condition | Rows | Strict correct | Strict accuracy | Invalid |
|---|---:|---:|---:|---:|
| Evidence pointer audit | `106` | `86` | `0.811` | `0` |
| Llama-3.2-3B-Instruct vanilla | `106` | `33` | `0.311` | `50` |
| Llama-3.2-3B-Instruct broad seed | `106` | `9` | `0.085` | `95` |
| Llama-3.1-8B-Instruct vanilla | `106` | `57` | `0.538` | `16` |
| Llama-3.1-8B-Instruct broad seed | `106` | `26` | `0.245` | `57` |

## Paired Pointer Checks

| Baseline | Pointer-only wins | Baseline-only wins | Both correct | Both wrong |
|---|---:|---:|---:|---:|
| Llama-3.2-3B-Instruct vanilla | `62` | `9` | `24` | `11` |
| Llama-3.2-3B-Instruct broad_seed | `79` | `2` | `7` | `18` |
| Llama-3.1-8B-Instruct vanilla | `42` | `13` | `44` | `7` |
| Llama-3.1-8B-Instruct broad_seed | `66` | `6` | `20` | `14` |

## Decision

SEC-LoRD is not promoted from this offline run. The old broad-seed method remains negative. The relationship-evidence rescue path remains alive only as a model gate: run vanilla vs relationship evidence vs broad-seed negative control on the 106 addressable rows, then apply the strict pass criteria.

Required model-gate criteria remain:

- Relationship-evidence strict accuracy beats vanilla by at least `+0.030` absolute.
- Relationship-evidence invalid rate is no worse than vanilla.
- Relationship-evidence-only paired wins exceed vanilla-only paired wins.
- No extraction experiment runs unless those criteria pass.

## Next Command

```powershell
.\.venv-diag\Scripts\python.exe .\scripts\build_sec_lord_relationship_evidence_gate.py
# Then run the model/API batch over:
# runs\sec-lord-relationship-evidence-gate-20260516\evidence_addressable_prompts.jsonl
```
