"""Prepare SecEval external inputs with the frozen CTI lexical retriever.

No generator calls or checker fitting. Published labels are isolated from model
inputs. All eligible-format rows are retained; outcomes never select questions.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import types
import urllib.request

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
PACKAGE = Path("C:/w/px_final_20260917/final_praxis/papers/20260914/01_cti")
REVISION = "205dab7b0888a06f4b53ca7d9c7093e1326683e1"
DATA_URL = f"https://huggingface.co/datasets/XuanwuAI/SecEval/resolve/{REVISION}/questions.json"
DATA_SHA = "194c3a511104be422a678675a71d44315d0c0392b040745155aeebc321e692e0"
CORPUS = Path("runs/px003-px034-confirmatory-20260731/attack_19_1_multidomain.json")
CORPUS_SHA = "bca81a8d69218ace1f7b5c706c605d22ad77d64425375b3d7804fdaf87c2ded9"
BUILDER_HASHES = {
    "build_sec_lord_relationship_evidence_gate.py": "5a825420ec6d30af986e1282626ac0101c42ab2c3f753b2e6d1ccaaaac3d6754",
    "build_px003_query_only_prompts.py": "658e60eb38a661c07a6e0bbcc248f5fbb510547d69b7c909fbd0966c00b372db",
}
PRIOR_CTI = Path("runs/px003-px034-confirmatory-20260731/ctibench_2500_query_only.jsonl")
PRIOR_CTI_SHA = "75d87d944cc2bcbe623ba3248a55a7c7e859111b08a52a7f06d42223f7f594c8"
PRIOR_ATHENA = Path("runs/px068-source-compatibility-router-20260731/sealed/athena-cti-ckt-3k.pinned.jsonl")
PRIOR_PX071 = {
    "adversarial_cti": "eb478091a33ce96d918d496613b360abf4af0332518d76d29c43aa7427f2da96",
    "technical_weakness_impact": "e515f733640fb9ffb2226da2bf452dc528c13429ef4aecda9b33390028c53ca2",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_verified(path, expected, provenance, purpose):
    raw = path.read_bytes()
    actual = sha(raw)
    if expected:
        require(actual == expected, f"Pinned SHA-256 mismatch: {path}")
    provenance.append({"path": str(path.resolve()), "sha256": actual, "bytes": len(raw),
                       "purpose": purpose, "compared_with_registered_hash": expected is not None})
    return raw


def jsonl(raw):
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def normalized(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value).lower()))


def clean_choices(row):
    choices = row.get("choices", [])
    if not isinstance(choices, list) or not all(isinstance(c, str) for c in choices):
        return None
    return [re.sub(r"^[A-D]\s*[:.)]\s*", "", choice) for choice in choices]


def load_prior(workspace, provenance):
    import pandas as pd
    cti = jsonl(read_verified(workspace / PRIOR_CTI, PRIOR_CTI_SHA, provenance, "historical CTIBench questions and frozen retrieval regression"))
    athena = jsonl(read_verified(workspace / PRIOR_ATHENA, None, provenance, "historical Athena exposure, including three later-excluded rows"))
    prior = [("ctibench", r["id"], r["question"], list(r["options"].values())) for r in cti]
    prior.extend(("athena", str(r.get("id", i)), r["question"], [r.get("option_" + c, "") for c in "abcde"]) for i, r in enumerate(athena))
    require(len(cti) == 2500 and len(athena) == 3000, "Historical CTI/Athena inventories changed")
    for name, digest in PRIOR_PX071.items():
        path = workspace / "data/px071_public_sources_20260818/SecKnowledge-Eval" / name / "test-00000-of-00001.parquet"
        read_verified(path, digest, provenance, "PX071 previously inspected source")
        frame = pd.read_parquet(path)
        require(len(frame) == (709 if name == "adversarial_cti" else 167), "PX071 inventory changed")
        prior.extend(("px071", name + ":" + str(i), row["question"], list(row["choices"])) for i, row in enumerate(frame.to_dict("records")))
    require(len(prior) == 6376, "Expected 6376 prior exposure rows")
    return prior, cti


def overlap_audit(source, retained_indices, prior):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    by_question, by_pair = defaultdict(set), defaultdict(set)
    for dataset, _identifier, question, options in prior:
        by_question[normalized(question)].add(dataset)
        by_pair[(normalized(question), tuple(sorted(normalized(v) for v in options)))].add(dataset)
    exact_question, exact_pair = [], []
    for index, row in enumerate(source):
        options = clean_choices(row) or []
        q = normalized(row["question"])
        if q in by_question:
            exact_question.append({"original_index": index, "prior_datasets": sorted(by_question[q])})
        pair = (q, tuple(sorted(normalized(v) for v in options)))
        if pair in by_pair:
            exact_pair.append({"original_index": index, "prior_datasets": sorted(by_pair[pair])})
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True, min_df=1, sublinear_tf=True)
    texts = [r[2] for r in prior] + [r["question"] for r in source]
    matrix = vectorizer.fit_transform(texts)
    similarity = linear_kernel(matrix[len(prior):], matrix[:len(prior)])
    maxima, neighbors = similarity.max(axis=1), similarity.argmax(axis=1)
    selected = np.array(retained_indices)
    def summary(values):
        return {"maximum_nearest_cosine": float(values.max()),
                "counts_at_or_above": {str(t): int((values >= t).sum()) for t in (.7, .8, .9)}}
    nearest = []
    for index in np.argsort(maxima)[-10:][::-1]:
        match = prior[int(neighbors[index])]
        nearest.append({"original_index": int(index), "original_id": source[index]["id"],
                        "prior_dataset": match[0], "prior_id": match[1], "cosine": float(maxima[index])})
    return {"prior_rows": len(prior), "prior_counts": dict(Counter(r[0] for r in prior)),
            "question_normalization": "lowercase ASCII alphanumeric tokens joined by spaces",
            "exact_question_matches": exact_question, "exact_question_and_unordered_options_matches": exact_pair,
            "lexical_method": "TF-IDF word 1-2 grams; lowercase; min_df=1; sublinear_tf=True; vocabulary fitted only for decontamination over old+new questions, never supplied to checker training",
            "all_downloaded_rows": summary(maxima), "retained_rows": summary(maxima[selected]),
            "nearest_ten": nearest,
            "limits": "Lexical checks cannot exclude paraphrase/concept/source-document overlap or generator pretraining exposure. The historical inventory is bounded to the three named CTI corpora."}


def frozen_retriever(package, provenance):
    # Force both module imports to exact frozen files, never workspace scripts.
    # exec(compile()) avoids writing bytecode in the frozen package.
    sources = {}
    for name, digest in BUILDER_HASHES.items():
        path = package / "frozen/builders" / name
        sources[name] = read_verified(path, digest, provenance, "frozen CTI retriever implementation")
    package_module = types.ModuleType("scripts")
    package_module.__path__ = []
    sys.modules["scripts"] = package_module
    for name in BUILDER_HASHES:
        modname = "scripts." + Path(name).stem
        module = types.ModuleType(modname)
        module.__file__ = str(package / "frozen/builders" / name)
        sys.modules[modname] = module
        exec(compile(sources[name], module.__file__, "exec"), module.__dict__)
    return sys.modules["scripts.build_px003_query_only_prompts"]


def encode_rows(rows):
    return ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n").encode("utf-8")


def init_worker(package, candidates, search_index):
    global WORKER_RETRIEVER, WORKER_CANDIDATES, WORKER_SEARCH_INDEX
    WORKER_RETRIEVER = frozen_retriever(Path(package), [])
    WORKER_CANDIDATES = candidates
    WORKER_SEARCH_INDEX = search_index


def retrieve_and_check(payload):
    row, answer = payload
    safe = {"question": row["question"], "options": row["options"]}
    def retrieve(value):
        ranked = WORKER_RETRIEVER.rank_query_only_evidence(value, WORKER_CANDIDATES, top_k=6, search_index=WORKER_SEARCH_INDEX)
        return [{"kind": r["kind"], "text": r["text"], "score": r["score"]} for r in ranked]
    evidence = retrieve(safe)
    require(len(evidence) == 6, "Retriever returned fewer than six facts: " + row["id"])
    altered = dict(safe, expected_output="ABCD"[("ABCD".index(answer) + 1) % 4],
                   answer="TRAP", source_url="TRAP", technique_id="TRAP", dataset_stratum="TRAP")
    require(retrieve(altered) == evidence, "Label/source perturbation altered retrieval: " + row["id"])
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--package", type=Path, default=PACKAGE)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    started = time.perf_counter()
    provenance = []
    corpus = args.workspace / CORPUS
    require(corpus.is_file(), "Required frozen ATT&CK19.1 corpus is absent; do not substitute another corpus")
    read_verified(corpus, CORPUS_SHA, provenance, "fixed ATT&CK19.1 multidomain evidence corpus")
    source_path = ROOT / "inputs/seceval_questions.json"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    if not source_path.exists():
        raw = urllib.request.urlopen(DATA_URL, timeout=60).read()
        require(sha(raw) == DATA_SHA, "Downloaded SecEval bytes differ from pinned source")
        source_path.write_bytes(raw)
    raw = read_verified(source_path, DATA_SHA, provenance, "pinned official SecEval source")
    source = json.loads(raw)
    require(len(source) == 2189 and len({r["id"] for r in source}) == 2189, "SecEval source inventory changed")
    retained, excluded, labels = [], [], []
    for index, row in enumerate(source):
        options = clean_choices(row)
        reasons = []
        if row.get("answer") not in list("ABCD"):
            reasons.append("not_exactly_one_published_A_D_answer")
        if options is None or len(options) != 4 or len(set(map(normalized, options))) != 4 or any(not normalized(x) for x in options):
            reasons.append("not_four_nonempty_distinct_options")
        if reasons:
            excluded.append({"original_index": index, "original_id": row["id"], "reasons": reasons})
            continue
        identifier = "seceval_" + str(index)
        retained.append({"id": identifier, "question": row["question"], "options": dict(zip("ABCD", options))})
        labels.append({"id": identifier, "original_index": index, "original_id": row["id"],
                       "source": row["source"], "cohort": "attack_source" if row["source"] == "attck" else "other_source",
                       "answer": row["answer"]})
    require(len(retained) == 1247 and sum(r["cohort"] == "attack_source" for r in labels) == 287, "Unexpected retained inventory")
    print(json.dumps({"stage": "SOURCE_AND_FILTER_VERIFIED", "retained": len(retained), "excluded": len(excluded)}), flush=True)
    prior, cti = load_prior(args.workspace, provenance)
    overlap = overlap_audit(source, [r["original_index"] for r in labels], prior)
    require(not overlap["exact_question_matches"] and not overlap["exact_question_and_unordered_options_matches"], "Historical exact overlap detected; stop before silently changing selection")
    retriever = frozen_retriever(args.package, provenance)
    candidate_index = retriever.build_candidate_index(corpus)
    candidates = retriever.flatten_candidates(candidate_index)
    search_index = retriever.build_candidate_search_index(candidates)
    def evidence_for(row):
        ranked = retriever.rank_query_only_evidence(row, candidates, top_k=6, search_index=search_index)
        return [{"kind": r["kind"], "text": r["text"], "score": r["score"]} for r in ranked]
    regression_indices = [0, 499, 1577, 1578, 2000, 2499]
    for index in regression_indices:
        row = cti[index]
        safe = {"question": row["question"], "options": row["options"]}
        require(evidence_for(safe) == row["relationship_evidence"], "Frozen retrieval no longer reproduces original evidence: " + row["id"])
    label_checks = 0
    require(1 <= args.workers <= 2, "Use one or two local retrieval workers to bound memory")
    payloads = [(row, label["answer"]) for row, label in zip(retained, labels)]
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                             initargs=(str(args.package), candidates, search_index)) as pool:
        for row, evidence in zip(retained, pool.map(retrieve_and_check, payloads, chunksize=5)):
            row["evidence"] = evidence
            label_checks += 1
            if label_checks % 50 == 0:
                print(json.dumps({"stage": "RETRIEVING_AND_CHECKING", "complete": label_checks, "total": len(retained)}), flush=True)
    require(all(set(r) == {"id", "question", "options", "evidence"} for r in retained), "Unexpected model input metadata")
    input_bytes, label_bytes = encode_rows(retained), encode_rows(labels)
    (ROOT / "test_inputs.jsonl").write_bytes(input_bytes)
    (ROOT / "sealed_labels.jsonl").write_bytes(label_bytes)
    audit = {
        "status": "PASS_PINNED_SOURCE_FILTER_RETRIEVAL_AND_EXPOSURE_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(), "generator_inference_calls": 0,
        "source": {"dataset": "XuanwuAI/SecEval", "revision": REVISION, "download_url": DATA_URL,
                   "sha256": DATA_SHA, "published_labels_used_unchanged": True,
                   "license": "CC BY-NC-SA 4.0", "license_source": "https://github.com/XuanwuAI/SecEval#licenses",
                   "source_rows": len(source), "README_count_differs": "README says 2126; pinned source contains2189"},
        "selection": {"rule": "Keep every row whose published answer is exactly A/B/C/D and whose four displayed options are nonempty and distinct after alphanumeric normalization. Strip existing A:/B:/C:/D: option prefixes only. Preserve question and option content otherwise.",
                      "model_outcomes_consulted": False, "retained": len(retained), "excluded": len(excluded),
                      "exclusion_reasons_nonexclusive": dict(Counter(reason for row in excluded for reason in row["reasons"])),
                      "exclusion_ledger": excluded,
                      "source_counts": dict(Counter(r["source"] for r in labels)),
                      "cohort_counts": dict(Counter(r["cohort"] for r in labels))},
        "retrieval": {"corpus_sha256": CORPUS_SHA, "top_k": 6, "facts": sum(len(r["evidence"]) for r in retained),
                      "local_worker_processes": args.workers, "parallelism": "Independent rows only; exact frozen ranker and original row ordering retained",
                      "inputs": ["question", "all four displayed option texts"], "frozen_builder_hashes": BUILDER_HASHES,
                      "label_and_source_perturbation_invariance_rows": label_checks,
                      "original_cti_exact_evidence_regression_ids": [cti[i]["id"] for i in regression_indices],
                      "candidate_facts": len(candidates), "unique_candidate_facts": len(search_index["unique_ids"]),
                      "inherited_source_pointer_fields_used": False},
        "overlap_audit": overlap,
        "interpretation_limits": [
            "External benchmark questions newly evaluated by this project, not guaranteed absent from model pretraining.",
            "The ATT&CK source family and retrieval corpus are shared with development. This is not source-family-disjoint confirmation.",
            "SecEval exposes coarse source labels, not per-question original URLs or ATT&CK technique IDs. ATT&CK-vs-other cohorts are provenance categories, not human-verified evidence applicability.",
            "Published labels were GPT-4-generated/calibrated; this project has not independently human-verified their correctness.",
            "Eight retained non-ATT&CK/non-CWE source categories are absent from the audited prior question-source inventory; semantic knowledge overlap can still exist.",
            "Source text/labels were inspected for schema and decontamination before model inference. No generated external answer outcomes informed selection.",
        ],
        "provenance": provenance,
        "outputs": {"test_inputs.jsonl": {"sha256": sha(input_bytes), "rows": len(retained), "bytes": len(input_bytes)},
                    "sealed_labels.jsonl": {"sha256": sha(label_bytes), "rows": len(labels), "bytes": len(label_bytes)}},
        "preparation_script_sha256": sha(Path(__file__).read_bytes()), "elapsed_seconds": time.perf_counter() - started,
    }
    (ROOT / "DATA_AUDIT.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "retained": len(retained), "cohorts": audit["selection"]["cohort_counts"],
                      "outputs": audit["outputs"], "elapsed_seconds": audit["elapsed_seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
