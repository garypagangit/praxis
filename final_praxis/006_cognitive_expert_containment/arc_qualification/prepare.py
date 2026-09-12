"""Acquire pinned public ARC-Easy rows; no model imports or inference."""
import argparse, hashlib, io, json, urllib.request
from pathlib import Path

def digest(data): return hashlib.sha256(data).hexdigest()
def fetch(url, bound=16_000_000):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"FinalPraxis006-ARC"}), timeout=45) as r:
        data=r.read(bound+1)
    if len(data)>bound: raise ValueError("Download exceeds bound")
    return data
def frozen(path,data):
    if path.exists():
        if path.read_bytes()!=data: raise ValueError("Existing artifact differs: "+str(path))
    else: path.write_bytes(data)
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    metadata_path=a.out/"dataset_metadata.json"
    metadata=metadata_path.read_bytes() if metadata_path.exists() else fetch("https://huggingface.co/api/datasets/allenai/ai2_arc")
    meta=json.loads(metadata);revision=meta["sha"]
    if len(revision)!=40: raise ValueError("Expected exact dataset commit")
    frozen(metadata_path,metadata)
    files=sorted(x["rfilename"] for x in meta["siblings"]
                 if x["rfilename"].startswith("ARC-Easy/test-") and x["rfilename"].endswith(".parquet"))
    if not files: raise ValueError("Pinned dataset metadata contains no ARC-Easy test parquet")
    import pyarrow.parquet as pq
    rows=[];sources=[]
    for filename in files:
        url=f"https://huggingface.co/datasets/allenai/ai2_arc/resolve/{revision}/{filename}"
        path=a.out/Path(filename).name
        raw=path.read_bytes() if path.exists() else fetch(url)
        frozen(path,raw);rows.extend(pq.read_table(io.BytesIO(raw)).to_pylist())
        sources.append({"url":url,"sha256":digest(raw),"bytes":len(raw)})
    if len(rows)!=2376: raise ValueError("Expected 2376 ARC-Easy test rows")
    selected=[]
    for row in rows[:32]:
        labels=[str(x) for x in row["choices"]["label"]]
        texts=row["choices"]["text"];gold=str(row["answerKey"])
        if len(labels)!=len(texts) or len(set(labels))!=len(labels) or gold not in labels:
            raise ValueError("Invalid choice schema")
        if not texts or any(not isinstance(x,str) or not x for x in texts): raise ValueError("Empty choice")
        selected.append({"id":str(row["id"]),"question":row["question"],
                         "choices":{"label":labels,"text":texts},"answerKey":gold})
    fixture={"dataset":"allenai/ai2_arc","config":"ARC-Easy","split":"test",
             "revision":revision,"selection":"first 32 rows in pinned parquet order",
             "items":selected}
    data=(json.dumps(fixture,indent=2,ensure_ascii=False)+"\n").encode()
    frozen(a.out/"fixture.json",data)
    lock={"dataset":fixture["dataset"],"config":"ARC-Easy","split":"test","revision":revision,
          "license":"CC-BY-SA-4.0 per dataset card","source_files":sources,"total_rows":len(rows),
          "selected_ids":[r["id"] for r in selected],"fixture_sha256":digest(data),
          "dataset_card":"https://huggingface.co/datasets/allenai/ai2_arc",
          "protocol_source":"https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/tasks/arc/arc_easy.yaml"}
    frozen(a.out/"data_lock.json",(json.dumps(lock,indent=2)+"\n").encode())
    print(json.dumps(lock))
if __name__=="__main__": main()

