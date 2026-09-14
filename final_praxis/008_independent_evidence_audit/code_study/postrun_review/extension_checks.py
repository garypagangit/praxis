"""Version-two lineage audit, independent of the frozen extension implementation.

Reads artifacts only after explicit release. Never executes proposals or calls APIs.
"""
import copy
import math
from pathlib import Path
import re
import audit_results as base


def verify_extension_source(audit, args):
    expected=args.extension_protocol_sha256
    if not isinstance(expected,str) or not re.fullmatch(r"[0-9a-f]{64}",expected):
        raise ValueError("Explicit extension protocol hash is required")
    directory=args.extension_code
    freeze=base.read_json(directory/"EXTENSION_SOURCE_FREEZE.json")
    good=audit.check(freeze["protocol_sha256"]==expected==base.sha_file(directory/"PREREG_V2.md"),"v2:explicit_protocol_pin")
    good=audit.check(freeze["core_source_freeze_sha256"]==base.sha_file(args.code/"MODEL_SOURCE_FREEZE.json"),"v2:original_core_pin") and good
    for name,wanted in freeze["files"].items():
        good=audit.check(base.sha_file(base.safe_child(directory,name))==wanted,"v2:source_freeze_hash",name) and good
    good=audit.check(freeze["extension_model_calls_before_freeze"]==0 and freeze["heldout_scientific_outcomes_inspected_before_freeze"] is False,"v2:prospective_freeze_declaration") and good
    good=audit.check(freeze["api_limit_new_usd"]==30 and freeze["combined_api_limit_usd"]==60 and freeze["total_incremental_job_envelope_usd"]==100,"v2:frozen_cost_limits") and good
    if not good:
        raise ValueError("Extension source/protocol mismatch")
    if args.original_audit is None:
        raise ValueError("A completed original-version artifact audit is required")
    prior=base.read_json(args.original_audit)
    good=audit.check(prior.get("integrity_pass") is True and prior.get("audit_complete") is True and prior.get("checks_failed")==0 and prior.get("protocol_sha256")==base.PROTOCOL_SHA256,"v2:original_artifact_audit_passed")
    prior_receipt=base.sha_file(args.campaign/"study/public_results/RESULTS_RECEIPT.json")
    good=audit.check(prior.get("counters",{}).get("results_receipt_sha256")==prior_receipt,"v2:original_audit_binds_exact_result_receipt") and good
    # Recheck all original receipt inputs so the old audit cannot authorize changed
    # aggregate files or a changed ledger in this extracted campaign.
    receipt=base.read_json(args.campaign/"study/public_results/RESULTS_RECEIPT.json")
    for name,wanted in receipt["source_inputs_sha256"].items():
        root=args.code if name=="MODEL_SOURCE_FREEZE.json" or name.startswith("qualification/") else args.campaign/"study"
        good=audit.check(base.sha_file(base.safe_child(root,name))==wanted,"v2:original_audited_source_still_exact",name) and good
    if not good:
        raise ValueError("Original audit or original input provenance mismatch")
    audit.counts.update(extension_source_freeze_sha256=base.sha_file(directory/"EXTENSION_SOURCE_FREEZE.json"),
                        original_artifact_audit_sha256=base.sha_file(args.original_audit))
    return expected


def imported_review(row):
    return row["reviewer"]==base.REVIEWERS[1] and (row["cohort"]=="native" or row["split"]=="dev")


def new_request_id(job_id,row):
    return "v2-"+job_id if row["reviewer"]==base.REVIEWERS[0] else job_id


def exact_import(audit,args,item,source,destination,record=None):
    good=audit.check(item.get("source")==source and item.get("destination")==destination,"v2:fixed_import_path",destination)
    src=base.safe_child(args.campaign,source)
    dst=base.safe_child(args.study,destination)
    good=audit.check(src.read_bytes()==dst.read_bytes() and item.get("sha256")==base.sha_file(src),"v2:byte_identical_import",destination) and good
    if record is not None:
        good=audit.check(base.read_json(src)==record,"v2:import_matches_assembled_row",destination) and good
    return good


