"""Publish aggregate, audited window-diagnostic results; never row-level evidence."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def publish(run, audit, output):
    result = json.loads((run / 'RESULTS.json').read_text(encoding='utf-8'))
    checked = json.loads(audit.read_text(encoding='utf-8'))
    inputs = Path(__file__).with_name('INPUT_AUDIT.json')
    input_check = json.loads(inputs.read_text(encoding='utf-8'))
    if checked['status'] != 'PASS' or input_check['status'] != 'PASS':
        raise ValueError('Publication requires both audits to pass')
    if checked['results_sha256'] != digest(run / 'RESULTS.json'):
        raise ValueError('Results changed after audit')
    if output.exists():
        raise ValueError('Public output must be new')
    output.mkdir(parents=True)
    for name in ('RESULTS.json', 'PRE_FIT_RECEIPT.json', 'PROTOCOL.json', 'FEATURE_MANIFEST.json'):
        shutil.copyfile(run / name, output / name)
    shutil.copyfile(audit, output / 'AUDIT.json')
    shutil.copyfile(inputs, output / 'INPUT_AUDIT.json')
    names = {'first_lr': 'First-event logistic regression', 'pooled_lr': 'Pooled logistic regression (primary)',
             'pooled_extra_trees': 'Pooled ExtraTrees (secondary)', 'transfer_rule': 'Fixed transfer-tool rule',
             'activity_count': 'Observed activity count'}
    arms = ['first_lr', 'pooled_lr', 'pooled_extra_trees', 'transfer_rule', 'activity_count']
    macros = {(r['arm'], r['condition']): r for r in result['macro_family_results']}
    family = {(r['arm'], r['condition'], r['family']): r['metrics'] for r in result['family_results']}
    table = ['| Method | Clean recall | EXECVE/PROCTITLE removed | Clean known-label AP | Clean known-label ROC-AUC | Clean known-only F1 |',
             '|---|---:|---:|---:|---:|---:|']
    for arm in arms:
        clean, loss = macros[arm, 'clean'], macros[arm, 'command_absent']
        table.append(f"| {names[arm]} | {clean['recall']:.1%} | {loss['recall']:.1%} | {clean['known_average_precision']:.3f} | {clean['known_roc_auc']:.3f} | {clean['known_only_f1']:.1%} |")
    per_family = ['| Held-out family | Positive bins | First-event LR | Pooled LR | ExtraTrees | Tool rule | Activity count |',
                  '|---|---:|---:|---:|---:|---:|---:|']
    for f in ('1', '2', '3', '4', '6'):
        per_family.append(f"| {f} | {family['pooled_lr','clean',f]['positive']} | " + ' | '.join(
            f"{family[a,'clean',f]['recall']:.1%}" for a in arms) + ' |')
    micro = []
    for arm in arms:
        values = [family[arm, 'clean', f] for f in ('1', '2', '3', '4', '6')]
        found = sum(v['selected_target'] for v in values)
        positive = sum(v['positive'] for v in values)
        reviewed = sum(v['reviewed'] for v in values)
        micro.append({'arm': arm, 'selected_target': found, 'positive': positive, 'reviewed': reviewed,
                      'pooled_bin_recall': found / positive})
    summary = {'status': 'COMPLETE_PRIMARY_USEFUL_SIGNAL_FAILED_RETIRE_FORMULATION',
        'updated_utc': datetime.now(timezone.utc).isoformat(), 'windows': 5480, 'positive_windows': 264,
        'unknown_windows': 897, 'runs': 32, 'families': 5, 'models_fit': 15,
        'input_audit_checks_passed': len(input_check['checks']), 'family_results_audited': 50,
        'run_results_audited': 320, 'tests_passed': 172, 'test_wall_seconds': 32.411,
        'cpu_only': True, 'aws_compute_started': False, 'gates': result['gates'],
        'macro_family_results': result['macro_family_results'], 'pooled_clean_bin_counts_secondary': micro,
        'novel_method_validated': False, 'independent_confirmation': False,
        'recommendation': 'Retire this primary CAM-LDS fixed-window T1105 formulation; do not launch an evidence-recovery extension based on these findings.'}
    (output / 'SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    report = '''# Combined audit evidence for tool-transfer investigation

## Decision

**Completed: pooling helps relative to a single event, but the primary useful-signal gate fails. Retire this CAM-LDS formulation as the current praxis candidate.** The nonlinear control also performs poorly. This experiment does not establish a worthwhile evidence-recovery extension or a novel method.

At the same review budget, primary average recall rises from **10.4% to 21.3%** when audit evidence is pooled into ten-second windows. That passes the separate incremental-pooling criterion, but falls below the frozen **40% useful-signal minimum** and below three times random-budget recall (30.8%; chance itself is 10.3%). The simple tool rule reaches 21.9%. There is no positive overall result to promote into a praxis claim.

## What was run

- CAM-LDS: 32 runs across five previously exposed scenario families; 5,480 complete ten-second bins, including 264 positive, 4,319 other-annotation negatives and 897 unknown bins.
- All 83 author T1105 tool-transfer intervals are represented; 13 positive bins with no audit events remain in the denominator.
- Leave one family out; fit the three learned models on clean, known-label bins from the other four families. Fifteen fits, one seed and one window width, no tuning.
- Rank all bins, including unknowns, and inspect `ceil(10% * bins)` per run: **559 bins** in total. Rank ties use a frozen label-independent hash.
- Compare clean evidence with removal of EXECVE and PROCTITLE records. Labels, bins and review budgets do not change; other audit records retain some program clues.
- The primary statistic gives each scenario family equal weight. Every result is developmental; prior exposure prevents claiming untouched confirmation.

## Results at the frozen review budget

''' + '\n'.join(table) + '''

Recall columns are macro-family recall from ranking the **full grid**. AP and ROC-AUC use only known labels. The F1 column uses a separate top-10% review among known-label bins and is therefore conditional, not operational F1. Unknowns are never treated as known negatives. Macro known-label prevalence is 7.84%.

The primary pooled model's full-grid confirmed-positive yield lower bound is 15.1%, and 28.7% of its selected bins have unknown labels (both macro-family values). A verified operational precision or benign false-alert rate cannot be calculated from these labels.

## Family-level clean recall

''' + '\n'.join(per_family) + '''

Activity count's 30.0% macro result is driven by recovering all three positive bins in family 4, which represent just one source interval. It is not a generally superior detector. Across all positive bins without equal family weighting, pooled LR finds 77/264 (29.2%), first-event LR 44/264 (16.7%), and activity count 29/264 (11.0%). These secondary totals do not replace the frozen macro-family primary outcome.

## Frozen gates

| Question | Measured outcome | Decision |
|---|---|---|
| Is complete pooled evidence sufficiently useful? | 21.25% recall; chance 10.25%; above chance in 4/5 families | **FAIL:** below 40% and below 3x chance |
| Does pooling help compared with a single event? | +10.88 percentage points; improves 4/5 families; no family worsens | **PASS:** limited aggregation finding |
| Does pooled LR add value over the simple tool rule? | -0.67 percentage points | **FAIL:** required +5 points |
| Is there a substantial command-record-loss gap? | 21.25% to 16.62%, a 4.64-point decline | **No:** below the frozen 10-point criterion; clean signal also failed |

ExtraTrees reaches 19.35% clean recall and 15.80% after removal. It does not rescue the result, and it was never eligible to replace the primary after outcomes were inspected. These are practical descriptive gates, not statistical significance tests.

## What this establishes

The first-event control in this diagnostic omitted useful evidence available elsewhere in the same ten-second window. Combining evidence partly corrects that limitation. Prior robustness-v2 models already used historical context and a different query roster; this finding is not a direct ablation of that earlier experiment. Neither this representation nor the tested nonlinear alternative produces sufficiently reliable technique-window ranking across families. The current obstacle is broader than the two removed record types.

**Stop this formulation.** Preserve the code and negative findings. Any future APT investigation candidate should first establish trustworthy host/process or evidence-level labels and useful complete-evidence controls in an independently qualified cohort. Do not continue model sweeps or begin a recovery mechanism on the strength of this result.

This does not prove that all APT detection or all missing-evidence methods fail. It closes the bounded primary approach tested here. It also does not establish that label quality alone caused the failures.

## Integrity and limits

The input audit passed **62 checks**. The independent calculation audit recomputed all **50 family rows, 320 run rows and 10 selection masks**, checked gates and hash bindings, and reproduced predictions from all **15 saved models without refitting**. The complete software suite passed **172 tests** in 32.411 seconds. Audits were separate AI/code checks, not human adjudication or validation of label truth. An audit PASS does not turn the negative experiment positive.

The broad labels are padded author manifestation intervals, not exact malicious actions. Ten positive bins overlap their source interval by less than one second. No ordinary-user benign workload is present. The pre-existing replay envelope was selected using annotation boundaries; this is a retrospective selected-slice investigation, not whole-day monitoring or early warning. Some lexical and volume artifacts may remain. Five families, including family 4's single target interval, provide limited independent diversity.

The first software launch stopped before fitting on relative-path receipt bookkeeping; the documented one-line correction changed no inputs, settings or gates. The completed immutable run is `window_diagnostic_v1/run2`. CPU only; no AWS compute was started.

## Evidence and reproduction

- [Full numerical results](RESULTS.json), [summary](SUMMARY.json), [frozen protocol](PROTOCOL.json), [pre-fit receipt](PRE_FIT_RECEIPT.json).
- [Independent calculation audit](AUDIT.json), [independent input audit](INPUT_AUDIT.json), [feature manifest](FEATURE_MANIFEST.json).
- [Implementation and commands](../../window_diagnostic/README.md), [pre-fit design review](../../window_diagnostic/PROTOCOL_REVIEW.md), [data qualification](../../window_diagnostic/DATA_QUALIFICATION.md), [execution correction](../../window_diagnostic/EXECUTION_NOTES.md).
- [CAM-LDS paper](https://doi.org/10.1007/s10207-026-01318-x), [pinned data release](https://zenodo.org/records/18861762), [literature context](../../window_diagnostic/README.md#literature-and-source).

Raw logs, feature matrices, row-level predictions and saved models remain private. Git contains code, aggregate results and evidence hashes. The prior robustness experiments are preserved.
'''
    (output / 'REPORT.md').write_text(report, encoding='utf-8')
    publication = {'created_utc': datetime.now(timezone.utc).isoformat(),
        'artifacts_sha256': {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
        'source_results_sha256': checked['results_sha256'], 'raw_or_row_level_data_published': False}
    (output / 'PUBLICATION.json').write_text(json.dumps(publication, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publish(args.run, args.audit, args.output)
