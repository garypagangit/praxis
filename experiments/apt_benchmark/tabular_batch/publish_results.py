"""Package audited E0/E1/E3/E4 evidence, optionally E2/E1B, for Git review.

Reads private outputs without changing them. Publishes no prepared/raw rows,
predictions, model checkpoints, per-row support rosters, or cloud/account settings.
This helper makes no Git commit and performs no scientific fit or AWS action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

MODULE='experiments/apt_benchmark/tabular_batch'
DEFAULT_COMMIT='926bc35bd214931a3f2dc83715483d58c3219cbf'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def value_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def committed_bytes(repo,commit,name):
    return subprocess.check_output(['git','show',commit+':'+MODULE+'/'+name],cwd=repo)


def require(value,message):
    if not value:raise ValueError(message)


def inspect_public(value):
    """Fail closed on row arrays or private paths introduced by future schemas."""
    forbidden={'selected_fit_indices','selected_fit_fingerprints','calibration_indices','test_indices',
               'calibration_probabilities','test_probabilities','calibration_y','test_y','fingerprints',
               'query_indices','query_fingerprints','query_probabilities','query_labels','query_y','query_weights','support_indices',
               'account','bucket','instance','stop_role_arn','profile','secret_access_key','session_token'}
    if isinstance(value,dict):
        blocked=set(value)&forbidden
        if isinstance(value.get('query_weights'),str):blocked.discard('query_weights')
        require(not blocked,'Private fields cannot enter public evidence')
        for item in value.values():inspect_public(item)
    elif isinstance(value,list):
        for item in value:inspect_public(item)
    elif isinstance(value,str):
        require(not re.search(r'(?:(?<![A-Za-z])[A-Za-z]:[\\/]|s3://|arn:aws:|/opt/praxis/|/opt/dlami/)',value),'Private path/cloud identifier in public evidence')


def e1_receipts(run_roots,analysis):
    expected={(c['model'],c['seed']):c for c in analysis['cells']};receipts=[];found=set()
    for number,root in enumerate(map(Path,run_roots),1):
        path=root/'PREFIT_RECEIPT.json';prefit=read(path);execution=prefit['execution']
        require(value_sha(execution)==prefit['execution_binding'],'E1 prefit hash mismatch')
        common={k:execution[k] for k in ['data_sha256','manifest_sha256','protocol_sha256','code_sha256']}
        require(common==analysis['common_binding'],'E1 receipt binding differs from analyzed cells')
        supports={seed:{'count':len(v['indices']),'indices_sha256':value_sha(v['indices']),
                        'fingerprints_sha256':value_sha(v['fingerprints'])} for seed,v in execution['supports'].items()}
        completed=[]
        for model in execution['models']:
            for seed in map(int,execution['supports']):
                key=(model,seed)
                if key not in expected:continue
                require(key not in found,'Duplicate source receipt for analyzed cell');found.add(key)
                cell_dir=root/'cells'/model/str(seed);marker=read(cell_dir/'COMPLETE.json')
                require(set(marker['file_sha256'])=={'CELL.json','PREDICTIONS.npz'},'Unexpected completion artifact roster')
                for name,digest in marker['file_sha256'].items():require(sha(cell_dir/name)==digest,'Completed E1 artifact changed')
                require(marker['comparison_binding']==expected[key]['comparison_binding'],'E1 comparison binding differs')
                require(marker['file_sha256']['PREDICTIONS.npz']==expected[key]['prediction_sha256'],'Analyzed predictions differ')
                completed.append({'model':model,'seed':seed,'execution_binding':marker['execution_binding'],
                                  'comparison_binding':marker['comparison_binding'],'file_sha256':marker['file_sha256']})
        receipts.append({'source_run_number':number,'prefit_receipt_sha256':sha(path),'created_utc':prefit.get('created_utc'),
                         'execution_binding':prefit['execution_binding'],'common_binding':common,
                         'models':execution['models'],'requested_device':execution['requested_device'],
                         'versions':execution['versions'],'supports_aggregate_hashes_only':supports,'completed_cells':completed})
    require(found==set(expected),'Missing source completion receipts for analyzed E1 cells')
    return {'schema_version':1,'source_analysis_sha256':None,'runs':receipts,'completed_cells':len(found),
            'omitted_private_content':'Per-row indices/fingerprints, arrays, models, private filesystem and account settings.'}


def e3_public(results):
    allowed={'arm','fit_count','fit_seconds','model_sha256','noise_rate','prediction_sha256','seed','test','treatment_audit','treatment_trace'}
    for row in results['rows']:
        require(set(row)<=allowed|{'model_file','prediction_file'},'Unexpected E3 row fields; review before publication')
    return {'protocol':results['protocol'],'rows':[{k:v for k,v in row.items() if k in allowed} for row in results['rows']],
            'summary':results['summary'],'publication_note':'Private model and prediction file paths omitted; their SHA256 receipts retained.'}


def mean(values):return sum(values)/len(values)


def full_batch_status(e1):
    expected={(model,seed) for model in ('random_forest','xgboost','lightgbm','tabicl_v2','tabpfn_2_5_synthetic')
              for seed in range(20260921,20260931)}
    completed={(c['model'],c['seed']) for c in e1['cells']}
    full=completed==expected
    return {'completed':full,'required_cells':len(expected),'available_cells':len(completed),
            'e1':e1['primary']['e1']['status'] if full else 'INCOMPLETE',
            'e4':e1['primary']['e4']['status'] if full else 'INCOMPLETE'}


def completed_pilot(path,code,protocol_name,expected_data_sha,*,repo=None,frozen_commit=None):
    """Verify private pilot completion; publish hashes and aggregates, never rosters."""
    path=Path(path);path=path/'AGGREGATE.json' if path.is_dir() else path
    require(path.name=='AGGREGATE.json','Pilot input must be its completed AGGREGATE.json')
    root=path.parent.resolve();aggregate=read(path);marker=read(root/'COMPLETE.json')
    require('AGGREGATE.json' in marker['artifact_sha256'],'Pilot completion does not bind its aggregate')
    for name,digest in marker['artifact_sha256'].items():
        member=(root/name).resolve()
        require(member.is_relative_to(root) and member.is_file(),'Invalid completed pilot artifact path')
        require(sha(member)==digest,'Completed pilot artifact changed: '+name)
    prefit_path=root/'PREFIT_RECEIPT.json';prefit=read(prefit_path)
    binding=prefit.get('binding',prefit.get('execution'))
    binding_sha=prefit.get('binding_sha256',prefit.get('execution_binding'))
    require(value_sha(binding)==binding_sha==marker.get('binding_sha256',marker.get('execution_binding')),'Pilot binding changed')
    require(aggregate['prefit_receipt_sha256']==sha(prefit_path),'Pilot aggregate prefit receipt mismatch')
    require(binding['data_npz_sha256']==aggregate.get('input_sha256',binding['data_npz_sha256'])==expected_data_sha,'Pilot data differs from E1/E3')
    require(binding['protocol_sha256']==aggregate['protocol_sha256']==sha(code/protocol_name),'Pilot protocol differs from current source')
    for name,digest in binding['code_sha256'].items():
        require((code/name).resolve().is_relative_to(code.resolve()),'Invalid pilot source path')
        require(sha(code/name)==digest,'Pilot scientific source changed: '+name)
    for name,digest in marker.get('cell_complete_sha256',{}).items():
        directory=(root/'cells'/name).resolve()
        require(directory.is_relative_to(root/'cells'),'Invalid pilot cell path')
        require(sha(directory/'COMPLETE.json')==digest,'Pilot cell completion changed')
        cell_marker=read(directory/'COMPLETE.json')
        require(cell_marker['execution_binding']==binding_sha,'Pilot cell execution binding differs')
        require(set(cell_marker['file_sha256'])=={'CELL.json','PREDICTIONS.npz'},'Unexpected pilot cell artifact roster')
        for member,member_sha in cell_marker['file_sha256'].items():require(sha(directory/member)==member_sha,'Pilot cell artifact changed')
        cell=read(directory/'CELL.json')
        require(sha(directory/'BACKEND_PRIVATE.json')==cell['backend_private_sha256'],'Pilot backend receipt changed')
        require(cell['prefit_receipt_sha256']==aggregate['prefit_receipt_sha256'],'Pilot cell prefit binding differs')
    receipt={'completion_sha256':sha(root/'COMPLETE.json'),'completion':marker,
             'prefit_receipt_sha256':sha(prefit_path),'binding_sha256':binding_sha,
             'source_code_sha256':binding['code_sha256'],'protocol_sha256':binding['protocol_sha256'],
             'data_npz_sha256':binding['data_npz_sha256'],'manifest_sha256':binding['manifest_sha256'],
             'private_rosters_omitted':True}
    if frozen_commit:
        commit=subprocess.check_output(['git','rev-parse',frozen_commit],cwd=repo,text=True).strip()
        for name,digest in {**binding['code_sha256'],protocol_name:binding['protocol_sha256']}.items():
            require(hashlib.sha256(committed_bytes(repo,commit,name)).hexdigest()==digest,'Pilot source differs from frozen commit: '+name)
        receipt['scientific_runtime_commit']=commit
    inspect_public(aggregate);inspect_public(receipt)
    return aggregate,receipt,read(code/protocol_name),sha(path)


def make_report(e1,e3,source_commit,e2=None,prescreen=None):
    primary=e1['primary'];foundation_count=sum(c['model'] in {'tabicl_v2','tabpfn_2_5_synthetic'} for c in e1['cells'])
    batch=full_batch_status(e1);full_foundations=batch['completed']
    e1_status=batch['e1'];e4_status=batch['e4']
    lines=['# Few-label APT detection: what the new batch shows','']
    if prescreen:
        p=prescreen['primary_descriptive'];candidate=mean([row['candidate_weighted_estimated_macro_f1'] for row in p['pairs']]);baseline=mean([row['comparator_weighted_estimated_macro_f1'] for row in p['pairs']])
        lead='A smaller CPU test found a promising lead' if p['status']=='PRELIMINARY_PROMISING' else 'The smaller CPU test did not clear its success criteria'
        lines += [f"**{lead}:** TabICL's estimated macro F1 was {100*candidate:.2f}%, compared with {100*baseline:.2f}% for the tree model selected separately for each seed by training cross-validation, a difference of {100*p['mean_weighted_estimated_macro_f1_delta']:+.2f} percentage points. The declared joint F1 and mean recall screen returned **{p['status']}**.",'',
                  'These are prevalence-weighted estimates from three fitting seeds, all 858 test attacks and a sample of 1,024 normal rows from one exposed development split. Training used only 32 labels per class, including NormalTraffic; abundant benign labels were not tested. Tree tuning used a bounded three-candidate grid, not broad hyperparameter optimization. These are not full-test foundation scores, independent-incident evidence, or proof of novelty. The complete E1/E4 comparison remains unfinished.','']
    lines += [
           '**This is a development screen on existing SCVIC training data. It does not establish performance on new incidents or a novel praxis contribution.**','',
           'This batch tests scarce or incorrect labels and model uncertainty. It does not test the earlier missing-or-delayed-log hypothesis, and it establishes no improvement in resilience to missing logs.','',
           f"{e1['completed_cell_count']} full-E1 model/seed cells were independently audited. Full-E1 foundation-model cells available: {foundation_count}/20. {('E1B separately completed six foundation cells. ' if prescreen else '')}The separate E3 label-noise experiment completed 18 cells; both tested correction adaptations failed their success criteria.",'',
           '## Experiment status','',
           '| Experiment | Question in simple language | Current result |','|---|---|---|',
           '| E0 | Do the datasets support the planned tests? | SCVIC supports 32 examples per class in this development split; larger equal budgets and the original temporal design are unsupported. |',
           f'| E1 | Which model recognizes attack stages with very few labels? | {e1_status}; classical controls available, foundation comparison requires the registered foundation cells. |',
           f"| E1B | Is a smaller CPU foundation-model screen worth following up? | {prescreen['primary_descriptive']['status'] if prescreen else 'Not completed'}; separate development prescreen, never a replacement for E1/E4. |",
           f"| E2 | Can a cheap first check make the complete system faster? | {('CPU necessary-speed condition ' + ('passed' if e2['decision']['necessary_speed_condition_passed'] else 'failed') + '; full pipeline frontier remains untested.') if e2 else 'Not completed; timing pilot pending.'} |",
           '| E3 | Can a checker find and repair wrong training labels? | Negative for both tested gradient/GMM adaptations at 20% injected noise. |',
           f'| E4 | Can uncertainty sets stay small without excluding attack stages? | {e4_status} for the foundation comparison; classical empirical coverage results are available. |',
           '| E5 | Can fusion reliably catch a stage absent from training? | Not run: no qualified independent open-set evaluation; the proposed unseen-stage guarantee is unsupported. |',
           '| E6 | Can the system predict the next attack stage? | Blocked: S-DAPT corrected source, raw sequences and data rights remain unqualified. |',
           '| E7 | Does GRANDE help on this data? | Optional, not run. Prior security applications exist; a first-use claim is unavailable. |','',
           '## E1: available model results','',
           'Each fitting seed uses the same 32 labeled examples per class across models. Reported ranges show changes across fitting samples on the same test set; they are not confidence intervals.','',
           '| Model | Seeds | Mean macro F1 | Minimum–maximum |','|---|---:|---:|---:|']
    for name,m in sorted(e1['model_summaries'].items()):
        f=m['macro_f1'];lines.append(f"| {name} | {f['seed_count']} | {100*f['mean']:.2f}% | {100*f['min']:.2f}–{100*f['max']:.2f}% |")
    lines+=['','Macro F1 gives all six classes equal weight, including NormalTraffic. The primary comparator is chosen by training-only inner cross-validation for each seed, never by test results. The full E1 protocol was not changed after observing its outcomes.']
    if full_foundations:
        lines+=['',f"E1 descriptive gate: **{e1_status}**. Mean paired TabICL-minus-selected-GBDT macro-F1 difference: {100*primary['e1']['mean_paired_macro_f1_delta']['mean']:+.2f} percentage points. The high-risk recall guards are retained in [E1_ANALYSIS.json](E1_ANALYSIS.json)."]
    if prescreen:
        q=prescreen['query'];screen_primary=prescreen['primary_descriptive']
        lines+=['','## E1B: smaller CPU foundation-model prescreen','',
                f"This separate test uses the first three fitting seeds and the same 192 labeled training examples per seed: 32 per class, including NormalTraffic. It evaluates every one of the {q['attack_rows']:,} test attacks plus {q['normal_rows']:,} hash-selected normal rows. Each sampled normal row receives weight {q['normal_weight']:.5f}, representing {q['original_test_normal_rows']:,} original normal test rows. This estimates the original test prevalence; it does not evaluate all original normal rows.",'',
                '| Model | Seeds | Estimated macro F1, weighted sample | Actual macro F1, full test | Estimate minus full test |',
                '|---|---:|---:|---:|---:|']
        for name,model in sorted(prescreen['model_summaries'].items()):
            weighted=model['mean_prevalence_weighted_estimated_macro_f1'];full=model.get('mean_baseline_full_test_macro_f1');delta=model.get('mean_weighted_estimate_minus_full_test_macro_f1')
            lines.append(f"| {name} | {model['seed_count']} | {100*weighted:.2f}% | {f'{100*full:.2f}%' if full is not None else 'Not evaluated'} | {f'{100*delta:+.2f} points' if delta is not None else 'Not available'} |")
        lines+=['','Raw false alarms below count normal rows assigned any attack label. All models saw the same 1,024 normal queries; columns show the three fitting seeds.','',
                '| Model | Seed 20260921 | Seed 20260922 | Seed 20260923 | Mean false-alarm rate |',
                '|---|---:|---:|---:|---:|']
        false_alarm_counts={}
        for name in sorted(prescreen['model_summaries']):
            cells=sorted([c for c in prescreen['cells'] if c['model']==name],key=lambda c:c['seed']);counts=[]
            for cell in cells:
                metrics=cell['query_unweighted_metrics'];normal=metrics['classes'].index('NormalTraffic');row=metrics['confusion_matrix'][normal]
                count=int(sum(row)-row[normal]);counts.append(count);false_alarm_counts[(name,cell['seed'])]=count
            lines.append(f"| {name} | {' | '.join(map(str,counts))} | {100*mean(counts)/q['normal_rows']:.2f}% |")
        selected_counts=[false_alarm_counts[(p['comparator_selected_by_e1_inner_cv'],p['seed'])] for p in screen_primary['pairs']]
        lines.append(f"| Selected tree comparator | {' | '.join(map(str,selected_counts))} | {100*mean(selected_counts)/q['normal_rows']:.2f}% |")
        primary_false_alarms=[count for (model,seed),count in false_alarm_counts.items() if model=='tabicl_v2']
        lines+=['',f"TabICL still marked {min(primary_false_alarms)} to {max(primary_false_alarms)} of the 1,024 normal flows as attacks: {100*min(primary_false_alarms)/q['normal_rows']:.2f}% to {100*max(primary_false_alarms)/q['normal_rows']:.2f}%. This is a comparative improvement under a small label budget, not an operational detector that meets a low false-alert budget.",'',
                '| Model | Mean InitialCompromise recall | Mean DataExfiltration recall |',
                '|---|---:|---:|']
        by_cell={(c['model'],c['seed']):c for c in prescreen['cells']}
        for name in ('tabicl_v2','tabpfn_2_5_synthetic','Selected tree comparator'):
            group=[by_cell[(p['comparator_selected_by_e1_inner_cv'],p['seed'])] for p in screen_primary['pairs']] if name=='Selected tree comparator' else [c for c in prescreen['cells'] if c['model']==name]
            recalls=[mean([c['prevalence_weighted_estimated_metrics']['per_stage'][stage]['recall'] for c in group]) for stage in ('InitialCompromise','DataExfiltration')]
            lines.append(f"| {name} | {100*recalls[0]:.2f}% | {100*recalls[1]:.2f}% |")
        lines+=['',f"Prescreen decision: **{screen_primary['status']}**. TabICL remains the primary foundation model; TabPFN is secondary regardless of its result. The selected tree comparator comes from inner training cross-validation.",'',
                f"Across the {screen_primary['paired_seed_count']} paired seeds, TabICL's estimated macro-F1 difference from that comparator was {100*screen_primary['mean_weighted_estimated_macro_f1_delta']:+.2f} percentage points. Mean recall differences were {100*screen_primary['mean_high_risk_recall_deltas']['InitialCompromise']:+.2f} points for InitialCompromise and {100*screen_primary['mean_high_risk_recall_deltas']['DataExfiltration']:+.2f} for DataExfiltration. The prescreen requires at least a 2-point F1 gain and no more than a 5-point mean loss on either high-risk stage.",'',
                'The full-test baseline column makes the sampling approximation visible; it is not a full-test foundation score. Each sampled normal error represents about 29 original rows, so a few errors can change the estimate substantially. All three seeds share the same test sample; their variation does not measure this sampling uncertainty. Foundation predictions may also change with query-batch composition; batch invariance was not established. The original E1/E4 remains incomplete, and this prescreen evaluates no calibration sets or GPU performance. [E1B aggregate](E1B_AGGREGATE.json), [protocol](E1B_PROTOCOL.json), and [receipts](E1B_RECEIPTS.json) retain all models and guards.']
    lgb=e1['model_summaries'].get('lightgbm')
    if lgb:
        initial=lgb['per_stage']['InitialCompromise'];marginal=next(m for m in lgb['e4'] if m['method']=='marginal' and m['nominal_coverage']==.9)
        lines+=['',f"In the ten-seed E1 control results, LightGBM's InitialCompromise mean recall was {100*initial['recall']['mean']:.2f}% and ROC-AUC was {initial['roc_auc_ovr']['mean']:.5f}, but precision was only {100*initial['precision']['mean']:.2f}% and F1 was {initial['f1']['mean']:.5f}. It found many of the 15 labeled cases while falsely assigning that stage to many other flows. High recall or ROC-AUC alone does not make a useful detector.",'',
                '## E4: overall coverage can hide missed attack stages','',
                'E4 uses a separate labeled calibration partition with 30,782 rows: 853 attack rows and 29,929 normal rows. The 32-per-class number describes model fitting only; it is not the total labeling cost of this calibrated system. The separate E1B CPU prescreen used no calibration labels.','',
                f"LightGBM's nominal 90% marginal prediction sets covered the correct label for {100*marginal['coverage']['mean']:.2f}% of test rows on average, with {marginal['mean_set_size']['mean']:.4f} labels per set. Stage coverage was much lower: lateral movement {100*marginal['per_class']['LateralMovement']['mean']:.2f}%, pivoting {100*marginal['per_class']['Pivoting']['mean']:.2f}%, and exfiltration {100*marginal['per_class']['DataExfiltration']['mean']:.2f}%.",'',
                'In simple terms, doing well across mostly normal traffic can conceal weak protection for some attack stages. Marginal coverage does not promise coverage separately for every stage. This finding does not refute conformal theory and is not novel by itself. All marginal and class-conditional results at 90% and 95% are retained. InitialCompromise has only 14 calibration and 15 test examples; its 95% class-conditional rule must always include that class.']
    if full_foundations:
        lines+=['',f"E4 descriptive foundation comparison: **{e4_status}**. It checks set size against declared empirical coverage floors, not equality of achieved coverage or a population guarantee."]
    lines+=['','## E3: the tested label checker did not help','',
            'We deliberately corrupted 20% of training labels, then tested two declared adaptations of gradient-history/Gaussian-mixture checking: remove suspicious examples or change their labels. Source labels and test labels were not changed. These are adaptations, not an exact reproduction of the original Gradients algorithm.','',
            '| Method | Mean F1 with clean training labels | Mean F1 with 20% corrupted labels |','|---|---:|---:|']
    for arm,label in [('no_correction','Unchanged XGBoost'),('gradient_gmm_removal_adaptation','Remove flagged examples'),('gradient_gmm_relabel_adaptation','Relabel flagged examples')]:
        clean=mean([r['test']['macro_f1'] for r in e3['rows'] if r['arm']==arm and r['noise_rate']==0])
        noisy=mean([r['test']['macro_f1'] for r in e3['rows'] if r['arm']==arm and r['noise_rate']==.2])
        lines.append(f'| {label} | {100*clean:.2f}% | {100*noisy:.2f}% |')
    clean_removal=[r['treatment_audit']['per_stage']['InitialCompromise'] for r in e3['rows']
                   if r['arm']=='gradient_gmm_removal_adaptation' and r['noise_rate']==0]
    noisy_removal=[r['treatment_audit'] for r in e3['rows'] if r['arm']=='gradient_gmm_removal_adaptation' and r['noise_rate']==.2]
    noisy_relabel=[r['treatment_audit'] for r in e3['rows'] if r['arm']=='gradient_gmm_relabel_adaptation' and r['noise_rate']==.2]
    rare_removed=[r['originally_clean_removed_or_mislabeled'] for r in clean_removal]
    rare_total=[r['originally_clean_count'] for r in clean_removal]
    rare_range=str(min(rare_removed)) if min(rare_removed)==max(rare_removed) else f'{min(rare_removed)} to {max(rare_removed)}'
    lines+=['',f"The audit identifies a failure mechanism: with clean labels, removal discarded {rare_range} of the {min(rare_total)} valid InitialCompromise examples per seed. At 20% injected noise, only {100*mean([r['actual_treatment']['precision'] for r in noisy_removal]):.1f}% of removed examples actually had corrupted labels. Relabeling repaired an average of {mean([r['noisy_labels_corrected_and_retained'] for r in noisy_relabel]):.0f} corrupted labels, but also changed {mean([r['originally_clean_removed_or_mislabeled'] for r in noisy_relabel]):.0f} originally correct labels per seed. This checker failed to separate correct rare-stage examples from labeling errors."]
    lines+=['','Both treatments lowered mean F1 in the clean and noisy conditions and harmed rare-stage recall. The proposed checker is therefore not supported by this experiment. This rejects these specific adaptations under this protocol; it does not establish that all label-noise methods fail. E3 used up to 256 fit examples per class, with only 43 InitialCompromise examples, so its scores are not directly comparable to E1’s equal 32-per-class experiment.','',
            '## E2 scope','']
    if e2:
        decision=e2['decision'];full_seconds=decision['full_stage_median_seconds'];screen_seconds=decision['screen_alone_median_seconds']
        lines+=['The optional [E2_AGGREGATE.json](E2_AGGREGATE.json) records a same-CPU latency pilot. It checks whether the first-stage binary screen alone can meet the necessary speed condition for a fivefold cascade speedup. It does not evaluate the full cascade, its held-out classification outcomes, or a GPU speed comparison.','',
                f"For {e2['query_rows']:,} rows, the selected {e2['selected_gbdt']} stage classifier took a median {full_seconds:.6f} seconds; the TabPFN binary screen alone took {screen_seconds:.3f} seconds, approximately {screen_seconds/full_seconds:,.0f} times as long. The screen needed to take at most {decision['required_screen_max_seconds']:.6f} seconds to make a fivefold serial-cascade speedup possible. Recorded decision: **{decision['status']}**.",
                '', 'These are three warm timing repetitions on one CPU batch, not a statistical speed guarantee. [E2 protocol](E2_PROTOCOL.json) and [completion/source receipts](E2_RECEIPTS.json) preserve the exact configuration.']
    else:lines+=['No end-to-end cascade or throughput improvement has been established. CPU and GPU timings from separate model experiments cannot establish that claim.']
    lines+=['','## Evidence and reproducibility','',
            f'E1/E3 scientific runtime frozen at commit `{source_commit}`. The separate E2 and E1B freeze commits, when present, are recorded in their receipts and provenance. Model inference artifacts remain private. The public package contains aggregate metrics, protocols and checksum receipts.','',
            '- [E0 qualification](../../tabular_batch/E0_DATASET_GATE.md)',
            '- [E1 analysis](E1_ANALYSIS.json), [E1 source receipts](E1_RECEIPTS.json), [E1 protocol](E1_PROTOCOL.json)',
            '- [E3 aggregate results](E3_RESULTS.json), [summary](E3_SUMMARY.json), [independent audit](E3_AUDIT.json), [protocol](E3_PROTOCOL.json)',
            '- [Source provenance](PROVENANCE.json) and [publication checksums](PUBLICATION.json)',
            '- [Requested versus evaluated scope](../../tabular_batch/BATCH_REVIEW.md) and [query-batching review](../../tabular_batch/QUERY_BATCHING_REVIEW.md)',
            '- [Literature and novelty review](../../tabular_batch/LITERATURE_VALIDITY.md)','',
            'The source is the author training CSV, not the unavailable author test file. Exact feature duplicates were removed, but related flows and incidents are not proven independent. Existing labels were accepted for this benchmark. There is no early-warning, next-stage, actor-attribution, significance, or operational-certification claim.','']
    return '\n'.join(lines)


def check_links(output,pending=()):
    checked=[]
    for md in output.glob('*.md'):
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',md.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):continue
            path=(md.parent/target.split('#')[0]).resolve()
            require(path.exists() or path in {(output/name).resolve() for name in pending},f'Broken local Markdown link: {target}')
            checked.append({'file':md.name,'target':target})
    return checked


def publish(repo,e1_analysis,e1_runs,e3_run,e3_audit,output,*,frozen_commit=DEFAULT_COMMIT,e2_path=None,
            e2_frozen_commit='431e783',e2_audit_path=None,prescreen_path=None,prescreen_frozen_commit=None,
            prescreen_audit_path=None):
    repo=Path(repo).resolve();output=Path(output).resolve();code=repo/MODULE
    require(output.is_relative_to(repo/'experiments/apt_benchmark/results'),'Public target must be within benchmark results')
    require(not e2_audit_path or e2_path,'E2 audit requires the completed E2 run')
    require(not prescreen_audit_path or prescreen_path,'E1B audit requires the completed prescreen run')
    e1_analysis=Path(e1_analysis);e3_run=Path(e3_run);e3_audit=Path(e3_audit)
    a=read(e1_analysis/'ANALYSIS.json');results=read(e3_run/'RESULTS.json');summary=read(e3_run/'SUMMARY.json')
    audit=read(e3_audit/'AUDIT.json');complete=read(e3_run/'RUN_COMPLETE.json');prefit=read(e3_run/'PRE_FIT_RECEIPT.json')
    require(a['audit_status']=='PASS','E1 calculation audit must pass')
    require(audit['audit_status']=='PASS' and audit['run_status']=='COMPLETE','E3 independent audit must be complete and pass')
    require(complete['results_sha256']==sha(e3_run/'RESULTS.json'),'E3 result changed after completion')
    require(audit['receipt_sha256']==sha(e3_run/'PRE_FIT_RECEIPT.json'),'E3 audited receipt changed')
    require(summary==results['summary']==audit['independent_summary'],'E3 summaries disagree')
    require(complete['run_count']==len(results['rows'])==audit['audited_cells']==18,'E3 grid is incomplete')
    require(a['common_binding']['data_sha256']==prefit['data_npz_sha256'],'E1/E3 data differ')
    commit=subprocess.check_output(['git','rev-parse',frozen_commit],cwd=repo,text=True).strip()
    source_files={}
    for name,digest in a['common_binding']['code_sha256'].items():
        observed=hashlib.sha256(committed_bytes(repo,commit,name)).hexdigest()
        require(observed==digest,f'E1 runtime hash differs from frozen commit: {name}')
        source_files[name]=observed
    for name,expected in [('run_e3.py',prefit['runner_sha256']),('protocol.json',a['common_binding']['protocol_sha256']),('protocol_e3.json',prefit['protocol_sha256'])]:
        observed=hashlib.sha256(committed_bytes(repo,commit,name)).hexdigest()
        require(observed==expected,f'Frozen source/protocol mismatch: {name}');source_files[name]=observed
    require(prefit['protocol_sha256']==audit['protocol_sha256'],'E3 registered protocol hashes disagree')
    require(read(e3_run/'PROTOCOL.json')==json.loads(committed_bytes(repo,commit,'protocol_e3.json')),'E3 run protocol contents differ from frozen protocol')
    receipts=e1_receipts(e1_runs,a);receipts['source_analysis_sha256']=sha(e1_analysis/'ANALYSIS.json')
    outputs={'E1_ANALYSIS.json':a,'E1_RECEIPTS.json':receipts,'E1_PROTOCOL.json':json.loads(committed_bytes(repo,commit,'protocol.json')),
             'E3_RESULTS.json':e3_public(results),'E3_SUMMARY.json':summary,'E3_AUDIT.json':audit,'E3_PROTOCOL.json':read(e3_run/'PROTOCOL.json'),
             'E3_RECEIPTS.json':{'prefit':prefit,'completion':complete,'private_prefit_sha256':sha(e3_run/'PRE_FIT_RECEIPT.json'),'private_results_sha256':sha(e3_run/'RESULTS.json'),'private_audit_sha256':sha(e3_audit/'AUDIT.json'),'private_reserialized_protocol_sha256':sha(e3_run/'PROTOCOL.json'),'protocol_copy_note':'Run protocol has identical JSON content to frozen source; formatting differs, so byte hashes differ.'}}
    e2=None;prescreen=None;extra_receipts={}
    if e2_path:
        e2,e2_receipt,e2_protocol,e2_sha=completed_pilot(e2_path,code,'protocol_e2_latency.json',prefit['data_npz_sha256'],repo=repo,frozen_commit=e2_frozen_commit)
        outputs.update({'E2_AGGREGATE.json':e2,'E2_RECEIPTS.json':e2_receipt,'E2_PROTOCOL.json':e2_protocol})
        extra_receipts['e2_aggregate_sha256']=e2_sha
        if e2_audit_path:
            e2_audit_path=Path(e2_audit_path);e2_audit_path=e2_audit_path/'E2_AUDIT.json' if e2_audit_path.is_dir() else e2_audit_path
            e2_audit=read(e2_audit_path)
            require(e2_audit['audit_status']=='PASS' and e2_audit['run_status']=='COMPLETE','E2 audit must be complete and pass')
            require(e2_audit['artifact_hashes']==e2_receipt['completion']['artifact_sha256'],'E2 audit covers different artifacts')
            require(e2_audit['decision']==e2['decision'],'E2 audit decision differs')
            outputs['E2_AUDIT.json']=e2_audit;extra_receipts['e2_audit_sha256']=sha(e2_audit_path)
    if prescreen_path:
        require(prescreen_frozen_commit,'E1B publication requires its separately frozen Git commit')
        prescreen,prescreen_receipt,prescreen_protocol,prescreen_sha=completed_pilot(prescreen_path,code,'protocol_e1_cpu_prescreen.json',prefit['data_npz_sha256'],repo=repo,frozen_commit=prescreen_frozen_commit)
        require(prescreen['foundation_cell_count']==6,'E1B publication requires all six foundation cells')
        require(prescreen['full_e1_completed'] is False and prescreen['e4_evaluated'] is False,'Prescreen must not claim full E1/E4 completion')
        outputs.update({'E1B_AGGREGATE.json':prescreen,'E1B_RECEIPTS.json':prescreen_receipt,'E1B_PROTOCOL.json':prescreen_protocol})
        extra_receipts['e1b_aggregate_sha256']=prescreen_sha
        if prescreen_audit_path:
            prescreen_audit_path=Path(prescreen_audit_path);prescreen_audit_path=prescreen_audit_path/'AUDIT.json' if prescreen_audit_path.is_dir() else prescreen_audit_path
            prescreen_audit=read(prescreen_audit_path)
            require(prescreen_audit['audit_status']=='PASS' and prescreen_audit['run_status']=='COMPLETE','E1B audit must be complete and pass')
            for name,digest in {'AGGREGATE.json':prescreen_sha,'PREFIT_RECEIPT.json':prescreen_receipt['prefit_receipt_sha256'],
                                'COMPLETE.json':prescreen_receipt['completion_sha256']}.items():
                require(prescreen_audit['artifact_hashes'].get(name)==digest,'E1B audit covers different artifacts: '+name)
            outputs['E1B_AUDIT.json']=prescreen_audit;extra_receipts['e1b_audit_sha256']=sha(prescreen_audit_path)
    source_receipts={'e1_analysis_sha256':sha(e1_analysis/'ANALYSIS.json'),'e3_results_sha256':sha(e3_run/'RESULTS.json'),
                     'e3_summary_sha256':sha(e3_run/'SUMMARY.json'),'e3_audit_sha256':sha(e3_audit/'AUDIT.json')}
    source_receipts.update(extra_receipts)
    outputs['PROVENANCE.json']={'schema_version':1,'scientific_runtime_commit':commit,'scientific_runtime_sha256':source_files,
        'data_sha256':prefit['data_npz_sha256'],'manifest_sha256':prefit['manifest_sha256'],
        'source_aggregate_hashes':source_receipts,'publication_helper_sha256':sha(Path(__file__)),
        'e1_analysis_code_current_sha256':sha(code/'analyze_e1.py'),'e3_audit_code_current_sha256':sha(code/'audit_e3.py'),
        'publication_scope':'Aggregate evidence only; no raw/prepared rows, prediction arrays, per-row fit rosters, checkpoints or private AWS account settings.'}
    if e2:outputs['PROVENANCE.json']['e2_scientific_runtime_commit']=e2_receipt['scientific_runtime_commit']
    if e2_audit_path:outputs['PROVENANCE.json']['e2_audit_code_current_sha256']=sha(code/'audit_e2.py')
    if prescreen:outputs['PROVENANCE.json']['e1b_scientific_runtime_commit']=prescreen_receipt['scientific_runtime_commit']
    if prescreen_audit_path:outputs['PROVENANCE.json']['e1b_audit_code_current_sha256']=sha(code/'audit_cpu_prescreen.py')
    for value in outputs.values():inspect_public(value)
    allowed=set(outputs)|{'REPORT.md','PUBLICATION.json'}
    if output.exists():
        unknown={p.name for p in output.iterdir()}-allowed
        require(not unknown,'Public directory contains unhandled artifacts; use a fresh target or include previous optional evidence')
    output.mkdir(parents=True,exist_ok=True)
    for name,value in outputs.items():(output/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    report=make_report(a,results,commit,e2,prescreen)
    if e2_audit_path:report=report.replace('## Evidence and reproducibility','[Independent E2 audit](E2_AUDIT.json): PASS for artifact bindings, query/support reconstruction, probability checks and timing arithmetic. Timings were not replayed.\n\n## Evidence and reproducibility')
    if prescreen_audit_path:
        report=report.replace('## E1B: smaller CPU foundation-model prescreen','## E1B: smaller CPU foundation-model prescreen\n\n[Independent E1B calculation audit](E1B_AUDIT.json): PASS. This verifies the recorded evidence and calculations; it does not turn the prescreen into independent validation or a full E1 result.')
    (output/'REPORT.md').write_text(report,encoding='utf-8')
    links=check_links(output,pending=('PUBLICATION.json',))
    files={name:{'sha256':sha(output/name),'bytes':(output/name).stat().st_size} for name in sorted(allowed-{'PUBLICATION.json'})}
    batch=full_batch_status(a)
    receipt={'schema_version':1,'scientific_runtime_commit':commit,'files':files,'local_markdown_links_checked':links,
             'self_hash_policy':'PUBLICATION.json is intentionally excluded from its own hash list.',
             'source_aggregate_hashes':source_receipts,'private_inputs_modified':False,'scientific_fits_performed':0,
             'e1_primary_status':batch['e1'],'e4_primary_status':batch['e4'],'e1_full_batch':batch,
             'e3_screen_status':summary['screen_status']}
    if e2:receipt['e2_cpu_necessary_condition_status']=e2['decision']['status']
    if prescreen:receipt['e1b_prescreen_status']=prescreen['primary_descriptive']['status']
    if prescreen_audit_path:receipt['e1b_audit_status']=prescreen_audit['audit_status']
    (output/'PUBLICATION.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    for name,record in files.items():require(sha(output/name)==record['sha256'],'Public artifact changed during publication')
    require(check_links(output)==links,'Publication links changed during assembly')
    return {'public_files':len(files)+1,'markdown_links_verified':len(links),'e1_completed_cells':a['completed_cell_count'],'e3_cells':len(results['rows']),'e1_primary':batch['e1'],'e4_primary':batch['e4'],'e3':summary['screen_status'],'e1b':prescreen['primary_descriptive']['status'] if prescreen else 'NOT_COMPLETED'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--e1-analysis',type=Path,required=True)
    parser.add_argument('--e1-run',type=Path,action='append',required=True)
    parser.add_argument('--e3-run',type=Path,required=True);parser.add_argument('--e3-audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--e2',type=Path)
    parser.add_argument('--e2-frozen-commit',default='431e783');parser.add_argument('--prescreen',type=Path)
    parser.add_argument('--e2-audit',type=Path)
    parser.add_argument('--prescreen-audit',type=Path)
    parser.add_argument('--prescreen-frozen-commit','--e1b-commit',dest='prescreen_frozen_commit')
    parser.add_argument('--frozen-commit',default=DEFAULT_COMMIT)
    args=parser.parse_args()
    print(json.dumps(publish(args.repo,args.e1_analysis,args.e1_run,args.e3_run,args.e3_audit,args.output,frozen_commit=args.frozen_commit,e2_path=args.e2,e2_frozen_commit=args.e2_frozen_commit,e2_audit_path=args.e2_audit,prescreen_path=args.prescreen,prescreen_frozen_commit=args.prescreen_frozen_commit,prescreen_audit_path=args.prescreen_audit),indent=2))
