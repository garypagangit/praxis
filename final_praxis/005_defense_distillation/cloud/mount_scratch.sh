set -eu
python3 - <<'PY'
import json,pathlib,subprocess,time
serial='vol02b4f3854b7ff5bc4'
mount=pathlib.Path('/mnt/praxis-20260912-005')
for attempt in range(15):
    items=json.loads(subprocess.check_output(['lsblk','--json','--bytes','--output','NAME,PATH,SERIAL,SIZE,FSTYPE,MOUNTPOINT,TYPE'],text=True))['blockdevices']
    matches=[x for x in items if (x.get('serial') or '').replace('-','')==serial and x['type']=='disk']
    if len(matches)==1:break
    time.sleep(2)
else:raise RuntimeError('Authorized new scratch volume did not appear by exact serial')
device=matches[0]
if int(device['size'])!=100*1024**3:raise RuntimeError('Unexpected size')
if device.get('mountpoint') not in [None,str(mount)]:raise RuntimeError('Unexpected mount; refusing to format')
if device.get('children'):raise RuntimeError('Unexpected partitions; refusing to format')
if not device.get('fstype'):
    probe=subprocess.run(['blkid',device['path']],capture_output=True,text=True)
    if probe.returncode!=2 or probe.stdout.strip():raise RuntimeError('Unexpected existing signature')
    subprocess.run(['mkfs.ext4','-L','praxis00520260912',device['path']],check=True)
elif device['fstype']!='ext4':raise RuntimeError('Unexpected filesystem')
mount.mkdir(parents=True,exist_ok=True)
if device.get('mountpoint')!=str(mount):
    if any(mount.iterdir()):raise RuntimeError('Refuse to conceal existing directory data')
    subprocess.run(['mount',device['path'],str(mount)],check=True)
uuid=subprocess.check_output(['blkid','-s','UUID','-o','value',device['path']],text=True).strip()
entry='UUID='+uuid+' '+str(mount)+' ext4 defaults,nofail 0 2\n'
fstab=pathlib.Path('/etc/fstab')
if str(mount) not in fstab.read_text():
    with fstab.open('a') as f:f.write('\n# Authorized Final Praxis005 temporary experiment volume\n'+entry)
for name in ['tmp','hf_cache','xdg_cache','pip_cache']:(mount/name).mkdir(exist_ok=True)
print(json.dumps({'device':device['path'],'matched_serial':serial,'mount':str(mount),'uuid':uuid}))
PY
df -h /mnt/praxis-20260912-005
