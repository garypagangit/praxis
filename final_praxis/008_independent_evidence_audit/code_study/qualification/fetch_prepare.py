"""Pinned public GETs, data parsing, AST audit, and bundle preparation only.

Never executes downloaded code, dataset loaders, tests, or reference programs.
Requires pyarrow only on the preparation machine to read the released Parquet.
"""
from __future__ import annotations
import argparse
import ast
import collections
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import textwrap
import urllib.parse
import urllib.request

SEED = "praxis008-code-study-v1"
HEP_REV = "9a41762f73a8cb23bb5811b73d5aab164efcf378"
DATA_DIGESTS = {
    "HumanEvalPackPython.parquet":"ed5f15d789156e21222bfcd556c425a39042355c84ae1e8b058abd6a3d7f8075",
    "HumanEvalPlus.jsonl.gz":"272720b90ac375502c8ed23cd791c2a93dfb22a911641a494da74a426c09f101",
    "HumanEvalPack_README.md":"38c39ae78cf49c548a87082e0317c58681b682b3922d6edbb295abe843342632",
}
SOURCES = {
    "evalplus": ("evalplus/evalplus", "26d6d00bb1fd0fa37f39c99d5290da67891d1c5e", ["LICENSE", "evalplus/__init__.py", "evalplus/config.py", "evalplus/eval/__init__.py", "evalplus/eval/_special_oracle.py", "evalplus/eval/utils.py", "evalplus/data/humaneval.py"]),
    "octopack": ("bigcode-project/octopack", "e17a8f6470264286bc6a52eb8263582083bf3bf6", ["LICENSE", "README.md", "evaluation/create/humaneval-x/README.md", "evaluation/create/humaneval-x/data/python/data/humanevalpack.jsonl", "evaluation/run/humanevalpack_evaluation.ipynb"]),
    "harness": ("bigcode-project/bigcode-evaluation-harness", "fd7f6ed8841140e5923b48a96a48809c14d991a0", ["LICENSE", "lm_eval/tasks/humanevalpack.py"]),
}
HERE = Path(__file__).resolve().parent

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n").encode())
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Praxis-source-qualification"}), timeout=60) as response:
        return response.read()

def signature(code, entry):
    try:
        tree=ast.parse(code)
        functions=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==entry]
        if len(functions)!=1: return None, "missing_or_multiple_entry_points"
        fn=functions[0]
        sig={"kind":type(fn).__name__,"name":fn.name,"args":ast.dump(fn.args,include_attributes=False),"returns":ast.dump(fn.returns,include_attributes=False) if fn.returns else None}
        return sig,None
    except SyntaxError as error:
        return None,"syntax_error:"+str(error.lineno)

