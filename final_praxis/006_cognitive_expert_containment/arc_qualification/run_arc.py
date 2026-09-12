"""ARC-Easy likelihood capability gate using the existing qualified MiCRo source."""
import argparse, hashlib, importlib.metadata, json, os, sys, time
from pathlib import Path

def digest(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def dump(data): return (json.dumps(data,sort_keys=True,indent=2)+"\n").encode()
def freeze(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);raw=dump(data)
    if path.exists():
        if path.read_bytes()!=raw: raise ValueError("Frozen artifact differs: "+str(path))
    else:
        with path.open("xb") as f: f.write(raw)
def write(path,data):
    temp=path.with_suffix(path.suffix+".tmp");temp.write_bytes(dump(data));temp.replace(path)
def winner(scores):
    if not scores: raise ValueError("No scores")
    return max(range(len(scores)),key=lambda i:scores[i])

def load_qualified_model(qualification,previous):
    # Reuse the exact reviewed architecture and portability patch from the first gate.
    receipts=read(qualification/"source_receipts.json")
    portability=read(previous/"portability.json")
    source=previous/"source_repos"
    model_file=source/"models"/"micro_llama.py"
    if digest(model_file.read_bytes())!=portability["patched_sha256"]:
        raise ValueError("Qualified patched source changed")
    for name in ("models/modules.py","repo_config.yml"):
        receipt=next(r for r in receipts if r["file"]==name)
        if digest((source/name).read_bytes())!=receipt["sha256"]: raise ValueError("Qualified dependency changed")
    expected=next(r["sha256"] for r in receipts if r["file"]=="models/micro_llama.py")
    if portability["original_sha256"]!=expected: raise ValueError("Original source pin differs")
    numerical=read(previous/"numerical_checks.json")
    if (not numerical["finite"] or numerical["repeat_max_abs"]>1e-6
        or numerical["eager_sdpa_max_abs"]>1e-3
        or numerical["ablation_reset_max_abs"]>1e-6
        or max(numerical["cached_full_max_abs"])>1e-3):
        raise ValueError("Prior numerical gate failed")
    sys.path.insert(0,str(source))
    import torch
    from transformers import AutoConfig,AutoTokenizer
    from models.micro_llama import MiCRoLlama,MiCRoLlamaConfig
    torch.set_num_threads(4);torch.manual_seed(20260912)
    dependencies=read(qualification/"loader_dependencies.json");settings=read(qualification/"settings.json")
    base=dependencies["base"];tok=dependencies["tokenizer"]
    config=AutoConfig.from_pretrained(base["id"],revision=base["revision"],
        trust_remote_code=False,local_files_only=True).to_dict()
    config["config_path"]=str(source/"repo_config.yml");config["ablate"]=[]
    model,info=MiCRoLlama.from_pretrained(settings["model"],revision=settings["model_revision"],
        config=MiCRoLlamaConfig(**config),torch_dtype=torch.float32,low_cpu_mem_usage=True,
        use_safetensors=True,output_loading_info=True,local_files_only=True)
    if any(info.get(k) for k in ("missing_keys","unexpected_keys","mismatched_keys","error_msgs")):
        raise ValueError("Checkpoint did not load exactly: "+str(info))
    tokenizer=AutoTokenizer.from_pretrained(tok["id"],revision=tok["revision"],
        trust_remote_code=False,local_files_only=True)
    model=model.float().eval()
    assert len(model.layers)==30 and model.config.num_hidden_layers==120
    return model,tokenizer,{"loading":info,"torch":torch.__version__,
        "transformers":importlib.metadata.version("transformers"),"model":settings,
        "parameters":sum(p.numel() for p in model.parameters()),"dtype":"float32","threads":4}

def score_candidate(model,tokenizer,question,choice,ablation):
    import torch
    # Match zero-shot harness text and default target delimiter; no chat wrapper.
    context="Question: "+question+"\nAnswer:"
    continuation=" "+choice
    context_ids=tokenizer.encode(context,add_special_tokens=False)
    full=tokenizer.encode(context+continuation,add_special_tokens=False)
    # Fail visibly if tokenizer boundary assumptions differ from the harness.
    if not context_ids or full[:len(context_ids)]!=context_ids or len(full)<=len(context_ids):
        raise ValueError("Context/continuation token boundary requires audit")
    n=len(full)-len(context_ids)
    if len(full)>model.config.max_position_embeddings: raise ValueError("No input truncation is permitted")
    ids=torch.tensor([full[:-1]],dtype=torch.long)
    with torch.inference_mode():
        result=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,
                     experts_ablate=ablation,logits_to_keep=n,return_dict=True)
        if result.logits.shape[1]!=n or not torch.isfinite(result.logits).all():
            raise ValueError("Invalid likelihood logits")
        target=torch.tensor(full[-n:],dtype=torch.long)
        scores=result.logits[0].float().log_softmax(-1).gather(-1,target[:,None]).squeeze(-1)
        if not torch.isfinite(scores).all(): raise ValueError("Nonfinite token likelihood")
        routes=[0,0,0,0]
        for routing in result.routing_weights:
            selected=routing.argmax(-1)
            for expert in range(4): routes[expert]+=int(selected.eq(expert).sum())
        if ablation and routes[1]: raise ValueError("Social expert remains selected")
    return {"log_likelihood":float(scores.double().sum()),"continuation_tokens":n,
            "choice_characters":len(choice),"token_ids":full[-n:],
            "routing_selection_counts":routes}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--qualification",type=Path,required=True)
    p.add_argument("--previous-out",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--execute",action="store_true")
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    fixture=read(a.data/"fixture.json");lock=read(a.data/"data_lock.json")
    if digest((a.data/"fixture.json").read_bytes())!=lock["fixture_sha256"]: raise ValueError("Fixture differs")
    if len(fixture["items"])!=32 or lock["selected_ids"]!=[r["id"] for r in fixture["items"]]:
        raise ValueError("Selection differs")
    prereg=Path(os.environ["PRAXIS_PREREG_PATH"])
    prereg_sha=digest(prereg.read_bytes())
    if prereg_sha!=os.environ["PRAXIS_PREREG_SHA256"]: raise ValueError("Preregistration differs")
    manifest={"prereg_sha256":prereg_sha,"data_lock":lock,"runner_sha256":digest(Path(__file__).read_bytes()),
        "source_receipts_sha256":digest((a.qualification/"source_receipts.json").read_bytes()),
        "settings_sha256":digest((a.qualification/"settings.json").read_bytes()),
        "dependencies_sha256":digest((a.qualification/"loader_dependencies.json").read_bytes()),
        "qualified_source_sha256":digest((a.previous_out/"source_repos/models/micro_llama.py").read_bytes()),
        "protocol":"zero-shot Question: {question}\\nAnswer:; full choice text with leading space; no chat/BOS/EOS",
        "primary_metric":"acc, summed continuation token log-likelihood",
        "secondary_metric":"acc_norm, sum divided by len(original choice text) in characters",
        "conditions":["baseline","social_ablation"],"threads":4,"dtype":"float32",
        "wall_time_limit_seconds":2400,"novel_method_tested":False,"paper_score_reproduction_claimed":False}
    freeze(a.out/"manifest.json",manifest)
    if not a.execute:
        print("Prepared: 32 questions, baseline and social ablation; no model loaded.");return
    model,tokenizer,environment=load_qualified_model(a.qualification,a.previous_out)
    freeze(a.out/"environment.json",environment)
    started=time.monotonic();results=[]
    for index,row in enumerate(fixture["items"]):
        for condition,ablation in (("baseline",[]),("social_ablation",["social"])):
            path=a.out/"cells"/f"{index:03d}-{condition}.json"
            if path.exists(): results.append(read(path));continue
            if time.monotonic()-started>2400: raise TimeoutError("Bounded CPU evaluation elapsed")
            choices=row["choices"]["text"];labels=row["choices"]["label"]
            # Gold is used only after candidate forwards.
            scores=[score_candidate(model,tokenizer,row["question"],choice,ablation) for choice in choices]
            ll=[r["log_likelihood"] for r in scores]
            norm=[score/len(choice) for score,choice in zip(ll,choices)]
            prediction=labels[winner(ll)];prediction_norm=labels[winner(norm)]
            cell={"id":row["id"],"index":index,"condition":condition,"scores":scores,
                "choice_labels":labels,"prediction":prediction,"prediction_norm":prediction_norm,
                "gold":row["answerKey"],"correct":prediction==row["answerKey"],
                "correct_norm":prediction_norm==row["answerKey"],"manifest_sha256":digest(dump(manifest))}
            freeze(path,cell);results.append(cell);print(json.dumps({"index":index,"condition":condition,"correct":cell["correct"]}),flush=True)
            write(a.out/"progress.json",{"completed":len(results),"planned":64})
    pairs={i:{r["condition"]:r for r in results if r["index"]==i} for i in range(32)}
    baseline=sum(r["baseline"]["correct"] for r in pairs.values())
    summary={"n":32,"completed":len(results),"baseline_correct":baseline,"baseline_wrong":32-baseline,
        "baseline_acc":baseline/32,"ablation_acc":sum(r["social_ablation"]["correct"] for r in pairs.values())/32,
        "baseline_acc_norm":sum(r["baseline"]["correct_norm"] for r in pairs.values())/32,
        "ablation_acc_norm":sum(r["social_ablation"]["correct_norm"] for r in pairs.values())/32,
        "correct_to_wrong":sum(r["baseline"]["correct"] and not r["social_ablation"]["correct"] for r in pairs.values()),
        "wrong_to_correct":sum(not r["baseline"]["correct"] and r["social_ablation"]["correct"] for r in pairs.values()),
        "capability_gate":baseline>=2 and 32-baseline>=2,"scope":"task-matched capability only",
        "novel_method_tested":False,"paper_score_reproduction_claimed":False}
    write(a.out/"summary.json",summary);print(json.dumps(summary))
if __name__=="__main__": main()

