"""Independently reconstruct counts, group errors and calibration thresholds."""
import argparse,collections,json,math
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
r=json.loads((a.evidence/'RESULTS.json').read_text());checks=0
for model in r['results']:
    pred=json.loads((a.evidence/(model['model']+'_predictions.json')).read_text());q=model['threshold']
    for split in ['calibration','test','kypo','rouxii']:
        counts=collections.Counter();groups=collections.defaultdict(list)
        for row in pred[split]:
            v=int(row['score']>=q);y=row['label'];counts['tp' if y and v else 'fn' if y else 'fp' if v else 'tn']+=1
            if not y:groups[row['group']].append(v)
        for key in ['tp','fp','tn','fn']:assert counts[key]==model[split][key];checks+=1
        if groups:
            rate=sum(sum(v)/len(v) for v in groups.values())/len(groups)
            assert abs(rate-model[split]['human_group_mean_fpr'])<1e-12;checks+=1
            if split=='calibration':assert rate<=.05;checks+=1
    human=[x for x in pred['calibration'] if x['label']==0]
    candidates=sorted(set([min(x['score'] for x in pred['calibration'])-1]+[x['score'] for x in human]+[math.nextafter(x['score'],math.inf) for x in human]+[max(x['score'] for x in pred['calibration'])+1]))
    def fpr(threshold):
        d=collections.defaultdict(list)
        for x in human:d[x['group']].append(x['score']>=threshold)
        return sum(sum(v)/len(v) for v in d.values())/len(d)
    assert next(v for v in candidates if fpr(v)<=.05)==q;checks+=1
stress=json.loads((a.evidence/'stress_predictions.json').read_text())
old=json.loads((a.evidence/'RESULTS.json').read_text())
# The threshold is recovered from the original frozen-model reproduction evidence.
threshold=.7166681886449789
for column,key in [('original','frozen_masked_original'),('equalized','frozen_masked_equalized')]:
    counts=collections.Counter()
    for row in stress:
        y=row['label'];v=row[column]>=threshold
        counts['tp' if y and v else 'fn' if y else 'fp' if v else 'tn']+=1
    for name in ['tp','fp','tn','fn']:assert counts[name]==old[key][name];checks+=1
flip=sum((x['original']>=threshold)!=(x['equalized']>=threshold) for x in stress)/len(stress)
assert abs(flip-old['stress_flip_rate'])<1e-12;checks+=1
print(json.dumps({'status':'PASS','checks':checks}))
