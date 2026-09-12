import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cloud_control import client,save,BUCKET,HOSTS
s3=client('s3');prefix='final-praxis/20260912/runs/fp005-20260912-37fdd3f/'
def get(name):return json.loads(s3.get_object(Bucket=BUCKET,Key=prefix+name)['Body'].read())
status=get('cloud_status.json');assert status['state']=='COMPLETED' and status['returncode']==0 and not status['sync_errors']
summary=get('outputs/summary.json');assert not summary['missing']
keys=[o['Key'] for page in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=prefix+'repair_protobuf_') for o in page.get('Contents',[])]
complete=[k for k in keys if k.endswith('/repair_complete.json')];assert len(complete)==1
base=complete[0][len(prefix):].rsplit('/',1)[0]+'/'
assert get(base+'repair_complete.json')['original_artifacts_unchanged']
assert get(base+'protected_artifacts_before.json')==get(base+'protected_artifacts_after.json')
ec2=client('ec2');instance=HOSTS['005']
prior=ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
assert prior['InstanceType']=='g5.xlarge'
if prior['State']['Name']=='running':print(save('005-complete-stop-request',ec2.stop_instances(InstanceIds=[instance])),flush=True)
ec2.get_waiter('instance_stopped').wait(InstanceIds=[instance],WaiterConfig={'Delay':5,'MaxAttempts':12})
name='praxis-20260912-stop-44ade397-dbece3';sched=client('scheduler');checked=sched.get_schedule(Name=name)
assert json.loads(checked['Target']['Input'])['InstanceIds']==[instance]
sched.delete_schedule(Name=name)
print(save('005-completed-stopped',{'instance':instance,'state':'stopped','summary_status':summary['status'],'original_artifacts_verified_unchanged':True,'removed_completed_watchdog':name,'retained_ebs':True}),flush=True)
