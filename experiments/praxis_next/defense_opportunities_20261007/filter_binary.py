import json,pathlib,shutil
from threadpoolctl import threadpool_limits
from screen import HERE,save,sha,e
import binary as b
for name in ['BINARY_RESULTS.json','BINARY_PREDICTIONS.json']:
 shutil.copyfile(HERE/'evidence'/name,HERE/'evidence'/('UNFILTERED_'+name))
source=HERE/'evidence/REPLAY_INPUT.json';rows=json.loads(source.read_text());counts={0:0,1:0}
for r in rows:
 old=r['shell_commands'];r['shell_commands']=[c for c in old if e.verb(c) not in {'task','clear','exit','history'}];counts[r['label']]+=len(old)-len(r['shell_commands'])
dest=HERE/'evidence/FILTERED_REPLAY_INPUT.json';save(dest,rows);b.HERE=HERE
with threadpool_limits(limits=1):b.run(dest)
save(HERE/'evidence/CONTROL_FILTER.json',{'removed_submissions_all':counts,'source_sha256':sha(source),'filtered_sha256':sha(dest),'code_sha256':sha(pathlib.Path(__file__)),'stage':'post-unfiltered-result sensitivity; not preregistered'})
