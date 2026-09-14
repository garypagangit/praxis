"""Index committed qualification evidence without inference or network calls."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cti-repo', type=Path, required=True)
    p.add_argument('--soup-repo', type=Path, required=True)
    p.add_argument('--forecast-repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    definitions = [
        ('CTI', args.cti_repo, 'final_praxis/cti_development_20260914',
         ['MANIFEST.json', 'CONSISTENCY_CHECK.json', 'CONTROL_TEST_RECEIPT.json', 'INTERNAL_RESEARCH_GUIDE.pdf']),
        ('009', args.soup_repo, 'final_praxis/009_soup_streaming',
         ['QUALIFICATION_PROTOCOL.md', 'RELEASE_MANIFEST.json', 'RELEASE_VERIFICATION.json', 'results/GPU_SUMMARY.json', 'results/gpu/ARTIFACT_REVIEW.json']),
        ('010', args.forecast_repo, 'final_praxis/010_attack_aware_forecasting',
         ['QUALIFICATION_PROTOCOL.md', 'PROTOCOL_FREEZE.json', 'RUNTIME_FREEZE.json', 'STATUS.json',
          'results/cpu/CPU_QUALIFICATION_RECEIPT.json', 'completed_qualification/setup/CLOUD_SETUP_REVIEW.json',
          'completed_qualification/new3/QUALIFICATION_RECEIPT.json']),
    ]
    records = []
    for label, repo, prefix, names in definitions:
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=repo, text=True).strip()
        base = repo / prefix
        if label == '010':
            for mode in ['original25', 'calibration']:
                for filename in ['QUALIFICATION_RECEIPT.json', 'FAILED_QUALIFICATION_RECEIPT.json']:
                    relative = f'completed_qualification/{mode}/{filename}'
                    if (base / relative).is_file():
                        names.append(relative)
            for optional in ['RELEASE_MANIFEST.json', 'RELEASE_VERIFICATION.json', 'completed_qualification/FINAL_AUDIT.json']:
                if (base / optional).is_file():
                    names.append(optional)
        files = []
        for name in names:
            relative = prefix + '/' + name
            data = (repo / relative).read_bytes()
            committed = subprocess.check_output(['git', 'show', head + ':' + relative], cwd=repo)
            if data != committed:
                raise ValueError('Uncommitted evidence: ' + relative)
            files.append({'path': relative, 'bytes': len(data), 'sha256': sha(data),
                          'url': f'https://github.com/garypagangit/praxis/blob/{head}/{relative}'})
        # Verify every sealed item is actually present in the committed tree.
        manifest_name = 'MANIFEST.json' if label == 'CTI' else 'RELEASE_MANIFEST.json'
        manifest_path = base / manifest_name
        inventory_count = 0
        if manifest_path.exists():
            inventory = json.loads(manifest_path.read_text())['files']
            if isinstance(inventory, list):
                inventory = {r.get('file', r.get('path')): r for r in inventory}
            for name, metadata in inventory.items():
                data = subprocess.check_output(['git', 'show', head + ':' + prefix + '/' + name], cwd=repo)
                if sha(data) != metadata['sha256']:
                    raise ValueError('Manifest/index disagreement: ' + name)
                inventory_count += 1
        records.append({'package': label, 'branch': branch, 'commit': head, 'evidence': files,
                        'sealed_files_verified_in_commit': inventory_count})
    report = {'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'status': 'PASS_COMMITTED_EVIDENCE_IDENTITY', 'packages': records,
              'scope': 'Committed byte identity and sealed inventory only; no scientific efficacy, novelty or academic approval certification.',
              'network_calls': 0, 'inference_calls': 0}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'packages': len(records),
                      'sealed_files_verified': sum(r['sealed_files_verified_in_commit'] for r in records)}))


if __name__ == '__main__':
    main()
