"""Archive a completed private review and its exact Git source, then verify S3."""
import argparse,base64,hashlib,io,json,subprocess,zipfile
from datetime import datetime,timezone
from pathlib import Path
from cloud_control import client,BUCKET

parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--study',required=True);parser.add_argument('--commit',required=True);parser.add_argument('--name',required=True);args=parser.parse_args()
assert args.name.replace('-','').isalnum() and args.study in ('automated_review','automated_review_v2')
prefix='final_praxis/005_defense_distillation/'+args.study+'/'
out=(args.repo/prefix/'outputs').resolve(strict=True)
status=json.loads((out/'automated_review.json').read_text(encoding='utf-8'))
assert status['workflow_status']=='AUTOMATED_REVIEW_COMPLETE' and status['completed_request_records']==120
aggregate=json.loads((out/'aggregates.json').read_text(encoding='utf-8'))
assert aggregate['artifact_validation']=='PASS'
members={}
for path in out.rglob('*'):
    if not path.is_file() or path.suffix not in ('.json','.jsonl','.md','.txt'):continue
    assert not path.is_symlink() and path.resolve().is_relative_to(out)
    raw=path.read_bytes()
    if path.suffix=='.json':json.loads(raw)
    members['outputs/'+path.relative_to(out).as_posix()]=raw
names=subprocess.check_output(['git','ls-tree','-r','--name-only',args.commit,'--',prefix],cwd=args.repo,text=True).splitlines()
assert any(n.endswith('/PREREGISTRATION.md') for n in names)
for name in names:members['source/'+name]=subprocess.check_output(['git','show',args.commit+':'+name],cwd=args.repo)
manifest={'source_commit':subprocess.check_output(['git','rev-parse',args.commit],cwd=args.repo,text=True).strip(),'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in members.items()}}
members['archive_manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
    for name,raw in sorted(members.items()):archive.writestr(name,raw)
blob=buffer.getvalue();digest=hashlib.sha256(blob).hexdigest();checksum=base64.b64encode(bytes.fromhex(digest)).decode()
key='final-praxis/20260912/automated-review/'+args.name+'.zip';s3=client('s3')
s3.put_object(Bucket=BUCKET,Key=key,Body=blob,ChecksumSHA256=checksum,ContentType='application/zip')
head=s3.head_object(Bucket=BUCKET,Key=key,ChecksumMode='ENABLED')
assert head['ChecksumSHA256']==checksum and head['ContentLength']==len(blob)
record={'verified_utc':datetime.now(timezone.utc).isoformat(),'uri':'s3://'+BUCKET+'/'+key,'sha256':digest,'bytes':len(blob),'files':len(members),'source_commit':manifest['source_commit'],'server_checksum_verified':True,'review_status':status['workflow_status'],'resolved_both':status['resolved_both'],'cases_processed':28,'api_accounted_usd_estimate':status['api_accounted_usd_estimate'],'human_review_performed':False}
dest=Path(__file__).resolve().parent/'execution'/(args.name+'-archive.json');dest.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2))
