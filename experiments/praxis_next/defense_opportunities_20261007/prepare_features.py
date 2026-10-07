"""Build the reusable first-ten-command feature cache if absent."""
import json
from screen import OLD,e,save
dest=OLD/'cache/features.json'
if dest.exists():
 print('Existing feature cache retained:',dest)
else:
 rows=json.loads((OLD/'cache/records.json').read_text())
 save(dest,{r['id']:e.features(r['turns'][:10]) for r in rows})
 print('Prepared',len(rows),'session features')
