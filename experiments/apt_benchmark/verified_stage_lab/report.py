"""Publish completed aggregate lab evidence without fitting or choosing models."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics


SEEDS = [20260922, 20260923, 20260924]
ARMS = ['current', 'current_roles', 'current_history', 'current_roles_history',
        'current_roles_wrong_history', 'history_only', 'timing_diagnostic']
COMPARATORS = ['majority', 'prior_evidence_rule']
CONDITIONS = ['clean', 'drop_remote', 'drop_file', 'delay50ms', 'role_permutation']
POPULATIONS = ['linked', 'crossed', 'factorial_all']
SUBSETS = ['all', 'status200_only']
CLASSES = ['Neither', 'RemoteAction', 'FileTransfer', 'Both']
LABELS = {
    'current': 'Current + coverage controls',
    'current_roles': 'Current + roles',
    'current_history': 'Current + earlier event meanings',
    'current_roles_history': 'Current + roles + earlier event meanings',
    'current_roles_wrong_history': 'Current + roles + wrong-source history',
    'history_only': 'Earlier event meanings + coverage controls',
    'timing_diagnostic': 'DIAGNOSTIC: context + current elapsed time',
    'majority': 'Majority outcome',
    'prior_evidence_rule': 'Direct prior-evidence rule',
}
CONDITION_LABELS = {
    'clean': 'Clean observations', 'drop_remote': 'Remote-job records removed',
    'drop_file': 'File-write records removed', 'delay50ms': 'Prior arrival shifted by 50 ms',
    'role_permutation': 'Role metadata permuted',
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def average(items):
    """Average measurements, preserving identical booleans/nulls as facts."""
    require(bool(items), 'Empty metric collection')
    first = items[0]
    if isinstance(first, dict):
        require(all(isinstance(x, dict) and set(x) == set(first) for x in items), 'Metric keys differ')
        return {k: average([x[k] for x in items]) for k in first}
    if isinstance(first, list):
        require(all(isinstance(x, list) and len(x) == len(first) for x in items), 'Metric dimensions differ')
        return [average([x[k] for x in items]) for k in range(len(first))]
    if first is None or isinstance(first, (str, bool)):
        require(all(type(x) is type(first) and x == first for x in items), 'Structural metric differs')
        return first
    require(all(not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
                for x in items), 'Nonfinite or invalid metric')
    return float(statistics.mean(items))


def verify_metrics(metrics):
    require(set(metrics) == set(CONDITIONS), 'All five conditions are required')
    for condition in CONDITIONS:
        require(set(metrics[condition]) == set(POPULATIONS), 'Linked, crossed, and full-factorial populations required')
        for population in POPULATIONS:
            group = metrics[condition][population]
            require(set(group) == set(SUBSETS), 'All and status200-only metrics required')
            for subset in SUBSETS:
                m = group[subset]
                require(set(m['per_class']) == set(CLASSES), 'Four outcome classes required')
                require(set(m['outcomes']) == {'remote', 'transfer'}, 'Both operation outputs required')
                require(type(m['rows']) is int and m['rows'] > 0, 'Nonempty subset required')
                require(len(m['confusion']) == 4 and all(len(row) == 4 for row in m['confusion']), 'Confusion shape differs')
                require(sum(sum(row) for row in m['confusion']) == m['rows'], 'Confusion count differs')
                for i, name in enumerate(CLASSES):
                    require(sum(m['confusion'][i]) == m['per_class'][name]['support'], 'Class support differs')
                average([m])  # Finite scalar/structural validation throughout.
            require(group['status200_only']['rows'] <= group['all']['rows'], 'Successful subset exceeds all rows')


def validate_run(run, protocol):
    complete = read(run / 'COMPLETE.json')
    for name, key in [('SUMMARY.json', 'summary_sha256'), ('STARTED.json', 'started_sha256')]:
        require(complete.get(key) == sha(run / name), 'Root completion hash differs: ' + name)
    summary, started = read(run / 'SUMMARY.json'), read(run / 'STARTED.json')
    spec = read(protocol)
    require(spec['seeds'] == SEEDS and spec['arms'] == ARMS and spec['conditions'] == CONDITIONS,
            'Frozen protocol roster differs')
    require(summary['receipt']['protocol_sha256'] == sha(protocol), 'Protocol binding differs')
    require(summary['receipt']['models_fitted'] == 21, 'All 21 fits required')
    require([r['seed'] for r in summary['seeds']] == SEEDS, 'Three complete ordered seeds required')
    for key, value in started.items():
        require(summary['receipt'].get(key) == value, 'Start receipt differs from summary')
    prep = summary['preparation']
    require(prep['protocol_sha256'] == sha(protocol)
            and prep['data_sha256'] == summary['receipt']['prepared_sha256'], 'Preparation binding differs')
    source_hashes = {}
    for name, digest in spec['source_bindings'].items():
        require(Path(name).name == name, 'Unexpected source path')
        require(sha(protocol.parent / name) == digest, 'Frozen source changed: ' + name)
        source_hashes[name] = digest
    cell_hashes = {}
    first_support = None
    for cell in summary['seeds']:
        directory = run / str(cell['seed'])
        completion = read(directory / 'COMPLETE.json')
        expected = {'PREDICTIONS.npz', 'METRICS.json'} | {a + '.joblib' for a in ARMS}
        require(set(completion.get('files', {})) == expected, 'Incomplete cell artifact roster')
        for filename, digest in completion['files'].items():
            require(Path(filename).name == filename and sha(directory / filename) == digest,
                    'Cell artifact hash differs: ' + filename)
        require(read(directory / 'METRICS.json') == cell, 'Completed cell metrics differ from summary')
        require(set(cell['arms']) == set(ARMS), 'Seven arms required')
        require(set(cell['comparators']) == set(COMPARATORS), 'Both fixed comparators required')
        require(set(cell['hidden_policy_twins']) == set(ARMS), 'All hidden-policy diagnostics required')
        for arm in ARMS + COMPARATORS:
            metrics = cell['arms'][arm] if arm in ARMS else cell['comparators'][arm]
            verify_metrics(metrics)
            support = {p: {s: [metrics['clean'][p][s]['per_class'][c]['support'] for c in CLASSES]
                           for s in SUBSETS} for p in POPULATIONS}
            if first_support is None:
                first_support = support
            require(support == first_support, 'Models or seeds use different test supports')
            for condition in CONDITIONS:
                for population in POPULATIONS:
                    for subset in SUBSETS:
                        require([metrics[condition][population][subset]['per_class'][c]['support'] for c in CLASSES]
                                == support[population][subset], 'Stress condition changed query support')
            for subset in SUBSETS:
                require([a + b for a, b in zip(support['linked'][subset], support['crossed'][subset])]
                        == support['factorial_all'][subset], 'Full-factorial support is not the union')
        for diagnostic in cell['hidden_policy_twins'].values():
            require(set(diagnostic) == set(POPULATIONS), 'Twin populations differ')
            for t in diagnostic.values():
                require(t['policy_context_supplied'] is False and t['separate_physical_executions'] is False,
                        'Twin scope differs')
                require(t['counterfactual_rows'] == 2 * t['underlying_completed_operations'], 'Twin count differs')
                require(math.isclose(t['accuracy'], .5, abs_tol=1e-12)
                        and math.isclose(t['roc_auc'], .5, abs_tol=1e-12), 'Matched hidden-policy invariant differs')
        cell_hashes[str(cell['seed'])] = sha(directory / 'COMPLETE.json')
    return summary, cell_hashes, source_hashes


def contrasts(summary):
    pairs = [('current_roles_history', 'current', 'Full context versus current + coverage controls'),
             ('current_history', 'current', 'Earlier event meanings beyond current controls'),
             ('current_roles_history', 'current_roles_wrong_history', 'Correct versus wrong-source history'),
             ('current_roles_history', 'prior_evidence_rule', 'Full context versus direct prior-evidence rule'),
             ('current_roles_history', 'current_history', 'Roles beyond current + history')]
    out = []
    for candidate, reference, label in pairs:
        for condition in CONDITIONS:
            for population in POPULATIONS:
                for subset in SUBSETS:
                    deltas = []
                    for cell in summary['seeds']:
                        def get(a):
                            return (cell['arms'] if a in ARMS else cell['comparators'])[a][condition][population][subset]
                        a, b = get(candidate), get(reference)
                        values = {k: a[k] - b[k] for k in ['macro_f1', 'accuracy']}
                        for operation in ['remote', 'transfer']:
                            for key in ['precision', 'recall', 'f1', 'ap', 'roc_auc', 'tp', 'fp', 'fn']:
                                av, bv = a['outcomes'][operation][key], b['outcomes'][operation][key]
                                values[operation + '_' + key] = av - bv if av is not None and bv is not None else None
                        deltas.append({'seed': cell['seed'], 'delta': values})
                    out.append({'candidate': candidate, 'reference': reference, 'purpose': label,
                                'condition': condition, 'population': population, 'subset': subset,
                                'mean_delta': average([x['delta'] for x in deltas]), 'per_seed': deltas})
    return out


def pct(x):
    return 'N/A' if x is None else f'{100 * x:.2f}%'


def num(x, digits=4):
    return 'N/A' if x is None else f'{x:.{digits}f}'


def pp(x):
    return 'N/A' if x is None else f'{100 * x:+.2f} pp'


def render_report(e):
    means = e['means']
    audit = '[Independent calculation audit](AUDIT.json): PASS.' if e['audit']['status'] == 'PASS' else 'Independent calculation audit: PENDING. Completed run receipts are verified; this is not yet an audited result.'
    headline = '; '.join(pop + ' ' + num(means['current']['clean'][pop]['all']['macro_f1'])
                         + ' to ' + num(means['current_roles_history']['clean'][pop]['all']['macro_f1'])
                         for pop in POPULATIONS)
    lines = ['# Verified operations, earlier activity, and broken workflow correspondence', '',
             '**Completed controlled mechanism experiment. Algorithmic novelty and operational APT detection are not established.**', '', audit, '',
             '**Observed clean four-outcome macro-F1, current + coverage controls to full context:** ' + headline + '. The complete tables retain successful-request-only results, every stress condition, and the direct prior-evidence rule.', '',
             'This experiment recognizes four completed application outcomes: neither, a remote hash computation, complete object persistence at the receiver, or both. They are harmless custom-service analogues performed by three loopback worker processes on one operating system. They are not verified malicious lateral movement or theft.', '',
             '**Transfer means complete persisted object, not any bytes leaving the sender.** Every RPC carries a dummy buffer in its HTTP body, including hash-only and denied requests. Failed transfer operations can persist a partial object while receiving a negative completed-transfer label. Therefore a negative transfer label does not mean zero transmitted bytes, zero data exposure, or no exfiltration; a positive label does not establish unauthorized theft.', '',
             'The model fits only episodes where the requested current operation matches the preceding operation. The **linked** test subset deliberately retains that engineered relationship; the **crossed** subset actively mismatches the two requested operations. The **factorial_all** population contains both subsets and fully crosses prior and current requests, making those requests independent by construction. It is their union, not an additional independent sample. A high linked score measures predictable scripted workflow, not general attack understanding.', '',
             'The six main arms exclude current elapsed time. The timing arm is a separate diagnostic. The current baseline already includes observed prior-record volume and availability controls; adding history tests event-type, success, and byte information beyond those controls.', '',
             'All values average three fits evaluated on identical observations. The seeds are not three independent collections; no confidence interval or significance claim is made. Counts can be fractional because they average fits.', '',
             '## Execution and split counts', '',
             '| Partition | Linked episodes | Crossed episodes |', '|---|---:|---:|']
    for partition in ['fit', 'calibration', 'test']:
        c = e['counts'][partition]
        lines.append(f"| {partition} | {c['linked']['rows']} | {c['crossed']['rows']} |")
    lines += ['', 'Only linked fit episodes train the models. Calibration predictions are saved; no calibrated threshold or tuning result is claimed. Whole blocks define the fixed splits. Stress versions and counterfactual twins add no independent physical runs.', '',
              '## Primary clean comparison: matched, mismatched, and full-factorial workflows', '',
              '| Arm | Linked all F1 | Crossed all F1 | Factorial all F1 | Linked status-200 F1 | Crossed status-200 F1 | Factorial status-200 F1 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for arm in ARMS + COMPARATORS:
        m = means[arm]['clean']
        values = [m[p][s]['macro_f1'] for s in SUBSETS for p in POPULATIONS]
        lines.append('| ' + LABELS[arm] + ' | ' + ' | '.join(num(v) for v in values) + ' |')
    lines += ['', '**Read status-200 rows alongside the full population.** Authentication denials and failed operations have outcome “Neither”; these easier cases can raise overall accuracy. Status 200 removes those failures but still includes successful requests for neither operation. Four-class macro-F1 always includes all four classes.', '',
              '## Paired contrasts', '',
              'Every contrast is candidate minus reference on the same rows and fit seeds. AP is average precision for each operation bit, obtained by summing the appropriate class probabilities; it is distinct from four-class macro-F1.', '']
    for subset in SUBSETS:
        lines += ['### ' + ('All test transactions' if subset == 'all' else 'Status-200 transactions'), '',
                  '| Comparison / condition | Linked F1 change | Crossed F1 change | Factorial F1 change | Linked transfer AP change | Crossed transfer AP change | Factorial transfer AP change |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        rows = [r for r in e['contrasts'] if r['subset'] == subset and r['population'] == 'linked']
        for r in rows:
            group = [next(v for v in e['contrasts'] if all(v[k] == r[k] for k in ['candidate', 'reference', 'condition', 'subset']) and v['population'] == pop)['mean_delta'] for pop in POPULATIONS]
            values = [v[key] for key in ['macro_f1', 'transfer_ap'] for v in group]
            lines.append('| ' + r['purpose'] + ' / ' + CONDITION_LABELS[r['condition']] + ' | ' + ' | '.join(pp(v) for v in values) + ' |')
    lines += ['', '## Complete outcome results', '',
              'All seven learned arms and both comparators are retained under every condition. “Remote” means completed hash computation; “transfer” means a complete persisted object with matching bytes and hash. Neither output identifies malicious intent or absence of partial exposure. Precision, recall, F1, AP, and ROC AUC are available for both outputs and every subset in [EVIDENCE.json](EVIDENCE.json), including all seed-level confusion matrices.', '']
    for condition in CONDITIONS:
        lines += ['### ' + CONDITION_LABELS[condition], '']
        for population in POPULATIONS:
            lines += ['#### ' + population.capitalize() + ' test population', '',
                      '| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |',
                      '|---|---:|---:|---:|---:|']
            for arm in ARMS + COMPARATORS:
                m = means[arm][condition][population]
                lines.append(f"| {LABELS[arm]} | {pct(m['all']['accuracy'])} | {num(m['all']['macro_f1'])} | {pct(m['status200_only']['accuracy'])} | {num(m['status200_only']['macro_f1'])} |")
            for operation in ['remote', 'transfer']:
                lines += ['', 'Status-200 ' + operation + ' outcome:', '',
                          '| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |',
                          '|---|---:|---:|---:|---:|---:|---:|']
                for arm in ARMS + COMPARATORS:
                    m = means[arm][condition][population]['status200_only']['outcomes'][operation]
                    lines.append(f"| {LABELS[arm]} | {pct(m['precision'])} | {pct(m['recall'])} | {num(m['f1'])} | {num(m['ap'])} | {num(m['roc_auc'])} | {num(m['tp'],2)} / {num(m['fp'],2)} / {num(m['fn'],2)} |")
            lines.append('')
    lines += ['## Hidden-policy identifiability check', '',
              'Each completed-operation observation is copied into two counterfactual interpretations with opposite hidden authorization labels. The technical feature vector and prediction remain identical. These are not extra physical executions or independent samples. With policy context withheld, the paired construction forces accuracy and ROC AUC to 0.5; this is an identifiability demonstration, not empirical chance performance on a real maliciousness benchmark.', '',
              '| Arm | Linked underlying operations | Crossed underlying operations | Factorial underlying operations | Accuracy / AUC in each population |',
              '|---|---:|---:|---:|---:|']
    for arm in ARMS:
        group = [e['hidden_policy_twins'][arm][p] for p in POPULATIONS]
        counts = ' | '.join(num(v['underlying_completed_operations'],0) for v in group)
        metrics = '; '.join(p + ': ' + pct(v['accuracy']) + ' / ' + num(v['roc_auc']) for p, v in zip(POPULATIONS,group))
        lines.append(f"| {LABELS[arm]} | {counts} | {metrics} |")
    lines += ['', '## Interpretation boundaries', '',
              '- The direct rule reads earlier successful remote-job and file-write evidence and uses the current success status. Matching that rule does not establish special value from machine learning.',
              '- The role permutation changes logical metadata for identical worker processes. It is not a new host population, a real organizational role change, or domain-transfer validation.',
              '- The 50 ms condition is a synthetic arrival shift. It is not a measured production delay distribution or a clock-synchronization repair experiment. Dropping remote-job or file-write records removes one observation channel while preserving the fixed outcomes and test queries.',
              '- The observations describe post-transaction interpretation with only strictly earlier history. They do not demonstrate warning before an action occurs, blocking, or prevented exfiltration.',
              '- The authorization twins expose missing policy information. They do not substitute for independently executed normal-admin and malicious attack campaigns.',
              '- The literature note describes prospective design requirements. This realized run did not execute separate authorized-admin and unauthorized-attack campaigns; it executed harmless operation/outcome combinations and later paired opposite hidden-policy interpretations.',
              '- The separately implemented audit verifies saved calculations and operation artifacts. It is not independent human labeling, peer review, or external deployment validation.', '',
              'The applicable research context and prior-art overlap are in [LITERATURE_SCOPE.md](../../verified_stage_lab/LITERATURE_SCOPE.md). The defensible contribution is measured sensitivity to information and workflow assumptions, if supported by the audited results; novelty remains unestablished.', '',
              '## Provenance', '',
              f"- Frozen protocol SHA256: `{e['provenance']['protocol_sha256']}`.",
              f"- Private completed summary SHA256: `{e['provenance']['summary_sha256']}`.",
              '- Public files contain aggregate metrics and hashes. Raw observations, probabilities, model files, worker receipts, and private paths are excluded.',
              '- [SUMMARY.json](SUMMARY.json) provides the compact result index; [EVIDENCE.json](EVIDENCE.json) preserves the full aggregate and seed-level metric roster; [PUBLICATION.json](PUBLICATION.json) binds these public files.', '']
    return '\n'.join(lines)


def validate_audit(path, summary_sha):
    audit = read(path)
    require(audit.get('audit_status') == 'PASS', 'Independent audit has not passed')
    for section in ['collection', 'preparation', 'models']:
        require(audit.get(section, {}).get('audit_status') == 'PASS',
                'Complete collection, preparation, and model audit required')
    require(audit['models'].get('summary_sha256') == summary_sha,
            'Audit does not bind this completed summary')
    require(audit['models'].get('models_audited') == 21, 'Audit model roster differs')
    require(audit['models'].get('metric_tables_recomputed') == 810, 'Audit metric roster differs')
    require([x['seed'] for x in audit['models'].get('seed_receipts', [])] == SEEDS
            and all(x['models'] == 7 for x in audit['models']['seed_receipts']), 'Audit seed roster differs')
    require(audit.get('auditor_sha256') == sha(Path(__file__).with_name('audit.py')),
            'Independent auditor source binding differs')
    return audit


def publish(run, output, protocol, audit_path=None):
    summary, cell_hashes, source_hashes = validate_run(run, protocol)
    summary_sha = sha(run / 'SUMMARY.json')
    audit = validate_audit(audit_path, summary_sha) if audit_path else None
    if audit:
        require(audit['preparation']['prepared_sha256'] == summary['receipt']['prepared_sha256']
                and audit['preparation']['protocol_sha256'] == sha(protocol)
                and audit['preparation']['counts'] == summary['preparation']['counts'],
                'Audited preparation differs from completed run')
        require(audit['collection']['collection_receipt_sha256'] == summary['preparation']['collection_receipt_sha256'],
                'Audited collection differs from prepared input')
        for cell in audit['models']['seed_receipts']:
            folder = run / str(cell['seed'])
            require(cell['prediction_sha256'] == sha(folder / 'PREDICTIONS.npz')
                    and cell['metrics_sha256'] == sha(folder / 'METRICS.json'), 'Audited cell binding differs')
    means = {arm: average([(r['arms'] if arm in ARMS else r['comparators'])[arm] for r in summary['seeds']])
             for arm in ARMS + COMPARATORS}
    evidence = {'status': 'COMPLETE', 'scope': 'Controlled loopback application outcomes: remote hash computation and complete object persistence; no operational APT or novelty claim',
                'label_limits': 'Every RPC transmits a dummy buffer. Failed transfer can persist partial bytes. A negative completed-transfer label does not establish zero transmission or exposure; a positive label does not establish unauthorized theft.',
                'audit': {'status': 'PASS' if audit else 'PENDING', 'source_summary_sha256': summary_sha},
                'seeds': SEEDS, 'models_fitted': 21, 'arms': ARMS, 'comparators': COMPARATORS,
                'conditions': CONDITIONS, 'populations': POPULATIONS, 'subsets': SUBSETS, 'class_order': CLASSES,
                'counts': summary['preparation']['counts'], 'means': means, 'contrasts': contrasts(summary),
                'hidden_policy_twins': {arm: average([r['hidden_policy_twins'][arm] for r in summary['seeds']]) for arm in ARMS},
                'per_seed': summary['seeds'],
                'provenance': {'summary_sha256': summary_sha, 'started_sha256': sha(run / 'STARTED.json'),
                               'complete_sha256': sha(run / 'COMPLETE.json'),
                               'protocol_sha256': sha(protocol), 'prepared_sha256': summary['receipt']['prepared_sha256'],
                               'preparation_sha256': summary['receipt']['preparation_sha256'],
                               'collection_receipt_sha256': summary['preparation']['collection_receipt_sha256'],
                               'seed_complete_sha256': cell_hashes, 'frozen_source_sha256': source_hashes,
                               'publisher_sha256': sha(Path(__file__))},
                'runtime': {'fit_and_prediction_elapsed_seconds': summary['receipt']['elapsed_seconds'],
                            'cloud_compute_started': summary['receipt']['cloud_compute_started']},
                'environment': summary['receipt'].get('environment', {})}
    compact = {k: evidence[k] for k in ['status', 'scope', 'audit', 'seeds', 'models_fitted', 'counts', 'runtime', 'provenance']}
    compact['clean_primary_comparison'] = {a: means[a]['clean'] for a in ['current', 'current_roles_history', 'prior_evidence_rule', 'majority']}
    compact['clean_paired_contrasts'] = [r for r in evidence['contrasts'] if r['condition'] == 'clean']
    output.mkdir(parents=True, exist_ok=True)
    owned = {'REPORT.md', 'EVIDENCE.json', 'SUMMARY.json', 'PUBLICATION.json', 'AUDIT.json'}
    existing = {p.name for p in output.iterdir()}
    require(existing <= owned, 'Output contains unrelated files')
    if existing:
        require((output / 'PUBLICATION.json').is_file(), 'Preserve incomplete publication; use a fresh output')
        old = read(output / 'PUBLICATION.json')
        require(old['source_summary_sha256'] == summary_sha, 'Existing publication binds a different run')
        for name, digest in old['artifact_sha256'].items():
            require(name in owned and sha(output / name) == digest, 'Existing publication changed')
        require(not (old['audit_status'] == 'PASS' and audit is None), 'Cannot downgrade an audited publication')
    write(output / 'EVIDENCE.json', evidence)
    write(output / 'SUMMARY.json', compact)
    (output / 'REPORT.md').write_text(render_report(evidence), encoding='utf-8')
    if audit:
        write(output / 'AUDIT.json', audit)
    names = ['EVIDENCE.json', 'SUMMARY.json', 'REPORT.md'] + (['AUDIT.json'] if audit else [])
    write(output / 'PUBLICATION.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
                                       'status': 'COMPLETE', 'audit_status': evidence['audit']['status'],
                                       'source_summary_sha256': summary_sha,
                                       'publisher_sha256': sha(Path(__file__)),
                                       'artifact_sha256': {name: sha(output / name) for name in names}})
    return compact


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--protocol', type=Path, default=Path(__file__).with_name('protocol.json'))
    p.add_argument('--audit', type=Path)
    args = p.parse_args()
    result = publish(args.run, args.output, args.protocol, args.audit)
    print(json.dumps({'status': result['status'], 'audit': result['audit']['status'], 'models_fitted': result['models_fitted']}))


if __name__ == '__main__':
    main()
