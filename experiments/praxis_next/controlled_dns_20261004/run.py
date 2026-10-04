"""Loopback-only dummy DNS transfer laboratory and frozen non-XAI comparison."""
import base64,collections,hashlib,json,math,socket,threading,time
from pathlib import Path
import numpy as np
import dpkt
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMClassifier

ROOT=Path(__file__).resolve().parent
OUT=Path('C:/w/px110_controlled_dns_20261004_attempt2')
FEATURES=['length_mean','length_std','length_max','entropy_mean','entropy_std','digit_fraction','query_count','dns_message_bytes','gap_mean','gap_std']

def entropy(s):
    c=collections.Counter(s)
    return -sum((v/len(s))*math.log2(v/len(s)) for v in c.values())

def generate():
    assert not OUT.exists(), 'Use a fresh, explicitly registered run; do not overwrite evidence'
    OUT.mkdir()
    server=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);server.bind(('127.0.0.1',0));server.settimeout(.2)
    address=server.getsockname(); stop=threading.Event(); received={}; errors=[]
    def receive():
        with (OUT/'receiver_messages.jsonl').open('w') as f:
            while not stop.is_set():
                try: wire,peer=server.recvfrom(65535)
                except socket.timeout:continue
                try:
                    assert peer[0]=='127.0.0.1'
                    now=time.perf_counter_ns(); msg=dpkt.dns.DNS(wire)
                    parts=msg.qd[0].name.split('.')
                    label,index,run=parts[:3]
                    received.setdefault(run,[]).append((int(index),label,now,len(wire)))
                    response=dpkt.dns.DNS(id=msg.id,qr=1,rd=1,ra=1,qd=msg.qd)
                    reply=bytes(response)
                    f.write(json.dumps({'run':run,'receiver_monotonic_ns':now,'request_b64':base64.b64encode(wire).decode(),'response_b64':base64.b64encode(reply).decode()})+'\n')
                    server.sendto(reply,peer)
                except Exception as e:errors.append(repr(e));stop.set()
    thread=threading.Thread(target=receive,daemon=True);thread.start()
    client=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);client.settimeout(3)
    rows=[]; manifests=[]
    try:
        for split,npos,nneg,seed in [('train',24,480,11001),('calibration',12,240,11002),('development',24,480,11003)]:
            rng=np.random.default_rng(seed)
            labels=np.array([1]*npos+[0]*nneg);rng.shuffle(labels)
            for number,y in enumerate(labels):
                run=f'r{seed}{number:04d}'; count=int(rng.choice([8,16,32])); gap=float(rng.choice([0,.0005,.001]))
                size=int(rng.choice([8,16,32])); chunks=[]; expected=None
                if y:
                    text_mode=bool(rng.integers(2))
                    expected=(b'harmless research file '*(count*size//23+2))[:count*size] if text_mode else rng.bytes(count*size)
                    chunks=[base64.b32encode(expected[i:i+size]).decode().rstrip('=').lower() for i in range(0,len(expected),size)]
                else:
                    mode=int(rng.integers(3))
                    for i in range(count):
                        if mode==0:label=f'{rng.choice(["mail","api","sync","cdn","service"])}-{rng.integers(10000)}'
                        elif mode==1:label=hashlib.sha256(rng.bytes(size)).hexdigest()[:int(rng.choice([16,32,52]))]
                        else:label=base64.b32encode(rng.bytes(size)).decode().rstrip('=').lower()
                        chunks.append(label)
                start=time.time_ns()
                for i,label in enumerate(chunks):
                    q=dpkt.dns.DNS(id=i,rd=1,qd=[dpkt.dns.DNS.Q(name=f'{label}.{i}.{run}.lab.test',type=dpkt.dns.DNS_A)])
                    request=bytes(q);client.sendto(request,address); reply,peer=client.recvfrom(65535)
                    assert peer==address and dpkt.dns.DNS(reply).id==i
                    if gap:time.sleep(gap)
                records=received[run]
                assert len(records)==len(chunks) and [r[0] for r in records]==list(range(len(chunks)))
                received_labels=[r[1] for r in records]
                verified=None; sender_hash=receiver_hash=None
                if y:
                    decoded=b''.join(base64.b32decode(s.upper()+'='*((-len(s))%8)) for s in received_labels)
                    sender_hash=hashlib.sha256(expected).hexdigest();receiver_hash=hashlib.sha256(decoded).hexdigest()
                    verified=sender_hash==receiver_hash;assert verified
                    (OUT/(run+'.received.bin')).write_bytes(decoded)
                lengths=np.array([len(s) for s in received_labels]); ent=np.array([entropy(s) for s in received_labels])
                gaps=np.diff([r[2] for r in records])/1e9
                feature=[lengths.mean(),lengths.std(),lengths.max(),ent.mean(),ent.std(),sum(c.isdigit() for s in received_labels for c in s)/sum(lengths),len(records),sum(r[3] for r in records),gaps.mean(),gaps.std()]
                rows.append({'id':run,'split':split,'y':int(y),'x':[float(v) for v in feature]})
                manifests.append({'id':run,'split':split,'label':int(y),'start_wall_ns':start,'end_wall_ns':time.time_ns(),'messages':len(records),'sender_sha256':sender_hash,'receiver_sha256':receiver_hash,'verified_transfer':verified})
            print(split,'generated',len(labels),'sequences',flush=True)
    finally:
        stop.set();thread.join(timeout=3);client.close();server.close()
    assert not errors,errors
    (OUT/'cases.json').write_text(json.dumps(rows))
    (OUT/'transfers.json').write_text(json.dumps(manifests,indent=2))
    return rows,manifests

def main():
    frozen=json.loads((ROOT/'FREEZE.json').read_text())
    assert hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest()==frozen['sha256']
    rows,manifest=generate()
    sets={s:[r for r in rows if r['split']==s] for s in ['train','calibration','development']}
    X={s:np.array([r['x'] for r in rs]) for s,rs in sets.items()}; y={s:np.array([r['y'] for r in rs]) for s,rs in sets.items()}
    models={'logistic':make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,random_state=11001)),
            'lightgbm':LGBMClassifier(n_estimators=100,num_leaves=9,learning_rate=.05,random_state=11001,n_jobs=2,verbosity=-1)}
    scores={s:{} for s in ['calibration','development']}
    for name,model in models.items():
        model.fit(X['train'],y['train'])
        import joblib
        joblib.dump(model,OUT/(name+'.joblib'))
        for s in scores:scores[s][name]=model.predict_proba(X[s])[:,1]
    for s in scores:
        ranks=[]
        for col in [0,3,6,7]:
            reference=np.sort(X['train'][y['train']==0,col])
            ranks.append(np.searchsorted(reference,X[s][:,col],side='right')/len(reference))
        scores[s]['composite']=np.mean(ranks,axis=0)
    table=[]
    for s in scores:
        for name,score in scores[s].items():
            k=math.ceil(.05*len(score)); ids=np.array([r['id'] for r in sets[s]])
            chosen=np.lexsort((ids,-score))[:k]; hits=int(y[s][chosen].sum())
            table.append({'split':s,'method':name,'cases':len(score),'budget':k,'verified_transfers':int(y[s].sum()),'transfers_surfaced':hits,'transfers_missed':int(y[s].sum())-hits,'benign_referrals':k-hits})
    calibration=[r for r in table if r['split']=='calibration']
    winner=sorted(calibration,key=lambda r:(-r['transfers_surfaced'],r['benign_referrals'],r['method']))[0]['method']
    selected=next(r for r in table if r['split']=='development' and r['method']==winner)
    result={'experiment':'PX-110','status':'CONTROLLED_DEVELOPMENT_FEASIBILITY_ONLY','features':FEATURES,
       'verified_transfers':sum(m['verified_transfer'] is True for m in manifest),'benign_sequences':sum(m['label']==0 for m in manifest),
       'rows':table,'calibration_selected_method':winner,'headroom_gate':selected['transfers_missed']>=3,
       'xai_benefit_tested':False,'aws_spend_usd':0,
       'limits':['One custom loopback harness; not real APT traffic.','Complete DNS message logs are not PCAPs.','No receiver metadata used as detector input.','No new confirmation or novelty claim.']}
    (ROOT/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'predictions.json').write_text(json.dumps({s:{k:v.tolist() for k,v in methods.items()} for s,methods in scores.items()}))
    (ROOT/'EVIDENCE.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
