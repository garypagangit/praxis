"""Fail-closed checks for the development evidence index (AI-assisted code)."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pointer(value, path):
    for part in path.strip('/').split('/'):
        key = part.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def audit(index, root=HERE):
    checks = []

    def record(name, okay, detail=''):
        checks.append({'check': name, 'passed': bool(okay), 'detail': detail})

    record('eight_declared_comparisons', len(index.get('comparisons', [])) == 8)
    record('no_new_inference', index.get('new_inference_calls') == 0)
    record('no_academic_approval', index.get('academic_approval_claimed') is False)
    record('no_validated_new_method', index.get('novel_method_validated') is False)
    record('px071_no_efficacy', index.get('px071_efficacy_available') is False)
    record('source_terminal_status', index.get('source_status') == 'PASS_SOURCE_KNOWN_ONLY')
    record('external_terminal_status', index.get('external_status') == 'FAIL_ROUTER_CONFIRMATION')
    for rel, expected in index.get('files', {}).items():
        path = (root / rel).resolve()
        record('sha:' + rel, path.is_file() and sha(path) == expected)
    record('source_inventory_nonempty', len(index.get('files', {})) >= 7)
    for row in index.get('comparisons', []):
        try:
            source = root / row['source']
            record(row['id'] + ':source_sha', sha(source) == row['source_sha256'])
            scope = pointer(json.loads(source.read_text()), row['pointer'])
            contrast = pointer(scope, row['comparison_pointer_suffix'])
            expected = {
                'n': contrast['paired_rows'],
                'treatment_correct': scope['conditions'][row['condition']]['correct'],
                'control_correct': scope['conditions'][row['control']]['correct'],
                'difference': contrast['accuracy_difference'],
                'ci95': contrast['paired_bootstrap_ci95'],
                'p_value': contrast.get(row['p_value_field']),
            }
            for key, value in expected.items():
                record(row['id'] + ':' + key, row.get(key) == value)
            record(row['id'] + ':count_arithmetic', math.isclose(
                (row['treatment_correct'] - row['control_correct']) / row['n'],
                row['difference'], rel_tol=0, abs_tol=1e-15))
            record(row['id'] + ':finite_ordered_ci', len(row['ci95']) == 2 and
                   all(math.isfinite(v) for v in row['ci95']) and row['ci95'][0] <= row['ci95'][1])
        except (KeyError, ValueError, TypeError, OSError, ZeroDivisionError) as exc:
            record(row.get('id', 'unknown') + ':source_error', False, type(exc).__name__)
    try:
        base = root.parent / 'papers/20260914/01_cti'
        router = json.loads((base / 'evidence/PX068_ANALYSIS.json').read_text())['router_metrics']
        record('router_metrics_equal', index.get('router_metrics') == router)
        receipt = json.loads((base / 'evidence/reproduced_full/REPRODUCTION_RECEIPT.json').read_text())
        record('full_reproduction_pass', receipt['status'] == 'PASS' and
               receipt['full2500_statistical_payload_equal'] is True and
               receipt['px068_statistical_payload_equal'] is True and
               receipt['bootstrap_intervals_recomputed'] == 156 and
               receipt['bootstrap_intervals_explicitly_taken_from_archive'] == 0)
        manifest = json.loads((base / 'MANIFEST.json').read_text())
        record('immutable_package_inventory_present', len(manifest['files']) == 54)
        for item in manifest['files']:
            file = base / item['file']
            record('immutable:' + item['file'], file.is_file() and
                   file.stat().st_size == item['bytes'] and sha(file) == item['sha256'])
        guide = (root / 'INTERNAL_RESEARCH_GUIDE.md').read_text(encoding='utf-8')
        for row in index['comparisons']:
            text = (f"{row['treatment_correct']:,} vs {row['control_correct']:,}; "
                    f"{100 * row['difference']:+.2f} pp "
                    f"[{100 * row['ci95'][0]:.2f}, {100 * row['ci95'][1]:.2f}]")
            record('guide_table:' + row['id'], text in guide)
        record('guide_has_internal_use_boundary', 'Not a document for academic submission.' in guide)
        record('extension_marked_unrun', 'status UNRUN' in guide)
    except (KeyError, ValueError, TypeError, OSError) as exc:
        record('source_receipt_error', False, type(exc).__name__)
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=Path, default=HERE / 'EVIDENCE_INDEX.json')
    parser.add_argument('--output', type=Path, default=HERE / 'CONSISTENCY_CHECK.json')
    args = parser.parse_args()
    rows = audit(json.loads(args.index.read_text()))
    result = {'status': 'PASS' if all(r['passed'] for r in rows) else 'FAIL',
              'checks_total': len(rows), 'checks_passed': sum(r['passed'] for r in rows),
              'checks_failed': sum(not r['passed'] for r in rows),
              'scope': 'Source hashes, exact archived values, arithmetic and historical reproduction receipt; not independent model replication, novelty review or academic approval.',
              'academic_submission_ready': False, 'inference_calls': 0,
              'index_sha256': sha(args.index), 'checker_sha256': sha(Path(__file__)),
              'checks': rows}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'checks_total', 'checks_passed', 'checks_failed')}))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
