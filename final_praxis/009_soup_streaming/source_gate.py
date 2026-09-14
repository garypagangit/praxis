"""Reinspect cached public base evidence without running a model."""
import argparse
import hashlib
import json
from pathlib import Path

from common import bind_source, provenance, save_json, sha


def audit(source, cache):
    import pyarrow.parquet as pq
    bind_source(source)
    root = Path(source)
    cache = Path(cache)
    checks, data = [], []
    metadata = json.loads((cache / 'emotion_metadata.json').read_text())
    card = (cache / 'emotion_README.md').read_text()
    text_labels = {}
    texts_by_split = {}
    downloads = json.loads((cache / 'download_receipt.json').read_text())
    for row in downloads:
        split = row['split']
        path = cache / (split + '-00000-of-00001.parquet')
        table = pq.read_table(path)
        values = table.to_pydict()
        expected_rows = 16000 if split == 'train' else 2000
        keys = [hashlib.sha256(v.encode()).hexdigest() for v in values['text']]
        texts_by_split[split] = set(keys)
        for key, label in zip(keys, values['label']):
            text_labels.setdefault(key, set()).add(label)
        check = {'check': 'pinned_' + split, 'passed': sha(path) == row['sha256']
                 and table.num_rows == expected_rows and table.column_names == ['text', 'label']
                 and all(type(v) is int and 0 <= v <= 5 for v in values['label'])}
        checks.append(check)
        data.append({**row, 'within_split_duplicate_text_count': len(keys) - len(set(keys)),
                     'label_counts': {str(i): values['label'].count(i) for i in range(6)}})
    prep_present = any(p.name == 'prep_convergence.py' for p in root.rglob('*.py'))
    license_permits_research = 'educational and research purposes only' in card
    checks.append({'check': 'pinned_dataset_revision', 'passed': metadata['sha'] == 'cab853a1dbdf4c42c2b3ef2173804746df8825fe'})
    checks.append({'check': 'full_card_research_permission', 'passed': license_permits_research})
    standalone = (root / 'benchmarks/harness/bitexact.py').read_text()
    unit_reference = (root / 'tests/test_issue385_stream_dtype.py').read_text()
    return {'scope': 'Public source, artifact and dataset qualification; no inference',
            'provenance': provenance(), 'checks': checks,
            'data_access_schema_terms_pass': all(c['passed'] for c in checks),
            'dataset_revision': metadata['sha'], 'data': data,
            'exact_text_overlap': {'train_validation': len(texts_by_split['train'] & texts_by_split['validation']),
                                   'train_test': len(texts_by_split['train'] & texts_by_split['test']),
                                   'validation_test': len(texts_by_split['validation'] & texts_by_split['test'])},
            'same_text_multiple_labels': sum(len(v) > 1 for v in text_labels.values()),
            'paper_v3': {'doi': '10.5281/zenodo.21918325', 'date': '2026-08-13', 'pages': 37,
                         'pdf_sha256': sha(cache / 'exact_layer_streaming_v3.pdf')},
            'exact_published_quality_reproduction_ready': False,
            'exact_split_preparation_script_present': prep_present,
            'quality_reproduction_limit': 'Original sample-preparation script and exact full split IDs not recovered; gated original Llama checkpoint not downloaded. A fresh split/model would be an adapted reproduction.',
            'nf4_reference_gap': {'standalone_harness_has_matched_dequant_reference': 'install_dequant_forward' in standalone,
                                 'updated_unit_test_has_matched_dequant_reference': 'install_dequant_forward(base)' in unit_reference,
                                 'interpretation': 'Do not classify native fused-vs-dequant arithmetic differences as streaming defects.'},
            'terms': {'metadata': metadata['cardData']['license'], 'research_use_explicit': license_permits_research,
                      'unrestricted_redistribution_verified': False, 'raw_data_kept_outside_git': True},
            'novel_algorithm_gate': 'NOT ESTABLISHED: async read-ahead and bounded buffers are established; must beat matched offload/prefetch baselines in a distinct, useful regime.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit(args.source, args.cache)
    save_json(args.output, result)
    print(json.dumps({'data_access_schema_terms_pass': result['data_access_schema_terms_pass'],
                      'exact_published_quality_reproduction_ready': False,
                      'exact_text_overlap': result['exact_text_overlap']}))
