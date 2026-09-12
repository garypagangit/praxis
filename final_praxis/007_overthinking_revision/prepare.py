"""Freeze calibration-only subsets of the public SRU release; never call a model."""
import hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
REV='36974db6bb1dc6bb31ff9fb56c9201beed78edd8'
BASE='https://raw.githubusercontent.com/dependentsign/sycophancy-rational-updating/'+REV+'/data/'
LOCK={'aqua':('c87f2eb2bf77eb717da379dce03891dd97c33b1295a94d9e4103aa37a766e89e','9424d64952d7801fc62e1f6740459f524d611326dd1f0f510d9fe1b2e463ec19'),'exfever':('b584797d46b7b807891a433b5879b647841aa85e9654692c92de4943796c9fd7','352ff9b0ccf412c57b925ab4ad86536fcb02e04bb4f1f957efb7078f544ff58b')}
def main():
    target=HERE/'source_data';target.mkdir(parents=True,exist_ok=True)
    items=[]
    for name,pair in LOCK.items():
        for suffix,expected in [(name+'.jsonl',pair[0]),('splits/'+name+'.json',pair[1])]:
            path=target/suffix;path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():raw=path.read_bytes()
            else:
                with urllib.request.urlopen(BASE+suffix,timeout=60) as r:raw=r.read()
                path.write_bytes(raw)
            assert hashlib.sha256(raw).hexdigest()==expected,suffix
        rows=[json.loads(s) for s in (target/(name+'.jsonl')).read_text(encoding='utf-8').splitlines()]
        split=json.loads((target/'splits'/(name+'.json')).read_text())
        cal=set(split['cal']);test=set(split['test']);assert not cal.intersection(test)
        chosen=sorted([r for r in rows if r['qid'] in cal],key=lambda r:hashlib.sha256(f"007-pilot-v1:{name}:{r['qid']}".encode()).hexdigest())[:16]
        assert len(chosen)==16
        for row in chosen:
            items.append({'id':str(row['qid']),'dataset':name,'question':row['question'] if name=='aqua' else row['claim'],
                'options':[{'label':label,'text':value} for label,value in zip(row['letters'],row['choice_texts'])] if name=='aqua' else [],
                'gold':row['gold_letter'] if name=='aqua' else ('TRUE' if row['gold_bool'] else 'FALSE'),'evidence':row['evidence']})
    frozen={'calibration_only':True,'source_revision':REV,'source_hashes':LOCK,'selection':'16 per dataset by SHA256(007-pilot-v1:dataset:qid), ascending','items':items}
    raw=(json.dumps(frozen,indent=2,ensure_ascii=False)+'\n').encode()
    path=HERE/'fixtures.json'
    if path.exists():assert path.read_bytes()==raw,'Immutable fixture differs'
    else:path.write_bytes(raw)
    print(json.dumps({'items':len(items),'fixture_sha256':hashlib.sha256(raw).hexdigest()}))
if __name__=='__main__':main()
