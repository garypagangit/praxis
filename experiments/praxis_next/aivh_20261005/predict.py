"""Predict from a JSON list of recorded commands; never execute commands."""
import argparse,json,sys
from pathlib import Path
import joblib,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'supplied'))
from aivh.ingest import Command,Session
from aivh.features import extract
from build_development_data import normalize

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,required=True,help='Trusted local PX-117 joblib artifact only')
    parser.add_argument('--commands',type=Path,required=True,help='JSON array of recorded command strings')
    args=parser.parse_args()
    commands=json.loads(args.commands.read_text(encoding='utf-8'))
    if not isinstance(commands,list) or not commands or not all(isinstance(c,str) and c.strip() for c in commands):
        raise ValueError('Expected a nonempty JSON array of nonempty recorded command strings')
    commands=[normalize(c) for c in commands[:10]]
    artifact=joblib.load(args.model)
    if artifact['kind']=='ngrams': X=['\n'.join(commands)]
    elif artifact['kind']=='length': X=np.array([[len(commands)]])
    else:
        f=extract(Session('input','unknown','input',[Command(c,None) for c in commands]))
        X=np.array([[f[k] for k in artifact['feature_names']]])
    m=artifact['model'];score=float(m.predict_proba(X)[0,list(m.classes_).index(1)])
    print(json.dumps({'prediction':'autonomous_ai_like' if score>=artifact['threshold'] else 'human_like',
        'ai_score':score,'threshold':artifact['threshold'],'commands_observed':len(commands),
        'scope':artifact['scope'],'validated_apt_detector':False},indent=2))

if __name__=='__main__':main()
