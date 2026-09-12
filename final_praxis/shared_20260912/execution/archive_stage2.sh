set -eu
/mnt/praxis-20260912-004/venv/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,base64,zipfile,boto3
scratch=Path('/mnt/praxis-20260912-004')
runs=['fp006-containment-20260912-dd8a05a','fp007-selective-20260912-1c47aca','fp007-inline-20260912-648cdcd','fp006-empathy-20260912-5c33bc4']
s3=boto3.client('s3',region_name='us-east-1');bucket='praxis-garypagan-272615233626-us-east-1'
for run in runs:
    status=json.loads((scratch/run/'cloud_status.json').read_text())
    assert status['state']=='COMPLETED' and status['returncode']==0 and not status['sync_errors'],(run,status['state'])
records=[]
for run in runs:
    root=scratch/run;dest=scratch/'completed-stage2-archives';dest.mkdir(exist_ok=True);archive=dest/(run+'.zip')
    files=[p for p in (root/'outputs').rglob('*') if p.is_file() and p.suffix in ('.json','.jsonl','.md','.txt')]
    files += [root/'cloud_status.json',root/'bundle_manifest.json']
    hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    # Stable complete-run JSON must parse, including the final budget/progress snapshots.
    for p in files:
        if p.suffix=='.json':json.loads(p.read_text())
    if not archive.exists():
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
            for p in files:z.write(p,p.relative_to(root).as_posix())
            z.writestr('archive_file_hashes.json',json.dumps(hashes,sort_keys=True))
    with zipfile.ZipFile(archive) as z:
        assert json.loads(z.read('archive_file_hashes.json'))==hashes
        assert all(hashlib.sha256(z.read(name)).hexdigest()==digest for name,digest in hashes.items())
    raw=archive.read_bytes();digest=hashlib.sha256(raw).digest();checksum=base64.b64encode(digest).decode()
    key='final-praxis/20260912/archives/'+archive.name
    response=s3.put_object(Bucket=bucket,Key=key,Body=raw,ChecksumSHA256=checksum)
    assert response['ChecksumSHA256']==checksum
    records.append({'run_id':run,'uri':'s3://'+bucket+'/'+key,'sha256':digest.hex(),'bytes':len(raw),'files':len(files),'server_checksum_verified':True})
receipt={'all_four_cpu_studies_completed_and_archived':True,'archives':records}
(scratch/'stage2_archive_receipt.json').write_text(json.dumps(receipt,indent=2))
s3.put_object(Bucket=bucket,Key='final-praxis/20260912/archives/stage2_archive_receipt.json',Body=json.dumps(receipt,indent=2).encode())
print(json.dumps(receipt))
PY
