"""Score recorded commands; never execute them."""
import argparse,json
from pathlib import Path
import joblib
from common import command,inputs
p=argparse.ArgumentParser()
p.add_argument('--model',type=Path,required=True,help='Trusted PX-117C model artifact')
p.add_argument('--commands',type=Path,required=True,help='JSON list of recorded command strings')
args=p.parse_args();raw=json.loads(args.commands.read_text(encoding='utf-8'))
if not isinstance(raw,list) or not all(isinstance(c,str) for c in raw):raise ValueError('Expected a JSON list of command strings')
cs=[v for c in raw if (v:=command(c)) is not None]
if len(cs)<10:raise ValueError('At least ten qualifying discovery-like commands required')
a=joblib.load(args.model);score=float(a['model'].predict_proba(inputs([{'commands':cs[:10]}],a['kind']))[0,1])
print(json.dumps({'prediction':'autonomous_ai_like' if score>=a['threshold'] else 'human_like',
                  'ai_score':score,'threshold':a['threshold'],'eligible_commands_used':10,
                  'scope':a['scope'],'validated_apt_attribution':False},indent=2))
