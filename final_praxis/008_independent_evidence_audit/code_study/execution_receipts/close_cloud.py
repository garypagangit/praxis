"""Stop this run's host after durable completion and a passed artifact audit."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import time
import boto3

ROOT = Path(__file__).resolve().parent
ACTIVE = 'i-07178e293e8df2a60'
OTHER = 'i-039ed976444ade397'
WATCHDOG = 'praxis-20260912-stop-e8df2a60-3f1541'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main(audit_path):
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    if not (audit.get('integrity_pass') is True and audit.get('audit_complete') is True and audit.get('checks_failed') == 0):
        raise ValueError('Full extension artifact audit must pass before normal closeout')
    if audit.get('protocol_sha256') != '9e6ba43fd988b47273c13ae4a5dc569640d210d2178103afaab964ed2bf236c3':
        raise ValueError('Closeout requires the separately registered extension audit')
    if audit.get('counters', {}).get('results_receipt_sha256') != sha(ROOT/'study_v2/public_results/RESULTS_RECEIPT.json'):
        raise ValueError('Closeout audit does not bind the retained extension results')
    downloaded = json.loads((ROOT / 'V2_DOWNLOAD_RECEIPT.json').read_text())
    if downloaded.get('extracted') is not True or downloaded.get('ssm_status') != 'Success':
        raise ValueError('Completed extension archive must be retained locally')
    if sha(ROOT/'model_study_v2_archive.tar.gz') != downloaded['archive_sha256']:
        raise ValueError('Retained extension archive hash mismatch')
    status = json.loads((ROOT / 'study_v2/EXTENSION_PROCESS_STATUS.json').read_text())
    if status.get('status') != 'finished':raise ValueError('Extension is not complete')
    costs = []
    for directory in ('study', 'study_v2'):
        ledger = json.loads((ROOT / directory / 'budget.json').read_text())
        total = sum(row['accounted_usd'] for row in ledger['entries'].values())
        if ledger['limit_usd'] != 30 or total > 30:raise ValueError('Unexpected API ledger')
        costs.append(total)
    session = boto3.Session(profile_name='praxis-build', region_name='us-east-1')
    if session.client('sts').get_caller_identity()['Account'] != '272615233626':raise ValueError('Wrong AWS account')
    ec2 = session.client('ec2')
    def states():
        response = ec2.describe_instances(InstanceIds=[ACTIVE, OTHER])
        return {i['InstanceId']:i['State']['Name'] for r in response['Reservations'] for i in r['Instances']}
    before = states()
    requested = datetime.datetime.now(datetime.timezone.utc)
    stop_result = ec2.stop_instances(InstanceIds=[ACTIVE]) if before[ACTIVE] not in ('stopped', 'stopping') else {'StoppingInstances':[]}
    after = before
    for attempt in range(61):
        after = states()
        if after[ACTIVE] == 'stopped':break
        time.sleep(10)
    verified = datetime.datetime.now(datetime.timezone.utc)
    if after != {ACTIVE:'stopped', OTHER:'stopped'}:
        raise RuntimeError('Both campaign hosts must be verified stopped: ' + repr(after))
    watchdog = {'name':WATCHDOG, 'disposition':'not_attempted'}
    try:
        session.client('scheduler').delete_schedule(Name=WATCHDOG)
        watchdog['disposition']='deleted_after_verified_stop'
    except Exception as error:
        watchdog.update(disposition='retained_or_absent', detail=str(error))
    started = datetime.datetime.fromisoformat('2026-09-14T00:18:33+00:00')
    upper_hours = (verified - started).total_seconds()/3600
    compute = upper_hours*1.006
    receipt = {'verified_utc':verified.isoformat(),'stop_requested_utc':requested.isoformat(),
        'host_states_before':before, 'host_states':after, 'stop_response':stop_result,
        'account_id':'272615233626','region':'us-east-1','host_started_utc':started.isoformat(),
        'host_seconds_until_verified_stop_upper_estimate':upper_hours*3600,
        'g5_xlarge_usd_per_hour':1.006,'host_compute_usd_upper_estimate':compute,
        'api_original_usd_estimate':costs[0],'api_extension_usd_estimate':costs[1],
        'combined_api_usd_estimate':sum(costs), 'known_compute_and_api_subtotal_estimate':compute+sum(costs),
        'auxiliary_storage_and_transfer_allowance_usd':5,
        'total_incremental_usd_upper_estimate':compute+sum(costs)+5,
        'cost_scope':'Usage/rate API estimates plus host time through observed stopped state; additional five-dollar allowance for incidental storage/transfer. Not an invoice or an account-wide spending total.',
        'invoice_claimed':False,'new_inference_calls_after_closeout':0,'watchdog':watchdog,
        'extension_artifact_audit_sha256':sha(audit_path),'extension_download_receipt_sha256':sha(ROOT/'V2_DOWNLOAD_RECEIPT.json'),
        'original_download_receipt_sha256':sha(ROOT/'MODEL_DOWNLOAD_RECEIPT.json')}
    (ROOT/'CLOUD_CLOSEOUT.json').write_bytes((json.dumps(receipt,indent=2,default=str)+'\n').encode())
    print(json.dumps(receipt,indent=2,default=str))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',type=Path,required=True);a=p.parse_args();main(a.audit.resolve())
