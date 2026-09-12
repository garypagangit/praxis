"""Verify the completed campaign and retained archives without starting compute."""
import base64,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cloud_control import client,BUCKET,HOSTS

root=Path(__file__).resolve().parent
s3=client('s3')
archive_raw=s3.get_object(Bucket=BUCKET,Key='final-praxis/20260912/archives/stage2_archive_receipt.json')['Body'].read()
archive=json.loads(archive_raw)
assert archive['all_four_cpu_studies_completed_and_archived']
verified=[]
for item in archive['archives']:
    key=item['uri'].split('/'+BUCKET+'/',1)[1]
    head=s3.head_object(Bucket=BUCKET,Key=key,ChecksumMode='ENABLED')
    assert head['ContentLength']==item['bytes']
    assert head['ChecksumSHA256']==base64.b64encode(bytes.fromhex(item['sha256'])).decode()
    verified.append({'run_id':item['run_id'],'sha256':item['sha256'],'bytes':head['ContentLength'],'s3_checksum_verified':True})
snapshot=json.loads((root/'stage2_latest.json').read_text(encoding='utf-8'))
assert not snapshot['read_errors']
jobs={}
for name in ('005','006','007','006empathy','007inline'):
    status=snapshot[name]['cloud']
    assert status['state']=='COMPLETED' and status['returncode']==0 and not status['sync_errors']
    jobs[name]={'run_id':snapshot[name]['run_id'],'state':status['state'],'returncode':status['returncode'],'sync_errors':status['sync_errors']}
instances=[]
for reservation in client('ec2').describe_instances(InstanceIds=[HOSTS['004'],HOSTS['005']])['Reservations']:
    for instance in reservation['Instances']:
        assert instance['State']['Name']=='stopped' and instance['InstanceType']=='g5.xlarge'
        instances.append({'instance_id':instance['InstanceId'],'state':instance['State']['Name'],'instance_type':instance['InstanceType']})
scheduler=client('scheduler')
absent=[]
for name in ('praxis-20260912-stop-e8df2a60-812677','praxis-20260912-restore-stage2-e8df2a60'):
    try:scheduler.get_schedule(Name=name)
    except scheduler.exceptions.ResourceNotFoundException:absent.append(name)
    else:raise AssertionError('Obsolete schedule remains: '+name)
record={'verified_utc':datetime.now(timezone.utc).isoformat(),'jobs':jobs,'instances':instances,'obsolete_cpu_schedules_absent':absent,'archives':verified,'archive_receipt_sha256':hashlib.sha256(archive_raw).hexdigest(),'api_estimate_007_original_usd':snapshot['007']['accounted_api_usd_estimate'],'api_estimate_007_inline_usd':snapshot['007inline']['accounted_api_usd_estimate'],'existing_ebs_retained':True,'billing_note':'API estimates exclude EC2/EBS and are not an AWS invoice. Stopped hosts retain storage charges.'}
(root/'stage2_archive_receipt.json').write_bytes(archive_raw)
(root/'FINAL_CLOSEOUT.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record,indent=2))
