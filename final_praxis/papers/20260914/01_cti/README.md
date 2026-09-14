# CTI paper and reproducible evidence

Read the completed paper in [Markdown](PAPER.md), [PDF](PAPER.pdf), or [Word](PAPER.docx), beginning with its plain-English executive summary. The finding is substantial benefit from compatible relationship evidence, substantial harm from mismatched automatic retrieval, and a failed external router. The paper does not claim a successful new defense. PX-071 has no completed efficacy result in this package. The final 20-page document passed [visual review](VISUAL_QA.json).

## Included evidence

| Artifact | Contents and role |
|---|---|
| [Full CTIBench analysis](evidence/FULL_2500_ANALYSIS.json) | All 2,500 questions, both fixed strata, six source-known conditions and two query-only conditions, two models, gates and intervals |
| [CTIBench data](data/) | Four compressed files preserving exact original prediction bytes: 15,000 source-known plus 5,000 query-only rows per model |
| [Primary protocol](protocol/FULL_2500_PREREGISTRATION.md) | Original internal prospective rules; its historical “strict” parser wording is corrected in the new paper, without changing the artifact |
| [Frozen analysis code](frozen/scripts/) | Exact historical statistical implementations |
| [Frozen builders](frozen/builders/) | Exact evidence construction, router training, and Athena preparation code; provided for inspection, not automatically executed |
| [External analysis](evidence/PX068_ANALYSIS.json) | PX-068 failed router evaluation on 2,997 primary questions |
| `data/px068_*_derived.jsonl.gz` | 11,988 derived policy rows per model, without restricted Athena question text or answer labels |
| [External terminal audit](evidence/PX068_TERMINAL_AUDIT.json) | Archived completeness, source-hash and decision-rule checks |
| [Exposure sensitivity](evidence/EXPOSED_ITEM_SENSITIVITY.json) | Post hoc exclusion of 500 previously used CTIBench IDs; not a new confirmatory holdout |
| [Study status](evidence/STUDY_STATUS.json) | Primary source-known-only confirmation; failed PX-068; no completed PX-071 scientific result |
| [Provenance](PROVENANCE.json) | Exact copies, source Git commit and hashes, compressed-byte hashes and Athena projection transformations |
| [Source terms](licenses/SOURCES_AND_LICENSES.md) | Data attribution and artifact-specific redistribution limits |

The historical code is pinned to source commit `720d9e76a6142aae95ad1c31153d9ac38499fbb0`. Original report paths and prospective status labels inside frozen documents are historical provenance, not dependencies or current terminal decisions. The [release manifest](MANIFEST.json) covers the complete delivered package except the manifest itself and transient Python caches. Run `python verify_release.py` to verify its file hashes.

## Reproduce the results without models or cloud access

Use Python 3.10 or later. Only the Python standard library is required for statistical reproduction; model weights, GPU libraries, credentials, internet access and original local report folders are unnecessary. Run from this directory:

```text
python reproduce.py --bootstrap none --output reproduction_output
```

This quick mode verifies packaged source hashes, all 40,000 CTIBench raw-to-parser outcomes, all Athena derived policy assignments, all arm counts, Wilson intervals, paired cells, exact McNemar tests, Holm adjustments, and gate arithmetic. It explicitly uses the archived paired-bootstrap intervals as numerical inputs. Its receipt does not claim those intervals were independently regenerated.

For a complete deterministic rerun of all 156 paired-bootstrap intervals:

```text
python reproduce.py --bootstrap all --output reproduction_full
```

This uses the frozen standard-library random generator and all 20,000 resamples per interval. It can take tens of minutes on a CPU. A smaller option regenerates the 14 principal intervals: the eligible source-known vanilla/technique contrasts, both query strata, and the three registered external superiority/harm comparisons for each model.

```text
python reproduce.py --bootstrap primary --output reproduction_primary
python -m unittest test_reproduce.py
```

All modes write `REPRODUCTION_RECEIPT.json`, reconstructed full CTIBench and PX-068 reports, and an explicitly separate PX-068 intended-A–E validity diagnostic. A mismatch exits with a nonzero status. A PASS means the stated checks reproduced the archived observations. It does not certify that a scientific hypothesis passed, that benchmark labels are error-free, or that model inference has been independently replicated.

The [quick reproduction receipt](evidence/reproduced_counts/REPRODUCTION_RECEIPT.json) and [completed full-bootstrap receipt](evidence/reproduced_full/REPRODUCTION_RECEIPT.json) both pass. The full run regenerated all 156 intervals, used no archived interval as an input, and matched both complete statistical payloads exactly in 888.48 seconds with Python 3.11.9. The quick pass verifies all 31 final source/provenance artifacts; the full run began with the original 25, before six additional historical inspection/license files were added. All analyzed data and executable analysis files are unchanged. The source-code hash and counts bind the claimed reproduction. An [independent package review](evidence/INDEPENDENT_PACKAGE_REVIEW.json) verifies the manuscript tables, actual input inventory, seed coverage, and source-hash agreement. Public package checks are distinct from the [historical integrity audit](evidence/FULL_2500_HISTORICAL_INTEGRITY.md) and [historical separate rerun](evidence/FULL_2500_HISTORICAL_REPRODUCTION.md).

## Interpretation and data boundaries

There are 2,500 CTIBench question units, not 40,000 independent samples. The latter count contains model/condition repeats and 5,000 repeated vanilla cells. Athena has 2,997 primary question units; its four policy rows per question are selected from two underlying model outputs. The oracle policy is diagnostic and is not a deployable algorithm.

CTIBench raw predictions permit local verification of parser behavior and released-label correctness. Athena correctness is supplied as a derived indicator from the authenticated original analysis. The public command can verify arithmetic and policy selection from those indicators but cannot independently reconstruct Athena correctness from raw text that is not redistributed. To inspect the complete external source, obtain it directly from the pinned repository under its license. No model calls are required to audit the included statistics.

The frozen Athena summary has a disclosed A–E validity defect. To reproduce that legacy summary faithfully, the driver uses internal sentinel values encoding the already observed `legacy_valid` Boolean; these are not reconstructed answer labels. The explicit `correct` field supplies correctness. The separate `intended_ae_valid` field supports the corrected validity diagnostic. See [Incident 03](evidence/PX068_INCIDENT_03.md) and [Incident 04](evidence/PX068_INCIDENT_04.md). Neither is silently repaired into a scientific success.

Source model licenses and hardware requirements apply to any new inference. This package does not distribute weights or promise identical GPU generation across software environments. Assembly and statistical reproduction of this release made zero new inference or cloud calls.
