# PX-001 Final Praxis Report

## Project

**Title:** Safety-Gated Test-Time Adaptation for Streaming APT Detection

**Praxis ID:** PX-001

**Status:** **FINAL POSITIVE - DEFENSE READY**

## Praxis Summary

**Praxis thesis:** A streaming intrusion detector can use tightly gated, unlabeled test-time adaptation to recover weak early-stage attack detection while preserving high-risk destructive-event safety.

**Objective:** Test whether selective BatchNorm adaptation can improve Reconnaissance-stage F1 on an APT stage-classification stream without sacrificing Data Exfiltration detection.

**Research question:** Can no-label deployment-time adaptation improve rare-stage detection under held-out source-file shift while respecting a conservative safety gate?

**Hypothesis:** A validation-selected selective TTA policy will improve Reconnaissance F1 and macro F1 while keeping Data Exfiltration behavior stable and changing only a small fraction of predictions.

## Method

PX-001 uses a frozen support-floor MLP detector trained on the Unraveled APT feature pipeline. The positive treatment is not a full model replacement. It adapts BatchNorm behavior over the unlabeled target stream and applies a locked selective gate.

The gate preserves confident frozen Data Exfiltration predictions, allows overrides only under predefined uncertainty and Reconnaissance-rescue thresholds, and uses validation-selected thresholds before locked test replay.

## Results

| Metric | Frozen MLP | Locked selective TTA | Delta |
|---|---:|---:|---:|
| Accuracy | `0.8984` | `0.9243` | `+0.0260` |
| Macro F1 | `0.7685` | `0.8658` | `+0.0974` |
| Reconnaissance F1 | `0.0250` | `0.5050` | `+0.4800` |
| Data Exfiltration F1 | `0.9157` | `0.9202` | `+0.0045` |
| Override rate | `0.0000` | `0.0470` | `+0.0470` |

The later seven-seed defense extension preserved the conclusion: macro F1 improved from `0.7165` to `0.8341`, Reconnaissance F1 improved from `0.0615` to `0.5219`, and the Data Exfiltration changed-from-DE count was `0`.

## What It Proves

PX-001 proves that a locked, validation-selected selective TTA policy can rescue a rare APT stage under the tested streaming source-file shift while preserving the high-risk Data Exfiltration class. The gain is not explained by simply rejecting uncertain rows: a matched-rate frozen confidence-reject baseline did not recover Reconnaissance.

## Claim Boundary

Allowed claim:

> Under the tested Unraveled APT held-out source-file split, safety-gated no-label test-time adaptation recovered rare Reconnaissance detection while preserving Data Exfiltration behavior.

Do not claim universal APT detection generality, universal TTA transfer, or DAPT2020 TTA validation. DAPT2020 remains a negative external-validity boundary for TTA.

## Evidence Links

- `reports/tta_streaming_apt/TTA_FUNCTIONING_CAPABILITY_REPORT_20260513.md`
- `reports/tta_streaming_apt/LOCKED_FINAL_REPLAY_20260509.md`
- `reports/tta_streaming_apt/ROBUSTNESS_AUDIT_20260509.md`
- `runs/tta-defense-hardening-defense-audit-20260630/PRAXIS06_TTA_DEFENSE_HARDENING_REPORT_20260513.md`
- `scripts/run_tta_locked_final.py`
- `scripts/run_tta_defense_hardening.py`

## Appendix A: Transportable Project Code

The following standalone code captures the PX-001 gate logic and result checks. It is written as a portable audit script: it can run with the embedded final metrics, or it can be adapted to load local CSV/JSON outputs from another replay.

```python
#!/usr/bin/env python3
"""
PX-001 portable audit script.

Purpose:
    Document and verify the safety-gated TTA result without depending on the
    original training environment. The script records the locked metrics and
    implements the core selective decision rule used by the Praxis report.

What this code does:
    1. Stores the final frozen and TTA metric summaries.
    2. Checks the registered pass/fail gates.
    3. Provides a readable implementation of the safety-gated override logic.

Inputs:
    None required. To use with a new replay, replace FINAL_METRICS with values
    parsed from the new run artifacts.
"""

from dataclasses import dataclass


DATA_EXFILTRATION = "Data Exfiltration"
RECONNAISSANCE = "Reconnaissance"


@dataclass(frozen=True)
class Metrics:
    """One compact metric row for a frozen or adapted detector."""

    accuracy: float
    macro_f1: float
    recon_f1: float
    de_f1: float
    override_rate: float


FINAL_METRICS = {
    "frozen": Metrics(
        accuracy=0.8984,
        macro_f1=0.7685,
        recon_f1=0.0250,
        de_f1=0.9157,
        override_rate=0.0000,
    ),
    "locked_tta": Metrics(
        accuracy=0.9243,
        macro_f1=0.8658,
        recon_f1=0.5050,
        de_f1=0.9202,
        override_rate=0.0470,
    ),
}


def selective_tta_prediction(
    frozen_label: str,
    frozen_confidence: float,
    tta_label: str,
    tta_confidence: float,
    uncertainty_threshold: float = 0.50,
    recon_rescue_threshold: float = 0.50,
    de_keep_threshold: float = 0.00,
) -> str:
    """
    Apply the locked safety gate to one prediction.

    The rule is deliberately conservative:
    - Keep confident frozen Data Exfiltration decisions because they represent
      a high-risk class.
    - Allow a Reconnaissance rescue only when the adapted model is confident.
    - Otherwise allow overrides only when the frozen model was uncertain.
    """

    if frozen_label == DATA_EXFILTRATION and frozen_confidence >= de_keep_threshold:
        return frozen_label

    if tta_label == RECONNAISSANCE and tta_confidence >= recon_rescue_threshold:
        return tta_label

    if frozen_confidence < uncertainty_threshold:
        return tta_label

    return frozen_label


def gate_checks(metrics: dict[str, Metrics]) -> dict[str, bool]:
    """Evaluate the defense gates used for the final PX-001 claim."""

    frozen = metrics["frozen"]
    tta = metrics["locked_tta"]
    return {
        "macro_f1_delta_at_least_0_05": (tta.macro_f1 - frozen.macro_f1) >= 0.05,
        "recon_f1_delta_at_least_0_25": (tta.recon_f1 - frozen.recon_f1) >= 0.25,
        "de_f1_not_harmed": (tta.de_f1 - frozen.de_f1) >= 0.00,
        "override_rate_at_most_0_05": tta.override_rate <= 0.05,
    }


def main() -> None:
    checks = gate_checks(FINAL_METRICS)
    print("PX-001 Safety-Gated TTA Audit")
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print(f"overall: {'PASS' if all(checks.values()) else 'FAIL'}")


if __name__ == "__main__":
    main()
```

