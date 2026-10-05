"""Describe frozen model features; never fit a model or execute log commands."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from common import inputs

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--records', required=True)
    p.add_argument('--models', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    data = json.loads(Path(a.records).read_text())
    lookup = {r['id']: r for r in data['rows'] + data['external']}
    result = {'scope': 'Post-hoc descriptive associations, not causal AI markers; no fitting or threshold changes.', 'models': {}}
    for kind in ['lexical', 'verbs']:
        base = Path(a.models)
        model = joblib.load(base / (kind + '.joblib'))['model']
        pred = json.loads((base / (kind + '_participant_holdout_predictions.json')).read_text())
        rows = [lookup[r['id']] for r in pred['test']]
        x = model[0].transform(inputs(rows, kind))
        names = model[0].get_feature_names_out()
        co = model[-1].coef_[0]
        labels = np.array([r['label'] for r in rows])
        findings = []
        for i in list(np.argsort(co)[-10:][::-1]) + list(np.argsort(co)[:5]):
            present = x[:, i].toarray().ravel() > 0
            findings.append({'feature': str(names[i]), 'coefficient': float(co[i]),
                             'ai_windows_present': int(sum(present & (labels == 1))),
                             'human_windows_present': int(sum(present & (labels == 0)))})
        result['models'][kind] = {'ai_windows': int(sum(labels == 1)),
                                  'human_windows': int(sum(labels == 0)), 'features': findings}
    Path(a.output).write_text(json.dumps(result, indent=2) + '\n')

if __name__ == '__main__':
    main()
