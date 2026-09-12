"""Auditable cloud control for the authorized004–007 pilot campaign."""
from __future__ import annotations
import argparse, base64, hashlib, json, shlex, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parent
BUCKET = 'praxis-garypagan-272615233626-us-east-1'
PREFIX = 'final-praxis/20260912/'
ACCOUNT = '272615233626'
HOSTS = {'004': 'i-07178e293e8df2a60', '005': 'i-039ed976444ade397'}
MODELS = ['qwen.qwen3-coder-next', 'mistral.devstral-2-123b']
REMOTE = '/opt/praxis/campaign-20260912'

def session():
    return boto3.Session(profile_name='praxis-build', region_name='us-east-1')

def client(name):
    return session().client(name, config=Config(connect_timeout=10, read_timeout=30,
        retries={'total_max_attempts': 2}))

def save(label, value):
    directory = ROOT / 'execution'; directory.mkdir(parents=True, exist_ok=True)
    path = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + label + '-' + uuid.uuid4().hex[:6] + '.json')
    path.write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')
    return str(path)

def freeze(prereg, option, hours):
    prereg = Path(prereg).resolve()
    if option not in HOSTS or not 0 < hours <= 8:
        raise ValueError('Unknown host or runtime beyond8hours')
    content = prereg.read_bytes()
    if len(content) < 500:
        raise ValueError('Substantive preregistration required')
    import subprocess
    repo = subprocess.check_output(['git','rev-parse','--show-toplevel'], cwd=prereg.parent, text=True).strip()
    relative = prereg.relative_to(Path(repo)).as_posix()
    committed = subprocess.check_output(['git','show','HEAD:' + relative], cwd=repo)
    if committed != content:
        # Git normalizes CRLF; only that tracked serialization distinction is allowed.
        if committed.replace(b'\r\n',b'\n') != content.replace(b'\r\n',b'\n'):
            raise ValueError('Preregistration differs from committed bytes')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    value = {'option':option,'preregistration':str(prereg),'preregistration_sha256':hashlib.sha256(content).hexdigest(),
        'commit':commit,'recorded_utc':datetime.now(timezone.utc).isoformat(),'hours_limit':hours,
        'compute_usd_bound':hours*1.006,'pilot_total_usd_bound':75,'invoice_claimed':False}
    save('freeze-'+option,value)
    return value

def ensure_role_and_schedule(instance, hours):
    iam = client('iam'); name = 'praxis-20260912-stop-only'
    trust = {'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'scheduler.amazonaws.com'},
        'Action':'sts:AssumeRole','Condition':{'StringEquals':{'aws:SourceAccount':ACCOUNT}}}]}
    try:
        role = iam.get_role(RoleName=name)['Role']
    except iam.exceptions.NoSuchEntityException:
        role = iam.create_role(RoleName=name,AssumeRolePolicyDocument=json.dumps(trust),
            Description='Stop only the two authorized20260912Praxis experiment hosts')['Role']
        save('created-watchdog-role',{'arn':role['Arn']})
    policy = {'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'ec2:StopInstances',
        'Resource':['arn:aws:ec2:us-east-1:'+ACCOUNT+':instance/'+i for i in HOSTS.values()]}]}
    iam.put_role_policy(RoleName=name,PolicyName='StopExperimentHostsOnly',PolicyDocument=json.dumps(policy))
    schedule_name = 'praxis-20260912-stop-'+instance[-8:]+'-'+uuid.uuid4().hex[:6]
    stop_at = datetime.now(timezone.utc)+timedelta(hours=hours)
    params = dict(Name=schedule_name,ScheduleExpression='at('+stop_at.strftime('%Y-%m-%dT%H:%M:%S')+')',
        ScheduleExpressionTimezone='UTC',FlexibleTimeWindow={'Mode':'OFF'},ActionAfterCompletion='DELETE',
        Target={'Arn':'arn:aws:scheduler:::aws-sdk:ec2:stopInstances','RoleArn':role['Arn'],
            'Input':json.dumps({'InstanceIds':[instance]}),
            'RetryPolicy':{'MaximumRetryAttempts':3,'MaximumEventAgeInSeconds':300}},
        Description='Authorized bounded Praxis campaign automatic host stop')
    sched = client('scheduler')
    for attempt in range(6):
        try:
            result = sched.create_schedule(**params); break
        except sched.exceptions.ValidationException:
            if attempt == 5: raise
            time.sleep(3)
    checked = sched.get_schedule(Name=schedule_name)
    if checked['State'] != 'ENABLED': raise RuntimeError('Cloud watchdog not enabled')
    save('watchdog',{'request':params,'response':result,'verified':checked})
    return {'name':schedule_name,'stop_at_utc':stop_at.isoformat()}

