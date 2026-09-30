"""Check loaded legacy estimators against saved probabilities on a fixed sample."""
import importlib.util,json,warnings
from pathlib import Path
import joblib,numpy as np,sklearn
from common import save
HERE=Path(__file__).resolve().parent
def main():
    spec=importlib.util.spec_from_file_location('px',HERE.parent/'px081_evidence_acquisition/run.py');px=importlib.util.module_from_spec(spec);spec.loader.exec_module(px)
    d=dict(np.load(px.DEFAULT_INPUT));ix=np.flatnonzero(d['split']==2);y=d['y'][ix]
    sample=np.concatenate([np.flatnonzero(y==k)[:100] for k in range(4)]);checks=[]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for seed in px.SEEDS:
            models=joblib.load(px.DEFAULT_OUTPUT/f'seed_{seed}/models.joblib')
            for condition in ['clean','wrong_host_history']:
                saved=np.load(px.DEFAULT_OUTPUT/f'seed_{seed}/{condition}_inputs.npz')['probabilities']
                for state in range(4):
                    p=px.predict(models['classifiers'][state],px.subset_x(d,ix[sample],state,condition=='wrong_host_history'))
                    assert np.array_equal(p,saved[state,sample])
                    checks.append({'seed':seed,'condition':condition,'state':state,'exact_probability_match':True})
    save(HERE/'PREDICTION_COMPATIBILITY.json',{'passed':True,'rows_per_check':len(sample),'sample_rule':'first up to 100 test rows in each true class; compatibility check only, not performance selection','sklearn_loaded_version':sklearn.__version__,'serialized_encoder_version':'1.7.2','checks':checks,'limit':'This verifies sampled probabilities, not every prediction. All prior calibration hard decisions and original test replay paths were separately matched.'})
    print('Exact sampled probability matches:',len(checks),'rows each:',len(sample))
if __name__=='__main__':main()
