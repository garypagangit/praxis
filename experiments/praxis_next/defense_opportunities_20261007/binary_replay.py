import argparse,json,pathlib,sys
from threadpoolctl import threadpool_limits
from screen import HERE,OLD,save,sha
import binary as b
def run(source):
 old=HERE.parent/'aivh_lyptus_20261007/results/PX121_records.json';rows=[r for r in json.loads(old.read_text()) if r['label']]
 for r in json.loads(source.read_text()):
  if r['benchmark']!='intercode-ctf':continue
  rows.append({'id':r['id'],'task':r['task'],'group':r['expert'],'family':'human','label':0,'shell_commands':[x['command'] for x in r['commands']]})
 dest=HERE/'evidence/REPLAY_INPUT.json';save(dest,rows)
 save(HERE/'evidence/REPLAY_SOURCE.json',{'replay_sha256':sha(source),'ai_sha256':sha(old),'replay_code_commit':'1652f92c94c833979039b68213971a307eb6f8d1','binary_code_sha256':sha(OLD/'binary.py'),'wrapper_sha256':sha(pathlib.Path(__file__)),'license':'Derived from Lyptus public CC-BY4.0 data; see SOURCES.md'})
 b.HERE=HERE;b.run(dest)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--replay',type=pathlib.Path,required=True);a=p.parse_args()
 with threadpool_limits(limits=1):run(a.replay)