def effective_gates(audit,args,gates):
    measured_hashes={cohort:base.sha_file(args.study/("GATE_"+cohort+"_development.json")) for cohort in ("native","generated")}
    checks={cohort:gates[cohort+"_development"]["models"][base.REVIEWERS[0]]["pass"] and gates[cohort+"_development"]["all_assignments_accounted"] for cohort in ("native","generated")}
    joint=all(checks.values())
    annotation=dict(checks=checks,**{"pass":joint},measured_gate_sha256=measured_hashes,protocol_sha256=args.extension_protocol_sha256)
    audit.check(gates["proposer"]==dict(split="development",proposer=base.REVIEWERS[0],**annotation),"v2:proposer_conjunction_and_hashes")
    effective=copy.deepcopy(gates)
    paths={}
    for cohort in ("native","generated"):
        key=cohort+"_development"
        wanted=copy.deepcopy(gates[key])
        wanted["models"][base.REVIEWERS[0]]["measured_pass"]=wanted["models"][base.REVIEWERS[0]]["pass"]
        wanted["models"][base.REVIEWERS[0]]["pass"]=joint
        wanted["pass"]=wanted["all_assignments_accounted"] and all(row["pass"] for row in wanted["models"].values())
        wanted["effective_qwen_joint_gate"]=annotation
        path=args.study/("EFFECTIVE_GATE_"+key+".json")
        actual=base.read_json(path)
        audit.check(actual==wanted,"v2:effective_heldout_gate_exact",cohort)
        effective[key]=actual
        paths[path.name]=base.sha_file(path)
    return effective,paths,measured_hashes


def warmup_assignment(audit,args,frozen_prompts):
    raw=base.read_json(args.study/"SCHEMA_WARMUP_RAW.json")
    summary=base.read_json(args.study/"SCHEMA_WARMUP.json")
    request_id="v2-review-schema-warmup-v2"
    original='def synthetic_identity(x: int) -> int:\n    """Return x unchanged."""\n    return x\n'
    proposal='def synthetic_identity(x: int) -> int:\n    """Return x unchanged."""\n    return x + 1\n'
    spec=dict(entry_point="synthetic_identity",signature="x: int",returns="int",description="Return x unchanged.")
    messages=frozen_prompts.review_messages(spec,original,proposal,[],[])
    job=dict(job_id=request_id,row=dict(eligible=True,reviewer=base.REVIEWERS[0],split="dev",cohort="synthetic_warmup"),messages=messages)
    parsed=base.parse_review(raw)
    audit.check(parsed["model_valid"] is True,"v2:warmup_valid_not_decision_gate")
    audit.check(summary.get("valid") is True and summary.get("kind")=="synthetic_schema_warmup_not_experiment_task" and summary.get("substantive_decision_not_a_gate") is True,"v2:warmup_nonexperimental_identity")
    audit.check(summary.get("schema_sha256")==base.sha_text(base.canonical(base.REVIEW_SCHEMA)) and summary.get("protocol_sha256")==args.extension_protocol_sha256,"v2:warmup_schema_protocol_hashes")
    audit.check(summary.get("request_id")==request_id==raw.get("request_id") and summary.get("raw_result_sha256")==base.sha_file(args.study/"SCHEMA_WARMUP_RAW.json"),"v2:warmup_raw_binding")
    result_path=args.study/"raw_inference"/(request_id+".result.json")
    audit.check(base.read_json(result_path)==raw,"v2:warmup_identical_adapter_result")
    request_name=str(raw["request_receipt"]).replace("\\","/").split("/")[-1]
    audit.check(summary.get("request_receipt_sha256")==base.sha_file(args.study/"raw_inference"/request_name) and summary.get("finish_reason")==raw["finish_reason"] and summary.get("usage")==raw["usage"],"v2:warmup_receipt_summary")
    return request_id,job,dict(parsed,model_status="complete")


