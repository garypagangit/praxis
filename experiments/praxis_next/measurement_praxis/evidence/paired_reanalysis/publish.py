"""Post-result rendering and mean audit; does not alter frozen analyses."""
from pathlib import Path
import json
import numpy as np

from reanalysis import HERE, NAMES, read, write, sha, flat_points


def fmt(value, percent=False):
    return f'{value*100:.2f}' if percent else f'{value:.4f}'


def ci(value, percent=False):
    if value['lower'] is None:return 'undefined'
    return f"[{fmt(value['lower'],percent)}, {fmt(value['upper'],percent)}]"


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(str(x) for x in row)+' |' for row in rows])


def subsets(results,group):
    return [i for i in results if all(i['spec'][k]==group[k] for k in ('study','contrast','condition','budget'))]


def audit_means(results,groups):
    checks=0
    for g in groups:
        items=subsets(results,g)
        assert len(items)==3
        for side in ('baseline','candidate'):
            flat=[flat_points(i['result'],side) for i in items]
            for key,got in g['means'][side].items():
                expected=sum(row[key] for row in flat)/3
                assert abs(expected-got)<1e-10,(key,expected,got)
                checks+=1
        for key,got in g['means']['delta'].items():
            direct=sum(flat_points(i['result'],'candidate')[key]-flat_points(i['result'],'baseline')[key] for i in items)/3
            assert abs(direct-got)<1e-10,(key,direct,got)
            checks+=1
        for stage,record in g['stages'].items():
            expected=sum(i['result']['paired_deltas']['delta_macro_f1']>1e-12 and
                         i['result']['paired_deltas']['stages'][stage]['delta_warning_recall'] < -1e-12 for i in items)
            assert expected==record['macro_f1_up_warning_down_seeds']
            checks+=1
    return checks


def stage_patterns(results):
    out={}
    for study in ('PX081','PX082'):
        selected=[i['result'] for i in results if i['spec']['study']==study]
        out[study]={}
        for stage in NAMES[1:]:
            macro_ci=lambda r:r['bootstrap']['intervals']['delta_macro_f1']
            warn_ci=lambda r:r['bootstrap']['intervals']['stages'][stage]['delta_warning_recall']
            out[study][stage]={
                'comparisons':len(selected),
                'macro_up_warning_down':sum(r['paired_deltas']['stages'][stage]['macro_f1_up_warning_down'] for r in selected),
                'macro_down_warning_up':sum(r['paired_deltas']['stages'][stage]['macro_f1_down_warning_up'] for r in selected),
                'warning_delta_interval_entirely_below_zero':sum(warn_ci(r)['upper'] is not None and warn_ci(r)['upper']<0 for r in selected),
                'macro_interval_positive_and_warning_interval_negative':sum(macro_ci(r)['lower'] is not None and warn_ci(r)['upper'] is not None and
                     macro_ci(r)['lower']>0 and warn_ci(r)['upper']<0 for r in selected)}
    return out


def make_figure(groups):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[1.65,1]},layout='constrained')
    for ax,study in zip(axes,('PX081','PX082')):
        selected=[g for g in groups if g['study']==study]
        labels=[]
        for i,g in enumerate(selected):
            labels.append((g['condition'].replace('_',' ')+' / budget '+str(g['budget'])) if study=='PX081' else
                {'current_mixed_minus_past':'Current: mixed − past','current_history_mixed_minus_past':'History: mixed − past',
                 'chronological_history_minus_current':'Past only: history − current'}[g['contrast']])
            ax.scatter(g['means']['delta']['macro_f1']*100,i-.12,color='#2563A6',marker='o',s=35,label='Macro-F1' if i==0 else None)
            ax.scatter(g['means']['delta']['DataExfiltration.warning_recall']*100,i+.12,color='#B64A32',marker='s',s=32,
                       label='Exfiltration warning recall' if i==0 else None)
        ax.set_yticks(range(len(selected)),labels,fontsize=8)
        ax.invert_yaxis();ax.axvline(0,color='#666666',linewidth=.9);ax.grid(axis='x',alpha=.2)
        ax.set_xlabel('Candidate − baseline (percentage points)')
        ax.set_title('PX081: harm − entropy' if study=='PX081' else 'PX082: paired contrasts')
        ax.spines[['top','right']].set_visible(False)
    axes[0].legend(loc='lower right',fontsize=8)
    fig.suptitle('F1 gains can coexist with lost attack warnings',fontsize=14)
    fig.savefig(HERE/'METRIC_DISAGREEMENT.png',dpi=180)
    fig.savefig(HERE/'METRIC_DISAGREEMENT.pdf')
    plt.close(fig)


