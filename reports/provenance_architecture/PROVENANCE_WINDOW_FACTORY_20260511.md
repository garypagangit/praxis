# Provenance Window Factory

Generated: 2026-05-11

## Decision

Status: **ARCHITECTURE READY - LABELS OR LONGER STREAMS NEEDED**.

This is an architecture unlock, not a scientific result. It creates reusable chronological provenance windows and fixed-width feature tables that graph SSL, TGN, drift, stage-routing, watermarking, and detector-zoo experiments can share.

## Artifacts

| Artifact | Path |
|---|---|
| windows | `runs\provenance-window-factory-20260511\windows.csv` |
| features | `runs\provenance-window-factory-20260511\window_features.csv` |
| labels_template | `runs\provenance-window-factory-20260511\labels_template.csv` |
| manifest | `runs\provenance-window-factory-20260511\manifest.json` |

## Corpus Summary

| Metric | Value |
|---|---:|
| Edge rows | 98862 |
| Windows | 20 |
| Labeled windows | 0 |
| Source files | 1 |
| Timestamp span seconds | 245.329 |
| Event vocabulary size | 29 |
| Exec vocabulary size | 32 |

## Experiments This Opens

| Experiment | What this provides | Still missing for a defensible claim |
|---|---|---|
| Concept drift on provenance detectors | Chronological windows and drift-ready feature tables | Longer host streams plus labels/anomaly spans |
| Continuous-time TGN | Sorted temporal windows and node/event vocabulary | Supervised anomaly target or self-supervised objective better than next-event type |
| Contrastive SSL on provenance graphs | Shared window boundaries and feature vocabulary | Better node features and hard-negative policy |
| Stage routing on provenance graphs | Common temporal windows for graph-stage prediction | Stage labels or reliable attack-window mapping |
| Watermarking / MIA / adversarial robustness | Detector-zoo compatible window features | Stable detector suite and non-proxy labels |

## Honest Limitation

The current Cadets sample can validate plumbing, but it does not by itself prove drift, graph-stage prediction, or detector robustness. For that we need longer streams and labels.
