"""Reconstruct transfers from saved received messages and replay review counts."""
import base64,hashlib,json,math
from collections import defaultdict
from pathlib import Path
import dpkt

ROOT=Path(__file__).resolve().parent
OUT=Path('C:/w/px110_controlled_dns_20261004_attempt2')
def main():
    manifest=json.loads((OUT/'transfers.json').read_text())
    cases=json.loads((OUT/'cases.json').read_text())
    groups=defaultdict(list); messages=0
    with (OUT/'receiver_messages.jsonl').open() as f:
        for line in f:
            record=json.loads(line);q=dpkt.dns.DNS(base64.b64decode(record['request_b64']))
            reply=dpkt.dns.DNS(base64.b64decode(record['response_b64']))
            assert reply.id==q.id and reply.qr==1
            data,index,run,*suffix=q.qd[0].name.split('.')
            assert suffix==['lab','test'] and run==record['run']
            groups[run].append((int(index),data));messages+=1
    checks=[]
    for m in manifest:
        rs=sorted(groups[m['id']]);assert len(rs)==m['messages']
        assert [i for i,_ in rs]==list(range(len(rs)))
        if m['label']==1:
            content=b''.join(base64.b32decode(s.upper()+'='*((-len(s))%8)) for _,s in rs)
            digest=hashlib.sha256(content).hexdigest()
            assert digest==m['sender_sha256']==m['receiver_sha256']
            assert content==(OUT/(m['id']+'.received.bin')).read_bytes()
            checks.append(m['id'])
    assert len(groups)==len(cases)==1260
    preds=json.loads((OUT/'predictions.json').read_text())
    result=json.loads((ROOT/'RESULTS.json').read_text())
    replay=[]
    for row in result['rows']:
        subset=[r for r in cases if r['split']==row['split']]
        score=preds[row['split']][row['method']]
        ranked=sorted(zip(subset,score),key=lambda rs:(-rs[1],rs[0]['id']))
        k=math.ceil(.05*len(subset));hits=sum(r['y'] for r,_ in ranked[:k])
        assert hits==row['transfers_surfaced'] and k-hits==row['benign_referrals']
        replay.append({'split':row['split'],'method':row['method'],'pass':True})
    out={'complete_received_dns_messages':messages,'sequences':len(groups),
         'independently_reconstructed_transfers':len(checks),'receiver_files_equal':True,
         'prediction_replay_checks':replay,'all_checks_pass':True,
         'limit':'Application-message evidence from one loopback generator; no link-layer capture or real-world generalization.'}
    (ROOT/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
