"""Version-two assembly with exact version-one record reuse and new Qwen schema calls."""
from __future__ import annotations
import argparse
import copy
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
CORE = HERE.parent
sys.path.insert(0, str(CORE))
import study_runner as runner
import finalize_results
import prompts
from technical_extension.adapter import StructuredReviewAdapter, SCHEMA_SHA256, REVIEW_JSON_SCHEMA


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_copy(source, destination):
    source, destination = Path(source), Path(destination)
    payload = source.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != payload:
        raise ValueError("Refusing changed imported artifact: " + str(destination))
    destination.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def unique_records(records, field, label):
    result = {}
    for record in records:
        identifier = record.get(field) if isinstance(record, dict) else None
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,150}', identifier):
            raise ValueError('Invalid identity in ' + label)
        if identifier in result:
            raise ValueError('Duplicate identity in ' + label + ': ' + identifier)
        result[identifier] = record
    return result


def copy_imports(campaign, output, imports):
    # Validate all sources and destination conflicts before copying any artifact.
    for item in imports:
        source, destination = campaign / item['source'], output / item['destination']
        payload = source.read_bytes()
        item['sha256'] = hashlib.sha256(payload).hexdigest()
        if destination.exists() and destination.read_bytes() != payload:
            raise ValueError('Imported artifact conflicts with existing destination')
    for item in imports:
        if exact_copy(campaign / item['source'], output / item['destination']) != item['sha256']:
            raise ValueError('Import source changed during copy')


def import_development_proposals(campaign, output):
    original = campaign / "study"
    jobs = unique_records(runner.rows(original / 'proposal_jobs_development.jsonl'), 'proposal_id', 'development proposal jobs')
    proposals = unique_records(runner.rows(original / 'proposals_development.jsonl'), 'proposal_id', 'development proposals')
    if set(jobs) != set(proposals):
        raise ValueError('Development proposal assignment/record identity universes differ')
    for identifier, proposal in proposals.items():
        job = jobs[identifier]
        if proposal.get('assignment_sha256') != runner.digest(runner.policies.canonical(job)):
            raise ValueError('Development proposal assignment hash mismatch')
        if any(proposal.get(key) != value for key, value in job.items() if key != 'messages'):
            raise ValueError('Development proposal immutable assignment fields differ')
        if runner.read(original / 'proposals' / (identifier + '.json')) != proposal:
            raise ValueError('Development proposal aggregate/per-call record mismatch')
    imports = []
    for name in ("proposal_jobs_development.jsonl", "proposals_development.jsonl"):
        imports.append({"source": "study/" + name, "destination": name,
                        "kind": "development_proposal_aggregate"})
    for proposal in proposals.values():
        name = "proposals/" + proposal["proposal_id"] + ".json"
        imports.append({"source": "study/" + name, "destination": name,
                        "kind": "development_proposal",
                        "proposal_id": proposal["proposal_id"]})
    copy_imports(campaign, output, imports)
    runner.save(output / "IMPORTED_DEVELOPMENT_PROPOSALS.json", {"imports": imports})


def import_devstral(campaign, output, cohort, split):
    if cohort == "generated" and split != "development":
        raise ValueError("Generated heldout reviews were not run in version one")
    original = campaign / "study"
    suffix = cohort + "_" + split
    old_rows = unique_records(runner.rows(original / ("decisions_" + suffix + ".jsonl")), 'job_id', 'original review decisions')
    new_jobs = unique_records(runner.rows(output / ("review_jobs_" + suffix + ".jsonl")), 'job_id', 'new review jobs')
    expected_ids = {identifier for identifier, job in new_jobs.items() if job['row']['reviewer'] == 'mistral.devstral-2-123b'}
    imported_ids = {identifier for identifier, row in old_rows.items() if row['reviewer'] == 'mistral.devstral-2-123b'}
    if imported_ids != expected_ids:
        raise ValueError('Devstral imported/assigned identity universes differ')
    imports = []
    for row in old_rows.values():
        if row["reviewer"] != "mistral.devstral-2-123b":
            continue
        job = new_jobs[row["job_id"]]
        if row["assignment_sha256"] != runner.digest(runner.policies.canonical(job)):
            raise ValueError("Imported Devstral assignment is not identical")
        if any(row.get(key) != value for key, value in job['row'].items()):
            raise ValueError('Imported Devstral immutable assignment fields differ')
        name = "decisions/" + row["job_id"] + ".json"
        if runner.read(original / name) != row:
            raise ValueError("Original aggregate and immutable per-call record disagree")
        imports.append({"source": "study/" + name, "destination": name,
                        "kind": "review_decision",
                        "job_id": row["job_id"], "cohort": cohort, "split": split,
                        "reviewer": row["reviewer"], "new_call": False})
    copy_imports(campaign, output, imports)
    runner.save(output / ("IMPORTED_DEVSTRAL_" + suffix + ".json"), {"imports": imports})


