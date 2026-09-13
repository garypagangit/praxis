"""Inventory released answer/CSV provenance without scoring or upstream execution.

Standard library only. Reads a pre-existing pinned artifact-audit cache. Optional
--fetch performs public GitHub GETs; every returned file is checked against the
pinned recursive Git tree. Raw third-party content stays in --private-dir.
Notebook outputs are never inspected. No query/scoring functions are executed.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import urllib.parse
import urllib.request


COMMIT = "082dcbf5304329ef1ff08f5830e4116256b00a59"
REPOSITORY = "LanLi2017/LLM4DC"
MODELS = ("gemma2", "gemma2base", "llama3.1", "mistral")
SOURCE_PATHS = (
    "evaluation/q_execution.py", "README.md", "purposes/all_purposes.csv",
    "run_ev.ipynb", "run_ev_ablation.ipynb", "run_ev_g9b.ipynb", "test.ipynb",
    "llm_wf_ablation.py", "llm_wf_ab.py", "CoT.rerun/llm_wf_gemma_27b.py",
    "CoT.rerun/llm_wf_llama3_1.py",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))


def without_exported_range_index(rows):
    if rows and rows[0] and rows[0][0] == "" and all(
            len(row) == len(rows[0]) and row[0] == str(i) for i, row in enumerate(rows[1:])):
        return [row[1:] for row in rows], True
    return rows, False


def domain_paths(identifier):
    if identifier < 31:
        return "menu", f"datasets/menu_datasets/menu_p{identifier}.csv", f"datasets/menu_datasets/clean_tables/menu_sample_p{identifier}.csv"
    if identifier < 62:
        return "chi", f"datasets/CFI_datasets/chi_food_data_p{identifier}.csv", f"datasets/CFI_datasets/cleaned_tables/chi_sample_p{identifier}.csv"
    if identifier < 92:
        return "ppp", f"datasets/ppp_datasets/ppp_data_p{identifier}.csv", f"datasets/ppp_datasets/cleaned_tables/ppp_sample_p{identifier}.csv"
    if identifier < 111:
        return "dish", f"datasets/dish_datasets/dish_data_p{identifier}.csv", f"datasets/dish_datasets/cleaned_tables/dish_sample_p{identifier}.csv"
    if identifier < 127:
        return "flights", f"datasets/flights/flights_data_p{identifier}.csv", f"datasets/flights/cleaned_tables/flights_data_p{identifier}.csv"
    return "hos", f"datasets/hospital/hos_data_p{identifier}.csv", f"datasets/hospital/clean_tables/hos_pp{identifier}.csv"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-audit", required=True, type=Path)
    parser.add_argument("--private-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    audit, private, output = (p.resolve() for p in (args.artifact_audit, args.private_dir, args.output_dir))
    if private == output or private.is_relative_to(output):
        raise ValueError("Third-party cache must be outside the publication output directory")
    tree_bytes = (audit / "inventory/tree.json").read_bytes()
    tree = json.loads(tree_bytes)
    assert tree["sha"] == COMMIT and tree["truncated"] is False
    blobs = {x["path"]: x for x in tree["tree"] if x["type"] == "blob"}

    def fetch(path):
        relative = PurePosixPath(path)
        assert not relative.is_absolute() and ".." not in relative.parts and path in blobs
        original = audit / "inventory/cache" / path
        local = private / "cache" / path
        if original.exists():
            payload = original.read_bytes()
        elif local.exists():
            payload = local.read_bytes()
        elif args.fetch:
            url = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/" + urllib.parse.quote(path)
            request = urllib.request.Request(url, headers={"User-Agent": "Praxis-read-only-provenance"})
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(payload)
        else:
            raise FileNotFoundError(f"Not cached: {path}. Use --fetch for pinned public GETs.")
        git_hash = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
        assert git_hash == blobs[path]["sha"] and len(payload) == blobs[path]["size"], path
        metadata = {"path": path, "git_blob_sha1": git_hash, "sha256": sha256(payload), "bytes": len(payload)}
        return path, payload, metadata

    answer_paths = sorted(p for p in blobs if "/answer_" in p and p.endswith(".json"))
    model_paths = sorted(p for p in blobs if p.endswith(".csv") and "/datasets_llm/" in p and (
        p.startswith(("CoT.response/", "ablation/", "CoT.rerun/gemma2/", "CoT.rerun/llama3.1/"))))
    sources = {p: fetch(p) for p in SOURCE_PATHS}
    purposes = list(csv.DictReader(io.StringIO(sources["purposes/all_purposes.csv"][1].decode("utf-8-sig"))))
    ids = sorted(int(r["ID"]) for r in purposes)
    assert len(ids) == len(set(ids)) == 142
    raw_paths = [domain_paths(i)[1] for i in ids]
    clean_paths = [domain_paths(i)[2] for i in ids]
    paths = sorted(set(answer_paths + model_paths + raw_paths + clean_paths))
    fetched = dict(sources)
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for result in pool.map(fetch, paths):
            fetched[result[0]] = result

    def reference(path):
        return dict(fetched[path][2]) if path in fetched else {"path": path, "exists_in_pinned_tree": path in blobs}

    csv_metadata = {}
    grouped = collections.defaultdict(dict)
    for path in model_paths:
        group = str(PurePosixPath(path).parent)
        match = re.search(r"_p(\d+)\.csv$", path)
        assert match, path
        identifier = int(match.group(1))
        assert identifier not in grouped[group], (group, identifier)
        grouped[group][identifier] = path
        rows = list(csv.reader(io.StringIO(fetched[path][1].decode("utf-8-sig"))))
        raw = domain_paths(identifier)[1]
        raw_rows = list(csv.reader(io.StringIO(fetched[raw][1].decode("utf-8-sig"))))
        normalized_rows, range_index_removed = without_exported_range_index(rows)
        normalized_raw, raw_range_index_removed = without_exported_range_index(raw_rows)
        csv_metadata[path] = {
            **reference(path), "purpose_id": identifier, "row_count": max(0, len(rows) - 1),
            "column_count": len(rows[0]) if rows else 0,
            "malformed_row_numbers": [n for n, row in enumerate(rows[1:], 2) if len(row) != len(rows[0])],
            "raw_source": reference(raw),
            "byte_identical_to_raw": fetched[path][1] == fetched[raw][1],
            "csv_cells_identical_to_raw": rows == raw_rows,
            "csv_cells_identical_after_optional_range_index_drop": normalized_rows == normalized_raw,
            "exported_range_index_removed_for_comparison": range_index_removed,
            "raw_exported_range_index_removed_for_comparison": raw_range_index_removed,
            "meaning": "Byte identity is an artifact property; it does not prove model execution or semantic correctness.",
        }

    source_evidence = []
    needles = ("answer_1-154", "llm_folder", "base_tag", "CoT.response", "CoT.rerun", "ablation/", "datasets_llm")
    for path in SOURCE_PATHS:
        if not path.endswith((".py", ".ipynb")):
            continue
        payload = fetched[path][1]
        locations = []
        if path.endswith(".ipynb"):
            notebook = json.loads(payload)
            chunks = [(cell_index, "".join(cell["source"])) for cell_index, cell in enumerate(notebook["cells"]) if cell["cell_type"] == "code"]
        else:
            chunks = [(None, payload.decode("utf-8"))]
        for cell_index, text in chunks:
            for line_number, line in enumerate(text.splitlines(), 1):
                matched = [needle for needle in needles if needle in line]
                if matched:
                    locations.append({"cell_index": cell_index, "line_number": line_number, "markers": matched, "line_sha256": sha256(line.encode("utf-8"))})
        source_evidence.append({**reference(path), "code_locations": locations, "notebook_outputs_inspected": False})

    records = []
    answer_summaries = []
    for path in answer_paths:
        rows = []
        for line_number, line in enumerate(fetched[path][1].decode("utf-8-sig").splitlines(), 1):
            if line.strip():
                # Parse IDs only for mapping; answer payloads are never compared.
                row = json.loads(line)
                rows.append({"purpose_id": int(row["pp_id"]), "line_number": line_number, "line_sha256": sha256(line.encode("utf-8"))})
        by_id = collections.defaultdict(list)
        for row in rows:
            by_id[row["purpose_id"]].append(row)
        actual_present_ids = set(by_id)
        label = PurePosixPath(path).stem.removeprefix("answer_1-154_")
        kind = "reference" if label == "gt" else "raw" if label == "dirty" else "ablation" if label.startswith("base_") else "rerun" if path.startswith("CoT.rerun/") else "cot_response"
        model = label.removeprefix("base_") if kind not in ("reference", "raw") else None
        assert model is None or model in MODELS
        file_records = []
        for identifier in ids:
            domain, raw, clean = domain_paths(identifier)
            candidates = []
            if kind in ("reference", "raw"):
                candidates.append({"role": kind, "path": clean if kind == "reference" else raw, "basis": "groundtruth_tag / dirty_tag branch in reviewed q_execution.py"})
            elif kind == "rerun":
                group = f"CoT.rerun/{model}/datasets_llm"
                expected = grouped[group].get(identifier)
                candidates.append({"role": "rerun", "path": expected, "group": group, "basis": "same model/directory/ID; no released per-answer generation receipt"})
            else:
                expected_cot = f"CoT.response/{model}/datasets_llm/{model}_{domain}_test_p{identifier}.csv"
                expected_ablation = f"ablation/{model}/datasets_llm/base_{model}_{domain}_test_p{identifier}.csv"
                if kind == "cot_response":
                    candidates.append({"role": "intended_cot_response", "path": expected_cot, "basis": "consumer notebook and non-base q_execution branch"})
                    candidates.append({"role": "alternative_ablation_writer", "path": expected_ablation, "basis": "active base_tag writer emits this same unprefixed answer filename", "raw_fallback": raw})
                else:
                    candidates.append({"role": "intended_ablation", "path": expected_ablation, "basis": "base-prefixed answer consumer in run_ev_ablation.ipynb; q_execution requires output rename", "raw_fallback": raw})
            for candidate in candidates:
                candidate_path = candidate["path"]
                if candidate_path is not None and candidate_path in fetched:
                    candidate.update(reference(candidate_path))
                    candidate["classification"] = "RELEASED_CSV_BYTE_IDENTICAL_TO_RAW" if candidate_path in csv_metadata and csv_metadata[candidate_path]["byte_identical_to_raw"] else "RELEASED_CSV_RAW_CELLS_IDENTICAL_AFTER_RANGE_INDEX_CHECK" if candidate_path in csv_metadata and csv_metadata[candidate_path]["csv_cells_identical_after_optional_range_index_drop"] else "RELEASED_CSV_PRESENT"
                else:
                    candidate["classification"] = "MISSING_CSV_RAW_FALLBACK_BY_CODE" if "raw_fallback" in candidate else "NO_RELEASED_CSV_FOR_ID"
                if "raw_fallback" in candidate:
                    candidate["fallback_source"] = reference(candidate.pop("raw_fallback"))
                    candidate["fallback_taken_in_pinned_configuration"] = candidate_path not in blobs
            record = {
                "answer_file": path, "purpose_id": identifier, "domain": domain,
                "saved_answer": "PRESENT" if len(by_id[identifier]) == 1 else "MISSING" if not by_id[identifier] else "DUPLICATE",
                "answer_lines": by_id[identifier], "intended_role": kind, "model": model,
                "source_candidates": candidates,
                "historical_answer_to_csv_binding": "UNVERIFIED_NO_PER_ANSWER_SOURCE_HASH",
                "answer_recomputed": False, "correctness_scored": False,
            }
            records.append(record)
            file_records.append(record)
        answer_summaries.append({
            **reference(path), "intended_role": kind, "model": model, "answer_rows": len(rows),
            "unique_ids": len(actual_present_ids), "missing_purpose_ids": sorted(set(ids) - actual_present_ids),
            "duplicate_ids": [i for i in ids if len(by_id[i]) > 1], "extra_ids": sorted(actual_present_ids - set(ids)),
            "candidate_classifications": dict(collections.Counter(c["classification"] for r in file_records for c in r["source_candidates"])),
            "historical_binding": "UNVERIFIED_NO_PER_ANSWER_SOURCE_HASH",
        })

    group_summary = []
    for group, entries in sorted(grouped.items()):
        group_summary.append({"group": group, "verified_files": len(entries), "missing_purpose_ids": sorted(set(ids) - set(entries)),
                              "byte_identical_to_raw": sum(csv_metadata[path]["byte_identical_to_raw"] for path in entries.values()),
                              "csv_cells_identical_after_optional_range_index_drop": sum(csv_metadata[path]["csv_cells_identical_after_optional_range_index_drop"] for path in entries.values()),
                              "malformed_csv_count": sum(bool(csv_metadata[path]["malformed_row_numbers"]) for path in entries.values())})
    report = {
        "schema_version": 1, "repository": REPOSITORY, "commit": COMMIT,
        "tree_sha256": sha256(tree_bytes), "script_sha256": sha256(Path(__file__).read_bytes()),
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Artifact/source mapping only. No upstream code execution, notebook-output inspection, query replay, answer comparison, correctness scores, model/API calls, or cloud actions.",
        "decision": "HISTORICAL_BINDING_AMBIGUOUS_RECOMPUTE_FROM_PINNED_CSVS_AFTER_SCORING_FREEZE",
        "notes": [
            "Complete answer files do not prove complete model generation.",
            "The active q_execution.py sets base_tag=True and an ablation input folder but writes an unprefixed answer filename.",
            "Notebook consumers support intended CoT/ablation labels but do not certify historical per-answer source files.",
            "Fallback classifications describe what the pinned branch would read; they are not proof of how a historical answer was produced.",
            "A saved CSV byte-identical to raw is kept separate from a missing CSV. Neither alone proves generation success.",
            "All third-party raw files remain in private caches. Published artifacts contain only hashes, paths, IDs, counts, and findings.",
        ],
        "purpose_ids": ids, "verified_files": len(fetched), "verified_bytes": sum(v[2]["bytes"] for v in fetched.values()),
        "answer_files": answer_summaries, "csv_groups": group_summary,
        "source_evidence": source_evidence,
    }
    write_json(output / "PROVENANCE_SUMMARY.json", report)
    write_json(output / "ANSWER_SOURCE_MAP.json", {"repository": REPOSITORY, "commit": COMMIT, "records": records})
    write_json(output / "CSV_MANIFEST.json", {"repository": REPOSITORY, "commit": COMMIT, "files": list(csv_metadata.values())})
    write_json(output / "VERIFIED_SOURCE_MANIFEST.json", {"repository": REPOSITORY, "commit": COMMIT, "files": [fetched[path][2] for path in sorted(fetched)]})
    write_json(private / "EXECUTION_RECEIPT.json", {"checked_at_utc": report["checked_at_utc"], "script": str(Path(__file__).resolve()), "artifact_audit": str(audit), "private_dir": str(private), "output_dir": str(output), "fetch_permitted": args.fetch, "report_sha256": sha256((output / "PROVENANCE_SUMMARY.json").read_bytes())})
    print(json.dumps({k: report[k] for k in ("decision", "verified_files", "verified_bytes", "csv_groups")}, indent=2))


if __name__ == "__main__":
    main()
