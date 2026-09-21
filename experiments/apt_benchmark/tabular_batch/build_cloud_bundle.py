"""Build/inspect a private E1 bundle offline; never call AWS or start a host.

Only explicit runtime files, the frozen prepared arrays/manifest, and verified
public checkpoints enter the archive. Optional old account settings are copied
privately with a distinct S3 prefix; no credentials enter the archive or output.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

try:
    from .model_backend import CHECKPOINTS,ensure_checkpoint
except ImportError:
    from model_backend import CHECKPOINTS,ensure_checkpoint

RUNTIME_FILES=('run_e1.py','model_backend.py','requirementsfoundation.txt',
               'requirements_baselines.txt','protocol.json','run_cloud.sh','cloud_runtime.py')
CONTROLLER='experiments/apt_final/native_graph/cloud_control.py'
MODULE='experiments/apt_benchmark/tabular_batch'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def build(repo,prepared,cache,output,*,settings_source=None,allow_uncommitted=False):
    repo=Path(repo).resolve(strict=True);prepared=Path(prepared).resolve(strict=True)
    cache=Path(cache).resolve(strict=True);output=Path(output).resolve()
    try:output.relative_to(repo)
    except ValueError:pass
    else:raise ValueError('Bundle/account output must remain outside the repository')
    if (output/'ACTIVE_RUN.json').exists():raise ValueError('Cannot rebuild an active/executed attempt')
    output.mkdir(parents=True,exist_ok=True)
    code=repo/MODULE
    protocol=json.loads((code/'protocol.json').read_text())
    if sha(prepared/'DATA.npz')!=protocol['data_npz_sha256'] or sha(prepared/'MANIFEST.json')!=protocol['manifest_sha256']:
        raise ValueError('Prepared data/manifest do not match protocol')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    files={};uncommitted=[]
    for name in RUNTIME_FILES:
        path=code/name;relative=path.relative_to(repo).as_posix()
        committed=subprocess.run(['git','show','HEAD:'+relative],cwd=repo,capture_output=True)
        if committed.returncode or committed.stdout!=path.read_bytes():uncommitted.append(relative)
        files['repo/'+relative]=path
    if uncommitted and not allow_uncommitted:raise ValueError('Runtime files must match committed HEAD before final bundle')
    files['data/DATA.npz']=prepared/'DATA.npz';files['data/MANIFEST.json']=prepared/'MANIFEST.json'
    checkpoints={}
    for name in ['tabicl_v2','tabpfn_2_5_synthetic']:
        path=ensure_checkpoint(name,cache,allow_download=False)
        spec=CHECKPOINTS[name]
        files['model_cache/'+path.relative_to(cache).as_posix()]=path
        checkpoints[name]={'revision':spec.revision,'sha256':spec.sha256,'bytes':spec.size_bytes,'license':spec.license}
    manifest={'schema_version':1,'runtime_git_head':commit,'all_runtime_bytes_committed':not uncommitted,
              'uncommitted_runtime_files':uncommitted,
              'models':['tabicl_v2','tabpfn_2_5_synthetic'],'data_sha256':protocol['data_npz_sha256'],
              'protocol_sha256':sha(code/'protocol.json'),
              'files':{name:{'sha256':sha(path),'bytes':path.stat().st_size} for name,path in sorted(files.items())}}
    manifest_bytes=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    bundle=output/'bundle.tar.gz'
    # Stable metadata makes unchanged inputs produce identical archive bytes.
    with bundle.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as archive:
        for name,path in sorted(files.items()):
            info=tarfile.TarInfo(name);info.size=path.stat().st_size;info.mode=0o644;info.mtime=0
            with path.open('rb') as source:archive.addfile(info,source)
        info=tarfile.TarInfo('BUNDLE_CONTENTS.json');info.size=len(manifest_bytes);info.mode=0o644;info.mtime=0
        archive.addfile(info,io.BytesIO(manifest_bytes))
    with tarfile.open(bundle,'r:gz') as archive:
        members=archive.getmembers()
        if len(members)!=len(files)+1 or not all(m.isfile() for m in members):raise ValueError('Archive verification failed')
        for name,receipt in manifest['files'].items():
            content=archive.extractfile(name)
            h=hashlib.sha256()
            for block in iter(lambda:content.read(1024*1024),b''):h.update(block)
            if h.hexdigest()!=receipt['sha256']:raise ValueError('Archived member hash mismatch')
    bundle_sha=sha(bundle)
    freeze={'schema_version':1,'experiment':'E1 foundations only','bundle_sha256':bundle_sha,
            'bundle_bytes':bundle.stat().st_size,'bundle_file_count':len(files)+1,
            'all_runtime_bytes_committed':not uncommitted,'runtime_git_head':commit,
            'data_sha256':protocol['data_npz_sha256'],'manifest_sha256':protocol['manifest_sha256'],
            'protocol_sha256':sha(code/'protocol.json'),
            'builder_sha256':sha(Path(__file__)),
            'runtime_files':{str(Path(name).relative_to('repo')).replace('\\','/'):receipt for name,receipt in manifest['files'].items() if name.startswith('repo/')},
            'checkpoints':checkpoints,'controller':{'path':CONTROLLER,'sha256':sha(repo/CONTROLLER),
                'total_cap_seconds':3600,'watchdog_seconds':3360,'worker_deadline_seconds':3120,'publication_reserve_seconds':150},
            'prepared_offline':True,'aws_calls_performed_by_builder':0,'scientific_fits_performed_by_builder':0,
            'launch_eligible':not uncommitted}
    write_json(output/'BUNDLE_CONTENTS.json',manifest);write_json(output/'RUNTIME_FREEZE.json',freeze)
    (output/'bundle.sha256').write_text(bundle_sha+'\n')
    if settings_source:
        old=json.loads(Path(settings_source).read_text())
        allowed=['profile','region','account','instance','bucket','stop_role_arn','usd_per_hour','rate_source']
        new={key:old[key] for key in allowed if key in old}
        new['prefix']='apt-tabular-e1-20260921/attempt1/'
        if new['prefix']==old['prefix']:raise ValueError('Distinct S3 prefix required')
        target=output/'settings.json'
        if target.exists() and json.loads(target.read_text())!=new:raise ValueError('Existing account settings differ')
        write_json(target,new)
    return freeze


def render_bootstrap(repo,output):
    """Render only after root started controller; this function still makes no calls."""
    from datetime import datetime,timezone
    output=Path(output).resolve();repo=Path(repo).resolve(strict=True)
    settings=json.loads((output/'settings.json').read_text());active=json.loads((output/'ACTIVE_RUN.json').read_text())
    freeze=json.loads((output/'RUNTIME_FREEZE.json').read_text())
    if not freeze['launch_eligible']:raise ValueError('Provisional bundle cannot launch')
    if sha(output/'bundle.tar.gz')!=freeze['bundle_sha256']:raise ValueError('Bundle changed')
    for key in ['account','region','instance','bucket','prefix','stop_role_arn']:
        if active[key]!=settings[key]:raise ValueError('Active/settings mismatch')
    if active.get('gate_failed') or active['stage']!='started':raise ValueError('Controller is not ready for worker submission')
    controller_deadline=int(datetime.fromisoformat(active['worker_deadline_utc']).timestamp())
    now_epoch=int(datetime.now(timezone.utc).timestamp())
    remaining=controller_deadline-now_epoch
    timeout=min(2800,remaining-140)
    if timeout<300:raise ValueError('Insufficient remaining worker time')
    # SSM command timeout is tighter than the controller deadline because it
    # reserves delivery overhead. Finish publication before that tighter bound.
    deadline=min(controller_deadline,now_epoch+timeout-20)
    bundle_uri='s3://'+settings['bucket']+'/'+settings['prefix']+'bundle.tar.gz'
    output_uri='s3://'+settings['bucket']+'/'+settings['prefix']+'outputs'
    args=[bundle_uri,freeze['bundle_sha256'],output_uri,'apt-tabular-'+active['run_id'][:16],str(deadline)]
    source=(repo/MODULE/'run_cloud.sh').read_bytes()
    expected=freeze['runtime_files'][MODULE+'/run_cloud.sh']['sha256']
    if hashlib.sha256(source).hexdigest()!=expected:raise ValueError('Worker changed after freeze')
    # Deliver frozen worker bytes inline; no shell-generated string interpolation.
    script='#!/usr/bin/env bash\nset -euo pipefail\nbash -s -- '+' '.join(shlex.quote(v) for v in args)+" <<'APT_FROZEN_CLOUD_WORKER'\n"+source.decode().replace('\r\n','\n')+'\nAPT_FROZEN_CLOUD_WORKER\n'
    (output/'bootstrap.sh').write_text(script,encoding='utf-8',newline='\n')
    write_json(output/'SEND_PLAN.json',{'timeout_seconds':timeout,'effective_worker_deadline_epoch':deadline,'controller_worker_deadline_epoch':controller_deadline,'script_sha256':sha(output/'bootstrap.sh'),'bundle_key':settings['prefix']+'bundle.tar.gz','result_key':settings['prefix']+'outputs/result.tar.gz','result_hash_key':settings['prefix']+'outputs/result.sha256','no_aws_calls_performed':True})
    return {'bootstrap_rendered':True,'timeout_seconds':timeout,'no_aws_calls_performed':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepared',type=Path);parser.add_argument('--model-cache',type=Path)
    parser.add_argument('--settings-source',type=Path)
    parser.add_argument('--allow-uncommitted',action='store_true')
    parser.add_argument('--render-bootstrap',action='store_true')
    args=parser.parse_args()
    if args.render_bootstrap:result=render_bootstrap(args.repo,args.output)
    else:
        if args.prepared is None or args.model_cache is None:parser.error('--prepared and --model-cache required when building')
        result=build(args.repo,args.prepared,args.model_cache,args.output,settings_source=args.settings_source,allow_uncommitted=args.allow_uncommitted)
        result={key:result[key] for key in ['bundle_sha256','bundle_bytes','bundle_file_count','all_runtime_bytes_committed','prepared_offline','launch_eligible']}
    print(json.dumps(result,indent=2))
