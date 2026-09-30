"""Small public metadata requests only; no authentication or challenge bypass."""
import concurrent.futures,json,datetime
from pathlib import Path
import requests
URLS=[
'https://api.github.com/repos/IoT-CPS-Labs/SCVIC-APT-2021',
'https://api.datacite.org/dois/10.21227/g2z5-ep97',
'https://data.mendeley.com/public-api/datasets/b8fmtzvpy8/versions/4',
'https://data.mendeley.com/public-api/datasets/b8fmtzvpy8/versions/4/files']
def fetch(url):
    try:
        r=requests.get(url,timeout=25);d={'url':url,'status':r.status_code,'bytes':len(r.content),'content_type':r.headers.get('content-type')}
        if 'datacite' in url and r.ok:
            a=r.json()['data']['attributes'];d['metadata']={k:a.get(k) for k in ['contentUrl','relatedIdentifiers','url']}
        if 'mendeley' in url and r.ok and 'json' in d['content_type']:d['metadata']=r.json()
        return d
    except requests.RequestException as e:return {'url':url,'error':type(e).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,URLS))
Path(__file__).with_name('SOURCE_CHECKS.json').write_text(json.dumps({'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requests':rows},indent=2)+'\n')
for r in rows:print(r['url'],r.get('status',r.get('error')),r.get('bytes'))
