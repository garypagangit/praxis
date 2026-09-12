"""Resolve public source metadata without executing upstream code or loading models."""
from pathlib import Path
import concurrent.futures, hashlib, json, urllib.request

ROOT = Path(__file__).resolve().parent
MODELS = {"base": "Qwen/Qwen2.5-3B-Instruct", "extended_refusal": "HarethahMo/qwen2.5-3B-extended-refusal", "guard": "Qwen/Qwen3Guard-Gen-0.6B", "guard_independent": "OpenSafetyLab/MD-Judge-v0.1"}
REPOS = {"harmbench": "centerforaisafety/HarmBench", "xstest": "paul-rottger/xstest", "gsm8k": "openai/grade-school-math"}

def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FinalPraxis005/1.0"}), timeout=40) as response:
        return response.read()

def main():
    receipt_dir=ROOT/"source_receipts"
    receipt_dir.mkdir(exist_ok=True)
    spec={"models":{},"datasets":{},"retrievals":[]}
    tasks={f"model_{key}":f"https://huggingface.co/api/models/{name}" for key,name in MODELS.items()}
    tasks.update({f"repo_{key}":f"https://api.github.com/repos/{name}" for key,name in REPOS.items()})
    tasks["er_dataset"]="https://huggingface.co/api/datasets/HarethahMo/extended-refusal"
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        values=dict(zip(tasks,pool.map(fetch,tasks.values())))
    for key,data in values.items():
        (receipt_dir/f"{key}.json").write_bytes(data)
        spec["retrievals"].append({"url":tasks[key],"path":f"source_receipts/{key}.json","sha256":hashlib.sha256(data).hexdigest()})
    for key,name in MODELS.items():
        obj=json.loads(values[f"model_{key}"])
        spec["models"][key]={"id":name,"revision":obj["sha"],"gated":obj.get("gated"),"license":obj.get("cardData",{}).get("license"),"files":[x["rfilename"] for x in obj.get("siblings",[])]}
        for filename in ("README.md","config.json","LICENSE"):
            url=f"https://huggingface.co/{name}/resolve/{obj['sha']}/{filename}"
            try:
                b=fetch(url); path=receipt_dir/f"{key}_{filename}";path.write_bytes(b)
                spec["retrievals"].append({"url":url,"path":f"source_receipts/{path.name}","sha256":hashlib.sha256(b).hexdigest()})
            except Exception as exc:
                spec["retrievals"].append({"url":url,"error":str(exc)})
    er=json.loads(values["er_dataset"])
    spec["datasets"]["extended_refusal"]={"id":"HarethahMo/extended-refusal","revision":er["sha"],"license":er.get("cardData",{}).get("license"),"files":[x["rfilename"] for x in er.get("siblings",[])]}
    files={"harmbench":"data/behavior_datasets/harmbench_behaviors_text_test.csv","xstest":"xstest_prompts.csv","gsm8k":"grade_school_math/data/train.jsonl"}
    for key,repo in REPOS.items():
        meta=json.loads(values[f"repo_{key}"])
        commit=json.loads(fetch(f"https://api.github.com/repos/{repo}/commits/{meta['default_branch']}"))["sha"]
        spec["datasets"][key]={"repo":repo,"revision":commit,"license":meta.get("license"),"path":files[key]}
    (ROOT/"sources.lock.json").write_text(json.dumps(spec,indent=2),encoding="utf-8")
    print(json.dumps({"models":{k:{a:b for a,b in v.items() if a!='files'} for k,v in spec['models'].items()},"datasets":spec['datasets']},indent=2))

if __name__=="__main__":main()
