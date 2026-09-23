"""Render a checked SSM acquisition command after start; perform no AWS calls."""
from __future__ import annotations
import argparse,datetime,hashlib,json,shlex,time
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(repo,private):
    repo=repo.resolve(strict=True);private=private.resolve(strict=True)
    settings=json.loads((private/'settings.json').read_text())
    active=json.loads((private/'ACTIVE_RUN.json').read_text())
    freeze=json.loads((private/'RUNTIME_FREEZE.json').read_text())
    if active.get('gate_failed') or active['stage']!='started':raise ValueError('Controller not ready')
    for key in ['account','region','instance','bucket','prefix','stop_role_arn']:
        if settings[key]!=active[key]:raise ValueError('Attempt identity mismatch')
    if sha(private/'bundle.tar.gz')!=freeze['bundle_sha256']:raise ValueError('Bundle changed')
    for name,record in freeze['runtime_files'].items():
        p=repo/Path(name).relative_to('repo')
        if sha(p)!=record['sha256']:raise ValueError('Frozen runtime changed')
    if sha(repo/freeze['controller_path'])!=freeze['controller_sha256']:raise ValueError('Base controller changed')
    deadline=int(datetime.datetime.fromisoformat(active['worker_deadline_utc']).timestamp())
    now=int(time.time()); timeout=min(900,deadline-now-160)
    if timeout<450:raise ValueError('Insufficient bounded acquisition time')
    script_deadline=min(deadline,now+timeout-20)
    args=[f"s3://{settings['bucket']}/{settings['prefix']}bundle.tar.gz",freeze['bundle_sha256'],
          f"s3://{settings['bucket']}/{settings['prefix']}outputs",'praxis-provics-'+active['run_id'][:16],str(script_deadline)]
    body=(repo/'experiments/praxis_next/compute/run_provics_cloud.sh').read_text()
    marker='PRAXIS_PROVICS_FROZEN_WORKER'
    if marker in body:raise ValueError('Heredoc delimiter collision')
    script="bash -s -- "+' '.join(shlex.quote(x) for x in args)+" <<'"+marker+"'\n"+body+'\n'+marker+'\n'
    (private/'bootstrap.sh').write_text(script,encoding='utf8',newline='\n')
    plan={'timeout_seconds':timeout,'script_deadline_epoch':script_deadline,
          'script_sha256':sha(private/'bootstrap.sh'),'aws_calls':0}
    (private/'SEND_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--private',required=True,type=Path)
    a=p.parse_args();print(json.dumps(render(a.repo,a.private),indent=2))
