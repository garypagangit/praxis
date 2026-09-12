"""Read-only, aggregate-only monitor for the new studies and original005 repair."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import boto3
from botocore.config import Config
RUNS={'006':'fp006-containment-20260912-dd8a05a','007':'fp007-selective-20260912-1c47aca','005':'fp005-20260912-37fdd3f','007inline':'fp007-inline-20260912-648cdcd','006empathy':'fp006-empathy-20260912-5c33bc4'}
ROOT=Path(__file__).resolve().parent
read_errors=[]
BUCKET='praxis-garypagan-272615233626-us-east-1'
s3=boto3.Session(profile_name='praxis-build',region_name='us-east-1').client('s3',config=Config(connect_timeout=10,read_timeout=20,retries={'total_max_attempts':2},max_pool_connections=12))
def get(run,name):
    try:return json.loads(s3.get_object(Bucket=BUCKET,Key='final-praxis/20260912/runs/'+run+'/'+name)['Body'].read())
    except s3.exceptions.NoSuchKey:return None
    except json.JSONDecodeError:
        read_errors.append({'run':run,'file':name,'reason':'JSON snapshot unavailable; may be updating'})
        return None
def read(pair):
    number,run=pair;record={'run_id':run,'cloud':get(run,'cloud_status.json')}
    if number.startswith('006'):
        for name in ('sanity','calibration_frozen','summary'):record[name]=get(run,'outputs/'+name+'.json')
    elif number.startswith('007'):
        progress=get(run,'outputs/progress.json')
        record['progress']={k:progress.get(k) for k in ('model','split','complete_questions','planned_questions','initial','validity','technical_gate_passed')} if progress else None
        budget=get(run,'outputs/budget.json')
        record['accounted_api_usd_estimate']=sum(x['accounted_usd'] for x in budget['entries'].values()) if budget else None
        record['ledger_entries']=len(budget['entries']) if budget else None
        record['complete']=get(run,'outputs/complete.json')
        for model in ('qwen.qwen3-coder-next','mistral.devstral-2-123b'):
            for split in ('cal','test'):
                summary=get(run,'outputs/'+model+'__'+split+'.json')
                if summary:record[model+'/'+split]={k:summary.get(k) for k in ('initial','validity','technical_gate_passed','paired_comparisons')}
    else:record['summary']=get(run,'outputs/summary.json')
    try:
        tail=s3.get_object(Bucket=BUCKET,Key='final-praxis/20260912/runs/'+run+'/driver.log',Range='bytes=-18000')['Body'].read().decode(errors='replace')
        record['traceback_present_in_tail']='Traceback (most recent call last):' in tail
        lines=[]
        for line in tail.splitlines():
            if not line.startswith('{'):continue
            try:x=json.loads(line)
            except ValueError:continue
            if 'event' in x or 'completed_confirmation_questions' in x or 'complete_questions' in x:lines.append(x)
        record['latest_events']=lines[-3:]
    except s3.exceptions.NoSuchKey:pass
    return number,record
with ThreadPoolExecutor(max_workers=3) as pool:result=dict(pool.map(read,RUNS.items()))
result['checked_utc']=datetime.now(timezone.utc).isoformat()
result['read_errors']=read_errors
path=ROOT/'execution/stage2_latest.json';path.write_text(json.dumps(result,indent=2,default=str)+'\n',encoding='utf-8')
display=json.loads(json.dumps(result,default=str))
for name in RUNS:
    c=display[name].get('cloud')
    if c:display[name]['cloud']={k:c.get(k) for k in ('state','updated_utc','elapsed_seconds','sync_errors','returncode')}
summary=display['005'].get('summary')
if summary:display['005']['summary']={k:summary.get(k) for k in ('status','missing','arms','limitations')}
print(json.dumps(display,indent=2,default=str))
