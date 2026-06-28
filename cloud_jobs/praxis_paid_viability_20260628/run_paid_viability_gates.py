from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_ID = os.environ.get("MODEL_ID", "meta-llama/Llama-3.2-3B-Instruct")
USER_AGENT = "praxis-paid-viability-20260628"

HALLUHARD_URL = "https://raw.githubusercontent.com/epfml/halluhard/main/research_questions/data/research_questions_all.jsonl"
SWE_ROWS_URL = "https://datasets-server.huggingface.co/rows?dataset=Fsoft-AIC%2FSWE-EVO&config=default&split=test&offset=0&length=48"
SWE_DATASET = "Fsoft-AIC/SWE-EVO"
SWE_INSTANCE = "psf__requests_v2.9.0_v2.9.1"
SWE_MODEL = "glm-4p5"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_text(url: str, timeout: int = 90) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def fetch_json(url: str, timeout: int = 90) -> Any:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.json()


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def norm(text: Any) -> str:
    value = "" if text is None else str(text)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def snippet(text: Any, limit: int = 140) -> str:
    value = "" if text is None else str(text)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def ratio(a: Any, b: Any) -> float:
    import difflib

    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def parse_json_object(text: str) -> tuple[dict[str, Any], str | None]:
    stripped = text.strip()
    try:
        obj = json.loads(stripped)
        return obj if isinstance(obj, dict) else {}, None
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(stripped[start : end + 1])
            return obj if isinstance(obj, dict) else {}, None
        except json.JSONDecodeError as exc:
            return {}, str(exc)
    return {}, "no_json_object"


def load_model() -> tuple[Any, Any]:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=os.environ.get("HF_TOKEN"))
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        token=os.environ.get("HF_TOKEN"),
        torch_dtype=dtype,
        device_map="auto",
    )
    model.eval()
    return tokenizer, model


def generate_batch(tokenizer: Any, model: Any, prompts: list[str], max_new_tokens: int) -> list[str]:
    messages = [[{"role": "user", "content": prompt}] for prompt in prompts]
    texts = [
        tokenizer.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
        for message in messages
    ]
    encoded = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=1536)
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.eos_token_id,
        )
    decoded: list[str] = []
    input_lengths = encoded["attention_mask"].sum(dim=1).tolist()
    for idx, length in enumerate(input_lengths):
        decoded.append(tokenizer.decode(output[idx][int(length) :], skip_special_tokens=True))
    return decoded


def content_grounded(claimed_content: Any, abstract: Any, threshold: float = 0.80) -> tuple[bool, float]:
    claim_norm = norm(claimed_content)
    abstract_norm = norm(abstract)
    if claim_norm and claim_norm in abstract_norm:
        return True, 1.0
    score = ratio(claimed_content, abstract)
    return score >= threshold, score


