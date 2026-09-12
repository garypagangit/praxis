import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cloud_control import client,save,BUCKET,HOSTS
s3=client('s3')
record=json.loads(s3.get_object(Bucket=BUCKET,Key='final-praxis/20260912/archives/stage2_archive_receipt.json')['Body'].read())
assert record['all_four_cpu_studies_completed_and_archived'] and len(record['archives'])==4
for archive in record['archives']:
    assert archive['server_checksum_verified']
    status=json.loads(s3.get_object(Bucket=BUCKET,Key='final-praxis/20260912/runs/'+archive['run_id']+'/cloud_status.json')['Body'].read())
    assert status['state']=='COMPLETED' and status['returncode']==0 and not status['sync_errors']
instance=HOSTS['004'];ec2=client('ec2')
prior=ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
assert prior['InstanceType'] in ('m6i.2xlarge','g5.xlarge')
if prior['State']['Name']=='running':print(save('stage2-complete-stop-request',ec2.stop_instances(InstanceIds=[instance])),flush=True)
ec2.get_waiter('instance_stopped').wait(InstanceIds=[instance],WaiterConfig={'Delay':5,'MaxAttempts':12})
if prior['InstanceType']!='g5.xlarge':
    ec2.modify_instance_attribute(InstanceId=instance,InstanceType={'Value':'g5.xlarge'})
for attempt in range(12):
    final=ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
    if final['State']['Name']=='stopped' and final['InstanceType']=='g5.xlarge':break
    time.sleep(2)
assert final['State']['Name']=='stopped' and final['InstanceType']=='g5.xlarge'
removed=[];scheduler=client('scheduler')
for name in ('praxis-20260912-stop-e8df2a60-812677','praxis-20260912-restore-stage2-e8df2a60'):
    try:existing=scheduler.get_schedule(Name=name)
    except scheduler.exceptions.ResourceNotFoundException:continue
    target=json.loads(existing['Target']['Input']);assert target.get('InstanceId')==instance or target.get('InstanceIds')==[instance]
    scheduler.delete_schedule(Name=name);removed.append(name)
print(save('stage2-completed-cpu-restored',{'instance':instance,'state':'stopped','restored_type':'g5.xlarge','archives':record['archives'],'deleted_schedules':removed,'results_and_existing_ebs_retained':True}),flush=True)
