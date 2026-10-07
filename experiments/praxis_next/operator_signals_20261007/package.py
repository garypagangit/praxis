"""Compress prediction evidence and write a public-file integrity manifest."""
import gzip, hashlib, json
from prepare import HERE,save,sha

for folder in [HERE/'evidence',HERE/'initial_solver/evidence']:
 for name in ['PREDICTIONS.json','ABLATION_PREDICTIONS.json']:
  p=folder/name
  out=p.with_suffix(p.suffix+'.gz')
  with out.open('wb') as raw:
   with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as z:z.write(p.read_bytes())
  with gzip.open(out,'rb') as z:assert hashlib.sha256(z.read()).hexdigest()==sha(p)
manifest=[]
for p in sorted(HERE.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(HERE)
 if any(x in {'cache','__pycache__'} for x in rel.parts):continue
 if p.name in {'MANIFEST.json','PREDICTIONS.json','ABLATION_PREDICTIONS.json'}:continue
 manifest.append({'path':rel.as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
save(HERE/'evidence/MANIFEST.json',manifest)
print('Public files',len(manifest),'bytes',sum(x['bytes'] for x in manifest))
