"""Report bounded pilot evidence without treating enriched samples as population tests."""
import argparse,collections,csv,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/vlm_pilots_20261002')
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def normalize(r):
    """Posthoc syntax repair only: remove one complete Markdown JSON fence."""
    out=dict(r)
    if r.get('status')!='INVALID_JSON_OR_SCHEMA':return out
    raw=r.get('raw','').strip()
    lines=raw.splitlines()
    if len(lines)<3 or lines[0].strip() not in ['```json','```'] or lines[-1].strip()!='```':return out
    try:
        value=json.loads('\n'.join(lines[1:-1]))
        if not isinstance(value,dict) or value.get('answer') not in ['yes','no','insufficient'] or not isinstance(value.get('reason'),str):return out
    except (ValueError,TypeError):return out
    out.update(parsed=value,status='PARSED',normalization='REMOVED_MARKDOWN_FENCE_ONLY')
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outputs',type=Path,required=True);a=ap.parse_args()
    p=a.outputs/'responses.jsonl';responses=[json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []
    truth={v['pilot_name']:v for v in json.loads((PRIVATE/'private_truth.json').read_text()).values() if 'pilot_name' in v}
    byid={r['id']:r for r in responses};assert len(byid)==len(responses)
    rows=[]
    for analysis in ['strict_frozen_parser','posthoc_fence_only_replay']:
      if analysis=='posthoc_fence_only_replay':byid={r['id']:normalize(r) for r in responses}
      for cohort in ['representative','diagnostic']:
        members={k:v for k,v in truth.items() if v['cohort']==cohort}
        for mode in ['image','text']:
            row={'analysis':analysis,'cohort':cohort,'mode':mode,'selected':len(members),'attempted':0,'valid':0,'abstained_or_invalid':0,
                 'exfil_support':sum(v['exfil'] for v in members.values()),'benign_support':sum(v['benign'] for v in members.values()),
                 'vlm_exfil_warned':0,'vlm_benign_warned':0,'added_base_exfil_windows':0,'added_full_exfil_windows':0,
                 'added_base_benign_windows':0,'added_full_benign_windows':0}
            for name,v in members.items():
                r=byid.get(name+'_'+mode)
                if r is None:continue
                row['attempted']+=1
                answer=r.get('parsed',{}).get('answer');valid=r.get('status')=='PARSED'
                row['valid']+=int(valid)
                row['abstained_or_invalid']+=int(not valid or answer=='insufficient')
                yes=valid and answer=='yes'
                row['vlm_exfil_warned']+=int(yes and v['exfil']);row['vlm_benign_warned']+=int(yes and v['benign'])
                for gate in ['base','full']:
                    row[f'added_{gate}_exfil_windows']+=int(yes and v['exfil'] and not v[gate])
                    row[f'added_{gate}_benign_windows']+=int(yes and v['benign'] and not v[gate])
                    assert (v[gate] or yes)>=v[gate]
            rows.append(row)
    save(HERE/'RESULTS.json',{'rows':rows,'status_counts':dict(collections.Counter(r['status'] for r in responses if r['experiment']=='PX-098')),
        'inference_responses':sum(r['experiment']=='PX-098' for r in responses),'scope':'Small exposed-data pilot; enriched diagnostic counts are not population recall or workload; syntax-only replay was added after observing fenced outputs'})
    (HERE/'RESPONSES.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in responses if r['experiment']=='PX-098'))
    stage=[]
    for r in responses:
        if r['experiment']!='PX-099':continue
        table=json.loads((PRIVATE/'inputs'/(r['id'].rsplit('_',1)[0]+'.json')).read_text())
        hostset=set(table['hosts']);bins=len(table['values'][0]);intervals=r.get('parsed',{}).get('intervals',[])
        valid=0
        for item in intervals:
            if not isinstance(item,dict):continue
            start,end=item.get('start_bin'),item.get('end_bin_exclusive')
            valid+=int(isinstance(item.get('host'),str) and item['host'] in hostset and type(start)==int and type(end)==int and 0<=start<end<=bins and item.get('stage') in ['benign','other_attack','movement','exfiltration'])
        stage.append({'id':r['id'],'status':r['status'],'intervals':len(intervals),'valid_host_time_stage_intervals':valid,
            'seconds':r['seconds'],'input_tokens':r.get('input_tokens'),'stage_accuracy':'NOT_SCORED'})
    dest=HERE.parent/'vlm_stages_20261002'
    save(dest/'RESULTS.json',{'outputs':stage,'scope':'Schema and bounds feasibility only; no stage accuracy or transition improvement established'})
    (dest/'RESPONSES.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in responses if r['experiment']=='PX-099'))
    for f in ['runtime.json','WORKER_EXIT.txt']:
        if (a.outputs/f).exists():(HERE/f.upper()).write_bytes((a.outputs/f).read_bytes())
    print(json.dumps({'gate':rows,'stages':stage},indent=2))
if __name__=='__main__':main()
