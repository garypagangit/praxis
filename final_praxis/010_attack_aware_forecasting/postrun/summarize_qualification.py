"""Package completed Q1 receipts and deterministic descriptive accounting.

No inference, cloud access, or third-party data reads. Requires a passing
three-mode audit; remains fail-closed until the final calibration completes.
"""
import argparse
import datetime
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_bytes((json.dumps(value, indent=2) + "\n").encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    completed = root / "completed_qualification"
    audit_path = completed / "FINAL_ARTIFACT_AUDIT.json"
    audit = json.loads(audit_path.read_text())
    assert audit["disposition"] == "PASS_ACCOUNTING" and not audit["failures"] and not audit["missing_modes"]
    assert audit["source_sha256"] == sha(root / "postrun/audit_qualification.py")
    modes = {}
    for mode in ["original25", "new3", "calibration"]:
        directory = completed / mode
        path = directory / "QUALIFICATION_RECEIPT.json"
        receipt = json.loads(path.read_text())
        assert receipt["qualification_gate"] == "PASS"
        assert audit["receipts"][mode]["sha256"] == sha(path)
        for name, expected in receipt["artifacts"].items():
            target = (directory / name).resolve()
            assert target.is_relative_to(directory) and sha(target) == expected
        modes[mode] = receipt
    freeze = json.loads((root / "RUNTIME_FREEZE.json").read_text())
    assert all(sha(root / name) == expected for name, expected in freeze["files"].items())
    actions = [json.loads(line) for line in (completed / "original25/interventions.jsonl").read_text().splitlines()]
    action_counts = {}
    for policy in ["historical_oracle_blend", "rolling", "alarm_only_blend", "literal_freeze"]:
        action_counts[policy] = {}
        for stream in ["att", "cln"]:
            for name, lower, upper in [("pre_onset", 51, 71), ("endpoint", 71, 101)]:
                rows = [r for r in actions if r["policy"] == policy and r["stream"] == stream and lower <= r["t"] < upper]
                action_counts[policy][stream + "_" + name] = {"positions": len(rows), "alarms": sum(r["alarm"] for r in rows), "actions": dict(Counter(r["action"] for r in rows))}
    calibration = modes["calibration"]
    original = modes["original25"]
    new3 = modes["new3"]
    summary = {
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "qualification": "PASS_TO_PROSPECTIVE_DEVELOPMENT_ONLY",
        "candidate_praxis_efficacy": "UNTESTED",
        "scope": "Pinned public-source implementation qualification and fixed development controls; not an author-environment bitwise replication or a new defense trial.",
        "audit_checks_passed": audit["checks_passed"],
        "audit_checks_total": audit["checks_total"],
        "audit_sha256": sha(audit_path),
        "separately_authored_review": {"receipt": "independent_review/INDEPENDENT_010_RESULTS_REVIEW.json", "sha256": sha(completed / "independent_review/INDEPENDENT_010_RESULTS_REVIEW.json"), "checks_passed": 20026, "checks_total": 20026, "scope": "Independent saved-result reconstruction; no forecast, latency, memory or adaptive-optimizer reexecution."},
        "original25_comparisons": original["comparisons"],
        "original25_action_counts": action_counts,
        "new3_shift": {k: new3[k] for k in ["step_onset_delay", "step_full_retention", "step_first32_alarm_fraction", "step_last32_alarm_fraction", "step_late_alarm_fraction", "post_return_alarm_points"]},
        "calibration": {k: calibration[k] for k in ["dataset_rows", "original_train_boundary", "scored_positions", "true_positive_points", "false_positive_points", "anomaly_points", "normal_points", "requested_n_epochs", "effective_epochs"]},
        "model_runtime_seconds": {mode: receipt["runtime_seconds"] for mode, receipt in modes.items()},
        "model_peak_allocated_gib": {mode: receipt["peak_allocated_gib"] for mode, receipt in modes.items()},
        "model_runtime_sum_seconds": sum(receipt["runtime_seconds"] for receipt in modes.values()),
        "cost_scope": "Runtime receipts are not a billing invoice. Root campaign operational receipts account for shared AWS host/setup/stop and cost.",
        "heldout_hai_scored": False,
        "novel_defense_tested": False,
        "source_amendment_A1": "Exact upstream requested n_epochs=1/effective epochs=2 mismatch preserved before inference.",
        "auditor_correction_A2": "Float32 blend operation order corrected before original25 artifact inspection; no tolerance relaxation.",
        "data_scope_deviation_D1": "Unpreregistered timestamp/header-only expansion to all eight HAI files after model execution started; no additional sensor/label values parsed. Ledger frozen and further access stopped.",
        "future_split_requirement": "Cite the D1 ledger and preregister any date-based split before sensor or label analysis; benchmark filename splits are not chronological.",
        "next_gate": "Freeze a small chronological development design for a causally observable constrained context-update modification, with benign-shift recovery and false-alarm constraints. Any claimed forecast-influence bound requires explicit sensitivity or perturbation assumptions; bounded admission mass alone does not bound a nonlinear forecast. Do not proceed directly to heldout efficacy or primary-Praxis claims.",
        "summary_script_sha256": sha(Path(__file__)),
    }
    save(completed / "QUALIFICATION_SUMMARY.json", summary)
    table = "\n".join("| {policy} | {alarm_attack_points}/{attack_points} | {alarm_clean_points}/{clean_points} | {detected_episodes}/{episode_denominator} |".format(**row) for row in original["comparisons"])
    document = f"""# Candidate 010: completed qualification

**Decision: advance to a new, prospective development design. The proposed novel defense remains untested.** All three actual model modes completed, and the artifact auditor passed {audit['checks_passed']}/{audit['checks_total']} checks. Source and CPU gates also passed before model execution. A [separately authored independent review](independent_review/INDEPENDENT_010_RESULTS_REVIEW.json) passed 20,026/20,026 checks; its exact source, validation receipts, prior partial reviews, and replay wrapper are included.

## Question and qualification scope

Can a causal monitoring procedure retain persistent sensor-attack evidence while recovering after legitimate changes? Published context protection and adaptive calibration already exist. A bounded update mass alone does not bound the change in a nonlinear forecast; any mathematical influence guarantee requires explicit sensitivity or perturbation assumptions. This qualification establishes reproducible baselines, executable public-data calibration, and the operational feasibility of native TimesFM 3. It does not establish the novelty or efficacy of the proposed constrained context-update modification.

The frozen QH1 observer/source comparison and QH2 synthetic persistence controls passed: 222 CPU checks, 20 original observer simulations, and all 10 predetermined persistence seeds. QH3 completed the full 20-seed original TimesFM 2.5 comparison and exact selected Chronos/W1ACAS public example. QH4 completed native TimesFM 3 finite/repeat/latency/memory gates. See [protocol](../QUALIFICATION_PROTOCOL.md), [runtime freeze](../RUNTIME_FREEZE.json), and [final audit](FINAL_ARTIFACT_AUDIT.json).

## Original TimesFM 2.5 results

| Policy | Attack alarms | Clean alarms | Episode hits |
|---|---:|---:|---:|
{table}

Each endpoint denominator is 600 positions from 20 matched simulations. All 4,800 endpoint records and 8,000 admission records are retained. Literal freezing increases clean false alarms as well as attack alarms. Equal endpoint totals for historical and alarm-only blending do not imply general equivalence: the historical path disables protection before known attack onset, whereas alarm-only blending actually modifies eight of 400 pre-onset positions in each matched stream. The complete action accounting is in [QUALIFICATION_SUMMARY.json](QUALIFICATION_SUMMARY.json).

This reruns reviewed released calculations with pinned contemporary assets, not a reconstruction of the authors' unspecified original software/checkpoint environment. Historical use of oracle onset is disclosed and separated from deployable controls. This is a development comparison of existing policies, not a test of our proposed new method.

## Native TimesFM 3 probe

Median batch latency was {new3['median_batch_latency_seconds']:.6f} seconds; peak allocated GPU memory was {new3['peak_allocated_gib']:.3f} GiB; repeated forecasts differed by {new3['max_repeat_abs_difference']}. On the prespecified +2 synthetic shift, three of 256 shifted positions alarmed, with none after the first 32 shifted positions and two alarms after return. This is consistent with adaptation to a predictable change on one fixed development probe. It cannot distinguish malicious intent from an identical benign observation stream. See [raw forecasts and receipt](new3/QUALIFICATION_RECEIPT.json) and [figure](figures/new3_persistence.png).

## Public-data calibration

The exact TSB-AD NAB example has {calibration['dataset_rows']} rows, of which {calibration['scored_positions']} are scored after the fixed first-{calibration['original_train_boundary']}-row boundary. At fixed alpha 0.01, {calibration['true_positive_points']}/{calibration['anomaly_points']} anomalous positions and {calibration['false_positive_points']}/{calibration['normal_points']} normal positions alarmed. All values, labels, target-window alignments and reported counts were checked against the pinned file. The underlying forecaster and adaptive optimizer were not reexecuted by the artifact auditor.

The released wrapper's n_epochs=1/epochs=2 mismatch was preserved and disclosed in the pre-inference A1 amendment. The source demo's label-informed best-PA-F1 threshold is omitted in favor of the frozen threshold; consequently these are not reproduced paper aggregate metrics. The entire selected series is development/reproduction data, not a heldout cyber test. Retained y_true arrays and per-position labels are derived NAB/TSB-AD data with [source attribution and licenses](licenses/NOTICE.md).

## Reproducibility and limits

The three modes used {summary['model_runtime_sum_seconds']:.2f} seconds of measured worker runtime in total; this excludes shared host setup and does not constitute an invoice. Per-mode timing, installed packages, source/model identities, complete raw rows and the artifact auditor are included. The root campaign records operational isolation, instance shutdown and cost separately.

The original auditor promoted float32 predictions to float64 before blending. Source review corrected this before original 2.5 artifact inspection, preserving the strict tolerance; the targeted and negative controls pass 11/11. See [auditor correction A2](../postrun/AUDITOR_CORRECTION_A2.json). The frozen worker and protocol were unchanged.

HAI metadata access expanded beyond the train1-only plan after model execution started. [Scope deviation Q1-D1](HAI_METADATA_SCOPE_DEVIATION.json) records the exact timestamp/header-only access, source hash, all eight file identities, and stopped further access. No additional sensor or label values were parsed. The filename train/test partitions are not chronological; any future date-based split must cite this post-start ledger and be frozen before sensor/label analysis. HAI raw data remain outside Git, and no heldout HAI model efficacy was inspected.

Reproduce the raw-row audit after retrieving the pinned external NAB example:

```text
python postrun/audit_qualification.py --cache EXTERNAL_CACHE --original25 completed_qualification/original25 --new3 completed_qualification/new3 --calibration completed_qualification/calibration --output completed_qualification/FINAL_ARTIFACT_AUDIT.json
python postrun/replay_independent_review.py --cache EXTERNAL_CACHE --output NEW_INDEPENDENT_REPLAY.json
python postrun/summarize_qualification.py
```

The first command validates hashes, complete row universes, arithmetic and chronology alignment without new inference; the independent replay command rebuilds the expected receipt layout and runs the separately authored reviewer without loading a model; the last command regenerates the descriptive summary and release manifest. Model reruns use the frozen [GPU runbook](../GPU_RUNBOOK.md) with fresh output directories and external asset caches.

## Next investment decision

Invest in a small frozen development experiment on the proposed causal modification, using explicit false-alarm and benign-recovery constraints and comparable simple baselines. These qualification results justify technical development, not selection as the primary Praxis. The persistence phenomenon, buffer protection, and adaptive calibration all have direct prior art; a successful new causal mechanism and a defensible evaluation remain necessary.
"""
    (completed / "QUALIFICATION_SUMMARY.md").write_bytes(document.encode())
    manifest_path = completed / "RELEASE_MANIFEST.json"
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == manifest_path or "__pycache__" in path.parts:
            continue
        if path.suffix not in {".py", ".json", ".md", ".txt", ".npz", ".jsonl", ".csv", ".png", ".pdf", ".log"}:
            continue
        assert path.stat().st_size < 50_000_000
        files[path.relative_to(root).as_posix()] = {"sha256": sha(path), "bytes": path.stat().st_size}
    save(manifest_path, {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "scope": "Candidate 010 qualification release; excludes model weights, downloaded upstream source trees and HAI raw data.", "includes_derived_NAB_data": True, "includes_D1_A1_A2_licenses": True, "log_policy": "Includes only logs intentionally placed in this public candidate directory. Full cloud worker.log is not copied because it contains an operational private storage prefix.", "files": files})
    print(json.dumps({"qualification": summary["qualification"], "checks_passed": summary["audit_checks_passed"], "files": len(files), "total_bytes": sum(row["bytes"] for row in files.values())}))


if __name__ == "__main__":
    main()
