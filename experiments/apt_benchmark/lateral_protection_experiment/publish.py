"""Publish audited aggregates only; private rows and model files stay private."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import shutil
import numpy as np
from ..tabular_batch.run_e1 import write_json, sha256_file, utc_now
from .run import read, verify_files

POLICIES=['reference','candidate','threshold_only','cv_natural_argmax','cv_natural_benign_threshold']
NAMES={'reference':'Lateral-sensitive reference','candidate':'Constrained candidate','threshold_only':'Threshold-only ablation',
       'cv_natural_argmax':'Natural tree, argmax','cv_natural_benign_threshold':'Natural tree, benign 1% threshold'}

def means(rows,part):
    values={}
    for name in POLICIES:
        selected=[r['partitions'][part][name] for r in rows if name in r['partitions'][part]]
        if not selected: continue
        names=['benign_fpr','fp','tp','attack_recall','attack_precision','attack_f1','roc_auc','average_precision','alert_fraction']
        values[name]={'pairs':len(selected),'seeds':[r['seed'] for r in rows if name in r['partitions'][part]],**{key:float(np.mean([x[key] for x in selected])) for key in names},
            'stage_recall':{stage:float(np.mean([x['per_stage'][stage]['recall'] for x in selected])) for stage in selected[0]['per_stage']},
            'stage_detected':{stage:float(np.mean([x['per_stage'][stage]['detected'] for x in selected])) for stage in selected[0]['per_stage']},
            'worst_lateral_recall':min(x['per_stage']['LateralMovement']['recall'] for x in selected),
            'worst_benign_fpr':max(x['benign_fpr'] for x in selected)}
    return values

def table(rows):
    return '\n'.join(['| '+' | '.join(map(str,row))+' |' for row in [rows[0],['---']*len(rows[0]),*rows[1:]]])

def pct(value): return f'{100*value:.3f}%'

def publish(run, audit_path, output, external=None, external_audit=None):
    summary=read(run/'SUMMARY.json'); audit=read(audit_path); prefit=read(run/'PREFIT_RECEIPT.json')
    if summary['status']!='COMPLETE' or audit['audit_status']!='PASS' or audit['run_status']!='COMPLETE' or audit['audited_cells']!=152:
        raise ValueError('Publication requires all 152 cells and passing independent consistency audit')
    if audit['artifact_hashes']['SUMMARY.json']!=sha256_file(run/'SUMMARY.json') or audit['execution_binding']!=summary['execution_binding']:
        raise ValueError('Summary changed after audit')
    if audit['artifact_hashes']['PREFIT_RECEIPT.json'] != sha256_file(run/'PREFIT_RECEIPT.json'):
        raise ValueError('Prefit receipt changed after audit')
    output.mkdir(parents=True,exist_ok=True)
    grouped={str(b):[r for r in summary['groups'] if r['budget']==b] for b in [1024,32,128,512]}
    aggregate={b:{p:means(rows,p) for p in ['verification','test']} for b,rows in grouped.items()}
    matched_feasible={b:{p:means([r for r in rows if r['selection_status']=='SELECTED'],p) for p in ['verification','test']} for b,rows in grouped.items()}
    fit_records=[]; cells=[]
    for group in prefit['fixed']['groups']:
        group_key=f"{group['budget']}/{group['seed']}"
        group_path=run/'groups'/str(group['budget'])/str(group['seed'])/'RESULT.json'
        if audit['group_result_hashes'][group_key] != sha256_file(group_path):
            raise ValueError('Group result changed after audit')
        group_result=read(group_path)
        for model in ['xgboost','lightgbm']:
            for scheme in ['natural','balanced','lateral2','lateral4']:
                folder=run/'cells'/str(group['budget'])/str(group['seed'])/model/scheme
                if group_result['cell_complete_sha256'][model+'/'+scheme] != sha256_file(folder/'COMPLETE.json'):
                    raise ValueError('Cell completion changed after audit')
                verify_files(folder,read(folder/'COMPLETE.json')['files'])
                verify_files(folder,read(folder/'FIT_COMPLETE.json')['files'])
                fit=read(folder/'FITTED.json'); cell=read(folder/'CELL.json'); cells.append(cell)
                fit_records.append({'budget':group['budget'],'seed':group['seed'],'model':model,'scheme':scheme,
                    'selected_parameters':fit['cv_metadata']['selected_parameters'],
                    'selected_cv_macro_f1':fit['cv_metadata']['selected_mean_macro_f1'],'timing_seconds':fit['timing_seconds'],
                    'fit_complete_sha256':sha256_file(folder/'FIT_COMPLETE.json'),'complete_sha256':sha256_file(folder/'COMPLETE.json')})
    unique_support=set(i for g in prefit['fixed']['groups'] for i in g['indices'])
    ledger={'classes':prefit['fixed']['classes'],'per_fit_total':{str(b):160+b for b in [32,128,512,1024]},'per_fit_attack':160,
            'unique_fitting_rows_across_registered_groups':len(unique_support),
            'selection':{k:v for k,v in prefit['fixed']['partitions']['selection'].items() if k=='class_counts'},
            'verification':{k:v for k,v in prefit['fixed']['partitions']['verification'].items() if k=='class_counts'},
            'test':{k:v for k,v in prefit['fixed']['partitions']['test'].items() if k=='class_counts'},
            'available_labeled_fit_pool_rows':92350, 'total_prepared_labeled_rows':153919,
            'interpretation':'Label-based support sampling and splits access the larger known-label pool; allocated fitting labels are not total acquisition cost. All evaluation rows already exposed in earlier work.'}
    decisions={b:{'feasible_groups':sum(r['selection_status']=='SELECTED' for r in rows),'required_groups':len(rows),
                'candidate_equals_threshold_only':sum(bool(r['selection'].get('candidate_equals_threshold_only')) for r in rows),
                'candidate_cells':dict(Counter(r['selection']['choices']['candidate']['cell_id'] for r in rows if r['selection_status']=='SELECTED')),
                'reference_cells':dict(Counter(r['selection']['choices']['reference']['cell_id'] for r in rows if r['selection_status']=='SELECTED'))} for b,rows in grouped.items()}
    evidence={'created_utc':utc_now(),'status':'AUDITED_COMPLETE_DEVELOPMENT_STUDY','execution_binding':summary['execution_binding'],
              'primary_gate':summary['primary_gate'],'secondary_gates':summary['secondary_gates'],'aggregates':aggregate,
              'matched_feasible_aggregates':matched_feasible,
              'policy_selections':decisions,'label_ledger':ledger,'software_versions':prefit['fixed']['versions'],
              'source_freeze_git_head':prefit['git_head'],'protocol_sha256':prefit['fixed']['protocol_sha256'],
              'fit_tuning_elapsed_seconds_sum':sum(x['timing_seconds']['total_fit_and_tuning'] for x in fit_records),
              'note_runtime':'Sum of per-cell elapsed fit/tuning times, overlapping across two workers; not CPU-core seconds or total wall time. Inference was not benchmarked.'}
    for name,path in [('SUMMARY.json',run/'SUMMARY.json'),('AUDIT.json',audit_path)]: shutil.copy2(path,output/name)
    write_json(output/'CELL_METRICS.json',cells); write_json(output/'FIT_SUMMARY.json',fit_records)
    if external is not None:
        ext=read(external); ea=read(external_audit)
        if ea.get('audit_status')!='PASS': raise ValueError('External consistency audit did not pass')
        if ea['artifact_hashes']['RESULT.json'] != sha256_file(external):
            raise ValueError('External result changed after audit')
        if ext['protocol']['source_execution_binding'] != summary['execution_binding'] or ea['source_prefit_sha256'] != audit['artifact_hashes']['PREFIT_RECEIPT.json']:
            raise ValueError('External package belongs to a different source experiment')
        evidence['external']=ext; evidence['external_audit']=ea
        shutil.copy2(external,output/'EXTERNAL_RESULT.json'); shutil.copy2(external_audit,output/'EXTERNAL_AUDIT.json')
    write_json(output/'EVIDENCE.json',evidence)
    lines=['# Lateral-movement protection: completed development results','',
        '**Primary decision: '+summary['primary_gate']['status']+'.** All 152 final models and 19 groups completed; independent artifact/metric consistency audit passed. This is source development, not independent confirmation.','',
        '## Primary verification: 1,024 benign fitting examples','',
        'Rates below are means over the listed fitting seeds on the same 15,392 verification flows (14,965 benign; 72 lateral). Feasible subsets, if any, cannot replace the all-ten-seed gate.','']
    rows=[['Policy','Seeds','Benign FPR','Lateral detection','Attack recall','Attack F1']]
    for name,m in aggregate['1024']['verification'].items(): rows.append([NAMES[name],m['pairs'],pct(m['benign_fpr']),pct(m['stage_recall']['LateralMovement']),pct(m['attack_recall']),f"{m['attack_f1']:.4f}"])
    lines += [table(rows),'',
        '**Different seed sets:** reference/candidate/threshold-only rows cover feasible selections; ordinary controls cover every seed. Their unpaired means must not be interpreted as a candidate-versus-ordinary improvement. EVIDENCE.json includes matched-feasible-control means separately, which remain a selected-subset diagnostic, not the primary result.','']
    for name,m in aggregate['1024']['verification'].items():
        lines.append('- '+NAMES[name]+': seeds '+', '.join(map(str,m['seeds']))+'.')
    lines += ['','## Every primary seed','']
    rows=[['Seed','Status','Reference FP / lateral TP','Candidate FP / lateral TP','Same as threshold-only?']]
    for r in grouped['1024']:
        metrics=r['partitions']['verification']
        def counts(name):
            if name not in metrics:return 'Unavailable'
            m=metrics[name];return f"{m['fp']} / {m['per_stage']['LateralMovement']['detected']}"
        rows.append([r['seed'],r['selection_status'],counts('reference'),counts('candidate'),r['selection'].get('candidate_equals_threshold_only','Unavailable')])
    lines += [table(rows),'','## Secondary normal budgets','']
    rows=[['Normal budget','Feasible groups','Frozen point-screen decision']]
    for b in ['32','128','512']:
        rows.append([b,f"{decisions[b]['feasible_groups']}/3",summary['secondary_gates'][b]['status']])
    lines += [table(rows),'','Secondary outcomes do not rescue a failed primary endpoint. Full stage/ranking/classification results are in EVIDENCE.json and CELL_METRICS.json.','',
        '## Audit and claim boundaries','',
        'The audit independently reconstructs supports, partitions, weights, threshold choices, saved metrics and exact decision inequalities. It does not retrain models, independently relabel attacks, or create independent incidents. All failures remain visible.','',
        'Training weights and constrained thresholds are established methods. This experiment tests an applied tradeoff; no algorithmic novelty, early-warning claim, production suppression approval, or measured analyst-time savings is established.','']
    if 'external' in evidence:
        ext=evidence['external']; lines += ['## Limited DEDALE external stress','',f"Fixed source seed 20260921; {ext['benign_n']:,} unique sampled benign and {ext['lateral_n']} lateral flows from one execution. No target fitting or calibration.",
            f"Source selection status: **{ext['source_selection_status']}**. Missing policies: {', '.join(ext['missing_policies']) or 'none'}. When the source candidate is infeasible, these results describe the ordinary controls only; no proposed candidate is tested.",'']
        rows=[['Source-locked policy','False benign alerts','Lateral detections','FPR']]
        for name,m in ext['metrics'].items(): rows.append([NAMES[name],f"{m['fp']:,}/{m['benign_n']:,}",f"{m['per_stage']['LateralMovement']['detected']}/{m['per_stage']['LateralMovement']['n']}",pct(m['benign_fpr'])])
        lines += [table(rows),'',ext['interpretation'],'']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write_json(output/'PUBLICATION.json',{'created_utc':utc_now(),'source_execution_binding':summary['execution_binding'],
        'files':{p.name:sha256_file(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='PUBLICATION.json'},
        'private_data_policy':'No raw feature rows, IPs, identifiers, saved probabilities or model binaries copied to public result package'})
    return evidence

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--external',type=Path);p.add_argument('--external-audit',type=Path)
    a=p.parse_args();print(publish(a.run,a.audit,a.output,a.external,a.external_audit)['primary_gate'])

if __name__=='__main__':main()
