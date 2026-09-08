from pathlib import Path
import json, hashlib, sys
from .task_registry import get_task
from .verifier import verify

def verify_raw(path):
    rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    ids=[r["instance_id"] for r in rows]
    if len(ids)!=len(set(ids)):
        raise ValueError("duplicate instance_id")
    for r in rows:
        verdict=verify(get_task(r["task_id"]),r["final_state"])
        if verdict.success != r["det_success"]:
            raise ValueError(f"det label mismatch {r['instance_id']}")
    return {"n":len(rows),"sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest()}

if __name__=="__main__":
    print(verify_raw(sys.argv[1]))
