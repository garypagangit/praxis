"""Present a completed exposed-data diagnostic without inventing confirmation."""
from pathlib import Path
from datetime import datetime,timezone
import json

ROOT=Path(__file__).resolve().parent
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def ci(v):return f'[{v[0]:+.2f}, {v[1]:+.2f}]'
r=read('RESULTS.json');p=read('POLICY_FREEZE.json')
assert r['n']==1247 and r['scope']=='EXPOSED_DEVELOPMENT_DIAGNOSTIC_ONLY'
assert r['independent_confirmation'] is False and r['novelty_established'] is False
arms=r['metrics']['all']['arms'];new=arms['answer_change_nli']
labels={'baseline':'No extra facts','always_evidence':'Always add facts','previous_utility':'Previous utility checker',
        'previous_relevance':'Previous simple relevance checker','answer_change_nli':'Revised answer-change checker'}
table=['| Policy | Llama accuracy | Qwen accuracy | Mean change from no extra facts, pp [95% CI] |',
       '|---|---:|---:|---:|']
for key,label in labels.items():
    a=arms[key];m=a['models']
    table.append(f'| {label} | {m["llama"]["accuracy_pct"]:.2f}% | {m["qwen"]["accuracy_pct"]:.2f}% | {a["mean_delta_vs_baseline_pp"]:+.2f} {ci(a["mean_delta_ci95_pp"])} |')
change_table=['| Model | Accepted answer changes | Corrections | New errors | Useful corrections rejected |',
              '|---|---:|---:|---:|---:|']
for m in ['llama','qwen']:
    s=new['models'][m]
    change_table.append(f'| {m.title()} | {s["accepted_answer_changes"]} | {s["recoveries"]} | {s["induced_errors"]} | {s["rejected_useful_corrections"]} |')
comparison_table=['| Compared with | Llama difference, pp | Qwen difference, pp | Mean difference, pp [95% CI] |',
                  '|---|---:|---:|---:|']
for k,v in r['revised_minus_comparator'].items():
    comparison_table.append(f'| {labels[k]} | {v["model_difference_pp"]["llama"]:+.2f} | {v["model_difference_pp"]["qwen"]:+.2f} | {v["mean_difference_pp"]:+.2f} {ci(v["mean_ci95_pp"])} |')
positive=r['status']=='EXPOSED_DIAGNOSTIC_POSITIVE_BOTH_MODELS'
conclusion=('The revised checker improved the observed score in both models on these already examined questions. This is a development signal that needs untouched confirmation and independently reviewed evidence; it is not a validated new Praxis solution.' if positive else
            'The revised checker did not improve the observed score in both models. It does not justify a claim that the evidence-applicability problem is solved. Preserve this outcome and use human error review before selecting another design.')
