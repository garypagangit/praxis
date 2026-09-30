"""Send compact derived statistics, independently audit on AWS, stop the worker."""
import base64,hashlib,json,time,zlib
from pathlib import Path
from experiments.praxis_next.warning_control_20260930.cloud_control import control

HERE=Path(__file__).resolve().parent;PRIVATE=Path('C:/w/warning_control_20260930')
def main():
    c=control.Controller(PRIVATE/'settings.json');records={};total=0
    for p in (PRIVATE/'local_reference').glob('*.json'):
        d=json.loads(p.read_text())
        for r in d.get('baselines',[])+d.get('controlled',[]):
            cm=r['confusion'];key=json.dumps(cm);v=[r['macro_f1'],r['false_alerts'],r['benign_fpr'],r['warnings_per_100k']]
            for s in ['other_attack','movement','exfiltration']:v.extend([r[s]['missed'],r[s]['warning_recall'],r[s]['exact_recall']])
            if key in records:assert records[key]['values']==v
            records[key]={'cm':cm,'values':v};total+=1
    data=json.dumps({'records':list(records.values()),'represented_result_rows':total},separators=(',',':')).encode()
    (PRIVATE/'CLOUD_AUDIT_INPUT.json').write_bytes(data)
    encoded=base64.b64encode(zlib.compress(data,9)).decode();source=base64.b64encode(zlib.compress((HERE/'cloud_audit.py').read_bytes(),9)).decode()
    directory='/opt/dlami/nvme/praxis-warning-audit-'+c.active()['run_id'][:16]
    script="python3 - <<'WRITE_AUDIT'\nimport pathlib,zlib,base64\np=pathlib.Path("+repr(directory)+");p.mkdir(exist_ok=False)\n(p/'audit.py').write_bytes(zlib.decompress(base64.b64decode("+repr(source)+")))\n(p/'input.json').write_bytes(zlib.decompress(base64.b64decode("+repr(encoded)+")))\nWRITE_AUDIT\npython3 "+directory+'/audit.py '+directory+'/input.json\n'
    assert len(script.encode())<23000,len(script)
    (PRIVATE/'audit_bootstrap.sh').write_text(script,encoding='utf-8',newline='\n')
    print(json.dumps({'script_bytes':len(script),'distinct_matrices':len(records),'represented_rows':total}),flush=True)
    try:
        sent=c.send(PRIVATE/'audit_bootstrap.sh',120);print(json.dumps(sent),flush=True)
        for _ in range(30):
            time.sleep(3)
            rec=c.poll(sent['command_id']);detail=json.loads(Path(rec['receipt']).read_text())
            if detail['status'] in control.TERMINAL_STATES:break
        assert detail['status']=='Success',detail
        result=json.loads(detail['stdout']);assert result['passed']
        assert result['input_sha256']==hashlib.sha256(data).hexdigest()
        result['ssm_command_id']=sent['command_id'];result['source_sha256']=hashlib.sha256((HERE/'cloud_audit.py').read_bytes()).hexdigest()
        (HERE/'AWS_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:
        print(json.dumps(c.stop()),flush=True)
        for _ in range(60):
            result=c.finalize()
            if result['status']=='CLOSED_VERIFIED_STOPPED':print(json.dumps(result),flush=True);break
            time.sleep(5)
if __name__=='__main__':main()