def start(option, prereg, hours):
    record = freeze(prereg, option, hours)
    ec2 = client('ec2'); instance = HOSTS[option]
    prior = ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
    if prior['State']['Name'] != 'stopped':
        raise RuntimeError('Refuse to take over a host that is not stopped')
    behavior = ec2.describe_instance_attribute(InstanceId=instance,Attribute='instanceInitiatedShutdownBehavior')
    if behavior['InstanceInitiatedShutdownBehavior']['Value'] != 'stop':
        raise RuntimeError('Guest shutdown must stop, never terminate')
    watchdog = ensure_role_and_schedule(instance, hours)
    response = ec2.start_instances(InstanceIds=[instance])
    result = dict(record,instance=instance,watchdog=watchdog,response=response)
    print(json.dumps({'started':instance,'receipt':save('start-'+option,result),'watchdog':watchdog}),flush=True)

def enable_bedrock():
    iam = client('iam')
    policy = {'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'bedrock:InvokeModel',
        'Resource':['arn:aws:bedrock:us-east-1::foundation-model/'+m for m in MODELS]}]}
    response=iam.put_role_policy(RoleName='praxis-data-loader-role',PolicyName='Praxis20260912TwoModelInference',PolicyDocument=json.dumps(policy))
    print(save('scoped-bedrock-role-policy',{'policy':policy,'response':response}))

def send(option, script, timeout):
    if option not in HOSTS or not 30 <= timeout <= 28800: raise ValueError('Invalid execution scope')
    text = Path(script).read_text(encoding='utf-8')
    if len(text.encode()) > 23000: raise ValueError('Use an S3 bundle for larger scripts')
    params = dict(InstanceIds=[HOSTS[option]],DocumentName='AWS-RunShellScript',
        Parameters={'commands':[text],'executionTimeout':[str(timeout)]},TimeoutSeconds=120,
        Comment='AuthorizedFinalPraxis'+option+': '+Path(script).name,
        OutputS3BucketName=BUCKET,OutputS3KeyPrefix=PREFIX+'ssm')
    result = client('ssm').send_command(**params)
    command_id = result['Command']['CommandId']
    print(json.dumps({'command_id':command_id,'receipt':save('send-'+option,{'parameters':params,'response':result})}),flush=True)

def status(option, command_id=None):
    if command_id:
        result=client('ssm').get_command_invocation(CommandId=command_id,InstanceId=HOSTS[option])
        selected={k:result.get(k) for k in ['CommandId','Status','ResponseCode','ExecutionElapsedTime','StandardOutputContent','StandardErrorContent']}
    else:
        ec2=client('ec2').describe_instances(InstanceIds=[HOSTS[option]])['Reservations'][0]['Instances'][0]
        ssm=client('ssm').describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[HOSTS[option]]}])
        selected={'instance':HOSTS[option],'state':ec2['State'],'ssm':ssm['InstanceInformationList']}
    print(json.dumps({'receipt':save('status-'+option,selected),'result':selected},default=str),flush=True)

def transfer(action, path, key):
    if not key.startswith(PREFIX) or '..' in key.split('/'): raise ValueError('New campaign prefix required')
    path=Path(path)
    if action=='upload':
        client('s3').upload_file(str(path),BUCKET,key)
        result={'uploaded':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        client('s3').download_file(BUCKET,key,str(path))
        result={'downloaded':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    result['uri']='s3://'+BUCKET+'/'+key
    print(json.dumps({'receipt':save(action,result),**result}))

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['start','status','send','upload','download','stop','enable-bedrock'])
    p.add_argument('--option',choices=HOSTS);p.add_argument('--prereg');p.add_argument('--hours',type=float,default=8)
    p.add_argument('--script');p.add_argument('--timeout',type=int,default=600);p.add_argument('--command-id');p.add_argument('--path');p.add_argument('--key')
    a=p.parse_args()
    if a.action=='start':start(a.option,a.prereg,a.hours)
    elif a.action=='status':status(a.option,a.command_id)
    elif a.action=='send':send(a.option,a.script,a.timeout)
    elif a.action in ['upload','download']:transfer(a.action,a.path,a.key)
    elif a.action=='enable-bedrock':enable_bedrock()
    else:print(save('stop-'+a.option,client('ec2').stop_instances(InstanceIds=[HOSTS[a.option]])))

if __name__=='__main__':main()
