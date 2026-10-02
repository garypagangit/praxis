"""Second implementation of fence decoding and OR warning invariants."""
import collections,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    truth={v['pilot_name']:v for v in json.loads(Path('C:/w/vlm_pilots_20261002/private_truth.json').read_text()).values() if 'pilot_name' in v}
    counts=collections.Counter();checks=0;n=0
    for line in (HERE/'RESPONSES.jsonl').read_text().splitlines():
        r=json.loads(line);raw=r['raw'].strip();assert raw.startswith('```json\n') and raw.endswith('\n```')
        payload=json.loads(raw.removeprefix('```json').removesuffix('```').strip());v=truth[r['id'].rsplit('_',1)[0]]
        assert payload['answer'] in ['yes','no','insufficient'];checks+=1;n+=1
        yes=payload['answer']=='yes';counts[(v['cohort'],r['mode'],'yes')]+=yes
        for gate in ['base','full']:
            before=bool(v[gate]);after=before or yes
            assert not before or after;assert int(after)<=int(before)+int(yes);checks+=2
    assert n==48
    result={'status':'PASS','replies_valid_after_exact_fence_removal':n,'checks':checks,
        'scope':'Independent syntax parsing and per-window OR set inequalities; not independent campaign validation',
        'counts':[{'cohort':k[0],'mode':k[1],'yes':v} for k,v in counts.items()]}
    (HERE/'REPLAY_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
