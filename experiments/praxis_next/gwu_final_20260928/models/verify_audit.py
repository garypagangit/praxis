"""Check publication model inventory and its source binding without fitting."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inventory = json.loads((HERE / 'MODEL_INVENTORY.json').read_text(encoding='utf-8'))
    references = json.loads((HERE / 'REFERENCES.json').read_text(encoding='utf-8'))
    manuscript = (HERE / 'MODEL_EXPLANATION.md').read_text(encoding='utf-8')
    checks = []

    def check(label, value):
        if not value:
            raise AssertionError(label)
        checks.append(label)

    for relative, expected in inventory['source_sha256'].items():
        check('Bound source: ' + relative, digest(REPO / relative) == expected)
    records = inventory['experiments']
    check('Main fit count is 141', sum(r['new_fits_total'] for r in records[:3]) == 141)
    check('Classifier count is 111', sum(r['new_classifier_fits'] for r in records) == 111)
    check('Regressor count is 32 including two Ridge fits', sum(r['new_regressor_fits'] for r in records) == 32)
    check('No new fitting in this implementation audit', inventory['totals']['new_fits_this_audit'] == 0)
    check('No main stage-weighted classifiers claimed', all(not r['classifier_stage_weighted'] for r in records[:3]))
    retained = inventory['saved_estimators_inspected']
    check('77 retained main/new-selector estimators inspected', len(retained) == 77)
    for item in retained:
        check('Saved model hash: ' + item['file'] + ':' + str(item['bundle_key']), digest(Path(item['file'])) == item['file_sha256'])
        if item['python_class'] == 'LGBMClassifier':
            iterations = 180 if item['experiment'] == 'PX080' else 150
            check('Class-specific tree count: ' + item['file'] + ':' + str(item['bundle_key']),
                  item['actual_iterations'] == iterations and item['actual_tree_count'] == 4 * iterations)
    native = inventory['reused_native_estimators_inspected']
    check('Six native models are separate reused controls', len(native) == 6)
    for item in native:
        check('Native model hash: ' + item['model_file'], digest(Path(item['model_file'])) == item['model_sha256'])
        check('Native features/runtime/no inference: ' + item['model_file'],
              item['features'] == 65546 and item['original_sklearn_version'] == '1.9.0' and not item['prediction_called'])
    tree = ast.parse((HERE / 'build_inventory.py').read_text(encoding='utf-8'))
    check('Inventory builder has no fitting/prediction calls', not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr in {'fit', 'partial_fit', 'fit_predict', 'predict', 'predict_proba'}
        for node in ast.walk(tree)))
    check('Eight verified primary references', len(references) == 8 and all(
        r['apa'] and r['url'].startswith('https://') and r['status'] == 'VERIFIED_PRIMARY_SOURCE'
        and r['locator'] for r in references))
    table_rows = [line for line in manuscript.splitlines() if line.startswith('|')]
    check('All Markdown tables use at most six columns', all(line.count('|') - 1 <= 6 for line in table_rows))
    check('Equation blocks are paired', manuscript.count('$$') > 0 and manuscript.count('$$') % 2 == 0)
    outside_math = re.sub(r'\$\$.*?\$\$', '', manuscript, flags=re.S)
    check('No stray raw LaTeX outside equation blocks', re.search(r'\\[a-zA-Z]+', outside_math) is None)
    for destination in re.findall(r'\]\(([^)]+)\)', manuscript):
        if not destination.startswith(('https://', 'http://')):
            check('Local document link exists: ' + destination, (HERE / destination).resolve().is_file())
    artifacts = ['build_inventory.py', 'MODEL_INVENTORY.json', 'MODEL_EXPLANATION.md', 'REFERENCES.json', 'verify_audit.py']
    receipt = {
        'status': 'PASS', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Read-only implementation and publication checks; no new model fits or predictions.',
        'check_count': len(checks), 'checks': checks,
        'artifact_sha256': {name: digest(HERE / name) for name in artifacts},
        'equation_blocks': manuscript.count('$$') // 2,
        'max_table_columns': max(line.count('|') - 1 for line in table_rows),
        'source_binding_count': len(inventory['source_sha256']),
        'private_metadata_limit': 'Original model files were inspected only for saved metadata. Main PX082 estimators and PX081 forward-fold estimators were not retained; source and execution receipts establish those fit counts.'
    }
    (HERE / 'MODEL_AUDIT.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('status', 'check_count', 'source_binding_count', 'equation_blocks', 'max_table_columns')}))


if __name__ == '__main__':
    main()
