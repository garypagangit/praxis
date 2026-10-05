"""Preserve and inspect the supplied draft; never execute logged shell commands."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
SOURCE=Path('C:/w/aivh_review_20261005/px-aivh')
files={}
for p in SOURCE.rglob('*'):
    if not p.is_file() or '__pycache__' in p.parts:
        continue
    rel=p.relative_to(SOURCE)
    dest=HERE/'supplied'/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(p,dest)
    files[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps({
    'source':'C:/Users/garyp/Downloads/px-aivh.zip',
    'sha256':hashlib.sha256(Path('C:/Users/garyp/Downloads/px-aivh.zip').read_bytes()).hexdigest(),
    'status':'Supplied draft preserved unchanged. Its novelty/certification claims and reused PX-090 ID are not endorsed.',
    'files':files},indent=2)+'\n')
sys.path.insert(0,str(HERE/'supplied'))
from aivh.gate import ConformalGate
from aivh.ingest import _commands_from_keystream
from aivh import synth,features
tests=subprocess.run([sys.executable,str(HERE/'supplied/scripts/test_pipeline.py')],capture_output=True,text=True)
assert tests.returncode==0,tests.stderr
(HERE/'SUPPLIED_TESTS.txt').write_text(tests.stdout)
sessions=synth.generate()
result={
    'experiment':'PX-117','stage':'PACKAGE_QUALIFICATION_ONLY',
    'supplied_tests':{'exit':tests.returncode,'count':5},
    'small_calibration_probe':{'n':1,'alpha':0.05,'scores':[0.1],
        'observed_threshold':ConformalGate._quantile(np.array([0.1]),0.05),
        'required_valid_threshold':'1.0 (bounded nonconformity) or infinity because rank exceeds n',
        'status':'FAIL_FINITE_SAMPLE_EDGE_CASE'},
    'arrow_history_probe':{'input':'ls, Enter, Up-arrow, Enter',
        'observed_commands':[c.text for c in _commands_from_keystream([(0,'ls\r'),(1,'\x1b[A\r')])],
        'expected':'ls then ls in an ordinary shell with matching history',
        'status':'FAIL_COMMAND_RECONSTRUCTION'},
    'synthetic_gap_min_by_class':{label:sorted({features.extract(s)['T_gap_min'] for s in sessions if s.label==label})
                                for label in ['agent','human']},
    'scientific_efficacy':'NOT TESTED: no independently labeled matched human cohort',
    'aws_spend_usd':0,
}
(HERE/'QUALIFICATION_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
smoke=Path('C:/w/aivh_review_20261005/reproduced_gbm/report_gbm.json')
assert smoke.exists()
shutil.copyfile(smoke,HERE/'REPRODUCED_SYNTHETIC_GBM.json')
shutil.copyfile('C:/w/aivh_review_20261005/smoke.log',HERE/'SYNTHETIC_RUN.txt')
print(json.dumps(result,indent=2))
