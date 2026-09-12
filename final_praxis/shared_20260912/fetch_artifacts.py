"""Download immutable result files; never print generated benchmark responses."""
import argparse,hashlib,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.config import Config
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--small',action='store_true');a=p.parse_args()
assert a.run.replace('-','').isalnum()
a.out.mkdir(parents=True,exist_ok=True)
output_root=a.out.resolve(strict=True)
s3=boto3.Session(profile_name='praxis-build',region_name='us-east-1').client('s3',config=Config(connect_timeout=10,read_timeout=30,retries={'total_max_attempts':2},max_pool_connections=12))
bucket='praxis-garypagan-272615233626-us-east-1';prefix='final-praxis/20260912/runs/'+a.run+'/'
keys=[]
for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket,Prefix=prefix):
    for obj in page.get('Contents',[]):
        rel=obj['Key'][len(prefix):]
        if rel=='cloud_status.json' or rel.startswith('outputs/') and rel.endswith(('.json','.jsonl','.md','.txt')):
            if a.small and ('/cells/' in rel or '/receipts/' in rel):continue
            if obj['Size']>20_000_000:continue
            keys.append((obj['Key'],rel))
def fetch(pair):
    key,rel=pair;dest=(output_root/rel).resolve()
    if not dest.is_relative_to(output_root):raise ValueError('Unsafe download target: '+repr((rel,str(dest),str(output_root))))
    dest.parent.mkdir(parents=True,exist_ok=True)
    raw=s3.get_object(Bucket=bucket,Key=key)['Body'].read()
    if dest.exists() and dest.read_bytes()!=raw:raise ValueError('Previously downloaded artifact changed: '+rel)
    dest.write_bytes(raw)
    return {'file':rel,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
with ThreadPoolExecutor(max_workers=8) as pool:receipts=list(pool.map(fetch,keys))
(a.out/'download_receipts.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'run':a.run,'files':len(receipts),'bytes':sum(x['bytes'] for x in receipts),'out':str(a.out)}))
