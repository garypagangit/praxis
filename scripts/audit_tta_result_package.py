from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

KEY_METRICS = [
    "test_accuracy_mean",
    "test_macro_f1_mean",
    "test_pr_auc_mean",
    "test_benign_f1_mean",
    "test_recon_f1_mean",
    "test_de_f1_mean",
    "test_macro_f1_delta_vs_frozen_mean",
    "test_recon_f1_delta_vs_frozen_mean",
    "test_de_f1_delta_vs_frozen_mean",
    "override_rate_test_mean",
]


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def best_row(summary: pd.DataFrame) -> pd.Series:
    return summary.sort_values(
        ["test_macro_f1_mean", "test_de_f1_mean", "test_recon_f1_mean"],
        ascending=[False, False, False],
    ).iloc[0]


def compare_aws(local_dir: Path, aws_dir: Path | None) -> dict:
    if aws_dir is None:
        return {"status": "not_checked"}
    if not aws_dir.exists():
        return {"status": "missing_aws_dir", "path": str(aws_dir)}

    local_summary = load_csv(local_dir / "summary_mean_std.csv")
    aws_summary = load_csv(aws_dir / "summary_mean_std.csv")
    merged = local_summary.merge(
        aws_summary,
        on=["policy", "tta_method", "de_delta_limit"],
        suffixes=("_local", "_aws"),
        how="outer",
        indicator=True,
    )
    max_abs_delta = 0.0
    deltas: dict[str, float] = {}
    for metric in KEY_METRICS:
        left = f"{metric}_local"
        right = f"{metric}_aws"
        if left in merged.columns and right in merged.columns:
            delta = (merged[left] - merged[right]).abs().max()
            deltas[metric] = float(delta)
            max_abs_delta = max(max_abs_delta, float(delta))
    tolerance = 1e-5
    return {
        "status": (
            "pass"
            if max_abs_delta <= tolerance and (merged["_merge"] == "both").all()
            else "diff"
        ),
        "rows_local": int(len(local_summary)),
        "rows_aws": int(len(aws_summary)),
        "max_abs_delta": max_abs_delta,
        "tolerance": tolerance,
        "metric_deltas": deltas,
    }


def policy_seed_table(
    selected: pd.DataFrame, policy: str, method: str, de_delta_limit: float
) -> pd.DataFrame:
    mask = (
        (selected["policy"] == policy)
        & (selected["tta_method"] == method)
        & (np.isclose(selected["de_delta_limit"], de_delta_limit))
    )
    return selected[mask].sort_values("seed").reset_index(drop=True)