cost=r['verifier_cost'];cal=read('CALIBRATION_SCORING.json')
report=f'''# Checking the reason for an AI answer change

**{conclusion}**

Recorded status: `{r['status']}`. September 18, 2026.

## What changed

The previous checker estimated whether the whole six-fact bundle would help. The revision compares support for the model's original answer with support for its evidence-based answer. A published natural-language inference model scores each actual fact against a fixed question/option template. The policy permits a change only when the proposed answer's support exceeds the original answer's support by the frozen margin.

This is a generic semantic-checking adaptation. It does not yet explicitly verify every platform, version, time, or other condition, and it does not change retrieval. Supporting fact indices and text hashes make the scores traceable; they do not prove that the passages are sufficient.

## Design and qualification

- Published verifier: `cross-encoder/nli-deberta-v3-xsmall`, revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, CPU float32.
- All eight fixed qualification cases passed. Eight implementation tests passed. These establish basic execution, not cybersecurity efficacy.
- Thresholds were chosen only on the old 500-question CTIBench calibration split and frozen before the SecEval verifier run. Selected minimum support: **{p['policy']['support']}**; strict support advantage: **>{p['policy']['margin']}**.
- Calibration mean gain was {p['selected_calibration_metrics']['mean_gain_pp']:+.2f} points. It was used for selection and is not a heldout result.
- The scorer processed 280 calibration disagreement questions / 3,720 fact-option pairs, then 234 SecEval disagreement questions / 2,904 pairs. Every one of the 1,247 SecEval questions remains in accuracy denominators; same-answer cases keep the original answer.
- One old calibration question has an unused empty D option. The initial invocation stopped before scoring any pair. The [documented input-contract correction](ENGINEERING_AMENDMENT.md) retained the question and all its original strings; no score-dependent method change occurred.

## Complete development results

Accuracy is agreement with released SecEval answers. Changes are percentage points, not relative percentages.

{chr(10).join(table)}

{chr(10).join(change_table)}

## Paired comparisons

{chr(10).join(comparison_table)}

The comparisons use the same question outcomes. Their confidence intervals resample questions within the fixed coarse-source counts, preserving both models together (5,000 draws, seed 20260918). They are not source-document cluster intervals or multiplicity-adjusted confirmation.

## What this can and cannot establish

SecEval was examined before this revision was designed. It remains **exposed development data**, even though no SecEval labels entered the NLI scorer or threshold selection. The [previous frozen external failure](../cti_external_validation_20260918/REPORT.md) remains unchanged. This revision cannot retroactively turn that result into a pass.

The verifier has generic NLI training, and the question/option hypothesis template has not been independently validated as a cybersecurity support test. Taking the strongest of six fact scores may accept a spurious match or miss a necessary combination of facts. Published benchmark labels may also be wrong or version-dependent; no completed human review is claimed.

Both original and evidence-based generator answers were already available. The revision makes no fresh generator calls, so it tests answer selection, not an end-to-end deployment's total cost. It is not an equal-cost comparison with the previous pre-generation checker. Accepted answer changes are not answer coverage, abstention, or measured retrieval savings.

Calibration verifier inference took {cal['inference_seconds']:.2f} CPU seconds; external diagnostic inference took {cost['inference_seconds']:.2f} seconds. Truncated fact-option pairs: {cal['truncated_pairs']} calibration and {cost['truncated_pairs']} external. No new AWS instance was started for this revision.

## Next action

Complete the existing [blinded human-review handoff](../cti_external_validation_20260918/REVIEW_HANDOFF.md). Then decide whether the failure concerns evidence retrieval, support verification, question/answer labels, or a combination. Test appropriate-source retrieval and answer checking in separate conditions, then together, under a new frozen protocol on untouched source-controlled questions. The [confirmation plan](NEXT_CONFIRMATION.md) specifies that distinction and stopping rules. Improved retrieval and untouched confirmation have not been run here.

The generic idea overlaps [CoRM-RAG](https://arxiv.org/html/2605.01302v1), [PAVE](https://arxiv.org/html/2603.20673v1), and [SURE-RAG](https://arxiv.org/html/2605.03534v2). None is reproduced in full by this experiment. Better development accuracy alone does not establish novelty.

## Reproducible record

[Protocol](PROTOCOL.md), [model and design review](DESIGN_REVIEW.md), [input audit](INPUT_AUDIT.json), [frozen calibration policy](POLICY_FREEZE.json), [full results](RESULTS.json), [per-question decisions](revision_decisions.jsonl), and [independent arithmetic audit](INDEPENDENT_AUDIT.json).

Reproduce the independent audit from the repository root with `python reports/cti_checker_revision_20260918/audit_revision.py --output INDEPENDENT_AUDIT_RECHECK.json`, choosing a new output filename if that file already exists. The audit uses the included byte-identical calibration archives and repository-relative external-test records. The policy/scoring/analysis scripts refuse to overwrite scientific outputs; work in a separate copy for a new run. Model weights are not included; the exact public revision and model file hashes are recorded in the receipts.
'''
(ROOT/'REPORT.md').write_text(report,encoding='utf-8')
print(json.dumps({'status':r['status'],'report':str(ROOT/'REPORT.md')}))
