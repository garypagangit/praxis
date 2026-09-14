"""Bounded AWS qualification control. Credentials use the normal AWS profile chain.

Settings and operational receipts belong outside the public repository. This tool
does not create roles, alter permissions, invoke model APIs, or provision hosts.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

import boto3
from botocore.config import Config


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['status', 'start', 'send', 'poll', 'upload', 'download', 'stop'])
    p.add_argument('--settings', type=Path, required=True)
    p.add_argument('--protocol', type=Path, action='append', default=[])
    p.add_argument('--script', type=Path)
    p.add_argument('--path', type=Path)
    p.add_argument('--key')
    p.add_argument('--command-id')
    p.add_argument('--timeout', type=int, default=1800)
    a = p.parse_args()
    settings = json.loads(a.settings.read_text())
    session = boto3.Session(profile_name=settings['profile'], region_name=settings['region'])
    config = Config(connect_timeout=10, read_timeout=30, retries={'total_max_attempts': 2})
    client = lambda name: session.client(name, config=config)
    instance = settings['instance']
    receipts = a.settings.parent / 'receipts'
    receipts.mkdir(exist_ok=True)
    now = lambda: dt.datetime.now(dt.timezone.utc)

    def save(value):
        name = now().strftime('%Y%m%dT%H%M%SZ') + '-' + a.action + '-' + uuid.uuid4().hex[:6] + '.json'
        path = receipts / name
        path.write_text(json.dumps(value, indent=2, default=str) + '\n')
        print(json.dumps({'receipt': str(path), 'result': value}, default=str), flush=True)

    if a.action == 'start':
        if not a.protocol:
            raise ValueError('Committed research protocol required')
        freezes = []
        for protocol in a.protocol:
            protocol = protocol.resolve()
            repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=protocol.parent, text=True).strip())
            rel = protocol.relative_to(repo).as_posix()
            tracked = subprocess.check_output(['git', 'show', 'HEAD:' + rel], cwd=repo)
            if tracked != protocol.read_bytes():
                raise ValueError('Protocol differs from its exact committed bytes')
            freezes.append({'path': rel, 'sha256': digest(protocol), 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()})
        ec2 = client('ec2')
        prior = ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
        if prior['State']['Name'] != 'stopped' or prior['InstanceType'] != 'g5.xlarge':
            raise ValueError('Expected the explicitly selected stopped g5.xlarge')
        behavior = ec2.describe_instance_attribute(InstanceId=instance, Attribute='instanceInitiatedShutdownBehavior')
        if behavior['InstanceInitiatedShutdownBehavior']['Value'] != 'stop':
            raise ValueError('Guest shutdown must stop rather than terminate')
        stop_at = now() + dt.timedelta(hours=2)
        schedule = 'praxis-qual-20260914-' + uuid.uuid4().hex[:8]
        scheduler = client('scheduler')
        scheduler.create_schedule(Name=schedule, ScheduleExpression='at(' + stop_at.strftime('%Y-%m-%dT%H:%M:%S') + ')', ScheduleExpressionTimezone='UTC', FlexibleTimeWindow={'Mode': 'OFF'}, ActionAfterCompletion='DELETE', Target={'Arn': 'arn:aws:scheduler:::aws-sdk:ec2:stopInstances', 'RoleArn': settings['stop_role_arn'], 'Input': json.dumps({'InstanceIds': [instance]}), 'RetryPolicy': {'MaximumRetryAttempts': 3, 'MaximumEventAgeInSeconds': 300}}, Description='Stop the authorized qualification host within two hours')
        checked = scheduler.get_schedule(Name=schedule)
        assert checked['State'] == 'ENABLED' and json.loads(checked['Target']['Input'])['InstanceIds'] == [instance]
        state = {'instance': instance, 'schedule': schedule, 'scheduled_stop_utc': stop_at.isoformat(), 'protocols': freezes, 'started_request_utc': now().isoformat(), 'usd_per_hour': 1.006, 'maximum_hours': 2, 'reserve_usd': 25}
        (a.settings.parent / 'ACTIVE_RUN.json').write_text(json.dumps(state, indent=2) + '\n')
        try:
            state['response'] = ec2.start_instances(InstanceIds=[instance])
        except Exception:
            # The schedule remains as a fail-safe even if the start response is ambiguous.
            save(state)
            raise
        save(state)
    elif a.action == 'status':
        item = client('ec2').describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
        information = client('ssm').describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': [instance]}])['InstanceInformationList']
        save({'instance': instance, 'state': item['State']['Name'], 'type': item['InstanceType'], 'ssm': [{'ping': x['PingStatus'], 'platform': x.get('PlatformName')} for x in information]})
    elif a.action == 'send':
        active = json.loads((a.settings.parent / 'ACTIVE_RUN.json').read_text())
        remaining = (dt.datetime.fromisoformat(active['scheduled_stop_utc']) - now()).total_seconds()
        if not 30 <= a.timeout <= 3600 or a.timeout >= remaining:
            raise ValueError('Worker timeout must fit within the external stop deadline')
        script = a.script.read_text(encoding='utf-8')
        if len(script.encode()) > 23000:
            raise ValueError('Use a hash-checked S3 bundle for large workers')
        response = client('ssm').send_command(InstanceIds=[instance], DocumentName='AWS-RunShellScript', Parameters={'commands': [script], 'executionTimeout': [str(a.timeout)]}, TimeoutSeconds=120, Comment='Authorized Praxis009/010 qualification: ' + a.script.name[:50], OutputS3BucketName=settings['bucket'], OutputS3KeyPrefix=settings['prefix'] + 'ssm')
        save({'command_id': response['Command']['CommandId'], 'script_sha256': digest(a.script), 'timeout': a.timeout, 'submitted_utc': now().isoformat()})
    elif a.action == 'poll':
        r = client('ssm').get_command_invocation(CommandId=a.command_id, InstanceId=instance)
        save({k: r.get(k) for k in ['CommandId', 'Status', 'ResponseCode', 'ExecutionElapsedTime', 'StandardOutputContent', 'StandardErrorContent', 'StandardOutputUrl', 'StandardErrorUrl']})
    elif a.action in ['upload', 'download']:
        if not a.key or not a.key.startswith(settings['prefix']) or '..' in a.key.split('/'):
            raise ValueError('New qualification prefix required')
        if a.action == 'upload':
            client('s3').upload_file(str(a.path), settings['bucket'], a.key)
        else:
            a.path.parent.mkdir(parents=True, exist_ok=True)
            client('s3').download_file(settings['bucket'], a.key, str(a.path))
        save({'key': a.key, 'path': str(a.path), 'sha256': digest(a.path), 'bytes': a.path.stat().st_size})
    elif a.action == 'stop':
        save(client('ec2').stop_instances(InstanceIds=[instance]))


if __name__ == '__main__':
    main()
