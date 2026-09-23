"""Build a tiny checksummed acquisition payload offline; never start AWS compute."""
from __future__ import annotations
import argparse,gzip,hashlib,io,json
from pathlib import Path
import tarfile

FILES = (
    'experiments/praxis_next/data_qualification/acquire_provics.py',
    'experiments/praxis_next/compute/run_provics_cloud.sh',
    'experiments/praxis_next/compute/PROVICS_CLOUD_PROTOCOL.md',
    'experiments/praxis_next/compute/build_provics_bundle.py',
    'experiments/praxis_next/compute/provics_cloud_control.py',
    'experiments/praxis_next/compute/render_provics_bootstrap.py',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(repo,output,settings_source=None,attempt_id=1):
    repo=repo.resolve(strict=True);output=output.resolve()
    if not isinstance(attempt_id,int) or attempt_id < 1:raise ValueError('Positive attempt identity required')
    if output.is_relative_to(repo):raise ValueError('Private cloud artifacts must remain outside Git')
    if (output/'ACTIVE_RUN.json').exists():raise ValueError('Attempt already started')
    output.mkdir(parents=True,exist_ok=True)
    sources={'repo/'+p:repo/p for p in FILES}
    manifest={'scope':'ProvICS public subset acquisition and qualification; zero fits',
              'files':{name:{'bytes':p.stat().st_size,'sha256':digest(p)} for name,p in sources.items()}}
    raw_manifest=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    bundle=output/'bundle.tar.gz'
    with bundle.open('wb') as stream,gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for name,path in sorted(sources.items()):
            data=path.read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0;info.mode=0o644
            tar.addfile(info,io.BytesIO(data))
        info=tarfile.TarInfo('BUNDLE_CONTENTS.json');info.size=len(raw_manifest);info.mtime=0;info.mode=0o644
        tar.addfile(info,io.BytesIO(raw_manifest))
    with tarfile.open(bundle,'r:gz') as tar:
        assert set(tar.getnames())==set(sources)|{'BUNDLE_CONTENTS.json'}
        for name,record in manifest['files'].items():
            assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==record['sha256']
    freeze={'experiment':'New-data qualification for PX-080/PX-081',
            'bundle_sha256':digest(bundle),'bundle_bytes':bundle.stat().st_size,
            'runtime_files':manifest['files'],'model_fits':0,'cloud_calls_by_builder':0,
            'launch_status':'Requires root-committed protocol and freeze before controller start',
            'controller_path':'experiments/apt_final/native_graph/cloud_control.py',
            'controller_sha256':digest(repo/'experiments/apt_final/native_graph/cloud_control.py')}
    freeze['compute_bounds']={'total_seconds':2700,'watchdog_seconds':2400,
                              'worker_deadline_seconds':1800,'max_command_seconds':1500,
                              'total_reserve_usd':2.0,'incidental_allowance_usd':.75}
    for filename,value in [('BUNDLE_CONTENTS.json',manifest),('RUNTIME_FREEZE.json',freeze)]:
        (output/filename).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
    if settings_source:
        old=json.loads(settings_source.read_text(encoding='utf8'))
        keep=['profile','region','account','instance','bucket','stop_role_arn','usd_per_hour','rate_source']
        settings={k:old[k] for k in keep if k in old}
        settings['prefix']=f'praxis-next/provics-qualification/20260923-attempt{attempt_id}/'
        target=output/'settings.json'
        if target.exists() and json.loads(target.read_text())!=settings:raise ValueError('Private settings differ')
        target.write_text(json.dumps(settings,indent=2)+'\n',encoding='utf8')
    return freeze


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--settings-source',type=Path)
    p.add_argument('--attempt-id',type=int,default=1)
    a=p.parse_args();f=build(a.repo,a.output,a.settings_source,a.attempt_id)
    print(json.dumps({k:f[k] for k in ['bundle_sha256','bundle_bytes','model_fits','cloud_calls_by_builder','launch_status']},indent=2))
