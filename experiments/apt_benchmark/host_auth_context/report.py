"""Publish aggregate authentication-context results; never fit or select models."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics


SEEDS = [20260922, 20260923, 20260924]
CLASSES = ["Benign", "OtherAttackStage", "LateralMovement", "DataExfiltration"]
PRIOR = ["current", "current_roles", "current_history", "current_roles_history", "current_roles_wrong_host_history", "roles_only"]
NEW = ["current_availability", "context_availability", "current_auth", "context_auth", "context_wrong_auth", "auth_availability_only", "availability_only"]
ARMS = ["prior_" + a for a in PRIOR] + NEW
POLICIES = ["calibration_f1__global"] + [f"tail_{b}__{v}" for b in ["0.001", "0.005", "0.01", "0.02"] for v in ["global", "role_tail"]]
LABELS = {
    "prior_current": "Prior current flow",
    "prior_current_roles": "Prior flow + roles",
    "prior_current_history": "Prior flow + flow history",
    "prior_current_roles_history": "Prior flow + roles + flow history",
    "prior_current_roles_wrong_host_history": "Prior flow + roles + wrong-host flow history",
    "prior_roles_only": "Prior roles only",
    "current_availability": "Flow + log-volume/timing controls",
    "context_availability": "Flow/role/history + log-volume/timing controls",
    "current_auth": "Flow + controls + auth types/outcomes",
    "context_auth": "Flow/role/history + controls + auth types/outcomes",
    "context_wrong_auth": "Flow/role/history + controls + wrong-host auth",
    "auth_availability_only": "Log controls + auth only",
    "availability_only": "Log-volume/timing controls only",
}
PAIRS = [
    ("current_auth", "current_availability", "Authentication types/outcomes beyond current flow and log controls"),
    ("context_auth", "context_availability", "Authentication types/outcomes beyond flow/role/history and log controls"),
    ("context_auth", "context_wrong_auth", "Correct-host versus wrong-host authentication"),
    ("current_availability", "prior_current", "Observed-log volume/timing and availability beyond current flow"),
    ("context_availability", "prior_current_roles_history", "Observed-log volume/timing and availability beyond prior context"),
]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def average(items):
    """Mean numeric measurements; require identical structural/null/boolean facts."""
    if not items:
        raise ValueError("Cannot average no observations")
    first = items[0]
    if isinstance(first, dict):
        if any(not isinstance(v, dict) or set(v) != set(first) for v in items):
            raise ValueError("Inconsistent metric keys")
        return {k: average([v[k] for v in items]) for k in first}
    if isinstance(first, list):
        if any(not isinstance(v, list) or len(v) != len(first) for v in items):
            raise ValueError("Inconsistent metric dimensions")
        return [average([v[i] for v in items]) for i in range(len(first))]
    if first is None or isinstance(first, (str, bool)):
        if any(type(v) is not type(first) or v != first for v in items):
            raise ValueError("Inconsistent structural metric")
        return first
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in items):
        raise ValueError("Non-numeric measurement")
    return float(statistics.mean(items))


def validate_run(run):
    complete = read(run / "COMPLETE.json")
    for filename, key in [("SUMMARY.json", "summary_sha256"), ("STARTED.json", "started_sha256")]:
        if complete.get(key) != sha(run / filename):
            raise ValueError("Root completion hash mismatch: " + filename)
    summary = read(run / "SUMMARY.json")
    if [s["seed"] for s in summary["seeds"]] != SEEDS:
        raise ValueError("All three ordered seeds required")
    if summary["receipt"].get("mode") != "auth_fits_and_replay" or summary["receipt"].get("models_fitted") != 21:
        raise ValueError("Full authentication run of 21 new fits required")
    if summary["receipt"].get("saved_prediction_arms_replayed") != 18:
        raise ValueError("All 18 prior probability arms must be replayed")
    started = read(run / "STARTED.json")
    for key, value in started.items():
        if summary["receipt"].get(key) != value:
            raise ValueError("Start/summary receipt mismatch")
    cell_hashes = {}
    for cell in summary["seeds"]:
        seed = cell["seed"]
        directory = run / str(seed)
        receipt = read(directory / "COMPLETE.json")
        files = receipt.get("files", {})
        expected = {"PREDICTIONS.npz", "METRICS.json"} | {name + ".joblib" for name in NEW}
        if set(files) != expected:
            raise ValueError("Incomplete or unexpected cell artifact roster")
        for filename, digest in files.items():
            if Path(filename).name != filename or sha(directory / filename) != digest:
                raise ValueError("Cell artifact hash mismatch")
        if read(directory / "METRICS.json") != cell:
            raise ValueError("Seed summary differs from completed metrics")
        if set(cell["arms"]) != set(ARMS):
            raise ValueError("All 13 arms required")
        for arm in cell["arms"].values():
            if set(arm["decisions"]["policies"]) != set(POLICIES):
                raise ValueError("All nine fixed policies required")
            if set(arm["stage"]["per_class"]) != set(CLASSES):
                raise ValueError("Class roster mismatch")
            if "7" not in arm["role_strata"]:
                raise ValueError("Missing destination-role-shift stratum")
            for policy in arm["decisions"]["policies"].values():
                if policy["all_test"]["retained_baseline_alerts"] is not True:
                    raise ValueError("Policy failed its baseline-alert retention invariant")
        cell_hashes[str(seed)] = sha(directory / "COMPLETE.json")
    return summary, cell_hashes


def stage_values(m):
    e = m["per_class"]["DataExfiltration"]
    l = m["per_class"]["LateralMovement"]
    n = m["per_class"]["Benign"]["support"]
    return {"macro_f1": m["macro_f1_all_four"], "exfil_ap": e["ap"], "exfil_f1": e["f1"],
            "exfil_precision": e["precision"], "exfil_recall": e["recall"],
            "movement_exact_recall": l["recall"], "movement_any_attack_recall": m["lateral_any_attack_recall"],
            "benign_false_attack_count": m["benign_false_attack_count"],
            "benign_false_attack_rate": m["benign_false_attack_count"] / n if n else None}


def contrasts(summary):
    out = []
    for a, b, purpose in PAIRS:
        for population in ["all_test", "role_7"]:
            per_seed = []
            for cell in summary["seeds"]:
                get = lambda name: cell["arms"][name]["stage"] if population == "all_test" else cell["arms"][name]["role_strata"]["7"]
                va, vb = stage_values(get(a)), stage_values(get(b))
                delta = {k: va[k] - vb[k] if va[k] is not None and vb[k] is not None else None for k in va}
                per_seed.append({"seed": cell["seed"], "delta": delta})
            out.append({"candidate": a, "reference": b, "purpose": purpose, "population": population,
                        "mean_delta": average([d["delta"] for d in per_seed]), "per_seed": per_seed})
    return out


def pct(value):
    return "N/A" if value is None else f"{100 * value:.2f}%"


def num(value, places=4):
    return "N/A" if value is None else f"{value:.{places}f}"


def policy_name(key):
    if key == "calibration_f1__global":
        return "Calibration-F1 / global"
    budget, variant = key.removeprefix("tail_").split("__")
    return pct(float(budget)) + " calibration tail / " + ("global" if variant == "global" else "role-conditioned")


def stage_table(means, accessor):
    lines = ["| Arm | Macro-F1 | Exfil AP | Exfil P | Exfil R | Exfil F1 | Movement exact R | Movement any-attack R | Benign false attacks |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name in ARMS:
        v = stage_values(accessor(means[name]))
        lines.append(f"| {LABELS[name]} | {num(v['macro_f1'])} | {num(v['exfil_ap'])} | {pct(v['exfil_precision'])} | {pct(v['exfil_recall'])} | {num(v['exfil_f1'])} | {pct(v['movement_exact_recall'])} | {pct(v['movement_any_attack_recall'])} | {num(v['benign_false_attack_count'], 2)} |")
    return lines


def policy_report(means):
    lines = ["# Every frozen policy: raw flags, automatic labels and review costs", "",
             "Mean of three fits on the identical test rows. All 13 arms and all nine policies are retained. Counts can be fractional because they average repeated fits; they are not additional independent events.", "",
             "Each policy keeps the original current-flow model's movement flag and baseline attack queue, then adds the named arm's exfiltration flag. Both target flags mean unresolved review. An exfiltration flag in an insufficiently supported role group is also unresolved. Automatic exfiltration requires an exfiltration flag, no baseline movement flag and sufficient role support.", "",
             "Review union = baseline any-attack OR candidate exfiltration. It includes already resolved baseline attack alerts and is therefore a workload queue, not just abstentions. Unsupported and both-flag counts can overlap and must not be added. The union retains baseline alerts by construction; this is not improved model recall.", "",
             "The role-conditioned tail uses group-specific negative scores where at least 100 non-exfiltration calibration rows exist, otherwise the global threshold. Automatic exfiltration additionally requires at least 20 exfiltration and 100 non-exfiltration calibration rows. Neither support counts nor nominal tails certify safety; movement is absent from calibration.", ""]
    for population in ["all_test", "role_7"]:
        lines += ["## " + ("All test rows" if population == "all_test" else "Department → private services (role 7)"), ""]
        for policy in POLICIES:
            lines += ["### " + policy_name(policy), "",
                      "| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|"]
            rows = {}
            for name in ARMS:
                p = means[name]["decisions"]["policies"][policy]
                m = p["all_test"] if population == "all_test" else p["role_strata"]["7"]
                rows[name] = m
                e, f = m["exfil_flag"], m["exfil_flag"]["false_exfil_by_true_class"]
                lines.append(f"| {LABELS[name]} | {pct(e['precision'])} | {pct(e['recall'])} | {num(e['f1'])} | {num(f['Benign'],2)} | {num(f['OtherAttackStage'],2)} | {num(f['LateralMovement'],2)} | {num(e['tp'],2)} |")
            lines += ["", "| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
            for name, m in rows.items():
                e, by = m["automatic_exfil"], m["by_true_class"]
                total = lambda key: sum(v[key] for v in by.values())
                lines.append(f"| {LABELS[name]} | {pct(e['precision'])} | {pct(e['recall'])} | {num(e['f1'])} | {num(total('both_flags'),2)} | {num(total('unsupported_exfil_review'),2)} | {num(total('unresolved_review'),2)} | {num(m['review_union_count'],2)} / {num(m['review_union_benign_count'],2)} | {num(m['additional_review_count'],2)} |")
            lines += ["", "| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |",
                      "|---|---:|---:|---:|---:|---:|"]
            for name, m in rows.items():
                l, e = m["by_true_class"]["LateralMovement"], m["by_true_class"]["DataExfiltration"]
                lines.append(f"| {LABELS[name]} | {num(l['movement_flag'],2)} | {num(l['resolved_movement_only'],2)} | {num(l['unresolved_review'],2)} | {num(l['any_review'],2)} | {num(e['unresolved_review'],2)} |")
            lines.append("")
    return "\n".join(lines)


def report(evidence):
    means = evidence["means"]
    counts = means[ARMS[0]]["stage"]["per_class"]
    lines = ["# Does earlier authentication help distinguish movement from exfiltration?", "",
             f"**Completed development comparison: 21 new fits plus 18 saved probability-arm replays. Independent calculation audit: {evidence['audit']['status']}.** Three fitting seeds share the same later-period observations from one exposed UNRAVELED campaign and IT sensor.", "",
             "Authentication histories, host roles, temporal context and fusion have direct prior art. This study tests incremental information and error costs; it does not establish a new algorithm. See the [novelty review](../../host_auth_context/NOVELTY_REVIEW.md) and [fixed design](../../host_auth_context/DESIGN.md).", "",
             "## What was measured", "",
             "All seven new arms use the same prior fixed LightGBM settings and fitting identities; six earlier network-only arms are evaluated from saved probabilities. No result chooses a new preferred model or threshold. The log controls include **observed-log volume/timing and availability**, so the matched authentication contrast measures additional event-type/outcome information beyond those controls, not merely access to event counts.", "",
             "| Test author class | Rows |", "|---|---:|"]
    for name in CLASSES:
        lines.append(f"| {name} | {int(counts[name]['support']):,} |")
    lines += ["", "Movement labels in this sensor describe Remote System Discovery on one host pair; they are not independent verified successful logins. Exfiltration labels are author progress annotations, not content-confirmed theft. Earlier host events are source-side context, not proof of successful outgoing authentication to an unmonitored destination.", "",
              "## Stage classification: every arm", "",
              "Four-class argmax decisions; P = precision, R = recall, AP = average precision. Exact movement recall requires the movement label; any-attack recall also counts a different attack label. Normal false attacks and exfiltration false labels have different meanings. Values are arithmetic means of per-fit metrics, not metrics pooled across replicated events.", ""]
    lines += stage_table(means, lambda m: m["stage"])
    lines += ["", "## Paired component comparisons", "",
              "Candidate minus reference. AP/F1 deltas use their original 0–1 scale; recall deltas are percentage points. All declared auth and log-control contrasts are shown, including wrong-host auth. No significance or independent-campaign confidence claim is made.", "",
              "| Candidate − reference | Population | Δ exfil AP | Δ exfil F1 | Δ movement exact R (pp) | Δ movement any R (pp) | Δ benign false attacks |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for row in evidence["contrasts"]:
        d = row["mean_delta"]
        delta = lambda v, scale=1: "N/A" if v is None else f"{v*scale:+.4f}"
        lines.append(f"| {LABELS[row['candidate']]} − {LABELS[row['reference']]} | {row['population']} | {delta(d['exfil_ap'])} | {delta(d['exfil_f1'])} | {delta(d['movement_exact_recall'],100)} | {delta(d['movement_any_attack_recall'],100)} | {delta(d['benign_false_attack_count'])} |")
    lines += ["", "## Destination-role shift: department → private services", "",
              "Role code 7 has no fitting/calibration exfiltration examples. This is a later observed destination-role change, not a new independent campaign or a test of all unseen roles. All movement flows and the shifted exfiltration group still have different source-host associations. Reported macro-F1 includes all four classes even when a stratum has no support for one class.", ""]
    lines += stage_table(means, lambda m: m["role_strata"]["7"])
    role = means[ARMS[0]]["role_strata"]["7"]
    lines += ["", "Role-7 denominators: " + ", ".join(f"{int(role['per_class'][c]['support']):,} {c}" for c in CLASSES) + ".",
              f"Its target-pair exfiltration prevalence is {pct(role['exfil_vs_lateral_exfil_prevalence'])}; a high pairwise AP can therefore be weak evidence. All pairwise APs, full confusions, captures and other role groups remain in EVIDENCE.json.", "",
              "## Source-host diagnostics", "",
              "These are published laboratory source addresses, used only to report strata. Literal source identities are excluded from model inputs. Within-host reporting cannot remove all time, operating-system or collection confounding. The sole movement source prevents an independent unseen-source movement evaluation.", ""]
    for host in means[ARMS[0]]["by_source_host"]:
        m = means[ARMS[0]]["by_source_host"][host]
        lines += [f"### Source {host}", "", ", ".join(f"{int(m['per_class'][c]['support']):,} {c}" for c in CLASSES) + ".", ""]
        lines += stage_table(means, lambda item, host=host: item["by_source_host"][host])
        lines.append("")
    lines += ["## Exfiltration policies and review workload", "",
              "The complete [policy tables](POLICIES.md) include every arm, calibration-F1 global cutoff and all four nominal tails (0.1%, 0.5%, 1%, 2%) under global and role-conditioned decisions. They separate raw flags, false labels by true class, automatic exfiltration, both flags, insufficient-support reviews, total review queue and added benign work. EVIDENCE.json retains every seed, threshold and class-specific routing count.", "",
              "All policies retain the prior current-flow model's attack alerts mechanically. Their movement flag is also copied from that baseline. Retaining an alert in a union queue does not repair stage classification or guarantee movement detection. Role 7 lacks calibration exfiltration support: flagged cases are marked for review, and an unsupported review is not a correct automatic label. Movement is absent from calibration globally, so no threshold has a calibrated movement-error guarantee.", "",
              "## Interpretation boundaries", "",
              "- This is already exposed development data from one campaign; fitting seeds do not create independent attacks.",
              "- All fitted arms must be read with the volume/timing, availability-only and wrong-host controls. More information can identify a host or time regime instead of distinguishing attack semantics.",
              "- Histories are strictly earlier by the qualified event clock. Unmeasured collection latency remains unresolved, and completed-flow statistics prevent a live early-warning claim.",
              "- Exfiltration AP improvement alone is insufficient if exact stage precision/recall or movement recognition deteriorates. Binary any-attack detection is a separate endpoint.",
              "- Abstention moves work to review. Precision among automatic outputs must be read alongside coverage, unresolved attacks and benign reviews; a smaller queue of decided cases can conceal difficult cases.",
              "- A PASS calculation audit checks source/output binding and arithmetic, not human adjudication, attack truth, peer review or external deployment validity.", "",
              "## Bound artifacts", "",
              "[EVIDENCE.json](EVIDENCE.json) includes all mean and per-seed aggregate outcomes and paired contrasts. [PUBLICATION.json](PUBLICATION.json) binds the public files and source-summary hash. Private arrays and model files are retained in the experiment workspace and are not copied here.", ""]
    if evidence["audit"]["status"] == "PENDING":
        lines += ["**Calculation audit is pending. Treat these as completed runner outputs awaiting independent verification.**", ""]
    else:
        lines += ["[AUDIT.json](AUDIT.json) contains the bound independent calculation audit.", ""]
    return "\n".join(lines)


def publish(run, output, audit_path=None):
    summary, cell_hashes = validate_run(run)
    summary_hash = sha(run / "SUMMARY.json")
    audit = None
    audit_status = "PENDING"
    if audit_path is not None:
        audit = read(audit_path)
        if (audit.get("audit_status") != "PASS" or audit.get("run_status") != "COMPLETE"
                or audit.get("artifact_hashes", {}).get("SUMMARY.json") != summary_hash
                or audit.get("models_audited") != 21
                or audit.get("prediction_arms_audited") != 39
                or audit.get("policies_per_arm") != 9):
            raise ValueError("Audit must PASS and bind this source summary")
        audit_status = "PASS"
    evidence = {
        "status": "COMPLETE_RUNNER_OUTPUTS" if audit_status == "PENDING" else "COMPLETE_AUDITED",
        "scope": "One exposed UNRAVELED campaign, same IT sensor and later-flow development partition; author stage annotations",
        "source_summary_sha256": summary_hash, "source_complete_sha256": sha(run / "COMPLETE.json"),
        "source_cell_complete_sha256": cell_hashes,
        "protocol_sha256": summary["receipt"]["protocol_sha256"],
        "receipt": summary["receipt"], "audit": {"status": audit_status, "source_summary_sha256": summary_hash},
        "seeds": summary["seeds"], "arms": ARMS, "policies": POLICIES,
        "means": average([cell["arms"] for cell in summary["seeds"]]),
        "contrasts": contrasts(summary),
        "direction_note": "Positive AP/F1/recall deltas favor the candidate; positive false-alert counts indicate greater burden. No pass/fail or winner selection."
    }
    output.mkdir(parents=True, exist_ok=True)
    allowed = {"REPORT.md", "EVIDENCE.json", "POLICIES.md", "PUBLICATION.json", "AUDIT.json"}
    if any(p.name not in allowed or not p.is_file() for p in output.iterdir()):
        raise ValueError("Output contains unrelated files")
    if (output / "PUBLICATION.json").exists():
        previous = read(output / "PUBLICATION.json")
        if previous["source_summary_sha256"] != summary_hash:
            raise ValueError("Cannot overwrite publication from another scientific run")
        if previous.get("audit_status") == "PASS" and audit_status != "PASS":
            raise ValueError("Cannot downgrade audited publication")
    write(output / "EVIDENCE.json", evidence)
    (output / "REPORT.md").write_text(report(evidence), encoding="utf-8")
    (output / "POLICIES.md").write_text(policy_report(evidence["means"]), encoding="utf-8")
    if audit_path is not None:
        write(output / "AUDIT.json", audit)
    write(output / "PUBLICATION.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(), "reporter_sha256": sha(__file__),
        "source_summary_sha256": summary_hash, "source_complete_sha256": sha(run / "COMPLETE.json"),
        "audit_status": audit_status,
        "artifacts": {p.name: sha(p) for p in output.iterdir() if p.is_file() and p.name != "PUBLICATION.json"},
        "content": "Aggregate metrics, public lab-host strata and artifact hashes only; no fitted models or raw prediction/event arrays"
    })
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    evidence = publish(args.run, args.output, args.audit)
    print(json.dumps({"status": evidence["status"], "arms": len(ARMS), "seeds": len(SEEDS), "policies_per_arm": len(POLICIES)}))


if __name__ == "__main__":
    main()
