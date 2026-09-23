"""Compatibility check on the already published PX-082 design; zero new fits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
from .temporal_plan import plan

HERE=Path(__file__).resolve().parent
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
DESIGN=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px082/run_v1/DESIGN.npz')
EXPECTED='b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def run():
    output=HERE/'PORT_VERIFICATION.json'
    if output.exists():raise ValueError('Do not overwrite a verification receipt')
    if sha(DATA)!=EXPECTED:raise ValueError('Prior input changed')
    with np.load(DATA,allow_pickle=False) as z:
        # These are existing PX-082 source-qualified split/capture fields.
        # The old four-class mapping is reproduced for compatibility only;
        # this does not assert that the prior mapping is a native taxonomy.
        d={k:z[k] for k in ['current','y','capture','split','group_sha256','start','end']}
    actual=plan(current=d['current'],labels=d['y'],
        class_names=['Benign','OtherAttackStage','LateralMovement','DataExfiltration'],
        benign_index=0,row_ids=np.asarray([f'px082-row-{i:09}' for i in range(len(d['y']))]),
        event_hashes=d['group_sha256'],groups=d['capture'],starts=d['start'],
        ends=d['end'],splits=d['split'],clock_validated=True,groups_validated=True)
    with np.load(DESIGN,allow_pickle=False) as old:
        checks={name:bool(np.array_equal(actual[new],old[name])) for name,new in
            [('anchor','anchor'),('past_pool','past_pool'),('mixed_pool','mixed_pool'),('counts','matched_counts')]}
    receipt={'utc':datetime.now(timezone.utc).isoformat(),'purpose':'Existing PX-082 design compatibility, not new replication',
        'new_model_fits':0,'aws_used':False,'data_sha256':EXPECTED,'design_sha256':sha(DESIGN),
        'code_sha256':{p.name:sha(p) for p in [HERE/'temporal_plan.py',Path(__file__)]},
        'arrays_identical_to_published_design':checks,'all_checks_pass':all(checks.values()),
        'plan_summary':actual['summary'],
        'taxonomy_scope':'Reproduces prior four-class grouping only; future D1 sources retain native labels.'}
    output.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    if not receipt['all_checks_pass']:raise RuntimeError('Compatibility failed; receipt retained')


if __name__=='__main__':run()
