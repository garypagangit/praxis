"""Fail-closed paper-development readiness from exact local evidence receipts.

No inference, candidate execution, statistics recomputation, or AWS operation.
The caller supplies the coordinator-released receipt paths. Readiness means the
bounded empirical result is documented and technically closed; scientific
support, primary-Praxis investment, novelty and publication are separate.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path

HOSTS = {"i-07178e293e8df2a60", "i-039ed976444ade397"}
REVIEWERS = {"qwen.qwen3-coder-next", "mistral.devstral-2-123b"}
VERSIONS = {"original": "original_v1", "extension": "schema_extension_v2"}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value, expected):
    return type(value) is type(expected) and value == expected


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def same_money(a, b):
    return number(a) and number(b) and math.isclose(a, b, rel_tol=0, abs_tol=1e-8)


def timestamp(value):
    need(isinstance(value, str), "Explicit timestamp missing")
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(result.tzinfo is not None, "Timestamp must identify its timezone")
    return result.astimezone(dt.timezone.utc)


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, "Duplicate JSON key: " + key)
            out[key] = value
        return out
    def bad_constant(value):
        raise ValueError("Nonfinite JSON value: " + value)
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=bad_constant)


def child(root, relative):
    need(isinstance(relative, str) and relative, "Nonempty relative artifact name required")
    path = (root / relative).resolve()
    need(path.is_relative_to(root.resolve()) and path != root.resolve(), "Artifact escapes its declared directory")
    return path


class Evidence:
    def __init__(self):
        self.checks, self.files, self.payloads = [], {}, {}

    def read(self, path):
        path = Path(path).resolve()
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        key = str(path)
        need(key not in self.files or self.files[key]["sha256"] == digest, "Evidence changed while reading: " + key)
        self.files[key] = {"sha256": digest, "bytes": len(raw)}
        return raw

    def json(self, path):
        value = strict_json(self.read(path))
        need(isinstance(value, dict), "Receipt must be a JSON object: " + str(path))
        return value

    def sha(self, path):
        return hashlib.sha256(self.read(path)).hexdigest()

    def check(self, name, function):
        try:
            detail = function()
            self.checks.append({"check": name, "passed": True, "detail": detail or "Verified"})
            return True
        except (OSError, ValueError, KeyError, TypeError, IndexError, EOFError) as error:
            self.checks.append({"check": name, "passed": False, "detail": type(error).__name__ + ": " + str(error)})
            return False


def completed_counts(receipt, failed_key=None):
    total, passed = receipt.get("checks_total"), receipt.get("checks_passed")
    need(type(total) is int and type(passed) is int and total > 0 and passed == total,
         "Positive completed checks_total must equal literal integer checks_passed")
    if failed_key is not None:
        need(exact(receipt.get(failed_key), 0), "Explicit zero failed checks required")


def inspect_package(evidence, root, version):
    manifest = evidence.json(root / "PACKAGE_RECEIPT.json")
    need(manifest.get("version") == version, "Wrong result package version")
    need(manifest.get("results_edited") is False and exact(manifest.get("new_inference_calls"), 0),
         "Public packaging must preserve results and make no inference calls")
    listed = {}
    for item in manifest["artifacts"]:
        name = item["file"]
        need(name not in listed, "Duplicate packaged artifact")
        raw = evidence.read(child(root, name))
        need(hashlib.sha256(raw).hexdigest() == item["sha256"], "Package artifact hash mismatch: " + name)
        need(type(item["bytes"]) is int and len(raw) == item["bytes"], "Packaged byte count mismatch")
        uncompressed = gzip.decompress(raw) if name.endswith(".gz") else raw
        need(hashlib.sha256(uncompressed).hexdigest() == item["uncompressed_source_sha256"], "Uncompressed source hash mismatch: " + name)
        listed[name] = item
    required = {"MODEL_RESULTS.json", "ACQUISITION_RESULTS.json", "FLOW_AND_COSTS.json", "RESULTS_RECEIPT.json", "budget.json",
                "DECISIONS.jsonl.gz", "EXPECTED_DECISIONS.jsonl.gz", "OFFLINE.jsonl.gz", "EXPECTED_OFFLINE.jsonl.gz"}
    need(required <= set(listed), "Required public reproduction artifacts missing")
    report = evidence.json(root / "RESULTS_RECEIPT.json")
    for name in ("MODEL_RESULTS.json", "ACQUISITION_RESULTS.json", "FLOW_AND_COSTS.json", "DECISIONS.jsonl", "EXPECTED_DECISIONS.jsonl", "OFFLINE.jsonl", "EXPECTED_OFFLINE.jsonl"):
        packaged = name if name.endswith(".json") else name + ".gz"
        need(report["artifacts_sha256"][name] == listed[packaged]["uncompressed_source_sha256"], "Package is not the exact audited result: " + name)
    return {"root": root, "manifest": manifest, "result_receipt": report,
            "flow": evidence.json(root / "FLOW_AND_COSTS.json"), "model": evidence.json(root / "MODEL_RESULTS.json"),
            "acquisition": evidence.json(root / "ACQUISITION_RESULTS.json"), "budget": evidence.json(root / "budget.json"),
            "manifest_sha256": evidence.sha(root / "PACKAGE_RECEIPT.json"), "result_sha256": evidence.sha(root / "RESULTS_RECEIPT.json")}


def assess(paths, now=None):
    """Paths are explicit receipt locations; never substitutes a missing phase."""
    paths = {name: Path(value).resolve() for name, value in paths.items()}
    now = now or dt.datetime.now(dt.timezone.utc)
    e, state = Evidence(), {"packages": {}, "audits": {}, "reproductions": {}, "costs": {}, "end_times": {}}
    assessor_hash = e.sha(Path(__file__))

    def source_freezes():
        core = paths["core"]
        original = e.json(core / "MODEL_SOURCE_FREEZE.json")
        extension = e.json(core / "technical_extension/EXTENSION_SOURCE_FREEZE.json")
        need(extension["core_source_freeze_sha256"] == e.sha(core / "MODEL_SOURCE_FREEZE.json"), "V2 does not bind original source freeze")
        need(exact(original["main_study_model_calls_before_freeze"], 0) and original["main_policy_results_inspected_before_freeze"] is False,
             "Original preexecution freeze declaration missing")
        need(exact(extension["extension_model_calls_before_freeze"], 0) and extension["heldout_scientific_outcomes_inspected_before_freeze"] is False,
             "Extension prospective access declaration missing")
        for root, freeze, required in ((core, original, {"analysis.py", "offline_analysis.py", "MODEL_STUDY_PREREG.md"}),
                                      (core / "technical_extension", extension, {"PREREG_V2.md", "adapter.py", "run_extension.py"})):
            need(required <= set(freeze["files"]), "Incomplete source-freeze manifest")
            for relative, wanted in freeze["files"].items():
                need(e.sha(child(root, relative)) == wanted, "Frozen source mismatch: " + relative)
        need(e.sha(core / "MODEL_STUDY_PREREG.md") == original["protocol_sha256"], "V1 protocol mismatch")
        need(e.sha(core / "technical_extension/PREREG_V2.md") == extension["protocol_sha256"], "V2 protocol mismatch")
        state.update(core_freeze=original, extension_freeze=extension,
                     core_freeze_sha=e.sha(core / "MODEL_SOURCE_FREEZE.json"), extension_freeze_sha=e.sha(core / "technical_extension/EXTENSION_SOURCE_FREEZE.json"))
        return "Original and extension frozen source bytes and prospective declarations verified"
    e.check("frozen_sources_and_version_lineage", source_freezes)

    def qualification():
        audit = e.json(paths["qualification_audit"])
        completed_counts(audit)
        need(audit.get("errors") == [] and audit.get("decision") == "GO_SEPARATELY_FROZEN_POLICY_STUDY", "Qualification audit did not approve the fixed cohort")
        need(exact(audit.get("all164_retained"), 164) and exact(audit.get("assigned_tasks"), 164), "Qualification lost assigned source tasks")
        need(type(audit.get("eligible_pairs")) is int and audit["eligible_pairs"] >= 100 and type(audit.get("eligible_heldout_pairs")) is int and audit["eligible_heldout_pairs"] >= 60,
             "Qualification cohort is below frozen minimum")
        freeze = state["core_freeze"]
        need(e.sha(paths["qualification_audit"]) == freeze["full_qualification_audit_sha256"], "Qualification audit differs from model freeze")
        need(e.sha(paths["qualification_receipt"]) == freeze["qualification_receipt_sha256"] == audit["results_receipt_sha256"], "Qualification result receipt differs")
        state["qualification"] = {k: audit[k] for k in ("assigned_tasks", "eligible_pairs", "eligible_heldout_pairs")}
        control = e.json(paths["generated_review"])
        completed_counts(control)
        need(exact(control.get("checks_total"), 31) and exact(control.get("checks_passed"), 31), "Frozen generated coordinator review requires all 31 controls")
        need(control.get("control_source_sha256") == freeze["files"]["review/generated_controls.py"], "Generated coordinator review does not bind frozen control source")
        need(e.sha(paths["generated_review"]) == e.sha(paths["core"] / "review/GENERATED_COORDINATOR_REVIEW.json"), "Supplied generated review differs from committed receipt")
        need(control.get("passed") is True and isinstance(control.get("checks"), dict) and len(control["checks"]) == control["checks_total"]
             and all(value is True for value in control["checks"].values()), "Generated-execution coordinator controls incomplete or failed")
        return "Qualification and generated-execution controls passed; recorded exclusions remain exclusions"
    e.check("qualification_and_coordinator_audit", qualification)

    for phase, version in VERSIONS.items():
        def package(phase=phase, version=version):
            value = inspect_package(e, paths[phase + "_package"], version)
            expected = state["core_freeze" if phase == "original" else "extension_freeze"]["protocol_sha256"]
            need(value["result_receipt"]["protocol_sha256"] == expected, "Packaged result uses another protocol")
            state["packages"][phase] = value
            return "All packaged bytes, compressed source identities and required statistical inputs match"
        e.check(phase + "_public_package_integrity", package)

        def audit(phase=phase):
            value = e.json(paths[phase + "_audit"])
            completed_counts(value, "checks_failed")
            need(value.get("audit_complete") is True and value.get("integrity_pass") is True and value.get("auditor_file_unchanged_during_run") is True,
                 "Artifact audit is incomplete, failed or its source changed")
            need(value.get("failures") == [], "Artifact audit has failure records")
            need(isinstance(value.get("warnings"), list) and not any("Static selection replay was skipped" in str(x) for x in value["warnings"]), "Complete selector replay is required")
            need(value.get("configuration") == ("original_v1" if phase == "original" else "extension_v2_with_explicit_v1_reuse"), "Wrong artifact audit configuration")
            package = state["packages"][phase]
            need(value["protocol_sha256"] == package["result_receipt"]["protocol_sha256"], "Audit protocol differs from package")
            counts = value["counters"]
            for key, wanted in (("source_tasks",164),("review_jobs",9456),("review_records",9456),("generated_proposals",328),("offline_rows",131200)):
                need(exact(counts.get(key), wanted), "Audit assignment count missing/wrong: " + key)
            need(counts.get("results_receipt_sha256") == package["result_sha256"] and counts.get("protocol_sha256") == value["protocol_sha256"], "Audit not bound to these exact results")
            if phase == "extension":
                need(counts.get("original_artifact_audit_sha256") == e.sha(paths["original_audit"]), "Extension does not bind the supplied original audit")
                need(counts.get("extension_source_freeze_sha256") == state["extension_freeze_sha"], "Extension audit source-freeze mismatch")
                need(exact(counts.get("warmup_observations_in_experimental_denominators"), 0), "Warmup contaminated experiment denominators")
            state["audits"][phase] = value
            return "Complete passing artifact audit binds this package; every planned identity is retained"
        e.check(phase + "_independent_artifact_audit", audit)

        def reproduction(phase=phase, version=version):
            value = e.json(paths[phase + "_reproduction"])
            for key in ("pass", "model_all_statistics_exact", "acquisition_all_statistics_exact", "comparison_excludes_only_top_level_provenance"):
                need(value.get(key) is True, "Reproduction missing literal true: " + key)
            need(value.get("version") == version and value.get("package_receipt_sha256") == state["packages"][phase]["manifest_sha256"], "Reproduction is for another package")
            need(value.get("source_freeze_sha256") == state["core_freeze_sha"], "Reproduction source freeze differs")
            need(value.get("reproducer_sha256") == e.sha(paths["core"] / "paper_package/reproduce_statistics.py"), "Reproducer source differs")
            need(exact(value.get("bootstrap_draws_per_registered_analysis"), 5000) and exact(value.get("api_calls"), 0) and exact(value.get("candidate_programs_executed"), 0), "Unexpected reproduction procedure or resource use")
            state["reproductions"][phase] = value
            return "All statistical payload fields reproduced exactly, including registered bootstrap draws"
        e.check(phase + "_public_statistical_reproduction", reproduction)

        def process_and_flow(phase=phase):
            value = e.json(paths[phase + "_process"])
            need(value.get("status") == "finished" and value.get("phase") == "complete", "Model run process has not completed")
            if phase == "original":
                need(exact(value.get("exit_code"), 0) and exact(value.get("durable_decision_receipts"),9456), "Original process exit/record count invalid")
                ended = timestamp(value.get("ended_utc"))
            else:
                need(value.get("failure", "missing") is None and exact(value.get("durable_decision_records"),9456), "Extension failure/record count invalid")
                ended = timestamp(value.get("utc"))
            need(exact(value.get("expected_review_assignments"),9456), "Process assigned universe differs")
            need(ended <= now, "Process completion timestamp is in the future")
            package = state["packages"][phase]
            need(any(item["file"] == paths[phase + "_process"].name and item["sha256"] == e.sha(paths[phase + "_process"])
                     for item in package["manifest"]["artifacts"]), "Completed process receipt is not bound to this package")
            flow = package["flow"]
            for key, wanted in (("review_assignments",9456),("review_records",9456),("source_tasks",164),("generated_proposals",328),("proposal_directions_assigned",656),("offline_assigned_rows",131200),("offline_rows",131200)):
                need(exact(flow.get(key),wanted), "Final flow assignment mismatch: " + key)
            need(flow.get("experiment_processing_accounted") is True and flow.get("missing_review_record_ids") == [], "Final assignment flow is incomplete")
            statuses = flow.get("model_status_counts")
            need(isinstance(statuses,dict) and all(type(n) is int and n >= 0 for n in statuses.values()) and sum(statuses.values()) == 9456, "Model-status accounting must total all assignments")
            state["end_times"][phase] = ended
            return "Completed process and all assignments accounted, including any explicit technical-stop placeholders"
        e.check(phase + "_completed_process_and_assignment_flow", process_and_flow)

        def budget(phase=phase):
            package = state["packages"][phase]
            ledger, flow = package["budget"], package["flow"]
            need(number(ledger.get("limit_usd")) and ledger["limit_usd"] == 30 and isinstance(ledger.get("entries"),dict), "Phase ledger must retain $30 limit and entries")
            amounts = [row.get("accounted_usd") for row in ledger["entries"].values()]
            need(amounts and all(number(x) for x in amounts), "Phase ledger empty or has invalid/nonfinite/negative cost")
            amount = math.fsum(amounts)
            need(amount <= 30 and flow.get("within_frozen_api_ledger") is True and number(flow.get("api_budget_limit_usd")) and flow["api_budget_limit_usd"] == 30,
                 "Phase exceeds or misstates frozen budget")
            need(same_money(amount, flow.get("accounted_api_usd_estimate")), "Ledger sum and flow cost differ")
            need(same_money(amount, state["audits"][phase]["counters"].get("accounted_api_usd_estimate")), "Independent audit cost and ledger sum differ")
            need(flow.get("invoice_claimed") is False, "API estimate must not be represented as invoice")
            state["costs"][phase] = amount
            return "Ledger independently summed: $" + format(amount, ".8f") + " estimated API use"
        e.check(phase + "_api_ledger_within_limit", budget)

    def numerical_errata():
        audit = state["audits"]["extension"]
        warnings = [x for x in audit["warnings"] if str(x).startswith("NUMERICAL ERRATUM ")]
        if not warnings:
            return "No numerical erratum reported by the supplied completed audit"
        need(len(warnings) == 1, "Every numerical erratum requires an explicit supported correction")
        value = e.json(paths["core"] / "postrun_review/roundoff_amendment/NUMERICAL_ERRATUM.json")
        package = state["packages"]["extension"]
        need(value.get("results_receipt_sha256") == package["result_sha256"], "Erratum is for another result package")
        need(value.get("frozen_offline_source_sha256") == state["core_freeze"]["files"]["offline_analysis.py"], "Erratum is for another frozen analysis")
        need(type(value.get("exact_rational_effect")) is float and value["exact_rational_effect"] == 0,
             "Documented correction must state the exact zero")
        need(type(value.get("frozen_sorted_float_effect")) is float and 0 < value["frozen_sorted_float_effect"] < 1e-12,
             "Only the documented zero-roundoff discrepancy is resolved here")
        for key in ("corrected_static_edit_directional_benefit", "primary_hypotheses_changed",
                    "overall_offline_recommendation_changed", "archive_or_frozen_source_modified"):
            need(value.get(key) is False, "Erratum correction/scope differs: " + key)
        original = e.json(paths["core"] / "postrun_review/roundoff_amendment/INITIAL_ARTIFACT_AUDIT.json")
        need(e.sha(paths["core"] / "postrun_review/roundoff_amendment/INITIAL_ARTIFACT_AUDIT.json") == value["initial_audit_sha256"],
             "Initial failed audit not retained exactly")
        need(exact(original.get("checks_failed"),1) and original.get("integrity_pass") is False,
             "Initial single-discrepancy failed audit required")
        need(value["comparison"] in package["acquisition"]["comparisons"] and value["original_gate"] in package["acquisition"]["recommendation_gates"],
             "Erratum does not bind the exact archived comparison and gate")
        group = tuple(value["comparison"]["group"][key] for key in ("split","cohort","proposer","intent","direction","budget"))
        need(group == ("heldout","generated","qwen.qwen3-coder-next","adversarial_corruption","harmful",4),
             "A different secondary stratum needs its own correction review")
        expected_warning = "NUMERICAL ERRATUM " + repr(group) + ": " + json.dumps(
            {"static_edit_directional_benefit":{"exact_arithmetic":False,"archived_machine":True}},sort_keys=True)
        expected_warning += "; exact edit-minus-hybrid=" + repr(value["exact_rational_effect"])
        expected_warning += ", frozen float=" + repr(value["frozen_sorted_float_effect"])
        expected_warning += ". An exact zero is no directional benefit; preserve archived bytes and report the correction."
        need(warnings == [expected_warning], "Audit numerical warning differs from the exact disclosed correction")
        state["numerical_errata"] = {"correction": "Secondary static-edit directional benefit is false: exact effect is zero.",
            "primary_hypotheses_changed":False,"original_result_preserved":True,
            "receipt_sha256":e.sha(paths["core"] / "postrun_review/roundoff_amendment/NUMERICAL_ERRATUM.json")}
        return "Disclosed secondary roundoff correction bound to immutable results and retained initial failed audit; no primary result changes"
    e.check("disclosed_numerical_errata_bound_to_results", numerical_errata)

    def closeout():
        value = e.json(paths["cloud_closeout"])
        need(value.get("host_states") == {host: "stopped" for host in HOSTS}, "Both exact campaign hosts must be verified stopped")
        verified = timestamp(value.get("verified_utc"))
        need(len(state["end_times"]) == 2 and max(state["end_times"].values()) <= verified <= now, "Shutdown receipt predates completed model runs or lies in future")
        need(exact(value.get("new_inference_calls_after_closeout"),0) and value.get("invoice_claimed") is False, "Closeout must declare no later inference and no invoice claim")
        original, extension = state["costs"]["original"], state["costs"]["extension"]
        combined = original + extension
        need(combined <= 60, "Combined API estimate exceeds $60")
        for key,wanted in (("api_original_usd_estimate",original),("api_extension_usd_estimate",extension),("combined_api_usd_estimate",combined)):
            need(same_money(value.get(key),wanted), "Closeout cost does not match separate ledgers: " + key)
        host, total = value.get("host_compute_usd_upper_estimate"), value.get("total_incremental_usd_upper_estimate")
        need(number(host) and number(total) and total >= combined + host - 1e-8 and total <= 100, "Total incremental upper estimate is inconsistent or exceeds $100")
        state["closeout"] = value
        return "Both named hosts stopped after processing; separate/combined API and total incremental estimates within limits"
    e.check("current_cloud_shutdown_and_combined_cost", closeout)

    def stable_inputs():
        for path, item in list(e.files.items()):
            need(hashlib.sha256(Path(path).read_bytes()).hexdigest() == item["sha256"], "Receipt changed during readiness assessment: " + path)
        return "All captured evidence bytes remained unchanged"
    e.check("input_receipts_unchanged_during_assessment", stable_inputs)

    scientific = {}
    for phase, package in state["packages"].items():
        scientific[phase] = {"primary_hypotheses": package["model"].get("primary_hypotheses", []),
            "model_policy_gates": package["model"].get("policy_gates", []),
            "offline_primary_gates": [g for g in package["acquisition"].get("recommendation_gates", []) if g.get("primary_stratum") is True],
            "technical_gates": package["flow"].get("technical_gates", {}),
            "eligible_reviews_all_completed": package["flow"].get("eligible_reviews_all_completed"),
            "note": "Reported evidence fields only, not readiness conditions. Gated zeros are unobserved; technical qualification controls scientific interpretation."}
    ready = bool(e.checks) and all(row["passed"] for row in e.checks)
    return {"schema":"praxis008-paper-readiness-v1", "assessed_utc":now.isoformat(), "assessor_sha256":assessor_hash,
            "status":"READY_FOR_BOUNDED_EMPIRICAL_PAPER" if ready else "NOT_READY_EVIDENCE_CLOSURE_PENDING",
            "paper_development_ready":ready, "checks_total":len(e.checks), "checks_passed":sum(row["passed"] for row in e.checks),
            "checks_failed":sum(not row["passed"] for row in e.checks), "checks":e.checks,
            "input_evidence":e.files, "qualification":state.get("qualification"),
            "api_estimates_usd":state["costs"], "cloud_closeout":state.get("closeout"),
            "reported_scientific_evidence":scientific,
            "numerical_errata":state.get("numerical_errata"),
            "positive_policy_evidence":None,
            "primary_praxis_investment":"Separate result-and-literature assessment in RESULTS_AND_INVESTMENT.md; not automatically determined by readiness.",
            "novel_defense_validated":False, "external_publication_acceptance":"Not assessed or certified",
            "scope":["Readiness concerns complete technical/evidence closure for writing the bounded empirical result, including a negative result.",
                     "No positive hypothesis, favorable effect or policy gate is required or manufactured to obtain paper readiness.",
                     "Receipt verification is not a new AWS observation: the supplied coordinator closeout attests to the named hosts at its verified timestamp.",
                     "Exact statistical reproduction uses the frozen implementation; independent arithmetic/artifact audit and population validity are separate.",
                     "No model requests, candidate programs or cloud mutations are performed by this assessor."]}


def markdown(report):
    lines=["# Paper-development readiness", "", "**"+report["status"]+"**", "",
           "This decision concerns evidence closure for a bounded empirical paper. It does not establish a successful defense, novelty, primary-Praxis investment or publication acceptance.", "",
           f"Checks passed: {report['checks_passed']}/{report['checks_total']}.", "", "| Required evidence | Status | Explanation |", "|---|---|---|"]
    for check in report["checks"]:
        detail=check["detail"].replace("|","/").replace("\n"," ")
        lines.append("| "+check["check"]+" | "+("PASS" if check["passed"] else "PENDING/FAIL")+" | "+detail+" |")
    lines += ["", "Hypothesis effects and policy gates are retained separately in PAPER_READINESS.json. Qwen V1 gated heldout rows remain non-observations; a ready paper may report a negative result.", "",
              "The JSON receipt binds every input path and SHA256. Follow RESULTS_AND_INVESTMENT.md for the scientific contribution and investment assessment.", ""]
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core",type=Path,default=Path(__file__).resolve().parent.parent)
    for name in ("qualification_audit","qualification_receipt","generated_review","original_audit","extension_audit",
                 "original_package","extension_package","original_reproduction","extension_reproduction",
                 "original_process","extension_process","cloud_closeout"):
        parser.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    parser.add_argument("--output-json",type=Path,required=True)
    parser.add_argument("--output-markdown",type=Path,required=True)
    args=vars(parser.parse_args())
    output_json=args.pop("output_json")
    output_markdown=args.pop("output_markdown")
    report=assess(args)
    protected={Path(path).resolve() for path in report["input_evidence"]}
    need(output_json.resolve()!=output_markdown.resolve() and output_json.resolve() not in protected and output_markdown.resolve() not in protected,
         "Outputs must not overwrite evidence or each other")
    for path in (output_json,output_markdown): path.parent.mkdir(parents=True,exist_ok=True)
    output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    output_markdown.write_text(markdown(report),encoding="utf-8")
    print(json.dumps({key:report[key] for key in ("status","paper_development_ready","checks_passed","checks_total")}))
    return 0 if report["paper_development_ready"] else 2


if __name__=="__main__":
    raise SystemExit(main())