def paper_data(results,groups,patterns):
    temporal=[i for i in results if i['spec']['study']=='PX082' and i['spec']['contrast']!='chronological_history_minus_current']
    rows=[]
    for i in temporal:
        s=i['spec'];r=i['result'];d=r['paired_deltas'];iv=r['bootstrap']['intervals']
        rows.append(['Current' if s['contrast'].startswith('current_mixed') else 'Current + history',s['seed'],
            fmt(d['delta_macro_f1'],True),ci(iv['delta_macro_f1'],True),
            fmt(d['stages']['DataExfiltration']['delta_warning_recall'],True)])
    temporal_text='\n\n'.join([
        'The complete retrospective reanalysis gives positive current-feature macro-F1 differences in all three seeds, with each descriptive capture interval above zero. '
        'For current-plus-history, all point differences are positive, but the final seed interval spans zero. The intervals vary widely because the resampling units '
        'are only five capture fragments from the same campaign; they do not establish a population-wide inflation factor.',
        table(['Features','Fitting seed','Δ macro-F1 (pp)','95% paired interval (pp)','Δ exfil warning (pp)'],rows),
        'For every comparison, 1,981 of 2,000 draws support fixed-four-class macro-F1 and movement recall; 19 draws omit the true movement class and are excluded from those intervals. '
        'All 2,000 draws support exfiltration warning recall and benign false-alert rate. The same capture multiplicities are reused across all seeds and contrasts. '
        'These new support-conditional intervals are distinct from the original temporal experiment’s 1,000-draw bootstrap. '
        'Every stage, count and paired interval is retained in [the complete reanalysis](evidence/paired_reanalysis/REPORT.md).'])
    acquisition=[g for g in groups if g['study']=='PX081']
    rows=[]
    for g in acquisition:
        rows.append([g['condition'].replace('_',' '),g['budget'],fmt(g['means']['delta']['macro_f1'],True),
            fmt(g['means']['delta']['DataExfiltration.warning_recall'],True),
            f"{g['means']['delta']['DataExfiltration.attack_to_benign_count']:.2f}",g['stages']['DataExfiltration']['macro_f1_up_warning_down_seeds']])
    p=patterns['PX081']['DataExfiltration']
    clean=[i for i in results if i['spec']['study']=='PX081' and i['spec']['condition']=='clean' and i['spec']['budget']==3]
    detail=[]
    for i in clean:
        s=i['spec'];r=i['result'];d=r['paired_deltas'];a=r['baseline']['stages']['DataExfiltration'];b=r['candidate']['stages']['DataExfiltration'];iv=r['bootstrap']['intervals']
        detail.append([s['seed'],fmt(d['delta_macro_f1'],True),f"{a['attack_to_benign_count']} → {b['attack_to_benign_count']}",
            f"{a['support']-a['correct_count']} → {b['support']-b['correct_count']}",
            fmt(d['stages']['DataExfiltration']['delta_warning_recall'],True)+' '+ci(iv['stages']['DataExfiltration']['delta_warning_recall'],True)])
    warning_text='\n\n'.join([
        f"Across all registered conditions and budgets, {p['macro_up_warning_down']} of 27 paired seed comparisons raise macro-F1 while reducing exfiltration warning recall. "
        f"In {p['macro_interval_positive_and_warning_interval_negative']} of 27, the descriptive macro-F1 interval lies above zero and the warning-recall interval below zero. "
        'These comparisons share data and fitted components; budget-one clean and wrong-history outcomes are identical because that budget cannot acquire history. '
        'They are correlated repetitions of specified comparisons, not 27 independent tests or campaigns.',
        table(['Condition','Budget','Mean Δ F1 (pp)','Mean Δ exfil warning (pp)','Mean extra lost warnings','F1 up / warning down seeds'],rows),
        'Clean budget-three means conceal marked fitting-seed variation. Exfiltration-to-benign counts range from 203 to 1,105 for entropy and 206 to 1,127 for harm. '
        'The paired increases are 897, 3 and 22 lost warnings, respectively (mean 307.33). Macro-F1 improves in two seeds and declines slightly in one. '
        'For seed 8101, exact exfiltration errors change only from 1,122 to 1,130, while wrong-attack-stage predictions fall from 900 to 11 and benign predictions rise from 222 to 1,119. '
        'This concrete error-destination shift explains why nearly unchanged exact exfiltration recall can coexist with a large loss of warnings. It does not identify a generally effective policy.',
        table(['Seed','Δ F1 (pp)','Exfil → benign','All exact exfil errors','Δ warning pp [95% paired interval]'],detail),
        'All three attack stages, including zero changes and reverse directions, are included in [the complete paired table](evidence/paired_reanalysis/PAIRED_METRICS.csv). '
        'The full set was specified before this reanalysis, after selected warning-loss observations had already been inspected; it remains retrospective.'])
    history=[i for i in results if i['spec']['contrast']=='chronological_history_minus_current']
    rows=[]
    for i in history:
        s=i['spec'];r=i['result'];d=r['paired_deltas'];iv=r['bootstrap']['intervals'];a=r['baseline']['stages']['DataExfiltration'];b=r['candidate']['stages']['DataExfiltration']
        rows.append([s['seed'],fmt(d['delta_macro_f1'],True)+' '+ci(iv['delta_macro_f1'],True),
            f"{a['attack_to_benign_count']} → {b['attack_to_benign_count']}",
            fmt(d['stages']['DataExfiltration']['delta_warning_recall'],True)+' '+ci(iv['stages']['DataExfiltration']['delta_warning_recall'],True)])
    history_text='\n\n'.join([
        'On the same 1,722 exfiltration-labeled anchor rows, adding history increases benign predictions by 7, 6 and 8 across the three fitting seeds. '
        'Mean warning recall decreases by 0.41 percentage points, while macro-F1 rises by 2.17 points. This is a much smaller warning loss than the acquisition contrast. '
        'Only the final seed’s warning-difference interval excludes zero; the other two include zero. Both favorable and unfavorable outcomes should be read at that scale.',
        table(['Fitting seed','Δ macro-F1 pp [95% interval]','Exfil → benign, current → history','Δ exfil warning pp [95% interval]'],rows),
        'Intervals for the added missed-warning counts are [0, 17], [0, 14] and [1, 17], respectively. They reuse the same capture draws as the temporal contrasts. '
        'These are descriptive fragment-resampling intervals, not independent-campaign or prospective validation. '
        'The [reanalysis audit](evidence/paired_reanalysis/AUDIT.json) verifies unchanged input hashes, paired identities and independently recomputed arithmetic.'])
    write(HERE/'PAPER_DATA.json',dict(TEMPORAL_UNCERTAINTY=temporal_text,WARNING_REANALYSIS=warning_text,HISTORY_REANALYSIS=history_text))


