"""Publish a descriptive, tree-only report from all 60 independently audited cells.

No fitting, inference, threshold changes, or new research-success gate. The
foundation comparisons remain separate and require all their registered pairs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean

from .publish_followup import aggregate_only, require

CONDITIONS = ('equal_32_per_class', 'abundant_benign_1024')
MODELS = ('xgboost', 'lightgbm', 'random_forest')
SEEDS = tuple(range(20260921, 20260931))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def summarize(cells):
    classes = cells[0]['metrics']['classes']
    normal = classes.index('NormalTraffic')
    rows = []
    for cell in cells:
        cm = cell['metrics']['confusion_matrix']
        attack_count = sum(sum(row) for i, row in enumerate(cm) if i != normal)
        missed = sum(row[normal] for i, row in enumerate(cm) if i != normal)
        rows.append({
            'seed': cell['seed'], 'selected_model': cell['model'],
            'macro_f1': cell['metrics']['macro_f1'], 'normal_fpr': cell['normal_fpr'],
            'binary_attack_recall': 1 - missed / attack_count,
            'exact_stage_recall': {k: cell['metrics']['per_stage'][k]['recall'] for k in classes if k != 'NormalTraffic'},
            'binary_detection_by_stage': {k: 1 - cm[i][normal] / sum(cm[i]) for i, k in enumerate(classes) if i != normal},
        })
    return {
        'seeds': len(rows),
        'mean': {
            **{k: mean(row[k] for row in rows) for k in ('macro_f1', 'normal_fpr', 'binary_attack_recall')},
            **{k: {stage: mean(row[k][stage] for row in rows) for stage in rows[0][k]}
               for k in ('exact_stage_recall', 'binary_detection_by_stage')},
        },
        'per_seed': rows,
    }


def publish(audit_path, output):
    audit_path, output = Path(audit_path), Path(output)
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    require(audit['audit_status'] == 'PASS' and audit['strong_batch_complete'] is True and audit['complete_strong_cells'] == 60, 'All 60 independently audited strong cells are required')
    cells = audit['cells']
    roster = [(c['condition'], c['model'], c['seed']) for c in cells]
    expected = {(c, m, s) for c in CONDITIONS for m in MODELS for s in SEEDS}
    require(len(roster) == 60 and set(roster) == expected, 'Strong cell roster differs')
    for cell in cells:
        require(cell['metrics']['n'] == 30787, 'Full development test required')
        expected_cost = {k: 32 for k in cell['class_label_costs']}
        if cell['condition'] == CONDITIONS[1]:
            expected_cost['NormalTraffic'] = 1024
        require(cell['class_label_costs'] == expected_cost, 'Label budget differs')
    aggregate_only(audit)
    by_key = {(c['condition'], c['model'], c['seed']): c for c in cells}
    result = {'status': 'DESCRIPTIVE_UNEQUAL_LABEL_BUDGET', 'audit_status': 'PASS',
              'source_audit_sha256': sha(audit_path), 'created_utc': datetime.now(timezone.utc).isoformat(),
              'strong_cells': 60, 'independent_incidents': False, 'novel_method_validated': False,
              'foundation_comparison_decided': False, 'models': {}}
    for model in (*MODELS, 'cv_selected_gbdt'):
        result['models'][model] = {}
        for condition in CONDITIONS:
            chosen = []
            for seed in SEEDS:
                if model == 'cv_selected_gbdt':
                    # Same training-only selector as the frozen comparison; XGBoost wins exact ties.
                    chosen.append(max([by_key[condition, m, seed] for m in ('xgboost', 'lightgbm')], key=lambda c: c['cv_macro_f1']))
                else:
                    chosen.append(by_key[condition, model, seed])
            result['models'][model][condition] = summarize(chosen)
    aggregate_only(result)
    require(not output.exists(), 'Preserve previous report; use a fresh output directory')
    output.mkdir(parents=True)
    (output / 'AUDIT.json').write_bytes(audit_path.read_bytes())
    write(output / 'SUMMARY.json', result)
    selected = result['models']['cv_selected_gbdt']
    before, after = [selected[c]['mean'] for c in CONDITIONS]
    pair = lambda a, b, percent=True: f'{100*a:.2f}% → {100*b:.2f}%' if percent else f'{a:.4f} → {b:.4f}'
    lines = ['# More normal-traffic examples reduce false alarms, with attack-detection tradeoffs', '',
        f"Audited development results, {result['created_utc']}. **60/60 tree runs complete.**", '',
        '## Finding in plain language', '',
        'Teaching the existing models more about normal traffic substantially reduced false alarms and improved their overall classification score. The attack-training examples were unchanged. However, the models missed more lateral-movement activity. This is a measured development improvement with a security tradeoff, not a new algorithm or a validated deployment.', '',
        f"For the training-CV-selected tree, macro-F1 changed {pair(before['macro_f1'], after['macro_f1'], False)}, and the normal false-alarm rate changed {pair(before['normal_fpr'], after['normal_fpr'])}. Overall attack detection changed {pair(before['binary_attack_recall'], after['binary_attack_recall'])}.", '',
        '## What changed', '',
        'Both conditions used the same 32 examples of each of five attack classes. The first used 32 normal examples; the second used 1,024. That adds 992 benign fitting labels, increasing the total from 192 to 1,184. Each condition used the same wider hyperparameter search and fitting-only cross-validation. XGBoost versus LightGBM was selected by training CV, with XGBoost winning exact ties; test scores never selected the model.', '',
        'Each of the ten seeds was evaluated on the same 30,787 unique development-test flows from the SCVIC author training corpus. The source author holdout was unavailable. These are not ten independent incidents.', '',
        '## All model families', '',
        'Values show 192-label → 1,184-label conditions; means across ten seeds.', '',
        '| Model | Macro-F1 | Normal false alarms | Initial-stage recall | Exfiltration-stage recall |',
        '|---|---:|---:|---:|---:|']
    for model in (*MODELS, 'cv_selected_gbdt'):
        a, b = [result['models'][model][c]['mean'] for c in CONDITIONS]
        lines.append(f"| {model} | {pair(a['macro_f1'], b['macro_f1'], False)} | {pair(a['normal_fpr'], b['normal_fpr'])} | {pair(a['exact_stage_recall']['InitialCompromise'], b['exact_stage_recall']['InitialCompromise'])} | {pair(a['exact_stage_recall']['DataExfiltration'], b['exact_stage_recall']['DataExfiltration'])} |")
    lines += ['', '## The security tradeoff', '',
        'Correctly naming an attack stage and noticing any attack are different measurements. The first requires the right stage label; the second counts any non-normal prediction as detection.', '',
        '| Actual stage | Correct stage identification | Detected as any attack |', '|---|---:|---:|']
    for stage in before['exact_stage_recall']:
        lines.append(f"| {stage} | {pair(before['exact_stage_recall'][stage], after['exact_stage_recall'][stage])} | {pair(before['binary_detection_by_stage'][stage], after['binary_detection_by_stage'][stage])} |")
    lines += ['', 'The table uses the training-CV-selected tree, not the best family chosen from test results. In particular, the reduction in lateral-activity detection must be considered alongside the large false-alarm reduction. No new pass/fail criterion was applied to this descriptive unequal-label comparison.', '',
        '## What this means for the praxis', '',
        '- This supplies a stronger practical baseline for the foundation-model and review-policy experiments.',
        '- It shows why normal-traffic label availability must be disclosed: a balanced 192-label baseline can be a poor operational comparator when more benign examples are available.',
        '- More training data and tree classifiers are established methods. This result alone does not establish novelty. The [literature review](../../tabular_followup/NOVELTY_POSITION.md) documents direct overlap.',
        '- These trees have not been independently tested on Sandworm in the abundant-benign condition. The earlier negative Sandworm result used the original 192-label models; do not mix those results.',
        '- InitialCompromise has only 15 test examples and DataExfiltration has 106. Repeated seeds reuse these cases; no independent-incident confidence or generalization guarantee follows.',
        '- Early identification, actor identity, and robustness to missing or delayed logs were not measured here.', '',
        '## Evidence and remaining work', '',
        '[SUMMARY.json](SUMMARY.json) retains all seed-level tree summaries. [AUDIT.json](AUDIT.json) is the exact independent audit that verifies input, support, CV, imputation, prediction and completion hashes and recomputes metrics. Its foundation comparison is an explicitly incomplete snapshot; no foundation winner is declared here.', '',
        'The frozen full foundation runs, rare-stage review gate, and source-calibrated Sandworm threshold diagnostic continue under the existing [completion process](../../tabular_followup/RUN_STATUS.md). Their source, settings and criteria were not changed in response to this finding.', '']
    (output / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    receipt = {'status': result['status'], 'created_utc': result['created_utc'], 'publisher_sha256': sha(__file__),
               'source_audit_sha256': sha(audit_path), 'artifact_sha256': {n: sha(output / n) for n in ('AUDIT.json', 'SUMMARY.json', 'REPORT.md')},
               'no_raw_or_row_level_data_published': True, 'novel_method_validated': False}
    write(output / 'PUBLICATION.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.audit, args.output)))