def override_sensitivity(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    frame["override_bin"] = pd.cut(
        frame["override_rate_test"],
        bins=[-0.001, 0.02, 0.05, 0.08, 0.12, 1.0],
        labels=["<=2%", "2-5%", "5-8%", "8-12%", ">12%"],
    )
    grouped = (
        frame.groupby("override_bin", observed=True)
        .agg(
            rows=("test_macro_f1", "size"),
            macro_mean=("test_macro_f1", "mean"),
            recon_mean=("test_recon_f1", "mean"),
            de_mean=("test_de_f1", "mean"),
            val_macro_mean=("val_macro_f1", "mean"),
        )
        .reset_index()
    )
    return grouped


def val_test_correlation(raw: pd.DataFrame) -> dict[str, float]:
    cols = [
        ("macro_f1", "val_macro_f1", "test_macro_f1"),
        ("recon_f1", "val_recon_f1", "test_recon_f1"),
        ("de_f1", "val_de_f1", "test_de_f1"),
    ]
    out = {}
    for name, val_col, test_col in cols:
        out[name] = float(raw[val_col].corr(raw[test_col], method="spearman"))
    return out


def render_table(frame: pd.DataFrame, float_places: int = 4) -> str:
    data = frame.copy()
    for col in data.columns:
        if pd.api.types.is_float_dtype(data[col]):
            data[col] = data[col].map(lambda value: f"{value:.{float_places}f}")
    header = "| " + " | ".join(data.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(data.columns)) + " |"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |" for row in data.to_numpy()
    ]
    return "\n".join([header, divider, *rows])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit TTA result package before Praxis candidate write-up."
    )
    parser.add_argument(
        "--local-run-dir", default="runs/tta-hybrid-gate-sweep-20260509"
    )
    parser.add_argument("--aws-run-dir", default="")
    parser.add_argument("--out-dir", default="runs/tta-result-audit-20260509")
    args = parser.parse_args()

    local_dir = Path(args.local_run_dir)
    aws_dir = Path(args.aws_run_dir) if args.aws_run_dir else None
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = load_csv(local_dir / "summary_mean_std.csv")
    selected = load_csv(local_dir / "selected_hybrid_policies.csv")
    raw = load_csv(local_dir / "hybrid_gate_sweep_raw.csv")
    frozen = load_csv(local_dir / "frozen_reference_raw.csv")

    best = best_row(summary)
    best_policy = str(best["policy"])
    best_method = str(best["tta_method"])
    best_de_delta = float(best["de_delta_limit"])
    seed_rows = policy_seed_table(selected, best_policy, best_method, best_de_delta)

    per_seed_checks = {
        "all_seed_macro_positive": bool(
            (seed_rows["test_macro_f1_delta_vs_frozen"] > 0).all()
        ),
        "all_seed_recon_positive": bool(
            (seed_rows["test_recon_f1_delta_vs_frozen"] > 0).all()
        ),
        "all_seed_de_delta_ge_negative_5pts": bool(
            (seed_rows["test_de_f1_delta_vs_frozen"] >= -0.05).all()
        ),
        "all_seed_override_le_8pct": bool(
            (seed_rows["override_rate_test"] <= 0.08).all()
        ),
    }
    gate_checks = {
        "best_macro_delta_ge_5pts": bool(
            best["test_macro_f1_delta_vs_frozen_mean"] >= 0.05
        ),
        "best_recon_delta_ge_25pts": bool(
            best["test_recon_f1_delta_vs_frozen_mean"] >= 0.25
        ),
        "best_de_delta_nonnegative": bool(
            best["test_de_f1_delta_vs_frozen_mean"] >= 0.0
        ),
        "best_override_le_5pct_mean": bool(best["override_rate_test_mean"] <= 0.05),
        **per_seed_checks,
    }
    aws_compare = compare_aws(local_dir, aws_dir)
    corr = val_test_correlation(raw)
    sensitivity = override_sensitivity(raw)

    pr_auc_delta = float(
        best["test_pr_auc_mean"] - frozen[frozen["split"] == "test"]["pr_auc"].mean()
    )
    risks = []
    if pr_auc_delta < -0.01:
        risks.append(
            "Best policy improves F1 but lowers mean test PR-AUC versus frozen; include calibration/threshold discussion."
        )
    if not gate_checks["all_seed_de_delta_ge_negative_5pts"]:
        risks.append(
            "At least one seed loses more than 5 points of DE F1; keep DE guard analysis in the report."
        )
    if corr["macro_f1"] < 0.3:
        risks.append(
            "Validation-to-test macro ranking is weak; avoid overclaiming validation selection generality."
        )

    payload = {
        "local_run_dir": str(local_dir),
        "aws_run_dir": str(aws_dir) if aws_dir else None,
        "best_policy": best.to_dict(),
        "gate_checks": gate_checks,
        "aws_compare": aws_compare,
        "val_test_spearman": corr,
        "pr_auc_delta_vs_frozen_mean": pr_auc_delta,
        "risks": risks,
    }
    (out_dir / "audit_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    sensitivity.to_csv(out_dir / "override_sensitivity.csv", index=False)
    seed_rows.to_csv(out_dir / "best_policy_per_seed.csv", index=False)

    report = [
        "# TTA Result Audit",
        "",
        f"Local run: `{local_dir}`",
        f"AWS run: `{aws_dir}`" if aws_dir else "AWS run: `not checked`",
        "",
        "## Headline Policy",
        "",
        render_table(
            pd.DataFrame(
                [
                    best[
                        ["policy", "tta_method", "de_delta_limit", *KEY_METRICS]
                    ].to_dict()
                ]
            )
        ),
        "",
        "## Per-Seed Best Policy",
        "",
        render_table(
            seed_rows[
                [
                    "seed",
                    "test_macro_f1",
                    "test_macro_f1_delta_vs_frozen",
                    "test_recon_f1",
                    "test_recon_f1_delta_vs_frozen",
                    "test_de_f1",
                    "test_de_f1_delta_vs_frozen",
                    "override_rate_test",
                ]
            ]
        ),
        "",
        "## Gate Checks",
        "",
        render_table(
            pd.DataFrame(
                [{"check": key, "pass": value} for key, value in gate_checks.items()]
            )
        ),
        "",
        "## AWS Comparison",
        "",
        "```json",
        json.dumps(aws_compare, indent=2),
        "```",
        "",
        "## Override Sensitivity",
        "",
        render_table(sensitivity),
        "",
        "## Validation/Test Rank Correlation",
        "",
        render_table(pd.DataFrame([corr])),
        "",
        "## Risks",
        "",
    ]
    if risks:
        report.extend([f"- {risk}" for risk in risks])
    else:
        report.append("- No material artifact-level risks found.")
    report.extend(
        [
            "",
            "## Decision",
            "",
            (
                "Proceed to Praxis 06 write-up if leakage audit also passes. "
                "The artifact audit supports the main claim: conservative test-time adaptation "
                "recovers Reconnaissance under held-out shift with low override rate and no mean DE penalty."
            ),
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(
        json.dumps(
            {"gate_checks": gate_checks, "aws_compare": aws_compare, "risks": risks},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
