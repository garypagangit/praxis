# Provenance Window Factory

Generated: 2026-05-11

## Decision

Status: **SUPERVISED WINDOW FACTORY READY**.

This is an architecture unlock, not a scientific result. It creates reusable chronological provenance windows and fixed-width feature tables that graph SSL, TGN, drift, stage-routing, watermarking, and detector-zoo experiments can share.

## Artifacts

| Artifact | Path |
|---|---|
| windows | `runs\provenance-window-factory-20260511-e5cadets-pidsmaker\windows.csv` |
| features | `runs\provenance-window-factory-20260511-e5cadets-pidsmaker\window_features.csv` |
| labels_template | `runs\provenance-window-factory-20260511-e5cadets-pidsmaker\labels_template.csv` |
| manifest | `runs\provenance-window-factory-20260511-e5cadets-pidsmaker\manifest.json` |

## Corpus Summary

| Metric | Value |
|---|---:|
| Edge rows | 98862 |
| Windows | 20 |
| Labeled windows | 19 |
| Node-label rows | 126 |
| Node-labeled windows | 19 |
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
