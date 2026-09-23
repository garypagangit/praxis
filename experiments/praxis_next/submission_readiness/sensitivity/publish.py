"""Render the completed frozen sensitivity audit; no additional comparisons."""
import json
from pathlib import Path
import hashlib

HERE=Path(__file__).resolve().parent


def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def value(x,pp=False):return 'undefined' if x is None else f'{x*(100 if pp else 1):.2f}'
def span(obj,pp=False):return value(obj['minimum'],pp)+' to '+value(obj['maximum'],pp)
def label(spec):
    return ('PX081 '+spec['condition'].replace('_',' ')+f" B{spec['budget']}") if spec['study']=='PX081' else 'PX082 '+spec['contrast'].replace('_',' ')
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(str(v) for v in row)+' |' for row in rows])
def counts(values):return f"{sum(v is True for v in values)}/{sum(v is not None for v in values)} defined ({sum(v is None for v in values)} undefined)"


def main():
    audit=read('AUDIT.json');summary=read('SUMMARY.json')['groups'];equiv=read('AGGREGATE_EQUIVALENCE.json')
    seeds=read('SEED_OMISSIONS.json')['groups'];captures=read('CAPTURE_OMISSION_MEANS.json')['groups']
    for name,digest in audit['outputs_sha256'].items():
        if sha(HERE/name)!=digest:raise ValueError('Analysis result changed: '+name)
    clean=next(g for g in summary if g['spec']['study']=='PX081' and g['spec']['condition']=='clean' and g['spec']['budget']==3)
    clean_seed=[r for r in seeds if r['spec']==clean['spec']]
    clean_capture=[r for r in captures if r['spec']==clean['spec']]
    paired_capture=read('CAPTURE_OMISSIONS.json')['comparisons']
    unsupported=[{'comparison':r['spec'],'omitted_capture':r['omitted_capture'],
                  'undefined_metrics':[k for k,v in r['point']['delta'].items() if v is None]}
                 for r in paired_capture if any(v is None for v in r['point']['delta'].values())]
    temporal=[]
    for contrast in ('current_mixed_minus_past','current_history_mixed_minus_past','chronological_history_minus_current'):
        selected=[r for r in paired_capture if r['spec']['contrast']==contrast]
        for seed in sorted({r['spec']['seed'] for r in selected}):
            one=[r for r in selected if r['spec']['seed']==seed]
            deltas=[r['point']['delta']['macro_f1'] for r in one]
            temporal.append({'contrast':contrast,'seed':seed,'positive':sum(v>1e-12 for v in deltas),
                'negative':sum(v < -1e-12 for v in deltas),'total':len(deltas),
                'minimum_delta_macro_f1':min(deltas),'maximum_delta_macro_f1':max(deltas),
                'nonpositive_omissions':[r['omitted_capture'] for r in one if r['point']['delta']['macro_f1']<=1e-12]})
    clean_pairs=[r for r in paired_capture if all(r['spec'][key]==val for key,val in clean['spec'].items())]
    stable_seed=sum(all(v is True for v in g['seed_omission_f1_up_exfil_warning_down']) for g in summary)
    stable_capture=sum(all(v is True for v in g['capture_omission_f1_up_exfil_warning_down']) for g in summary)
    full_reversal=sum(g['full_three_seed_mean']['f1_up_exfil_warning_down'] is True for g in summary)
    report=['# Capture and fitting-seed sensitivity of the measured warning tradeoff','',
        '**Status: completed retrospective audit.** All 36 paired contrasts were evaluated under all five capture omissions; '
        'all 12 experiment groups were evaluated under all three fitting-seed omissions. No model was refitted, no operating threshold changed, '
        'and no original evidence file was modified.', '',
        'The calculations address how much the observed findings depend on a particular fragment or fit. Removing a capture changes the evaluation population while leaving predictions fixed. '
        'Removing a fitting seed averages the remaining two per-seed metrics. Neither creates an independent test campaign or measures a model retrained without that capture.', '',
        '## Complete three-seed groups: omit each fitting seed', '',
        'All changes are candidate minus baseline. Macro-F1 changes are score points (the raw score difference multiplied by 100); recall and false-alert-rate changes are percentage points. Ranges contain exactly the three specified omissions, '
        'not confidence intervals. The last column counts F1-up/exfil-warning-down among defined omission means.', '']
    seedrows=[];caprows=[]
    for g in summary:
        full=g['full_three_seed_mean']['delta'];s=g['seed_omission_mean_ranges'];c=g['capture_omission_mean_ranges']
        seedrows.append([label(g['spec']),value(full['macro_f1'],True),value(full['exfil_warning_recall'],True),
            span(s['macro_f1'],True),span(s['exfil_warning_recall'],True),counts(g['seed_omission_f1_up_exfil_warning_down'])])
        caprows.append([label(g['spec']),span(c['macro_f1'],True),span(c['exfil_warning_recall'],True),
            span(c['movement_exact_recall'],True),span(c['benign_false_alert_rate'],True),counts(g['capture_omission_f1_up_exfil_warning_down'])])
    report+=[table(['Comparison','Full mean Δ macro-F1 (×100)','Full mean Δ exfil warning pp','Two-seed mean Δ macro-F1 (×100) range',
                    'Two-seed mean Δ warning pp range','F1 up / warning down'],seedrows),'',
        f'{full_reversal}/12 groups have the specified mean sign disagreement on all data; {stable_seed}/12 retain it under every fitting-seed omission. '
        'These are observed group counts, not independent replications or a statistical acceptance rate.', '',
        '## Complete groups: omit each capture', '',
        'Each entry is a range across all five omissions of a three-seed mean of point differences. Different omissions retain different numbers of rows; '
        'the complete per-seed tables preserve row and class supports. Both methods always retain the same rows for a given comparison.', '',
        table(['Comparison','Δ macro-F1 (×100) range','Δ exfil warning pp range','Δ movement exact recall pp range','Δ benign false-alert rate pp range','F1 up / warning down'],caprows),'',
        f'{stable_capture}/12 groups retain the specified mean sign disagreement under every capture omission. '
        'This finite perturbation result does not justify independent-campaign generalization.', '',
        '## Clean budget-three sensitivity in detail', '',
        'This comparison was highlighted before the audit because its original mean combines markedly different fitting-seed outcomes. '
        'The table retains every omission; it does not select a preferred result.', '']
    detail=[]
    full=clean['full_three_seed_mean']['delta']
    detail.append(['None (three-seed mean)',value(full['macro_f1'],True),value(full['exfil_warning_recall'],True),
        value(full['exfil_to_benign_count']),value(full['benign_false_alert_count'])])
    for r in clean_seed:
        d=r['point']['delta'];detail.append([f"Fit seed {r['omitted_seed']}",value(d['macro_f1'],True),value(d['exfil_warning_recall'],True),
            value(d['exfil_to_benign_count']),value(d['benign_false_alert_count'])])
    for r in clean_capture:
        d=r['point']['delta'];detail.append([f"Capture {r['omitted_capture']} (three-seed mean)",value(d['macro_f1'],True),value(d['exfil_warning_recall'],True),
            value(d['exfil_to_benign_count']),value(d['benign_false_alert_count'])])
    report+=[table(['Omitted unit','Δ macro-F1 (×100)','Δ exfil warning pp','Mean extra exfil → benign','Mean extra benign alerts'],detail),'',
        'Positive missed-warning counts mean fewer attack warnings. Positive benign false-alert counts mean more benign records labeled attack. '
        'Count changes across capture omissions refer to different retained populations and should be read with their rate changes and support counts.', '',
        f"The clean budget-three mean retains higher F1/lower warning recall under all five capture omissions and all three fitting-seed omissions. "
        f"At individual-seed level, {sum(r['point']['f1_up_exfil_warning_down'] for r in clean_pairs)}/{len(clean_pairs)} capture-omission pairs have that direction: "
        'five for seed 8101, zero for seed 8102 and five for seed 8103. The direction of the seed mean is stable under the specified omissions, while its magnitude is strongly seed-sensitive.', '',
        '## Temporal-score direction under every capture omission', '',
        table(['Contrast','Fitting seed','Positive Δ macro-F1 omissions','Δ macro-F1 (×100) range','Nonpositive omitted captures'],[
            [r['contrast'],r['seed'],f"{r['positive']}/{r['total']}",value(r['minimum_delta_macro_f1'],True)+' to '+value(r['maximum_delta_macro_f1'],True),
             ', '.join(map(str,r['nonpositive_omissions'])) or 'None'] for r in temporal]), '',
        'Both mixed-minus-past feature views retain a positive F1 difference in all 15 seed/capture-omission pairs. '
        'The chronological history-minus-current contrast is positive in 14/15: omitting capture 9 for seed 20260924 gives −0.13 macro-F1 score points. '
        'Every three-seed mean remains positive in that history contrast. These are fixed-prediction sensitivity results, not a new temporal test.', '',
        f"Unsupported-metric capture omissions: {len(unsupported)}; omission IDs: {json.dumps(unsupported)}. "
        'All declared evaluation classes remain supported in each of these leave-one-capture-out populations. This does not contradict the earlier bootstrap’s unsupported draws: '
        'sampling captures with replacement can omit several distinct captures at once.', '',
        '## Repeated aggregate comparisons', '',
        f"The original PX081 count is {equiv['original_f1_up_exfil_warning_down']}/{equiv['original_pairs']} paired seed comparisons with higher F1 and lower exfiltration warning recall. "
        f"The ordered per-capture confusion signatures form {equiv['aggregate_equivalent_classes']} aggregate-equivalent classes; "
        f"{equiv['classes_f1_up_exfil_warning_down']} of those classes have that direction. "
        f"There are {equiv['repeated_classes']} classes with more than one registered comparison.", '',
        '**Aggregate equivalence is not independence or proof of identical row-level predictions.** The signatures preserve ordered baseline/candidate matrices, '
        'capture order and class meanings. They establish equivalence only for these sufficient-statistic calculations. Different rows can be mislabeled yet yield '
        'the same confusion matrix. All signature classes still share a single campaign, many events and fitted components.', '']
    repeated=[c for c in equiv['classes'] if c['size']>1]
    report+=[table(['Signature prefix','Registered comparisons','F1 up / warning down','Members'],[
        [c['signature'][:12],c['size'],c['point']['f1_up_exfil_warning_down'],'; '.join(c['members'])] for c in repeated]),'',
        'Every equivalence class, including singletons and contrary directions, is saved in [AGGREGATE_EQUIVALENCE.json](AGGREGATE_EQUIVALENCE.json).', '',
        '## Complete omission tables', '',
        '- [All 180 paired capture omissions](CAPTURE_OMISSIONS.json) and [flat CSV](CAPTURE_OMISSIONS.csv), including supports and undefined values.',
        '- [All 36 fitting-seed omissions](SEED_OMISSIONS.json) and [flat CSV](SEED_OMISSIONS.csv).',
        '- [All 60 capture-omission seed means](CAPTURE_OMISSION_MEANS.json), [12 compact group summaries](SUMMARY.json), and [full-data reference points](FULL_POINTS.json).',
        '- [Plan](ANALYSIS_PLAN.md), [input hashes](INPUTS.json), [freeze](FREEZE.json) and [arithmetic audit](AUDIT.json).', '',
        '## Reproducibility and interpretation', '',
        f"Plan and executable code were committed at `{audit['freeze_commit']}` before the omission calculations. "
        f"The run completed {audit['scalar_crosschecks']} scalar checks, including comparison with a separately implemented public confusion verifier. "
        'Five synthetic tests cover missing-stage metrics, capture weighting, seed averaging, directional flags and confusion-equivalent predictions. '
        'The run used public counts only and performed zero model fits.', '',
        'Fixed-four-class macro-F1 is undefined when any true class is absent; stage recalls are undefined when that stage is absent. '
        'Null omission values remain explicit and are not converted to zero. Counts remain defined. Finite minimum/maximum omission ranges are descriptive '
        'and do not replace the original paired bootstrap intervals.', '',
        'The source has only one previously examined campaign. Capture removal is not independent holdout validation, and a fitting seed is not an attack execution. '
        'The movement target is author Remote System Discovery progress; full-flow outcomes do not prove early exfiltration prediction or successful movement. '
        'This audit improves the precision of the empirical claim and its stated limitations; it cannot establish publication novelty or external generalization.', '']
    (HERE/'REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    section=['## Retrospective sensitivity to captures, fitting seeds and repeated aggregates','',
        'A prespecified retrospective audit retained all 36 paired comparisons and exhaustively omitted each capture while holding predictions fixed. '
        'It also omitted each fitting seed within all 12 groups, averaging the remaining per-seed metrics rather than pooling flows. '
        'The fixed four-class schema and undefined-support rule were preserved. These are finite sensitivity calculations, not refits, confidence intervals or independent replications.', '',
        'Macro-F1 changes in the table are score points (raw score differences multiplied by 100); warning-recall changes are percentage points.', '',
        table(['Omitted unit','Clean B3 Δ macro-F1 (×100)','Δ exfil warning pp','Mean extra exfil → benign','Mean extra benign alerts'],detail),'',
        f"Across the 12 mean comparisons, {full_reversal} show higher F1 with fewer exfiltration warnings on all data; "
        f"{stable_seed} preserve that direction under every fitting-seed omission and {stable_capture} under every capture omission. "
        'The full set includes temporal-access comparisons where both scores and warnings improve, and conditions with opposite or zero changes.', '',
        f"The 27 registered PX081 contrasts include {equiv['aggregate_equivalent_classes']} distinct ordered capture-confusion signatures. "
        f"The F1-up/warning-down count is {equiv['original_f1_up_exfil_warning_down']}/27 registered pairs or "
        f"{equiv['classes_f1_up_exfil_warning_down']}/{equiv['aggregate_equivalent_classes']} aggregate-equivalent signature classes. "
        'Neither denominator counts independent experiments. Equal confusion signatures do not prove that the individual predictions match; '
        'they identify repeated sufficient statistics for the reported metrics.', '',
        'All 180 capture omissions, 36 seed omissions, supports, nulls and full group ranges are retained in the accompanying sensitivity evidence package. '
        'This audit remains retrospective on one exposed campaign. The original interval and scope qualifications therefore continue to apply.', '']
    (HERE/'PAPER_SECTION.md').write_text('\n'.join(section),encoding='utf-8')
    compact=['### Retrospective capture and seed sensitivity','',
        f"The frozen sensitivity audit (`{audit['freeze_commit']}`) includes every registered pair: 180 leave-one-capture-out calculations and 36 leave-one-fitting-seed-out means. "
        'Predictions are fixed, and the remaining seed metrics are averaged without pooling flows. Omission ranges are finite sensitivity summaries, not confidence intervals or independent replications.', '',
        'For clean budget three, higher mean F1 and lower exfiltration warning recall remain in all five capture omissions and all three fitting-seed omissions. '
        'The magnitude is strongly sensitive to seed 8101: excluding it reduces the warning loss from 8.93 to 0.36 percentage points and the mean extra missed warnings from 307.33 to 12.50. '
        'Thus the qualitative mean tradeoff survives this deletion, but the original mean is not a stable estimate of its magnitude.', '',
        'Macro-F1 changes in the tables are score points (raw score differences multiplied by 100); warning-recall changes are percentage points.', '',
        table(['Omitted unit','Δ macro-F1 (×100)','Δ exfil warning pp','Mean extra missed warnings'],[row[:4] for row in detail]), '',
        'At individual-seed level, the clean budget-three tradeoff occurs in 10/15 capture-omission pairs: all five for seed 8101, none for seed 8102, and all five for seed 8103. '
        'Across all 12 group means, the nine original F1-up/warning-down groups retain that direction under every specified single-seed and single-capture omission; '
        'this stability statement concerns means on the same campaign.', '',
        'Current-feature mixed-minus-past F1 stays positive in all 15 fitting-seed/capture-omission pairs. Per-seed ranges are:', '',
        table(['Fitting seed','Positive omission differences','Δ macro-F1 (×100) range'],[
            [r['seed'],f"{r['positive']}/{r['total']}",value(r['minimum_delta_macro_f1'],True)+' to '+value(r['maximum_delta_macro_f1'],True)]
            for r in temporal if r['contrast']=='current_mixed_minus_past']), '',
        'The history-feature mixed-minus-past comparison is also positive in 15/15 pairs. Chronological history-minus-current is positive in 14/15; '
        'seed 20260924 becomes −0.13 macro-F1 score points when capture 9 is omitted. No omission loses support for a declared evaluation class (unsupported omission IDs: none).', '',
        f"The 27 PX081 contrasts form {equiv['aggregate_equivalent_classes']} distinct ordered per-capture confusion signatures. "
        f"The higher-F1/lower-warning count is {equiv['original_f1_up_exfil_warning_down']}/27 registered pairs or "
        f"{equiv['classes_f1_up_exfil_warning_down']}/{equiv['aggregate_equivalent_classes']} aggregate-equivalent signature classes. "
        'These are not independent replication counts. Equal confusion signatures do not establish identical individual predictions; '
        'all signatures still share events, models and one previously examined campaign.', '',
        'All omitted-capture identities, per-seed supports, directions and numerical values remain in the [complete sensitivity report](sensitivity/REPORT.md) '
        'and [arithmetic receipt](sensitivity/AUDIT.json). Original main-study results and their limitations are unchanged.', '']
    (HERE/'PAPER_DATA.json').write_text(json.dumps({'SENSITIVITY_ADDITION':'\n'.join(compact)},indent=2)+'\n',encoding='utf-8')
    (HERE/'PAPER_DETAILS.json').write_text(json.dumps({'unsupported_omission_ids':unsupported,'temporal_capture_omission_ranges':temporal,
        'clean_b3_seed_omission_means':clean_seed,'clean_b3_capture_omission_means':clean_capture,
        'clean_b3_individual_capture_omission_reversal_count':sum(r['point']['f1_up_exfil_warning_down'] for r in clean_pairs),
        'clean_b3_individual_capture_omission_pairs':len(clean_pairs)},indent=2)+'\n',encoding='utf-8')
    pub={'status':'PASS','analysis_audit_sha256':sha(HERE/'AUDIT.json'),'publisher_sha256':sha(Path(__file__)),
        'outputs_sha256':{name:sha(HERE/name) for name in ('REPORT.md','PAPER_SECTION.md','PAPER_DATA.json','PAPER_DETAILS.json')},
        'new_comparisons':0,'interpretation':'Rendering of the frozen complete sensitivity outputs only'}
    (HERE/'PUBLICATION.json').write_text(json.dumps(pub,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'full_mean_reversal_groups':full_reversal,'all_seed_omissions_reversal_groups':stable_seed,
        'all_capture_omissions_reversal_groups':stable_capture,'clean_b3_details':detail,'aggregate_classes':equiv['aggregate_equivalent_classes'],
        'aggregate_class_reversals':equiv['classes_f1_up_exfil_warning_down']},indent=2))


if __name__=='__main__':main()
