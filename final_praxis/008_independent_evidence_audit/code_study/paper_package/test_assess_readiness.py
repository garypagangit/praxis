"""Synthetic receipt-chain controls; no real study artifacts or AWS access.

The fabricated fixture describes a complete audited study. It is not a substitute
for the actual artifact auditor; this tests readiness's receipt contracts and
refusal of missing, contradictory, stale, or truthy-but-false evidence.
"""
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import assess_readiness as r

NOW = dt.datetime(2026, 1, 3, tzinfo=dt.timezone.utc)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def change(path, function):
    value = json.loads(path.read_bytes())
    function(value)
    save(path, value)


def fixture(root, costs=(2.0, 3.0)):
    paths = {"core": root / "core"}
    core = paths["core"]
    paths["qualification_receipt"] = save(root / "qualification.json", {"synthetic": True})
    paths["qualification_audit"] = save(root / "qualification_audit.json", {
        "checks_total": 1, "checks_passed": 1, "errors": [], "decision": "GO_SEPARATELY_FROZEN_POLICY_STUDY",
        "all164_retained": 164, "assigned_tasks": 164, "eligible_pairs": 135, "eligible_heldout_pairs": 101,
        "results_receipt_sha256": sha(paths["qualification_receipt"])})
    paths["generated_review"] = save(root / "generated_review.json", {
        "checks_total": 1, "checks_passed": 1, "checks": {"synthetic_control": True}, "passed": True})
    for name in ("analysis.py", "offline_analysis.py", "MODEL_STUDY_PREREG.md", "paper_package/reproduce_statistics.py", "review/generated_controls.py",
                 "technical_extension/PREREG_V2.md", "technical_extension/adapter.py", "technical_extension/run_extension.py"):
        path = core / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic fixture; never executed. " + name, encoding="utf-8")
    control = {"checks_total":31,"checks_passed":31,"checks":{"synthetic_"+str(i):True for i in range(31)},
               "passed":True,"control_source_sha256":sha(core/"review/generated_controls.py")}
    save(paths["generated_review"],control)
    save(core/"review/GENERATED_COORDINATOR_REVIEW.json",control)
    original = {"files": {name: sha(core/name) for name in ("analysis.py", "offline_analysis.py", "MODEL_STUDY_PREREG.md", "review/generated_controls.py")},
        "protocol_sha256": sha(core/"MODEL_STUDY_PREREG.md"), "main_study_model_calls_before_freeze": 0,
        "main_policy_results_inspected_before_freeze": False,
        "full_qualification_audit_sha256": sha(paths["qualification_audit"]),
        "qualification_receipt_sha256": sha(paths["qualification_receipt"])}
    save(core/"MODEL_SOURCE_FREEZE.json", original)
    extension = {"files": {name: sha(core/"technical_extension"/name) for name in ("PREREG_V2.md","adapter.py","run_extension.py")},
        "protocol_sha256": sha(core/"technical_extension/PREREG_V2.md"),
        "core_source_freeze_sha256": sha(core/"MODEL_SOURCE_FREEZE.json"),
        "extension_model_calls_before_freeze": 0, "heldout_scientific_outcomes_inspected_before_freeze": False}
    save(core/"technical_extension/EXTENSION_SOURCE_FREEZE.json", extension)
    for phase, cost in zip(("original", "extension"), costs):
        package = root/phase
        package.mkdir()
        paths[phase+"_package"] = package
        protocol = (original if phase=="original" else extension)["protocol_sha256"]
        process = {"status":"finished", "phase":"complete", "expected_review_assignments":9456}
        if phase=="original":
            process.update(exit_code=0, durable_decision_receipts=9456, ended_utc="2026-01-02T00:00:00+00:00")
        else:
            process.update(failure=None, durable_decision_records=9456, utc="2026-01-02T01:00:00+00:00")
        paths[phase+"_process"] = save(package/"PROCESS.json", process)
        flow = {"review_assignments":9456,"review_records":9456,"source_tasks":164,"generated_proposals":328,
                "proposal_directions_assigned":656,"offline_assigned_rows":131200,"offline_rows":131200,
                "experiment_processing_accounted":True,"missing_review_record_ids":[],"model_status_counts":{"complete":9456},
                "within_frozen_api_ledger":True,"api_budget_limit_usd":30,"accounted_api_usd_estimate":cost,
                "invoice_claimed":False,"technical_gates":{},"eligible_reviews_all_completed":True}
        save(package/"FLOW_AND_COSTS.json",flow)
        save(package/"MODEL_RESULTS.json", {"primary_hypotheses":[],"policy_gates":[{"bounded_policy_criteria_met":False}]})
        save(package/"ACQUISITION_RESULTS.json", {"recommendation_gates":[{"primary_stratum":True,"bounded_offline_criteria_met":False}]})
        save(package/"budget.json", {"limit_usd":30,"entries":{"synthetic":{"accounted_usd":cost}}})
        result_hashes = {name:sha(package/name) for name in ("FLOW_AND_COSTS.json","MODEL_RESULTS.json","ACQUISITION_RESULTS.json")}
        for name in ("DECISIONS.jsonl","EXPECTED_DECISIONS.jsonl","OFFLINE.jsonl","EXPECTED_OFFLINE.jsonl"):
            raw=b'{"synthetic":"receipt-binding fixture only"}\n'
            (package/(name+".gz")).write_bytes(gzip.compress(raw,mtime=0))
            result_hashes[name]=hashlib.sha256(raw).hexdigest()
        save(package/"RESULTS_RECEIPT.json", {"protocol_sha256":protocol,"artifacts_sha256":result_hashes})
        artifacts=[]
        for path in package.iterdir():
            raw=path.read_bytes()
            artifacts.append({"file":path.name,"sha256":sha(path),"bytes":len(raw),
                              "uncompressed_source_sha256":hashlib.sha256(gzip.decompress(raw) if path.suffix==".gz" else raw).hexdigest()})
        save(package/"PACKAGE_RECEIPT.json", {"version":r.VERSIONS[phase],"artifacts":artifacts,"results_edited":False,"new_inference_calls":0})
        counts = {"source_tasks":164,"review_jobs":9456,"review_records":9456,"generated_proposals":328,"offline_rows":131200,
                  "results_receipt_sha256":sha(package/"RESULTS_RECEIPT.json"),"protocol_sha256":protocol,"accounted_api_usd_estimate":cost}
        if phase=="extension":
            counts.update(original_artifact_audit_sha256=sha(paths["original_audit"]),
                          extension_source_freeze_sha256=sha(core/"technical_extension/EXTENSION_SOURCE_FREEZE.json"),
                          warmup_observations_in_experimental_denominators=0)
        paths[phase+"_audit"] = save(root/(phase+"_audit.json"), {
            "audit_complete":True,"integrity_pass":True,"checks_total":2,"checks_passed":2,"checks_failed":0,
            "auditor_file_unchanged_during_run":True,"failures":[],"warnings":[],"counters":counts,"protocol_sha256":protocol,
            "configuration":"original_v1" if phase=="original" else "extension_v2_with_explicit_v1_reuse"})
        paths[phase+"_reproduction"] = save(root/(phase+"_reproduction.json"), {
            "version":r.VERSIONS[phase],"pass":True,"model_all_statistics_exact":True,"acquisition_all_statistics_exact":True,
            "comparison_excludes_only_top_level_provenance":True,"package_receipt_sha256":sha(package/"PACKAGE_RECEIPT.json"),
            "source_freeze_sha256":sha(core/"MODEL_SOURCE_FREEZE.json"),"reproducer_sha256":sha(core/"paper_package/reproduce_statistics.py"),
            "bootstrap_draws_per_registered_analysis":5000,"api_calls":0,"candidate_programs_executed":0})
    paths["cloud_closeout"] = save(root/"closeout.json", {
        "host_states":{host:"stopped" for host in r.HOSTS},"verified_utc":"2026-01-02T02:00:00+00:00",
        "new_inference_calls_after_closeout":0,"invoice_claimed":False,
        "api_original_usd_estimate":costs[0],"api_extension_usd_estimate":costs[1],"combined_api_usd_estimate":sum(costs),
        "host_compute_usd_upper_estimate":8.0,"total_incremental_usd_upper_estimate":sum(costs)+13.0})
    return paths