def verify_halluhard_claim(row: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    title_score = ratio(claim.get("claimed_title"), row.get("title"))
    content_ok, content_score = content_grounded(claim.get("claimed_content"), row.get("abstract"))
    claimed_year = str(claim.get("claimed_year", "")).strip()
    year_match = claimed_year == str(row.get("publication_year", "")).strip()
    doi_match = norm(claim.get("claimed_doi")) and norm(claim.get("claimed_doi")) == norm(row.get("doi"))
    arxiv_match = norm(claim.get("claimed_arxiv_id")) and norm(claim.get("claimed_arxiv_id")) == norm(row.get("arxiv_id"))
    source_id_match = bool(doi_match or arxiv_match)
    title_match = title_score >= 0.92
    supported = bool(source_id_match and title_match and year_match and content_ok)
    return {
        "label": "supported" if supported else "hallucinated",
        "source_id_match": source_id_match,
        "title_similarity": title_score,
        "content_similarity": content_score,
        "year_match": year_match,
        "content_grounded": content_ok,
    }


def source_conditioned_prompt(row: dict[str, Any]) -> str:
    doi = row.get("doi") or ""
    arxiv_id = row.get("arxiv_id") or ""
    abstract = snippet(row.get("abstract"), 1200)
    return (
        "You are participating in a citation-grounding benchmark. "
        "Use only the source record below. Return only valid JSON with keys: "
        "claimed_title, claimed_year, claimed_doi, claimed_arxiv_id, claimed_content. "
        "Copy claimed_title, claimed_year, claimed_doi, and claimed_arxiv_id exactly from the source record. "
        "For claimed_content, copy one exact short phrase or sentence from the abstract. "
        "Do not add markdown or commentary.\n\n"
        f"Source title: {row.get('title')}\n"
        f"Publication year: {row.get('publication_year')}\n"
        f"DOI: {doi}\n"
        f"arXiv ID: {arxiv_id}\n"
        f"Abstract excerpt: {abstract}\n"
    )


def f1(rows: list[dict[str, Any]], label: str, pred_key: str) -> dict[str, float]:
    tp = sum(1 for row in rows if row["label"] == label and row[pred_key] == label)
    fp = sum(1 for row in rows if row["label"] != label and row[pred_key] == label)
    fn = sum(1 for row in rows if row["label"] == label and row[pred_key] != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": score}


def classification_metrics(rows: list[dict[str, Any]], pred_key: str) -> dict[str, Any]:
    labels = ["supported", "hallucinated"]
    per_label = {label: f1(rows, label, pred_key) for label in labels}
    return {
        "accuracy": sum(1 for row in rows if row["label"] == row[pred_key]) / len(rows),
        "macro_f1": sum(per_label[label]["f1"] for label in labels) / len(labels),
        "per_label": per_label,
    }


def run_halluhard(outdir: Path, tokenizer: Any, model: Any) -> dict[str, Any]:
    rows = parse_jsonl(fetch_text(HALLUHARD_URL))
    prompts = [source_conditioned_prompt(row) for row in rows]

    generations: list[dict[str, Any]] = []
    started = time.time()
    batch_size = int(os.environ.get("HALLUHARD_BATCH_SIZE", "4"))
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        outputs = generate_batch(tokenizer, model, batch, max_new_tokens=192)
        for offset, output in enumerate(outputs):
            idx = start + offset
            claim, parse_error = parse_json_object(output)
            verification = verify_halluhard_claim(rows[idx], claim)
            field_presence = bool(norm(claim.get("claimed_title")) and (norm(claim.get("claimed_doi")) or norm(claim.get("claimed_arxiv_id"))))
            expected_label = "supported"
            verification_fields = {key: value for key, value in verification.items() if key != "label"}
            generations.append(
                {
                    "idx": idx,
                    "case_type": "source_conditioned_supported",
                    "research_question": snippet(rows[idx].get("research_question"), 220),
                    "gold_title": snippet(rows[idx].get("title"), 220),
                    "raw_output": output,
                    "parse_error": parse_error,
                    "json_valid": parse_error is None,
                    "claimed_title": claim.get("claimed_title", ""),
                    "claimed_year": claim.get("claimed_year", ""),
                    "claimed_doi": claim.get("claimed_doi", ""),
                    "claimed_arxiv_id": claim.get("claimed_arxiv_id", ""),
                    "claimed_content": claim.get("claimed_content", ""),
                    "label": expected_label,
                    "verifier_prediction": verification["label"],
                    "always_supported_prediction": "supported",
                    "field_presence_prediction": "supported" if field_presence else "hallucinated",
                    **verification_fields,
                }
            )
            corrupt_idx = (idx + 1) % len(rows)
            corrupt_verification = verify_halluhard_claim(rows[corrupt_idx], claim)
            corrupt_verification_fields = {key: value for key, value in corrupt_verification.items() if key != "label"}
            generations.append(
                {
                    "idx": idx,
                    "case_type": "shifted_source_negative",
                    "research_question": snippet(rows[corrupt_idx].get("research_question"), 220),
                    "gold_title": snippet(rows[corrupt_idx].get("title"), 220),
                    "raw_output": output,
                    "parse_error": parse_error,
                    "json_valid": parse_error is None,
                    "claimed_title": claim.get("claimed_title", ""),
                    "claimed_year": claim.get("claimed_year", ""),
                    "claimed_doi": claim.get("claimed_doi", ""),
                    "claimed_arxiv_id": claim.get("claimed_arxiv_id", ""),
                    "claimed_content": claim.get("claimed_content", ""),
                    "label": "hallucinated",
                    "verifier_prediction": corrupt_verification["label"],
                    "always_supported_prediction": "supported",
                    "field_presence_prediction": "supported" if field_presence else "hallucinated",
                    **corrupt_verification_fields,
                }
            )

    metrics = classification_metrics(generations, "verifier_prediction")
    always = classification_metrics(generations, "always_supported_prediction")
    field = classification_metrics(generations, "field_presence_prediction")
    supported_predictions = sum(1 for row in generations if row["verifier_prediction"] == "supported")
    expected_supported = [row for row in generations if row["label"] == "supported"]
    supported_expected_pass = sum(1 for row in expected_supported if row["verifier_prediction"] == "supported")
    parse_valid = sum(1 for row in expected_supported if row["json_valid"])
    summary = {
        "generated_utc": utc_now(),
        "status": "SOURCE-CONDITIONED RESPONSE GATE PASS" if supported_expected_pass >= 100 and metrics["macro_f1"] >= max(always["macro_f1"], field["macro_f1"]) + 0.10 else "SOURCE-CONDITIONED RESPONSE GATE MIXED",
        "model_id": MODEL_ID,
        "rows": len(rows),
        "generations": len(expected_supported),
        "evaluation_pairs": len(generations),
        "parse_valid": parse_valid,
        "parse_valid_rate": parse_valid / len(expected_supported),
        "supported_claims": supported_expected_pass,
        "supported_rate": supported_expected_pass / len(expected_supported),
        "supported_predictions": supported_predictions,
        "label_counts": dict(Counter(row["label"] for row in generations)),
        "verifier_metrics": metrics,
        "always_supported_baseline": always,
        "field_presence_baseline": field,
        "wall_seconds": time.time() - started,
        "claim_boundary": "Source-conditioned HalluHard research-lane citation claims from an open local model, plus shifted-source negatives. This is a live response gate for one model, not an all-domain HalluHard result.",
    }
    write_json(outdir / "halluhard_model_response_summary.json", summary)
    with (outdir / "halluhard_model_responses.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "idx",
            "case_type",
            "json_valid",
            "parse_error",
            "label",
            "verifier_prediction",
            "source_id_match",
            "title_similarity",
            "content_similarity",
            "year_match",
            "claimed_title",
            "claimed_year",
            "claimed_doi",
            "claimed_arxiv_id",
            "gold_title",
            "research_question",
            "raw_output",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in generations:
            writer.writerow({field: row.get(field) for field in fields})
    render_halluhard_report(outdir / "HALLUHARD_SOURCE_CONDITIONED_RESPONSE_GATE_20260628.md", summary)
    return summary


def render_halluhard_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PX-011 HalluHard Source-Conditioned Response Gate",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Claim Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Model | `{summary['model_id']}` |",
        f"| Generations | `{summary['generations']}` |",
        f"| Evaluation pairs | `{summary['evaluation_pairs']}` |",
        f"| JSON parse-valid rate | `{summary['parse_valid_rate']:.4f}` |",
        f"| Supported claims | `{summary['supported_claims']}` |",
        f"| Supported rate | `{summary['supported_rate']:.4f}` |",
        f"| Verifier macro F1 | `{summary['verifier_metrics']['macro_f1']:.4f}` |",
        f"| Always-supported macro F1 | `{summary['always_supported_baseline']['macro_f1']:.4f}` |",
        f"| Field-presence macro F1 | `{summary['field_presence_baseline']['macro_f1']:.4f}` |",
        f"| Wall seconds | `{summary['wall_seconds']:.1f}` |",
        "",
        "## Interpretation",
        "",
        "This gate spends real generation compute. A PASS requires the open model to produce enough source-grounded claims and the verifier to beat response-only baselines on matched supported and shifted-source negative cases.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def hf_resolve(path: str) -> str:
    return f"https://huggingface.co/datasets/{SWE_DATASET}/resolve/main/{urllib.parse.quote(path, safe='/')}"


def parse_patch_files(patch: str) -> set[str]:
    files = set()
    for line in patch.splitlines():
        match = re.match(r"diff --git a/(.+?) b/(.+)$", line)
        if match:
            files.add(match.group(2))
    return files


def run_cmd(command: list[str], cwd: Path | None = None, timeout: int = 1800) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "wall_seconds": time.time() - started,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": command,
            "returncode": 124,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
            "wall_seconds": time.time() - started,
            "timeout": True,
        }


def docker_eval(image: str, repo_path: Path, tests: list[str], out_path: Path, timeout: int = 1800) -> dict[str, Any]:
    test_args = " ".join(tests)
    command = [
        "sudo",
        "docker",
        "run",
        "--rm",
        "-v",
        f"{repo_path}:/testbed",
        "-w",
        "/testbed",
        image,
        "bash",
        "-lc",
        f"python -m pytest -q {test_args}",
    ]
    result = run_cmd(command, timeout=timeout)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def apply_patch(repo_path: Path, patch_text: str, label: str) -> dict[str, Any]:
    patch_file = repo_path.parent / f"{label}.patch"
    patch_file.write_text(patch_text, encoding="utf-8")
    if not patch_text.strip():
        return {"applied": True, "check": {"returncode": 0, "stderr": "", "stdout": "", "timeout": False}, "apply": {"returncode": 0, "stderr": "", "stdout": "", "timeout": False}}
    check = run_cmd(["git", "apply", "--check", str(patch_file)], cwd=repo_path, timeout=120)
    if check["returncode"] != 0:
        return {"applied": False, "check": check, "apply": None}
    applied = run_cmd(["git", "apply", str(patch_file)], cwd=repo_path, timeout=120)
    return {"applied": applied["returncode"] == 0, "check": check, "apply": applied}


def cleanup_swe_work(work: Path) -> None:
    for name in ("base", "eval_base", "eval_model", "eval_gold"):
        shutil.rmtree(work / name, ignore_errors=True)


def run_swe_evo(outdir: Path) -> dict[str, Any]:
    started = time.time()
    data = fetch_json(SWE_ROWS_URL)
    rows = [item["row"] for item in data["rows"]]
    row = next(item for item in rows if item["instance_id"] == SWE_INSTANCE)
    preds = fetch_json(hf_resolve(f"SWE-agent/{SWE_MODEL}/preds.json"))
    pred = preds[SWE_INSTANCE]
    work = outdir / "swe_eval_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    pull = run_cmd(["sudo", "docker", "pull", row["image"]], timeout=1800)
    clone = run_cmd(["git", "clone", f"https://github.com/{row['repo']}.git", "base"], cwd=work, timeout=900)
    base_repo = work / "base"
    checkout = run_cmd(["git", "checkout", row["base_commit"]], cwd=base_repo, timeout=300) if base_repo.exists() else {"returncode": 1}
    tests = list(dict.fromkeys((row.get("FAIL_TO_PASS") or []) + (row.get("PASS_TO_PASS") or [])[:10]))

    def copy_repo(name: str) -> Path:
        dst = work / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(base_repo, dst, ignore=shutil.ignore_patterns(".git"))
        return dst

    results: dict[str, Any] = {
        "docker_pull": pull,
        "clone": clone,
        "checkout": checkout,
        "tests": tests,
        "instance": row,
        "model": SWE_MODEL,
        "model_patch_files": sorted(parse_patch_files(pred.get("model_patch", ""))),
        "gold_patch_files": sorted(parse_patch_files(row.get("patch", ""))),
        "test_patch_files": sorted(parse_patch_files(row.get("test_patch", ""))),
    }
    if pull["returncode"] != 0 or clone["returncode"] != 0 or checkout.get("returncode") != 0:
        summary = {
            "generated_utc": utc_now(),
            "status": "TRUE EVAL INFRA FAIL",
            "instance_id": SWE_INSTANCE,
            "model": SWE_MODEL,
            "results": results,
            "wall_seconds": time.time() - started,
        }
        write_json(outdir / "swe_evo_true_eval_summary.json", summary)
        render_swe_report(outdir / "SWE_EVO_TRUE_EVAL_SLICE_20260628.md", summary)
        cleanup_swe_work(work)
        return summary

    base_eval_repo = copy_repo("eval_base")
    model_eval_repo = copy_repo("eval_model")
    gold_eval_repo = copy_repo("eval_gold")
    base_test_apply = apply_patch(base_eval_repo, row.get("test_patch", ""), "test_base")
    model_test_apply = apply_patch(model_eval_repo, row.get("test_patch", ""), "test_model")
    gold_test_apply = apply_patch(gold_eval_repo, row.get("test_patch", ""), "test_gold")
    model_apply = apply_patch(model_eval_repo, pred.get("model_patch", ""), "model")
    gold_apply = apply_patch(gold_eval_repo, row.get("patch", ""), "gold")
    test_patch_applied = base_test_apply["applied"] and model_test_apply["applied"] and gold_test_apply["applied"]

    base_eval = docker_eval(row["image"], base_eval_repo, tests, outdir / "swe_base_eval.json", timeout=1800) if base_test_apply["applied"] else {"returncode": 997, "stdout": "", "stderr": "test patch did not apply to base eval repo", "wall_seconds": 0, "timeout": False}
    model_eval = docker_eval(row["image"], model_eval_repo, tests, outdir / "swe_model_eval.json", timeout=1800) if model_apply["applied"] and model_test_apply["applied"] else {"returncode": 998, "stdout": "", "stderr": "model or test patch did not apply", "wall_seconds": 0, "timeout": False}
    gold_eval = docker_eval(row["image"], gold_eval_repo, tests, outdir / "swe_gold_eval.json", timeout=1800) if gold_apply["applied"] and gold_test_apply["applied"] else {"returncode": 999, "stdout": "", "stderr": "gold or test patch did not apply", "wall_seconds": 0, "timeout": False}
    status = "TRUE EVAL INFRA FAIL" if not test_patch_applied else "TRUE EVAL PASS" if base_eval["returncode"] != 0 and model_eval["returncode"] == 0 and gold_eval["returncode"] == 0 else "TRUE EVAL FAIL"
    summary = {
        "generated_utc": utc_now(),
        "status": status,
        "instance_id": SWE_INSTANCE,
        "repo": row["repo"],
        "image": row["image"],
        "model": SWE_MODEL,
        "tests": tests,
        "test_patch_applied": test_patch_applied,
        "model_patch_applied": model_apply["applied"],
        "gold_patch_applied": gold_apply["applied"],
        "base_returncode": base_eval["returncode"],
        "model_returncode": model_eval["returncode"],
        "gold_returncode": gold_eval["returncode"],
        "model_patch_files": results["model_patch_files"],
        "gold_patch_files": results["gold_patch_files"],
        "test_patch_files": results["test_patch_files"],
        "file_overlap": len(set(results["model_patch_files"]) & set(results["gold_patch_files"])),
        "results": {**results, "base_test_apply": base_test_apply, "model_test_apply": model_test_apply, "gold_test_apply": gold_test_apply, "model_apply": model_apply, "gold_apply": gold_apply},
        "wall_seconds": time.time() - started,
        "claim_boundary": "One released-prediction SWE-EVO execution slice. This is not a full benchmark sweep or a trained repo-state world model.",
    }
    write_json(outdir / "swe_evo_true_eval_summary.json", summary)
    render_swe_report(outdir / "SWE_EVO_TRUE_EVAL_SLICE_20260628.md", summary)
    cleanup_swe_work(work)
    return summary


def render_swe_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PX-033 SWE-EVO True Evaluation Slice",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Claim Boundary",
        "",
        summary.get("claim_boundary", "One execution slice only."),
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Instance | `{summary['instance_id']}` |",
        f"| Model patch source | `{summary['model']}` |",
        f"| Test patch applied | `{summary.get('test_patch_applied')}` |",
        f"| Model patch applied | `{summary.get('model_patch_applied')}` |",
        f"| Gold patch applied | `{summary.get('gold_patch_applied')}` |",
        f"| Base return code | `{summary.get('base_returncode')}` |",
        f"| Model return code | `{summary.get('model_returncode')}` |",
        f"| Gold return code | `{summary.get('gold_returncode')}` |",
        f"| File overlap | `{summary.get('file_overlap')}` |",
        f"| Wall seconds | `{summary.get('wall_seconds', 0):.1f}` |",
        "",
        "## Interpretation",
        "",
        "A PASS means the released model patch turns a failing targeted test slice into a passing slice while the gold patch also passes. A FAIL means the next PX-033 step should inspect the patch/test logs before spending on agent generation.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    tokenizer, model = load_model()
    halluhard = run_halluhard(outdir, tokenizer, model)
    del model
    torch.cuda.empty_cache()
    swe = run_swe_evo(outdir)
    summary = {
        "generated_utc": utc_now(),
        "model_id": MODEL_ID,
        "halluhard": {
            "status": halluhard["status"],
            "generations": halluhard["generations"],
            "supported_rate": halluhard["supported_rate"],
            "verifier_macro_f1": halluhard["verifier_metrics"]["macro_f1"],
        },
        "swe_evo": {
            "status": swe["status"],
            "instance_id": swe["instance_id"],
            "model": swe.get("model"),
            "model_returncode": swe.get("model_returncode"),
            "gold_returncode": swe.get("gold_returncode"),
        },
        "wall_seconds": time.time() - started,
    }
    write_json(outdir / "combined_paid_viability_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
