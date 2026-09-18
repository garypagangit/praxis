"""Score frozen CTI question/evidence pairs with the published MiniLM reranker.

This is a relevance component, not a reproduction of full CRAG or CoRM-RAG.
Each JSONL result is resumable only under an identical data-file hash and spec.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time


MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
MODEL_FILES = [
    "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "vocab.txt",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_completed(path, input_sha, spec_sha, row_hashes):
    if not path.exists():
        return {}
    completed = {}
    with path.open("rb+") as f:
        while True:
            start = f.tell()
            line = f.readline()
            if not line:
                break
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if not line.endswith(b"\n") and not f.read(1):
                    f.truncate(start)
                    break
                raise RuntimeError(f"Corrupt completed record at byte {start}")
            item_id = str(record["id"])
            if item_id in completed:
                raise RuntimeError(f"Duplicate completed id {item_id}")
            if record.get("input_sha256") != input_sha or record.get("spec_sha256") != spec_sha:
                raise RuntimeError("Resume refused: data file or inference specification changed")
            if record.get("input_row_sha256") != row_hashes.get(item_id):
                raise RuntimeError(f"Resume refused: unknown or changed row {item_id}")
            completed[item_id] = record
            if not line.endswith(b"\n"):
                f.seek(0, 2)
                f.write(b"\n")
                break
    return completed


def main():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=here / "data_relevance_options.jsonl")
    p.add_argument("--output", type=Path, default=here / "relevance_options_scores.jsonl")
    p.add_argument("--metadata", type=Path, default=here / "relevance_options_metadata.json")
    p.add_argument("--cache-dir", type=Path, default=Path("C:/w/cti_checker_model_cache_20260918"))
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--max-length", type=int, default=512)
    args = p.parse_args()
    if min(args.batch_size, args.threads, args.max_length) < 1:
        p.error("batch-size, threads, and max-length must be positive")

    started = time.perf_counter()
    input_sha = sha256_file(args.input)
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    row_by_id = {}
    row_hashes = {}
    for row in rows:
        item_id = str(row["id"])
        if item_id in row_by_id:
            raise ValueError(f"Duplicate input id {item_id}")
        if not isinstance(row.get("question"), str) or not row["question"].strip():
            raise ValueError(f"Missing question for {item_id}")
        if not row.get("evidence") or not all(isinstance(e.get("text"), str) and e["text"].strip() for e in row["evidence"]):
            raise ValueError(f"Missing evidence text for {item_id}")
        row_by_id[item_id] = row
        row_hashes[item_id] = canonical_hash(row)

    spec = {
        "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
        "question_input": "original question plus all displayed options sorted by letter; no answer keys, labels, source identifiers or outcomes",
        "document_input": "one original evidence text per pair, input order preserved",
        "score": "raw sequence-classification logit; no sigmoid or calibration",
        "max_length": args.max_length, "truncation": "longest_first",
        "padding": "longest in batch", "device": "cpu", "dtype": "float32",
        "torch_threads": args.threads, "batch_size": args.batch_size,
        "aggregation": ["max", "mean", "population_std", "min"],
        "timing": "inference/tokenization batch time divided equally over its pairs; excludes model load",
        "implementation_sha256": sha256_file(__file__),
    }
    spec_sha = canonical_hash(spec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = read_completed(args.output, input_sha, spec_sha, row_hashes)
    pending_rows = [r for r in rows if str(r["id"]) not in completed]
    if not pending_rows:
        print(json.dumps({"status": "ALREADY_COMPLETE", "questions": len(rows), "output": str(args.output)}), flush=True)
        return

    import torch
    import transformers
    import huggingface_hub
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(20260918)
    snapshot = Path(snapshot_download(
        MODEL_ID, revision=MODEL_REVISION, cache_dir=str(args.cache_dir),
        allow_patterns=MODEL_FILES,
    ))
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False, use_safetensors=True,
    ).to("cpu").float().eval()
    model_hashes = {name: sha256_file(snapshot / name) for name in MODEL_FILES if (snapshot / name).exists()}
    metadata = {
        "status": "RUNNING", "started_utc": utc_now(), "input_path": str(args.input.resolve()),
        "input_sha256": input_sha, "spec_sha256": spec_sha, "spec": spec,
        "model_snapshot": str(snapshot), "model_file_sha256": model_hashes,
        "versions": {"torch": torch.__version__, "transformers": transformers.__version__, "huggingface_hub": huggingface_hub.__version__},
        "questions_total": len(rows), "questions_previously_completed": len(completed),
        "pairs_total": sum(len(r["evidence"]) for r in rows),
        "elapsed_model_setup_seconds": time.perf_counter() - started,
        "limitations": "Published general relevance model; not CRAG/CoRM, utility probability, CTI-trained verifier or new answer generation.",
    }
    write_json(args.metadata, metadata)
    print(json.dumps({"status": "MODEL_READY", "pending_questions": len(pending_rows), "model_revision": MODEL_REVISION}), flush=True)

    pairs = [(str(row["id"]), i, row["question"], ev["text"]) for row in pending_rows for i, ev in enumerate(row["evidence"])]
    partial = {}
    inference_started = time.perf_counter()
    last_progress = inference_started
    with args.output.open("a", encoding="utf-8", newline="\n") as out:
        for offset in range(0, len(pairs), args.batch_size):
            batch = pairs[offset:offset + args.batch_size]
            batch_started = time.perf_counter()
            queries = [x[2] for x in batch]
            documents = [x[3] for x in batch]
            untruncated = tokenizer(queries, documents, padding=False, truncation=False)
            original_lengths = [len(x) for x in untruncated["input_ids"]]
            encoded = tokenizer(queries, documents, padding=True, truncation=True,
                                max_length=args.max_length, return_tensors="pt")
            actual_lengths = encoded["attention_mask"].sum(dim=1).tolist()
            with torch.inference_mode():
                logits = model(**encoded).logits.reshape(-1).tolist()
            per_pair_seconds = (time.perf_counter() - batch_started) / len(batch)
            for pair, logit, orig_len, actual_len in zip(batch, logits, original_lengths, actual_lengths):
                item_id, evidence_index = pair[:2]
                p_item = partial.setdefault(item_id, {"logits": [], "original_tokens": [], "encoded_tokens": [], "elapsed_seconds": 0.0})
                if evidence_index != len(p_item["logits"]):
                    raise AssertionError("Evidence order changed")
                p_item["logits"].append(float(logit))
                p_item["original_tokens"].append(orig_len)
                p_item["encoded_tokens"].append(actual_len)
                p_item["elapsed_seconds"] += per_pair_seconds
                if len(p_item["logits"]) == len(row_by_id[item_id]["evidence"]):
                    scores = p_item["logits"]
                    record = {
                        "id": row_by_id[item_id]["id"], "input_sha256": input_sha,
                        "input_row_sha256": row_hashes[item_id], "spec_sha256": spec_sha,
                        "model_revision": MODEL_REVISION, "evidence_count": len(scores),
                        "logits": scores, "max": max(scores), "mean": statistics.mean(scores),
                        "std": statistics.pstdev(scores), "min": min(scores),
                        "token_counts": p_item["original_tokens"],
                        "encoded_token_counts": p_item["encoded_tokens"],
                        "truncated_pair_count": sum(a > b for a, b in zip(p_item["original_tokens"], p_item["encoded_tokens"])),
                        "truncated_token_count": sum(a - b for a, b in zip(p_item["original_tokens"], p_item["encoded_tokens"])),
                        "elapsed_seconds": p_item["elapsed_seconds"],
                    }
                    out.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                    out.flush()
                    completed[item_id] = record
                    del partial[item_id]
            if time.perf_counter() - last_progress >= 20:
                print(json.dumps({"status": "SCORING", "completed_questions": len(completed), "questions_total": len(rows), "new_pairs_scored": offset + len(batch), "inference_seconds": round(time.perf_counter() - inference_started, 2)}), flush=True)
                last_progress = time.perf_counter()

    if partial or len(completed) != len(rows):
        raise AssertionError("Incomplete scoring")
    metadata.update({
        "status": "COMPLETE", "finished_utc": utc_now(), "questions_completed": len(completed),
        "new_pairs_scored": len(pairs), "this_run_inference_seconds": time.perf_counter() - inference_started,
        "this_run_total_seconds": time.perf_counter() - started,
        "all_rows_allocated_inference_seconds": sum(r["elapsed_seconds"] for r in completed.values()),
        "pairs_truncated": sum(r["truncated_pair_count"] for r in completed.values()),
        "tokens_truncated": sum(r["truncated_token_count"] for r in completed.values()),
        "output_sha256": sha256_file(args.output),
    })
    write_json(args.metadata, metadata)
    print(json.dumps({"status": "COMPLETE", "questions": len(rows), "pairs": metadata["pairs_total"], "pairs_truncated": metadata["pairs_truncated"], "seconds": round(metadata["this_run_total_seconds"], 2)}), flush=True)


if __name__ == "__main__":
    main()
