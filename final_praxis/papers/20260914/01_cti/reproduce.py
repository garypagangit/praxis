"""Offline CTI statistical reproduction. Python >=3.10; standard library only.

No network, inference, or candidate-code execution. Frozen functions are imported
unchanged. --bootstrap all regenerates every interval; primary regenerates the
14 declared principal intervals; none explicitly uses archived bootstrap bounds.
Every mode recomputes all counts, Wilson intervals, paired cells, exact p values,
Holm adjustments, and gate arithmetic. Athena inputs are derived indicators.
"""
from __future__ import annotations
import argparse
import ast
import gzip
import hashlib
import json
import platform
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "frozen"))
from scripts import analyze_px003_confirmatory as common
from scripts import analyze_px003_full_2500 as cti
from scripts import analyze_px068_source_router as router


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_inputs(root=ROOT):
    records = load_json(root / "PROVENANCE.json")["artifacts"]
    for rec in records:
        path = root / rec["file"]
        raw = path.read_bytes()
        if digest(raw) != rec["sha256"] or len(raw) != rec["bytes"]:
            raise ValueError("Package hash/length mismatch: " + rec["file"])
        if "uncompressed_sha256" in rec:
            unpacked = gzip.decompress(raw)
            if digest(unpacked) != rec["uncompressed_sha256"] or len(unpacked) != rec["uncompressed_bytes"]:
                raise ValueError("Uncompressed hash/length mismatch: " + rec["file"])
    return len(records)


