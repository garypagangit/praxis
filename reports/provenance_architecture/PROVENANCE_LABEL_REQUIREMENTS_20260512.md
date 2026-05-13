# Provenance Label Requirements

Generated: 2026-05-12

## Decision

The provenance architecture is ready for real labels, but it should not produce supervised detector claims from PIDSMaker node-touch labels alone.

The full E5 Cadets window factory scaled successfully, but the detector gate blocked honestly because node-touch labels marked nearly every window as attack-touch: `9,609` attack-touch windows versus only `2` benign-or-unlabeled windows. That is not a usable supervised split.

## Required Label Manifest

Use interval labels when possible. The window factory already accepts CSV, JSON, or JSONL with these required fields:

| Column | Meaning | Example |
|---|---|---|
| `start_ns` | Inclusive interval start in nanoseconds | `1523020012345678900` |
| `end_ns` | Inclusive interval end in nanoseconds | `1523020312345678900` |
| `label` | Stage, attack, anomaly, or benign label | `reconnaissance` |

Accepted aliases already supported by the loader:

| Alias | Normalized column |
|---|---|
| `start` | `start_ns` |
| `end` | `end_ns` |
| `start_timestamp_nanos` | `start_ns` |
| `end_timestamp_nanos` | `end_ns` |
| `name` | `label` |

## Minimum Gate Before Detector Claims

Do not train or publish supervised provenance detectors until a window table passes all of these checks:

| Check | Minimum |
|---|---|
| At least two real classes | Required |
| Benign windows | `>= 20` |
| Attack/anomaly windows | `>= 20` |
| Stage-specific class used in a claim | `>= 20` windows for that stage |
| Chronological split support | Each train/validation/test split must contain the claimed positive class |
| Label source | Must be interval truth, confirmed benign spans, or a trusted release annotation; node-touch alone is not enough |

## What PIDSMaker Node Labels Can Still Do

| Use | Allowed? | Reason |
|---|---|---|
| Prioritize windows for inspection | Yes | High node-touch density can identify interesting regions |
| Weak-proxy density diagnostics | Yes | Clearly marked as non-ground-truth |
| Supervised benign-vs-attack detector claims | No | Nearly all windows touch labeled nodes |
| Stage-routing claims | No | Node labels are not stage intervals |

## Tests Added

`tests/test_provenance_window_factory.py` now includes an interval-label regression test. This confirms that real `start_ns,end_ns,label` manifests are attached to chronological windows and counted in the manifest.

## Practical Next Step

The next unlock is not more modeling. It is one of:

1. Obtain Cadets attack/benign interval spans from source truth.
2. Build a manually audited interval manifest for a small but defensible subset.
3. Switch to another host stream with usable interval labels.
4. Keep using the current full Cadets windows only for unsupervised representation stress tests and weak-proxy diagnostics.
