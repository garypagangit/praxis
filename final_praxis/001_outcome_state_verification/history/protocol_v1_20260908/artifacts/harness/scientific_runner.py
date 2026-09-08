"""Real model inference in immutable, independently verifiable stages."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from .scientific_protocol import (ROOT, allocation, instantiate, action_messages, execute_actions,
    controlled_state, visible_receipt, public_record, claim_messages, judge_messages, parse_decision,
    file_hash, digest, write_new)
from .verifier import verify

INFERENCE_DIR = None

def now():
    return datetime.now(timezone.utc).isoformat()

def preflight():
    freeze = json.loads((ROOT / "FROZEN_PROTOCOL.json").read_text(encoding="utf-8"))
    for relpath, expected in freeze["artifact_hashes"].items():
        if file_hash(ROOT / relpath) != expected:
            raise ValueError(f"frozen hash mismatch: {relpath}")
    config = json.loads((ROOT / "configs/scientific_v1.json").read_text(encoding="utf-8"))
    if config["agent"]["model_id"] == config["judge"]["model_id"]:
        raise ValueError("agent and judge must differ")
    rows = allocation()
    if len(rows) != 400 or Counter(row["condition"] for row in rows) != Counter(config["condition_counts"]):
        raise ValueError("allocation mismatch")
    gate = json.loads((ROOT / "artifacts/fixtures/GATE2_PASS.json").read_text(encoding="utf-8"))
    if gate["status"] != "PASS":
        raise ValueError("fixture gate missing")
    return freeze, config

def response_check(response, model):
    for key in ("text", "model_id", "revision"):
        if key not in response:
            raise ValueError(f"adapter response lacks {key}")
    if response["model_id"] != model["model_id"] or response["revision"] != model["revision"]:
        raise ValueError("actual model does not match frozen identity")

def infer(adapter, messages, model, max_tokens):
    if INFERENCE_DIR is None:
        raise ValueError("inference persistence directory not initialized")
    responses, pending = [None] * len(messages), []
    for index, prompt in enumerate(messages):
        payload = {"messages": prompt, "model": model, "max_new_tokens": max_tokens, "temperature": 0.0}
        lineage = digest(payload)
        folder = INFERENCE_DIR / lineage
        folder.mkdir(parents=True, exist_ok=True)
        if not (folder / "request.json").exists():
            write_new(folder / "request.json", payload)
        if (folder / "response.json").exists():
            responses[index] = json.loads((folder / "response.json").read_text(encoding="utf-8"))
        else:
            attempt = len(list(folder.glob("attempt_*.json")))
            if attempt >= 3:
                raise RuntimeError("maximum two infrastructure retries exceeded: " + lineage)
            write_new(folder / f"attempt_{attempt:02d}.json", {"lineage_id": lineage, "attempt": attempt,
                      "request_sha256": digest(payload), "started_utc": now()})
            pending.append((index, prompt, folder, attempt))
    if pending:
        try:
            generated = adapter.generate_batch([item[1] for item in pending], max_new_tokens=max_tokens, temperature=0.0)
            if len(generated) != len(pending):
                raise ValueError("batch denominator mismatch")
            for (index, _, folder, _), response in zip(pending, generated):
                response_check(response, model)
                write_new(folder / "response.json", response)
                responses[index] = response
        except Exception as exc:
            for _, _, folder, attempt in pending:
                write_new(folder / f"failure_{attempt:02d}.json", {"error_type": type(exc).__name__, "error": str(exc), "recorded_utc": now()})
            raise
    for response in responses:
        response_check(response, model)
    return responses

def run_stage(run_dir, phase, adapter, stage="discovery", batch_size=8):
    global INFERENCE_DIR
    freeze, config = preflight()
    run_dir = Path(run_dir)
    units = allocation(stage)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        if phase != "agent":
            raise ValueError("agent stage must initialize run")
        if stage == "discovery":
            pilot = ROOT / "PILOT_PASS.json"
            if not pilot.exists() or json.loads(pilot.read_text(encoding="utf-8"))["status"] != "PASS":
                raise ValueError("verified pilot required before discovery")
        run_dir.mkdir(parents=True, exist_ok=False)
        manifest = {"experiment_id": "Final Praxis 001", "stage": stage,
                    "protocol_sha256": file_hash(ROOT / "FROZEN_PROTOCOL.json"),
                    "created_utc": now(), "units": units, "config": config,
                    "allocation_sha256": digest(units), "frozen_artifacts": freeze["artifact_hashes"]}
        write_new(manifest_path, manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["protocol_sha256"] != file_hash(ROOT / "FROZEN_PROTOCOL.json") or manifest["units"] != units:
        raise ValueError("run manifest differs from frozen protocol/allocation")
    if manifest["stage"] != stage:
        raise ValueError("stage mismatch")
    if (run_dir / "COMPLETE.json").exists():
        raise ValueError("completed runs are immutable")
    INFERENCE_DIR = run_dir / "raw/inference"
    pending = [unit for unit in units if not (run_dir / "raw" / phase / (unit["instance_id"] + ".json")).exists()]
    for offset in range(0, len(pending), batch_size):
        batch = pending[offset:offset + batch_size]
        if phase == "agent":
            specs = [instantiate(unit["task_id"], unit["instance_id"]) for unit in batch]
            messages = [action_messages(spec, unit["instance_id"]) for spec, unit in zip(specs, batch)]
            missing = [(i, unit) for i, unit in enumerate(batch) if not (run_dir / "raw/actions" / (unit["instance_id"] + ".json")).exists()]
            generated = infer(adapter, [messages[i] for i, _ in missing], config["agent"], config["action_max_new_tokens"]) if missing else []
            for (i, unit), response in zip(missing, generated):
                write_new(run_dir / "raw/actions" / (unit["instance_id"] + ".json"),
                          {"unit": unit, "messages": messages[i], "response": response, "recorded_utc": now()})
            responses = [json.loads((run_dir / "raw/actions" / (unit["instance_id"] + ".json")).read_text(encoding="utf-8"))["response"] for unit in batch]
            partial = []
            for spec, unit, response in zip(specs, batch, responses):
                natural_state, actions, natural_receipts, error = execute_actions(spec, response["text"])
                stressed_state, scripted, mutations = controlled_state(spec, unit["condition"])
                record = public_record(spec, unit, actions, visible_receipt(stressed_state, actions))
                partial.append({**unit, "spec": asdict(spec), "initial_state_sha256": digest(spec.initial_state),
                    "action_response": response, "action_parse_error": error,
                    "natural_state": natural_state, "natural_receipts": natural_receipts,
                    "natural_verdict": asdict(verify(spec, natural_state)),
                    "final_state": stressed_state, "final_state_sha256": digest(stressed_state),
                    "controlled_scripted_actions": scripted, "controlled_mutations": mutations,
                    "public_record": record, "verdict": asdict(verify(spec, stressed_state)),
                    "claim_messages": claim_messages(record)})
            claims = infer(adapter, [item["claim_messages"] for item in partial], config["agent"], config["claim_max_new_tokens"])
            for item, claim in zip(partial, claims):
                parsed, error = parse_decision(claim["text"], claim=True)
                item.update(claim_response=claim, claim_decision=parsed, claim_parse_error=error,
                            protocol_sha256=manifest["protocol_sha256"], recorded_utc=now())
                write_new(run_dir / "raw/agent" / (item["instance_id"] + ".json"), item)
        elif phase == "judge":
            records = [json.loads((run_dir / "raw/agent" / (unit["instance_id"] + ".json")).read_text(encoding="utf-8")) for unit in batch]
            messages = [judge_messages(item["public_record"], item["claim_response"]["text"]) for item in records]
            responses = infer(adapter, messages, config["judge"], config["judge_max_new_tokens"])
            for unit, prompt, response in zip(batch, messages, responses):
                parsed, error = parse_decision(response["text"])
                write_new(run_dir / "raw/judge" / (unit["instance_id"] + ".json"),
                    {**unit, "response": response, "messages": prompt, "decision": parsed,
                     "parse_error": error, "protocol_sha256": manifest["protocol_sha256"], "recorded_utc": now()})
        else:
            raise ValueError(phase)
        print(json.dumps({"experiment": "001", "phase": phase, "completed_new": min(offset + batch_size, len(pending)), "total_pending_at_start": len(pending)}), flush=True)
    if phase == "judge":
        diagnostic = []
        for task_id in sorted({unit["task_id"] for unit in units}):
            for condition in ("clean_success", "collateral_damage"):
                matching = [unit for unit in units if unit["task_id"] == task_id and unit["condition"] == condition]
                if matching:
                    diagnostic.append(matching[0])
        diagnostic = [unit for unit in diagnostic if not (run_dir / "raw/full_state_judge" / (unit["instance_id"] + ".json")).exists()]
        for offset in range(0, len(diagnostic), batch_size):
            batch = diagnostic[offset:offset + batch_size]
            messages = []
            for unit in batch:
                agent = json.loads((run_dir / "raw/agent" / (unit["instance_id"] + ".json")).read_text(encoding="utf-8"))
                record = {**agent["public_record"], "authoritative_final_state": agent["final_state"]}
                messages.append(judge_messages(record, agent["claim_response"]["text"]))
            for unit, prompt, response in zip(batch, messages, infer(adapter, messages, config["judge"], config["judge_max_new_tokens"])):
                parsed, error = parse_decision(response["text"])
                write_new(run_dir / "raw/full_state_judge" / (unit["instance_id"] + ".json"),
                    {**unit, "messages": prompt, "response": response, "decision": parsed,
                     "parse_error": error, "protocol_sha256": manifest["protocol_sha256"], "recorded_utc": now()})
    return {"phase": phase, "units": len(units), "run_dir": str(run_dir)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["agent", "judge"], default="agent")
    parser.add_argument("--stage", choices=["pilot", "discovery"], default="discovery")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--endpoint")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _, config = preflight()
    if args.dry_run:
        print(json.dumps({"status": "PREFLIGHT_PASS", "stage": args.stage, "units": len(allocation(args.stage)), "config": config}, indent=2))
        return
    if args.run_dir is None:
        parser.error("--run-dir is required")
    from final_praxis.shared.model_adapter import HTTPAdapter, TransformersAdapter
    model = config["agent" if args.phase == "agent" else "judge"]
    adapter = HTTPAdapter(args.endpoint, model["model_id"], model["revision"]) if args.endpoint else TransformersAdapter(model["model_id"], model["revision"], seed=20260908)
    print(json.dumps(run_stage(args.run_dir, args.phase, adapter, args.stage, args.batch_size)))

if __name__ == "__main__":
    main()
