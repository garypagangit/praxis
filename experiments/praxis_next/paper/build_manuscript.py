"""Assemble the empirical manuscript from audited aggregates, without fitting models."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
SOURCES = [BASE/'px080_context_selector/results/MEANS.json',
           BASE/'px081_evidence_acquisition/AGGREGATE.json',
           BASE/'px082_temporal_audit/SUMMARY.json']
A, B, C = [json.loads(p.read_text(encoding='utf-8')) for p in SOURCES]

def select(rows, **where):
    found = [r for r in rows if all(r[k] == v for k, v in where.items())]
    assert len(found) == 1, where
    return found[0]

def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                     '|' + '|'.join(['---']*len(headers)) + '|'] +
                    ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows])

def pct(v): return f'{100*v:.2f}%'

conditions = ['clean', 'missing_half', 'missing_all', 'stale_5min', 'wrong_host']
names = ['Clean', 'Half missing', 'All missing', 'Five-minute stale', 'Wrong host']
rows = []
for c, label in zip(conditions, names):
    o = select(A, condition=c, arm='ordinary_gate')
    h = select(A, condition=c, arm='stage_harm_gate')
    d = select(A, condition=c, arm='context_dropout')
    rows.append([label, pct(o['movement_recall']), pct(h['movement_recall']),
                 pct(d['movement_recall']), f"{o['normal_false_attacks']:.1f} / {h['normal_false_attacks']:.1f}"])
gate_table = table(['History condition', 'Ordinary recall', 'Weighted recall', 'Dropout recall', 'False alerts: ordinary / weighted'], rows)
rows = []
for c, label in [('clean', 'Clean'), ('delayed_unavailable', 'Delayed/unavailable'), ('wrong_host_history', 'Wrong host')]:
    for p, pn in [('none', 'Current only'), ('entropy', 'Entropy'), ('harm', 'Error focused')]:
        r = select(B, condition=c, budget=3, policy=p)
        rows.append([label+' / '+pn, f"{r['macro_f1']:.4f}", pct(r['movement_recall']),
                     f"{r['benign_false_alerts']:.1f}", f"{r['weighted_error_total']:.1f}", f"{r['mean_spend']:.3f}"])
acq_table = table(['Condition / policy', 'Macro-F1', 'Movement recall', 'False alerts', 'Weighted errors', 'Spend'], rows)
rows = []
for v, vn in [('current', 'Current'), ('current_history', 'Current + history')]:
    for a, an in [('past_only_anchor', 'Past only'), ('time_mixed_anchor', 'Time mixed'), ('conventional_random', 'Random rows')]:
        r = select(C, view=v, arm=a)
        rows.append([vn+' / '+an, f"{r['macro_f1']:.4f}", pct(r['movement_recall']),
                     f"{r['movement_f1']:.4f}", f"{r['exfiltration_f1']:.4f}", pct(r['normal_false_attack_rate'])])
time_table = table(['Features / training', 'Macro-F1', 'Movement recall', 'Movement F1', 'Exfil. F1', 'False-alert rate'], rows)

plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.1))
for arm, label, color, marker in [('ordinary_gate','Ordinary gate','#355c7d','o'), ('stage_harm_gate','Weighted gate','#c06c38','s'), ('context_dropout','Context dropout','#48836b','^')]:
    vals = [select(A, condition=c, arm=arm) for c in conditions]
    axes[0].plot(range(5), [100*r['movement_recall'] for r in vals], label=label, color=color, marker=marker)
    axes[1].plot(range(5), [r['normal_false_attacks'] for r in vals], label=label, color=color, marker=marker)
axes[0].axhline(100*select(A, condition='clean', arm='current_roles')['movement_recall'], color='#444444', linestyle='--', label='Current + roles')
axes[1].axhline(select(A, condition='clean', arm='current_roles')['normal_false_attacks'], color='#444444', linestyle='--')
for ax in axes:
    ax.set_xticks(range(5), ['Clean','Half\nmissing','All\nmissing','Stale','Wrong\nhost'])
    ax.grid(axis='y', alpha=.18)
axes[0].set_ylabel('Author movement recall (%)'); axes[0].set_ylim(0, 100)
axes[1].set_ylabel('Benign false alerts (mean count)'); axes[1].set_ylim(0, 165)
axes[0].set_title('More movement labels recovered'); axes[1].set_title('With more false alerts than ordinary gating')
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc='lower center', ncol=4, frameon=False, fontsize=9)
fig.tight_layout(rect=(0,.1,1,1)); fig.savefig(ROOT/'context_tradeoffs.png', dpi=180); fig.savefig(ROOT/'context_tradeoffs.pdf'); plt.close(fig)

abstract = """# When Historical Context Helps and Hurts

