"""Record and stop only the two pre-existing GPUs started for this task."""
import argparse
import datetime as dt
import json
from pathlib import Path
import boto3
from botocore.config import Config

INSTANCES = {'qwen': 'i-039ed976444ade397', 'mistral': 'i-07178e293e8df2a60'}
REQUIRED = {'qwen': ['001/discovery_agent_v2.zip', '002/discovery_v1.zip', '003/discovery_v2.zip'],
            'mistral': ['001/discovery_complete_v2.zip']}
ROOT = Path(__file__).resolve().parents[1] / 'execution/20260908'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['state', 'stop'])
parser.add_argument('--role', choices=list(INSTANCES))
args = parser.parse_args()
session = boto3.Session(profile_name='praxis-build', region_name='us-east-1')
cfg = Config(connect_timeout=10, read_timeout=30, retries={'max_attempts': 2})
ec2 = session.client('ec2', config=cfg)
now = dt.datetime.now(dt.timezone.utc)
if args.action == 'stop':
    if not args.role:
        raise SystemExit('An explicit GPU role is required')
    s3 = session.client('s3', config=cfg)
    receipts = []
    for suffix in REQUIRED[args.role]:
        key = 'final-praxis/20260908/' + suffix
        obj = s3.head_object(Bucket='praxis-garypagan-272615233626-us-east-1', Key=key)
        receipts.append({'key': key, 'bytes': obj['ContentLength'], 'last_modified': obj['LastModified']})
    response = ec2.stop_instances(InstanceIds=[INSTANCES[args.role]])
    record = {'requested_utc': now, 'role': args.role, 'instance': INSTANCES[args.role],
              'archived_outputs': receipts, 'transition': response['StoppingInstances']}
    (ROOT / (args.role + '_STOP_REQUEST.json')).write_text(json.dumps(record, indent=2, default=str) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2, default=str))
else:
    response = ec2.describe_instances(InstanceIds=list(INSTANCES.values()))
    rows = []
    for reservation in response['Reservations']:
        for item in reservation['Instances']:
            role = next(k for k, v in INSTANCES.items() if v == item['InstanceId'])
            stop_path = ROOT / (role + '_STOP_REQUEST.json')
            stop = json.loads(stop_path.read_text(encoding='utf-8')) if stop_path.exists() else None
            end = dt.datetime.fromisoformat(stop['requested_utc']) if stop else now
            hours = max(0, (end - item['LaunchTime']).total_seconds()) / 3600
            rows.append({'role': role, 'instance': item['InstanceId'], 'state': item['State']['Name'],
                         'instance_type': item['InstanceType'], 'launch_time': item['LaunchTime'],
                         'stop_requested_utc': stop['requested_utc'] if stop else None,
                         'hours_to_stop_request_or_check': hours,
                         'estimated_compute_usd_to_stop_request_or_check': round(hours * 1.006, 4)})
    record = {'checked_utc': now, 'instances': rows, 'rate_usd_per_hour': 1.006,
              'cost_note': 'Estimate through stop request or this check; excludes shutdown transition, storage, S3, transfer, taxes and discounts. This is not an AWS invoice.'}
    (ROOT / 'COMPUTE_CLOSEOUT.json').write_text(json.dumps(record, indent=2, default=str) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2, default=str))
