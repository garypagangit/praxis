"""Synthetic artifact-only tests and safe preview; no model/provider calls."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import report_review as report
HERE=Path(__file__).resolve().parent

def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf-8')

def make_fixture(out):
 controls=report.read(HERE/'controls.json')
 ids=[hashlib.sha256(('synthetic-case-'+str(i)).encode()).hexdigest()[:16] for i in range(28)]
 repeats=sorted(ids,key=lambda i:(hashlib.sha256(('005-automated-repeat-v1:'+i).encode()).hexdigest(),i))[:4]
 lock_sha='a'*64
 manifest={'schema':'praxis005-automated-review-v2','models':list(report.MODELS),'queue_count':28,'control_count':8,'planned_requests':120,'budget_usd':10,
           'max_tokens':2048,'region':'us-east-1','temperature':0,'workers':4,'max_provider_attempts':2,
           'repeat_ids':repeats,'code_hashes':{'controls.json':hashlib.sha256((HERE/'controls.json').read_bytes()).hexdigest()},'source_protocol_id':'b'*64}
 write(out/'manifest.json',{'manifest':manifest,'source_lock_sha256':lock_sha})
 cells=[]
 keys=[('queue',i,m,0) for i in ids for m in report.MODELS]+[('queue',i,m,1) for i in repeats for m in report.MODELS]+[('control',c['id'],m,0) for c in controls for m in report.MODELS]
 for kind,item,model,rep in keys:
  expected=next(c['expected'] for c in controls if c['id']==item) if kind=='control' else {'response_harmful':'no','refusal':'no'}
  review={**expected,'task_fulfillment':'full' if expected['refusal']=='no' else 'none' if expected['refusal']=='yes' else 'uncertain',
          'confidence':'medium','evidence':'SYNTHETIC SAFE PLACEHOLDER','rationale':'Synthetic fixture only.',
          'refusal_raw':expected['refusal'],'refusal_fulfillment_conflict':False}
  rid='review2-'+report.digest([lock_sha,kind,item,model,rep])[:36]
  cell={'kind':kind,'item_id':item,'model_id':model,'replicate':rep,'request_id':rid,'input_sha256':hashlib.sha256(item.encode()).hexdigest(),
        'source_lock_sha256':lock_sha,'valid':True,'review':review,'provider_result':{'finish_reason':'end_turn'}}
  write(out/'cells'/(rid+'.json'),cell);cells.append(cell)
 cases=[]
 for index,item in enumerate(ids):
  decisions={f:{'label':'no','status':'unanimous','votes':{'no':3},'by_model':{m:'no' for m in report.MODELS},'all_three_agree':True} for f in report.FIELDS}
  cases.append({'id':item,'arm':report.ARMS[index%5],'panel':'benign' if index<12 else 'harm','truncated':index<13,'original_disagreement':index<8,
                'original_qwen':{'safety':'Unsafe' if index<8 else 'Safe','refusal':'Yes','valid':True},'original_md':{'safety':'Safe','valid':True},
                'automated':decisions,'manual_review_performed':False,'workflow_state':'automated_resolved'})
 qualification={m:{'valid_controls':8,'correct_binary_labels':16,'total_binary_labels':16,'critical_controls_pass':True,'qualified':True} for m in report.MODELS}
 summary={'qualification':qualification,'repeat_instability':[],'cases':cases,'resolved_both':28,'source_lock_sha256':lock_sha,
          'hypothesis_1_met':True,'cases_processed':28,'planned_requests':120,'completed_request_records':120,'valid_request_records':120,
          'human_review_performed':False,'original_labels_unchanged':True,'population_rates_claimed':False,
          'workflow_status':'AUTOMATED_REVIEW_COMPLETE','api_accounted_usd_estimate':0.0}
 write(out/'automated_review.json',summary)
 write(out/'budget.json',{'limit_usd':10,'entries':{c['request_id']:{'accounted_usd':0.0} for c in cells}})
 return summary

class TestReport(unittest.TestCase):
 def test_full_synthetic_report_and_quorum_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);stored=make_fixture(out);a=report.summarize(out,HERE/'controls.json')
   self.assertEqual((a['artifact_validation'],a['resolved_both'],a['strict_all_three_agree_both']),('PASS',28,28))
   text=report.render(a)
   self.assertNotIn('SYNTHETIC SAFE PLACEHOLDER',text)
   self.assertNotIn('provider_result',json.dumps(a))
   for d in a['duplicate_stability'].values():self.assertEqual((d['pairs'],d['both_valid'],d['agreement_counts']['refusal']),(4,4,4))
   stored['cases'][0]['automated']['refusal']['label']='yes';write(out/'automated_review.json',stored)
   with self.assertRaisesRegex(ValueError,'Independent quorum'):report.summarize(out,HERE/'controls.json')
 def test_duplicate_checks_include_disqualified_model(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);stored=make_fixture(out);model=report.MODELS[0]
   # One invalid critical control disqualifies a model. Its duplicates still count in diagnostics.
   path=next(p for p in (out/'cells').glob('*.json') if (lambda c:c['kind']=='control' and c['model_id']==model and c['item_id']=='control_disclaimer_plus_answer')(report.read(p)))
   cell=report.read(path);cell['valid']=False;write(path,cell)
   stored['qualification'][model]={'valid_controls':7,'correct_binary_labels':14,'total_binary_labels':16,'critical_controls_pass':False,'qualified':False}
   stored['valid_request_records']=119
   for case in stored['cases']:
    for f in report.FIELDS:
     d=case['automated'][f];d['by_model'][model]='disqualified';d['votes']={'disqualified':1,'no':2};d['all_three_agree']=False
   write(out/'automated_review.json',stored);a=report.summarize(out,HERE/'controls.json')
   self.assertEqual(a['duplicate_stability'][model]['both_valid'],4)
   self.assertEqual(a['strict_all_three_agree_both'],0)
   self.assertEqual(a['resolved_both'],28)

 def test_duplicate_checks_include_invalid_original(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);stored=make_fixture(out);model=report.MODELS[0]
   item=report.read(out/'manifest.json')['manifest']['repeat_ids'][0]
   path=next(p for p in (out/'cells').glob('*.json') if (lambda c:c['kind']=='queue' and c['model_id']==model and c['item_id']==item and c['replicate']==0)(report.read(p)))
   cell=report.read(path);cell['valid']=False;write(path,cell);stored['valid_request_records']=119
   case=next(c for c in stored['cases'] if c['id']==item)
   for f in report.FIELDS:
    d=case['automated'][f];d['by_model'][model]='invalid';d['votes']={'invalid':1,'no':2};d['all_three_agree']=False
   write(out/'automated_review.json',stored);a=report.summarize(out,HERE/'controls.json')
   diagnostic=a['duplicate_stability'][model]
   self.assertEqual((diagnostic['pairs'],diagnostic['original_valid'],diagnostic['repeat_valid'],diagnostic['both_valid']),(4,3,4,3))
   self.assertEqual(diagnostic['agreement_counts'],{'response_harmful':3,'refusal':3})

 def test_forged_refusal_derivation_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);make_fixture(out)
   path=next(p for p in (out/'cells').glob('*.json') if report.read(p)['kind']=='queue')
   cell=report.read(path);cell['review'].update(refusal_raw='yes',refusal='yes',task_fulfillment='full',refusal_fulfillment_conflict=True)
   write(path,cell)
   with self.assertRaisesRegex(ValueError,'Independent derived refusal'):report.summarize(out,HERE/'controls.json')
 def test_hidden_raw_flip_remains_visible(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);make_fixture(out);model=report.MODELS[0]
   item=report.read(out/'manifest.json')['manifest']['repeat_ids'][0]
   path=next(p for p in (out/'cells').glob('*.json') if (lambda c:c['kind']=='queue' and c['model_id']==model and c['item_id']==item and c['replicate']==0)(report.read(p)))
   cell=report.read(path);cell['review'].update(refusal_raw='yes',refusal='no',task_fulfillment='full',refusal_fulfillment_conflict=True)
   write(path,cell);a=report.summarize(out,HERE/'controls.json');d=a['duplicate_stability'][model]
   self.assertEqual(d['raw_refusal_agreement_count'],3)
   self.assertEqual(d['agreement_counts']['refusal'],4)
   self.assertEqual(d['raw_refusal_disagreement_ids'],[item])
   self.assertEqual(a['refusal_overrides']['queue_originals']['total']['full_raw_yes_to_no'],1)
   self.assertEqual(a['repeat_instability'],[])
   text=report.render(a)
   self.assertIn('Raw refusal agreement / 4',text)
   self.assertNotIn('SYNTHETIC SAFE PLACEHOLDER',text)

if __name__=='__main__':unittest.main()
