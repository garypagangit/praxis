"""Portable launcher: copy qualified inputs, then run frozen analysis code."""
import argparse,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--include-px118',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent;a.data=a.data.resolve();a.output=a.output.resolve()
if a.output.exists():raise SystemExit('Choose a new output folder to preserve prior results.')
a.output.mkdir(parents=True)
if a.include_px118:
    work=a.output/'px118';work.mkdir()
    for name in ['records.json','base_predictions.json','split_manifest.json','external_kypo.json','external_rouxii.json']:shutil.copy2(a.data/name,work/name)
    for name in ['train.py','prior.py','common.py']:shutil.copy2(root/'px118'/name,work/name)
    subprocess.run([sys.executable,'train.py'],cwd=work,check=True)
subprocess.run([sys.executable,str(root/'px119/run.py'),'--data',str(a.data),'--masked-model',str(root/'models/masked.joblib'),'--output',str(a.output/'px119')],check=True)
