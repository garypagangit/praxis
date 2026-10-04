"""Read-only qualification of a public sample; never execute or extract archive code."""
from pathlib import Path
import requests, json, tarfile, hashlib
ROOT=Path(__file__).parent
CACHE=Path('C:/w/px107_source_qualification'); CACHE.mkdir(exist_ok=True)
repo='Korving-F/dns-tunnel-dataset'
r=requests.get(f'https://api.github.com/repos/{repo}/git/trees/master?recursive=1',timeout=45); r.raise_for_status()
j=r.json(); files=[x for x in j['tree'] if x['path'].endswith('_full_dataset.tar.gz')]
sample='dns_tunnel_file_transfer/b6cfd110174fb553bb73a5279358c6c1/b6cfd110174fb553bb73a5279358c6c1_full_dataset.tar.gz'
entry=next(x for x in files if x['path']==sample)
assert entry['size']<25_000_000
url=f'https://raw.githubusercontent.com/{repo}/{j["sha"]}/{sample}'
r=requests.get(url,timeout=60); r.raise_for_status(); assert len(r.content)==entry['size']
p=CACHE/Path(sample).name; p.write_bytes(r.content)
with tarfile.open(p,'r:gz') as t:
    members=[{'path':m.name,'bytes':m.size} for m in t.getmembers() if m.isfile()]
    previews=[]
    transfer_checks=[]
    for m in t.getmembers():
        if m.isfile() and m.name.endswith('.cast'):
            content=t.extractfile(m).read(100000).decode('utf-8',errors='replace')
            if 'rsync' in content:
                transfer_checks.append({'path':m.name,'server_to_client_pull': '10.0.0.1:/root/test-file /tmp/' in content,'completion_marker': '100%' in content})
        if m.isfile() and m.name.endswith(('.cast','.log')) and len(previews)<5:
            previews.append({'path':m.name,'prefix':t.extractfile(m).read(1500).decode('utf-8',errors='replace')})
result={'id':'PX-107','status':'SOURCE_SAMPLE_INSPECTED_NOT_EFFICACY_TEST','source':repo,'commit':j['sha'],'archives':len(files),'file_transfer_archives':sum(x['path'].startswith('dns_tunnel_file_transfer/') for x in files),'c2_archives':sum(x['path'].startswith('dns_tunnel_c2/') for x in files),'total_archive_bytes':sum(x['size'] for x in files),'sample_url':url,'sample_bytes':entry['size'],'sha256':hashlib.sha256(r.content).hexdigest(),'sample_members':members,'sample_previews':previews,'limitations':['Archive configurations are not automatically independent transfer episodes.','Matched benign workloads, successful-transfer boundaries and collection artifacts need qualification.','DNS tunneling is not automatically data exfiltration; C2 excluded from positive exfiltration count.','No model trained, no efficacy outcome, no paid AWS job.']}
result['transfer_checks']=transfer_checks
result['primary_exfiltration_eligibility']='NOT_QUALIFIED: sampled successful transfer is a server-to-client pull; outbound exfiltration not established.'
(ROOT/'QUALIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('sample_previews','sample_members')},indent=2))
print(json.dumps(members[:20],indent=2))
