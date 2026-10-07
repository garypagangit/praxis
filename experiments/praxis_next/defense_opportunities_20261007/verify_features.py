"""Check every reused first10 feature record against the original parsed log."""
import json,pathlib
from screen import HERE,OLD,e,save,sha
rows=json.loads((OLD/'cache/records.json').read_text());fs=json.loads((OLD/'cache/features.json').read_text());assert set(fs)=={r['id'] for r in rows}
for r in rows:assert e.features(r['turns'][:10])==fs[r['id']],r['id']
save(HERE/'evidence/REUSED_FEATURES.json',{'status':'PASS','sessions_recomputed':len(rows),'feature_cache_sha256':sha(OLD/'cache/features.json'),'record_cache_sha256':sha(OLD/'cache/records.json'),'feature_code_sha256':sha(OLD/'experiment.py'),'scope':'All first10 cached representations exactly equal fresh extraction; no fits changed'})
print('PASS',len(rows),'recomputed feature records')
