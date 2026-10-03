"""python cli.py cases.json --bot verifier"""
import argparse,json
from pathlib import Path
from review_bot import review
p=argparse.ArgumentParser();p.add_argument('file',type=Path);p.add_argument('--bot',choices=['calculator','follower','verifier'],default='verifier');a=p.parse_args()
cases=json.loads(a.file.read_text(encoding='utf-8'))
if isinstance(cases,dict):cases=[cases]
print(json.dumps([{'case_id':c.get('case_id'),**review(c,a.bot)} for c in cases],indent=2))
