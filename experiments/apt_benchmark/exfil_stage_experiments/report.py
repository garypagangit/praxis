"""Publish all frozen pilot arms, paired contrasts, and static figures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from .run import CLASSES, PARAMETERS, SEEDS, sha, write_json


LABELS = {
    "raw_general_xgboost": "General XGB · raw",
    "raw_general_lightgbm": "General LGB · raw",
    "engineered_general_xgboost": "General XGB · engineered",
    "engineered_general_lightgbm": "General LGB · engineered",
    "raw_specialist_xgboost": "Exfil expert XGB · raw",
    "raw_specialist_lightgbm": "Exfil expert LGB · raw",
    "engineered_specialist_xgboost": "Exfil expert XGB · engineered",
    "engineered_specialist_lightgbm": "Exfil expert LGB · engineered",
    "engineered_general_average": "General-model average",
    "engineered_specialist_average": "Specialist average",
    "engineered_fixed_fusion": "General + specialist average",
    "engineered_selected_specialists": "Family selected per stage",
    "engineered_general_learned": "General-only learned fusion",
    "engineered_specialist_learned": "Specialist-only learned fusion",
    "engineered_learned_fusion": "General + specialist learned fusion",
}


def means(items):
    first = items[0]
    if isinstance(first, dict):
        return {k: means([x[k] for x in items]) for k in first}
    if isinstance(first, (float, int)):
        return float(np.mean(items))
    if isinstance(first, list):
        return np.mean(items, axis=0).tolist()
    raise TypeError(type(first))


def contrasts(seeds):
    result = []
    for family in PARAMETERS:
        for task in ("general", "specialist"):
            a, b = f"engineered_{task}_{family}", f"raw_{task}_{family}"
            result.append(("exfil", "average_precision", a, b, "engineered minus raw"))
        for view in ("raw", "engineered"):
            result.append(("exfil", "average_precision", f"{view}_specialist_{family}", f"{view}_general_{family}", "specialist minus general"))
    for a in ("engineered_fixed_fusion", "engineered_learned_fusion"):
        for b in ("engineered_general_xgboost", "engineered_general_lightgbm", "engineered_general_average", "engineered_general_learned"):
            result.append(("exfil", "average_precision", a, b, "combined minus general control"))
    for a in ("engineered_specialist_average", "engineered_selected_specialists", "engineered_specialist_learned", "engineered_fixed_fusion", "engineered_learned_fusion"):
        for b in ("engineered_general_xgboost", "engineered_general_lightgbm", "engineered_general_average", "engineered_general_learned"):
            result.append(("stage", "macro_f1", a, b, "stage specialization/fusion minus general control"))
    out = []
    for task, metric, a, b, description in result:
        deltas = [r[task][a][metric] - r[task][b][metric] for r in seeds]
        out.append({"task": task, "metric": metric, "candidate": a, "reference": b, "description": description,
                    "mean_delta": float(np.mean(deltas)), "paired_deltas": deltas,
                    "positive_seeds": int(np.sum(np.array(deltas) > 0)), "negative_seeds": int(np.sum(np.array(deltas) < 0))})
    return out


def figures(evidence, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    stage = evidence["means"]["stage"]
    keys = list(stage)
    values = np.array([[stage[k]["per_stage"][c]["f1"] for c in CLASSES] for k in keys])
    fig, ax = plt.subplots(figsize=(11.8, 6.6))
    im = ax.imshow(values, vmin=0, vmax=1, cmap="YlGnBu", aspect="auto")
    ax.set_yticks(range(len(keys)), [LABELS[k] for k in keys])
    ax.set_xticks(range(6), ["Exfiltration", "Initial\ncompromise", "Lateral\nmovement", "Normal", "Pivoting", "Reconnaissance"])
    for i in range(len(keys)):
        for j in range(6):
            ax.text(j, i, f"{values[i,j]:.3f}", ha="center", va="center", color="white" if values[i,j] > .65 else "black")
    ax.set_title("Correct stage identification · mean F1 across three fits", loc="left", fontweight="bold", pad=16)
    fig.colorbar(im, ax=ax, shrink=.65, label="Stage F1 (higher is better)")
    fig.text(.02, .02, "SCVIC development only · same 30,787 evaluation rows · not a chronological attack reconstruction", fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(output / "STAGE_F1.png", dpi=170)
    fig.savefig(output / "STAGE_F1.svg")
    plt.close(fig)
    exfil = evidence["means"]["exfil"]
    keys = list(exfil)
    fig, ax = plt.subplots(figsize=(10.8, 7.0))
    y = np.arange(len(keys))
    colors = ["#136f89" if "fusion" in k else "#365172" for k in keys]
    ax.barh(y, [exfil[k]["average_precision"] for k in keys], color=colors)
    for i, k in enumerate(keys):
        vals = [r["exfil"][k]["average_precision"] for r in evidence["seeds"]]
        ax.scatter(vals, [i]*len(vals), color="#df9b3c", s=22, edgecolors="#423319", linewidth=.5, zorder=3)
    ax.set_yticks(y, [LABELS[k] for k in keys]); ax.invert_yaxis()
    ax.set_xlim(0, 1); ax.set_xlabel("Exfiltration average precision (higher is better)")
    ax.set_title("Recognizing exfiltration · all declared arms", loc="left", fontweight="bold", pad=16)
    fig.text(.02, .02, "Bars: mean of three fits. Dots: individual fits on the same 106 exfiltration cases. Development evidence only.", fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(output / "EXFIL_AP.png", dpi=170); fig.savefig(output / "EXFIL_AP.svg")
    plt.close(fig)


def publish(run_dir, output):
    result = json.loads((run_dir / "SUMMARY.json").read_text(encoding="utf-8"))
    seeds = result["seeds"]
    if [s["seed"] for s in seeds] != SEEDS:
        raise ValueError("Missing or misordered seeds")
    output.mkdir(parents=True, exist_ok=True)
    evidence = {"source_summary_sha256": sha(run_dir / "SUMMARY.json"), "source_run": str(run_dir),
                "means": {task: means([r[task] for r in seeds]) for task in ("exfil", "stage")},
                "paired_contrasts": contrasts(seeds), "seeds": seeds,
                "interpretation": "Arithmetic means over fitting supports, same evaluation cases; no independent seed CI or new holdout claim"}
    write_json(output / "EVIDENCE.json", evidence)
    shutil.copy2(run_dir / "SUMMARY.json", output / "SUMMARY.json")
    write_json(output / "PRIVATE_ARTIFACTS.json", {"root": str(run_dir), "files": {str(p.relative_to(run_dir)): sha(p) for p in run_dir.rglob("*") if p.is_file()}})
    figures(evidence, output)
    exfil, stage = evidence["means"]["exfil"], evidence["means"]["stage"]
    pct = lambda v: f"{100*v:.2f}%"
    lines = ["# Exfiltration attribution and stage-specialist fusion: pilot results", "",
             "**Completed:** two development experiments; all three declared seeds and every arm. No method was dropped after its results. Source model/protocol freeze: `c961dff`. CPU only; no AWS compute started.", "",
             "## What was measured", "",
             "Experiment 1 tests whether an exfiltration specialist and 18 engineered traffic features help correctly identify exfiltration. Experiment 2 combines stage experts and measures the complete six-class classification. This does not measure attack chronology, early warning, or adversary identity.", "",
             "Each seed uses the same 1,184 fitting labels across arms (1,024 normal + 32 for each attack stage). Calibration uses 30,782 additional rows. Evaluation uses the same previously exposed 30,787 development rows, with 106 exfiltration, 15 initial-compromise, 144 lateral, 29,929 normal, 425 pivoting and 168 reconnaissance cases. Seed variation is training-support variation, not independent attacks.", "",
             f"The batch fitted {result['receipt']['base_fits_including_crossfit']} base models including cross-fitting, retained {result['receipt']['final_base_models']} final base models, and fitted {result['receipt']['fusion_fits']} fusion models. Elapsed modeling time: {result['receipt']['elapsed_seconds']:.1f} seconds.", "",
             "All configurations are fixed; this does not establish superiority over an exhaustively tuned baseline. General-only learned fusion controls for score recombination. Engineered generals control for the extra features. Learned fusion receives only out-of-fold fitting scores. See the [design](../../exfil_stage_experiments/DESIGN.md), [protocol](../../exfil_stage_experiments/protocol.json), [data qualification](../../exfil_stage_experiments/DATA_QUALIFICATION.md), and [literature review](../../exfil_stage_experiments/LITERATURE.md).", "",
             "## Experiment 1: exact exfiltration recognition", "",
             "AP means average precision over the precision–recall curve. F1/precision/recall and alert counts below use a threshold chosen to maximize exfiltration F1 on calibration data, then locked for evaluation. Counts are means over fits. False exfiltration alerts include normal traffic **and other attack stages**.", "",
             "| Method | AP | ROC-AUC | Precision | Recall | F1 | True exfil alerts /106 | All false exfil alerts | Normal false exfil alerts |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, m in exfil.items():
        t = m["calibration_f1_threshold"]
        lines.append(f"| {LABELS[name]} | {m['average_precision']:.4f} | {m['roc_auc']:.4f} | {pct(t['precision'])} | {pct(t['recall'])} | {t['f1']:.4f} | {t['tp']:.2f} | {t['fp']:.2f} | {t['normal_fp']:.2f} |")
    lines += ["", "![Exfiltration AP for every arm](EXFIL_AP.png)", "", "### Paired exfiltration contrasts", "",
              "Every contrast below was specified by the design's feature, specialization, and fusion comparisons. Delta is candidate minus reference in AP units. A positive mean is a descriptive improvement on these cases; three positive fits do not establish population reliability.", "",
              "| Candidate | Reference | Mean AP delta | Positive / negative fits |", "|---|---|---:|---:|"]
    for c in evidence["paired_contrasts"]:
        if c["task"] == "exfil":
            lines.append(f"| {LABELS[c['candidate']]} | {LABELS[c['reference']]} | {c['mean_delta']:+.4f} | {c['positive_seeds']} / {c['negative_seeds']} |")
    lines += ["", "## Experiment 2: the full stage assessment", "",
              "Stage decisions use the largest of six scores. F1 values give equal attention to precision and recall; macro-F1 averages the six class F1s equally. Each stage's full precision, recall, AP, ROC-AUC, and confusion are in EVIDENCE.json and the per-stage table below.", "",
              "| Method | Macro-F1 | Exfil F1 | Initial F1 | Lateral F1 | Normal F1 | Pivot F1 | Recon F1 | Normal any-attack FPR |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, m in stage.items():
        values = " | ".join(f"{m['per_stage'][c]['f1']:.4f}" for c in CLASSES)
        lines.append(f"| {LABELS[name]} | {m['macro_f1']:.4f} | {values} | {pct(m['normal_fpr_any_attack'])} |")
    lines += ["", "![F1 for each stage](STAGE_F1.png)", "", "### Stage fusion paired comparisons", "",
              "| Candidate | Reference | Mean macro-F1 delta | Positive / negative fits |", "|---|---|---:|---:|"]
    for c in evidence["paired_contrasts"]:
        if c["task"] == "stage":
            lines.append(f"| {LABELS[c['candidate']]} | {LABELS[c['reference']]} | {c['mean_delta']:+.4f} | {c['positive_seeds']} / {c['negative_seeds']} |")
    lines += ["", "## False-positive budget sensitivity", "",
              "The 0.1%, 0.5%, 1%, and 2% levels are descriptive calibration budgets chosen for comparison. Actual evaluation rates can differ. These are not population guarantees or pass/fail research requirements. Normal-only calibration does not control confusion with other attacks; both versions are reported.", "",
              "| Method | Calibration population | Nominal budget | Test exfil recall | Test precision | Test all-non-exfil FPR | Test normal FPR |", "|---|---|---:|---:|---:|---:|---:|"]
    for name, m in exfil.items():
        for key, population in [("normal_budget_thresholds", "Normal"), ("non_exfil_budget_thresholds", "All non-exfil")]:
            for budget, t in m[key].items():
                lines.append(f"| {LABELS[name]} | {population} | {pct(float(budget))} | {pct(t['recall'])} | {pct(t['precision'])} | {pct(t['non_exfil_fpr'])} | {pct(t['normal_fpr'])} |")
    lines += ["", "## Every stage: full identification metrics", "", "| Method | True stage | Precision | Recall | F1 | AP | ROC-AUC |", "|---|---|---:|---:|---:|---:|---:|"]
    for name, m in stage.items():
        for c in CLASSES:
            t = m["per_stage"][c]
            lines.append(f"| {LABELS[name]} | {c} | {pct(t['precision'])} | {pct(t['recall'])} | {t['f1']:.4f} | {t['average_precision']:.4f} | {t['roc_auc']:.4f} |")
    lines += ["", "## What the available evidence cannot establish", "",
              "- General and specialist ensembles already exist in the literature, including exfiltration-specific neural/tree work on SCVIC. A development gain here is an applied finding, not a new algorithm claim.",
              "- SCVIC rows are deduplicated by exact predictor fingerprints, not guaranteed independent executions; new support hashes do not create a new holdout. Comparison arms share the same support and measurement rows.",
              "- Flow-forward/backward is not verified victim-outbound/inbound direction. Full-flow features cannot show early detection.",
              "- The acquired DEDALE subset has two exfiltration flows from one execution. It can illustrate a source-locked timeline, not prove dependable exfiltration recognition across campaigns. No DEDALE models were fitted or evaluated in this batch.",
              "- Feature-view loss, actual missing/delayed logs, and causal host-linked stage fusion remain separately specified extensions. None is claimed as measured here.", "",
              "## Reproducibility", "",
              "[SUMMARY.json](SUMMARY.json) preserves each seed and arm. [EVIDENCE.json](EVIDENCE.json) contains arithmetic means and paired contrasts. [PRIVATE_ARTIFACTS.json](PRIVATE_ARTIFACTS.json) binds stored models, predictions and fit/fold identities by SHA-256. The independent [AUDIT.json](AUDIT.json) reports what was checked; consult its status before using the results. A computational audit is not independent empirical confirmation.", ""]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(output / "PUBLICATION.json", {"source_summary_sha256": sha(run_dir / "SUMMARY.json"), "reporter_sha256": sha(__file__),
                                            "artifacts": {p.name: sha(p) for p in output.iterdir() if p.is_file() and p.name not in ("PUBLICATION.json", "AUDIT.json")}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    publish(args.run, args.output)