def resign_synthetic_extension(paths):
    """Refresh only the fabricated fixture's package/receipt dependency chain."""
    package = paths["extension_package"]
    change(package / "RESULTS_RECEIPT.json", lambda value: value["artifacts_sha256"].update(
        {"ACQUISITION_RESULTS.json": sha(package / "ACQUISITION_RESULTS.json")}))
    def artifact_hashes(value):
        for item in value["artifacts"]:
            path = package / item["file"]
            raw = path.read_bytes()
            item.update(sha256=sha(path), bytes=len(raw),
                        uncompressed_source_sha256=hashlib.sha256(
                            gzip.decompress(raw) if path.suffix == ".gz" else raw).hexdigest())
    change(package / "PACKAGE_RECEIPT.json", artifact_hashes)
    change(paths["extension_audit"], lambda value: value["counters"].update(
        results_receipt_sha256=sha(package / "RESULTS_RECEIPT.json")))
    change(paths["extension_reproduction"], lambda value: value.update(
        package_receipt_sha256=sha(package / "PACKAGE_RECEIPT.json")))


def disclosed_zero_erratum_fixture(paths):
    """Manually specified synthetic cancellation; no study records are loaded."""
    group = {"split": "heldout", "cohort": "generated", "proposer": "qwen.qwen3-coder-next",
             "intent": "adversarial_corruption", "direction": "harmful", "budget": 4}
    comparison = {"group": group, "left": "edit", "right": "hybrid", "difference": 8e-20,
                  "role": "secondary_descriptive", "ci95": [-0.02, 0.02]}
    gate = {"group": group, "primary_stratum": False, "bounded_offline_criteria_met": False,
            "static_edit_directional_benefit": True}
    save(paths["extension_package"] / "ACQUISITION_RESULTS.json",
         {"comparisons": [comparison], "recommendation_gates": [gate]})
    resign_synthetic_extension(paths)
    amendment = paths["core"] / "postrun_review/roundoff_amendment"
    initial = save(amendment / "INITIAL_ARTIFACT_AUDIT.json", {
        "audit_complete": True, "integrity_pass": False,
        "checks_total": 2, "checks_passed": 1, "checks_failed": 1,
        "failures": ["Synthetic exact-zero directional flag mismatch"]})
    save(amendment / "NUMERICAL_ERRATUM.json", {
        "results_receipt_sha256": sha(paths["extension_package"] / "RESULTS_RECEIPT.json"),
        "frozen_offline_source_sha256": sha(paths["core"] / "offline_analysis.py"),
        "initial_audit_sha256": sha(initial), "exact_rational_effect": 0.0,
        "frozen_sorted_float_effect": 8e-20, "corrected_static_edit_directional_benefit": False,
        "primary_hypotheses_changed": False, "overall_offline_recommendation_changed": False,
        "archive_or_frozen_source_modified": False, "comparison": comparison, "original_gate": gate})
    # A literal independently specified expectation catches identity/format drift;
    # this is intentionally not constructed by importing the assessor's logic.
    warning = (
        "NUMERICAL ERRATUM ('heldout', 'generated', 'qwen.qwen3-coder-next', "
        "'adversarial_corruption', 'harmful', 4): "
        '{"static_edit_directional_benefit": {"archived_machine": true, "exact_arithmetic": false}}'
        "; exact edit-minus-hybrid=0.0, frozen float=8e-20. "
        "An exact zero is no directional benefit; preserve archived bytes and report the correction.")
    change(paths["extension_audit"], lambda value: value.update(warnings=[warning]))