## Attack-stage recognition, evidence selection, and temporal evaluation

**Empirical praxis manuscript - completed development studies**
23 September 2026 | Reproducible results and limits of inference

## Abstract

Historical evidence can improve attack-stage classification, but missing or incorrectly associated records may make it misleading. We investigate two practical selectors and a temporal evaluation audit using 382,229 author-labeled UNRAVELED flows. A history selector learns the additional classification error caused by context; an acquisition policy chooses optional evidence under simulated costs and delivery constraints. Both use forward-held-out supervision and fixed controls. Weighting consequential stages raised movement recall over ordinary selection in all five tested history conditions, by 4.76-14.29 percentage points, but increased false alerts and weighted errors throughout. Error-focused acquisition reduced simulated spending by 32.24% against entropy selection in clean, maximum-budget replay, without a consistent detection advantage. Supplementary confusion analysis found that higher macro-F1 could accompany fewer exfiltration examples recognized as any attack. In a separate same-anchor audit, time-mixed training increased macro-F1 by 0.0632 for current evidence and 0.0383 with history. These are development findings from previously examined data, not independent-campaign confirmation or proof of a novel superior detector. They support an applied evaluation requirement: distinguish missed attack warnings from incorrect attack-stage labels when deciding whether context or additional evidence is useful. A secondary policy-transfer study and cloud data-qualification record accompany the main experiments.

**Keywords:** attack-stage classification; historical context; active feature acquisition; temporal evaluation; adversarial activity; reproducible cybersecurity research.

"""
results = f"""
## 5. Results

### 5.1 A stage-weighted selector changes the tradeoff

The context study fitted 39 models and retained 105 arm-condition-seed probability tables. Mean movement recall of the weighted gate exceeded the matched ordinary gate in every registered history condition. The gain was smallest on clean history and largest on the stale snapshot. However, weighted error and benign false alerts were also higher in every condition. Thus, the weighting changed the operating tradeoff; it did not establish overall superiority.

**Table 1. History selection: all five conditions.** Recall refers to the exact author movement stage. False-alert counts are means over three fits on the same 192,193 benign rows. All methods share 35 movement evaluation rows. Current-plus-roles recall was 78.10% and its mean false-alert count was 139.3 in every condition.

{gate_table}

Under entirely missing history, ordinary dropout training achieved 68.57% movement recall compared with 42.86% for the proposed weighted gate. Under wrong-host history, the corresponding figures were 68.57% and 44.76%. The simple current-plus-roles baseline retained higher movement recall throughout. Clean macro-F1 was 0.7659 for ordinary gating and 0.7560 for weighted gating; their weighted error rates were 0.023988 and 0.024122. Costs therefore matter even where recall improves.

![Figure 1. History selection tradeoffs. Means over three fits on shared events; no independent-campaign error bars are implied.](context_tradeoffs.png)

The absolute gain of 4.76-14.29 percentage points represents approximately 1.7-5.0 additional correctly classified movement rows, averaged over fitting seeds. Reusing those rows in several interventions does not create additional independent attack evidence. Full seven-arm metrics, per-capture results, ROC-AUC, average precision and selector help/harm counts are retained in the [complete context report](../px080_context_selector/results/REPORT.md).

### 5.2 Lower acquisition spending does not imply safer decisions

The acquisition study fitted 60 classifiers and 24 transition regressors. Table 2 presents every delivery condition at the largest registered budget; budgets one and two and all controls remain in the [complete acquisition report](../px081_evidence_acquisition/README.md). The unrestricted full-context reference is separate because it does not obey the same acquisition constraints.

