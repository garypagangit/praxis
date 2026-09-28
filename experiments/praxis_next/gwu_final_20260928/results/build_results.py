"""Publish existing evidence only: no fitting, inference, downloads, or threshold changes."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math
import shutil
import statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[1]
TABLES = HERE / 'tables'
FIGS = HERE / 'figures'
SNAPS = HERE / 'source_snapshots'
for directory in (TABLES, FIGS, SNAPS):
    directory.mkdir(parents=True, exist_ok=True)
INPUTS = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(relative, snapshot=None):
    path = BASE / relative
    INPUTS.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size})
    if snapshot:
        shutil.copyfile(path, SNAPS / snapshot)
    return json.loads(path.read_text(encoding='utf-8'))

def writejson(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def writecsv(name, rows):
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with (TABLES / name).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

def copy_evidence(relative, output):
    source = BASE / relative
    INPUTS.append({'path': source.relative_to(ROOT).as_posix(), 'sha256': sha(source), 'bytes': source.stat().st_size})
    shutil.copyfile(source, TABLES / output)

sources = {
    'PX080': 'px080_context_selector/results/METRICS.json',
    'PX081': 'px081_evidence_acquisition/RESULTS.json',
    'PX082': 'px082_temporal_audit/METRICS.json',
    'PX083': 'px083_policy_transfer/results/METRICS.json',
}
raw = {study: load(path, study + '_METRICS.json') for study, path in sources.items()}
capture081 = load('px081_evidence_acquisition/CAPTURE_RESULTS.json', 'PX081_CAPTURE_METRICS.json')
native_controls = load('px083_policy_transfer/results/ORIGINAL_THRESHOLD_CONTROLS.json', 'PX083_ORIGINAL_THRESHOLD_CONTROLS.json')
paired = load('measurement_praxis/evidence/paired_reanalysis/MEANS.json', 'PAIRED_MEANS.json')['groups']
sensitivity = load('submission_readiness/sensitivity/SUMMARY.json', 'SENSITIVITY_SUMMARY.json')['groups']
seed_omissions = load('submission_readiness/sensitivity/SEED_OMISSIONS.json', 'SEED_OMISSIONS.json')['groups']
qualification = load('d1_benchmark_audit/QUALIFICATION.json', 'QUALIFICATION.json')
design = load('px082_temporal_audit/DESIGN.json', 'PX082_DESIGN.json')
cutoffs = load('d1_benchmark_audit/SUPPORT_CUTOFF_AUDIT.json', 'SUPPORT_CUTOFF_AUDIT.json')
refs = load('measurement_praxis/references.json', 'VERIFIED_REFERENCES.json')
dataset_refs = [r for r in refs if r['id'] in ['myneni2023', 'myneni2020', 'liu2022', 'liu2022dataset', 'shadabfar2025', 'tijjani2026withdrawn']]
dataset_refs += [
    {'id': 'kilian2025', 'apa': 'Kilian, S., Viet Triem Tong, V., Lalande, J.-F., Majorczyk, F., Sanchez, A., Talon, N., Besson, P.-V., Orsini, H., Lledo, P., & Gimenez, P.-F. (2025). CasinoLimit: An offensive dataset labeled with MITRE ATT&CK techniques. In 2025 28th International Symposium on Research in Attacks, Intrusions and Defenses (RAID). IEEE. https://doi.org/10.1109/RAID67961.2025.00039',
     'url': 'https://doi.org/10.1109/RAID67961.2025.00039', 'publication_status': 'Peer-reviewed RAID 2025 paper; verified in existing September 23 primary-source audit.',
     'support_scope': 'CasinoLimit source and technique annotation; does not validate our label construction or its equivalence to benign/attack flows.', 'dataset_url': 'https://zenodo.org/records/17256954'},
    {'id': 'landauer2026', 'apa': 'Landauer, M., Hotwagner, W., Boenke, T., Skopik, F., & Wurzenberger, M. (2026). CAM-LDS: Cyber attack manifestations for automatic interpretation of system logs and security alerts. International Journal of Information Security, 25(5), Article 148. https://doi.org/10.1007/s10207-026-01318-x',
     'url': 'https://doi.org/10.1007/s10207-026-01318-x', 'publication_status': 'Peer-reviewed journal version of record, August 26, 2026; existing September 23 primary-source audit.',
     'support_scope': 'CAM-LDS source and log/alert setting; the secondary analysis tests T1105 interval proxies, not the primary exfiltration task.', 'dataset_url': 'https://zenodo.org/records/18861762'}]
writejson(HERE / 'REFERENCES.json', dataset_refs)
for relative in ['paper/REFERENCES.md', 'px080_context_selector/PROTOCOL.md', 'px081_evidence_acquisition/PROTOCOL.md', 'px083_policy_transfer/PROTOCOL.md', 'px083_policy_transfer/results/DIAGNOSTICS.json', 'd1_benchmark_audit/DATASET_QUALIFICATION.md', '../apt_benchmark/host_history_exfil/DATA_INVENTORY.md', '../apt_benchmark/host_history_exfil/context.py', '../apt_benchmark/host_history_exfil/run.py']:
    path = (BASE / relative).resolve()
    INPUTS.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size})
for source, name in [
 ('measurement_praxis/evidence/paired_reanalysis/PAIRED_METRICS.csv', 'paired_stage_metrics.csv'),
 ('measurement_praxis/evidence/paired_reanalysis/MEANS.csv', 'paired_group_means.csv'),
 ('measurement_praxis/evidence/paired_reanalysis/DIRECTION_COUNTS.json', 'paired_direction_counts.json'),
 ('submission_readiness/sensitivity/CAPTURE_OMISSIONS.csv', 'capture_omissions.csv'),
 ('submission_readiness/sensitivity/SEED_OMISSIONS.csv', 'seed_omissions.csv'),
 ('submission_readiness/sensitivity/AGGREGATE_EQUIVALENCE.json', 'aggregate_equivalence.json'),
 ('measurement_praxis/evidence/qualification_audit/NATIVE_CLASS_COUNTS.csv', 'native_class_counts.csv'),
]:
    copy_evidence(source, name)

CLASSES = ['Benign', 'OtherAttackStage', 'LateralMovement', 'DataExfiltration']
CLASS_KEYS_081 = ['benign', 'other_attack', 'movement', 'exfiltration']
arms, stages, confusions, subgroups, subgroup_stages = [], [], [], [], []
checks = []

def metric_rows(study, record, identity, aggregate=False):
    cm = np.asarray(record['confusion'], dtype=np.int64)
    names = ['OtherTechnique', 'T1105'] if study == 'PX083' else CLASSES
    supports = cm.sum(axis=1)
    predicted = cm.sum(axis=0)
    n = int(cm.sum())
    declared_n = record.get('rows', record.get('n'))
    assert n == declared_n, (study, identity, n, declared_n)
    result = dict(identity)
    for key, value in record.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
    result['rows'] = n
    result['negative_support'] = int(supports[0])
    result['negative_flags'] = int(cm[0, 1:].sum())
    result['negative_flag_rate'] = int(cm[0, 1:].sum()) / int(supports[0]) if supports[0] else None
    result['negative_definition'] = 'Other author technique labels; not verified benign' if study == 'PX083' else 'Author benign flow labels'
    if study == 'PX083':
        per_class = {'T1105': record}
    elif study == 'PX081':
        per_class = {name: record[key] for name, key in zip(CLASSES, CLASS_KEYS_081)}
    else:
        per_class = record.get('classes', record.get('per_class'))
    stage_rows = []
    computed_f1 = []
    for i, name in enumerate(names):
        tp = int(cm[i, i]); support = int(supports[i]); pred_n = int(predicted[i])
        precision = tp / pred_n if pred_n else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * tp / (support + pred_n) if support + pred_n else 0.0
        computed_f1.append(f1)
        stored = per_class.get(name, {})
        for key, calculated in [('precision', precision), ('recall', recall), ('f1', f1)]:
            if key in stored and stored[key] is not None:
                assert math.isclose(stored[key], calculated, rel_tol=1e-11, abs_tol=1e-12), (study, key, stored[key], calculated)
        sr = {**identity, 'class': name, 'support': support, 'predicted_count': pred_n, 'true_positive_count': tp,
              'precision': stored.get('precision', precision), 'exact_recall': stored.get('recall', recall),
              'f1': stored.get('f1', f1), 'average_precision': stored.get('ap'), 'roc_auc': stored.get('roc_auc'),
              'ranking_metric_status': 'source reported; blank if unsupported' if stored else 'not reported for this class',
              'recall_supported': support > 0,
              'warning_recall': 1 - int(cm[i, 0]) / support if study != 'PX083' and i > 0 and support else None,
              'missed_warning_count': int(cm[i, 0]) if study != 'PX083' and i > 0 else None,
              'wrong_attack_stage_count': int(support - cm[i, i] - cm[i, 0]) if study != 'PX083' and i > 0 else None,
              'target_false_negative_count': int(cm[1, 0]) if study == 'PX083' and i == 1 else None,
              'warning_scope': 'Not applicable: binary T1105-vs-other-technique, not attack-vs-benign' if study == 'PX083' else 'Any non-benign predicted label'}
        stage_rows.append(sr)
        if name in ('LateralMovement', 'DataExfiltration'):
            prefix = 'movement' if name == 'LateralMovement' else 'exfiltration'
            result[prefix + '_support'] = support
            result[prefix + '_exact_recall'] = sr['exact_recall']
            result[prefix + '_warning_recall'] = sr['warning_recall']
            result[prefix + '_f1'] = f1
            result[prefix + '_missed_warning_count'] = sr['missed_warning_count']
    if study != 'PX083':
        assert math.isclose(record['macro_f1'], statistics.mean(computed_f1), rel_tol=1e-11, abs_tol=1e-12)
    if aggregate:
        for i, actual in enumerate(names):
            for j, prediction in enumerate(names):
                confusions.append({**identity, 'true_class': actual, 'predicted_class': prediction, 'count': int(cm[i, j])})
    return result, stage_rows

for study, rows in raw.items():
    for index, row in enumerate(rows):
        identity = {'configuration_id': f'{study}-{index:04d}', 'study': study,
                    'dataset': row.get('dataset', 'UNRAVELED'), 'condition': row.get('condition', 'unperturbed'),
                    'view': row.get('view', ''), 'arm': row.get('arm', row.get('policy')),
                    'budget': row.get('budget'), 'reference_only': row.get('reference_only', False),
                    'fit_seed': row.get('seed'), 'perturbation_seed': row.get('perturbation_seed'),
                    'source_record_index': index, 'source_path': sources[study]}
        top, class_rows = metric_rows(study, row, identity, aggregate=True)
        arms.append(top); stages.extend(class_rows)
        for kind in ('by_capture', 'by_run'):
            for subgroup, metrics in row.get(kind, {}).items():
                si = {**identity, 'subgroup_type': kind, 'subgroup_id': subgroup}
                detail, detail_stages = metric_rows(study, metrics, si)
                subgroups.append(detail); subgroup_stages.extend(detail_stages)
        if 'department_to_private_services' in row:
            si = {**identity, 'subgroup_type': 'role_stratum', 'subgroup_id': 'department_to_private_services'}
            detail, detail_stages = metric_rows(study, row['department_to_private_services'], si)
            subgroups.append(detail); subgroup_stages.extend(detail_stages)
    checks.append({'study': study, 'configurations': len(rows), 'confusion_totals_and_precision_recall_f1': 'PASS'})

lookup081 = {(r['seed'], r['condition'], r['budget'], r['policy']): i for i, r in enumerate(raw['PX081'])}
for row in capture081:
    index = lookup081[row['seed'], row['condition'], row['budget'], row['policy']]
    parent = next(r for r in arms if r['configuration_id'] == f'PX081-{index:04d}')
    identity = {k: parent[k] for k in ('configuration_id', 'study', 'dataset', 'condition', 'view', 'arm', 'budget', 'reference_only', 'fit_seed', 'perturbation_seed', 'source_record_index', 'source_path')}
    identity.update(subgroup_type='by_capture', subgroup_id=str(row['capture']))
    detail, detail_stages = metric_rows('PX081', row, identity)
    subgroups.append(detail); subgroup_stages.extend(detail_stages)

assert len(arms) == 588
assert len(stages) == 1764
writecsv('all_configuration_metrics.csv', arms)
writecsv('all_class_metrics.csv', stages)
writecsv('all_confusion_counts.csv', confusions)
writecsv('all_subgroup_metrics.csv', subgroups)
writecsv('all_subgroup_class_metrics.csv', subgroup_stages)
native_rows = []
for index, row in enumerate(native_controls):
    identity = {'configuration_id': f'PX083-native-{index:04d}', 'study': 'PX083-original-threshold-supplement',
                'dataset': row['dataset'], 'condition': row['condition'], 'arm': row['arm'],
                'perturbation_seed': row['perturbation_seed'], 'source_record_index': index}
    result, _ = metric_rows('PX083', row, identity)
    native_rows.append(result)
writecsv('original_threshold_controls.csv', native_rows)

groups = defaultdict(list)
group_fields = ['study', 'dataset', 'condition', 'view', 'arm', 'budget', 'reference_only']
for row in arms:
    groups[tuple(row[k] for k in group_fields)].append(row)
summary = []
numeric_excluded = {'fit_seed', 'perturbation_seed', 'source_record_index', 'seed', 'budget', 'reference_only'}
for key, rows in groups.items():
    entry = dict(zip(group_fields, key))
    entry['n_views'] = len(rows)
    entry['mean_definition'] = 'same-event perturbation mean; one view unless random-loss condition' if key[0] == 'PX083' else 'three fits on same evaluation events'
    for field in dict.fromkeys(k for r in rows for k in r):
        vals = [r.get(field) for r in rows]
        if field not in numeric_excluded and all(isinstance(v, (float, int)) and not isinstance(v, bool) for v in vals):
            entry[field] = statistics.mean(vals)
    summary.append(entry)
writecsv('all_group_means.csv', summary)

class_groups = defaultdict(list)
for row in stages:
    class_groups[tuple(row[k] for k in group_fields) + (row['class'],)].append(row)
class_summary = []
for key, rows in class_groups.items():
    entry = dict(zip(group_fields + ['class'], key)); entry['n_views'] = len(rows)
    for field in ['support', 'predicted_count', 'true_positive_count', 'precision', 'exact_recall', 'f1', 'average_precision', 'roc_auc', 'warning_recall', 'missed_warning_count', 'wrong_attack_stage_count']:
        vals = [r[field] for r in rows]
        entry[field] = statistics.mean(vals) if all(v is not None for v in vals) else None
        entry[field + '_available_views'] = sum(v is not None for v in vals)
    class_summary.append(entry)
writecsv('all_class_group_means.csv', class_summary)

# Printable full arm inventory, including unfavorable and reference-only rows.
def fmt(value, digits=4, percentage=False):
    return 'NA' if value is None else (f'{value * 100:.2f}%' if percentage else f'{value:.{digits}f}')
parts = ['# Complete group-mean results', '',
 'All 308 arm/condition/budget group means are retained. PX080-082 means use three fits on the same records. PX083 uses three perturbations for random-loss conditions and one deterministic view otherwise. Counts may therefore be fractional. No displayed group is an independent campaign.', '',
 'Full per-fit precision, recall, F1, average precision, ROC-AUC, class supports, warning destinations and confusion counts are in the CSV tables. Blank ranking metrics mean unavailable; they are not replaced with invented estimates.', '']
for study in sources:
    parts += ['## ' + study, '']
    if study != 'PX083':
        parts += ['| Condition / view / budget | Arm | Macro-F1 | Exact recall: movement / exfil. | Exfil. warning recall | Benign flags |', '|---|---|---:|---:|---:|---:|']
        for row in summary:
            if row['study'] != study: continue
            condition = row['condition'] if study != 'PX082' else row['view']
            if row['budget'] is not None: condition += f" / B{row['budget']}"
            arm = row['arm'] + (' (unrestricted reference)' if row['reference_only'] else '')
            parts += [f"| {condition} | {arm} | {fmt(row.get('macro_f1'))} | {fmt(row.get('movement_exact_recall'), percentage=True)} / {fmt(row.get('exfiltration_exact_recall'), percentage=True)} | {fmt(row.get('exfiltration_warning_recall'), percentage=True)} | {fmt(row['negative_flags'], 2)} |"]
    else:
        for dataset in ['casino', 'camlds']:
            parts += ['### ' + dataset, '', '| Condition | Arm | T1105 F1 | Recall | AP / ROC-AUC | Other-label flags |', '|---|---|---:|---:|---:|---:|']
            for row in summary:
                if row['study'] != study or row['dataset'] != dataset: continue
                parts += [f"| {row['condition']} | {row['arm']} | {fmt(row.get('f1'))} | {fmt(row.get('recall'), percentage=True)} | {fmt(row.get('ap'))} / {fmt(row.get('roc_auc'))} | {fmt(row['negative_flags'], 2)} |"]
            parts += ['']
    parts += ['']
(HERE / 'COMPLETE_GROUP_TABLES.md').write_text('\n'.join(parts).rstrip() + '\n', encoding='utf-8')

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 14, 'axes.titlesize': 16,
                     'axes.labelsize': 14, 'xtick.labelsize': 14, 'ytick.labelsize': 14,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42,
                     'savefig.dpi': 220})
TEAL, RED, NAVY = '#087F8C', '#B9473E', '#24385B'
FIGURE_RECORDS = []
def save(fig, name, caption):
    fig.savefig(FIGS / (name + '.png'), bbox_inches='tight', facecolor='white')
    fig.savefig(FIGS / (name + '.pdf'), bbox_inches='tight', facecolor='white', metadata={'Title': caption})
    plt.close(fig)
    FIGURE_RECORDS.append({'id': name, 'caption': caption,
        'png': 'figures/' + name + '.png', 'pdf': 'figures/' + name + '.pdf',
        'png_sha256': sha(FIGS / (name + '.png')), 'pdf_sha256': sha(FIGS / (name + '.pdf'))})

# Figure 4: the complete nine acquisition group means; favorable groups not selected.
g81 = [r for r in paired if r['study'] == 'PX081']
labels = [r['condition'].replace('delayed_unavailable', 'Delayed / unavailable').replace('wrong_host_history', 'Wrong-host history').replace('clean', 'Clean') + f" | B{r['budget']}" for r in g81]
fig, axes = plt.subplots(1, 3, figsize=(13.4, 7), sharey=True, gridspec_kw={'width_ratios': [1, 1.1, 1]})
for ax, metric, scale, title in zip(axes, ['macro_f1', 'DataExfiltration.warning_recall', 'benign_false_alert_count'], [100, 100, 1], ['Macro-F1 change\n(score points; ×100)', 'Exfil. warning change\n(percentage points)', 'Benign alert change\n(records per fit)']):
    values = [r['means']['delta'][metric] * scale for r in g81]
    ax.axvline(0, color='#8A929C', lw=0.8)
    colors = [TEAL if (v >= 0 if metric != 'benign_false_alert_count' else v <= 0) else RED for v in values]
    ax.barh(np.arange(9), values, color=colors, height=.56)
    span = max(values) - min(values) or 1
    for i, value in enumerate(values):
        ax.text(value + (.025 * span if value >= 0 else -.025 * span), i, f'{value:+.2f}' if scale == 100 else f'{value:+.1f}', va='center', ha='left' if value >= 0 else 'right', fontsize=14)
    ax.set_title(title, pad=12); ax.margins(x=.45); ax.grid(axis='x', alpha=.15)
axes[0].set_yticks(np.arange(9), labels); axes[0].invert_yaxis()
fig.suptitle('Higher overall scores can accompany fewer exfiltration warnings', fontsize=18, color=NAVY, y=.98)
fig.text(.5, .02, 'Error-focused minus entropy acquisition; means of 3 fits on 208,094 shared flows.\nExfiltration denominator: 3,442. Benign denominator: 192,193.\nCosts, delays, and failures are simulated.', ha='center', fontsize=14)
fig.tight_layout(rect=(0, .19, 1, .93))
save(fig, 'fig04_acquisition_complete_tradeoffs', 'All nine acquisition group means. Directions are candidate minus baseline; no pooled uncertainty or independent-replication claim.')

# Figure 5: all selector arms and all five conditions.
arms80 = ['current_roles', 'context', 'fixed_fusion', 'confidence_gate', 'ordinary_gate', 'stage_harm_gate', 'context_dropout']
display80 = ['Current + roles', 'Context', 'Equal fusion', 'Confidence gate', 'Ordinary gate', 'Stage-harm gate', 'Context dropout']
colors80 = ['#24385B', '#9B59B6', '#C38C25', '#8A8A8A', '#2784BA', '#B9473E', '#087F8C']
conditions80 = ['clean', 'missing_half', 'missing_all', 'stale_5min', 'wrong_host']
fig, axes = plt.subplots(1, 2, figsize=(13.4, 7), sharey=True)
for ax, field, scale, title, cmap, vmax in zip(axes,
        ['movement_exact_recall', 'negative_flags'], [100, 1],
        ['Movement recall (%)\nHigher is better; denominator 35', 'Benign false alerts\nLower is better; denominator 192,193'],
        ['Blues', 'Oranges'], [85, 145]):
    values = np.array([[next(r for r in summary if r['study'] == 'PX080' and r['condition'] == condition and r['arm'] == arm)[field] * scale for condition in conditions80] for arm in arms80])
    ax.imshow(values, cmap=cmap, vmin=0, vmax=vmax, aspect='auto')
    for (i, j), value in np.ndenumerate(values):
        ax.text(j, i, f'{value:.1f}', ha='center', va='center', fontsize=14, color='white' if value > vmax * .72 else '#17232F')
    ax.set_xticks(range(5), ['Clean', 'Half\nmissing', 'All\nmissing', 'Stale\n5 min', 'Wrong\nhost'], fontsize=14)
    ax.set_yticks(range(7), display80, fontsize=14)
    ax.set_title(title, fontsize=16, pad=15)
fig.suptitle('Context selection: movement recall and false-alert tradeoffs', fontsize=18, color=NAVY, y=.98)
fig.text(.5, .02, 'Every cell is a mean of 3 fits on the same flows; darker shading means more of that quantity.\nMovement labels denote Remote System Discovery on one host pair.\nMissing, stale, and wrong-host histories are simulated.', ha='center', fontsize=14)
fig.tight_layout(rect=(0, .20, 1, .93))
save(fig, 'fig05_selector_stage_workload', 'All seven context-selection arms under all five conditions; three-fit means, with the same rare-stage and benign denominators.')

# Figure 6: full mean and all three leave-one-seed means; fixed predictions.
full = next(r for r in sensitivity if r['spec']['study'] == 'PX081' and r['spec']['condition'] == 'clean' and r['spec']['budget'] == 3)
omits = [r for r in seed_omissions if r['spec']['study'] == 'PX081' and r['spec']['condition'] == 'clean' and r['spec']['budget'] == 3]
points = [full['full_three_seed_mean']['delta']] + [r['point']['delta'] for r in omits]
labels = ['All 3 fitting seeds'] + [f"Omit seed {r['omitted_seed']}" for r in omits]
fig, axes = plt.subplots(1, 3, figsize=(13.4, 6.3), sharey=True)
for ax, key, scale, title in zip(axes, ['macro_f1', 'exfil_warning_recall', 'exfil_to_benign_count'], [100, 100, 1], ['Macro-F1 change\n(score points; ×100)', 'Exfil. warning change\n(percentage points)', 'Extra exfil. → benign\n(mean records per fit)']):
    values = [r[key] * scale for r in points]
    ax.axvline(0, color='#8A929C', lw=.8)
    for i, value in enumerate(values):
        ax.plot([0, value], [i, i], color=TEAL if key == 'macro_f1' else RED, lw=3, alpha=.55)
        ax.scatter([value], [i], color=TEAL if key == 'macro_f1' else RED, s=60)
        ax.annotate(f'{value:+.2f}', (value, i), xytext=(5 if value >= 0 else -5, 9), textcoords='offset points', ha='left' if value >= 0 else 'right', fontsize=14)
    ax.set_title(title); ax.margins(x=.5, y=.24); ax.grid(axis='x', alpha=.15)
axes[0].set_yticks(range(4), labels); axes[0].invert_yaxis()
fig.suptitle('One fitting seed accounts for most of the headline warning loss', fontsize=18, color=NAVY, y=.98)
fig.text(.5, .02, 'Clean budget 3; error-focused minus entropy acquisition. Fixed predictions, not refits.\nWithout seed 8101: +0.65 F1 score points; −0.36 warning percentage points.\nOmission ranges are not confidence intervals.', ha='center', fontsize=14)
fig.tight_layout(rect=(0, .22, 1, .92))
save(fig, 'fig06_fitting_seed_influence', 'Full three-fit mean and every leave-one-fit-out mean for the same clean budget-three comparison.')

# Figure 7: native labels remain native; no artificial taxonomy harmonization.
with (TABLES / 'native_class_counts.csv').open(encoding='utf-8') as handle:
    native = list(csv.DictReader(handle))
fig, axes = plt.subplots(1, 3, figsize=(13.4, 7))
for ax, dataset, subtitle in zip(axes, ['SCVIC-APT-2021', 'DAPT2020', 'DSRL-APT-2023'], ['Recorded clock not qualified', 'No all-class single time cutoff', 'Synthetic derivative of DAPT']):
    rows = [r for r in native if r['dataset'] == dataset]
    values = [int(r['observed_rows']) for r in rows]
    y = np.arange(len(rows))
    ax.barh(y, values, color=[NAVY if 'Benign' in r['native_class'] or 'Normal' in r['native_class'] else TEAL for r in rows], height=.6)
    ax.set_yticks(y, [r['native_class'].replace('DataExfiltration', 'Data Exfiltration').replace('InitialCompromise', 'Initial Compromise').replace('LateralMovement', 'Lateral Movement').replace('NormalTraffic', 'Normal Traffic') for r in rows], fontsize=14)
    ax.set_xscale('log'); ax.set_xlim(1, 1200000); ax.invert_yaxis()
    ax.set_xticks([1, 1000, 1000000], ['1', '1,000', '1,000,000'], fontsize=14)
    for i, value in enumerate(values):
        ax.text(value * (.84 if value >= 500 else 1.2), i, f'{value:,}', va='center', ha='right' if value >= 500 else 'left', fontsize=14, color='white' if value >= 500 else '#17232F')
    ax.set_title(dataset + '\n' + subtitle.replace(' ', '\n', 1), fontsize=14)
    ax.set_xlabel('Released rows\n(log scale)'); ax.grid(axis='x', alpha=.13)
fig.suptitle('Row counts do not establish independent temporal evaluation', fontsize=18, color=NAVY, y=.98)
fig.text(.5, .02, 'Native labels and counts from inspected release bytes; DSRL derives from DAPT.\nS-DAPT has no bar because no qualified dataset bytes were acquired.\nAn unavailable measurement is not zero rows.', ha='center', fontsize=14)
fig.tight_layout(rect=(0, .22, 1, .90), w_pad=2)
save(fig, 'fig07_native_support_and_lineage', 'All native-class counts for the three inspected extension artifacts with measured bytes; no S-DAPT counts are fabricated.')

# Figure 8: every secondary condition; binary target and negative semantics remain separate.
conditions83 = ['clean', 'random_25', 'random_50', 'random_75', 'support_burst_60', 'command_records_absent', 'delay_30_deadline_0', 'delay_30_deadline_30', 'delay_120_deadline_0', 'delay_120_deadline_30', 'delay_120_deadline_120', 'execve_absent', 'proctitle_absent', 'syscall_absent', 'path_absent']
fig, axes = plt.subplots(1, 2, figsize=(13.4, 8), sharey=True)
for ax, dataset, denom in zip(axes, ['casino', 'camlds'], ['17 T1105 / 903 other-label targets', '100 T1105 / 4,109 other-label targets']):
    values = []
    for condition in conditions83:
        a = next(r for r in summary if r['study'] == 'PX083' and r['dataset'] == dataset and r['condition'] == condition and r['arm'] == 'current')
        b = next(r for r in summary if r['study'] == 'PX083' and r['dataset'] == dataset and r['condition'] == condition and r['arm'] == 'target_cost_gate')
        values.append([(b['recall'] - a['recall']) * 100, (b['negative_flag_rate'] - a['negative_flag_rate']) * 100])
    values = np.asarray(values)
    ax.imshow(values, cmap='RdBu_r', vmin=-70, vmax=70, aspect='auto')
    for (i, j), value in np.ndenumerate(values):
        ax.text(j, i, f'{value:+.2f}', ha='center', va='center', color='white' if abs(value) > 40 else '#18232C', fontsize=14)
    ax.set_xticks([0, 1], ['T1105 recall Δ\n(higher is better)', 'Other-label flag Δ\n(lower is better)'], fontsize=14)
    ax.set_yticks(range(len(conditions83)), [s.replace('_', ' ') for s in conditions83], fontsize=14)
    ax.set_title(('CasinoLimit' if dataset == 'casino' else 'CAM-LDS') + '\n' + denom, fontsize=14)
fig.suptitle('Secondary T1105 transfer: benefits and costs vary by condition', fontsize=18, color=NAVY, y=.98)
fig.text(.5, .02, 'Target-cost minus current expert, percentage points. Red means an increase, not uniform benefit.\nRandom loss averages 3 perturbations; other conditions are deterministic.\nOther-label flags are not benign false alarms.', ha='center', fontsize=14)
fig.tight_layout(rect=(0, .20, 1, .93))
save(fig, 'fig08_secondary_policy_transfer', 'All 15 secondary conditions on each source. The target-cost gate matches the context expert’s hard decisions in all 21 views per source; these are not exfiltration results.')

writejson(HERE / 'FIGURES.json', FIGURE_RECORDS)
writejson(HERE / 'SOURCE_MANIFEST.json', {'purpose': 'Publication assembly from completed evidence only', 'new_model_fits': 0, 'new_inference': 0, 'threshold_changes': 0, 'build_source_sha256': sha(Path(__file__)), 'inputs': INPUTS})
coverage = {'configuration_records': {k: len(v) for k, v in raw.items()}, 'total_configuration_records': len(arms),
            'class_metric_rows': len(stages), 'confusion_count_rows': len(confusions),
            'subgroup_metric_rows': len(subgroups), 'subgroup_class_metric_rows': len(subgroup_stages),
            'group_mean_rows': len(summary), 'figures': len(FIGURE_RECORDS),
            'class_group_mean_rows': len(class_summary),
            'additional_original_threshold_controls': len(native_rows),
            'metric_rules': 'Ranking metrics copied only from source; blank is unavailable. Class-warning metrics are arithmetic derived from saved confusion counts. No new ROC curves reconstructed.',
            'scope': 'All registered arms/conditions/seeds in PX080-083 public metrics, including PX081 unrestricted references; original native-threshold supplement preserved byte for byte.',
            'source_audit_checks': checks}
writejson(HERE / 'COVERAGE.json', coverage)
writejson(HERE / 'ASSEMBLY_AUDIT.json', {'status': 'PASS', 'checks': checks, 'configurations_checked': len(arms), 'derived_subgroup_records_checked': len(subgroups), 'calculation_scope': 'Confusion totals, source precision/recall/F1, four-class macro-F1; preserved source AP/AUC without recomputation', 'new_fits': 0, 'limitations': 'This publication check does not revalidate source annotations or reproduce score-based AP/AUC from private predictions.'})
print(json.dumps(coverage, indent=2))
