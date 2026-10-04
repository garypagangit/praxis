"""Replay all frozen batch decisions from saved scores using plain Python sorting."""
import json,math,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=Path('C:/w/px110_controlled_dns_20261004_attempt2')
def main():
    rows=json.loads((DATA/'cases.json').read_text())
    scores=json.loads((DATA/'batch/scores.json').read_text())
    thresholds=json.loads((DATA/'batch/thresholds.json').read_text())
    report=json.loads((ROOT/'BATCH_RESULTS.json').read_text())
    checks=[]
    for kind in ['ranking','gates']:
        for result in report[kind]:
            split=result['split'];name=result['method'];data=[r for r in rows if r['split']==split]
            eligible=[i for i in range(len(data)) if scores[split]['confidence'][i]<thresholds['anchor']]
            capacity=math.ceil(.05*len(eligible))
            if kind=='ranking':chosen=sorted(eligible,key=lambda i:(-scores[split][name][i],data[i]['id']))[:capacity]
            else:chosen=[i for i in eligible if scores[split][name][i]>=thresholds['referrals'][name]][:capacity]
            hits=sum(data[i]['y'] for i in chosen)
            assert hits==result['added_transfers']
            assert len(chosen)-hits==result['added_benign']
            assert len(chosen)==result['added_reviews']<=capacity
            assert not any(scores[split]['confidence'][i]>=thresholds['anchor'] for i in chosen)
            checks.append({'split':split,'mode':kind,'method':name,'pass':True})
    external=ROOT.parent/'xai_acquisition_20261004/HEADROOM.json'
    source=json.loads(external.read_text())
    assert len(source)==6 and all(r['exfil_rows_recoverable_in_unwarned_cases']==0 for r in source)
    external_status=[{'method':n,'status':'NOT_EVALUABLE_NO_ELIGIBLE_EXFIL_CASES',
                     'source':'AIT recorded scripted laboratory executions; not operational breach telemetry',
                     'independent_episode_proxies':2,'efficacy_result':None} for n in sorted({r['method'] for r in report['ranking'] if r['method'].startswith(tuple('ABCDEF'))})]
    out={'all_checks_pass':True,'decision_cells':len(checks),'checks':checks,
         'external_headroom_sha256':hashlib.sha256(external.read_bytes()).hexdigest(),
         'external_cells':source,'external_stage':external_status,
         'external_validation_passed':False,
         'saved_scores_sha256':hashlib.sha256((DATA/'batch/scores.json').read_bytes()).hexdigest()}
    (ROOT/'BATCH_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'decision_cells':len(checks),'all_checks_pass':True,'external_validation_passed':False}))
if __name__=='__main__':main()
