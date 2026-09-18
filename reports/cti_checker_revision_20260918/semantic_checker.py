"""Pinned, CPU-only NLI diagnostic with a mandatory synthetic qualification gate.

Scoring reads explicitly projected question/option/evidence records only. It never
reads answer labels, released sources, generator correctness, or policy cutoffs.
The question-to-hypothesis bridge is an unvalidated adaptation, not proof of truth.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MODEL_ID = "cross-encoder/nli-deberta-v3-xsmall"
REVISION = "a150876415327c80daeff35ca6f68f5ed8cf5c24"
LABELS = ["contradiction", "entailment", "neutral"]
MAX_LENGTH = 512
TEMPLATE = 'The answer to the question "{question}" is "{option}".'
METHOD = "question_answer_template_individual_fact_nli_v1"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def qualification_cases():
    ordinary = [
        ("ordinary_entailment_1", "A man is eating pizza.", "A man eats something.", "entailment"),
        ("ordinary_contradiction_1", "A man is eating pizza.", "No person is eating anything.", "contradiction"),
        ("ordinary_entailment_2", "The only operating system installed on this server is Linux.",
         "Linux is installed on this server.", "entailment"),
        ("ordinary_contradiction_2", "The only operating system installed on this server is Linux.",
         "Linux is not installed on this server.", "contradiction"),
    ]
    bridges = [
        ("template_entailment_1", "The operating system installed on this server is Linux, not Windows.",
         "Which operating system is installed on this server?", "Linux", "entailment"),
        ("template_contradiction_1", "The operating system installed on this server is Linux, not Windows.",
         "Which operating system is installed on this server?", "Windows", "contradiction"),
        ("template_entailment_2", "The server accepts connections on port 443 and does not accept connections on port 80.",
         "Which port accepts connections on the server?", "Port 443", "entailment"),
        ("template_contradiction_2", "The server accepts connections on port 443 and does not accept connections on port 80.",
         "Which port accepts connections on the server?", "Port 80", "contradiction"),
    ]
    return ([{"id": i, "premise": p, "hypothesis": h, "expected": e} for i, p, h, e in ordinary]
            + [{"id": i, "premise": p, "hypothesis": TEMPLATE.format(question=q, option=o),
                "expected": e} for i, p, q, o, e in bridges])


def validate_inputs(path):
    records, seen = [], set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if set(r) - {"id", "question", "options", "evidence", "required_options"}:
            raise ValueError("Input has unapproved fields; project safe inputs first")
        if not isinstance(r["id"], str) or r["id"] in seen:
            raise ValueError("Missing/duplicate question ID")
        seen.add(r["id"])
        if not isinstance(r["question"], str) or not r["question"].strip():
            raise ValueError("Question is not a nonempty string")
        if set(r["options"]) != set("ABCD") or any(not isinstance(v, str)
                                                     for v in r["options"].values()):
            raise ValueError("Expected exactly four string-valued options")
        if not isinstance(r["evidence"], list) or not r["evidence"]:
            raise ValueError("Evidence list is empty")
        for fact in r["evidence"]:
            if set(fact) - {"text", "kind", "score"} or not isinstance(fact["text"], str) or not fact["text"].strip():
                raise ValueError("Unapproved fact fields or empty text")
        required = r.get("required_options", list("ABCD"))
        if not isinstance(required, list) or not required or len(required) != len(set(required)) or set(required) - set("ABCD"):
            raise ValueError("Invalid required options")
        if any(not r["options"][option].strip() for option in required):
            raise ValueError("A requested option is empty")
        records.append(r)
    if not records:
        raise ValueError("No input records")
    return records


def load_model(cache_dir, threads):
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    torch.set_num_threads(threads)
    snapshot = Path(snapshot_download(MODEL_ID, revision=REVISION, cache_dir=cache_dir,
        allow_patterns=["README.md", "config.json", "model.safetensors", "tokenizer.json",
                        "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json", "spm.model"]))
    if snapshot.name != REVISION:
        raise ValueError("Snapshot revision did not match pinned revision")
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(snapshot, local_files_only=True,
        trust_remote_code=False, use_safetensors=True).cpu().eval()
    actual = [model.config.id2label[i].lower() for i in range(3)]
    if actual != LABELS:
        raise ValueError(f"Unexpected model label mapping: {actual}")
    model_files = {p.name: sha(p) for p in sorted(snapshot.iterdir()) if p.is_file()}
    return tokenizer, model, model_files


def infer_pairs(tokenizer, model, pairs, batch_size):
    import torch
    output = []
    for start in range(0, len(pairs), batch_size):
        batch = pairs[start:start + batch_size]
        first, second = zip(*batch)
        uncut = tokenizer(list(first), list(second), truncation=False, padding=False)
        lengths = [len(x) for x in uncut["input_ids"]]
        encoded = tokenizer(list(first), list(second), truncation="longest_first", max_length=MAX_LENGTH,
                            padding=True, return_tensors="pt")
        with torch.inference_mode():
            values = torch.softmax(model(**encoded).logits.float(), dim=-1).cpu().tolist()
        for value, n in zip(values, lengths):
            if len(value) != 3 or not all(math.isfinite(v) for v in value):
                raise ValueError("Non-finite/malformed NLI probabilities")
            output.append({**dict(zip(LABELS, value)), "input_tokens_before_truncation": n,
                           "truncated": n > MAX_LENGTH,
                           "prediction": LABELS[max(range(3), key=lambda j: value[j])]})
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--qualification", type=Path, required=True)
    p.add_argument("--qualification-only", action="store_true")
    p.add_argument("--cache-dir", default="C:/w/cti_checker_model_cache_20260918")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--threads", type=int, default=4)
    args = p.parse_args()
    if not args.qualification_only and not all([args.inputs, args.out]):
        p.error("Scoring requires --inputs and --out")
    if args.batch_size < 1 or args.threads < 1:
        p.error("Batch size and threads must be positive")
    for target in [args.receipt, args.qualification, args.out]:
        if target and target.exists():
            raise FileExistsError(f"Refusing to overwrite {target}")
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    tokenizer, model, model_files = load_model(args.cache_dir, args.threads)
    loaded_seconds = time.perf_counter() - start
    cases = qualification_cases()
    answers = infer_pairs(tokenizer, model, [(r["premise"], r["hypothesis"]) for r in cases], args.batch_size)
    case_results = [{**r, **a, "passed": a["prediction"] == r["expected"]}
                    for r, a in zip(cases, answers)]
    passed = all(r["passed"] for r in case_results)
    qualification = {"status": "PASS" if passed else "FAIL_STOP_BEFORE_DATA",
        "cases": case_results, "required_correct": 8, "correct": sum(r["passed"] for r in case_results),
        "gate_fixed_before_dataset_scores": True, "model_id": MODEL_ID, "revision": REVISION,
        "template": TEMPLATE, "cases_sha256": object_sha(cases)}
    write_new(args.qualification, qualification)
    receipt = {"schema_version": 1, "method": METHOD,
        "model_id": MODEL_ID, "revision": REVISION, "template": TEMPLATE,
        "labels": LABELS, "device": "cpu", "dtype": "float32", "batch_size": args.batch_size,
        "threads": args.threads, "max_length": MAX_LENGTH, "truncation": "longest_first",
        "model_files_sha256": model_files, "code_sha256": sha(__file__),
        "qualification_sha256": sha(args.qualification), "model_load_seconds": loaded_seconds,
        "created_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "versions": {k: importlib.metadata.version(k) for k in ("torch", "transformers", "huggingface-hub", "tokenizers")}}
    if not passed or args.qualification_only:
        receipt.update(status="QUALIFIED_NOT_SCORED" if passed else "QUALIFICATION_FAILED_NO_DATA_READ",
                       dataset_rows_read=0, scored_pairs=0, total_seconds=time.perf_counter() - start)
        write_new(args.receipt, receipt)
        print(json.dumps({"status": receipt["status"], "qualification_correct": qualification["correct"]}))
        return 0 if passed else 2
    # This is intentionally after the qualification gate: no dataset is opened on failure.
    records = validate_inputs(args.inputs)
    total_pairs, truncated_pairs = 0, 0
    inference_start = time.perf_counter()
    with args.out.open("x", encoding="utf-8") as f:
        for i, r in enumerate(records):
            options = sorted(r.get("required_options", list("ABCD")))
            hypotheses = {k: TEMPLATE.format(question=r["question"], option=r["options"][k]) for k in options}
            pairs = [(e["text"], hypotheses[k]) for k in options for e in r["evidence"]]
            pair_results = infer_pairs(tokenizer, model, pairs, args.batch_size)
            total_pairs += len(pair_results)
            truncated_pairs += sum(v["truncated"] for v in pair_results)
            n_facts = len(r["evidence"])
            summary = {}
            for j, k in enumerate(options):
                facts = [{"fact_index": n, **v} for n, v in enumerate(pair_results[j*n_facts:(j+1)*n_facts])]
                best = max(range(n_facts), key=lambda n: (facts[n]["entailment"], -n))
                summary[k] = {"max_entailment": facts[best]["entailment"],
                    "max_contradiction": max(v["contradiction"] for v in facts),
                    "contradiction_at_strongest_support": facts[best]["contradiction"],
                    "strongest_support_fact": best, "per_fact": facts}
            row = {"id": r["id"], "input_sha256": object_sha(r), "hypotheses": hypotheses,
                   "facts": [{"index": j, "text_sha256": hashlib.sha256(e["text"].encode()).hexdigest()}
                             for j, e in enumerate(r["evidence"])], "options": summary}
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            if (i+1) % 25 == 0 or i+1 == len(records):
                f.flush()
                print(json.dumps({"scored_questions": i+1, "total_questions": len(records),
                                  "pairs": total_pairs, "seconds": time.perf_counter()-inference_start}), flush=True)
    receipt.update(status="COMPLETE", dataset_rows_read=len(records), scored_pairs=total_pairs,
        truncated_pairs=truncated_pairs, input_sha256=sha(args.inputs), output_sha256=sha(args.out),
        inference_seconds=time.perf_counter()-inference_start, total_seconds=time.perf_counter()-start,
        completed_utc=datetime.now(timezone.utc).isoformat(), labels_or_outcomes_read=False,
        scores_are_not_calibrated_probabilities_of_correctness=True)
    write_new(args.receipt, receipt)
    print(json.dumps({"status": "COMPLETE", "records": len(records), "pairs": total_pairs,
                      "truncated_pairs": truncated_pairs}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
