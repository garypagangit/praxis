"""Freeze EX-FEVER stage2 data without inference or outcome-dependent selection.
Run: python prepare_dataset.py --source-dir /path/to/007/source_data
Optional --exposed-fixture arguments add newly discovered exposure before freezing.
Existing output bytes are immutable: use a new output directory for a new protocol.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, shutil
HERE = pathlib.Path(__file__).resolve().parent
REV = "36974db6bb1dc6bb31ff9fb56c9201beed78edd8"
UPSTREAM_REV = "ec059bf32ce981aa66830083c34377ad44346b4d"
LOCK = {"exfever.jsonl": "b584797d46b7b807891a433b5879b647841aa85e9654692c92de4943796c9fd7",
        "splits/exfever.json": "352ff9b0ccf412c57b925ab4ad86536fcb02e04bb4f1f957efb7078f544ff58b"}
SEED = "007-stage2-exfever-v1"
PRIOR_SHA = "9ddda10cbe2480736033c537513872aabaaf11b00b8159d86d46fe801bd3967a"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(s): return " ".join(s.casefold().split())
def encode(obj): return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)+"\n").encode("utf-8")
def freeze(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("Refusing to change frozen file: "+str(path))
    path.write_bytes(raw)
def load_source(source):
    receipts = {}
    for name, expected in LOCK.items():
        p = source/name
        raw = p.read_bytes()
        if sha(raw) != expected: raise ValueError("Source SHA mismatch: "+name)
        receipts[name] = {"sha256": expected, "bytes": len(raw),
            "url": "https://raw.githubusercontent.com/dependentsign/sycophancy-rational-updating/"+REV+"/data/"+name}
    rows = [json.loads(x) for x in (source/"exfever.jsonl").read_text(encoding="utf-8").splitlines()]
    split = json.loads((source/"splits/exfever.json").read_text(encoding="utf-8"))
    byid = {str(r["qid"]): r for r in rows}
    assert len(rows) == len(byid) == 2000
    pools = {s:set(map(str,split[s])) for s in ("cal","test")}
    assert all(len(pools[s]) == 1000 for s in pools)
    assert not pools["cal"] & pools["test"]
    assert pools["cal"] | pools["test"] == set(byid)
    for row in rows:
        assert type(row["gold_bool"]) is bool
        assert row["label_raw"] in ("SUPPORT","REFUTE")
        assert row["gold_bool"] == (row["label_raw"] == "SUPPORT")
        assert row["claim"].strip() and row["evidence"].strip()
        assert row["evidence"] == row["explanation"]
    return byid, pools, receipts
def exposures(paths):
    ids, claims, receipts = set(), set(), []
    for p in paths:
        raw = p.read_bytes()
        fixture = json.loads(raw)
        items = fixture["items"] if isinstance(fixture,dict) else fixture
        found = []
        for row in items:
            if row.get("dataset","").casefold() == "exfever":
                qid = str(row.get("id",row.get("qid")))
                ids.add(qid); found.append(qid)
                claims.add(canonical(row.get("question",row.get("claim",""))))
        receipts.append({"name":p.name,"sha256":sha(raw),"exfever_ids":sorted(set(found))})
    return ids, claims, receipts
def select(byid, pools, exposed_ids, exposed_claims):
    # Structural/content exclusions apply before hashing; never inspect model outcomes.
    reasons = collections.defaultdict(list)
    claim_to_ids = collections.defaultdict(list)
    for qid,row in byid.items():
        claim_to_ids[canonical(row["claim"])].append(qid)
        if qid in exposed_ids: reasons[qid].append("previously_exposed_id")
        if canonical(row["claim"]) in exposed_claims: reasons[qid].append("previously_exposed_exact_claim")
    # Remove all members of exact duplicate claim groups crossing cal/test.
    # Within-split duplicates retain lexicographically first ID, independent of label.
    for claim, ids in claim_to_ids.items():
        if len(ids) < 2: continue
        if any(i in pools["cal"] for i in ids) and any(i in pools["test"] for i in ids):
            for i in ids: reasons[i].append("exact_claim_cross_split_duplicate")
        else:
            for i in sorted(ids)[1:]: reasons[i].append("exact_claim_within_split_duplicate")
    eligible={s:sorted(pools[s]-set(reasons)) for s in pools}
    chosen={}
    for s,n in (("cal",64),("test",128)):
        order=sorted(eligible[s],key=lambda i:(sha((SEED+":"+s+":"+i).encode()),i))
        if len(order)<n: raise ValueError("Insufficient eligible "+s)
        chosen[s]=order[:n]
    assert not set(chosen["cal"]) & set(chosen["test"])
    assert not (set(chosen["cal"])|set(chosen["test"])) & exposed_ids
    return chosen, eligible, dict(sorted(reasons.items()))
def normalize(row, split):
    gold="TRUE" if row["gold_bool"] else "FALSE"
    return {"id":str(row["qid"]),"dataset":"exfever","release_split":split,
        "question":row["claim"],"options":[],"gold":gold,"gold_original_bool":row["gold_bool"],
        "gold_original_label":row["label_raw"],"evidence":row["evidence"],
        "evidence_kind":"upstream_author_written_explanation",
        "golden_entity":row["golden_entity"],"mention":row["mention"],
        "source_row_sha256":sha(encode(row))}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=pathlib.Path,default=HERE/"source_data")
    p.add_argument("--exposed-fixture",action="append",type=pathlib.Path,default=[])
    p.add_argument("--output-dir",type=pathlib.Path,default=HERE/"prepared")
    a=p.parse_args()
    prior=HERE/"prior_exposed_fixtures.json"
    assert sha(prior.read_bytes()) == PRIOR_SHA
    paths=[prior]+a.exposed_fixture
    byid,pools,receipts=load_source(a.source_dir)
    ids,claims,exposure_receipts=exposures(paths)
    chosen,eligible,reasons=select(byid,pools,ids,claims)
    items=[normalize(byid[q],s) for s in ("cal","test") for q in chosen[s]]
    raw=encode({"schema_version":1,"source_revision":REV,"selection_seed":SEED,
        "calibration_count":64,"test_count":128,"labels_changed":False,"items":items})
    freeze(a.output_dir/"fixtures.json",raw)
    # Initial inference gets only this projection, never full evaluator fixtures.
    public=encode({"items":[{k:r[k] for k in ("id","dataset","release_split","question","options")} for r in items]})
    freeze(a.output_dir/"initial_public.json",public)
    exposure_raw=encode({"exposed_ids":sorted(ids),"receipts":exposure_receipts,"exclusion_reasons":reasons})
    freeze(a.output_dir/"exposure_audit.json",exposure_raw)
    group_counts={s:dict(collections.Counter(r["gold"] for r in items if r["release_split"]==s)) for s in chosen}
    # Entity overlap is descriptive and not used to select favorable cases.
    cal_entities=set(e for q in chosen["cal"] for e in byid[q]["golden_entity"])
    overlapping_test=[q for q in chosen["test"] if cal_entities.intersection(byid[q]["golden_entity"])]
    manifest={"schema_version":1,"source_revision":REV,"source_files":receipts,
        "upstream_revision":UPSTREAM_REV,"upstream_split":"EX-FEVER data/test.csv",
        "upstream_test_csv_sha256":"7b172195801a934a24ce0c050ab0a006670a398c7f638f47ffca6cc7bcb81140",
        "upstream_provenance":"Public SRU manifest; upstream CSV not independently downloaded here",
        "selection":"ascending SHA256(007-stage2-exfever-v1:release_split:qid), then qid",
        "counts":{"source":len(byid),"cal_eligible":len(eligible["cal"]),"test_eligible":len(eligible["test"]),
                  "previously_exposed_ids":len(ids),"cal_selected":64,"test_selected":128},
        "selected_ids":chosen,"gold_counts":group_counts,
        "fixtures_sha256":sha(raw),"initial_public_sha256":sha(public),"exposure_audit_sha256":sha(exposure_raw),
        "exact_claim_overlap_after_filter":0,"test_items_with_cal_entity_overlap":overlapping_test,
        "scope":"Unexposed in enumerated Praxis fixtures; not proof of absence from pretraining or external runs",
        "conditions":"Root protocol will freeze none/reference/irrelevant explanation and independent TRUE/FALSE assertions",
        "false_evidence_available":False,
        "valid_evidence_is":"benchmark intended valid explanation, NOT universally independently validated",
        "gold_mutations":0,"model_requests":0}
    freeze(a.output_dir/"manifest.json",encode(manifest))
    print(json.dumps({"manifest":str(a.output_dir/"manifest.json"),"counts":manifest["counts"],
                      "fixture_sha256":sha(raw),"gold_counts":group_counts,
                      "entity_overlap_test_count":len(overlapping_test)}))
if __name__=="__main__": main()
