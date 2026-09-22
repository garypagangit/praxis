"""Report every declared arm and later-period role stratum."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from .run import ARMS, CLASSES, SEEDS, sha, write

LABELS = {"current": "Current flow only", "current_roles": "Current + roles", "current_history": "Current + earlier activity",
          "current_roles_history": "Current + roles + earlier activity", "current_roles_wrong_host_history": "Current + roles + wrong-host history",
          "roles_only": "Roles alone (shortcut diagnostic)"}
STRATUM = "DEPARTMENT->PRIVATE_SERVICES"


def figure(mean, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    values = [[mean[n]["test"]["per_class"]["DataExfiltration"]["ap"], mean[n]["test"]["lateral_any_attack_recall"]] for n in ARMS]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8), sharey=True)
    for j, (ax, title, color) in enumerate(zip(axes, ["Exfiltration ranking · average precision", "Movement recognized as any attack · recall"], ["#136f89", "#8f4262"])):
        y = np.arange(len(ARMS)); v = [r[j] for r in values]
        ax.barh(y, v, color=color)
        for k, value in enumerate(v): ax.text(min(value + .015, .96), k, f"{value:.3f}", va="center", fontsize=10)
        ax.set_xlim(0, 1.06); ax.set_xticks([0, .25, .5, .75, 1.]); ax.set_title(title, loc="left", fontsize=12)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlabel("Higher is better")
    axes[0].set_yticks(np.arange(len(ARMS)), [LABELS[n] for n in ARMS]); axes[0].invert_yaxis()
    fig.suptitle("Host context helps ranking, with a movement-detection cost", x=.025, ha="left", fontweight="bold", fontsize=15)
    fig.text(.025, .025, "UNRAVELED · mean of three fits on the same later-period cases · author stage labels, not verified theft outcomes", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .93)); fig.savefig(output / "CONTEXT_TRADEOFF.png", dpi=170); plt.close(fig)


def average(items):
    if isinstance(items[0], dict): return {k: average([v[k] for v in items]) for k in items[0]}
    if items[0] is None:
        if any(v is not None for v in items): raise ValueError("Inconsistent null metric")
        return None
    if isinstance(items[0], list): return np.mean(items, axis=0).tolist()
    return float(np.mean(items))


def publish(run, prepared, output):
    s = json.loads((run / "SUMMARY.json").read_text(encoding="utf-8"))
    if [r["seed"] for r in s["seeds"]] != SEEDS: raise ValueError("Incomplete run")
    mean = average([r["arms"] for r in s["seeds"]])
    contrasts = []
    pairs = [("current_roles", "current"), ("current_history", "current"),
             ("current_roles_history", "current_roles"), ("current_roles_history", "current_history"),
             ("current_roles_history", "current_roles_wrong_host_history")]
    for a, b in pairs:
        for population in ["test", STRATUM]:
            def get(r, name):
                item = r["arms"][name]
                return item["test"] if population == "test" else item["role_strata"][population]
            for metric in ["exfil_ap", "exfil_f1", "lateral_f1", "macro_f1"]:
                def value(m):
                    if metric == "macro_f1": return m["macro_f1_all_four"]
                    cl = "LateralMovement" if metric == "lateral_f1" else "DataExfiltration"
                    return m["per_class"][cl]["ap" if metric == "exfil_ap" else "f1"]
                d = [value(get(r, a)) - value(get(r, b)) for r in s["seeds"]]
                contrasts.append({"candidate": a, "reference": b, "population": population, "metric": metric,
                                  "mean_delta": float(np.mean(d)), "per_seed_deltas": d, "positive_seeds": sum(v > 0 for v in d), "negative_seeds": sum(v < 0 for v in d)})
    evidence = {"source_summary_sha256": sha(run / "SUMMARY.json"), "means": mean, "contrasts": contrasts,
                "scope": "One previously exposed APT campaign; author stage annotations; later single-sensor captures, not independent confirmed movement/theft"}
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(run / "SUMMARY.json", output / "SUMMARY.json")
    shutil.copy2(prepared / "PREPARATION.json", output / "PREPARATION.json")
    write(output / "EVIDENCE.json", evidence)
    figure(mean, output)
    write(output / "PRIVATE_ARTIFACTS.json", {"run_root": str(run), "prepared_root": str(prepared),
        "run_files": {str(p.relative_to(run)): sha(p) for p in run.rglob("*") if p.is_file()},
        "prepared_files": {p.name: sha(p) for p in prepared.iterdir() if p.is_file()}})
    percent = lambda v: "N/A" if v is None else f"{v*100:.2f}%"
    val = lambda v: "N/A" if v is None else f"{v:.4f}"
    lines = ["# Host roles and earlier activity: alternative-dataset pilot", "",
             "**All 18 fixed-configuration fits completed:** six arms, three fitting supports. UNRAVELED single IT sensor; later complete captures are the evaluation period. CPU only. Source/protocol freeze: `b6e9e8d`.", "",
             "## What this answers", "",
             "This tests whether coarse roles and strictly earlier completed activity improve prediction of the author's movement/exfiltration **stage annotations**. The source does not independently verify that each labeled flow performs successful movement or carries stolen data. All IT-sensor movement rows describe Remote System Discovery on one host pair. The distinction is material: a stage-label gain is not proof of detecting actual theft.", "",
             "The [frozen design](../../host_history_exfil/DESIGN.md), [data inventory](../../host_history_exfil/DATA_INVENTORY.md) and [dataset literature](../../host_history_exfil/DATASET_LITERATURE.md) explain the source, chronology, role mapping, missing movement calibration support and proposed stronger follow-up.", "",
             "## Data and method", "",
             "Malformed middle CSV fields were excluded; existing annotations were read from their validated right-hand positions. Feature/event identities and source hashes were checked. No target labels enter role or history features. All history flows finish strictly before the current flow starts. Current-flow statistics still require flow completion, so this is not early warning.", "",
             "| Partition | Benign | Other attack stage | Movement | Exfiltration |", "|---|---:|---:|---:|---:|"]
    for part, counts in s["preparation"]["split_counts"].items():
        lines.append(f"| {part} | " + " | ".join(str(counts[c]) for c in CLASSES) + " |")
    fit_counts = s["seeds"][0]["fit_counts"]
    lines += ["", "Each fit used " + ", ".join(f"{fit_counts[c]:,} {c}" for c in CLASSES) + ". Arms share these same fitting identities per seed. Every calibration and test row is retained; there is no random row train/test split.", "",
              f"Prepared {s['preparation']['rows']:,} rows; removed {s['preparation']['duplicate_rows_removed']} duplicate observable rows and quarantined {s['preparation']['conflicting_rows_quarantined']} conflicting rows. Modeling elapsed time: {s['receipt']['elapsed_seconds']:.1f} seconds.", "",
              "## Main later-period results", "",
              "Mean of three fits on the same later cases. AP is average precision. The first table uses the largest of four stage scores. Normal false alerts are benign rows called any attack; exfiltration precision includes confusion with other attacks.", "",
              "| Method | Four-class macro-F1 | Exfil AP | Exfil precision | Exfil recall | Exfil F1 | Movement F1 | Movement any-attack recall | Benign false attacks |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name in ARMS:
        m = mean[name]["test"]; e = m["per_class"]["DataExfiltration"]; l = m["per_class"]["LateralMovement"]
        lines.append(f"| {LABELS[name]} | {m['macro_f1_all_four']:.4f} | {val(e['ap'])} | {percent(e['precision'])} | {percent(e['recall'])} | {e['f1']:.4f} | {l['f1']:.4f} | {percent(m['lateral_any_attack_recall'])} | {m['benign_false_attack_count']:.2f} |")
    lines += ["", "![Context ranking and movement-recall tradeoff](CONTEXT_TRADEOFF.png)", "", "## Same coarse roles, shifted exfiltration destination", "",
              "Department-to-private-services evaluation has **1,576 benign, 35 movement and 1,101 exfiltration rows**. Its fitting split has zero exfiltration examples; calibration has neither target class in this stratum. This is a new destination-role context, not a matched in-distribution comparison. A role-only shortcut can fail here even when aggregate scores look high.", "",
              "The four-class F1 calculation includes OtherAttackStage even though it has no examples in this stratum; interpret the individual target F1s and counts directly. Pairwise AP considers only the two target labels; its no-skill reference is exfiltration prevalence **96.92%**, so a high value alone is weak evidence.", "",
              "| Method | Exfil AP vs all stratum rows | Exfil precision | Exfil recall | Exfil F1 | Movement precision | Movement recall | Movement F1 | Exfil-vs-movement AP |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name in ARMS:
        m = mean[name]["role_strata"][STRATUM]; e = m["per_class"]["DataExfiltration"]; l = m["per_class"]["LateralMovement"]
        lines.append(f"| {LABELS[name]} | {val(e['ap'])} | {percent(e['precision'])} | {percent(e['recall'])} | {e['f1']:.4f} | {percent(l['precision'])} | {percent(l['recall'])} | {l['f1']:.4f} | {val(m['exfil_vs_lateral_ap'])} |")
    lines += ["", "## Calibration-selected exfiltration decisions", "",
              "Thresholds maximize exfiltration F1 on calibration, then stay fixed. Calibration contains no movement examples; therefore these thresholds were not calibrated against movement confusion. The counted test movement mistakes make that limitation visible.", "",
              "| Method | Precision | Recall | F1 | True exfil alerts | False benign→exfil | False other-stage→exfil | False movement→exfil |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name in ARMS:
        m = mean[name]["exfil_f1_threshold"]; c = m["false_exfil_by_true_class"]
        lines.append(f"| {LABELS[name]} | {percent(m['precision'])} | {percent(m['recall'])} | {m['f1']:.4f} | {m['tp']:.2f} | {c['Benign']:.2f} | {c['OtherAttackStage']:.2f} | {c['LateralMovement']:.2f} |")
    lines += ["", "## Paired differences: every declared component comparison", "",
              "Deltas are candidate minus reference. These are fitting-support differences on shared cases, not independent-campaign confidence estimates.", "",
              "| Candidate | Reference | Population | Metric | Mean delta | Positive / negative fits |", "|---|---|---|---|---:|---:|"]
    for c in contrasts:
        lines.append(f"| {LABELS[c['candidate']]} | {LABELS[c['reference']]} | {c['population']} | {c['metric']} | {c['mean_delta']:+.4f} | {c['positive_seeds']} / {c['negative_seeds']} |")
    lines += ["", "## Fixed calibration-budget sensitivity", "",
              "Nominal 0.1%, 0.5%, 1%, and 2% non-exfiltration calibration tails are descriptive points, not success requirements or future guarantees. Movement is absent from calibration. Complete threshold values and later confusion counts are retained in SUMMARY.json.", "",
              "| Method | Nominal calibration budget | Test exfil precision | Test exfil recall | Test false exfil alerts |", "|---|---:|---:|---:|---:|"]
    for name in ARMS:
        for budget, m in mean[name]["non_exfil_budget_thresholds"].items():
            lines.append(f"| {LABELS[name]} | {percent(float(budget))} | {percent(m['precision'])} | {percent(m['recall'])} | {m['fp']:.2f} |")
    lines += ["", "## Interpretation limits and artifacts", "",
              "- A different dataset is not automatically independent confirmation: these source files were used in earlier GML development, and the record describes one APT campaign.",
              "- Using one sensor prevents a cross-interface shortcut but does not remove fixed-host, role, script or source-label associations. Intra-subnet traffic is not comprehensively observed.",
              "- Earlier history contains traffic observations only; stages, attacker identities, future events and future host inventories are excluded. No guarantee covers unmeasured exporter delays.",
              "- Only 35 later movement rows represent one annotated host pair; three fitting seeds do not create more attacks. Calibration has no movement examples.",
              "- Roles-only and wrong-host-history controls expose some shortcuts. A gain over them is not a causal explanation or proof of successful exfiltration.",
              "- Newer source files were also inspected directly. [Comprehensive APT2025 qualification](../../host_history_exfil/COMPREHENSIVE_PROBE.md) found schema failures, duplicates and failed/preparatory transfers among tactic tags; it is not silently treated as validated ground truth.", "",
              "[SUMMARY.json](SUMMARY.json) contains all seed/arm, role-pair and capture metrics. [EVIDENCE.json](EVIDENCE.json) holds means and paired differences. [PREPARATION.json](PREPARATION.json) and [PRIVATE_ARTIFACTS.json](PRIVATE_ARTIFACTS.json) bind inputs, models and scores. Consult the independent [AUDIT.json](AUDIT.json) before using results; an audit verifies saved-output calculations, not attack truth.", ""]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    write(output / "PUBLICATION.json", {"reporter_sha256": sha(__file__), "artifacts": {p.name: sha(p) for p in output.iterdir() if p.is_file() and p.name not in ["PUBLICATION.json", "AUDIT.json"]}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True); parser.add_argument("--prepared", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args(); publish(a.run, a.prepared, a.output)