def arguments(campaign, output, split, cohort="native"):
    return SimpleNamespace(tasks=campaign / "bundle/data/tasks.jsonl", qualification=campaign / "full",
                           output=output, split=split, cohort=cohort, proposals=None, evaluations=None,
                           evaluation_root=None, gate=None, workers=8, profile="role", jobs=None)


def warmup_messages():
    original = 'def synthetic_identity(x: int) -> int:\n    """Return x unchanged."""\n    return x\n'
    proposal = original.replace("    return x\n", "    return x + 1\n")
    spec = prompts.specification(original, "synthetic_identity")
    return prompts.review_messages(spec, original, proposal, [], [])


def expected_warmup_request():
    messages = warmup_messages()
    return {'modelId': prompts.PROPOSER,
            'messages': [{'role': item['role'], 'content': [{'text': item['content']}]} for item in messages if item['role'] != 'system'],
            'system': [{'text': item['content']} for item in messages if item['role'] == 'system'],
            'inferenceConfig': {'maxTokens': 1024, 'temperature': 0},
            'requestMetadata': {'experiment': 'final-praxis-008-code-20260914', 'request_id': 'v2-review-schema-warmup-v2', 'preregistration_sha256': sha(HERE / 'PREREG_V2.md')},
            'outputConfig': {'textFormat': {'type': 'json_schema', 'structure': {'jsonSchema': {'name': 'experiment_response', 'schema': runner.policies.canonical(REVIEW_JSON_SCHEMA)}}}}}


def validate_warmup_raw(raw, output):
    if raw.get('request_id') != 'v2-review-schema-warmup-v2' or raw.get('model_id') != prompts.PROPOSER:
        raise ValueError('Warmup model/request identity mismatch')
    if raw.get('preregistration_sha256') != sha(HERE / 'PREREG_V2.md') or raw.get('runtime', {}).get('structured_output') is not True:
        raise ValueError('Warmup protocol/schema mode mismatch')
    request_path = Path(raw.get('request_receipt', '')).resolve()
    if not request_path.is_relative_to((output / 'raw_inference').resolve()) or not request_path.is_file():
        raise ValueError('Warmup request receipt missing or outside inference directory')
    request = runner.read(request_path)['request']
    if request != expected_warmup_request():
        raise ValueError('Warmup request/schema differs from frozen synthetic request')
    if raw.get('prompt_sha256') != runner.digest(runner.policies.canonical(request)):
        raise ValueError('Warmup request hash mismatch')
    if raw.get('inference_input_sha256') != runner.digest(runner.policies.canonical({key: value for key, value in request.items() if key != 'requestMetadata'})):
        raise ValueError('Warmup inference-content hash mismatch')
    if not prompts.parse_review(raw)['valid']:
        raise ValueError('Schema warmup did not yield a terminal valid response')
    return sha(request_path)


def warmup(output):
    destination = output / 'SCHEMA_WARMUP.json'
    raw_path = output / 'SCHEMA_WARMUP_RAW.json'
    if destination.exists():
        saved = runner.read(destination)
        if saved.get('valid') is not True:
            raise ValueError('The immutable schema warmup failed')
        if saved.get('kind') != 'synthetic_schema_warmup_not_experiment_task' or saved.get('request_id') != 'v2-review-schema-warmup-v2' or saved.get('schema_sha256') != SCHEMA_SHA256 or saved.get('protocol_sha256') != sha(HERE / 'PREREG_V2.md'):
            raise ValueError('Cached warmup identity/schema/protocol mismatch')
        if not raw_path.exists() or saved.get('raw_result_sha256') != sha(raw_path):
            raise ValueError('Cached warmup raw-result hash mismatch')
        raw = runner.read(raw_path)
        request_hash = validate_warmup_raw(raw, output)
        if saved.get('request_receipt_sha256') != request_hash or saved.get('finish_reason') != raw['finish_reason'] or saved.get('usage') != raw['usage']:
            raise ValueError('Cached warmup result/request summary mismatch')
        return
    if raw_path.exists():
        raw = runner.read(raw_path)  # Recover a crash after durable raw storage, without a new call.
    else:
        ledger = runner.BudgetLedger(output / 'budget.json', limit_usd=30)
        adapter = StructuredReviewAdapter(prompts.PROPOSER, profile=None, receipt_dir=output / 'raw_inference', ledger=ledger, max_attempts=2, timeout=600)
        raw = adapter.generate(warmup_messages(), max_new_tokens=1024, request_id='review-schema-warmup-v2')
        runner.save(raw_path, raw)
    failure, request_hash = None, None
    try:
        request_hash = validate_warmup_raw(raw, output)
    except (ValueError, KeyError, TypeError, OSError) as error:
        failure = str(error)
    runner.save(destination, {'kind': 'synthetic_schema_warmup_not_experiment_task', 'valid': failure is None,
                              'request_id': raw.get('request_id'), 'schema_sha256': SCHEMA_SHA256,
                              'protocol_sha256': sha(HERE / 'PREREG_V2.md'), 'raw_result_sha256': sha(raw_path),
                              'request_receipt_sha256': request_hash, 'finish_reason': raw.get('finish_reason'),
                              'usage': raw.get('usage'), 'validation_failure': failure, 'substantive_decision_not_a_gate': True})
    if failure is not None:
        raise ValueError(failure)


