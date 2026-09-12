"""Create a hashed bundle restricted to the new study and this cloud runtime."""
import argparse, hashlib, json, subprocess, zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--study',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.repo.resolve()
    study=(root/'final_praxis'/a.study).resolve()
    if study.parent!=root/'final_praxis' or not study.is_dir():raise ValueError('Explicit new study required')
    files=[]
    for directory in [study,root/'final_praxis/shared_20260912']:
        for path in directory.rglob('*'):
            if not path.is_file():continue
            if path.is_symlink():raise ValueError('Symlink not permitted in cloud bundle')
            if set(path.relative_to(directory).parts).intersection({'__pycache__','execution','runs','results','.venv','cache','hf_cache','vendor','checkpoints'}):continue
            if path.suffix in {'.pyc','.zip','.safetensors','.pt','.pth'}:continue
            if path.stat().st_size>25_000_000:raise ValueError('Unexpected large source artifact')
            files.append(path)
    manifest={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):archive.write(path,path.relative_to(root).as_posix())
        archive.writestr('bundle_manifest.json',json.dumps({'git_commit':commit,'files':manifest},indent=2))
    print(json.dumps({'bundle':str(a.output),'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'files':len(files),'bytes':a.output.stat().st_size,'commit':commit}))

if __name__=='__main__':main()
