"""Inspect downloaded public logs as data; execute no logged commands."""
import collections
import hashlib
import json
import sys
import zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
DATA=Path('C:/w/aivh_review_20261005/public_data')
sys.path.insert(0,str(HERE/'supplied'))
from aivh.ingest import _parse_zenodo_turns

def identity(name,expected):
    path=DATA/name
    blob=path.read_bytes()
    md5=hashlib.md5(blob).hexdigest()
    assert md5==expected, name
    return {'file':name,'bytes':len(blob),'md5':md5,'sha256':hashlib.sha256(blob).hexdigest()}

human=identity('kypo_data.zip','3ef1a76ef43904e0842fca98e613cca7')
agent=identity('Logs_final.zip','4f3b30538e6e4c492716f87f184dd816')
human.update(url='https://zenodo.org/records/6670113',archives=0,records=0,invalid_lines=0)
exercises=collections.Counter(); fields=collections.Counter()
with zipfile.ZipFile(DATA/'kypo_data.zip') as z:
    for n in z.namelist():
        if not n.endswith('useractions.json'):
            continue
        human['archives']+=1
        for line in z.read(n).decode('utf-8-sig').splitlines():
            if not line.strip():continue
            try:r=json.loads(line)
            except ValueError:human['invalid_lines']+=1;continue
            human['records']+=1
            exercises[n.split('/')[0]]+=1
            fields.update(r.keys())
human['records_by_exercise']=dict(exercises)
human['field_presence_counts']=dict(fields)
human['limit']='Author-described human training records; files are not automatically unique people or attack episodes. No matched tasks with the agent source established.'
agent.update(url='https://zenodo.org/records/20818246',session_files=0,parse_failures=0,sessions_with_no_parsed_commands=0,commands=0)
turn_shapes=collections.Counter()
envs=collections.Counter();models=collections.Counter();prompts=collections.Counter(); failures=[]
with zipfile.ZipFile(DATA/'Logs_final.zip') as z:
    for n in z.namelist():
        parts=n.split('/')
        if len(parts)!=6 or parts[0]!='Logs_final' or not parts[-1].endswith('.json'):
            continue
        agent['session_files']+=1
        try:
            raw=json.loads(z.read(n))
            assert isinstance(raw,list)
            turn_shapes.update(str(len(t)) if isinstance(t,list) else type(t).__name__ for t in raw[1:])
            commands=_parse_zenodo_turns(raw)
            agent['commands']+=len(commands)
            agent['sessions_with_no_parsed_commands']+=not bool(commands)
        except Exception as exc:
            agent['parse_failures']+=1
            failures.append({'path':n,'exception':type(exc).__name__})
        prompts[parts[1]]+=1;envs[parts[3]]+=1;models[parts[4]]+=1
agent.update(environments=dict(envs),models=dict(models),prompts=dict(prompts),failures=failures,turn_shapes=dict(turn_shapes),
             limit='Archive parsing is not validation of session independence, passive timing equivalence, APT labels or a matched human/agent comparison.')
result={'human':human,'agent':agent,'classifier_fit':False,
        'decision':'Real sources acquired; matched-label efficacy qualification remains open. No pooled-source accuracy is a confirmatory result.'}
(HERE/'PUBLIC_DATA_QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
