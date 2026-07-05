# PX-003/PX-034 Full-Bucket Downstream Accuracy Audit

Status: **PASS FOR FULL-BUCKET RELATIONSHIP-EVIDENCE LIFT; ROUTER CLAIM NARROWED**

## Purpose

This audit implements the reviewer recommendation to test whether the PX-034 source-conflict buckets predict downstream CTI answerability when a model is forced to answer. It joins model predictions to the 500-row source-conflict router table and reports accuracy by bucket.

## Headline

- Relationship-evidence minus vanilla delta, all evaluated rows: `0.2080`.
- Relationship-evidence minus vanilla delta on DECISIVE rows: `0.2830`.
- Predictions without a bucket join: `0`.
- Relationship evidence improved accuracy in every PX-034 source-conflict bucket.
- The buckets do **not** support a simple "DECISIVE rows are the only answerable rows" claim. `WEAK_SINGLE_SOURCE` scored highest under relationship evidence at `0.9189`, and `CONFLICTING_HIGH_SUPPORT` still reached `0.8101`.

## Per-Condition Bucket Accuracy

### `relationship_evidence`

Overall accuracy: `0.8220` over `500` rows; invalid rate `0.0000`.

| Bucket | Rows | Accuracy | Correct | Invalid rate |
|---|---:|---:|---:|---:|
| `AMBIGUOUS_MULTI_SOURCE` | `28` | `0.7143` | `20` | `0.0000` |
| `CONFLICTING_HIGH_SUPPORT` | `179` | `0.8101` | `145` | `0.0000` |
| `DECISIVE` | `106` | `0.9057` | `96` | `0.0000` |
| `UNSUPPORTED` | `150` | `0.7733` | `116` | `0.0000` |
| `WEAK_SINGLE_SOURCE` | `37` | `0.9189` | `34` | `0.0000` |

### `vanilla`

Overall accuracy: `0.6140` over `500` rows; invalid rate `0.0000`.

| Bucket | Rows | Accuracy | Correct | Invalid rate |
|---|---:|---:|---:|---:|
| `AMBIGUOUS_MULTI_SOURCE` | `28` | `0.5357` | `15` | `0.0000` |
| `CONFLICTING_HIGH_SUPPORT` | `179` | `0.5307` | `95` | `0.0000` |
| `DECISIVE` | `106` | `0.6226` | `66` | `0.0000` |
| `UNSUPPORTED` | `150` | `0.6933` | `104` | `0.0000` |
| `WEAK_SINGLE_SOURCE` | `37` | `0.7297` | `27` | `0.0000` |

## Interpretation

The reviewer recommendation produced a useful narrowing result.

What strengthened:

- PX-003 is stronger as a full-dataset retrieval-conditioned CTI result: Qwen2.5-7B improved from `0.6140` vanilla to `0.8220` with relationship evidence over all `500` rows.
- The decisive slice still shows the largest clean delta among the original defense slice: `0.6226` to `0.9057`.
- The run has `0` invalid outputs and `0` bucket-join misses.

What narrowed:

- PX-034 should not be described as a complete answerability router. Strong forced-answer performance appears outside `DECISIVE`, especially `WEAK_SINGLE_SOURCE` and `CONFLICTING_HIGH_SUPPORT`.
- The safer claim is that PX-034 is a source-support and conflict taxonomy that identifies a high-confidence evidence slice, not a proof that non-decisive rows are unanswerable.

Updated defense wording:

> Relationship evidence improves CTI-MCQ performance across the full 500-row source-conflict table, while PX-034 identifies the high-confidence decisive evidence slice used for the strongest original defense replication. The source-conflict router should be presented as evidence-risk stratification, not as a hard answerability oracle.