**Table 2. Acquisition results at budget three.** The cost weights are 1/1/4/4; spending uses simulated units. The policies share budget caps but need not spend the same amount. Counts are three-fit means.

{acq_table}

Error-focused acquisition spent 32.24% less than entropy acquisition in clean replay and 26.12% less with delayed or unavailable evidence. It nevertheless made more weighted stage errors in both comparisons. Wrong-host history increased its weighted errors by 53.81% relative to current evidence alone. The policy has no post-acquisition rejection mechanism: a successfully delivered but misleading group can change the final classifier.

There are favorable isolated operating points. With budget one, the error-focused policy slightly reduced weighted error against entropy and current-only controls. That budget cannot retrieve history, so it cannot establish robustness to bad history. With budget two under wrong-host corruption it avoided some of entropy selection's harm. Reporting these observations alongside unfavorable conditions preserves the complete experimental record without treating the most favorable cell as confirmation.

### 5.3 Wrong stage and missed attack are different errors

A supplementary analysis, added after inspection of the first acquisition seed, calculated whether true exfiltration received any non-benign label. It uses unchanged saved confusion matrices and is not a new fitted endpoint. At budget three, clean macro-F1 increased from 0.7148 with entropy acquisition to 0.7379 with error-focused acquisition, while exfiltration recognized as any attack decreased from 85.18% to 76.25%. Under delayed delivery, macro-F1 increased from 0.7180 to 0.7427 while any-attack exfiltration recall decreased from 81.00% to 69.20%.

Some entropy predictions assigned exfiltration to movement. That stage was incorrect, but it still raised an attack warning. Some error-focused predictions instead assigned benign. The true-class weighted loss charges both mistakes equally; macro-F1 can improve through their different effects on other classes' precision. This is a concrete measurement mismatch, not evidence that F1 is invalid for its defined task.

### 5.4 Training composition materially changes measured performance

The temporal audit fitted 18 classifiers across two feature views, three protocols and three seeds. Its primary comparison fixes the same 104,051 later anchor rows and matches training class counts after fingerprint exclusion. The random-row diagnostic has a different evaluation population of 210,226 rows and must be interpreted separately.

**Table 3. Temporal protocols.** Past-only and time-mixed rows within each view share the anchor. Random-row results are descriptive. False-alert rate uses the benign denominator in each corresponding evaluation population.

{time_table}

Time-mixed training raised macro-F1 by 0.0632 with current features and 0.0383 with history. Movement recall increased by 35.19 and 27.78 percentage points. The time-mixed pool deliberately includes later examples and can represent different workflows. For history, its training summaries may also incorporate earlier anchor observations. These effects are part of the diagnostic rather than an acceptable deployment-training procedure.

The chronological history comparison also contains a limited favorable result: macro-F1 increased from 0.7365 to 0.7582, movement F1 from 0.2091 to 0.2836, and exfiltration F1 from 0.7565 to 0.7671, while mean false alerts fell from 24.0 to 14.3. This cross-view comparison is supplementary to the primary training-pool contrast. Movement recall increased in only one seed, by two of eighteen anchor rows. Exfiltration-to-benign errors increased in all seeds, from 565/563/563 to 572/569/571. An improved aggregate score therefore does not establish uniformly safer classification even in the favorable chronological comparison.

The [temporal report](../px082_temporal_audit/REPORT.md) preserves every seed and descriptive capture-bootstrap interval. Those intervals describe resampling five captures within this campaign; they do not estimate independent-campaign generalization. One history seed's interval for the time-mixed macro-F1 difference includes zero.

"""
discussion = """
## 6. Discussion

### 6.1 What the results support

The measured benefits are real but conditional. Prior traffic can improve stage F1 and reduce false alerts in a chronological comparison. Weighting a selector can recover more rare stage labels. Error-focused acquisition can use fewer simulated collection units. None of those statements alone establishes that an operational detector preserves attack warnings or dominates simpler controls.

