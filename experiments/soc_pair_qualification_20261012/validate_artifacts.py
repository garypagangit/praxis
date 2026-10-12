"""Check published aggregate claims against per-record audit artifacts."""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'results'


def load(name):
    return json.loads((ROOT / (name + '.json')).read_bytes())


def main():
    q = load('QUALIFICATION')
    pairs, sessions, transitions = [load(n) for n in
        ('PAIR_AUDIT', 'SESSION_AUDIT', 'TRANSITION_AUDIT')]
    assert q['new_model_fits'] == 0
    assert not q['errors'] and not q['prior_hash_mismatches']
    assert len(pairs) == q['checks']['prior_pair_hash_comparisons']
    assert all('event_message_result_disagreement' not in p['issues'] for p in pairs)
    assert all(p['verified_exit_code'] is None and not p['equivalent_timing_qualified'] for p in pairs)
    assert all(not any(k.startswith('_') for k in p) for p in pairs + transitions)
    by_key = {(p['id'], p['index']): p for p in pairs}
    assert len(by_key) == len(pairs)
    for t in transitions:
        a, b = by_key[t['id'], t['index']], by_key[t['id'], t['next_index']]
        assert a['qualified'] and b['qualified']
        assert b['index'] == a['index'] + 1
        assert (a['log'] == b['log']) if a['origin'] == 'H' else (a['reply_message'] < b['call_message'])
        assert t['reused_in_next_command'] <= t['new_to_retained_history'] <= t['candidate_entities']
        assert t['hit'] == bool(t['reused_in_next_command'])
        assert t['supported'] == bool(t['new_to_retained_history'])
    for origin in ('H', 'A'):
        pp = [p for p in pairs if p['origin'] == origin]
        ss = [s for s in sessions if s['origin'] == origin]
        tt = [t for t in transitions if t['origin'] == origin]
        c = q['cohorts'][origin]
        assert len(pp) == c['blocks'] and len(ss) == c['sessions']
        assert sum(p['qualified'] for p in pp) == c['qualified_pairs']
        assert len(tt) == c['qualified_transitions']
        assert sum(t['hit'] for t in tt) == c['uptake_hit_transitions']
        assert sum(t['supported'] for t in tt) == c['supported_transitions']
        assert dict(collections.Counter(i for p in pp for i in p['issues'])) == c['issue_counts']
    for definition, expected in q['matched_coverage'].items():
        eligible = [s for s in sessions if s[definition]]
        tasks = {(s['benchmark'], s['task']) for s in eligible if s['origin'] == 'H'} & {
            (s['benchmark'], s['task']) for s in eligible if s['origin'] == 'A'}
        selected = [s for s in eligible if (s['benchmark'], s['task']) in tasks]
        assert len(tasks) == expected['tasks']
        assert sum(s['origin'] == 'H' for s in selected) == expected['human']
        assert sum(s['origin'] == 'A' for s in selected) == expected['ai']
        assert len({s['group'] for s in selected if s['origin'] == 'H'}) == expected['human_groups']
        if definition == 'first5_pairs_qualified':
            assert selected == load('MATCHED_FIRST5_SESSIONS')
            for origin in ('H', 'A'):
                for field, metric in [('supported', 'supported'), ('hits', 'hits')]:
                    assert sum(s['first5_retained_history_' + field] > 0 for s in selected
                               if s['origin'] == origin) == expected['sessions_with_' + metric + '_first5'][origin]
    print('PASS: aggregate counts, fixed-prefix cohorts, associations and export boundary')


if __name__ == '__main__':
    main()
