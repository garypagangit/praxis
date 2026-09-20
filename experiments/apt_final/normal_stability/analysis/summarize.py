"""Descriptive summaries of the fixed family; never selects or refits an arm."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np


def spread(values):
    return {'mean':float(np.mean(values)), 'minimum':float(min(values)), 'maximum':float(max(values))}


def summarize(result):
    normal=[r for r in result['normal_records'] if r['duplicate_of_encoder_seed'] is None]
    attack=[r for r in result['attack_records'] if r['duplicate_of_encoder_seed'] is None]
    fields=('dataset','strategy','representation','condition')
    keys=sorted({tuple(r[f] for f in fields) for r in attack})
    rows=[]
    for key in keys:
        selected=[r for r in attack if tuple(r[f] for f in fields)==key]
        held=[r for r in normal if tuple(r[f] for f in fields)==key]
        row=dict(zip(fields,key))
        row.update(unique_attack_cases=len(selected),unique_normal_cases=len(held))
        for metric in ('recall','precision','f1','false_positive_rate','average_precision'):
            row[metric]=spread([r['metrics'][metric] for r in selected])
        row['normal_false_positive_rate']=spread([r['metrics']['false_positive_rate'] for r in held])
        row['attack_cases_passing_readiness']=sum(r['metrics']['recall']>=.5 and r['metrics']['false_positive_rate']<=.02 for r in selected)
        row['normal_cases_passing_stability']=sum(r['metrics']['false_positive_rate']<=.02 for r in held)
        rows.append(row)
    return {'scope':'DESCRIPTIVE_FIXED_DEVELOPMENT_FAMILY','repeats_are_independent_campaigns':False,
            'duplicate_local_copies_excluded':True,'decision':result['decision'],'rows':rows}


def markdown(summary):
    lines=['# Full descriptive results','','Means summarize overlapping development repeats; they are not independent campaign estimates.',
           'Local-feature copies across encoder seeds are excluded. FPR means the fraction of normal or benchmark-negative entities flagged.',
           'Conditions: clean or 50% of retained relationships removed. All rates below are percentages.','',
           '| Dataset | Strategy | Representation | Condition | Unique cases | Recall mean (min) | Test FPR mean (max) | F1 mean | Normal FPR mean (max) |',
           '|---|---|---|---|---:|---:|---:|---:|---:|']
    for r in summary['rows']:
        metric=lambda k:f"{r[k]['mean']*100:.2f} ({r[k]['maximum']*100:.2f})"
        recall=f"{r['recall']['mean']*100:.2f} ({r['recall']['minimum']*100:.2f})"
        lines.append(f"| {r['dataset']} | {r['strategy']} | {r['representation']} | {r['condition']} | {r['unique_attack_cases']} | {recall} | {metric('false_positive_rate')} | {r['f1']['mean']*100:.2f} | {metric('normal_false_positive_rate')} |")
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    summary=summarize(json.loads(args.results.read_text(encoding='utf-8')))
    (args.output/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (args.output/'FULL_RESULTS.md').write_text(markdown(summary),encoding='utf-8')
    print(json.dumps({'rows':len(summary['rows']),'decision':summary['decision']['status']}))
