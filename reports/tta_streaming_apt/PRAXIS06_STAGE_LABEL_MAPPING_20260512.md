# Praxis 06 Stage Label Mapping

Generated: 2026-05-12

## Purpose

This appendix makes the stage-label contract explicit for the Praxis 06 TTA result. The main claim depends on per-stage behavior, especially Reconnaissance recovery and Data Exfiltration preservation, so the label mapping must be stable and inspectable.

## Source

The active mapping is defined in:

- `src/praxis/unraveled_v02.py`
- reused by `src/praxis/unraveled_v03.py`
- consumed by `scripts/run_tta_hybrid_gate_sweep.py`
- consumed by `scripts/run_tta_locked_final.py`

## Stage Index Mapping

| Integer label | Stage name | Role in Praxis 06 |
|---:|---|---|
| `0` | `Benign` | Majority non-attack class |
| `1` | `Reconnaissance` | Primary rare-stage recovery target |
| `2` | `Establish Foothold` | Attack stage |
| `3` | `Lateral Movement` | Attack stage |
| `4` | `Data Exfiltration` | High-consequence preservation target |

## Normalized Stage Names

| Raw normalized key | Integer label |
|---|---:|
| `benign` | `0` |
| `reconnaissance` | `1` |
| `establish foothold` | `2` |
| `lateral movement` | `3` |
| `data exfiltration` | `4` |

The active Praxis 06 benchmark excludes `Cover up`. The `unraveled_v02` loader raises an error if `include_cover_up` is enabled for this benchmark family.

## Split Support In Locked TTA Result

| Split | Benign | Reconnaissance | Establish Foothold | Lateral Movement | Data Exfiltration |
|---|---:|---:|---:|---:|---:|
| Train | `268,710` | `5,151` | `15,047` | `15,748` | `3,077` |
| Validation | `22,011` | `23,791` | `5,784` | `8,047` | `2,253` |
| Test | `47,888` | `5,852` | `6,287` | `3,650` | `2,192` |

## Why Reconnaissance And Data Exfiltration Are Highlighted

Reconnaissance is the principal rare-stage failure mode in the locked TTA result. The frozen model's Reconnaissance F1 is `0.0250`, and the locked selective TTA policy raises it to `0.5050`.

Data Exfiltration is treated as the preservation class because it is high-consequence. The locked policy is constrained so adaptation cannot rescue Reconnaissance by sacrificing Data Exfiltration. Mean Data Exfiltration F1 changes from `0.9157` to `0.9202`.

## Defense Note

The claim is only as broad as this mapping. Praxis 06 should not claim coverage of every ATT&CK tactic or every kill-chain phase. It evaluates a five-class local APT-stage mapping over the trusted Unraveled feature pipeline.