def main():
    results=read(HERE/'PAIRED_RESULTS.json')['results'];groups=read(HERE/'MEANS.json')['groups']
    meanchecks=audit_means(results,groups);patterns=stage_patterns(results)
    write(HERE/'DIRECTION_COUNTS.json',patterns)
    lines=['# Retrospective paired reanalysis: stage scores and lost warnings',
        '', '**Status:** all 36 comparisons completed; all 66 private probability archives match their original receipts. '
        'No new fits. The frozen analysis commit is `c0d884e`. This is a retrospective measurement analysis of previously examined results, not independent confirmation.',
        '', 'An incorrect attack-stage name can still alert an analyst. Predicting benign for a true attack removes that warning. '
        'The tables report these separately. Positive F1/recall deltas are favorable; positive missed-warning or false-alert counts are unfavorable.',
        '', '## Complete seed-mean results', '', 'These are arithmetic point means across three fitting seeds. There is no confidence interval for a pooled seed mean. '
        'PX081 uses 208,094 rows (35 author movement events); PX082 uses the identical 104,051-row common anchor across all paired arms (18 movement events).', '']
    rows=[]
    for g in groups:
        m=g['means'];label=(g['condition']+f" / B{g['budget']}") if g['study']=='PX081' else g['contrast']
        rows.append([g['study'],label,fmt(m['baseline']['macro_f1'])+' → '+fmt(m['candidate']['macro_f1']),
            fmt(m['delta']['macro_f1'],True),fmt(m['baseline']['DataExfiltration.warning_recall'],True)+' → '+fmt(m['candidate']['DataExfiltration.warning_recall'],True),
            f"{m['baseline']['DataExfiltration.attack_to_benign_count']:.2f} → {m['candidate']['DataExfiltration.attack_to_benign_count']:.2f}",
            f"{m['baseline']['benign_false_alert_count']:.2f} → {m['candidate']['benign_false_alert_count']:.2f}",
            g['stages']['DataExfiltration']['macro_f1_up_warning_down_seeds']])
    lines += [table(['Study','Contrast / condition','Macro-F1','Δ F1 (pp)','Exfil warning recall (%)','Exfil → benign mean count','Benign false alerts mean','F1 up / warning down seeds'],rows),
        '', 'For PX081 the candidate is harm and baseline is entropy. For PX082 mixed-minus-past, future-training exposure is deliberate protocol sensitivity, not deployment-valid improvement.',
        '', '## Complete warning/recognition decomposition by stage', '']
    rows=[]
    for g in groups:
        m=g['means'];label=(g['condition']+f" / B{g['budget']}") if g['study']=='PX081' else g['contrast']
        for stage in NAMES[1:]:
            rows.append([g['study']+' '+label,stage,g['stages'][stage]['support'],
                fmt(m['baseline'][stage+'.exact_stage_recall'],True)+' → '+fmt(m['candidate'][stage+'.exact_stage_recall'],True),
                fmt(m['baseline'][stage+'.warning_recall'],True)+' → '+fmt(m['candidate'][stage+'.warning_recall'],True),
                f"{m['baseline'][stage+'.attack_to_benign_count']:.2f} → {m['candidate'][stage+'.attack_to_benign_count']:.2f}",
                f"{m['baseline'][stage+'.wrong_attack_stage_count']:.2f} → {m['candidate'][stage+'.wrong_attack_stage_count']:.2f}"])
    lines += [table(['Contrast','Stage','Support','Exact recall (%)','Warning recall (%)','Attack → benign','Wrong attack stage'],rows),
        '', '## Per-seed paired macro-F1 and exfiltration-warning differences', '',
        'Brackets are descriptive 95% paired capture-percentile intervals. They resample the same five fragments from one campaign. '
        'They do not quantify independent-campaign generalization or constitute confirmatory tests. All rate/count/stage intervals are in PAIRED_METRICS.csv.', '']
    rows=[]
    for i in results:
        s=i['spec'];r=i['result'];d=r['paired_deltas'];iv=r['bootstrap']['intervals']
        label=(s['condition']+f" / B{s['budget']}") if s['study']=='PX081' else s['contrast']
        rows.append([s['study']+' '+label,s['seed'],fmt(d['delta_macro_f1'],True)+' '+ci(iv['delta_macro_f1'],True),
            fmt(d['stages']['DataExfiltration']['delta_warning_recall'],True)+' '+ci(iv['stages']['DataExfiltration']['delta_warning_recall'],True),
            d['stages']['DataExfiltration']['delta_attack_to_benign_count'],
            iv['delta_macro_f1']['valid_replicates'],iv['stages']['DataExfiltration']['delta_warning_recall']['valid_replicates']])
    lines += [table(['Contrast','Seed','Δ macro-F1 pp [interval]','Δ exfil warning pp [interval]','Δ exfil → benign','F1 valid draws','Exfil valid draws'],rows),
        '', '## Complete directional counts', '']
    rows=[]
    for study,stages in patterns.items():
        for stage,p in stages.items():rows.append([study,stage,p['comparisons'],p['macro_up_warning_down'],p['macro_down_warning_up'],
            p['warning_delta_interval_entirely_below_zero'],p['macro_interval_positive_and_warning_interval_negative']])
    lines += [table(['Study','Stage','Pairs','F1 up / warning down','F1 down / warning up','Warning interval below 0','F1 interval above 0 + warning below 0'],rows),
        '', 'Counts of interval directions are descriptive; the pairs share rows and models and are not independent replications.',
        '', '## Uncertainty, verification and practical limits', '',
        'One row-bound bootstrap plan per cohort is shared across every comparison and fitting seed. The two cohorts use identical capture multiplicities '
        '(2,000 draws, seed 20260923). Stage rates/F1 are undefined in draws lacking their true stage; fixed-four-class macro-F1 needs every true class. '
        'Every interval reports valid/undefined draws. Count intervals remain defined at zero stage support. Original PX082 intervals are unchanged; '
        'these new intervals use a different declared support convention and shared resampling plan.', '',
        'The source is a previously exposed single UNRAVELED campaign. Five captures are fragments of that campaign, not five independent attacks. '
        'The author movement label is Remote System Discovery progress on one host pair. Completed flows do not demonstrate early prediction, confirmed movement, '
        'or confirmed data theft. PX081 collection costs/availability are simulated; PX082 future-training arms intentionally violate chronological deployment. '
        'These findings establish a concrete measurement disagreement on this benchmark, not a generally superior detector or novel universal metric.', '',
        f'Independent vectorized confusion arithmetic checked 720 point/interval quantities; a separate publication audit checked {meanchecks} mean/direction quantities. '
        'This verifies arithmetic and saved-source identity, not human label correctness. All 20 relevant synthetic/helper tests passed before freeze.', '',
        '## Artifacts', '',
        '- [Analysis plan](ANALYSIS_PLAN.md), [freeze](FREEZE.json), [input provenance](INPUTS.json), [arithmetic audit](AUDIT.json).',
        '- [All paired metrics](PAIRED_RESULTS.json), [flat paired metrics and CIs](PAIRED_METRICS.csv).',
        '- [Three-seed means](MEANS.json), [flat means](MEANS.csv), [direction counts](DIRECTION_COUNTS.json).',
        '- [Capture sufficient statistics](CAPTURE_CONFUSIONS.json), [shared capture draws](CAPTURE_DRAWS.json).',
        '- [Figure](METRIC_DISAGREEMENT.png), [vector figure](METRIC_DISAGREEMENT.pdf).', '']
    (HERE/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    make_figure(groups)
    section=['## Retrospective paired analysis of stage recognition and warnings','',
        'We reanalyzed unchanged probabilities after observing selected warning-recall differences. The complete plan was frozen at commit `c0d884e` before this reanalysis, '
        'but it is not an original preregistration or independent confirmation. All 27 entropy-versus-harm PX081 pairs and all nine common-anchor PX082 pairs were retained. '
        'No new models, thresholds or calibration were fitted. Warning recall means any nonbenign prediction among the true events of one attack stage; '
        'it distinguishes an incorrect attack name from an absent warning.', '',
        'One 2,000-draw paired capture-bootstrap plan (seed 20260923) was reused across all seeds and comparisons on each cohort. The plans share capture multiplicities '
        'and preserve whole fragments and unequal fragment sizes. Intervals are descriptive, conditional on this single campaign; absent-stage rate draws are marked '
        'undefined and excluded transparently. Seed means are point summaries, never pooled-row confidence intervals.', '',
        '### Complete mean effects', '',
        table(['Study / contrast','Δ macro-F1 pp','Δ exfil warning pp','Δ exfil → benign mean','F1 up / warning down seeds'],[
            [g['study']+' '+((g['condition']+f" B{g['budget']}") if g['study']=='PX081' else g['contrast']),
             fmt(g['means']['delta']['macro_f1'],True),fmt(g['means']['delta']['DataExfiltration.warning_recall'],True),
             f"{g['means']['delta']['DataExfiltration.attack_to_benign_count']:.2f}",g['stages']['DataExfiltration']['macro_f1_up_warning_down_seeds']] for g in groups]),'',
        '### Exact per-seed intervals and counts for manuscript tables', '']
    for study in ('PX081','PX082'):
        p=patterns[study]['DataExfiltration']
        section.append(f"{study}: {p['macro_up_warning_down']}/{p['comparisons']} pairs increase macro-F1 and reduce exfiltration warning recall at the point estimate; "
                       f"{p['warning_delta_interval_entirely_below_zero']}/{p['comparisons']} warning-difference intervals are entirely below zero; "
                       f"{p['macro_interval_positive_and_warning_interval_negative']}/{p['comparisons']} simultaneously have a macro-F1 interval above zero and warning interval below zero. "
                       'These are correlated descriptive comparisons, not counts of independent confirmations.')
        section.append('')
    detailed=[i for i in results if i['spec']['study']=='PX082' or (i['spec']['condition']=='clean' and i['spec']['budget']==3)]
    rows=[]
    for i in detailed:
        s=i['spec'];r=i['result'];d=r['paired_deltas'];iv=r['bootstrap']['intervals']
        before=r['baseline']['stages']['DataExfiltration'];after=r['candidate']['stages']['DataExfiltration']
        rows.append([s['study']+' '+('clean B3 harm−entropy' if s['study']=='PX081' else s['contrast']),s['seed'],
            fmt(d['delta_macro_f1'],True)+' '+ci(iv['delta_macro_f1'],True),
            fmt(d['stages']['DataExfiltration']['delta_warning_recall'],True)+' '+ci(iv['stages']['DataExfiltration']['delta_warning_recall'],True),
            f"{before['attack_to_benign_count']} → {after['attack_to_benign_count']}",
            f"{before['support']-before['correct_count']} → {after['support']-after['correct_count']}",
            f"{before['wrong_attack_stage_count']} → {after['wrong_attack_stage_count']}"])
    section += [table(['Comparison','Seed','Δ macro-F1 pp [95%]','Δ exfil warning pp [95%]','Exfil → benign','All exact exfil errors','Other attack label'],rows),'',
        '### Interpretation', '',
        'The defensible contribution is an applied measurement result: aggregate stage scores and attack-warning retention can recommend different choices on the same events. '
        'An F1 gain alone therefore does not establish that analysts retain more warnings. This does not make warning recall a novel metric or prove which operating point '
        'is best in a real organization. Report the stage decomposition together with benign false alerts and the intended operational objective.', '',
        'Chronological history comparisons assess context under past-only training; time-mixed comparisons intentionally expose future events and measure evaluation-protocol sensitivity. '
        'The author movement annotations are Remote System Discovery progress, and full-flow features cannot establish early exfiltration warning. '
        'The same previously exposed campaign underlies both cohorts. Dataset breadth and a genuinely fresh execution remain necessary before claiming generalization.', '',
        'Complete results, every stage and count interval, supports, shared draws and receipts are in [REPORT.md](REPORT.md), [PAIRED_METRICS.csv](PAIRED_METRICS.csv), '
        '[PAIRED_RESULTS.json](PAIRED_RESULTS.json) and [AUDIT.json](AUDIT.json).', '']
    (HERE/'PAPER_SECTION.md').write_text('\n'.join(section),encoding='utf-8')
    paper_data(results,groups,patterns)
    files=['REPORT.md','PAPER_SECTION.md','PAPER_DATA.json','DIRECTION_COUNTS.json','METRIC_DISAGREEMENT.png','METRIC_DISAGREEMENT.pdf']
    write(HERE/'PUBLICATION_AUDIT.json',{'status':'PASS','mean_and_direction_quantities_checked':meanchecks,
        'arithmetic_audit_sha256':sha(HERE/'AUDIT.json'),'publisher_source_sha256':sha(Path(__file__)),
        'outputs_sha256':{name:sha(HERE/name) for name in files},'interpretation':'Post-result rendering and mean audit; no new models or scientific comparisons'})
    print(json.dumps({'mean_audit_checks':meanchecks,'patterns':patterns},indent=2))


if __name__=='__main__':main()
