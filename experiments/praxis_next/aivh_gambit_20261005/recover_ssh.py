"""Bounded recovery of this attempt's incomplete install; restore network state."""
import ipaddress,json,subprocess,time,os
from pathlib import Path
import boto3,requests
HERE=Path(__file__).resolve().parent
OUT=Path(os.environ.get('PRAXIS_AWS_PRIVATE','C:/w/assurance_aws_20261004_attempt6'))
INSTANCE='i-07178e293e8df2a60'
s=boto3.Session(profile_name='praxis-build',region_name='us-east-1')
ec=s.client('ec2')
i=ec.describe_instances(InstanceIds=[INSTANCE])['Reservations'][0]['Instances'][0]
assert i['State']['Name']=='running'
prior=[g['GroupId'] for g in i['SecurityGroups']]
source=str(ipaddress.IPv4Address(requests.get('https://checkip.amazonaws.com',timeout=10).text.strip()))
target=str(ipaddress.IPv4Address(i['PublicIpAddress']))
key=OUT/'repair_key'
if not key.exists(): subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
group=None; attached=False
try:
    group=ec.create_security_group(GroupName='praxis-assurance-repair-'+str(int(time.time())),Description='Temporary SSH from operator IP only for assurance disk recovery',VpcId=i['VpcId'])['GroupId']
    ec.authorize_security_group_ingress(GroupId=group,IpPermissions=[{'IpProtocol':'tcp','FromPort':22,'ToPort':22,'IpRanges':[{'CidrIp':source+'/32','Description':'Temporary operator recovery'}]}])
    ec.modify_instance_attribute(InstanceId=INSTANCE,Groups=prior+[group]); attached=True
    sent=s.client('ec2-instance-connect').send_ssh_public_key(InstanceId=INSTANCE,InstanceOSUser='ubuntu',SSHPublicKey=Path(str(key)+'.pub').read_text(),AvailabilityZone=i['Placement']['AvailabilityZone'])
    assert sent['Success']
    cmd=['ssh','-i',str(key),'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(OUT/'repair_known_hosts'),'-o','ConnectTimeout=15','ubuntu@'+target,'sudo bash -s']
    script=Path(os.environ.get('PRAXIS_SSH_SCRIPT',str(HERE/'recover_disk.sh')))
    r=subprocess.run(cmd,input=script.read_text().encode('utf-8'),capture_output=True,timeout=70)
    stdout=r.stdout.decode('utf-8',errors='replace'); stderr=r.stderr.decode('utf-8',errors='replace')
    (OUT/'DISK_RECOVERY.txt').write_text(stdout+'\n'+stderr)
    print(stdout[-1800:]); print('Recovery exit',r.returncode)
    assert r.returncode==0,stderr
finally:
    if attached: ec.modify_instance_attribute(InstanceId=INSTANCE,Groups=prior)
    if group: ec.delete_security_group(GroupId=group)
    (OUT/'NETWORK_RESTORED.json').write_text(json.dumps({'instance':INSTANCE,'original_security_groups':prior,'temporary_group_deleted':group,'restored':True},indent=2))
