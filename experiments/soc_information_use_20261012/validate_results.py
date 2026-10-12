"""Consistency checks independent of the raw corpus replay."""
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent/'results'
def load(name):
    return json.loads((ROOT/(name+'.json')).read_bytes())

sessions = load('SESSION_RESULTS')
summary = load('SUMMARY')
correction = load('QUALIFICATION_CORRECTION')
assert len(sessions)==12 and summary['new_model_fits']==0
for s in sessions:
    for field in ('rotations','setup_literal_exclusion_rotations'):
        assert len(s[field])==5
        for r in s[field]:
            assert len(r['transitions'])==4
            hits=sum(t['hit'] for t in r['transitions'])
            support=sum(t['supported'] for t in r['transitions'])
            assert r['hit_fraction']==hits/4
            assert r['opportunity_fraction']==support/4
            assert r['hit_given_opportunity']==(hits/support if support else None)
    assert s['aligned_hit_fraction']==s['rotations'][0]['hit_fraction']
    assert s['rotated_mean_hit_fraction']==mean(r['hit_fraction'] for r in s['rotations'][1:])
bad={(r['benchmark'],r['task']) for r in correction['checked_sessions'] if r['issues']}
assert len(bad)==4
kept=[s for s in sessions if (s['benchmark'],s['task']) not in bad]
assert len(kept)==4
for label,field in [('wrapper_corrected','rotations'),('wrapper_corrected_setup_excluded','setup_literal_exclusion_rotations')]:
    saved=correction['sensitivities'][label]
    assert summary['qualification_correction_and_sensitivities'][label]==saved
    for origin in ('H','A'):
        ss=[s for s in kept if s['origin']==origin]
        assert saved['origin_means'][origin]['sessions']==len(ss)
        assert saved['origin_means'][origin]['aligned_hit_fraction']==mean(s[field][0]['hit_fraction'] for s in ss)
review=load('REVIEW_SELECTION')
assert len(review)==26
assert all('command' not in r and 'response' not in r and 'new_literals' not in r for r in review)
print('PASS: rotations, denominators, corrected cohort, sensitivities and review export')