def effective_heldout_gates(output):
    measured, source_hashes = {}, {}
    for cohort in ('native', 'generated'):
        path = output / ('GATE_' + cohort + '_development.json')
        gate = runner.read(path)
        if gate.get('cohort') != cohort or gate.get('split') != 'development' or set(gate.get('models', {})) != set(prompts.REVIEWERS):
            raise ValueError('Measured development gate identity mismatch')
        if type(gate.get('all_assignments_accounted')) is not bool or any(type(value.get('pass')) is not bool for value in gate['models'].values()):
            raise ValueError('Measured development gate flags must be booleans')
        measured[cohort], source_hashes[cohort] = gate, sha(path)
    checks = {cohort: gate['models'][prompts.PROPOSER]['pass'] and gate['all_assignments_accounted'] for cohort, gate in measured.items()}
    joint = all(checks.values())
    runner.save(output / 'PROPOSER_DEVELOPMENT_GATE.json', {'split': 'development', 'proposer': prompts.PROPOSER,
                'checks': checks, 'pass': joint, 'measured_gate_sha256': source_hashes, 'protocol_sha256': sha(HERE / 'PREREG_V2.md')})
    paths = {}
    for cohort, measured_gate in measured.items():
        gate = copy.deepcopy(measured_gate)
        gate['models'][prompts.PROPOSER]['measured_pass'] = gate['models'][prompts.PROPOSER]['pass']
        gate['models'][prompts.PROPOSER]['pass'] = joint
        gate['pass'] = gate['all_assignments_accounted'] and all(value['pass'] for value in gate['models'].values())
        gate['effective_qwen_joint_gate'] = {'checks': checks, 'pass': joint, 'measured_gate_sha256': source_hashes, 'protocol_sha256': sha(HERE / 'PREREG_V2.md')}
        paths[cohort] = output / ('EFFECTIVE_GATE_' + cohort + '_development.json')
        runner.save(paths[cohort], gate)
    return paths


def verify_freeze():
    manifest = runner.read(HERE / "EXTENSION_SOURCE_FREEZE.json")
    for relative, expected in manifest["files"].items():
        if sha(HERE / relative) != expected:
            raise ValueError("Extension source changed after freeze: " + relative)
    if sha(CORE / "MODEL_SOURCE_FREEZE.json") != manifest["core_source_freeze_sha256"]:
        raise ValueError("Original core source-freeze identity changed")
    for relative, expected in runner.read(CORE / "MODEL_SOURCE_FREEZE.json")["files"].items():
        if sha(CORE / relative) != expected:
            raise ValueError("Original core source changed: " + relative)
    if sha(HERE / "PREREG_V2.md") != os.environ.get("PRAXIS_PREREG_SHA256"):
        raise ValueError("Extension protocol hash mismatch")


