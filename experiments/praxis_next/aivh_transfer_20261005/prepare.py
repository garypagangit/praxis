"""Qualify external records and freeze the AWS bundle before model fitting."""
import collections,hashlib,json,re,shutil,sys,tarfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=HERE.parent/'aivh_gambit_20261005';PRIVATE=Path('C:/w/px118_20261005')
sys.path.insert(0,str(OLD));from common import command

def main():
 zpath=PRIVATE/'rouxii-dataset.zip'
 assert hashlib.md5(zpath.read_bytes()).hexdigest()=='ca55baa9bc97ca121b74e450f746d6cf'
 stats=collections.defaultdict(collections.Counter);rows=[];audit=[]
 with zipfile.ZipFile(zpath) as z:
  for n in sorted(x for x in z.namelist() if x.endswith('/report.json')):
   meta=json.loads(z.read(n));framework=meta.get('attacker',{}).get('name','rouxii')
   if '/HackingBuddy/' in n:framework='hackingbuddy'
   elif '/PentestGPT/' in n:framework='pentestgpt'
   else:framework='rouxii'
   stats[framework]['runs']+=1
   session=n.rsplit('/',1)[0]+'/session.md'
   if session not in z.namelist():stats[framework]['missing_session']+=1;continue
   if framework=='rouxii':stats[framework]['fixed_operator_representation_excluded']+=1;continue
   txt=z.read(session).decode('utf-8',errors='replace').replace('\r\n','\n')
   blocks=re.split(r'^## \[(user|assistant)\]\s*$',txt,flags=re.M)
   raw=[]
   for role,body in zip(blocks[1::2],blocks[2::2]):
    if framework=='hackingbuddy' and role=='assistant':
     raw+=re.findall(r'^exec_command (.+)$',body,flags=re.M)
    if framework=='pentestgpt' and role=='user':
     raw+=re.findall(r'^execute_command: (.+)$',body,flags=re.M)
   cs=[c for s in raw if (c:=command(s)) is not None]
   stats[framework]['explicit_commands']+=len(raw);stats[framework]['eligible_commands']+=len(cs)
   audit.append({'run_hash':hashlib.sha256(n.encode()).hexdigest(),'framework':framework,'explicit':len(raw),'eligible':len(cs)})
   if len(cs)<10:stats[framework]['fewer_than_ten']+=1;continue
   fp=hashlib.sha256('\n'.join(cs[:10]).encode()).hexdigest()
   rid='rouxii:'+hashlib.sha256(n.encode()).hexdigest()
   rows.append({'id':rid,'commands':cs[:10],'label':1,'group':rid,'family':meta.get('model'),'fingerprint':fp,'source':'Rouxii'})
   stats[framework]['eligible_runs']+=1
 unique={r['fingerprint']:r for r in rows};rows=list(unique.values())
 (PRIVATE/'external_rouxii.json').write_text(json.dumps(rows))
 qual={'archive_md5':hashlib.md5(zpath.read_bytes()).hexdigest(),'archive_sha256':hashlib.sha256(zpath.read_bytes()).hexdigest(),'frameworks':dict(stats),'eligible_unique_windows':len(rows),'run_counts':audit,'status':'ELIGIBLE' if rows else 'NOT_ESTIMABLE_NO_ELIGIBLE_TEN_COMMAND_WINDOWS'}
 (HERE/'ROUXII_QUALIFICATION.json').write_text(json.dumps(qual,indent=2))
 source=Path('C:/w/px117c_aws_20261005')
 shutil.copyfile(source/'records.json',PRIVATE/'records.json')
 shutil.copyfile(source/'collected/outputs/lexical_participant_holdout_predictions.json',PRIVATE/'base_predictions.json')
 shutil.copyfile(source/'collected/outputs/split_manifest.json',PRIVATE/'split_manifest.json')
 d=json.loads((PRIVATE/'records.json').read_text());used=set();ext=[]
 for r in d['external']:
  if r['fingerprint'] not in used:used.add(r['fingerprint']);ext.append(r)
 (PRIVATE/'external_kypo.json').write_text(json.dumps(ext))
 settings=json.loads((source/'settings.json').read_text());settings['prefix']='praxis-next/aivh/20261005-transfer1/'
 (PRIVATE/'settings.json').write_text(json.dumps(settings,indent=2))
 run=(OLD/'cloud_run.py').read_text().replace('C:\\w\\px117c_aws_20261005','C:/w/px118_20261005').replace('praxis-gambit-','praxis-transfer-')
 (HERE/'cloud_run.py').write_text(run)
 shutil.copyfile(OLD/'recover_ssh.py',HERE/'recover_ssh.py');shutil.copyfile(OLD/'cloud.sh',HERE/'cloud.sh')
 with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz') as a:
  for name in ['records.json','base_predictions.json','split_manifest.json','external_kypo.json','external_rouxii.json']:a.add(PRIVATE/name,arcname=name)
  a.add(HERE/'train.py',arcname='train.py');a.add(OLD/'train.py',arcname='prior.py');a.add(OLD/'common.py',arcname='common.py')
 files=[HERE/n for n in ['train.py','prepare.py','PROTOCOL.txt','cloud_run.py','recover_ssh.py','cloud.sh','ROUXII_QUALIFICATION.json']]+[OLD/'train.py',OLD/'common.py']
 freeze={'bundle_sha256':hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest(),'runtime_files':{f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'stage':'EXPOSED_DATA_DEVELOPMENT_AND_EXTERNAL_QUALIFICATION'}
 (HERE/'CLOUD_FREEZE.json').write_text(json.dumps(freeze,indent=2))
 print(json.dumps({'qualification':dict(stats),'eligible_unique':len(rows),'bundle_bytes':(PRIVATE/'bundle.tar.gz').stat().st_size}))

if __name__=='__main__':main()
