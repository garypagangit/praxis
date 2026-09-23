"""Descriptive, unfiltered reporting of the frozen PX-081 run."""
from pathlib import Path
import json
from statistics import mean

HERE=Path(__file__).resolve().parent

def main():
    rows=json.loads((HERE/'RESULTS.json').read_text()); receipt=json.loads((HERE/'RUN_RECEIPT.json').read_text())
    lines=['# PX-081: Choosing which evidence to inspect next','',
      '## Plain-language result','',
      'This development experiment asks whether selecting extra information by its expected reduction in dangerous-stage errors improves decisions over selecting information by uncertainty reduction. All costs, delivery delays and channel failures below are simulated offline. The source data are real captured traffic with author stage annotations, from one previously examined UNRAVELED campaign. These results do not measure live collection, independent attack generalization or early exfiltration prediction.','',
      f"Completed {receipt['classifier_fits']} classifier and {receipt['regressor_fits']} selector fits across three seeds. Evaluation: {receipt['evaluation_n']:,} flows; benign/other/movement/exfiltration counts = {receipt['evaluation_class_counts']}. Calibration labels were not used. Seed averages below are descriptive fitting sensitivity, not independent-campaign confidence intervals.",'',
      '## All matched comparisons','',
      'Movement/exfiltration recall measures exact author-stage recognition. False alerts count benign rows assigned any attack. Weighted errors use the prespecified illustrative true-class costs 1/1/4/4; this is not a published acceptance standard. Spend is simulated units per decision.','']
    aggregate=[]
    for condition in ('clean','delayed_unavailable','wrong_host_history'):
        lines += [f'### {condition}','',
           '| Budget | Policy | Macro-F1 | Movement recall | Exfiltration recall | Benign false alerts | Weighted errors | Mean spend | Query rate |',
           '|---:|---|---:|---:|---:|---:|---:|---:|---:|']
        for budget in (1,2,3):
            for policy in ('none','roles_first','history_first','random','entropy','harm'):
                group=[r for r in rows if r['condition']==condition and r['budget']==budget and r['policy']==policy]
                r={'condition':condition,'budget':budget,'policy':policy,
                   **{k:mean(x[k] for x in group) for k in ('macro_f1','benign_false_alerts','weighted_error_total','mean_spend','query_rate','errors')},
                   'movement_recall':mean(x['movement']['recall'] for x in group),
                   'exfiltration_recall':mean(x['exfiltration']['recall'] for x in group),
                   'movement_f1':mean(x['movement']['f1'] for x in group),
                   'exfiltration_f1':mean(x['exfiltration']['f1'] for x in group),
                   'movement_any_attack_recall':mean(1-x['confusion'][2][0]/sum(x['confusion'][2]) for x in group),
                   'exfiltration_any_attack_recall':mean(1-x['confusion'][3][0]/sum(x['confusion'][3]) for x in group)}
                aggregate.append(r)
                lines.append(f"| {budget} | {policy} | {r['macro_f1']:.4f} | {r['movement_recall']:.2%} | {r['exfiltration_recall']:.2%} | {r['benign_false_alerts']:.1f} | {r['weighted_error_total']:.1f} | {r['mean_spend']:.3f} | {r['query_rate']:.2%} |")
        lines.append('')
    lines += ['## Unrestricted full-context reference','',
       'This reference always reveals both groups. It violates replay acquisition constraints when evidence is late, unavailable or unaffordable, so it is not eligible for same-budget superiority claims. Its cost is listed as3; elapsed time is0 only because this is an instantaneous-information reference, not a collection measurement.','',
       '| Condition | Macro-F1 | Movement recall | Exfiltration recall | Benign false alerts |','|---|---:|---:|---:|---:|']
    for condition in ('clean','delayed_unavailable','wrong_host_history'):
        g=[r for r in rows if r['condition']==condition and r['reference_only']]
        lines.append(f"| {condition} | {mean(r['macro_f1'] for r in g):.4f} | {mean(r['movement']['recall'] for r in g):.2%} | {mean(r['exfiltration']['recall'] for r in g):.2%} | {mean(r['benign_false_alerts'] for r in g):.1f} |")
    lines += ['','## Prespecified contrasts: harm minus entropy','',
      'A negative weighted-error difference favors harm selection. A positive movement-recall difference favors harm selection. These contrasts retain all budgets and conditions; none is designated successful after observing the table.','',
      '| Condition | Budget | Weighted error difference | Macro-F1 difference | Movement recall difference | Exfiltration recall difference | Spend difference |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for condition in ('clean','delayed_unavailable','wrong_host_history'):
        for budget in (1,2,3):
            a=next(r for r in aggregate if r['condition']==condition and r['budget']==budget and r['policy']=='harm')
            b=next(r for r in aggregate if r['condition']==condition and r['budget']==budget and r['policy']=='entropy')
            lines.append(f"| {condition} | {budget} | {a['weighted_error_total']-b['weighted_error_total']:+.1f} | {a['macro_f1']-b['macro_f1']:+.4f} | {a['movement_recall']-b['movement_recall']:+.2%} | {a['exfiltration_recall']-b['exfiltration_recall']:+.2%} | {a['mean_spend']-b['mean_spend']:+.3f} |")
    lines += ['','## Supplementary safety check: recognized as any attack','',
      'This descriptive check was added after inspecting the first seed, using the already-preserved confusion matrices. It does not replace the frozen exact-stage objectives. Calling an exfiltration flow movement is an exact-stage error but still an attack warning; calling it benign removes that warning. A higher macro-F1 can therefore coexist with lower attack recognition.','',
      '| Condition | Budget | Policy | Movement recognized as any attack | Exfiltration recognized as any attack |',
      '|---|---:|---|---:|---:|']
    for r in aggregate:
        if r['policy'] in ('none','entropy','harm'):
            lines.append(f"| {r['condition']} | {r['budget']} | {r['policy']} | {r['movement_any_attack_recall']:.2%} | {r['exfiltration_any_attack_recall']:.2%} |")
    lines += ['','## Limits and next decision','',
      '- This is a simple greedy expected-error-reduction probe, not a reproduction of SEFA, Learning-To-Measure, Sim-CTKG or a novelty claim.',
      '- Acquisition policies inspect only already observed features/probabilities. Simulated hidden availability and arrival become known only after a charged query.',
      '- Static roles and existing history summaries are hypothetical query groups. Actual collection/cache costs were not measured. Dynamic feature-value evolution is not tested.',
      '- A wrong-host summary is deliberate correspondence corruption, not a new real workflow or independently sampled incident.',
      '- Only35 evaluation movement flows exist, and their source annotations concern remote-system discovery on one host pair. The forward-fold selector targets contain only18 movement rows. There is no movement case in the unused calibration capture.',
      '- Exact-stage loss charges the same error weight for assigning the wrong attack stage and assigning benign. The supplementary any-attack table exposes this limitation; a future asymmetric loss would require a separate frozen experiment.',
      '- OOF training protects selector targets against in-fold fitting, but all source captures belong to an exposed campaign. A positive score cannot establish external generalization.',
      '- Before a method-based praxis claim: qualify independent executions, implement stronger recent acquisition baselines, measure true channel availability/latency, and compare at operational false-alarm and review workloads.','',
      '## Reproduce and inspect','',
      '[Protocol](PROTOCOL.md), [implementation notes](METHOD_NOTES.md), [freeze](FREEZE.json), [run receipt](RUN_RECEIPT.json), [audit](AUDIT.json), [all results](RESULTS.json), [capture breakdown](CAPTURE_RESULTS.json). Private per-row probability/action/availability traces are at the path in the run receipt. They are omitted from Git to avoid publishing source event linkage.','',
      '```powershell',
      "& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' -m pytest experiments/praxis_next/px081_evidence_acquisition/test_px081.py -q",
      "& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' experiments/praxis_next/px081_evidence_acquisition/audit.py",
      '```','']
    (HERE/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    (HERE/'AGGREGATE.json').write_text(json.dumps(aggregate,indent=2)+'\n',encoding='utf-8')
    print('Wrote README.md and AGGREGATE.json')

if __name__=='__main__':main()
