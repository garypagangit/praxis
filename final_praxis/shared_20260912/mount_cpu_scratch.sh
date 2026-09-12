set -eu
python3 - <<'PY'
import json,pathlib,subprocess,time
serial='vol0a3755ed724c147ee'
mount=pathlib.Path('/mnt/praxis-20260912-004')
for attempt in range(15):
    items=json.loads(subprocess.check_output(['lsblk','--json','--output','PATH,SERIAL,FSTYPE,MOUNTPOINT,TYPE'],text=True))['blockdevices']
    matches=[x for x in items if (x.get('serial') or '').replace('-','')==serial and x['type']=='disk']
    if len(matches)==1:break
    time.sleep(2)
else:raise RuntimeError('New campaign EBS device did not appear by exact volume serial')
device=matches[0]
if device.get('mountpoint') not in [None,str(mount)]:raise RuntimeError('Unexpected mount; refusing to format')
if device.get('children'):raise RuntimeError('Unexpected partitions; refusing to format')
if not device.get('fstype'):
    # Exact AWS-created campaign volume, no existing filesystem/partitions.
    probe=subprocess.run(['blkid',device['path']],capture_output=True,text=True)
    if probe.returncode!=2 or probe.stdout.strip():raise RuntimeError('Unexpected existing signature')
    subprocess.run(['mkfs.ext4','-L','praxis20260912',device['path']],check=True)
elif device['fstype']!='ext4':raise RuntimeError('Unexpected filesystem')
mount.mkdir(parents=True,exist_ok=True)
if device.get('mountpoint')!=str(mount):subprocess.run(['mount',device['path'],str(mount)],check=True)
uuid=subprocess.check_output(['blkid','-s','UUID','-o','value',device['path']],text=True).strip()
entry='UUID='+uuid+' '+str(mount)+' ext4 defaults,nofail 0 2\n'
fstab=pathlib.Path('/etc/fstab')
if str(mount) not in fstab.read_text():
    with fstab.open('a') as f:f.write('\n# Authorized Final Praxis004 temporary experiment volume\n'+entry)
for name in ['docker','docker-exec','tmp','study','venv']:(mount/name).mkdir(exist_ok=True)
(mount/'docker-config.json').write_text('{}\n')
print(json.dumps({'device':device['path'],'matched_serial':serial,'mount':str(mount),'uuid':uuid}))
PY
systemd-run --unit=praxis-docker-20260912 --collect --property=RuntimeMaxSec=28000 --setenv=DOCKER_TMPDIR=/mnt/praxis-20260912-004/tmp /usr/bin/dockerd --config-file /mnt/praxis-20260912-004/docker-config.json --data-root /mnt/praxis-20260912-004/docker --exec-root /mnt/praxis-20260912-004/docker-exec --pidfile /run/praxis-docker-20260912.pid --host unix:///run/praxis-docker-20260912.sock --bridge none --iptables=false --ip6tables=false --ip-masq=false --storage-driver=overlay2 --containerd-namespace=praxis004 --containerd-plugins-namespace=praxis004-plugins
python3 - <<'PY'
import subprocess,time
for _ in range(20):
    r=subprocess.run(['docker','--host','unix:///run/praxis-docker-20260912.sock','info','--format','{{.DockerRootDir}}'],capture_output=True,text=True)
    if r.returncode==0:
        print(r.stdout);break
    time.sleep(2)
else:raise RuntimeError('Dedicated Docker daemon did not become ready')
PY
df -h /mnt/praxis-20260912-004