def run(campaign):
    output = campaign / "study_v2"
    output.mkdir(exist_ok=True)
    phase, succeeded, failure = "verify", False, None
    try:
        verify_freeze()
        original_status = runner.read(campaign / "study/STUDY_PROCESS_STATUS.json")
        if original_status["status"] != "finished" or original_status["exit_code"] != 0:
            raise ValueError("Original run must finish and remain preserved before importing")
        runner.BedrockAdapter = StructuredReviewAdapter  # Explicit versioned dependency injection.
        phase = "schema_warmup"
        warmup(output)
        phase = "freeze_references_and_import_proposals"
        references = output / "REFERENCE_MANIFEST.json"
        if not references.exists():
            subprocess.run([sys.executable, str(CORE / "generated_execution.py"), "--tasks-file", str(campaign / "bundle/data/tasks.jsonl"),
                            "--qualification-private", str(campaign / "full/private"), "--qualification-summary", str(campaign / "full/public/SUMMARY.json"),
                            "--prepare-reference-manifest", str(references)], check=True)
        import_development_proposals(campaign, output)
        for split in ("development", "heldout"):
            if split == "heldout":
                phase = "heldout_proposals"
                heldout_gates = effective_heldout_gates(output)
                args = arguments(campaign, output, split)
                runner.prepare_proposals(args)
                args.jobs = output / "proposal_jobs_heldout.jsonl"
                args.gate = output / "PROPOSER_DEVELOPMENT_GATE.json"
                runner.infer_proposals(args)
                phase = "heldout_generated_execution"
                subprocess.run(["bash", str(CORE / "run_generated_docker.sh"), "praxis008-qualification:20260914", str(CORE),
                                str(campaign / "bundle"), str(campaign / "full"), str(output / "proposals_heldout.jsonl"),
                                str(references), str(campaign / "generated_v2_heldout")], check=True)
            for cohort in ("native", "generated"):
                phase = "prepare_" + cohort + "_" + split
                args = arguments(campaign, output, split, cohort)
                if cohort == "generated":
                    args.proposals = output / ("proposals_" + split + ".jsonl")
                    args.evaluation_root = campaign / ("generated_development" if split == "development" else "generated_v2_heldout")
                    args.evaluations = args.evaluation_root / "public/PROPOSAL_RESULTS.jsonl"
                runner.prepare_reviews(args)
                if cohort == "native" or split == "development":
                    import_devstral(campaign, output, cohort, split)
                args.jobs = output / ("review_jobs_" + cohort + "_" + split + ".jsonl")
                if split == "heldout":
                    args.gate = heldout_gates[cohort]
                phase = "inference_" + cohort + "_" + split
                runner.infer_reviews(args)
        phase = "analysis"
        finalize_results.finalize(output, HERE / "PREREG_V2.md", os.environ["PRAXIS_PREREG_SHA256"])
        imported = sorted(output.glob("IMPORTED_*.json"))
        receipt = {"extension_source_freeze_sha256": sha(HERE / "EXTENSION_SOURCE_FREEZE.json"),
                   "extension_protocol_sha256": sha(HERE / "PREREG_V2.md"),
                   "original_source_freeze_sha256": sha(CORE / "MODEL_SOURCE_FREEZE.json"),
                   "original_results_receipt_sha256": sha(campaign / "study/public_results/RESULTS_RECEIPT.json"),
                   "extension_results_receipt_sha256": sha(output / "public_results/RESULTS_RECEIPT.json"),
                   "import_manifests": {p.name: sha(p) for p in imported},
                   "schema_warmup_sha256": sha(output / "SCHEMA_WARMUP.json"),
                   "schema_warmup_raw_sha256": sha(output / 'SCHEMA_WARMUP_RAW.json'),
                   "effective_heldout_gates": {path.name: sha(path) for path in heldout_gates.values()},
                   "measured_development_gates": {cohort: sha(output / ('GATE_' + cohort + '_development.json')) for cohort in ('native', 'generated')},
                   "proposer_development_gate_sha256": sha(output / 'PROPOSER_DEVELOPMENT_GATE.json'),
                   "actual_new_request_namespace": "v2-review-* for Qwen reviews; unchanged IDs in this separate directory for new proposal/Devstral calls",
                   "reused_calls_are_not_new_observations": True,
                   "original_api_usd_estimate": sum(r["accounted_usd"] for r in runner.read(campaign / "study/budget.json")["entries"].values()),
                   "extension_api_usd_estimate": sum(r["accounted_usd"] for r in runner.read(output / "budget.json")["entries"].values())}
        runner.save(output / "EXTENSION_ASSEMBLY_RECEIPT.json", receipt)
        phase, succeeded = "complete", True
    except BaseException as error:
        failure = {"type": type(error).__name__, "detail": str(error)}
        raise
    finally:
        status = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "phase": phase,
                  "status": "finished" if succeeded else "incomplete_requires_recovery", "failure": failure,
                  "expected_review_assignments": 9456, "durable_decision_records": len(list((output / "decisions").glob("*.json"))),
                  "paper_ready_claimed": False}
        temporary = output / "EXTENSION_PROCESS_STATUS.tmp"
        temporary.write_text(json.dumps(status, indent=2) + "\n")
        os.replace(temporary, output / "EXTENSION_PROCESS_STATUS.json")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--campaign-root", type=Path, required=True)
    args = p.parse_args()
    os.environ["PRAXIS_PREREG_PATH"] = str(HERE / "PREREG_V2.md")
    run(args.campaign_root.resolve())