def literal_examples(text, entry):
    try: tree=ast.parse(textwrap.dedent(text))
    except SyntaxError as error: return [],0,"syntax_error:"+str(error.lineno)
    checks=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="check"]
    names={entry}|{arg.arg for node in checks for arg in node.args.args}
    found=[];unsupported=0
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name) or node.func.id not in names: continue
        if node.keywords:
            unsupported+=1;continue
        try:
            value=[ast.literal_eval(arg) for arg in node.args]
            found.append(sha(canonical(value)))
        except (ValueError,TypeError,SyntaxError): unsupported+=1
    return sorted(set(found)),unsupported,None

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir",type=Path,required=True)
    parser.add_argument("--offline",action="store_true")
    args=parser.parse_args();private=args.private_dir.resolve();private.mkdir(parents=True,exist_ok=True)
    if private.is_relative_to(HERE): raise ValueError("Raw sources/data must stay outside publication directory")
    cache=private/"qualification_cache";receipts=[]
    def cached(name,url,blob=None):
        path=cache/name
        if path.exists(): data=path.read_bytes()
        elif args.offline: raise FileNotFoundError(str(path))
        else:
            data=get(url);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        actual=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        if blob is not None and actual!=blob: raise ValueError("Git blob mismatch: "+name)
        if name in DATA_DIGESTS and sha(data)!=DATA_DIGESTS[name]:raise ValueError("Pinned dataset SHA256 mismatch: "+name)
        receipts.append({"path":name,"url":url,"bytes":len(data),"sha256":sha(data),"git_blob_sha1":actual if blob else None})
        return data
    for name,(repo,revision,paths) in SOURCES.items():
        raw=cached(f"trees/{name}.json",f"https://api.github.com/repos/{repo}/git/trees/{revision}?recursive=1")
        tree=json.loads(raw);assert not tree["truncated"]
        blobs={item['path']:item for item in tree['tree'] if item['type']=='blob'}
        for path in paths:
            cached(f"source/{name}/{path}",f"https://raw.githubusercontent.com/{repo}/{revision}/"+urllib.parse.quote(path),blobs[path]['sha'])
    hep_data=cached("HumanEvalPackPython.parquet",f"https://huggingface.co/datasets/bigcode/humanevalpack/resolve/{HEP_REV}/python/test-00000-of-00001.parquet")
    cached("HumanEvalPack_README.md",f"https://huggingface.co/datasets/bigcode/humanevalpack/resolve/{HEP_REV}/README.md")
    plus_data=cached("HumanEvalPlus.jsonl.gz","https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz")
    import pyarrow.parquet as pq
    import pyarrow as pa
    hep=pq.read_table(pa.BufferReader(hep_data)).to_pylist()
    plus=[json.loads(line) for line in gzip.decompress(plus_data).decode().splitlines() if line.strip()]
    hep_by={row['task_id']:row for row in hep};plus_by={row['task_id']:row for row in plus}
    expected={f'Python/{i}' for i in range(164)}
    assert len(hep)==len(hep_by)==len(plus)==len(plus_by)==164 and set(hep_by)==expected and set(plus_by)=={f'HumanEval/{i}' for i in range(164)}
    order=sorted(expected,key=lambda task:sha((SEED+'|task|'+task).encode()))
    development=set(order[:41]);pilot=order[:8]
    old=[json.loads(line) for line in (cache/'source/octopack/evaluation/create/humaneval-x/data/python/data/humanevalpack.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    old_by={row['task_id']:row for row in old}
    identity=[];runtime=[];input_manifest=[]
    for task_id in sorted(expected,key=lambda task:int(task.split('/')[1])):
        h=hep_by[task_id];p=plus_by[task_id.replace('Python/','HumanEval/')]
        programs={'canonical':h['prompt']+h['canonical_solution'],'buggy':h['prompt']+h['buggy_solution'],'reference':p['prompt']+p['canonical_solution']}
        signatures={};errors={}
        for variant,program in programs.items():signatures[variant],errors[variant]=signature(program,h['entry_point'])
        sig_match=h['entry_point']==p['entry_point'] and not any(errors.values()) and signatures['canonical']==signatures['buggy']==signatures['reference']
        examples,unsupported,example_error=literal_examples(h['example_test'],h['entry_point'])
        inputs={};base=set();plus_set=set()
        for suite,values in [('base',p['base_input']),('plus',p['plus_input'])]:
            for index,inp in enumerate(values):
                fp=sha(canonical(inp));row=inputs.setdefault(fp,{'case_id':fp,'input':inp,'memberships':[]})
                row['memberships'].append({'suite':suite,'index':index})
                (base if suite=='base' else plus_set).add(fp)
        forced=base|(set(examples)&set(inputs))
        additional=sorted(plus_set-forced,key=lambda fp:sha((SEED+'|input|'+task_id+'|'+fp).encode()))
        tools=forced|set(additional[:len(additional)//4]);outcomes=set(inputs)-tools
        assert not tools&outcomes and tools|outcomes==set(inputs)
        cases=[]
        for fp,row in sorted(inputs.items()):
            row['split']='tool' if fp in tools else 'outcome';cases.append(row)
        ident={'task_id':task_id,'plus_task_id':p['task_id'],'split':'development' if task_id in development else 'heldout','pilot':task_id in pilot,'entry_point':h['entry_point'],'id_alignment':True,'signature_alignment':sig_match,'signature_sha256':{k:sha(canonical(v)) if v else None for k,v in signatures.items()},'syntax_or_signature_errors':errors,'program_sha256':{k:sha(v.encode()) for k,v in programs.items()},'bug_type':h['bug_type'],'failure_symptoms':h['failure_symptoms'],'hf_vs_octopack_different_fields':[key for key in h if h.get(key)!=old_by.get(task_id,{}).get(key)],'base_inputs':len(p['base_input']),'plus_inputs':len(p['plus_input']),'unique_inputs':len(inputs),'duplicate_input_occurrences':len(p['base_input'])+len(p['plus_input'])-len(inputs),'tool_unique_inputs':len(tools),'outcome_unique_inputs':len(outcomes),'literal_example_calls_unique':len(examples),'literal_example_calls_matched':len(set(examples)&set(inputs)),'unsupported_example_calls':unsupported}
        ident['example_extraction_error']=example_error
        identity.append(ident)
        runtime.append({'task_id':task_id,'entry_point':h['entry_point'],'split':ident['split'],'pilot':ident['pilot'],'identity_eligible':sig_match,'programs':programs,'original_test':h['test'],'example_test':h['example_test'],'atol':p['atol'],'cases':cases})
        input_manifest.append({'task_id':task_id,'cases':[{key:value for key,value in row.items() if key!='input'} for row in cases]})
    bundle=private/'bundle';(bundle/'data').mkdir(parents=True,exist_ok=True);(bundle/'qualification').mkdir(exist_ok=True)
    task_bytes=('\n'.join(json.dumps(row,ensure_ascii=False,allow_nan=False) for row in runtime)+'\n').encode()
    (bundle/'data/tasks.jsonl').write_bytes(task_bytes)
    source_manifest={'schema_version':1,'sources':{name:{'repository':repo,'revision':rev} for name,(repo,rev,_) in SOURCES.items()},'humanevalpack_revision':HEP_REV,'humanevalplus_release':'v0.1.10','sources_executed':False,'files':receipts}
    input_bytes=('\n'.join(json.dumps(row,sort_keys=True,separators=(',',':')) for row in input_manifest)+'\n').encode()
    input_gzip=gzip.compress(input_bytes,mtime=0)
    (HERE/'INPUT_SPLITS.jsonl.gz').write_bytes(input_gzip)
    split_manifest={'seed':SEED,'task_order':order,'development_ids':order[:41],'heldout_ids':order[41:],'pilot_ids':pilot,'task_rank_rule':'sha256(seed + |task| + task_id)','input_rank_rule':'sha256(seed + |input| + task_id + | + input_fingerprint)','case_fingerprint':'SHA256 canonical JSON of positional input array; sorted object keys; scalar numeric spelling preserved','input_assignment_file':'INPUT_SPLITS.jsonl.gz','input_assignment_sha256':sha(input_gzip),'tasks':[{'task_id':row['task_id'],'case_count':len(row['cases']),'case_assignment_sha256':sha(canonical(row))} for row in input_manifest]}
    write_json(HERE/'SOURCE_MANIFEST.json',source_manifest)
    write_json(HERE/'TASK_IDENTITY.json',{'tasks':identity,'all164_retained':True,'program_execution':False})
    write_json(HERE/'SPLIT_MANIFEST.json',split_manifest)
    write_json(HERE/'PREPARATION_SUMMARY.json',{'tasks':164,'signature_aligned':sum(row['signature_alignment'] for row in identity),'syntax_error_counts':dict(collections.Counter(error for row in identity for error in row['syntax_or_signature_errors'].values() if error)),'base_input_occurrences':sum(row['base_inputs'] for row in identity),'plus_input_occurrences':sum(row['plus_inputs'] for row in identity),'unique_inputs':sum(row['unique_inputs'] for row in identity),'tool_inputs':sum(row['tool_unique_inputs'] for row in identity),'reserved_outcome_inputs':sum(row['outcome_unique_inputs'] for row in identity),'failure_symptoms':dict(collections.Counter(row['failure_symptoms'] for row in identity)),'tasks_payload_sha256':sha(task_bytes),'task_split_seed':SEED,'downloaded_programs_executed':False})
    for path in HERE.iterdir():
        if path.is_file() and path.suffix in {'.py','.json','.md','.txt','.sh','.gz'} or path.name=='Dockerfile': shutil.copyfile(path,bundle/'qualification'/path.name)
    (bundle/'vendor').mkdir(exist_ok=True)
    for name,(_,_,paths) in SOURCES.items():
        for path in paths:
            src=cache/'source'/name/path;dst=bundle/'vendor'/name/path;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    files={path.relative_to(bundle).as_posix():sha(path.read_bytes()) for path in sorted(bundle.rglob('*')) if path.is_file() and path.name!='BUNDLE_MANIFEST.json'}
    write_json(bundle/'BUNDLE_MANIFEST.json',{'files':files,'tasks_payload_sha256':sha(task_bytes),'programs_executed':False})
    tar_path=private/'praxis008-code-qualification.tar.gz'
    with tarfile.open(tar_path,'w:gz') as archive:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():archive.add(path,arcname=path.relative_to(bundle).as_posix())
    write_json(private/'BUNDLE_RECEIPT.json',{'bundle':str(tar_path),'sha256':sha(tar_path.read_bytes()),'bytes':tar_path.stat().st_size,'file_count':len(files)+1})
    print(json.dumps({'bundle':str(tar_path),'bytes':tar_path.stat().st_size,'sha256':sha(tar_path.read_bytes()),'signature_aligned':sum(row['signature_alignment'] for row in identity),'tasks':164,'programs_executed':False},indent=2))

if __name__=='__main__':main()
