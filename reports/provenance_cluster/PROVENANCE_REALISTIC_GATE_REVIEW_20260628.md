# PX-012/PX-013/PX-014 Provenance Realistic Gate Review

Generated: 2026-06-28

Status: **MIXED CLUSTER - TWO FAILED, ONE DATA-BLOCKED**

## Scope

This review closes the realistically testable provenance cluster without spending GPU on weak or under-labeled setups. It reads the existing Cadets SSL, TGN, and concept-drift gates and applies promotion criteria that would justify another experiment.

## Decisions

| ID | Experiment | Decision | Evidence |
|---|---|---|---|
| PX-012 | Contrastive SSL for Provenance Graph Windows | `FAILED_CURRENT_CYCLE` | Positive > negative rate is only `0.5227`; not enough for GPU GraphCL. |
| PX-013 | Continuous-Time TGN for APT Provenance Streams | `FAILED_CURRENT_CYCLE` | Logistic temporal/hash features Macro-F1 `0.5972` underperform the previous-event transition baseline `0.6044`. |
| PX-014 | Concept Drift on Provenance Detectors | `DATA_BLOCKED_ARCHITECTURE_ONLY` | Parser/windowing works on `98,862` rows, but the sample has one source file, `245.329` seconds of span, and no honest attack/anomaly labels. |

## Promotion Checks

| Check | PX-012 | PX-013 | PX-014 |
|---|---:|---:|---:|
| Beats cheap baseline or clears minimum separation | `False` | `False` | `False` |
| Has enough labeled or long-horizon data for a publishable claim | `False` | `False` | `False` |
| Worth GPU follow-on now | `False` | `False` | `False` |
| Keep as reusable pipeline evidence | `True` | `True` | `True` |

## Interpretation

PX-012 and PX-013 should be archived for the dissertation cycle. They are not useless code, but they do not justify more training: the SSL representation signal barely separates positives from negatives, and the TGN-style temporal model does not beat a simple transition baseline.

PX-014 should not be called a failed detector result because it did not have a real drift benchmark. It is a working parser/windowing artifact and a data-readiness blocker: a proper drift experiment needs longer host streams, labels or anomaly windows, and a detector family.

## Dashboard Action

- Mark PX-012 as a failed weak gate.
- Mark PX-013 as a failed weak gate.
- Keep PX-014 as data-blocked architecture evidence, not a positive result.

## Evidence

- PX-012 report: `reports/contrastive_ssl_provenance_graphs/CADETS_SSL_REPRESENTATION_PILOT_20260509.md`
- PX-012 summary: `runs/cadets-ssl-representation-pilot-20260509/summary.json`
- PX-013 report: `reports/continuous_time_tgn_apt_provenance/CADETS_TGN_NEXT_EVENT_PILOT_20260509.md`
- PX-013 summary: `runs/cadets-tgn-next-event-pilot-20260509/summary.json`
- PX-014 report: `reports/concept_drift_provenance_detectors/CADETS_DRIFT_GATE_20260510.md`
- PX-014 summary: `runs/cadets-concept-drift-gate-20260510/summary.json`
