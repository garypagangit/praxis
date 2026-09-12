"""Read-only audit of private run artifacts; prints aggregate diagnostics only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import boto3
from botocore.config import Config

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import run

bucket = "praxis-garypagan-272615233626-us-east-1"
prefix = "final-praxis/20260912/runs/fp005-20260912-37fdd3f/outputs/"
destination = HERE.parents[1] / "outputs" / "fp005_audit_20260912"
destination.mkdir(parents=True, exist_ok=True)
s3 = boto3.Session(profile_name="praxis-build", region_name="us-east-1").client(
    "s3", config=Config(connect_timeout=10, read_timeout=30, retries={"total_max_attempts": 2}))
config, sources, identity = run.load_protocol()
names = ["prepared.json", "teacher_complete.json", "teacher_generations.jsonl", "distillation_data.json", "eval.json"]
names += [f"generations_{a}.jsonl" for a in config["arms"]]
names += [f"checkpoints/{a}/train_complete.json" for a in ("base_kd", "er_kd", "er_replay")]


def fetch(name):
    try:
        obj = s3.get_object(Bucket=bucket, Key=prefix + name)
    except s3.exceptions.NoSuchKey:
        return name, None
    body = obj["Body"].read()
    path = destination / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return name, {"bytes": len(body), "sha256": run.digest_bytes(body),
                  "last_modified": obj["LastModified"].isoformat(), "etag": obj["ETag"]}


with ThreadPoolExecutor(max_workers=5) as pool:
    receipts = dict(pool.map(fetch, names))
audit = {"observed_utc": datetime.now(timezone.utc).isoformat(), "protocol_id": identity,
         "s3_uri": "s3://" + bucket + "/" + prefix, "receipts": receipts,
         "limitations": ["live partial evaluation snapshots are not outcome estimates",
                         "numeric-answer verification does not prove intermediate reasoning",
                         "no semantic safety conclusions before both judges and manual review"]}
panels = run.read_json(destination / "eval.json") if receipts["eval.json"] else []
expected = {r["id"]: r for r in panels}
if receipts["prepared.json"]:
    run.verify_cpu_reference(run.read_json(destination / "prepared.json"))
    audit["frozen_data_and_selection_verified"] = True
if receipts["teacher_complete.json"] and receipts["distillation_data.json"]:
    manifest = run.read_json(destination / "teacher_complete.json")
    rows = run.read_json(destination / "distillation_data.json")
    pool = run.read_json(HERE.parents[1] / "outputs" / "fp005_prepare_20260912" / "teacher_pool.json")
    pool_by_id = {r["id"]: r for r in pool}
    if manifest["protocol_id"] != identity or manifest["data_sha256"] != receipts["distillation_data.json"]["sha256"]:
        raise ValueError("Teacher artifact identity/hash mismatch")
    if len(rows) != manifest["accepted"] or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Teacher count or unique-ID mismatch")
    generations = run.read_jsonl(destination / "teacher_generations.jsonl")
    if [r["id"] for r in generations] != [r["id"] for r in pool[:len(generations)]]:
        raise ValueError("Teacher generation order differs from the fixed pool")
    if [r["id"] for r in rows] != [r["id"] for r in generations if r["accepted"]][:config["teacher_target"]]:
        raise ValueError("Distillation data is not the first accepted teacher examples")
    if not all(r["accepted"] and not r["truncated"] and r["training_length_ok"] and
               r["id"] in pool_by_id and r["prompt"] == pool_by_id[r["id"]]["prompt"] and
               run.numeric_answer(r["response"]) == pool_by_id[r["id"]]["answer"] for r in rows):
        raise ValueError("Teacher eligibility does not match frozen source and acceptance rule")
    eval_math = {run.normalize(r["prompt"]) for r in panels if r["panel"] == "math"}
    audit["teacher"] = {"accepted": len(rows), "attempts": manifest["attempts"],
        "data_hash_verified": True, "eligibility_verified": True, "first_accepted_selection_verified": True,
        "exact_prompt_overlap_with_test": sum(run.normalize(r["prompt"]) in eval_math for r in rows),
        "peak_gpu_bytes": manifest["peak_gpu_bytes"]}
    if "--tokenizer-check" in sys.argv:
        from transformers import AutoTokenizer
        entry = sources["models"]["base"]
        tokenizer = AutoTokenizer.from_pretrained(entry["id"], revision=entry["revision"], trust_remote_code=False,
                                                  local_files_only=True)
        encoded = [run.encode_training(tokenizer, row, config["sequence_length"]) for row in rows]
        audit["teacher"].update({"completion_masks_checked": len(encoded),
            "maximum_sequence_length": max(len(r["input_ids"]) for r in encoded),
            "minimum_completion_tokens": min(sum(t != -100 for t in r["labels"]) for r in encoded)})
audit["training"] = {}
for arm in ("base_kd", "er_kd", "er_replay"):
    name = f"checkpoints/{arm}/train_complete.json"
    if not receipts[name]:
        continue
    training = run.read_json(destination / name)
    key = "base" if arm == "base_kd" else "extended_refusal"
    if (training["protocol_id"] != identity or training["arm"] != arm or
        training["base"] != sources["models"][key] or not training["adapter_l2_change"] > 0 or
        training["steps"] != config["train_steps"] or
        training["examples_seen"] != config["train_steps"] * config["grad_accumulation"] or
        training["teacher_data_sha256"] != receipts["distillation_data.json"]["sha256"]):
        raise ValueError("Training metadata does not match the frozen design")
    checkpoint_pending = False
    for filename, expected_hash in training["adapter_files"].items():
        artifact = f"checkpoints/{arm}/{filename}"
        _, receipt = fetch(artifact)
        if receipt is None:
            checkpoint_pending = True
            break
        if receipt["sha256"] != expected_hash:
            raise ValueError("Serialized adapter differs from training manifest")
        receipts[artifact] = receipt
    if checkpoint_pending:
        audit["training"][arm] = {"status": "checkpoint_upload_pending"}
        continue
    from safetensors import safe_open
    import torch
    with safe_open(destination / f"checkpoints/{arm}/adapter_model.safetensors", framework="pt", device="cpu") as f:
        tensors = {k: f.get_tensor(k).float() for k in f.keys()}
    if not all(torch.isfinite(t).all() for t in tensors.values()):
        raise ValueError("Nonfinite serialized adapter")
    b_matrices = [t for name, t in tensors.items() if "lora_B" in name]
    b_squared_norm = sum(float(t.square().sum()) for t in b_matrices)
    if not b_matrices or not b_squared_norm > 0:
        raise ValueError("Serialized LoRA B matrices did not move from zero initialization")
    record = {k: training[k] for k in ("steps", "examples_seen", "replay_examples_seen", "supervised_tokens",
        "trainable_parameters", "adapter_l2_change", "loss_first4", "loss_last4", "peak_gpu_bytes")}
    record.update({"serialized_files_verified": True, "serialized_tensor_count": len(tensors),
        "nonzero_lora_b_matrices": sum(bool(t.any()) for t in b_matrices), "lora_b_l2_norm": b_squared_norm ** .5})
    audit["training"][arm] = record
audit["arms"] = {}
for arm in config["arms"]:
    filename = f"generations_{arm}.jsonl"
    if not receipts[filename]:
        continue
    text = (destination / filename).read_text(encoding="utf-8")
    lines = text.splitlines()
    partial = bool(lines and not text.endswith("\n"))
    if partial:
        lines = lines[:-1]
    rows = [json.loads(line) for line in lines if line.strip()]
    if any(r["protocol_id"] != identity or r["arm"] != arm or r["id"] not in expected or
           r["prompt"] != expected[r["id"]]["prompt"] for r in rows):
        raise ValueError("Evaluation records disagree with frozen examples/protocol")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate evaluation records")
    record = {"completed": len(rows), "expected": len(panels), "ignored_partial_trailing_record": partial}
    for panel in ("harm", "benign", "math"):
        subset = [r for r in rows if r["panel"] == panel]
        record[panel] = {"n": len(subset), "truncated": sum(r["truncated"] for r in subset),
                         "empty": sum(not r["response"].strip() for r in subset)}
        if panel == "math":
            record[panel]["final_answer_correct_untruncated"] = sum(
                not r["truncated"] and run.numeric_answer(r["response"]) == expected[r["id"]]["answer"] for r in subset)
            record[panel]["correct_but_truncated_diagnostic"] = sum(
                r["truncated"] and run.numeric_answer(r["response"]) == expected[r["id"]]["answer"] for r in subset)
            record[panel]["missing_final_answer_diagnostic"] = sum(run.numeric_answer(r["response"]) is None for r in subset)
    audit["arms"][arm] = record
run.write_json(HERE / "cloud" / "execution" / "artifact_audit.json", audit)
print(json.dumps({k: v for k, v in audit.items() if k != "receipts"}, indent=2))
