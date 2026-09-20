"""Post-pilot exploratory rule-family generalization; never an IID certificate."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import warnings

import joblib
import numpy as np

if __package__:
    from . import exploratory_benchmark as prior
    from .calibration import calibrate, apply_certificate
    from .feature_grouping import feature_group_sha, exact_feature_sha
    from .evidence_checker import evidence_view, evidence_group_sha, has_evidence, evidence_eligible, perturb, CONDITIONS
    from .scorers import LinearSVMScorer
else:
    import exploratory_benchmark as prior
    from calibration import calibrate, apply_certificate
    from feature_grouping import feature_group_sha, exact_feature_sha
    from evidence_checker import evidence_view, evidence_group_sha, has_evidence, evidence_eligible, perturb, CONDITIONS
    from scorers import LinearSVMScorer


RELEASE = "RELEASED_EXPLORATORY_RULE_GENERALIZATION"
FAMILY_GROUPING = "dual_view_duplicate_families_v1"
ROLES = prior.ROLES
REGIMES = ("content_families", "rule_components")
ARMS = ("KEEP_ALL", "FULL_ZERO_MARGIN", "EVIDENCE_ZERO_MARGIN", "FULL_PAC_SCORE_ONLY", "EVIDENCE_PAC_SCORE_ONLY", "CROSS_VIEW_GATE_PAC", "FULL_MATCHED_UTILITY", "FULL_MARGINAL_CRC")
GATE = {"max_attack_suppression": .01, "min_nonattack_suppression": .5,
        "min_attack_improvement": .01, "max_nonattack_loss": .05, "min_nonattack_improvement": .05,
        "comparators": ["FULL_PAC_SCORE_ONLY", "EVIDENCE_PAC_SCORE_ONLY"], "paired_quantiles": [.025, .975]}
SOURCE_FILES = ("generalization_benchmark.py", "evidence_checker.py", "exploratory_benchmark.py", "feature_grouping.py", "scorers.py", "calibration.py")


def build_family_splits(rows, held_ordinals, seed, regime="rule_components"):
    """Connect all source groups before excluding held/mixed content families.

    Base families connect full-view or meaningful evidence-view duplicates.
    Harder components additionally connect exact nonempty rule names. Removing
    held/mixed base families never splits an existing component or moves its role.
    """
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("Label") not in prior.LABELS:
            raise ValueError("Every source row requires the frozen binary label schema")
        groups[feature_group_sha(row)].append(i)
    held = set(held_ordinals)
    if any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(rows) for i in held):
        raise ValueError("Invalid held-review ordinal")
    if regime not in REGIMES:
        raise ValueError("Unknown split regime")
    full_groups = groups
    parents = {g: g for g in full_groups}

    def find(g):
        while parents[g] != g:
            parents[g] = parents[parents[g]]
            g = parents[g]
        return g

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[max(a, b)] = min(a, b)

    first_evidence = {}
    missing_evidence = []
    for g, indices in full_groups.items():
        for i in indices:
            if has_evidence(rows[i]):
                key = evidence_group_sha(rows[i])
                if key in first_evidence:
                    union(g, first_evidence[key])
                else:
                    first_evidence[key] = g
            else:
                missing_evidence.append(i)
    dual_connected = defaultdict(list)
    for g in full_groups:
        dual_connected[find(g)].append(g)
    groups, full_keys = {}, {}
    for keys in dual_connected.values():
        keys = sorted(keys)
        family = keys[0] if len(keys) == 1 else prior.sha_bytes(prior.canonical(keys))
        groups[family] = sorted(i for g in keys for i in full_groups[g])
        full_keys[family] = keys
    parents = {g: g for g in groups}
    first_rule = {}
    for g, indices in groups.items():
        for i in indices:
            rule = rows[i].get("rule_name")
            if regime == "rule_components" and isinstance(rule, str) and rule.strip():
                if rule in first_rule:
                    union(g, first_rule[rule])
                else:
                    first_rule[rule] = g
    connected = defaultdict(list)
    for g in groups:
        connected[find(g)].append(g)
    components, component_for_group = [], {}
    for keys in connected.values():
        keys = sorted(keys)
        component_id = keys[0] if regime == "content_families" else prior.sha_bytes(prior.canonical(keys))
        role = prior.split_role(component_id, seed)
        component = {"component_sha256": component_id, "role": role, "member_content_groups": keys,
                     "rule_names": sorted({rows[i]["rule_name"] for g in keys for i in groups[g]
                                           if isinstance(rows[i].get("rule_name"), str) and rows[i]["rule_name"].strip()})}
        components.append(component)
        for g in keys:
            component_for_group[g] = component
    retained, excluded = [], []
    for g, indices in groups.items():
        labels = {prior.LABELS[rows[i]["Label"]] for i in indices}
        reasons = []
        if len(labels) != 1:
            reasons.append("mixed_labels")
        if held.intersection(indices):
            reasons.append("held_human_review")
        component = component_for_group[g]
        record = {"group_sha256": g, "source_ordinals": indices,
                  "representative_ordinal": min(indices),
                  "full_view_group_sha256": full_keys[g],
                  "evidence_view_group_sha256": sorted({evidence_group_sha(rows[i]) for i in indices if has_evidence(rows[i])}),
                  "exact_feature_sha256": sorted({exact_feature_sha(rows[i]) for i in indices}),
                  "component_sha256": component["component_sha256"], "role": component["role"]}
        if reasons:
            excluded.append({**record, "reasons": reasons})
        else:
            retained.append({**record, "attack_label": labels.pop()})
    retained.sort(key=lambda g: g["representative_ordinal"])
    excluded.sort(key=lambda g: g["representative_ordinal"])
    components.sort(key=lambda c: c["component_sha256"])
    parts = {role: [g for g in retained if g["role"] == role] for role in ROLES}
    if set(g["attack_label"] for g in parts["fit"]) != {0, 1}:
        raise ValueError("The frozen fitting split lacks a class; no seed search is allowed")
    if not parts["test"]:
        raise ValueError("The frozen test split is empty; no seed search is allowed")
    summary = {
        "source_rows": len(rows), "normalized_full_view_groups": len(full_groups), "dual_view_duplicate_families": len(groups),
        "components_before_exclusions": len(components), "held_review_rows": len(held),
        "no_meaningful_evidence_rows": len(missing_evidence),
        "excluded_groups_union": len(excluded), "excluded_rows_union": sum(len(g["source_ordinals"]) for g in excluded),
        "exclusion_scope": "Dual-view duplicate families only; remaining rule-component members retain their fixed role",
        "exclusion_reason_counts": {reason: {"groups": sum(reason in g["reasons"] for g in excluded),
                                              "rows": sum(len(g["source_ordinals"]) for g in excluded if reason in g["reasons"])}
                                    for reason in ("mixed_labels", "held_human_review")},
        "retained_groups": len(retained), "retained_rows": sum(len(g["source_ordinals"]) for g in retained),
        "rule_components_are_not_verified_independent_incidents": True, "splits": {},
    }
    for role, selected in parts.items():
        summary["splits"][role] = {
            "components": len({g["component_sha256"] for g in selected}), "groups": len(selected),
            "rows": sum(len(g["source_ordinals"]) for g in selected),
            "attack_groups": sum(g["attack_label"] for g in selected),
            "nonattack_groups": sum(1 - g["attack_label"] for g in selected),
            "attack_rows": sum(g["attack_label"] * len(g["source_ordinals"]) for g in selected),
            "nonattack_rows": sum((1 - g["attack_label"]) * len(g["source_ordinals"]) for g in selected),
            "attack_bearing_components": len({g["component_sha256"] for g in selected if g["attack_label"]}),
            "nonattack_bearing_components": len({g["component_sha256"] for g in selected if not g["attack_label"]}),
        }
    return parts, {"components": components, "retained_groups": retained, "excluded_groups": excluded,
                   "no_meaningful_evidence_source_ordinals": sorted(missing_evidence)}, summary


def component_bootstrap(units, arms, repetitions, seed):
    """Resample whole rule components, preserving all their heterogeneous rows.

    units maps unit name to {labels, component_index, predictions: arm->mask}.
    Both primary representatives and secondary rows must use the same contiguous
    component indexing. Bands describe this finite empirical component sample.
    """
    if not units or repetitions < 1:
        raise ValueError("Invalid resampling request")
    component_sets, numerators, denominators = [], {}, {}
    for unit, data in units.items():
        y, ids = np.asarray(data["labels"]), np.asarray(data["component_index"])
        if y.ndim != 1 or ids.shape != y.shape or len(y) == 0 or not np.isin(y, [0, 1]).all() or ids.dtype.kind not in "iu":
            raise ValueError("Invalid component labels/indexing")
        unique = np.unique(ids)
        if not np.array_equal(unique, np.arange(len(unique))):
            raise ValueError("Components must use contiguous nonnegative indices")
        component_sets.append(unique)
        n_components = len(unique)
        for arm in arms:
            mask = np.asarray(data["predictions"][arm])
            if mask.shape != y.shape or mask.dtype.kind != "b":
                raise ValueError("Prediction arrays must be boolean and aligned")
            for label, metric in ((1, "attack_suppression_fraction"), (0, "nonattack_suppression_fraction")):
                key = f"{unit}__{arm}__{metric}"
                denominators[key] = np.bincount(ids, weights=(y == label).astype(int), minlength=n_components).astype(np.int64)
                numerators[key] = np.bincount(ids, weights=((y == label) & mask).astype(int), minlength=n_components).astype(np.int64)
    if any(not np.array_equal(component_sets[0], s) for s in component_sets[1:]):
        raise ValueError("All units must describe the same components")
    n_components = len(component_sets[0])
    draws = {key: np.full(repetitions, np.nan) for key in numerators}
    rng = np.random.default_rng(seed)
    for b in range(repetitions):
        frequency = np.bincount(rng.integers(0, n_components, size=n_components), minlength=n_components)
        for key in draws:
            numerator, denominator = int(frequency @ numerators[key]), int(frequency @ denominators[key])
            if denominator:
                draws[key][b] = numerator / denominator
    bands = {}
    for key, values in draws.items():
        finite = values[np.isfinite(values)]
        bands[key] = {"percentiles_2_5_and_97_5": None if len(finite) == 0 else np.quantile(finite, [.025, .975]).tolist(),
                      "defined_resamples": len(finite), "undefined_resamples": repetitions - len(finite)}
    return {"method": "whole-split-component resampling of the observed empirical test sample",
            "interpretation": "Descriptive percentile bands, not verified independent-incident or population confidence intervals. Undefined class denominators are counted; zero observed events can give degenerate bands.",
            "repetitions": repetitions, "seed": seed, "components": n_components, "bands": bands}, draws


def matched_utility_threshold(scores, labels, gate_suppressed):
    """Selection-only full-score threshold; no PAC property is claimed."""
    values, y, gated = np.asarray(scores, float), np.asarray(labels), np.asarray(gate_suppressed, bool)
    if values.ndim != 1 or y.shape != values.shape or gated.shape != values.shape or not np.isfinite(values).all():
        raise ValueError("Invalid utility-matching inputs")
    benign = np.sort(values[y == 0])
    target, n = int(np.sum(gated & (y == 0))), len(benign)
    if target == 0:
        threshold = {"kind": "positive_infinity", "value": None}
        achieved = 0
    elif target == n:
        threshold = {"kind": "negative_infinity", "value": None}
        achieved = n
    else:
        cutoff = float(benign[n - target - 1])
        threshold = {"kind": "finite", "value": cutoff}
        achieved = int(np.sum(benign > cutoff))
    return {"threshold": threshold, "selection_nonattack_examples": n,
            "target_nonattack_suppressed": target, "achieved_nonattack_suppressed": achieved,
            "tie_shortfall": target - achieved, "certificate_claim": False,
            "selection_rule": "Strict threshold gives at most target count; target zero keeps all; target all suppresses all finite scores"}


def above(scores, threshold):
    kind = threshold["kind"]
    if kind == "positive_infinity":
        return np.zeros(len(scores), dtype=bool)
    if kind == "negative_infinity":
        return np.ones(len(scores), dtype=bool)
    return np.asarray(scores) > threshold["value"]


def decide(data, frozen):
    full, evidence = data["full_scores"], data["evidence_scores"]
    return {
        "KEEP_ALL": np.zeros(len(full), dtype=bool), "FULL_ZERO_MARGIN": full > 0,
        "EVIDENCE_ZERO_MARGIN": evidence > 0,
        "FULL_PAC_SCORE_ONLY": apply_certificate(frozen["full_pac"], full),
        "EVIDENCE_PAC_SCORE_ONLY": apply_certificate(frozen["evidence_pac"], evidence),
        "CROSS_VIEW_GATE_PAC": apply_certificate(frozen["gate_pac"], full, data["checker_eligible"]),
        "FULL_MATCHED_UTILITY": above(full, frozen["matched_utility"]["threshold"]),
        "FULL_MARGINAL_CRC": above(full, frozen["full_marginal"]["threshold"]),
    }


def paired_comparisons(metrics, draws):
    answer = {}
    for unit in ("primary_representatives", "secondary_all_rows"):
        answer[unit] = {}
        for baseline in (*GATE["comparators"], "FULL_MATCHED_UTILITY"):
            changes = {}
            for metric in ("attack_suppression_fraction", "nonattack_suppression_fraction"):
                values = draws[f"{unit}__CROSS_VIEW_GATE_PAC__{metric}"] - draws[f"{unit}__{baseline}__{metric}"]
                finite = values[np.isfinite(values)]
                a, b = metrics[unit]["CROSS_VIEW_GATE_PAC"][metric], metrics[unit][baseline][metric]
                changes[metric] = {"gate_minus_baseline": None if a is None or b is None else a - b,
                                   "paired_percentiles_2_5_and_97_5": None if not len(finite) else np.quantile(finite, [.025, .975]).tolist(),
                                   "defined_resamples": len(finite)}
            answer[unit][baseline] = changes
    return answer


def practical_decision(hard_clean):
    metrics = hard_clean["suppression"]["primary_representatives"]
    paired = hard_clean["paired_gate_comparisons"]["primary_representatives"]
    gate = metrics["CROSS_VIEW_GATE_PAC"]
    attack, benign = gate["attack_suppression_fraction"], gate["nonattack_suppression_fraction"]
    guard = attack is not None and benign is not None and attack <= GATE["max_attack_suppression"] and benign >= GATE["min_nonattack_suppression"]
    routes = {"A_attack_improvement": {}, "B_utility_improvement": {}}
    for baseline in GATE["comparators"]:
        ba, bb = metrics[baseline]["attack_suppression_fraction"], metrics[baseline]["nonattack_suppression_fraction"]
        aci = paired[baseline]["attack_suppression_fraction"]["paired_percentiles_2_5_and_97_5"]
        bci = paired[baseline]["nonattack_suppression_fraction"]["paired_percentiles_2_5_and_97_5"]
        defined = None not in (attack, benign, ba, bb)
        routes["A_attack_improvement"][baseline] = bool(defined and aci is not None and attack <= ba - GATE["min_attack_improvement"] and benign >= bb - GATE["max_nonattack_loss"] and aci[1] < 0)
        routes["B_utility_improvement"][baseline] = bool(defined and bci is not None and benign >= bb + GATE["min_nonattack_improvement"] and attack <= ba and bci[0] > 0)
    route_pass = {name: all(comparisons.values()) for name, comparisons in routes.items()}
    passed = bool(guard and any(route_pass.values()))
    return {"status": "PRELIMINARY_PRACTICAL_GATE_PASS" if passed else "NO_GO_THIS_FIXED_CHECKER_COMPARISON",
            "passed": passed, "hard_clean_guard": bool(guard), "route_comparisons": routes, "same_route_against_both": route_pass,
            "criteria": GATE, "interpretation": "Post-pilot exploratory decision only; component bands are descriptive and not simultaneous population inference, operational certification or novelty evidence"}


def paired_condition_changes(outcomes, draws_by_condition):
    """Same test units and same component draws, with all thresholds unchanged."""
    result = {}
    for changed, reference in (("neutral", "clean"), ("directive", "clean"), ("directive", "neutral")):
        effects = {}
        for key in draws_by_condition[changed]:
            unit, arm, metric = key.split("__")
            samples = draws_by_condition[changed][key] - draws_by_condition[reference][key]
            finite = samples[np.isfinite(samples)]
            a = outcomes[changed]["suppression"][unit][arm][metric]
            b = outcomes[reference]["suppression"][unit][arm][metric]
            effects[key] = {"observed_change": None if a is None or b is None else a - b,
                            "paired_percentiles_2_5_and_97_5": None if not len(finite) else np.quantile(finite, [.025, .975]).tolist(),
                            "defined_resamples": len(finite)}
        result[f"{changed}_minus_{reference}"] = {
            "interpretation": "Paired fixed-model lexical-sensitivity diagnostic with identical component draws; not prompt-injection validation or a pass-gate criterion",
            "effects": effects}
    return result


def validate_and_freeze_inputs(source_path, protocol_path, audit_path):
    raw = source_path.read_bytes()
    spec, audit = json.loads(protocol_path.read_bytes()), json.loads(audit_path.read_bytes())
    required = {"release_status": RELEASE, "split_fractions": prior.FRACTIONS, "alpha": .01, "delta": .05,
                "bootstrap_repetitions": 10000, "grouping": FAMILY_GROUPING, "regimes": list(REGIMES),
                "conditions": list(CONDITIONS), "arms": list(ARMS)}
    if any(spec.get(k) != v for k, v in required.items()):
        raise ValueError("Protocol differs from the frozen generalization procedure")
    if any(spec.get("practical_gate", {}).get(k) != v for k, v in GATE.items()):
        raise ValueError("Protocol practical gate differs from the implementation")
    seed = spec.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2 ** 32 - 1:
        raise ValueError("Invalid frozen seed")
    source_hash, audit_hash = prior.sha_bytes(raw), prior.sha_bytes(audit_path.read_bytes())
    if source_hash != prior.EXPECTED_SOURCE_SHA256 or source_hash != spec.get("expected_source_sha256"):
        raise ValueError("Source hash mismatch")
    if audit_hash != spec.get("expected_audit_sha256") or audit.get("source_sha256") != source_hash:
        raise ValueError("Held-review audit hash/source mismatch")
    if LinearSVMScorer(seed).metadata()["config_sha256"] != spec.get("scorer_config_sha256"):
        raise ValueError("Frozen SVM recipe mismatch")
    rows = json.loads(raw)
    if not isinstance(rows, list) or not all(isinstance(r, dict) and r.get("Label") in prior.LABELS for r in rows):
        raise ValueError("Invalid source schema")
    sample = audit.get("sample", [])
    if len(sample) != 50 or audit.get("human_review", {}).get("cases") != 50:
        raise ValueError("Expected 50 reserved review cases")
    held = []
    for case in sample:
        i = case["source_row_zero_based"]
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(rows):
            raise ValueError("Invalid review ordinal")
        content = prior.sha_bytes(prior.canonical({k: v for k, v in rows[i].items() if k != "Label"}))
        if content != case["input_content_sha256"] or prior.sha_bytes(f"{i}|{content}".encode()) != case["case_id"]:
            raise ValueError("Review identity/content mismatch")
        held.append(i)
    if len(set(held)) != 50:
        raise ValueError("Duplicate review ordinal")
    return rows, held, spec, {"source_sha256": source_hash, "audit_sha256": audit_hash, "protocol_sha256": prior.sha_bytes(protocol_path.read_bytes())}


def committed_inputs(protocol_path):
    root = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    hashes = {}
    for path in [Path(__file__).with_name(name) for name in SOURCE_FILES] + [protocol_path]:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError("Protocol must be inside the committed repository")
        name = path.relative_to(root).as_posix()
        frozen = subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{name}"])
        if path.read_bytes() != frozen:
            raise ValueError(f"Uncommitted operative file: {name}")
        hashes[name] = prior.sha_bytes(frozen)
    return {"git_commit": commit, "committed_file_sha256": hashes}


def run(source, protocol, audit, private_output, output):
    source, protocol, audit, private, public = [Path(p).resolve() for p in (source, protocol, audit, private_output, output)]
    repo = Path(__file__).resolve().parents[2]
    if private.exists() or public.exists():
        raise ValueError("Outputs must be new; preserve previous attempts")
    if private.is_relative_to(repo) or private.is_relative_to(public) or public.is_relative_to(private):
        raise ValueError("Private output must be outside the repository and public tree")
    rows, held, spec, bindings = validate_and_freeze_inputs(source, protocol, audit)
    provenance = committed_inputs(protocol)
    layouts = {regime: build_family_splits(rows, held, spec["seed"], regime) for regime in REGIMES}
    private.mkdir(parents=True)
    public.mkdir(parents=True)
    started, memory_start = time.perf_counter(), prior.peak_memory()
    states, freeze_regimes, normal_diagnostics, timing = {}, {}, {}, {}

    def score_rows(models, indices, condition, destination):
        values = {key: [] for key in ("full_scores", "evidence_scores", "has_evidence", "checker_eligible", "full_latency_seconds", "evidence_latency_seconds")}
        for i in indices:
            alert = perturb(rows[i], condition)
            before = time.perf_counter()
            full = float(models["full"].score([alert])[0])
            full_time = time.perf_counter() - before
            before = time.perf_counter()
            evidence = float(models["evidence"].score([evidence_view(alert)])[0])
            evidence_time = time.perf_counter() - before
            if not np.isfinite([full, evidence]).all():
                raise ValueError("Invalid score; no results may be accepted")
            for key, value in (("full_scores", full), ("evidence_scores", evidence), ("full_latency_seconds", full_time), ("evidence_latency_seconds", evidence_time), ("has_evidence", has_evidence(alert)), ("checker_eligible", evidence_eligible(alert, evidence))):
                values[key].append(value)
        values = {key: np.asarray(value, dtype=bool if key in {"has_evidence", "checker_eligible"} else float) for key, value in values.items()}
        values["source_ordinals"] = np.asarray(indices, dtype=np.int64)
        values["labels"] = np.asarray([prior.LABELS[rows[i]["Label"]] for i in indices], dtype=np.int8)
        np.savez_compressed(destination, **values)
        return values

    # Both regimes finish fitting/selection/calibration before any test scoring.
    for regime in REGIMES:
        parts, manifest, summary = layouts[regime]
        folder = private / regime
        folder.mkdir()
        prior.write_json(folder / "SPLIT_MANIFEST.json", manifest)
        models, model_records = {}, {}
        fit_indices = [g["representative_ordinal"] for g in parts["fit"]]
        fit_labels = [g["attack_label"] for g in parts["fit"]]
        timing[regime] = {"fit": {}, "scoring": {}}
        for view in ("full", "evidence"):
            model = LinearSVMScorer(seed=spec["seed"])
            alerts = [rows[i] if view == "full" else evidence_view(rows[i]) for i in fit_indices]
            before = time.perf_counter()
            with warnings.catch_warnings(record=True) as seen:
                warnings.simplefilter("always")
                model.fit(alerts, fit_labels, split_role="fit")
            timing[regime]["fit"][view] = time.perf_counter() - before
            joblib.dump(model, folder / f"MODEL_{view}.joblib")
            models[view] = model
            model_records[view] = {"metadata": model.metadata(), "view": view,
                                   "fit_warnings": [{"category": w.category.__name__, "message": str(w.message)} for w in seen],
                                   "artifact_sha256": prior.sha_bytes((folder / f"MODEL_{view}.joblib").read_bytes())}
        scored, diagnostics = {}, {}
        for role in ("fit", "selection", "calibration"):
            before = time.perf_counter()
            data = score_rows(models, [g["representative_ordinal"] for g in parts[role]], "clean", folder / f"SCORES_{role}.npz")
            timing[regime]["scoring"][role] = time.perf_counter() - before
            scored[role] = data
            diagnostics[role] = {view: prior.classifier_metrics(data["labels"], data[f"{view}_scores"]) for view in ("full", "evidence")}
        cal = scored["calibration"]
        positive = cal["labels"] == 1
        metadata = {**bindings, "regime": regime, "scope": "EXPLORATORY_FORMULA_NO_OPERATIONAL_CERTIFICATION",
                    "calibration_artifact_sha256": prior.sha_bytes((folder / "SCORES_calibration.npz").read_bytes())}
        full_pac = calibrate(cal["full_scores"][positive], alpha=.01, delta=.05, metadata={**metadata, "view": "full"}).to_dict()
        evidence_pac = calibrate(cal["evidence_scores"][positive], alpha=.01, delta=.05, metadata={**metadata, "view": "evidence"}).to_dict()
        gate_pac = calibrate(cal["full_scores"][positive], cal["checker_eligible"][positive], alpha=.01, delta=.05, metadata={**metadata, "view": "full_with_evidence_eligibility"}).to_dict()
        selection = scored["selection"]
        gate_selection = apply_certificate(gate_pac, selection["full_scores"], selection["checker_eligible"])
        frozen = {"models": model_records, "full_pac": full_pac, "evidence_pac": evidence_pac, "gate_pac": gate_pac,
                  "full_marginal": prior.marginal_calibrate(cal["full_scores"][positive], .01),
                  "matched_utility": matched_utility_threshold(selection["full_scores"], selection["labels"], gate_selection),
                  "split_summary": summary, "split_manifest_sha256": prior.sha_bytes((folder / "SPLIT_MANIFEST.json").read_bytes()),
                  "selection_role": "Used only for the preregistered utility-matched comparator; no model/seed/feature selection",
                  "calibration_attack_representatives": int(positive.sum()),
                  "calibration_attack_bearing_components": summary["splits"]["calibration"]["attack_bearing_components"]}
        freeze_regimes[regime], states[regime], normal_diagnostics[regime] = frozen, models, diagnostics
    freeze = {"status": "BOTH_REGIMES_FROZEN_BEFORE_ANY_TEST_SCORING", "created_utc": datetime.now(timezone.utc).isoformat(),
              **bindings, **provenance, "regimes": freeze_regimes, "operational_certification": False,
              "multiplicity": "Separate formula calibrations; no joint PAC guarantee across arms, regimes or shifts"}
    prior.write_json(public / "GLOBAL_CALIBRATION_FREEZE.json", freeze)
    outcomes = {}
    for regime in REGIMES:
        parts, _, summary = layouts[regime]
        test_groups = parts["test"]
        indices = [i for g in test_groups for i in g["source_ordinals"]]
        counts = np.asarray([len(g["source_ordinals"]) for g in test_groups])
        representative_positions = np.r_[0, np.cumsum(counts)[:-1]]
        component_keys = sorted({g["component_sha256"] for g in test_groups})
        component_map = {key: i for i, key in enumerate(component_keys)}
        representative_components = np.asarray([component_map[g["component_sha256"]] for g in test_groups])
        row_components = np.repeat(representative_components, counts)
        outcomes[regime] = {"split_summary": summary, "normal_diagnostics": normal_diagnostics[regime], "conditions": {}}
        clean, condition_draws = None, {}
        for condition in CONDITIONS:
            folder = private / regime / condition
            folder.mkdir()
            before = time.perf_counter()
            data = score_rows(states[regime], indices, condition, folder / "SCORES.npz")
            timing[regime]["scoring"][f"test_{condition}"] = time.perf_counter() - before
            chosen = decide(data, freeze_regimes[regime])
            np.savez_compressed(folder / "PREDICTIONS.npz", **data, representative_positions=representative_positions,
                                component_index=row_components, **chosen)
            units = {
                "primary_representatives": {"labels": data["labels"][representative_positions], "component_index": representative_components,
                                            "predictions": {a: p[representative_positions] for a, p in chosen.items()}},
                "secondary_all_rows": {"labels": data["labels"], "component_index": row_components, "predictions": chosen},
            }
            metrics = {unit: {arm: prior.suppression_metrics(values["labels"], values["predictions"][arm]) for arm in ARMS} for unit, values in units.items()}
            bootstrap, draws = component_bootstrap(units, ARMS, spec["bootstrap_repetitions"], spec["seed"])
            bootstrap["component_definition"] = "dual-view duplicate family" if regime == "content_families" else "connected exact-rule-name and dual-view duplicate families"
            np.savez_compressed(folder / "BOOTSTRAP_DRAWS.npz", **draws)
            condition_draws[condition] = draws
            if condition == "clean":
                clean = data
            classifier = {unit: {view: prior.classifier_metrics(data["labels"][positions], data[f"{view}_scores"][positions]) for view in ("full", "evidence")}
                          for unit, positions in (("primary_representatives", representative_positions), ("secondary_all_rows", np.arange(len(indices))))}
            outcomes[regime]["conditions"][condition] = {
                "classifier": classifier, "suppression": metrics, "bootstrap": bootstrap,
                "paired_gate_comparisons": paired_comparisons(metrics, draws),
                "observed_evidence": {"rows_with_evidence": int(data["has_evidence"].sum()), "checker_eligible_rows": int(data["checker_eligible"].sum()),
                                      "missing_to_present_since_clean": int(np.sum(~clean["has_evidence"] & data["has_evidence"])),
                                      "present_to_missing_since_clean": int(np.sum(clean["has_evidence"] & ~data["has_evidence"])),
                                      "eligibility_false_to_true_since_clean": int(np.sum(~clean["checker_eligible"] & data["checker_eligible"])),
                                      "eligibility_true_to_false_since_clean": int(np.sum(clean["checker_eligible"] & ~data["checker_eligible"]))},
                "latency_seconds": {view: None if not len(indices) else {"mean": float(data[f"{view}_latency_seconds"].mean()), "median": float(np.median(data[f"{view}_latency_seconds"])), "p95": float(np.quantile(data[f"{view}_latency_seconds"], .95))} for view in ("full", "evidence")},
            }
        outcomes[regime]["paired_condition_changes"] = paired_condition_changes(outcomes[regime]["conditions"], condition_draws)
    result = {"status": "COMPLETED_POST_PILOT_EXPLORATORY_GENERALIZATION", "created_utc": datetime.now(timezone.utc).isoformat(),
              **bindings, **provenance, "operational_certification": False, "human_review_completed": False, "novelty_claim": False,
              "regimes": outcomes, "practical_decision": practical_decision(outcomes["rule_components"]["conditions"]["clean"]),
              "global_freeze_sha256": prior.sha_bytes((public / "GLOBAL_CALIBRATION_FREEZE.json").read_bytes()),
              "timing": timing, "elapsed_seconds": time.perf_counter() - started,
              "memory": {"before_fit_process_peak": memory_start, "final_process_peak": prior.peak_memory()},
              "private_artifacts": {p.relative_to(private).as_posix(): {"sha256": prior.sha_bytes(p.read_bytes()), "bytes": p.stat().st_size} for p in sorted(private.rglob("*")) if p.is_file()},
              "limitations": ["Designed after observing the prior pilot; this is a stress test, not pristine independent confirmation.",
                              "Both-view duplicate closure and rule separation do not prove incident independence or future SOC generalization.",
                              "Attack representatives, not independent rule components, supply the formula sample size; no deployment certificate is claimed.",
                              "The evidence view is a projection of the same processed alert, not independent raw authority.",
                              "Neutral/directive header additions measure SVM lexical sensitivity. They are not successful LLM prompt injection, real attacker validation or evidence of source-log provenance.",
                              "Missingness and eligibility use the observed perturbed record; appended text can create eligibility and those flips are reported.",
                              "Human labels, study terms and full G0 remain unresolved. Component bootstrap bands are descriptive and do not imply simultaneous population inference."]}
    prior.write_json(public / "RESULTS.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "protocol", "audit", "private-output", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.protocol, args.audit, args.private_output, args.output)
    print(json.dumps({"status": result["status"], "practical_decision": result["practical_decision"]}, indent=2))
