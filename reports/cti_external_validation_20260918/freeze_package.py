"""Freeze completed local preparation; build exact runtime tar only after Git commit."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
REL = 'reports/cti_external_validation_20260918/'
RUNTIME = ['cloud_runner.py', 'trusted_cloud_controller.py', 'cti_cloud_controller.py',
           'run_cloud.sh', 'inference_worker.py', 'frozen_inference.py',
           'generator_inputs.jsonl', 'qualification_inputs.jsonl']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    if (ROOT/'FREEZE.json').exists() or (ROOT/'SCIENTIFIC_FREEZE.json').exists():
        raise FileExistsError('A frozen attempt is immutable; use a separate explicit amendment')
    for name in ['CHECKER_VALIDATION.json', 'policy_predictions.jsonl', 'PROMPT_VERIFICATION.json',
                 'DATA_AUDIT.json', 'ANALYSIS_REVIEW.json', *RUNTIME]:
        if not (ROOT/name).is_file() or not (ROOT/name).stat().st_size:
            raise ValueError('Preparation is incomplete: '+name)
    checker = json.loads((ROOT/'CHECKER_VALIDATION.json').read_text())
    review = json.loads((ROOT/'ANALYSIS_REVIEW.json').read_text())
    if checker['status'] != 'PASS' or review['status'] != 'PASS_PENDING_REAL_OUTPUTS':
        raise ValueError('Preparation review has not passed')
    if checker['policy_predictions_sha256'] != sha(ROOT/'policy_predictions.jsonl'):
        raise ValueError('Validated checker decisions changed')
    for name in ('PROTOCOL.md', 'analyze_external.py', 'inference_worker.py', 'frozen_inference.py'):
        if review['reviewed_sha256'][name] != sha(ROOT/name):
            raise ValueError('Reviewed scientific implementation changed: '+name)
    if (ROOT/'RESULTS.json').exists() or (ROOT/'predictions.jsonl').exists():
        raise ValueError('Fresh scientific outcomes must not exist before this freeze')
    files = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(ROOT.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py', '.sh', '.json', '.jsonl', '.md', '.html', '.joblib'}}
    scientific = {'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'BEFORE_ANY_FRESH_GENERATOR_ANSWERS', 'files': files,
        'preparation': 'All policy decisions and analysis rules fixed; no fresh labels used for fitting/calibration.',
        'human_review_status': 'PENDING; zero completed reviews'}
    (ROOT/'SCIENTIFIC_FREEZE.json').write_text(json.dumps(scientific, indent=2)+'\n', encoding='utf-8')
    runtime = {'frozen_utc': scientific['frozen_utc'], 'files': {REL+n: sha(ROOT/n) for n in RUNTIME},
        'worker_args': ['--inputs', REL+'generator_inputs.jsonl', '--qualification', REL+'qualification_inputs.jsonl'],
        'scientific_freeze_sha256': sha(ROOT/'SCIENTIFIC_FREEZE.json'),
        'runtime': {'host_cap_seconds': 3600, 'watchdog_seconds': 3360, 'worker_deadline_seconds': 3120,
                    'maximum_command_seconds': 3000, 'total_reserve_usd': 10, 'maximum_attempts': 1,
                    'test_questions': 1247, 'fresh_outputs': 4988, 'qualification_outputs': 32}}
    (ROOT/'FREEZE.json').write_text(json.dumps(runtime, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'scientific_files': len(files), 'runtime_files': len(RUNTIME),
                      'freeze_sha256': sha(ROOT/'FREEZE.json')}))


def bundle(destination):
    frozen = json.loads((ROOT/'FREEZE.json').read_text())
    names = sorted([*frozen['files'], REL+'PROTOCOL.md', REL+'FREEZE.json'])
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    for name in names:
        actual = (REPO/name).read_bytes()
        committed = subprocess.check_output(['git', 'show', 'HEAD:'+name], cwd=REPO)
        if actual != committed:
            raise ValueError('Bundle input differs from committed Git HEAD: '+name)
    if destination.exists():
        raise FileExistsError(destination)
    with tarfile.open(destination, 'w:gz') as archive:
        for name in names:
            info = archive.gettarinfo(str(REPO/name), arcname=name)
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mode = 0o700 if name.endswith('.sh') else 0o600
            with (REPO/name).open('rb') as stream:
                archive.addfile(info, stream)
    receipt = {'commit': commit, 'path': str(destination.resolve()), 'sha256': sha(destination),
               'bytes': destination.stat().st_size, 'members': names}
    destination.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['freeze', 'bundle'])
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.action == 'freeze':
        freeze()
    else:
        if args.output is None:
            p.error('bundle requires --output')
        bundle(args.output)
