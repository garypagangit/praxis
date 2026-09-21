"""Acquire only the small author CSV and README; never the 1.8 GB packet capture."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.request

RECORD='https://zenodo.org/api/records/16911636'
ALLOWED={'SandwormAPT_flow_labelled.csv':1342640,'APT_Dataset_Readme.pdf':525281}


def acquire(output):
    if output.exists() and any(output.iterdir()):raise ValueError('Use a fresh directory; existing acquisition is preserved.')
    output.mkdir(parents=True,exist_ok=True)
    metadata=urllib.request.urlopen(RECORD,timeout=45).read();data=json.loads(metadata)
    if data['metadata']['license']['id']!='cc-by-4.0':raise ValueError('Expected author dataset license changed.')
    (output/'ZENODO_METADATA.json').write_bytes(metadata);receipts=[]
    for item in data['files']:
        name=item['key']
        if name not in ALLOWED:continue
        if item['size']!=ALLOWED[name]:raise ValueError('Source size changed; requalify author version.')
        raw=urllib.request.urlopen(item['links']['self'],timeout=90).read(ALLOWED[name]+1)
        if len(raw)!=ALLOWED[name]:raise ValueError('Unexpected or incomplete download length.')
        if 'md5:'+hashlib.md5(raw).hexdigest()!=item['checksum']:raise ValueError('Author checksum mismatch.')
        (output/name).write_bytes(raw)
        receipts.append({'name':name,'bytes':len(raw),'url':item['links']['self'],
                         'author_checksum':item['checksum'],'sha256':hashlib.sha256(raw).hexdigest()})
    if {r['name'] for r in receipts}!=set(ALLOWED):raise ValueError('Required author files absent.')
    receipt={'acquired_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'record_url':RECORD,
             'dataset_doi':'10.5281/zenodo.16911636','metadata_sha256':hashlib.sha256(metadata).hexdigest(),
             'api_license_metadata':'CC-BY-4.0',
             'rights_caveat':'The landing page copyright field says CC BY-NC-ND 4.0 while its license field/API say CC-BY-4.0. Retain bytes privately for noncommercial evaluation and publish aggregates only; do not redistribute raw or derived data.',
             'files':receipts,'pcap_acquired':False,'scientific_fits':0}
    (output/'ACQUISITION.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    acquire(parser.parse_args().output)
