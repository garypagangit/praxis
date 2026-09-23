"""Export every PX-080 comparison without selecting an outcome."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import numpy as np
from .run import CONDITIONS,ARMS,SEEDS,write,sha

def report(run,output):
    output.mkdir(parents=True,exist_ok=True)
    rows=json.loads((run/'METRICS.json').read_text());complete=json.loads((run/'COMPLETE.json').read_text())
    flat=[]
    for r in rows:
        flat.append({'seed':r['seed'],'condition':r['condition'],'arm':r['arm'],'macro_f1':r['macro_f1'],'stage_weighted_error':r['stage_weighted_error'],
            'movement_recall':r['classes']['LateralMovement']['recall'],'movement_f1':r['classes']['LateralMovement']['f1'],
            'movement_any_attack_recall':r['movement_any_attack_recall'],'exfil_recall':r['classes']['DataExfiltration']['recall'],
            'exfil_f1':r['classes']['DataExfiltration']['f1'],'exfil_ap':r['classes']['DataExfiltration']['ap'],
            'normal_false_attacks':r['normal_false_attacks'],'context_selected_fraction':r.get('context_selected_fraction'),
            'context_harm_count':r.get('selected_context_harm_count'),'context_help_count':r.get('selected_context_help_count')})
    with (output/'METRICS.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    means=[]
    for c in CONDITIONS:
        for arm in ARMS:
            selected=[r for r in flat if r['condition']==c and r['arm']==arm]
            means.append({'condition':c,'arm':arm,**{k:float(np.mean([r[k] for r in selected])) if selected[0][k] is not None else None for k in flat[0] if k not in ['seed','condition','arm']}})
    write(output/'MEANS.json',means)
    for n in ['METRICS.json','COMPLETE.json','STARTED.json','FOLDS.json']:
        shutil.copyfile(run/n,output/n)
    if (run/'AUDIT.json').exists():shutil.copyfile(run/'AUDIT.json',output/'AUDIT.json')
    lines=['# PX-080: Does learning context harm preserve attack-stage recognition?','',
        '**Completed development pilot.** Every fixed comparison is shown, including failures. This is a previously exposed, single-campaign UNRAVELED evaluation, not independent confirmation. No exfiltration forecast was performed.','',
        f"The run fitted {complete['fits']} models and saved {complete['prediction_tables']} arm/condition/seed probability tables. Evaluation counts (benign, other attack, movement, exfiltration): {complete['test_counts']}. CPU experiment runtime: {complete['elapsed_seconds']:.1f} seconds. Three seeds reuse the same events.",'',
        '## What changed','',
        'The current expert and context expert share current flow summaries and coarse roles. The proposed selector learns whether using context increases stage errors, giving movement/exfiltration errors four times the training cost. An ordinary selector learns unweighted error differences on exactly the same forward-held-out predictions. Costs are design choices, not standards or safety guarantees. All selectors use observable model scores and evidence age/availability at deployment.','',
        'History is prior completed-flow activity. The five-minute condition is a simulated stale snapshot; missing and wrong-host conditions are simulated interventions. Current decisions still use completed-flow measurements and are not early warnings.','',
        '## All comparisons','',
        'Values are means across three fits. Counts may be fractional because these are means. Stage-weighted error is lower-is-better; the other detection metrics are higher-is-better. Interpret false-alarm and movement costs alongside any aggregate improvement.']
    for c in CONDITIONS:
        lines+=['',f'### {c}','', '| Arm | Macro F1 | Movement recall | Movement F1 | Exfil recall | Exfil F1 | Normal false alarms | Weighted error |',
                '|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in [r for r in means if r['condition']==c]:
            lines.append(f"| {r['arm']} | {r['macro_f1']:.4f} | {r['movement_recall']:.2%} | {r['movement_f1']:.4f} | {r['exfil_recall']:.2%} | {r['exfil_f1']:.4f} | {r['normal_false_attacks']:.2f} | {r['stage_weighted_error']:.6f} |")
    lines+=['','## Selector decisions','','These are counts of selected context that changes an otherwise correct decision into an error (harm), or corrects a current-only error (help). They are descriptive test outcomes, never inputs to the selector.','',
        '| Condition | Selector | Context used | Harm count | Help count |','|---|---|---:|---:|---:|']
    for r in means:
        if r['context_selected_fraction'] is not None:lines.append(f"| {r['condition']} | {r['arm']} | {r['context_selected_fraction']:.2%} | {r['context_harm_count']:.2f} | {r['context_help_count']:.2f} |")
    lines+=['','## Limits and next scientific decision','',
        '- Only 35 evaluation movement rows, representing the author\'s Remote System Discovery progress annotation on one pair of hosts; 27 movement fitting rows and no movement calibration rows. These are not 35 independently verified intrusions.',
        '- Forward selectors learn from only four development captures; the same dataset was examined in earlier work. Chronology and held-out predictions prevent direct in-fit leakage but do not make this an untouched confirmatory experiment.',
        '- Coarse role shift, capture-level results and all per-class AP/ROC metrics are retained in METRICS.json. Seeds measure fitting variability, not independent-campaign uncertainty.',
        '- No arbitrary pass threshold and no tuned test operating point. A positive aggregate metric is insufficient if dangerous-stage recognition worsens or benefits do not exceed ordinary gating/dropout.',
        '- A strong next claim requires independent executions with verified event outcomes and matched benign controls. Novelty must be assessed against existing gating, temporal fusion and context-ablation work.',
        '', '## Reproducibility','', '[Frozen protocol](../PROTOCOL.md) · [Source binding](../FREEZE.json) · [All metrics](METRICS.json) · [Summary CSV](METRICS.csv) · [Audit](AUDIT.json)',
        '', 'Private row-linked probabilities, forward-fold targets, source identities and saved fitted models are retained under the private run directory. Public receipts bind input and scientific source hashes.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(output/'ARTIFACTS.json',{'private_run':str(run),'files':{p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='ARTIFACTS.json'}})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();report(a.run,a.output)
