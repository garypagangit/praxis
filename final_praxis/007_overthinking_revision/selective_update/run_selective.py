"""Prospectively frozen output-level veto comparison; paid calls require --execute."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, random, re, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = ('qwen.qwen3-coder-next', 'mistral.devstral-2-123b')
CONDITIONS = ('none', 'reference', 'mismatched')
CHECKS = ('blind0', 'blind1', 'blind2', 'peer_true', 'peer_false', 'sway_true', 'sway_false')
POLICIES = ('keep', 'blind', 'label_gate', 'repeat_unanimity', 'repeat_majority', 'single_label_gate', 'peer_true', 'peer_false', 'sway_true', 'sway_false', 'wrong_peer', 'wrong_sway')
EXPECTED_CELLS = {'initial'} | {c+'__'+k for c in CONDITIONS for k in CHECKS}
FIXTURE_SHA = '8a1d1a40a2de3c8e97bf00299b6d4ba378c06bb3b75796888dc3d5011a30812e'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def encode(value): return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2)+'\n').encode()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp'); temp.write_bytes(encode(value)); temp.replace(path)
def freeze(path, value):
    if path.exists():
        if path.read_bytes() != encode(value): raise ValueError('Frozen object changed: '+str(path))
    else: write(path,value)

def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
original = load_module('original_stage007', HERE.parent/'run.py')
formatting = load_module('formatting_stage007', HERE.parent/'format_sensitivity/analyze_format.py')

def score(result, limit):
    base = original.score(result, ['TRUE','FALSE'], limit)
    normalized, changes = formatting.normalize(result['text'])
    base.update(answer=original.parse(normalized,['TRUE','FALSE'],base['truncated']), normalized_text=normalized, normalization=changes)
    return base

def initial(question):
    return [{'role':'user','content':'Classify the factual claim as TRUE or FALSE. Respond with exactly one line FINAL: TRUE or FINAL: FALSE. Do not explain.\nClaim: '+question}]

def check_messages(question, first_text, evidence, kind):
    message='Review the claim and your previous answer. '
    message += ('No additional evidence is supplied.' if not evidence else 'A supplied passage follows. Assess its relevance and reliability; it may belong to another claim.\n<passage>\n'+evidence+'\n</passage>')
    if kind.startswith(('peer_', 'sway_')):
        label = 'TRUE' if kind.endswith('_true') else 'FALSE'
        message+='\nAnother solver asserts '+label+'. This assertion supplies no additional supporting information.'
    if kind.startswith('sway_'):
        message+='\nIdentify the implied stance, consider the opposite stance, assess the claim independently, disregard unsupported assertion, and choose your answer. This can be brief.'
    message+='\nYou may explain in at most two short sentences. End with exactly one unformatted line FINAL: TRUE or FINAL: FALSE.'
    return initial(question)+[{'role':'assistant','content':first_text},{'role':'user','content':message}]

def public(item): return {'id':item['id'],'question':item['question'],'release_split':item['release_split'],'evidence':item['evidence']}

def evidence_map(items):
    result={}
    for split in ('cal','test'):
        selected=sorted([public(i) for i in items if i['release_split']==split],key=lambda i:int(i['id']))
        for pos,item in enumerate(selected):
            donor=selected[(pos+1)%len(selected)]
            left=set(re.findall(r'\w+',item['question'].lower())); right=set(re.findall(r'\w+',donor['question'].lower()))
            result[item['id']]={'none':'','reference':item['evidence'],'mismatched':donor['evidence'],
                'donor_id':donor['id'],'same_normalized_claim':' '.join(item['question'].lower().split())==' '.join(donor['question'].lower().split()),
                'claim_token_jaccard':len(left&right)/len(left|right), 'donor_evidence_sha256':sha(donor['evidence'].encode())}
    assert all(not m['same_normalized_claim'] for m in result.values())
    return result

def decisions(y0, labels):
    b=labels['blind0']; valid=lambda seq:all(x in ('TRUE','FALSE') for x in seq)
    unanimous=lambda seq:seq[0] if valid(seq) and len(set(seq))==1 else y0
    repeat=[labels[k] for k in ('blind0','blind1','blind2')]
    answer={'keep':y0,'blind':b,'label_gate':unanimous([b,labels['peer_true'],labels['peer_false']]),
        'repeat_unanimity':unanimous(repeat),'repeat_majority':Counter(repeat).most_common(1)[0][0] if valid(repeat) else y0,
        'single_label_gate':unanimous([b,labels['peer_true']])}
    answer.update({k:labels[k] for k in ('peer_true','peer_false','sway_true','sway_false')}); return answer

def cell_dir(out, model, item): return out/'cells'/sha((model+':'+item['id']).encode())[:20]
def read_cells(out,model,item):
    d=cell_dir(out,model,item)
    return {p.stem:json.loads(p.read_text(encoding='utf-8')) for p in d.glob('*.json')}

def measure(rows, policy):
    c=Counter(n=0,initial_correct=0,initial_wrong=0,initial_invalid=0,correct=0,invalid=0,updates=0,harm=0,c_to_w=0,c_to_invalid=0,recovery=0,harmful_updates=0)
    for r in rows:
        y0,gold,y=r['initial'],r['gold'],r['decisions'][policy]
        c['n']+=1;c['correct']+=int(y==gold);c['invalid']+=int(y is None);c['updates']+=int(y!=y0)
        c['initial_correct']+=int(y0==gold);c['initial_wrong']+=int(y0 is not None and y0!=gold);c['initial_invalid']+=int(y0 is None)
        c['harm']+=int(y0==gold and y!=gold);c['c_to_w']+=int(y0==gold and y is not None and y!=gold);c['c_to_invalid']+=int(y0==gold and y is None)
        c['recovery']+=int(y0 is not None and y0!=gold and y==gold);c['harmful_updates']+=int(y!=y0 and y!=gold)
    for name,num,den in [('accuracy','correct','n'),('coverage','updates','n'),('harm_rate','harm','initial_correct'),('recovery_rate','recovery','initial_wrong'),('harmful_update_risk','harmful_updates','updates')]: c[name]=c[num]/c[den] if c[den] else None
    return dict(c)

def bootstrap_difference(rows, comparator, target):
    # A question is the resampling unit. All three condition cells stay together.
    groups={}
    for row in rows: groups.setdefault(row['id'],[]).append(row)
    ids=sorted(groups); rng=random.Random(70072)
    def difference(sample):
        a=measure(sample,'label_gate')[target]; b=measure(sample,comparator)[target]
        return None if a is None or b is None else a-b
    observed=difference(rows); boot=[]
    if not ids: return {'difference':None,'ci95':None,'question_n':0}
    for _ in range(2000):
        val=difference([r for i in rng.choices(ids,k=len(ids)) for r in groups[i]])
        if val is not None:boot.append(val)
    boot.sort()
    return {'difference':observed,'ci95':[boot[int(.025*len(boot))],boot[min(len(boot)-1,int(.975*len(boot)))]] if boot else None,'question_n':len(ids)}

def summarize(items,out,model,split,intervals=False,calibration=None):
    selected=[i for i in items if i['release_split']==split]; rows=[]; validity=Counter(); initial_counts=Counter(); complete_questions=0
    for item in selected:
        cells=read_cells(out,model,item)
        if 'initial' not in cells:continue
        y0=cells['initial']['score']['answer'];gold=item['gold']
        initial_counts['valid']+=int(y0 is not None);initial_counts['correct']+=int(y0==gold);initial_counts['wrong']+=int(y0 is not None and y0!=gold)
        if set(cells)-EXPECTED_CELLS: raise ValueError('Unexpected cell keys')
        complete_questions+=int(set(cells)==EXPECTED_CELLS)
        for c in cells.values():validity['responses']+=1;validity['valid']+=int(c['score']['answer'] is not None)
        for condition in CONDITIONS:
            if not all(condition+'__'+k in cells for k in CHECKS):continue
            labels={k:cells[condition+'__'+k]['score']['answer'] for k in CHECKS}
            choice=decisions(y0,labels)
            wrong='false' if gold=='TRUE' else 'true'
            choice.update(wrong_peer=labels['peer_'+wrong],wrong_sway=labels['sway_'+wrong])
            rows.append({'id':item['id'],'condition':condition,'initial':y0,'gold':gold,'labels':labels,'decisions':choice})
    phase_complete=complete_questions==len(selected)
    gate=phase_complete and initial_counts['valid']>=61 and initial_counts['correct']>=8 and initial_counts['wrong']>=8 and validity['valid']/max(validity['responses'],1)>=.95
    result={'model':model,'split':split,'planned_questions':len(selected),'complete_questions':complete_questions,'initial':dict(initial_counts),'validity':dict(validity),
        'technical_gate_passed':gate if split=='cal' else None,'metrics':{},'cross_tab':{},'thinning':{},'publication_claim':False,'resource_use':{}}
    for condition in CONDITIONS:
        subset=[r for r in rows if r['condition']==condition]
        result['metrics'][condition]={p:measure(subset,p) for p in POLICIES}
        cross={}
        for r in subset:
            ls=r['labels'];b=ls['blind0']
            if b is None or r['initial'] is None or b==r['initial']:continue
            label_invalid=any(ls[k] is None for k in ('blind0','peer_true','peer_false'))
            repeat_invalid=any(ls[k] is None for k in ('blind0','blind1','blind2'))
            key=f"label_unstable={len({ls[k] for k in ('blind0','peer_true','peer_false')})!=1};repeat_unstable={len({ls[k] for k in ('blind0','blind1','blind2')})!=1};invalid={label_invalid or repeat_invalid}"
            c=cross.setdefault(key,{'n':0,'candidate_errors':0});c['n']+=1;c['candidate_errors']+=int(b!=r['gold'])
        result['cross_tab'][condition]=cross
        changed_n=sum(c['n'] for c in cross.values()); errors=sum(c['candidate_errors'] for c in cross.values())
        for c in cross.values():c['candidate_error_rate']=c['candidate_errors']/c['n']
        result.setdefault('h2_interpretable',{})[condition]=changed_n>=20 and 0<errors<changed_n
        result.setdefault('invalid_veto',{})[condition]={p:sum(any(r['labels'][k] is None for k in names) for r in subset) for p,names in {'label_gate':('blind0','peer_true','peer_false'),'repeat_unanimity':('blind0','blind1','blind2')}.items()}
        result.setdefault('stable_wrong',{})[condition]=sum(all(r['labels'][k] in ('TRUE','FALSE') for k in ('blind0','peer_true','peer_false')) and len({r['labels'][k] for k in ('blind0','peer_true','peer_false')})==1 and r['labels']['blind0']!=r['gold'] for r in subset)
        result.setdefault('stable_wrong_updates',{})[condition]=sum(all(r['labels'][k] in ('TRUE','FALSE') for k in ('blind0','peer_true','peer_false')) and len({r['labels'][k] for k in ('blind0','peer_true','peer_false')})==1 and r['labels']['blind0']!=r['gold'] and r['labels']['blind0']!=r['initial'] for r in subset)
        result.setdefault('disagreement_categories',{})[condition]=dict(Counter('invalid' if any(r['labels'][k] is None for k in ('blind0','peer_true','peer_false')) else 'opposite_peer_labels_disagree' if r['labels']['peer_true']!=r['labels']['peer_false'] else 'peers_agree_but_differ_from_blind' if r['labels']['peer_true']!=r['labels']['blind0'] else 'all_agree' for r in subset))
        for policy,names in {'label_gate':('blind0','peer_true','peer_false'),'repeat_unanimity':('blind0','blind1','blind2'),'repeat_majority':('blind0','blind1','blind2'),'blind':('blind0',)}.items():
            c=Counter()
            for item in selected:
                cells=read_cells(out,model,item)
                for name in names:
                    cell=cells.get(condition+'__'+name)
                    if cell:
                        response=cell['result'];c['calls']+=1;c['input_tokens']+=response.get('input_tokens',0);c['output_tokens']+=response.get('output_tokens',0);c['estimated_cost_usd']+=response.get('accounted_usd_estimate',response.get('cost_usd_estimate',0));c['seconds']+=cell.get('seconds',0)
            result['resource_use'][condition+'/'+policy]=dict(c)
        for comparator in ('repeat_majority','repeat_unanimity'):
            source=calibration['metrics'][condition] if calibration else result['metrics'][condition]
            a=source['label_gate']['coverage'];b=source[comparator]['coverage'];prob=min(1,a/b) if a is not None and b else 1.0
            thinned=[]
            for r in subset:
                rr=dict(r);rr['decisions']=dict(r['decisions']);u=int(sha(f'70072:{model}:{condition}:{r["id"]}:{comparator}'.encode())[:16],16)/2**64
                if u>=prob:rr['decisions'][comparator]=r['initial']
                thinned.append(rr)
            result['thinning'][condition+'/'+comparator]={'probability':prob,'source':'calibration' if calibration else 'same_calibration','achieved':measure(thinned,comparator)}
    if intervals and phase_complete:
        result['paired_comparisons']={}
        for comparator in ('repeat_majority','repeat_unanimity'):
            harm=bootstrap_difference(rows,comparator,'harm_rate')
            recovery=bootstrap_difference([r for r in rows if r['condition']=='reference'],comparator,'recovery_rate')
            valid=harm['difference'] is not None and recovery['difference'] is not None
            descriptive=valid and harm['difference']<=-.05 and recovery['difference']>=-.05
            joint=[r for r in rows if r['initial'] is not None and all(r['labels'][k] is not None for k in ('blind0','blind1','blind2','peer_true','peer_false'))]
            joint_harm=bootstrap_difference(joint,comparator,'harm_rate')
            joint_recovery=bootstrap_difference([r for r in joint if r['condition']=='reference'],comparator,'recovery_rate')
            validity_ok=bool(rows) and len(joint)/len(rows)>=.95
            strict=bool(descriptive and validity_ok and harm['ci95'] and recovery['ci95'] and harm['ci95'][1]<0 and recovery['ci95'][0]>-.05 and joint_harm['ci95'] and joint_recovery['ci95'] and joint_harm['ci95'][1]<0 and joint_recovery['ci95'][0]>-.05)
            result['paired_comparisons'][comparator]={'pooled_harm':harm,'reference_recovery':recovery,'joint_valid_harm':joint_harm,'joint_valid_recovery':joint_recovery,'joint_valid_fraction':len(joint)/len(rows) if rows else None,'observed_screen_pass':descriptive,'strict_investment_pass':strict,
                'harm_by_condition':{c:bootstrap_difference([r for r in rows if r['condition']==c],comparator,'harm_rate') for c in CONDITIONS}}
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--analyze',action='store_true');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    raw=(HERE/'data/fixtures.json').read_bytes();assert sha(raw)==FIXTURE_SHA
    items=json.loads(raw)['items'];assert len(items)==192 and len({i['id'] for i in items})==192
    mapping=evidence_map(items)
    manifest={'fixture_sha256':sha(raw),'prereg_sha256':sha((HERE/'PREREGISTRATION.md').read_bytes()),'runner_sha256':sha(Path(__file__).read_bytes()),'models':MODELS,'conditions':CONDITIONS,'checks':CHECKS,'planned_maximum_requests':8448,'budget_usd':25,'workers':6,'initial_temperature':0,'check_temperature':.3,'python':sys.version}
    freeze(out/'manifest.json',manifest);freeze(out/'evidence_mapping.json',mapping)
    if a.analyze:
        for model in MODELS:
            cal=summarize(items,out,model,'cal',True)
            for split in ('cal','test'):write(out/(model+'__'+split+'.json'),cal if split=='cal' else summarize(items,out,model,split,True,cal))
        return
    if not a.execute:
        for item in items:
            for condition in CONDITIONS:
                for k in CHECKS:
                    msg=check_messages(item['question'],'FINAL: TRUE',mapping[item['id']][condition],k)
                    assert len(msg)==3
                    assert msg==check_messages(public(item)['question'],'FINAL: TRUE',mapping[item['id']][condition],k)
        print(json.dumps({'state':'DRY_RUN_OK','questions':len(items),'maximum_requests':8448,'fixture_sha256':sha(raw),'model_calls':0}));return
    assert os.environ.get('PRAXIS_PREREG_SHA256')==manifest['prereg_sha256']
    sys.path.insert(0,str(HERE.parents[2]))
    from filelock import FileLock
    from final_praxis.shared_20260912.bedrock_adapter import BedrockAdapter,BudgetLedger
    with FileLock(str(out/'run.lock'),timeout=0):
        ledger=BudgetLedger(out/'budget.json',limit_usd=25)
        def run_question(model,item):
            # Only this public object is passed to generation. Gold is used in analysis after saving.
            item=public(item);d=cell_dir(out,model,item)
            adapter=BedrockAdapter(model_id=model,profile=None,receipt_dir=out/'receipts',ledger=ledger,max_attempts=2,allowed_temperatures=(0,0.3))
            def obtain(name,messages,limit,temp):
                request={'manifest':manifest,'model':model,'id':item['id'],'cell':name,'messages':messages,'max_tokens':limit,'temperature':temp}
                digest=sha(encode(request));path=d/(name+'.json')
                if path.exists():
                    cell=json.loads(path.read_text(encoding='utf-8'));assert cell['request_sha256']==digest;return cell
                started=time.monotonic();response=adapter.generate(messages,max_new_tokens=limit,temperature=temp,request_id='fp007s2-'+digest[:32])
                cell={'model':model,'id':item['id'],'split':item['release_split'],'cell':name,'request_sha256':digest,'messages':messages,'result':response,'score':score(response,limit),'seconds':time.monotonic()-started}
                write(path,cell);return cell
            first=obtain('initial',initial(item['question']),64,0)
            # Frozen hash order reduces systematic arm-order effects without outcome adaptation.
            plan=[(condition,k) for condition in CONDITIONS for k in CHECKS]
            plan.sort(key=lambda v:sha((model+item['id']+str(v)).encode()))
            for condition,k in plan:obtain(condition+'__'+k,check_messages(item['question'],first['result']['text'],mapping[item['id']][condition],k),256,.3)
            return item['id']
        for model in MODELS:
            cal=None
            for split in ('cal','test'):
                if split=='test' and not cal['technical_gate_passed']:
                    write(out/(model+'__test_not_started.json'),{'reason':'calibration_technical_gate_failed','calibration':cal});break
                selected=[i for i in items if i['release_split']==split]
                with ThreadPoolExecutor(max_workers=6) as executor:
                    pending=[executor.submit(run_question,model,item) for item in selected]
                    for future in as_completed(pending):
                        qid=future.result();current=summarize(items,out,model,split,False,cal)
                        write(out/'progress.json',current);print(json.dumps({'model':model,'split':split,'completed_id':qid,'complete_questions':current['complete_questions']}),flush=True)
                result=summarize(items,out,model,split,True,cal);write(out/(model+'__'+split+'.json'),result)
                if split=='cal':cal=result
        write(out/'complete.json',{'state':'COMPLETED','saved_responses':len(list((out/'cells').glob('*/*.json'))),'models':MODELS,'publication_claim':False})

if __name__=='__main__':main()
