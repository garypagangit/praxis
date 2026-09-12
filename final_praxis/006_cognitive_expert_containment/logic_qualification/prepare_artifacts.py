"""Retrieve pinned code and authorized tokenizer bytes, without model inference."""
import argparse, json, shutil, urllib.request
from pathlib import Path
from model_loader import TOKENIZER,TOKENIZER_REVISION,verify_bundle,file_sha256

HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    for row in json.loads((HERE/'source_receipts.json').read_text()):
        path=a.out/'source'/row['file'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(row['url'],timeout=60) as response: content=response.read(20_000_001)
            if len(content)>20_000_000: raise ValueError('Unexpected source size')
            path.write_bytes(content)
        if file_sha256(path)!=row['sha256']: raise ValueError('Source hash mismatch')
    from huggingface_hub import hf_hub_download
    for row in json.loads((HERE/'tokenizer_receipts.json').read_text()):
        path=a.out/'tokenizer'/row['file'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            source=hf_hub_download(TOKENIZER,row['file'],revision=TOKENIZER_REVISION)
            shutil.copyfile(source,path)
        if file_sha256(path)!=row['sha256']: raise ValueError('Tokenizer hash mismatch')
    print(json.dumps({'status':'VERIFIED','artifacts':verify_bundle(a.out/'source')}))

if __name__=='__main__':main()
