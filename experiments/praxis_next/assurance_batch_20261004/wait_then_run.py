"""Wait for prior shutdown, recover this run's disk usage, then run/audit GPU batch."""
import json,subprocess,sys,time
from pathlib import Path
import psutil
from experiments.praxis_next.compute.provics_cloud_control import control
HERE=Path(__file__).resolve().parent
def main(pid):
    try: proc=psutil.Process(pid)
    except psutil.NoSuchProcess: proc=None
    deadline=time.monotonic()+1800
    while proc is not None and proc.is_running() and time.monotonic()<deadline: time.sleep(10)
    if proc is not None and proc.is_running(): raise TimeoutError('Prior controller still active')
    old=Path('C:/w/assurance_aws_20261004_attempt4')
    c=control.Controller(old/'settings.json')
    while c.instance()['State']['Name']!='stopped' and time.monotonic()<deadline:time.sleep(10)
    assert c.instance()['State']['Name']=='stopped'
    if not (old/'COMPUTE.json').exists():
        r=c.finalize();assert r['status']=='CLOSED_VERIFIED_STOPPED'
        (old/'COMPUTE.json').write_text(Path(r['receipt']).read_text())
    print('Prior worker stopped; starting disk recovery and GPU batch',flush=True)
    subprocess.run([sys.executable,'-m','experiments.praxis_next.assurance_batch_20261004.cloud_run'],check=True)
    subprocess.run([sys.executable,str(HERE/'finish_cloud.py')],check=True)
if __name__=='__main__':main(int(sys.argv[1]))