def load_rows(name):
    with gzip.open(ROOT / "data" / name, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def frozen_parser():
    """Extract only the pure parser, without executing the inference runner."""
    path = ROOT / "frozen/inference/run_sec_lord_relationship_evidence_cloud.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "strict_parse")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {"re": re}
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    return namespace["strict_parse"]


def validate_cti(rows, expected_conditions, parse):
    indexed = common.index_predictions(rows)
    if len(indexed) != 2500 or any(set(v) != set(expected_conditions) for v in indexed.values()):
        raise ValueError("Missing or unexpected CTIBench assignment")
    cti.validate_strata(rows)
    strata = Counter(next(iter(v.values()))["dataset_stratum"] for v in indexed.values())
    if strata != {cti.ATTACK_STRATUM: 1578, cti.MISMATCH_STRATUM: 922}:
        raise ValueError("CTIBench stratum inventory differs")
    for row in rows:
        parsed = parse(row["raw_output"])
        if parsed != row["parsed_answer"] or type(row["correct"]) is not bool:
            raise ValueError("CTIBench parser/boolean mismatch: " + str(row["id"]))
        if row["correct"] != (parsed == row["expected_output"]):
            raise ValueError("CTIBench correctness mismatch: " + str(row["id"]))
    return indexed


def validate_derived(rows):
    indexed = common.index_predictions(rows)
    if len(indexed) != 2997 or any(set(v) != set(router.POLICIES) for v in indexed.values()):
        raise ValueError("Missing or unexpected Athena derived assignment")
    for row_id, policies in indexed.items():
        first = policies["vanilla"]
        for row in policies.values():
            for key in ("correct", "eligible", "legacy_valid", "intended_ae_valid", "route_relationship_evidence"):
                if type(row[key]) is not bool:
                    raise ValueError("Non-boolean derived indicator: " + row_id)
            for key in ("eligible", "route_relationship_evidence", "source_type", "attack_path_type"):
                if row[key] != first[key]:
                    raise ValueError("Inconsistent derived task metadata: " + row_id)
        for policy, selected in (("routed_policy", "relationship_evidence" if first["route_relationship_evidence"] else "vanilla"),
                                 ("oracle_policy", "relationship_evidence" if first["eligible"] else "vanilla")):
            for key in ("correct", "legacy_valid", "intended_ae_valid"):
                if policies[policy][key] != policies[selected][key]:
                    raise ValueError("Derived policy selection mismatch: " + row_id)
    if sum(v["vanilla"]["eligible"] for v in indexed.values()) != 998:
        raise ValueError("Athena eligibility inventory differs")
    return indexed


def interval_registry(cti_report, px_report):
    registry = {}
    primary = set()
    def add(namespace, contrast, is_primary):
        seed = common.deterministic_seed(namespace, contrast["treatment"], contrast["control"])
        if seed in registry:
            raise ValueError("Unexpected bootstrap seed collision")
        registry[seed] = contrast["paired_bootstrap_ci95"]
        if is_primary:
            primary.add(seed)
    for model, record in cti_report["models"].items():
        for cell in ("source_pointer", "query_only"):
            for scope, payload in [("all_2500", record[cell]["intention_to_treat"]), *record[cell]["strata"].items()]:
                for row in payload["comparisons"]:
                    selected = ((cell == "source_pointer" and scope == cti.ATTACK_STRATUM and row["control"] in ("vanilla", "technique_only_evidence"))
                                or (cell == "query_only" and scope in (cti.ATTACK_STRATUM, cti.MISMATCH_STRATUM)))
                    add(f"{model}:{cell}:{scope}", row, selected)
    suffixes = {"routed_vs_vanilla": "routed-vs-vanilla", "routed_vs_ungated": "routed-vs-ungated", "oracle_vs_vanilla_diagnostic": "oracle-vs-vanilla"}
    for model, record in px_report["models"].items():
        for scope, payload in record["scopes"].items():
            for name, row in payload["comparisons"].items():
                selected = (scope, name) in (("all_primary", "routed_vs_vanilla"), ("eligible", "routed_vs_vanilla"), ("ineligible", "routed_vs_ungated"))
                add(f"px068:{model}:{scope}:{suffixes[name]}", row, selected)
    return registry, primary


def semantic_payload(value):
    """Only archive file-location metadata is omitted from statistical equality."""
    if isinstance(value, dict):
        return {k: semantic_payload(v) for k, v in value.items()
                if k not in {"predictions_path", "prediction_path", "prediction_sha256"}}
    if isinstance(value, list):
        return [semantic_payload(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", choices=("none", "primary", "all"), default="none")
    parser.add_argument("--output", type=Path, default=ROOT / "reproduction_output")
    args = parser.parse_args()
    started = time.time()
    verified = verify_inputs()
    archived_cti = load_json(ROOT / "evidence/FULL_2500_ANALYSIS.json")
    archived_px = load_json(ROOT / "evidence/PX068_ANALYSIS.json")
    registry, primary_seeds = interval_registry(archived_cti, archived_px)
    original_bootstrap = common.bootstrap_paired_difference
    recomputed, inherited = [], []
    def bootstrap(differences, replicates, seed):
        if seed not in registry or replicates != 20000:
            raise ValueError("Unregistered bootstrap request")
        if args.bootstrap == "all" or (args.bootstrap == "primary" and seed in primary_seeds):
            result = list(original_bootstrap(differences, replicates, seed))
            if result != registry[seed]:
                raise ValueError("Bootstrap result differs for seed " + str(seed))
            recomputed.append(seed)
            print(f"Bootstrap verified {len(recomputed)}; n={len(differences)}", flush=True)
            return tuple(result)
        inherited.append(seed)
        return tuple(registry[seed])
    common.bootstrap_paired_difference = bootstrap
    parse = frozen_parser()
    data, cells = {}, {}
    for model in ("Llama", "Qwen"):
        cells[model] = {}
        data[model] = {}
        for cell, controls in (("source_pointer", cti.SOURCE_CONTROLS), ("query_only", cti.QUERY_CONTROLS)):
            name = f"full2500_{model.lower()}_{cell}.jsonl.gz"
            rows = load_rows(name)
            data[model][cell] = validate_cti(rows, (cti.TREATMENT, *controls), parse)
            cells[model][cell] = {
                "model": model, "cell": cell,
                "predictions_sha256": digest(gzip.decompress((ROOT / "data" / name).read_bytes())),
                "prediction_rows": len(rows),
                "intention_to_treat": cti.analyze_rows(rows, model, cell, "all_2500", controls, 20000),
                "strata": {s: cti.analyze_rows([r for r in rows if r["dataset_stratum"] == s], model, cell, s, controls, 20000)
                           for s in (cti.ATTACK_STRATUM, cti.MISMATCH_STRATUM)}}
    cti.add_cross_model_query_holm([r["query_only"] for r in cells.values()])
    for model, record in cells.items():
        source, query = record["source_pointer"], record["query_only"]
        gates = cti.evaluate_gates(source, query)
        gates["query_main"] = gates["query_main_pre_cross_model_holm"] and cti.comparison(query["strata"][cti.ATTACK_STRATUM], "vanilla")["cross_model_holm_p"] < .05
        record["gates"] = gates
        pair = data[model]
        parsed_matches = sum(pair["source_pointer"][i]["vanilla"]["parsed_answer"] == pair["query_only"][i]["vanilla"]["parsed_answer"] for i in pair["source_pointer"])
        correct_matches = sum(pair["source_pointer"][i]["vanilla"]["correct"] == pair["query_only"][i]["vanilla"]["correct"] for i in pair["source_pointer"])
        record["duplicate_vanilla_concordance"] = {"rows": 2500, "parsed_answer_matches": parsed_matches, "parsed_answer_match_rate": parsed_matches / 2500,
            "correctness_matches": correct_matches, "correctness_match_rate": correct_matches / 2500,
            "interpretation": "execution reproducibility diagnostic; not a treatment-effect gate"}
    source_keys = ("source_main", "source_relationship_specificity", "source_negative_controls", "source_invalid_safety", "source_mismatch_invalid_safety")
    full_keys = (*source_keys, "query_main", "query_mismatch_noninferiority", "query_attack_invalid_safety", "query_mismatch_invalid_safety")
    source_pass = all(all(r["gates"][k] for k in source_keys) for r in cells.values())
    full_pass = all(all(r["gates"][k] for k in full_keys) for r in cells.values())
    cti_result = {"analysis_version": "px003-px034-full-2500-v1", "bootstrap_replicates": 20000,
                  "portfolio_status": "PASS_FULL_SOURCE_AND_QUERY_CONFIRMATION" if full_pass else "PASS_SOURCE_KNOWN_ONLY" if source_pass else "FAIL_PREREGISTERED_CONFIRMATION", "models": cells}
    px_models, validity, router_record = {}, {}, None
    for short, model in (("llama", "llama-3-1-8b-instruct"), ("qwen", "qwen2-5-7b-instruct")):
        rows = load_rows(f"px068_{short}_derived.jsonl.gz")
        indexed = validate_derived(rows)
        truth = {i: {"eligible": v["vanilla"]["eligible"]} for i, v in indexed.items()}
        assignments = {i: {"route_relationship_evidence": v["vanilla"]["route_relationship_evidence"]} for i, v in indexed.items()}
        metrics = router.router_metrics(truth, assignments)
        if router_record is not None and metrics != router_record:
            raise ValueError("Router assignments differ between model projections")
        router_record = metrics
        # Internal sentinel values encode already observed legacy validity only.
        # They are not reconstructed Athena answers. Explicit correct overrides
        # label equality in the frozen statistical functions.
        adapted = [dict(r, parsed_answer="A" if r["legacy_valid"] else "", expected_output="A") for r in rows]
        px_models[model] = {"oracle_policy_is_diagnostic_only": True, "primary_gate_scopes": list(router.PRIMARY_GATE_SCOPES),
            "source_and_attack_path_subgroups_are_descriptive": True,
            "scopes": {scope: router.analyze_scope(adapted, model, scope, 20000) for scope in router.registered_scope_names(adapted)}}
        validity[model] = {policy: {"rows": 2997,
            "legacy_invalid": sum(not r["legacy_valid"] for r in rows if r["condition"] == policy),
            "intended_ae_invalid": sum(not r["intended_ae_valid"] for r in rows if r["condition"] == policy)} for policy in router.POLICIES}
    for scope, contrast in (("all_primary", "routed_vs_vanilla"), ("eligible", "routed_vs_vanilla"), ("ineligible", "routed_vs_ungated")):
        router.add_cross_model_holm(px_models, scope, contrast)
    router_pass = router.router_gate(router_record)
    for r in px_models.values():
        # Historic upstream integrity is preserved as a reported archived gate;
        # package hashes/derived-row integrity are newly verified above.
        r["gates"] = router.evaluate_model_gates(r, True, router_pass)
    px_result = {"analysis_version": "px068-source-compatibility-router-v1", "bootstrap_replicates": 20000,
        "portfolio_status": router.portfolio_status(px_models), "router_metrics": router_record, "router_gate_pass": router_pass,
        "oracle_policy_role": "diagnostic_upper_bound_only_not_a_confirmatory_gate", "models": px_models}
    cti_equal = semantic_payload(cti_result) == semantic_payload(archived_cti)
    px_equal = semantic_payload(px_result) == semantic_payload(archived_px)
    complete_intervals = len(recomputed) + len(inherited) == len(registry)
    receipt = {"status": "PASS" if cti_equal and px_equal and complete_intervals else "FAIL", "python": platform.python_version(),
        "bootstrap_mode": args.bootstrap, "bootstrap_replicates": 20000, "bootstrap_intervals_recomputed": len(recomputed),
        "bootstrap_intervals_explicitly_taken_from_archive": len(inherited), "all_bootstrap_requests_accounted": complete_intervals,
        "full2500_statistical_payload_equal": cti_equal, "px068_statistical_payload_equal": px_equal,
        "all_nonbootstrap_statistics_recomputed": True, "archived_files_hash_verified": verified,
        "cti_raw_parser_and_correctness_rows_verified": 40000, "cti_unique_questions": 2500,
        "athena_derived_policy_rows_verified": 23976, "athena_unique_questions": 2997,
        "athena_raw_text_or_answers_redistributed": False, "athena_correctness_from_raw_independently_recomputed": False,
        "new_inference_calls": 0, "network_calls": 0, "frozen_code_modified": False,
        "implementation_independence_claimed": False, "cti_status": cti_result["portfolio_status"], "px068_status": px_result["portfolio_status"],
        "limits": "Statistical reproduction of archived observations, not independent model replication, benchmark-label validation, or causal mechanism identification. Athena raw-to-indicator derivation is authenticated by source hashes and terminal audit, not rerun from restricted raw corpus here.",
        "runtime_seconds": round(time.time() - started, 3), "reproduce_sha256": digest(Path(__file__).read_bytes())}
    args.output.mkdir(parents=True, exist_ok=True)
    for name, payload in (("FULL_2500_REPRODUCED.json", cti_result), ("PX068_REPRODUCED.json", px_result), ("PX068_VALIDITY_DIAGNOSTIC.json", validity), ("REPRODUCTION_RECEIPT.json", receipt)):
        (args.output / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2), flush=True)
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