The strongest substantial result in the primary batch is protocol sensitivity: changing the available training periods changes conclusions even on the same evaluation rows and with matched class counts. This is useful evidence for an evaluation-centered praxis, alongside recent security work questioning benchmark comparability. Its contribution is a specific controlled measurement and a reproducible workflow on these data, not discovery of temporal bias itself.

### 6.2 The practical literature gap remains narrow

The unresolved applied question is whether a policy can use imperfect supporting evidence while preserving dangerous-activity recognition at a comparable false-alert workload. Existing temporal fusion, mixture-of-experts selection and feature acquisition make a broad claim of algorithm novelty untenable. The new work must show a distinct objective, observable evidence assumptions, and a material advantage against strong matched controls. These pilots implement plausible objectives but do not supply that superiority result.

A subsequent method could distinguish three consequences explicitly: a benign event flagged as an attack, an attack assigned the wrong stage, and an attack declared benign. Evidence acquisition could be followed by a trust decision before changing an existing warning. This is a proposed research direction, not a tested solution in this manuscript. Avoiding all changes to attack labels would trivially retain warnings and could also preserve false alarms; a useful system must measure that cost rather than claim safety by construction.

### 6.3 Operational reporting supported by the evidence

A defensible evaluation should retain current-evidence-only and missingness-trained controls; report exact-stage and any-attack recall together; disclose false-alert counts with denominators; and evaluate complete condition tables. Acquisition studies additionally need actual spend, failure and late-delivery rates, with failed requests kept in the accounting. Temporal studies need deployment-valid fitting periods and grouped source identities. These reporting choices expose practical tradeoffs demonstrated here, without purporting to constitute a new detection algorithm.

## 7. Validity, limitations, and reproducibility

**Target validity.** Author stage labels are not independent evidence of completed theft or remote execution. The movement class here represents discovery on one host pair. Current-flow features are available after completion; no lead time or forecasting result was measured. Technique-level transfer proxies in the supplementary study have a different meaning and cannot repair that limitation.

**Statistical independence and exposure.** Eleven captures come from one previously examined UNRAVELED campaign. The selectors' forward-held-out training has only eighteen distinct movement rows; all 1,299 exfiltration targets in those selector folds occur in one capture. Repeated fitting seeds and simulated copies increase computation, not independent event support. The full evaluation has thirty-five movement rows and the temporal anchor has eighteen. There was no untouched confirmatory campaign for the primary studies.

**Design choices.** Costs, budgets, simulated delays, degradation conditions, model capacities and the 4:1 stage weights were fixed research settings. They are not requirements established by the literature. No self-imposed 90% rule determines the interpretation. Inference compares observed benefits and costs against fixed controls. Score thresholds were not optimized on test results. Matched resource caps do not imply equal actual expenditure.

**Scope of comparisons.** These lightweight learned selectors do not reproduce SEFA, Learning-To-Measure or Sim-CTKG. TabM motivates a possible future base-model comparison but was not fitted in this batch. Differences among the three primary studies' raw scores also reflect feature sets, training details and evaluation populations; they cannot rank architectures across experiment identifiers.

**Audits.** The history audit replayed all 105 final probability arrays and checked 735 metric tables and twelve forward folds. The acquisition audit checked 981 metric tables, 162 sequential acquisition traces and twelve forward folds. The temporal audit checked eighteen prediction tables, 378 scalar calculations and nineteen output hashes. All passed. These are computational checks, not external human validation or a guarantee that source labels match physical attack outcomes.

**Source preservation.** Scientific protocols and programs were committed before fits. PX-080 binds to 06c5037; PX-081 and PX-082 bind to 2da1a1c. A [byte-format note](../FREEZE_BYTE_NOTE.md) records Git line-ending serialization of early JSON receipts; executed scientific source and protocols matched committed bytes. Private row-linked predictions, fold inputs and fitted models remain locally preserved, while public aggregate results, audit receipts and code are published in the experiment branch. Public links do not redistribute restricted raw datasets.

## 8. Conclusion

