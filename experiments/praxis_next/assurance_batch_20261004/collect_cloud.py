"""Finish collection after the controller exits, including slow-stop recovery."""
import hashlib,json,subprocess,sys,tarfile,time
from pathlib import Path
import psutil
from experiments.praxis_next.compute.provics_cloud_control import control
HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/assurance_aws_20261004_attempt2')
def main(pid):
    proc=psutil.Process(pid)
    assert 'experiments.praxis_next.assurance_batch_20261004.cloud_run' in proc.cmdline()
    deadline=time.monotonic()+3000
    while proc.is_running() and time.monotonic()<deadline: time.sleep(10)
    if proc.is_running(): raise TimeoutError('Controller still running; watchdog retained')
    c=control.Controller(PRIVATE/'settings.json')
    while c.instance()['State']['Name']!='stopped' and time.monotonic()<deadline: time.sleep(10)
    assert c.instance()['State']['Name']=='stopped', 'Do not remove watchdog while running'
    if not (PRIVATE/'COMPUTE.json').exists():
        r=c.finalize(); assert r['status']=='CLOSED_VERIFIED_STOPPED'
        (PRIVATE/'COMPUTE.json').write_text(Path(r['receipt']).read_text())
    dest=PRIVATE/'collected'
    if not dest.exists():
        for name in ['result.tar.gz','result.sha256']:
            c.transfer('download',PRIVATE/name,c.settings['prefix']+'outputs/'+name)
        assert hashlib.sha256((PRIVATE/'result.tar.gz').read_bytes()).hexdigest()==(PRIVATE/'result.sha256').read_text().strip()
        dest.mkdir()
        with tarfile.open(PRIVATE/'result.tar.gz') as a:
            for m in a.getmembers(): assert not m.issym() and not m.islnk() and (dest/m.name).resolve().is_relative_to(dest.resolve())
            a.extractall(dest)
    subprocess.run([sys.executable,str(HERE/'finish_cloud.py')],check=True)
if __name__=='__main__': main(int(sys.argv[1]))