def audit_extension_lineage_and_raw(audit,args,assignments,decisions,proposals,gates,frozen_prompts):
    original=args.campaign/"study"
    expected_review_ids={jid for jid,row in decisions.items() if imported_review(row)}
    seen_review_ids=set()
    manifests={path.name:path for path in args.study.glob("IMPORTED_*.json")}
    expected_names={"IMPORTED_DEVELOPMENT_PROPOSALS.json","IMPORTED_DEVSTRAL_native_development.json","IMPORTED_DEVSTRAL_native_heldout.json","IMPORTED_DEVSTRAL_generated_development.json"}
    audit.check(set(manifests)==expected_names,"v2:exact_import_manifest_family")
    for cohort,split in (("native","development"),("native","heldout"),("generated","development")):
        name="IMPORTED_DEVSTRAL_"+cohort+"_"+split+".json"
        items=base.read_json(manifests[name])["imports"]
        for item in items:
            jid=item["job_id"]
            allowed=jid in expected_review_ids and jid not in seen_review_ids
            audit.check(allowed,"v2:fixed_unique_reused_review",jid)
            seen_review_ids.add(jid)
            if not allowed: continue
            row=decisions[jid]
            audit.check(item.get("reviewer")==base.REVIEWERS[1] and item.get("new_call") is False and item.get("cohort")==cohort and item.get("split")==split and row["cohort"]==cohort and row["split"]==("dev" if split=="development" else split),"v2:reuse_declared_model_cohort",jid)
            exact_import(audit,args,item,"study/decisions/"+jid+".json","decisions/"+jid+".json",row)
    audit.check(seen_review_ids==expected_review_ids,"v2:all_fixed_reused_reviews_present")
    development_pids={pid for pid,row in proposals.items() if assignments["proposal-"+pid][0]["split"]=="development"}
    expected_destinations={"proposal_jobs_development.jsonl","proposals_development.jsonl"}|{"proposals/"+pid+".json" for pid in development_pids}
    seen_destinations=set()
    for item in base.read_json(manifests["IMPORTED_DEVELOPMENT_PROPOSALS.json"])["imports"]:
        dest=item["destination"]
        allowed=dest in expected_destinations and dest not in seen_destinations
        audit.check(allowed,"v2:fixed_unique_reused_development_proposal",dest)
        seen_destinations.add(dest)
        if not allowed: continue
        record=proposals[Path(dest).stem] if dest.startswith("proposals/") else None
        exact_import(audit,args,item,"study/"+dest,dest,record)
    audit.check(seen_destinations==expected_destinations,"v2:all_development_proposals_retained")
    new_assignments={}
    new_decisions={}
    for jid,row in decisions.items():
        if jid in expected_review_ids: continue
        rid=new_request_id(jid,row)
        new_assignments[rid]=assignments[jid]
        new_decisions[rid]=row
    new_proposals={pid:row for pid,row in proposals.items() if pid not in development_pids}
    for pid in new_proposals:
        new_assignments["proposal-"+pid]=assignments["proposal-"+pid]
    rid,job,decision=warmup_assignment(audit,args,frozen_prompts)
    audit.check(rid not in new_assignments and rid not in decisions,"v2:warmup_excluded_from_scientific_universe")
    new_assignments[rid]=(job,False)
    new_decisions[rid]=decision
    effective,gate_hashes,measured_hashes=effective_gates(audit,args,gates)
    freeze=base.read_json(args.extension_code/"EXTENSION_SOURCE_FREEZE.json")
    ledger=base.audit_raw(audit,args.study,new_assignments,new_decisions,new_proposals,effective,freeze["created_utc"],protocol_hash=args.extension_protocol_sha256,structured_reviews=True)
    receipt=base.read_json(args.study/"EXTENSION_ASSEMBLY_RECEIPT.json")
    wanted={"extension_source_freeze_sha256":base.sha_file(args.extension_code/"EXTENSION_SOURCE_FREEZE.json"),
            "extension_protocol_sha256":args.extension_protocol_sha256,"original_source_freeze_sha256":base.sha_file(args.code/"MODEL_SOURCE_FREEZE.json"),
            "original_results_receipt_sha256":base.sha_file(original/"public_results/RESULTS_RECEIPT.json"),
            "extension_results_receipt_sha256":base.sha_file(args.study/"public_results/RESULTS_RECEIPT.json"),
            "import_manifests":{name:base.sha_file(path) for name,path in manifests.items()},
            "schema_warmup_sha256":base.sha_file(args.study/"SCHEMA_WARMUP.json"),
            "schema_warmup_raw_sha256":base.sha_file(args.study/"SCHEMA_WARMUP_RAW.json"),
            "effective_heldout_gates":gate_hashes,"measured_development_gates":measured_hashes,
            "proposer_development_gate_sha256":base.sha_file(args.study/"PROPOSER_DEVELOPMENT_GATE.json"),"reused_calls_are_not_new_observations":True}
    audit.check(all(receipt.get(key)==value for key,value in wanted.items()),"v2:assembly_provenance_bindings")
    prior_cost=math.fsum(row["accounted_usd"] for row in base.read_json(original/"budget.json")["entries"].values())
    new_cost=audit.counts["accounted_api_usd_estimate"]
    audit.check(math.isclose(receipt["original_api_usd_estimate"],prior_cost,abs_tol=1e-9) and math.isclose(receipt["extension_api_usd_estimate"],new_cost,abs_tol=1e-9) and prior_cost+new_cost<=60+1e-9,"v2:separate_and_combined_cost_lineage")
    audit.counts.update(reused_review_assignments=len(expected_review_ids),reused_generated_proposal_assignments=len(development_pids),
                        new_review_assignments=len(decisions)-len(expected_review_ids),new_generated_proposal_assignments=len(new_proposals),
                        warmup_observations_in_experimental_denominators=0,original_api_usd_estimate=prior_cost,
                        combined_api_usd_estimate=prior_cost+new_cost,extension_assembly_receipt_sha256=base.sha_file(args.study/"EXTENSION_ASSEMBLY_RECEIPT.json"))
    audit.warnings.append("Version two is a mixed-lineage assembled dataset: reused Devstral/native and generated-development observations are not a fresh replication. Schema decoding is a distinct Qwen configuration; original and extension statistics must remain separate.")
    return ledger