class ReadinessTests(unittest.TestCase):
    def run_fixture(self, mutate=None, costs=(2.,3.)):
        with tempfile.TemporaryDirectory(prefix="praxis_readiness_control_") as folder:
            paths=fixture(Path(folder),costs)
            if mutate: mutate(paths)
            return r.assess(paths,now=NOW)

    def test_negative_science_can_be_ready_after_true_closure(self):
        result=self.run_fixture()
        self.assertTrue(result["paper_development_ready"],[c for c in result["checks"] if not c["passed"]])
        self.assertEqual(result["status"],"READY_FOR_BOUNDED_EMPIRICAL_PAPER")
        self.assertFalse(result["novel_defense_validated"])
        self.assertIsNone(result["positive_policy_evidence"])
        self.assertFalse(result["reported_scientific_evidence"]["extension"]["model_policy_gates"][0]["bounded_policy_criteria_met"])

    def test_arbitrary_one_control_receipt_refuses(self):
        result=self.run_fixture(lambda p:change(p["generated_review"],lambda x:x.update(checks_total=1,checks_passed=1,checks={"only":True})))
        self.assertFalse(result["paper_development_ready"])

    def test_wrong_generated_control_source_refuses(self):
        result=self.run_fixture(lambda p:change(p["generated_review"],lambda x:x.update(control_source_sha256="0"*64)))
        self.assertFalse(result["paper_development_ready"])

    def test_missing_extension_audit_refuses_readiness(self):
        result=self.run_fixture(lambda p:p["extension_audit"].unlink())
        self.assertFalse(result["paper_development_ready"])
        self.assertTrue(any(c["check"]=="extension_independent_artifact_audit" and not c["passed"] for c in result["checks"]))

    def test_string_pass_and_boolean_count_are_not_evidence(self):
        for field,value in (("integrity_pass","true"),("audit_complete",False),("checks_total",True),("checks_failed",False)):
            with self.subTest(field=field):
                result=self.run_fixture(lambda p:change(p["extension_audit"],lambda x:x.update({field:value})))
                self.assertFalse(result["paper_development_ready"])

    def test_failed_or_inexact_reproduction_refuses(self):
        for field in ("pass","model_all_statistics_exact","acquisition_all_statistics_exact"):
            with self.subTest(field=field):
                result=self.run_fixture(lambda p:change(p["extension_reproduction"],lambda x:x.update({field:False})))
                self.assertFalse(result["paper_development_ready"])

    def test_reproduction_for_other_package_refuses(self):
        result=self.run_fixture(lambda p:change(p["extension_reproduction"],lambda x:x.update(package_receipt_sha256="0"*64)))
        self.assertFalse(result["paper_development_ready"])

    def test_missing_assignment_count_refuses(self):
        result=self.run_fixture(lambda p:change(p["extension_audit"],lambda x:x["counters"].update(review_records=9455)))
        self.assertFalse(result["paper_development_ready"])

    def test_wrong_reused_original_audit_refuses(self):
        result=self.run_fixture(lambda p:change(p["extension_audit"],lambda x:x["counters"].update(original_artifact_audit_sha256="1"*64)))
        self.assertFalse(result["paper_development_ready"])

    def test_skipped_selector_replay_refuses(self):
        result=self.run_fixture(lambda p:change(p["extension_audit"],lambda x:x.update(warnings=["Static selection replay was skipped; other checks passed."])))
        self.assertFalse(result["paper_development_ready"])

    def test_numerical_warning_without_disclosed_erratum_refuses(self):
        result=self.run_fixture(lambda p:change(p["extension_audit"],lambda x:x.update(warnings=["NUMERICAL ERRATUM synthetic cancellation"])))
        self.assertFalse(result["paper_development_ready"])
        self.assertTrue(any(c["check"]=="disclosed_numerical_errata_bound_to_results" and not c["passed"] for c in result["checks"]))

    def test_numerical_erratum_for_another_package_refuses(self):
        def mutate(paths):
            change(paths["extension_audit"],lambda x:x.update(warnings=["NUMERICAL ERRATUM synthetic cancellation"]))
            save(paths["core"]/"postrun_review/roundoff_amendment/NUMERICAL_ERRATUM.json",{"results_receipt_sha256":"0"*64})
        result=self.run_fixture(mutate)
        self.assertFalse(result["paper_development_ready"])
        self.assertTrue(any(c["check"]=="disclosed_numerical_errata_bound_to_results" and "another result package" in c["detail"] for c in result["checks"]))

    def test_new_unresolved_numerical_erratum_refuses(self):
        result=self.run_fixture(lambda p:change(p["extension_audit"],lambda x:x.update(warnings=["NUMERICAL ERRATUM one","NUMERICAL ERRATUM two"])))
        self.assertFalse(result["paper_development_ready"])

    def test_bound_disclosed_zero_erratum_preserves_readiness_and_negative_policy(self):
        result = self.run_fixture(disclosed_zero_erratum_fixture)
        self.assertTrue(result["paper_development_ready"],
                        [check for check in result["checks"] if not check["passed"]])
        self.assertEqual(result["status"], "READY_FOR_BOUNDED_EMPIRICAL_PAPER")
        self.assertFalse(result["numerical_errata"]["primary_hypotheses_changed"])
        self.assertTrue(result["numerical_errata"]["original_result_preserved"])
        self.assertEqual(len(result["numerical_errata"]["receipt_sha256"]), 64)
        self.assertIsNone(result["positive_policy_evidence"])
        self.assertFalse(result["novel_defense_validated"])
        self.assertTrue(any(check["check"] == "disclosed_numerical_errata_bound_to_results"
                            and check["passed"] for check in result["checks"]))

    def test_single_changed_warning_identity_cannot_reuse_known_erratum(self):
        def mutate(paths):
            disclosed_zero_erratum_fixture(paths)
            change(paths["extension_audit"], lambda value: value.update(
                warnings=[value["warnings"][0].replace("'harmful', 4)", "'harmful', 8)")]))
        result = self.run_fixture(mutate)
        self.assertFalse(result["paper_development_ready"])
        failed = [check for check in result["checks"] if not check["passed"]]
        self.assertEqual([check["check"] for check in failed],
                         ["disclosed_numerical_errata_bound_to_results"])
        self.assertIn("warning differs from the exact disclosed correction", failed[0]["detail"])

    def test_timeout_or_one_stopped_host_is_not_shutdown(self):
        for states in ({next(iter(r.HOSTS)):"stopped"},{host:"stopping" for host in r.HOSTS}):
            with self.subTest(states=states):
                result=self.run_fixture(lambda p:change(p["cloud_closeout"],lambda x:x.update(host_states=states)))
                self.assertFalse(result["paper_development_ready"])

    def test_stale_shutdown_receipt_refuses(self):
        result=self.run_fixture(lambda p:change(p["cloud_closeout"],lambda x:x.update(verified_utc="2026-01-01T02:00:00+00:00")))
        self.assertFalse(result["paper_development_ready"])

    def test_overbudget_or_inconsistent_sum_refuses(self):
        self.assertFalse(self.run_fixture(costs=(31.,3.))["paper_development_ready"])
        result=self.run_fixture(lambda p:change(p["cloud_closeout"],lambda x:x.update(combined_api_usd_estimate=4.)))
        self.assertFalse(result["paper_development_ready"])

    def test_changed_package_and_frozen_source_refuse(self):
        for which in ("package","source"):
            with self.subTest(which=which):
                def mutate(paths):
                    target=paths["extension_package"]/"MODEL_RESULTS.json" if which=="package" else paths["core"]/"analysis.py"
                    target.write_text("changed",encoding="utf-8")
                self.assertFalse(self.run_fixture(mutate)["paper_development_ready"])

    def test_nonfinite_and_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):r.strict_json(b'{"pass":true,"pass":true}')
        with self.assertRaises(ValueError):r.strict_json(b'{"cost":NaN}')


if __name__=="__main__":
    unittest.main()
