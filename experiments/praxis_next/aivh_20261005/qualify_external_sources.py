"""Inspect public records and run a frozen one-source challenge; execute no logs."""
import collections, hashlib, json, re, zipfile
from pathlib import Path
import joblib
from build_development_data import normalize

HERE=Path(__file__).resolve().parent
DATA=Path('C:/w/aivh_review_20261005/candidates')
MODEL=Path('C:/w/px117_aws_20261005/collected/outputs/ngrams.joblib')

def digest(path,algorithm='sha256'):
    return hashlib.new(algorithm,path.read_bytes()).hexdigest()

def main():
    expected={'cache.zip':'e7717ec8e394be849f983745ba5bdb79',
              'output.zip':'c35c2a9687567ea1e933286d969fc82f'}
    for n,h in expected.items():
        assert digest(DATA/n,'md5')==h,(n,'publisher checksum mismatch')
    stats=collections.Counter(); rows=[]; techniques=collections.Counter()
    artifact=joblib.load(MODEL)
    with zipfile.ZipFile(DATA/'cache.zip') as cache,zipfile.ZipFile(DATA/'output.zip') as labels:
        for n in sorted(cache.namelist()):
            if not n.startswith('cache/syslog/') or not n.endswith('.json'):continue
            stats['cache_instances']+=1
            instance=Path(n).stem
            ln='output/system_labels/'+instance+'.json'
            if ln not in labels.namelist():
                stats['instances_without_label_file']+=1;continue
            mapping=collections.defaultdict(set)
            for lab in json.loads(labels.read(ln)).values():
                if lab.get('doubt') or lab.get('rejected_by') or not lab.get('technique'):continue
                for uid in lab.get('event_uids',[]):mapping[uid].add(lab['technique'])
            candidates=[]
            for event in json.loads(cache.read(n))['events']:
                stats['cache_events']+=1
                if event['event_uid'] not in mapping:continue
                stats['accepted_label_events']+=1
                sys=event['records'].get('SYSCALL',[])
                if not any(s.get('syscall')=='execve' and s.get('success')=='yes' and
                           re.match(r'^(pts|tty)',s.get('tty','')) for s in sys):continue
                procs=event['records'].get('PROCTITLE',[])
                if len(procs)!=1 or not procs[0].get('proctitle','').strip():continue
                candidates.append((event['timestamp'],event['event_uid'],normalize(procs[0]['proctitle'])))
                techniques.update(mapping[event['event_uid']])
            candidates.sort();stats['eligible_events']+=len(candidates)
            if len(candidates)<10:
                stats['instances_below_ten']+=1;continue
            prefix=candidates[:10]; text='\n'.join(c[2] for c in prefix)
            score=float(artifact['model'].predict_proba([text])[0,list(artifact['model'].classes_).index(1)])
            rows.append({'instance':instance,'eligible_events':len(candidates),
                         'event_uids':[c[1] for c in prefix],
                         'prefix_sha256':hashlib.sha256(text.encode()).hexdigest(),
                         'score':score,'ai_call':score>=artifact['threshold']})
    pwn=collections.Counter()
    for line in (DATA/'pwn_sample.json').read_text(encoding='utf-8').splitlines():
        r=json.loads(line);pwn['records']+=1
        if r['sourcetype']=='linux_audit':
            m=re.search(r'type=(\w+)',r['raw'])
            if m:pwn[m[1]]+=1
    result={'experiment':'PX-117B','status':'DESCRIPTIVE_SOURCE_CHALLENGE_ONLY',
            'selection':'GAMBiT preferred for acquisition; CasinoLimit available challenge',
            'hashes':{n:digest(DATA/n) for n in expected},'model_sha256':digest(MODEL),
            'threshold':artifact['threshold'],'qualification':dict(stats),
            'challenge_instances':len(rows),'ai_calls':sum(r['ai_call'] for r in rows),
            'ai_call_fraction':sum(r['ai_call'] for r in rows)/len(rows) if rows else None,
            'unique_prefixes':len(set(r['prefix_sha256'] for r in rows)),
            'technique_event_counts':dict(techniques),'pwn_n11_sample_counts':dict(pwn),
            'limitations':['AI assistance not excluded in CasinoLimit documentation reviewed',
                          'Process events differ from typed command turns',
                          'Some replacement instances share an attacker',
                          'One class only; no AUROC or AI recall measured',
                          'No refitting; no threshold adjustment'],
            'predictions':rows}
    (HERE/'EXTERNAL_SOURCE_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['qualification','challenge_instances','ai_calls','ai_call_fraction','unique_prefixes']}))

if __name__=='__main__':main()
