"""Summarize verified downloads without counting duplicate archives as new data."""
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
inventory = json.loads((root/'CIC_COMPLETE_INVENTORY.json').read_text())
audit = json.loads((root/'CIC_COMPLETE_AUDIT.json').read_text())
assert audit['all_checks_pass']
unique, duplicates = {}, []
for archive in inventory['archives']:
    sha = archive['sha256']
    if sha in unique:
        duplicates.append([archive['local_file'], unique[sha]['local_file']])
    else:
        unique[sha] = archive
cache = Path('C:/w/px107_source_qualification/cic_browser_20261004')
cache.mkdir(parents=True, exist_ok=True)
for sha, archive in unique.items():
    target = cache / (sha + '.zip')
    if not target.exists():
        shutil.copyfile(Path('C:/Users/garyp/Downloads')/archive['local_file'], target)
summary = {}
for category, prefix in [('attack', 'Attacks/'), ('benign', 'Benign/')]:
    members = [(a,m) for a in unique.values() for m in a['members'] if 'pcap' in m and m['path'].startswith(prefix)]
    checks = [next(r for r in audit['files'] if r['archive']==a['local_file'] and r['member']==m['path']) for a,m in members]
    summary[category] = {'distinct_capture_files':len(members),
        'packets':sum(m['pcap']['packets'] for _,m in members),
        'truncated_packets':sum(m['pcap']['truncated_packets'] for _,m in members),
        'udp_destination_53_packets':sum(r['udp_destination_53_packets'] for r in checks),
        'decodable_dns_queries':sum(r['decodable_dns_queries'] for r in checks),
        'dns_parse_errors':sum(r['dns_parse_errors'] for r in checks),
        'independent_reader_checks_passed':sum(len(r['checks']) for r in checks)}
out = {'download_status':'REQUESTED_PCAP_ARCHIVES_PRESENT', 'duplicates':duplicates,
       'summary':summary, 'source_qualification':'PARTIAL_CAPTURE_TRUNCATION_AND_EPISODE_PROVENANCE_UNRESOLVED',
       'limits':['Capture files are not verified independent successful transfers.',
                 'DNS parsing failures must not become class-predictive missing-value shortcuts.',
                 'No new models fitted or recovery efficacy measured.'],
       'next_step':'Assess usable header/timing features and episode provenance; complete DNS/payload reconstruction is not supported by these truncated captures alone.'}
(root/'CIC_DOWNLOAD_FINDINGS.json').write_text(json.dumps(out,indent=2)+'\n')
registry_path = root.parent/'REGISTRY.json'
registry = json.loads(registry_path.read_text())
for row in registry['experiments']:
    if row['id'] in ['PX-108','PX-109']:
        row['status']='SOURCE_RECEIVED_QUALIFICATION_PARTIAL'
        row['source_results']=root.name+'/CIC_DOWNLOAD_FINDINGS.json'
        row['finding']='All requested PCAP archives received; duplicates excluded. 12 attack and 6 benign captures; 72 independent reader checks pass. Attack packets heavily truncated; payload validity and independent transfer episodes unresolved. No efficacy result.'
registry_path.write_text(json.dumps(registry,indent=2)+'\n')
print(json.dumps(out,indent=2))
