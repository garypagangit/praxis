import copy,hashlib,json,sys,time
from pathlib import Path
import review_bot
HERE=Path(__file__).resolve().parent;CASES=HERE.parent/'explanation_trials_20261003/PX102_CASES.json';KEY=Path('C:/w/explanation_trials_20261003/PX102_ANSWER_KEY.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
 if sys.argv[1]=='freeze':
  assert not (HERE/'FREEZE.json').exists()
  save(HERE/'FREEZE.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':{str(p):sha(p) for p in [HERE/'run.py',HERE/'review_bot.py',HERE/'PROTOCOL.md',CASES,KEY]}});return
 for p,h in json.loads((HERE/'FREEZE.json').read_text())['files'].items():assert sha(Path(p))==h
 assert not (HERE/'RESULTS.json').exists();cases=json.loads(CASES.read_text());responses=[]
 conditions=['scores_only','valid_explanation','wrong_count','wrong_mean','wrong_OR','missing_member']
 for c in cases:
  facts=review_bot.parse(c['explanation']);assert facts is not None
  for condition in conditions:
   x=copy.deepcopy(c)
   if condition=='scores_only':x['explanation']=None
   elif condition=='missing_member':x['member_probabilities'][0]=None
   elif condition.startswith('wrong_'):
    a=dict(facts);field=condition[6:];a[field]=(a[field]+1)%4 if field=='count' else not a[field]
    x['explanation']=f"{a['count']} of 3 members warn. Mean aggregation {'warns' if a['mean'] else 'is silent'}. OR aggregation {'warns' if a['OR'] else 'is silent'}."
   for bot in ['calculator','follower','verifier']:
    responses.append({'case_id':c['case_id'],'condition':condition,'bot':bot,**review_bot.review(x,bot)})
 # The answer key is loaded only by the scorer, after every bot response exists.
 gold={r['case_id']:r['answer'] for r in json.loads(KEY.read_text())};summary=[]
 for condition in conditions:
  for bot in ['calculator','follower','verifier']:
   rr=[r for r in responses if r['condition']==condition and r['bot']==bot];answered=[r for r in rr if r['answer'] is not None];correct=sum(r['answer']==gold[r['case_id']] for r in answered)
   summary.append({'condition':condition,'bot':bot,'assigned':len(rr),'answered':len(answered),'correct':correct,'all_case_accuracy':correct/len(rr),'answered_case_accuracy':correct/len(answered) if answered else None,'rejected':sum(r['status']=='REJECTED' for r in rr),'abstained':sum(r['status']=='ABSTAIN' for r in rr),'verified':sum(r['status']=='VERIFIED' for r in rr)})
 unique=len({json.dumps(c['member_probabilities']) for c in cases})
 save(HERE/'RESPONSES.json',responses);save(HERE/'RESULTS.json',{'cases':len(cases),'unique_score_vectors':unique,'bot_reviews':len(responses),'human_participants':0,'llm_calls':0,'summary':summary})
 print(json.dumps({'cases':len(cases),'unique_score_vectors':unique,'summary':summary},indent=2))
if __name__=='__main__':main()
