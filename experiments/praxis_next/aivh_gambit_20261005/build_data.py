import collections,hashlib,json,sys,zipfile
from pathlib import Path
from common import command
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'aivh_20261005'
sys.path.insert(0,str(OLD/'supplied'))
from aivh.ingest import model_family
PRIVATE=Path('C:/w/px117c_aws_20261005');PRIVATE.mkdir(exist_ok=True)
DATA=Path('C:/w/aivh_review_20261005/public_data')
audit=collections.Counter();rows=[];external=[]
def record(source,key,group,commands,label,family='human'):
    text='\n'.join(commands)
    return {'id':hashlib.sha256((source+key).encode()).hexdigest()[:24],
            'source':source,'group':group,'commands':commands,'label':label,
            'family':family,'fingerprint':hashlib.sha256(text.encode()).hexdigest()}
humans=json.loads(Path('C:/w/aivh_review_20261005/gambit/commands_structurally_eligible.json').read_text(encoding='utf-8'))
byday=collections.defaultdict(list)
for r in humans:
    c=command(r['command']);audit['human_commands_seen']+=1
    if c:
        audit['human_commands_eligible']+=1
        byday[(r['participant'],r['timestamp'][:10])].append((r['timestamp'],c))
limits=collections.Counter()
for (participant,day),events in sorted(byday.items(),key=lambda kv:(kv[0][1],kv[0][0])):
    group='P'+participant.split('P')[1]
    cmds=[c for _,c in sorted(events,key=lambda t:t[0])]
    for start in range(0,len(cmds)-9,10):
        if limits[group]>=20:audit['human_windows_capped']+=1;continue
        rows.append(record('GAMBiT',f'{participant}/{day}/{start}',group,cmds[start:start+10],0));limits[group]+=1
with zipfile.ZipFile(DATA/'Logs_final.zip') as z:
    for name in sorted(z.namelist()):
        parts=name.split('/')
        if len(parts)!=6 or parts[0]!='Logs_final' or not name.endswith('.json'):continue
        audit['agent_sessions_seen']+=1;raw=json.loads(z.read(name));cs=[];ambiguous=False
        for turn in raw[1:]:
            if not isinstance(turn,list) or len(turn)!=3 or not isinstance(turn[2],list) or len(turn[2])!=2 or not isinstance(turn[2][1],str):ambiguous=True;break
            c=command(turn[2][1])
            if c:cs.append(c)
        if ambiguous:audit['agent_sessions_missing_explicit_command']+=1;continue
        if len(cs)<10:audit['agent_sessions_below_ten']+=1;continue
        r=record('Honey',name,name,cs[:10],1,model_family(parts[4]));rows.append(r)
with zipfile.ZipFile(DATA/'kypo_data.zip') as z:
    for name in sorted(z.namelist()):
        if not name.endswith('useractions.json'):continue
        cs=[]
        for line in z.read(name).decode('utf-8-sig').splitlines():
            if not line.strip():continue
            r=json.loads(line)
            if r.get('cmd_type')=='bash-command':
                c=command(r.get('cmd'))
                if c:cs.append(c)
        if len(cs)>=10:external.append(record('KYPO',name,name,cs[:10],0))
bundle={'rows':rows,'external':external}
(PRIVATE/'records.json').write_text(json.dumps(bundle),encoding='utf-8')
report={'experiment':'PX-117C','audit':dict(audit),'rows':len(rows),
        'classes':dict(collections.Counter(r['source'] for r in rows)),
        'human_groups':len(limits),'agent_families':dict(collections.Counter(r['family'] for r in rows if r['label']==1)),
        'external_kypo_records':len(external),'human_technique_labels_used_as_predictors':False,
        'records_sha256':hashlib.sha256((PRIVATE/'records.json').read_bytes()).hexdigest(),
        'strict_unassisted_human_labels_verified':False}
(HERE/'DATA.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
