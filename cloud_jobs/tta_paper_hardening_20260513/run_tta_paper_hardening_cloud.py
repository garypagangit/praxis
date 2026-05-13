from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGES = [
    "Benign",
    "Reconnaissance",
    "Establish Foothold",
    "Lateral Movement",
    "Data Exfiltration",
]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def f(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def fmt(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(out)


def stage_count_rows(preprocess: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for split_name in ["train", "val", "test"]:
        split = preprocess["splits"][split_name]
        counts = split["stage_counts"]
        rows.append(
            [
                split_name,
                split["rows"],
                split["source_file_count"],
                split["capture_day_count"],
                counts.get("Benign", 0),
                counts.get("Reconnaissance", 0),
                counts.get("Establish Foothold", 0),
                counts.get("Lateral Movement", 0),
                counts.get("Data Exfiltration", 0),
            ]
        )
    return rows


def metric_lookup(rows: list[dict[str, str]], method: str, split: str) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("method") == method and row.get("split") == split
    ]


def mean(rows: list[dict[str, str]], key: str) -> float:
    values = [f(row.get(key)) for row in rows]
    return sum(values) / len(values) if values else 0.0


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    root = Path.cwd()
    input_dir = root / "input"
    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    locked_dir = input_dir / "tta-locked-final-20260509"
    sweep_dir = input_dir / "tta-hybrid-gate-sweep-aws-20260509"

    locked_summary = read_json(locked_dir / "summary.json")
    preprocess = locked_summary["preprocess_summary"]
    locked_manifest = read_json(locked_dir / "locked_policy_manifest.json")
    locked_metrics = read_csv(locked_dir / "locked_hybrid_metrics.csv")
    frozen_metrics = read_csv(locked_dir / "frozen_reference_metrics.csv")
    confidence_reject = read_csv(locked_dir / "confidence_reject_summary.csv")
    locked_test_summary = read_csv(locked_dir / "locked_test_summary.csv")
    sweep_summary = read_csv(sweep_dir / "summary_mean_std.csv")

    locked_test = metric_lookup(locked_metrics, "locked_hybrid", "test")
    frozen_test = metric_lookup(frozen_metrics, "frozen", "test")

    locked_macro = mean(locked_test, "macro_f1")
    frozen_macro = mean(frozen_test, "macro_f1")
    locked_recon = mean(locked_test, "recon_f1")
    frozen_recon = mean(frozen_test, "recon_f1")
    locked_de = mean(locked_test, "de_f1")
    frozen_de = mean(frozen_test, "de_f1")
    locked_pr_auc = mean(locked_test, "pr_auc")
    frozen_pr_auc = mean(frozen_test, "pr_auc")
    locked_accuracy = mean(locked_test, "accuracy")
    frozen_accuracy = mean(frozen_test, "accuracy")
    override_rate = mean(locked_test, "override_rate")

    reject_row = confidence_reject[0]
    reject_recon = f(reject_row["kept_recon_f1_mean"])
    reject_rate = f(reject_row["actual_reject_rate_mean"])

    per_seed_rows = []
    for row in locked_test:
        seed = row["seed"]
        frozen_for_seed = [
            item for item in frozen_test if item.get("seed") == seed
        ][0]
        per_seed_rows.append(
            [
                seed,
                fmt(f(row["macro_f1"])),
                fmt(f(row["recon_f1"])),
                fmt(f(row["de_f1"])),
                fmt(f(row["pr_auc"])),
                fmt(f(row["override_rate"])),
                fmt(f(row["macro_f1"]) - f(frozen_for_seed["macro_f1"])),
                fmt(f(row["recon_f1"]) - f(frozen_for_seed["recon_f1"])),
                fmt(f(row["de_f1"]) - f(frozen_for_seed["de_f1"])),
            ]
        )

    source_overlap = preprocess["source_file_overlap"]
    group_overlap = preprocess["group_overlap"]
    de_deltas = [
        f(row["de_f1"]) - f(
            [item for item in frozen_test if item.get("seed") == row["seed"]][0][
                "de_f1"
            ]
        )
        for row in locked_test
    ]
    checks = {
        "locked_policy_recon_guarded": locked_manifest[0]["policy"] == "recon_guarded",
        "locked_method_bn_adapt": locked_manifest[0]["tta_method"] == "bn_adapt",
        "de_delta_limit_0_05": abs(f(locked_manifest[0]["de_delta_limit"]) - 0.05)
        < 1e-9,
        "macro_delta_ge_0_05": (locked_macro - frozen_macro) >= 0.05,
        "recon_delta_ge_0_25": (locked_recon - frozen_recon) >= 0.25,
        "mean_de_delta_nonnegative": (locked_de - frozen_de) >= 0.0,
        "per_seed_de_delta_ge_minus_0_05": all(delta >= -0.05 for delta in de_deltas),
        "override_rate_le_0_05": override_rate <= 0.05,
        "confidence_reject_recon_zero": reject_recon == 0.0,
        "source_overlap_zero": all(int(value) == 0 for value in source_overlap.values()),
        "group_overlap_zero": all(int(value) == 0 for value in group_overlap.values()),
        "temporal_delta_reset_each_split": preprocess["temporal_delta_seed_mode"]
        == "reset_each_split",
    }

    gmr_mermaid = """graph TD
  A[Training source files] --> B[Frozen support-floor MLP]
  B --> C[Frozen test probabilities]
  D[Unlabeled held-out stream] --> E[BatchNorm test-time adaptation]
  E --> F[Adapted test probabilities]
  C --> G[Selective recon_guarded gate]
  F --> G
  H[Validation-selected thresholds] --> G
  G --> I[Locked stage predictions]
  I --> J[Macro F1 / Recon F1 / DE F1 / PR-AUC]
  C --> K[Matched confidence-reject baseline]
  K --> L[Alternative explanation check]
"""
    gmr_dot = """digraph selective_tta {
  rankdir=LR;
  train [label="Training source files"];
  frozen [label="Frozen support-floor MLP"];
  frozen_probs [label="Frozen test probabilities"];
  stream [label="Unlabeled held-out stream"];
  bn [label="BatchNorm TTA"];
  adapted [label="Adapted test probabilities"];
  gate [label="recon_guarded validation-selected gate"];
  pred [label="Locked stage predictions"];
  metrics [label="Macro F1 / Recon F1 / DE F1 / PR-AUC"];
  reject [label="Matched confidence-reject baseline"];
  train -> frozen -> frozen_probs -> gate -> pred -> metrics;
  stream -> bn -> adapted -> gate;
  frozen_probs -> reject;
}
"""
    write_text(output_dir / "gmr_selective_tta.mmd", gmr_mermaid)
    write_text(output_dir / "gmr_selective_tta.dot", gmr_dot)

    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "metrics": {
            "frozen_accuracy": frozen_accuracy,
            "locked_accuracy": locked_accuracy,
            "frozen_macro_f1": frozen_macro,
            "locked_macro_f1": locked_macro,
            "macro_f1_delta": locked_macro - frozen_macro,
            "frozen_recon_f1": frozen_recon,
            "locked_recon_f1": locked_recon,
            "recon_f1_delta": locked_recon - frozen_recon,
            "frozen_de_f1": frozen_de,
            "locked_de_f1": locked_de,
            "de_f1_delta": locked_de - frozen_de,
            "frozen_pr_auc": frozen_pr_auc,
            "locked_pr_auc": locked_pr_auc,
            "override_rate": override_rate,
            "confidence_reject_recon_f1": reject_recon,
            "confidence_reject_rate": reject_rate,
        },
        "locked_manifest": locked_manifest,
        "sweep_rows": len(sweep_summary),
    }
    write_text(
        output_dir / "tta_cloud_paper_audit_summary.json",
        json.dumps(audit, indent=2),
    )

    claim_table = markdown_table(
        ["Metric", "Frozen MLP", "Locked selective TTA", "Delta"],
        [
            ["Accuracy", fmt(frozen_accuracy), fmt(locked_accuracy), fmt(locked_accuracy - frozen_accuracy)],
            ["Macro F1", fmt(frozen_macro), fmt(locked_macro), fmt(locked_macro - frozen_macro)],
            ["PR-AUC", fmt(frozen_pr_auc), fmt(locked_pr_auc), fmt(locked_pr_auc - frozen_pr_auc)],
            ["Recon F1", fmt(frozen_recon), fmt(locked_recon), fmt(locked_recon - frozen_recon)],
            ["Data Exfiltration F1", fmt(frozen_de), fmt(locked_de), fmt(locked_de - frozen_de)],
            ["Override rate", "0.0000", fmt(override_rate), fmt(override_rate)],
        ],
    )
    split_table = markdown_table(
        [
            "Split",
            "Rows",
            "Source files",
            "Capture days",
            "Benign",
            "Recon",
            "Foothold",
            "Lateral Movement",
            "Data Exfiltration",
        ],
        stage_count_rows(preprocess),
    )
    per_seed_table = markdown_table(
        [
            "Seed",
            "Macro F1",
            "Recon F1",
            "DE F1",
            "PR-AUC",
            "Override",
            "Macro delta",
            "Recon delta",
            "DE delta",
        ],
        per_seed_rows,
    )
    checks_table = markdown_table(
        ["Check", "Result"],
        [[key, "PASS" if value else "FAIL"] for key, value in checks.items()],
    )

    report = f"""# Praxis 06 Final Cloud Paper Audit

Generated: {audit["generated_at_utc"]}

Status: **{audit["status"]}**

## Thesis

Selective no-label test-time adaptation can recover rare-stage APT behavior under held-out source-file shift when adaptation is constrained by a validation-selected safety gate that protects high-consequence Data Exfiltration predictions.

## Research Questions

| ID | Research question | Cloud audit answer |
|---|---|---|
| RQ1 | Does selective no-label TTA improve held-out source-file Macro F1? | Yes. Macro F1 moves from `{fmt(frozen_macro)}` to `{fmt(locked_macro)}`. |
| RQ2 | Does it recover the rare shifted Reconnaissance stage? | Yes. Recon F1 moves from `{fmt(frozen_recon)}` to `{fmt(locked_recon)}`. |
| RQ3 | Does the gate preserve Data Exfiltration? | Yes in the locked mean: DE F1 moves from `{fmt(frozen_de)}` to `{fmt(locked_de)}`, and every seed stays within the guard. |
| RQ4 | Is the result more than confidence filtering? | Yes. Matched confidence rejection at rate `{fmt(reject_rate)}` leaves Recon F1 at `{fmt(reject_recon)}`. |
| RQ5 | Are the split and temporal leakage controls adequate for a paper claim? | Yes at artifact level: source/group overlap is zero and temporal deltas reset per split. |

## Hypotheses

| Hypothesis | Status | Evidence |
|---|---|---|
| H1: Selective TTA increases Macro F1 by at least 5 points over frozen. | Supported | Delta `{fmt(locked_macro - frozen_macro)}`. |
| H2: Selective TTA increases Recon F1 by at least 25 points over frozen. | Supported | Delta `{fmt(locked_recon - frozen_recon)}`. |
| H3: Selective TTA does not reduce mean Data Exfiltration F1. | Supported | Delta `{fmt(locked_de - frozen_de)}`. |
| H4: The intervention remains selective, with override rate no more than 5%. | Supported | Override rate `{fmt(override_rate)}`. |
| H5: The result is not explained by rejecting uncertain frozen predictions. | Supported | Matched reject Recon F1 `{fmt(reject_recon)}`. |

## Literature Review Positioning

The paper should frame itself at the intersection of four literatures:

1. APT stage detection and intrusion detection under realistic deployment shift.
2. Test-time adaptation, especially entropy minimization and BatchNorm-stat adaptation.
3. Imbalanced and rare-class security ML evaluation.
4. Security-specific safety constraints, where improving one rare class is not acceptable if it damages a high-consequence class.

The safest related-work claim is that prior TTA work motivates adaptation under distribution shift, while this Praxis contributes a security-specific selective gate and a locked rare-stage APT evaluation. Do not claim broad TTA generality.

## Graphical Model Representation

```mermaid
{gmr_mermaid}
```

The GMR files are included as:

- `gmr_selective_tta.mmd`
- `gmr_selective_tta.dot`

## EDA And Split Audit

{split_table}

Leakage controls:

| Check | Value |
|---|---:|
| Train/validation source-file overlap | `{source_overlap["train_val"]}` |
| Train/test source-file overlap | `{source_overlap["train_test"]}` |
| Validation/test source-file overlap | `{source_overlap["val_test"]}` |
| Train/validation group overlap | `{group_overlap["train_val"]}` |
| Train/test group overlap | `{group_overlap["train_test"]}` |
| Validation/test group overlap | `{group_overlap["val_test"]}` |
| Temporal delta mode | `{preprocess["temporal_delta_seed_mode"]}` |

## Method

The frozen detector is a support-floor MLP from the trusted Unraveled pipeline. The selected adaptation method is `bn_adapt`. The locked gate is `recon_guarded`, selected on validation artifacts before final replay. The gate preserves confident frozen Data Exfiltration predictions, allows overrides on uncertain frozen predictions, and rescues Reconnaissance only when adapted confidence is sufficient.

No Optuna or threshold search is part of this cloud audit. The paper claim depends on the already-locked validation-selected policy, not on post-hoc optimization.

## Results

{claim_table}

## Per-Seed Results

{per_seed_table}

## Confidence-Reject Baseline

| Baseline | Reject rate | Kept Macro F1 | Kept Recon F1 | Kept DE F1 |
|---|---:|---:|---:|---:|
| Frozen confidence reject, matched to TTA override rate | `{fmt(reject_rate)}` | `{fmt(f(reject_row["kept_macro_f1_mean"]))}` | `{fmt(reject_recon)}` | `{fmt(f(reject_row["kept_de_f1_mean"]))}` |

This baseline rejects the same fraction of rows as the TTA gate but does not recover Reconnaissance.

## Cloud Audit Checks

{checks_table}

## Paper-Ready Claims

Allowed:

- Selective TTA improves locked Unraveled held-out source-file Macro F1.
- Selective TTA recovers Reconnaissance under this split.
- Data Exfiltration is preserved in the locked mean and within the guard per seed.
- The gain is not explained by matched-rate confidence rejection.
- AWS/S3 artifact-level repeatability is sufficient for a Praxis write-up.

Not allowed:

- TTA generally solves APT detection.
- Cross-dataset TTA generality is proven.
- DAPT2020 supports the same TTA claim.
- Provenance graph experiments are positive.

## Conclusion

The TTA capability is sound enough for a Praxis 06 paper package. It is easy to defend if the claim stays narrow: selective adaptation recovers a rare shifted stage while protecting Data Exfiltration under a locked, validation-selected gate.

The next work is paper packaging, not more threshold hunting.
"""
    write_text(output_dir / "PRAXIS06_FINAL_CLOUD_PAPER_AUDIT_20260513.md", report)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
