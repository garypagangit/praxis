"""Inert engineering fixtures only: no human observations, models or shell calls."""
import copy, hashlib, json, pathlib
from boundary import project, design_gate
from test_boundary import fixture, provenance

root=pathlib.Path(__file__).resolve().parent/'results';root.mkdir(exist_ok=True)
views={v:project(fixture(),v,10) for v in ('commands','results','timing')}
twins=[]
for origin in 'HSAM':
    s=fixture();s['origin']=origin
    twins.append(hashlib.sha256(json.dumps(project(s,'results',10),sort_keys=True).encode()).hexdigest())
records=[provenance(o) for o in 'HSAM']
for r in records:r['synthetic_fixture']=True
result={'fixture_only':True,'views':views,'origin_metadata_variants':4,
  'identical_observation_hashes':len(set(twins))==1,
  'interpretation':'Four constructed label variants with identical defender observations cannot be distinguished from this view. This is a counterexample, not a measured natural collision rate.',
  'future_output_hidden':project(fixture(),'results',6)['events'][-1]['stdout'] is None,
  'fixture_training_gate':design_gate(records),'new_genuine_sessions':0,'detector_accuracy':None}
(root/'BOUNDARY_DEMO.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result,indent=2))
