"""Free data preparation; no model imports. Requires pyarrow."""
import argparse,hashlib,io,json,urllib.request
from pathlib import Path
import pyarrow.parquet as pq
def sha(raw):return hashlib.sha256(raw).hexdigest()
def normalized(text):return " ".join(text.casefold().split())
def freeze(path,data):
    raw=(json.dumps(data,sort_keys=True,indent=2)+"\n").encode()
    if path.exists() and path.read_bytes()!=raw:raise ValueError("Frozen file differs")
    path.write_bytes(raw)
def main():
    p=argparse.ArgumentParser();p.add_argument("--arc-data",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    meta=json.loads((a.arc_data/"dataset_metadata.json").read_text(encoding="utf-8-sig"))
    old=json.loads((a.arc_data/"data_lock.json").read_text(encoding="utf-8-sig"));revision=old["revision"]
    if revision!=meta["sha"]:raise ValueError("Dataset revision differs")
    sources=[];splits={}
    for split in ("train","test"):
        names=sorted(r["rfilename"] for r in meta["siblings"] if r["rfilename"].startswith("ARC-Easy/"+split+"-") and r["rfilename"].endswith(".parquet"))
        if not names:raise ValueError("No source files for "+split)
        rows=[]
        for name in names:
            target=a.out/Path(name).name
            prior=a.arc_data/Path(name).name
            url=f"https://huggingface.co/datasets/allenai/ai2_arc/resolve/{revision}/{name}"
            if target.exists():raw=target.read_bytes()
            elif prior.exists():raw=prior.read_bytes()
            else:
                with urllib.request.urlopen(url,timeout=45) as response:raw=response.read(16_000_001)
                if len(raw)>16_000_000:raise ValueError("Download too large")
            target.write_bytes(raw);rows.extend(pq.read_table(io.BytesIO(raw)).to_pylist())
            sources.append({"split":split,"url":url,"sha256":sha(raw),"bytes":len(raw)})
        splits[split]=rows
    if len(splits["test"])!=2376:raise ValueError("Unexpected test size")
    if [r["id"] for r in splits["test"][:32]]!=old["selected_ids"]:raise ValueError("Old exposed cohort changed")
    test_questions={normalized(r["question"]) for r in splits["test"]}
    train=[r for r in splits["train"] if normalized(r["question"]) not in test_questions][:16]
    confirm=splits["test"][32:64]
    if len(train)!=16 or len(confirm)!=32:raise ValueError("Wrong cohort sizes")
    confirm_texts=[normalized(r["question"]) for r in confirm]
    if len(set(confirm_texts))!=32 or set(confirm_texts)&{normalized(r["question"]) for r in splits["test"][:32]}:
        raise ValueError("Confirmation question text duplicates another or an exposed question; amend before execution")
    for row in train+confirm:
        row["choices"]["label"]=[str(x) for x in row["choices"]["label"]];row["answerKey"]=str(row["answerKey"])
        if row["answerKey"] not in row["choices"]["label"]:raise ValueError("Bad gold mapping")
        if any(not x for x in row["choices"]["text"]):raise ValueError("Empty choice")
    fixture={"revision":revision,"dataset":"allenai/ai2_arc","config":"ARC-Easy","calibration":train,"confirmation":confirm}
    freeze(a.out/"fixture.json",fixture)
    freeze(a.out/"data_lock.json",{"revision":revision,"sources":sources,
        "fixture_sha256":sha((a.out/"fixture.json").read_bytes()),
        "excluded_previous_test_ids":old["selected_ids"],
        "calibration_ids":[r["id"] for r in train],"confirmation_ids":[r["id"] for r in confirm],
        "selection":"first16 train excluding normalized question overlap with all test; test rows32:64",
        "license":"CC-BY-SA-4.0 per public dataset card"})
if __name__=="__main__":main()


