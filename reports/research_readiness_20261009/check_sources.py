"""Capture public source availability and metadata; do not run downloaded code."""
import concurrent.futures
import hashlib
import json
import pathlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

HERE=pathlib.Path(__file__).resolve().parent
SOURCES={
 'trace_paper':'https://arxiv.org/html/2605.01186v1',
 'trace_artifact':'https://anonymous.4open.science/r/TRACE-A66F',
 'trace_public_client':'https://anonymous.4open.science/script/core.3b07189932.min.js',
 'trace_app_client':'https://anonymous.4open.science/script/vendor.8d670664b8.min.js',
 'trace_repo_metadata':'https://anonymous.4open.science/api/repo/TRACE-A66F',
 'ohai_release':'https://www.sei.cmu.edu/library/observational-humanai-ohai-a-defender-attribution-framework-for-distinguishing-human-vs-ai-threats/',
 'lyptus_tree':'https://api.github.com/repos/lyptus-research/cyber-task-horizons-data/git/trees/main?recursive=1',
 'lyptus_human_readme':'https://raw.githubusercontent.com/lyptus-research/cyber-task-horizons-data/main/data/human/eval_logs/README.md',
 'lyptus_methodology':'https://raw.githubusercontent.com/lyptus-research/cyber-task-horizons-data/main/data/methodology/README.md',
 'lyptus_study':'https://lyptusresearch.org/research/offensive-cyber-time-horizons',
 'palisade_tree':'https://api.github.com/repos/PalisadeResearch/ai-vs-humans-ctf-report/git/trees/main?recursive=1',
 'palisade_interactions':'https://raw.githubusercontent.com/PalisadeResearch/ai-vs-humans-ctf-report/5af7ec957cd4fdae0bc8236e3b2b0bec4cba1393/data/AI%20vs%20Humans%20CTF%20-%20Challenge%20Interactions.csv',
 'honey_release':'https://zenodo.org/api/records/20818246',
}
def get(item):
    name,url=item
    record={'name':name,'url':url,'checked_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'ResearchDataQualification/1.0'})
        with urllib.request.urlopen(req,timeout=25) as response:
            data=response.read(6000000)
            record.update(status=response.status,final_url=response.url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        suffix='.json' if name.endswith('tree') or name=='honey_release' else '.txt'
        target=HERE/'source_snapshots'/(name+suffix)
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
        record['snapshot']=str(target)
        if name.endswith('tree'):
            tree=json.loads(data)
            paths=[x['path'] for x in tree.get('tree',[]) if x['type']=='blob']
            record.update(revision=tree.get('sha'),truncated=tree.get('truncated'),files=len(paths))
            record['human_eval_files']=len([p for p in paths if 'data/human/eval_logs/' in p and p.endswith(('.eval','.eval.gz'))])
            record['possible_control_files']=[p for p in paths if any(k in p.lower() for k in ['scripted','automation','baseline','human','readme','license'])][:100]
        if name=='honey_release':
            release=json.loads(data)
            record['files']=[{'key':x['key'],'bytes':x['size'],'checksum':x.get('checksum')} for x in release.get('files',[])]
            record['license']=release.get('metadata',{}).get('license')
    except Exception as exc:
        record['error']=type(exc).__name__+': '+str(exc)
        if isinstance(exc,urllib.error.HTTPError): record['status']=exc.code
    return record
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(get,SOURCES.items()))
    (HERE/'SOURCE_ACCESS.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k not in ['possible_control_files','snapshot']} for r in records],indent=2))