The experiments produced defensible empirical findings and working research infrastructure, but not a proven superior context selector or acquisition method. The weighted history selector recovered more movement annotations at a false-alert cost. Error-focused acquisition reduced simulated spending while sometimes suppressing attack warnings. A controlled temporal audit showed substantial score sensitivity to access to later training examples. Together these findings support a clear praxis question: how should a system value additional evidence when assigning a more accurate stage can come at the cost of losing the attack warning? Answering that method question requires independent, outcome-verified executions and comparison at explicit operational costs. The present manuscript supplies the measured motivation and limitations for that next study.

## Appendix A. Artifact guide

| Artifact | Purpose |
|---|---|
| [Experiment registry](../REGISTRY.json) | Study identifiers, statuses and claim limits |
| [Context study](../px080_context_selector/README.md) | Frozen method, all conditions, saved metrics and audit |
| [Acquisition study](../px081_evidence_acquisition/README.md) | Every budget, policy and delivery condition |
| [Temporal audit](../px082_temporal_audit/REPORT.md) | Same-anchor comparison and random-row diagnostic |
| [Policy transfer](../px083_policy_transfer/README.md) | Secondary recent-dataset score-policy replication |
| [Cloud compute record](../compute/README.md) | Actual AWS use, resource bounds and cleanup evidence |
| [Data qualification](../data_qualification/README.md) | Acquisition results and target validity checks |

Tables 1-3 and Figure 1 are generated from audited aggregate JSON by build_manuscript.py. The supplementary transfer table was independently checked against its saved aggregates. BUILD_INPUTS.json binds those aggregate results and the narrative sources. Rendering is separate from experiment execution and performs no fitting. The supplementary acquisition any-attack analysis and chronological cross-view reading are explicitly post-fit interpretations of preserved outputs.

"""
extra_paths = [ROOT/'POLICY_TRANSFER_SECTION.md', ROOT/'CLOUD_SECTION.md', ROOT/'REFERENCES.md']
for p in extra_paths:
    if not p.exists():
        raise FileNotFoundError(f'Finalize required manuscript section: {p}')
methods = (ROOT/'METHODS_AND_CONTEXT.md').read_text(encoding='utf-8')
text = abstract + methods + '\n' + results + extra_paths[0].read_text(encoding='utf-8') + '\n' + discussion
reference_audit = extra_paths[2].read_text(encoding='utf-8')
reference_entries = [p for p in reference_audit.split('\n\n')
                     if p.strip() and __import__('re').match(r'^[A-Z][^\n]+\(20\d\d\)\.', p)]
assert len(reference_entries) == 15
reference_text = '\n## References\n\n' + '\n\n'.join(reference_entries)
reference_text += '\n\nPublication status: Guerra and StageFinder are inspected preprints with author-reported future-conference acceptance. Learning-To-Measure is the inspected 2026 revision, listed in the ICML 2026 program. ProvICS is a preprint. UNRAVELED (2023) and TESSERACT (2019) provide data provenance and foundational prior art outside the two-year motivation window. See the [primary-source reference audit](REFERENCES.md) for publication/version details and the closest-work novelty assessment.\n'
text += '\n' + extra_paths[1].read_text(encoding='utf-8') + '\n' + reference_text
(ROOT/'manuscript.md').write_text(text, encoding='utf-8')
bound = SOURCES + [ROOT/'METHODS_AND_CONTEXT.md', Path(__file__)] + extra_paths
bound += [BASE/'px083_policy_transfer/results'/name for name in
          ['MEANS.json', 'DIAGNOSTICS.json', 'ORIGINAL_THRESHOLD_CONTROLS.json', 'AUDIT.json']]
bound += [BASE/'data_qualification/results/provics_cloud_attempt3/measurement_support.json',
          BASE/'data_qualification/results/provics_cloud_attempt3/INDEPENDENT_REVIEW.md',
          BASE/'compute/PROVICS_ATTEMPT3_RESULT.json']
(ROOT/'BUILD_INPUTS.json').write_text(json.dumps({
    'purpose':'Post-fit paper assembly only; no fits, thresholds or result selection',
    'sources':{str(p.relative_to(BASE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in bound},
    'manuscript_sha256':hashlib.sha256((ROOT/'manuscript.md').read_bytes()).hexdigest(),
    'word_count':len(text.split())}, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'manuscript':str(ROOT/'manuscript.md'),'words':len(text.split())}))
