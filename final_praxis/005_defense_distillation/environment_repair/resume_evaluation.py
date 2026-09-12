"""Environment-only 005 repair. Execute only on the original supervised host."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('/mnt/praxis-20260912-005/fp005-20260912-37fdd3f')
STOP = datetime.fromisoformat('2026-09-12T15:55:49.634894+00:00')
ORIGINAL_COMMIT = '37fdd3f154a78017f9eb313385e25379c36affde'
ARMS = ('base', 'er', 'base_kd', 'er_kd', 'er_replay')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packages():
    return {d.metadata['Name'].lower().replace('_', '-'): d.version
            for d in importlib.metadata.distributions()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def stage_commands(python, runner, output):
    return [[python, str(runner), 'judge', '--judge', 'md', '--out', str(output)],
            [python, str(runner), 'report', '--out', str(output)]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    study = ROOT/'code/final_praxis/005_defense_distillation'
    output = ROOT/'outputs'
    commands = stage_commands(sys.executable, study/'run.py', output)
    if not args.execute:
        print(json.dumps({'state': 'PLAN_ONLY', 'commands': commands, 'dependency': 'protobuf==5.29.5',
                          'deadline_utc': STOP.isoformat(), 'model_calls': 0}))
        return
    if Path(sys.prefix).resolve() != Path('/mnt/praxis-20260912-005/venv'):
        raise RuntimeError('Must use the original isolated 005 virtual environment')
    for variable, directory in {'HF_HOME': 'hf_cache', 'TMPDIR': 'tmp',
                                'XDG_CACHE_HOME': 'xdg_cache', 'PIP_CACHE_DIR': 'pip_cache'}.items():
        os.environ[variable] = str(ROOT.parent/directory)
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    if (STOP-datetime.now(timezone.utc)).total_seconds() < 900:
        raise RuntimeError('Insufficient time within original deadline')
    bundle = json.loads((ROOT/'code/bundle_manifest.json').read_text())
    if bundle['git_commit'] != ORIGINAL_COMMIT:
        raise RuntimeError('Original source commit mismatch')
    for name, expected in bundle['files'].items():
        if digest(ROOT/'code'/name) != expected:
            raise RuntimeError('Original source modified: '+name)
    prereg = study/'PREREGISTRATION.md'
    if os.environ.get('PRAXIS_PREREG_SHA256') != digest(prereg):
        raise RuntimeError('Supervisor must provide the original frozen preregistration hash')
    receipt = ROOT/('repair_protobuf_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    receipt.mkdir(exist_ok=False)
    write(receipt/'repair_start.json', {'original_commit': ORIGINAL_COMMIT, 'commands': commands,
          'repair_script_sha256': digest(Path(__file__)), 'prereg_sha256': digest(prereg),
          'deadline_utc': STOP.isoformat(), 'dependency_lock_sha256': digest(HERE/'requirements-repair.txt')})
    protected = [output/('generations_'+a+'.jsonl') for a in ARMS]
    protected += [output/'judgments_qwen.jsonl']
    protected += sorted((output/'checkpoints').glob('**/*'))
    protected += sorted(output.glob('teacher*'))
    protected = [p for p in protected if p.is_file()]
    for arm in ARMS:
        rows = [json.loads(s) for s in (output/('generations_'+arm+'.jsonl')).read_text().splitlines() if s.strip()]
        if len(rows) != 160 or len({r['id'] for r in rows}) != 160:
            raise RuntimeError('Cannot verify complete original generation arm: '+arm)
    qwen = [json.loads(s) for s in (output/'judgments_qwen.jsonl').read_text().splitlines() if s.strip()]
    if len(qwen) != 640 or len({(r['arm'], r['id']) for r in qwen}) != 640:
        raise RuntimeError('Cannot verify completed Qwen judgments')
    before_hashes = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    write(receipt/'protected_artifacts_before.json', before_hashes)
    previous_environment = output/'environment_judge_md.json'
    if previous_environment.exists():
        shutil.copy2(previous_environment, receipt/'environment_judge_md_before.json')
    before = packages()
    write(receipt/'packages_before.json', before)
    if before.get('protobuf') not in (None, '5.29.5'):
        raise RuntimeError('Unexpected existing protobuf version; do not replace silently')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-deps',
                    '--only-binary=:all:', '--require-hashes', '-r', str(HERE/'requirements-repair.txt')], check=True)
    after = packages()
    write(receipt/'packages_after.json', after)
    changed = {name for name in set(before)|set(after) if before.get(name) != after.get(name)}
    if not changed <= {'protobuf'} or after.get('protobuf') != '5.29.5':
        raise RuntimeError('Unexpected dependency change')
    qualification = '''import json,sys,hashlib
from transformers import AutoTokenizer
from pathlib import Path
sources=json.loads(Path(sys.argv[1]).read_text())
entry=sources['models']['guard_independent']
assert entry['id']=='OpenSafetyLab/MD-Judge-v0.1'
assert entry['revision']=='993302ce502a634b64a1cb8be95b6729d4d27b13'
t=AutoTokenizer.from_pretrained(entry['id'],revision=entry['revision'],trust_remote_code=False,local_files_only=True)
ids=t('Tokenizer dependency qualification.',add_special_tokens=True)['input_ids']
assert ids and all(isinstance(i,int) for i in ids)
print(json.dumps({'tokenizer_class':type(t).__name__,'is_fast':t.is_fast,'id':entry['id'],'revision':entry['revision'],'token_ids_sha256':hashlib.sha256(json.dumps(ids).encode()).hexdigest(),'model_inference':False}))
'''
    # Fresh process ensures Transformers detects the newly installed backend.
    checked = subprocess.check_output([sys.executable, '-c', qualification, str(study/'sources.lock.json')], text=True)
    (receipt/'tokenizer_qualification.json').write_text(checked, encoding='utf-8')
    try:
        for command in commands:
            remaining = min(3600, int((STOP-datetime.now(timezone.utc)).total_seconds())-300)
            if remaining <= 0:
                raise RuntimeError('Original deadline reached')
            subprocess.run(command, check=True, timeout=remaining)
    finally:
        after_hashes = {name: digest(ROOT/name) for name in before_hashes}
        write(receipt/'protected_artifacts_after.json', after_hashes)
        if before_hashes != after_hashes:
            raise RuntimeError('Original generations/training/Qwen artifacts changed')
    write(receipt/'repair_complete.json', {'state': 'MD_AND_REPORT_COMPLETED',
          'original_artifacts_unchanged': True, 'manual_adjudication_pending': True})


if __name__ == '__main__':
    main()
