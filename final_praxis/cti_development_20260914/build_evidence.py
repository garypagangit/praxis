"""Create a source-linked CTI evidence index; no models or network operations.

AI assistance disclosure: this code was developed with Codex. It indexes
existing immutable observations and does not establish academic approval.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'papers' / '20260914' / '01_cti'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    full_path = BASE / 'evidence/FULL_2500_ANALYSIS.json'
    px_path = BASE / 'evidence/PX068_ANALYSIS.json'
    full = json.loads(full_path.read_text())
    px = json.loads(px_path.read_text())
    records = []
    for model in ('Llama', 'Qwen'):
        for cell, stratum in (
            ('source_pointer', 'attack_technique_eligible'),
            ('query_only', 'attack_technique_eligible'),
            ('query_only', 'non_attack_domain_mismatch'),
        ):
            scope = full['models'][model][cell]['strata'][stratum]
            contrast = scope['comparisons'][0]
            assert contrast['control'] == 'vanilla'
            assert contrast['treatment'] == 'relationship_evidence'
            records.append({
                'id': f'{model}_{cell}_{stratum}',
                'source': '../papers/20260914/01_cti/evidence/FULL_2500_ANALYSIS.json',
                'source_sha256': sha(full_path),
                'pointer': f'/models/{model}/{cell}/strata/{stratum}',
                'model': model, 'cell': cell, 'stratum': stratum,
                'condition': 'relationship_evidence', 'control': 'vanilla',
                'n': contrast['paired_rows'],
                'treatment_correct': scope['conditions']['relationship_evidence']['correct'],
                'control_correct': scope['conditions']['vanilla']['correct'],
                'difference': contrast['accuracy_difference'],
                'ci95': contrast['paired_bootstrap_ci95'],
                'p_value_field': 'cross_model_holm_p' if 'cross_model_holm_p' in contrast else 'mcnemar_holm_p',
                'p_value': contrast.get('cross_model_holm_p', contrast.get('mcnemar_holm_p')),
                'comparison_pointer_suffix': '/comparisons/0',
            })
    for model in ('llama-3-1-8b-instruct', 'qwen2-5-7b-instruct'):
        scope = px['models'][model]['scopes']['ineligible']
        contrast = scope['comparisons']['routed_vs_ungated']
        records.append({
            'id': f'{model}_px068_ineligible',
            'source': '../papers/20260914/01_cti/evidence/PX068_ANALYSIS.json',
            'source_sha256': sha(px_path),
            'pointer': f'/models/{model}/scopes/ineligible',
            'model': model, 'cell': 'external_router', 'stratum': 'ineligible',
            'condition': 'routed_policy', 'control': 'relationship_evidence',
            'n': contrast['paired_rows'],
            'treatment_correct': scope['conditions']['routed_policy']['correct'],
            'control_correct': scope['conditions']['relationship_evidence']['correct'],
            'difference': contrast['accuracy_difference'],
            'ci95': contrast['paired_bootstrap_ci95'],
            'p_value_field': 'cross_model_holm_p',
            'p_value': contrast['cross_model_holm_p'],
            'comparison_pointer_suffix': '/comparisons/routed_vs_ungated',
        })
    files = {}
    for rel in ('MANIFEST.json', 'PAPER.md', 'evidence/STUDY_STATUS.json',
                'evidence/FULL_2500_ANALYSIS.json', 'evidence/PX068_ANALYSIS.json',
                'evidence/reproduced_full/REPRODUCTION_RECEIPT.json',
                'evidence/EXPOSED_ITEM_SENSITIVITY.json'):
        files['../papers/20260914/01_cti/' + rel] = sha(BASE / rel)
    output = {
        'version': 'cti-development-evidence-20260914-v1',
        'basis_commit': 'ccff6cf',
        'purpose': 'Evidence navigation and software verification; not submitted academic prose.',
        'new_inference_calls': 0,
        'academic_approval_claimed': False,
        'novel_method_validated': False,
        'px071_efficacy_available': False,
        'files': files,
        'comparisons': records,
        'router_metrics': px['router_metrics'],
        'source_status': full['portfolio_status'],
        'external_status': px['portfolio_status'],
    }
    (HERE / 'EVIDENCE_INDEX.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'comparisons': len(records), 'source_files': len(files), 'new_inference_calls': 0}))


if __name__ == '__main__':
    main()
