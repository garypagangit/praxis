"""Build explicitly sourced, command-only research records from pinned archives."""
import collections, hashlib, json, re, sys, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
DATA=Path('C:/w/aivh_review_20261005/public_data')
OUT=Path('C:/w/px117_aws_20261005')
sys.path.insert(0,str(HERE/'supplied'))
from aivh.ingest import Command,Session,model_family
from aivh.features import extract

def normalize(text):
    text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)
    text=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','IP_ADDRESS',text)
    return re.sub(r'\b\d+\b','NUMBER',text).strip()

def record(source,path,label,commands,family,task,environment):
    commands=[normalize(c) for c in commands][:10]
    s=Session(path,label,source,[Command(c,None) for c in commands])
    f=extract(s)
    features={k:v for k,v in f.items() if k.startswith(('C_','S_')) and k not in ['S_ref_prev_output_rate','S_repeat_after_error_rate']}
    text='\n'.join(commands)
    return {'id':hashlib.sha256((source+'|'+path).encode()).hexdigest()[:24],
        'source':source,'label':label,'family':family,'task':task,'environment':environment,
        'text':text,'fingerprint':hashlib.sha256(text.encode()).hexdigest(),
        'features':features,'n_commands':len(commands)}

def main():
    OUT.mkdir(exist_ok=True)
    rows=[]; audit={'human':collections.Counter(),'agent':collections.Counter(),'agent_rejections_by_model':collections.Counter()}
    for name,md5 in [('kypo_data.zip','3ef1a76ef43904e0842fca98e613cca7'),('Logs_final.zip','4f3b30538e6e4c492716f87f184dd816')]:
        assert hashlib.md5((DATA/name).read_bytes()).hexdigest()==md5
    with zipfile.ZipFile(DATA/'kypo_data.zip') as z:
        for path in z.namelist():
            if not path.endswith('useractions.json'):continue
            audit['human']['files_seen']+=1
            events=[json.loads(t) for t in z.read(path).decode('utf-8-sig').splitlines() if t.strip()]
            cmds=[r['cmd'] for r in events if r.get('cmd_type')=='bash-command' and isinstance(r.get('cmd'),str) and r['cmd'].strip()]
            if not cmds:audit['human']['no_bash_commands']+=1;continue
            rows.append(record('KYPO',path,0,cmds,'human',path.split('/')[0],'kypo_training'))
            audit['human']['eligible']+=1
    with zipfile.ZipFile(DATA/'Logs_final.zip') as z:
        for path in z.namelist():
            parts=path.split('/')
            if len(parts)!=6 or parts[0]!='Logs_final' or not path.endswith('.json'):continue
            audit['agent']['files_seen']+=1
            raw=json.loads(z.read(path)); selected=raw[1:11];cmds=[]
            for turn in selected:
                if not isinstance(turn,list) or len(turn)!=3 or not isinstance(turn[2],list) or len(turn[2])!=2:
                    break
                cmd=turn[2][1]
                if not isinstance(cmd,str) or not cmd.strip():break
                cmds.append(cmd)
            if not selected or len(cmds)!=len(selected):
                audit['agent']['rejected_ambiguous_prefix']+=1
                audit['agent_rejections_by_model'][parts[4]]+=1
                continue
            rows.append(record('Honey',path,1,cmds,model_family(parts[4]),parts[1],parts[3]))
            audit['agent']['eligible']+=1
    assert len({r['id'] for r in rows})==len(rows)
    (OUT/'records.json').write_text(json.dumps(rows),encoding='utf-8')
    summary={'stage':'DEVELOPMENT_ONLY_SOURCE_CONFOUNDED',
        'audit':{k:dict(v) for k,v in audit.items()},'records':len(rows),
        'duplicate_fingerprints':len(rows)-len({r['fingerprint'] for r in rows}),
        'feature_names':list(rows[0]['features']),
        'data_sha256':hashlib.sha256((OUT/'records.json').read_bytes()).hexdigest(),
        'source_label_contingency':dict(collections.Counter(r['source']+'|'+str(r['label']) for r in rows))}
    (HERE/'DEVELOPMENT_DATA.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
