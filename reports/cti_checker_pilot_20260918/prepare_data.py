"""Prepare an audited, retrospective CTI evidence-selection dataset.

Standard-library only. No inference, network, training, or frozen-input writes.
Only question/options/evidence may become checker features; all other output
fields are join, split, stratification, or evaluation metadata.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit


SCRIPT = Path(__file__).resolve()
DEFAULT_WORKSPACE = SCRIPT.parents[2]
DEFAULT_PACKAGE = Path("C:/w/px_final_20260917/final_praxis/papers/20260914/01_cti")
RUN = Path("runs/px003-px034-confirmatory-20260731")
PROMPT_REL = RUN / "ctibench_2500_query_only.jsonl"
EXPOSED_REL = RUN / "cloud_output_500/qwen2-5-7b-instruct/v19-1-query-only/predictions.jsonl"
PROMPT_SHA = "75d87d944cc2bcbe623ba3248a55a7c7e859111b08a52a7f06d42223f7f594c8"
EXPOSED_SHA = "1d74be3dee646d8cbbe174c3b15d8f1e1021b64062d1a4793bb6e8d81a4f696e"
STRATA = {"attack_technique_eligible": True, "non_attack_domain_mismatch": False}
MODELS = {"llama": "Llama", "qwen": "Qwen"}
CONDITIONS = {"vanilla", "relationship_evidence"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def jsonl(raw):
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def verified_file(path, expected, records, kind, uncompressed_expected=None):
    raw = path.read_bytes()
    actual = sha256(raw)
    require(actual == expected, f"Hash mismatch: {path}")
    record = {"path": str(path.resolve()), "sha256": actual, "bytes": len(raw), "kind": kind}
    if uncompressed_expected is not None:
        unpacked = gzip.decompress(raw)
        require(sha256(unpacked) == uncompressed_expected, f"Archive-content hash mismatch: {path}")
        record.update(uncompressed_sha256=sha256(unpacked), uncompressed_bytes=len(unpacked))
        records.append(record)
        return unpacked
    records.append(record)
    return raw


def source_group(source):
    source = source.strip()
    require(bool(source), "Missing source-group value")
    if source.lower() == "manual":
        return "manual"
    parsed = urlsplit(source)
    if not (parsed.scheme and parsed.netloc):
        # Released CTIBench also records document filenames rather than URLs.
        normalized_name = " ".join(source.casefold().split())
        normalized_name = re.sub(r"(?:_part\d+)?\.txt$", "", normalized_name)
        return "named_source:" + normalized_name
    host = parsed.hostname.lower() if parsed.hostname else ""
    match = re.match(r"^/techniques/(T\d{4})(?:[/.]|$)", parsed.path, flags=re.I)
    if host in {"attack.mitre.org", "www.attack.mitre.org"} and match:
        return "attack_technique_family:" + match.group(1).upper()
    # Preserve path, query and fragment because they can identify distinct source
    # content. Normalize only scheme/host and a redundant trailing slash.
    normalized = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(),
                            parsed.path.rstrip("/"), parsed.query, parsed.fragment))
    return normalized


def load_parser(package, provenance, sources):
    relative = "frozen/inference/run_sec_lord_relationship_evidence_cloud.py"
    raw = verified_file(package / relative, provenance[relative]["sha256"], sources, "frozen parser source")
    tree = ast.parse(raw.decode("utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "strict_parse")
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = {"re": re}
    exec(compile(module, str(package / relative), "exec"), namespace)
    return namespace["strict_parse"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--output", type=Path, default=SCRIPT.parent)
    args = parser.parse_args()
    sources = []
    provenance_path = args.package / "PROVENANCE.json"
    provenance_raw = provenance_path.read_bytes()
    provenance = {r["file"]: r for r in json.loads(provenance_raw)["artifacts"]}
    sources.append({"path": str(provenance_path.resolve()), "sha256": sha256(provenance_raw),
                    "bytes": len(provenance_raw), "kind": "package provenance registry"})
    prompts = jsonl(verified_file(args.workspace / PROMPT_REL, PROMPT_SHA, sources, "frozen query-only prompts"))
    require(len(prompts) == 2500, "Expected exactly 2500 question rows")
    prompt_by_id = {r["id"]: r for r in prompts}
    require(len(prompt_by_id) == 2500, "Duplicate question ID")
    require(Counter(r["dataset_stratum"] for r in prompts) ==
            {"attack_technique_eligible": 1578, "non_attack_domain_mismatch": 922}, "Stratum inventory mismatch")
    exposed_rows = jsonl(verified_file(args.workspace / EXPOSED_REL, EXPOSED_SHA, sources, "historical development-exposed ID inventory"))
    exposed_keys = [(r["id"], r["condition"]) for r in exposed_rows]
    require(len(exposed_keys) == len(set(exposed_keys)), "Duplicate exposed (id,condition)")
    exposed_ids = {r["id"] for r in exposed_rows}
    require(len(exposed_ids) == 500 and exposed_ids <= prompt_by_id.keys(), "Exposed ID mismatch")
    require(all(prompt_by_id[i]["dataset_stratum"] == "attack_technique_eligible" for i in exposed_ids), "Unexpected exposure stratum")
    parse = load_parser(args.package, provenance, sources)
    analysis_rel = "evidence/FULL_2500_ANALYSIS.json"
    analysis = json.loads(verified_file(args.package / analysis_rel, provenance[analysis_rel]["sha256"], sources, "published canonical analysis"))
    indexed = {}
    canonical_counts = {}
    checks = Counter()
    for model, published_name in MODELS.items():
        relative = f"data/full2500_{model}_query_only.jsonl.gz"
        prov = provenance[relative]
        rows = jsonl(verified_file(args.package / relative, prov["sha256"], sources,
                                  "canonical paired query-only predictions", prov["uncompressed_sha256"]))
        require(len(rows) == 5000, f"Wrong prediction count: {model}")
        pred = {}
        for row in rows:
            key = (row["id"], row["condition"])
            require(key not in pred, f"Duplicate prediction: {model}/{key}")
            require(row["id"] in prompt_by_id and row["condition"] in CONDITIONS, f"Unexpected assignment: {model}/{key}")
            source = prompt_by_id[row["id"]]
            for field in ("question", "expected_output", "dataset_stratum", "source_url"):
                require(row[field] == source[field], f"Join metadata mismatch: {model}/{key}/{field}")
                checks["joined_metadata_equal"] += 1
            parsed = parse(row["raw_output"])
            require(parsed == row["parsed_answer"], f"Parser mismatch: {model}/{key}")
            require(type(row["correct"]) is bool and row["correct"] == (parsed == row["expected_output"]), f"Correctness mismatch: {model}/{key}")
            checks["raw_output_correctness_recomputed"] += 1
            prompt_field = "vanilla_strict_prompt" if row["condition"] == "vanilla" else "relationship_evidence_prompt"
            require(source[prompt_field] in row["prompt"], f"Rendered prompt mismatch: {model}/{key}")
            checks["rendered_prompt_contains_frozen_prompt"] += 1
            pred[key] = row
        require(set(pred) == {(i, c) for i in prompt_by_id for c in CONDITIONS}, f"Missing prediction assignments: {model}")
        indexed[model] = pred
        canonical_counts[model] = {}
        archived = analysis["models"][published_name]["query_only"]
        scopes = {"all_2500": list(prompt_by_id),
                  **{s: [i for i, q in prompt_by_id.items() if q["dataset_stratum"] == s] for s in STRATA}}
        for scope, ids in scopes.items():
            reference = archived["intention_to_treat"] if scope == "all_2500" else archived["strata"][scope]
            canonical_counts[model][scope] = {}
            for condition in sorted(CONDITIONS):
                selected = [pred[(i, condition)] for i in ids]
                measured = {"rows": len(selected), "correct": sum(r["correct"] for r in selected),
                            "invalid": sum(r["parsed_answer"] not in "ABCD" or not r["parsed_answer"] for r in selected)}
                require(all(measured[k] == reference["conditions"][condition][k] for k in measured), f"Published count mismatch: {model}/{scope}/{condition}")
                checks["published_count_equal"] += len(measured)
                canonical_counts[model][scope][condition] = measured
    output = []
    for row in sorted(prompts, key=lambda r: int(r["id"].rsplit("_", 1)[1])):
        require(set(row["options"]) == set("ABCD"), f"Unexpected options: {row['id']}")
        evidence = []
        for entry in row["relationship_evidence"]:
            require(isinstance(entry["text"], str) and entry["text"] in row["relationship_evidence_prompt"], f"Evidence mismatch: {row['id']}")
            evidence.append({"kind": entry["kind"], "text": entry["text"], "score": entry["score"]})
        outcomes = {}
        for model in MODELS:
            vanilla = indexed[model][(row["id"], "vanilla")]
            ev = indexed[model][(row["id"], "relationship_evidence")]
            outcomes[model] = {"vanilla": vanilla["correct"], "evidence": ev["correct"],
                               "vanilla_valid": vanilla["parsed_answer"] in {"A", "B", "C", "D"},
                               "evidence_valid": ev["parsed_answer"] in {"A", "B", "C", "D"}}
        output.append({"id": row["id"], "question": row["question"], "options": row["options"],
                       "evidence": evidence, "source_group": source_group(row["source_url"]),
                       "eligible": STRATA[row["dataset_stratum"]], "previously_exposed": row["id"] in exposed_ids,
                       "outcomes": outcomes})
    encoded = ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in output) + "\n").encode("utf-8")
    groups = Counter(r["source_group"] for r in output)
    audit = {
        "status": "PASS_INPUT_INTEGRITY_AND_CANONICAL_COUNT_CHECKS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "warning": "RETROSPECTIVE EXPLORATORY DATA, NOT FRESH CONFIRMATION. All 2500 questions previously contributed to PX068 training and existing outcome analyses; excluding the 500 earlier development-exposed items does not make the remainder newly unseen.",
        "new_inference_calls": 0,
        "rows": len(output), "eligible": sum(r["eligible"] for r in output),
        "mismatch": sum(not r["eligible"] for r in output), "previously_exposed": len(exposed_ids),
        "exact_source_url_groups": len({r["source_url"] for r in prompts}),
        "source_groups": len(groups), "largest_source_groups": groups.most_common(10),
        "grouping": "Parent ATT&CK technique family Txxxx combines all subtechnique URLs. Other sources preserve full URL path/query/fragment with lowercased scheme/host and trailing slash removed. Named-document sources normalize case/whitespace and remove _partN.txt or .txt to keep all parts of the same document together. All Manual entries remain one group.",
        "allowed_feature_fields": ["question", "options", "evidence"],
        "metadata_never_features": ["id", "source_group", "eligible", "previously_exposed", "outcomes"],
        "excluded_inherited_source_aware_fields": ["option_support_scores", "technique_id", "technique_only_evidence", "source_pointer_relationship_evidence", "random_facts_evidence", "source_url", "dataset_stratum", "expected_output"],
        "outcome_meaning": "Boolean correctness of archived answer, separately per model and condition; validity means frozen parser returned one of A/B/C/D. Selecting an archived response evaluates routing, not new answer generation.",
        "checks": dict(checks), "canonical_counts": canonical_counts,
        "sources": sources,
        "prepared_data": {"file": "data.jsonl", "sha256": sha256(encoded), "bytes": len(encoded)},
        "preparation_script": {"file": SCRIPT.name, "sha256": sha256(SCRIPT.read_bytes())},
        "reproduce": f'python "{SCRIPT}" --workspace "{args.workspace.resolve()}" --package "{args.package.resolve()}" --output "{args.output.resolve()}"',
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "data.jsonl").write_bytes(encoded)
    (args.output / "DATA_AUDIT.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ("status", "rows", "eligible", "mismatch", "source_groups", "checks", "prepared_data")}, indent=2))


if __name__ == "__main__":
    main()
