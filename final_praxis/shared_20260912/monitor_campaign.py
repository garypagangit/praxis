"""Read safe aggregate AWS campaign status; no inference or resource mutation."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
import boto3
from botocore.config import Config
RUNS={'004_qualification':'fp004-20260912-73b5637','004':'fp004-model-20260912-6a22dc3','005':'fp005-20260912-37fdd3f','006':'fp006-20260912-11227b8','006_arc':'fp006-arc-20260912-6372d09','007':'fp007-20260912-81b445c'}
RUNS['004_source_access']='fp004-cap-20260912-4d97547'
BUCKET='praxis-garypagan-272615233626-us-east-1'
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    session=boto3.Session(profile_name='praxis-build',region_name='us-east-1')
    s3=session.client('s3',config=Config(connect_timeout=5,read_timeout=15,retries={'total_max_attempts':1}))
    result={'checked_utc':datetime.now(timezone.utc).isoformat(),'runs':{}}
    for option,run in RUNS.items():
        root='final-praxis/20260912/runs/'+run+'/';row={'run_id':run,'s3_uri':'s3://'+BUCKET+'/'+root}
        for label,key in [('cloud','cloud_status.json'),('qualification','outputs/qualification_summary.json'),('summary','outputs/summary.json'),('numerics','outputs/numerical_checks.json'),('budget','outputs/budget.json')]:
            if label=='summary' and option=='004':key='outputs/pilot_summary.json'
            if label=='summary' and option=='004_source_access':key='outputs/capability_summary.json'
            if label=='qualification' and option!='004_qualification':continue
            if label=='numerics' and option!='006':continue
            if label=='budget' and option not in {'004','007','004_source_access'}:continue
            try:
                value=json.loads(s3.get_object(Bucket=BUCKET,Key=root+key)['Body'].read())
                if label=='qualification':value={k:value[k] for k in ['stage','model_calls','qualified','interpretation']}
                if label=='cloud':value={k:value.get(k) for k in ['state','updated_utc','elapsed_seconds','returncode','sync_errors']}
                if label=='budget':value={'limit_usd':value['limit_usd'],'attempts':len(value.get('entries',{})),
                    'accounted_usd_estimate':sum(r.get('accounted_usd',r.get('reserved_usd',0)) for r in value.get('entries',{}).values()),'invoice_claimed':False}
                if label=='summary' and option=='007':value={k:value[k] for k in ['status','saved_cells','planned_requests']}|{'model_gates':{k:v for k,v in value['results'].items() if k.endswith('/gate')}}
                if label=='summary' and option=='004':value={k:value[k] for k in ['completed_arm_records','expected_arm_records','interpretation']}|{'initial':value['metrics']['original']}
                if label=='summary' and option=='004_source_access':value={k:v for k,v in value.items() if k!='records'}
                row[label]=value
            except s3.exceptions.NoSuchKey:pass
            except Exception as e:row[label+'_read_error']=type(e).__name__
        result['runs'][option]=row
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
