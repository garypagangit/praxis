"""Publish all conditions of the score-policy transfer experiment."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import numpy as np
from .run import ARMS,DATASETS,write,sha

def report(run,output):
    output.mkdir(parents=True,exist_ok=True);rows=json.loads((run/'METRICS.json').read_text());complete=json.loads((run/'COMPLETE.json').read_text())
    flat=[{k:v for k,v in r.items() if k not in ['confusion','by_run']} for r in rows]
    fields=list(dict.fromkeys(k for r in flat for k in r))
    with (output/'METRICS.csv').open('w',encoding='utf-8',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(flat)
    means=[]
    for dataset in DATASETS:
        for condition in dict.fromkeys(r['condition'] for r in rows if r['dataset']==dataset):
            for arm in ARMS:
                rr=[r for r in rows if r['dataset']==dataset and r['condition']==condition and r['arm']==arm]
                means.append({'dataset':dataset,'condition':condition,'arm':arm,'perturbation_views':len(rr),
                    **{k:float(np.mean([r[k] for r in rr])) for k in ['f1','recall','precision','ap','roc_auc','other_label_flags','other_label_flag_rate','target_cost_error']}})
    write(output/'MEANS.json',means)
    train=np.load(run/'TRAIN.npz',allow_pickle=False)
    diagnostics={'status':'POST_RESULT_EXPLANATORY_DIAGNOSTIC_NO_REFITTING','nonzero_calibration_error_comparisons':int(np.count_nonzero(train['ordinary_target'])),
        'calibration_rows':len(train['y']),'views':[]}
    for dataset in DATASETS:
        for gate,reference in [('ordinary_gate','current'),('target_cost_gate','context')]:
            changes=[];equal_scores=0
            for path in sorted((run/dataset).glob('*.npz')):
                z=np.load(path,allow_pickle=False);changes.append(int(np.sum((z[gate]>.5)!=(z[reference]>.5))));equal_scores+=int(np.array_equal(z[gate],z[reference]))
            diagnostics['views'].append({'dataset':dataset,'gate':gate,'reference':reference,'views':len(changes),
                'identical_hard_decision_views':sum(x==0 for x in changes),'maximum_changed_decisions_in_one_view':max(changes),'identical_score_views':equal_scores})
    write(output/'DIAGNOSTICS.json',diagnostics)
    for name in ['STARTED.json','COMPLETE.json','METRICS.json','ORIGINAL_THRESHOLD_CONTROLS.json','AUDIT.json']:
        if (run/name).exists():shutil.copyfile(run/name,output/name)
    lines=['# PX-083 — Casino-trained context-selection policy on Casino and CAM-LDS','',
        '**Secondary development replication on already exposed data.** T1105 is Ingress Tool Transfer; this experiment does not detect lateral movement or forecast exfiltration. Other-label flags are not benign false alarms.','',
        f"Two Ridge selectors were fitted on 1,494 Casino clean-calibration scores, including 87 T1105 positives, then applied unchanged to both datasets. No native classifiers were retrained. Saved prediction tables: {complete['prediction_tables']}; runtime {complete['runtime_seconds']:.2f} CPU seconds.",'',
        'The ordinary selector learns the difference in binary errors at score >0.5. The target-cost selector multiplies errors on T1105 training examples by four. This is a declared design choice. Both receive only native scores and observable visibility. Every arm uses the same strict 0.5 threshold. Original calibrated native-control results are retained separately and were not used to fit the selectors.','',
        '## Complete comparisons','',
        'Random-loss rows average three perturbations of the same events. Other rows contain one deterministic view. These are not independent fitting seeds or campaigns. Higher F1/recall is better; fewer other-label flags and lower target-cost error are better.']
    for dataset in DATASETS:
        lines+=['',f'### {dataset}','', '| Condition | Arm | F1 | Recall | Other-label flags | Cost error |','|---|---|---:|---:|---:|---:|']
        for r in [r for r in means if r['dataset']==dataset]:
            lines.append(f"| {r['condition']} | {r['arm']} | {r['f1']:.4f} | {r['recall']:.2%} | {r['other_label_flags']:.2f} | {r['target_cost_error']:.6f} |")
    lines+=['','## Why matching metrics do not show a new adaptive advantage','',
        f"A post-result diagnostic found only {diagnostics['nonzero_calibration_error_comparisons']} nonzero expert-error comparisons among {diagnostics['calibration_rows']} Casino calibration rows. The selectors change score sources, but different probability vectors can still lead to identical 0.5 decisions. No model was refitted for this diagnostic.",'',
        '| Dataset | Gate | Reference | Identical hard-decision views | Identical score views |','|---|---|---|---:|---:|']
    for r in diagnostics['views']:
        lines.append(f"| {r['dataset']} | {r['gate']} | {r['reference']} | {r['identical_hard_decision_views']}/{r['views']} | {r['identical_score_views']}/{r['views']} |")
    lines+=['','## Original native thresholds: clean-condition supplement','',
        'These thresholds were chosen in the earlier experiments. They are displayed to expose the operating-point limitation; they were not used to select or retrain the new gates.','',
        '| Dataset | Native arm | Original threshold | Recall | F1 | Other-label flags |','|---|---|---:|---:|---:|---:|']
    for r in json.loads((run/'ORIGINAL_THRESHOLD_CONTROLS.json').read_text()):
        if r['condition']=='clean':lines.append(f"| {r['dataset']} | {r['arm']} | {r['threshold']:.4f} | {r['recall']:.2%} | {r['f1']:.4f} | {r['other_label_flags']} |")
    lines+=['','## Limits','',
        '- Casino evaluates 920 targets/17 T1105 positives across18 runs. CAM-LDS evaluates4,209 targets/100 positives across18 runs from one held-out family. Repeated family recipes and author annotation uncertainty remain.',
        '- Casino target units represent annotation-onset proxies; CAM-LDS target units represent labeled time intervals. No pooled accuracy or claim of identical operational decisions is appropriate.',
        '- The two score policies transfer unchanged; the underlying classifiers were trained separately on their native datasets. This is policy transfer only.',
        '- CAM-LDS calibration (68 rows/8 positives from one run) is not used to train or tune these policies. Its old thresholds appear only in the descriptive native-control supplement.',
        '- The offline annotated target roster is not a production alert trigger. Invisible targets count as misses and produce no alarm.',
        '- Missing/delayed-record interventions are synthetic. Waiting out the complete injected delay restores clean data by construction, not by information recovery.',
        '- Existing test outcomes were previously examined. Computation and source checks do not turn this into independent confirmation or establish algorithm novelty.',
        '', '[Frozen protocol](../PROTOCOL.md) · [Qualified sources](../INPUTS.json) · [All metrics](METRICS.json) · [Audit](AUDIT.json) · [Original thresholds](ORIGINAL_THRESHOLD_CONTROLS.json)']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(output/'ARTIFACTS.json',{'files':{p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='ARTIFACTS.json'}})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();report(a.run,a.output)
