"""Publish bounded prediction chunks and checksums without raw Honey logs."""
import gzip,json,pathlib,hashlib
from screen import HERE,save,sha
with gzip.open(HERE/'cache/predictions.json.gz','rt',encoding='utf-8') as f:pred=json.load(f)
for i in range(0,len(pred),30):
 p=HERE/'evidence'/f'PREDICTIONS_{i//30:02}.json.gz';data=json.dumps(pred[i:i+30],separators=(',',':')).encode()
 p.write_bytes(gzip.compress(data,mtime=0))
 assert gzip.decompress(p.read_bytes())==data
files=[]
for p in sorted(HERE.rglob('*')):
 if not p.is_file() or any(x in {'cache','__pycache__'} for x in p.relative_to(HERE).parts) or p.name=='MANIFEST.json':continue
 files.append({'path':p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
save(HERE/'evidence/MANIFEST.json',files)
print('public files',len(files),'bytes',sum(x['bytes'] for x in files),'largest',max(x['bytes'] for x in files))
