"""Bounded remote entrypoint; dataset runs remain separate development replications."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--prior-dir', type=Path, required=True)
    args = parser.parse_args()
    config_path = Path(__file__).with_name('config.json')
    config = json.loads(config_path.read_text(encoding='utf-8'))
    status = {'scope': 'DEVELOPMENT_ONLY', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'datasets': {}, 'status': 'RUNNING'}
    def save():
        temporary = args.output / '.WORKER_STATUS.tmp'
        temporary.write_text(json.dumps(status, indent=2)+'\n', encoding='utf-8')
        temporary.replace(args.output / 'WORKER_STATUS.json')
    save()
    for dataset in config['datasets']:
        print(json.dumps({'event':'dataset_start','dataset':dataset}), flush=True)
        command = [sys.executable, '-u', '-m', 'experiments.apt_final.embedding_baseline.runner',
                   '--config', str(config_path), '--data-dir', str(args.data_dir),
                   '--prior-dir', str(args.prior_dir), '--dataset', dataset, '--output', str(args.output/dataset),
                   '--registration', str(args.registration), '--device', 'cuda']
        result = subprocess.run(command)
        status['datasets'][dataset] = {'returncode': result.returncode}
        save()
        if result.returncode:
            status['status'] = 'INCOMPLETE'
            save()
            return result.returncode
    status.update(status='COMPLETE', ended_utc=datetime.now(timezone.utc).isoformat())
    save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
