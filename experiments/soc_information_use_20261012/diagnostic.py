"""Inert replay of qualified results; no model calls or command execution."""
import collections
import hashlib
import json
from pathlib import Path
import statistics
import sys
import re

HERE = Path(__file__).resolve().parent
QUAL = HERE.parent / 'soc_pair_qualification_20261012'
sys.path.insert(0, str(QUAL))
from pair_rules import entities, normalize_output, resolve_text, uptake
from qualify_pairs import samples, family


def digest(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return json.loads(Path(p).read_bytes())


def save(p, obj):
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8', newline='\n')


WRAPPER = re.compile(r'(?i)(?:<START_TOOL_OUTPUT>|<END_TOOL_OUTPUT>|here is a truncated version|output of your call to .* was too long)')
SETUP_LITERALS = {'create_secret_table.sql', 'db.sql', 'run_task.py', 'run_benchmark.py'}


def score(commands, outputs, exclude=()):
    assert len(commands) == len(outputs) and len(commands) >= 2
    # Sensitivity-only excluded literals enter observed history, removing both
    # their opportunity and hit. The frozen primary uses no exclusions.
    rows = [uptake(outputs[i], commands[:i+1] + [' '.join(sorted(exclude))], commands[i+1], outputs[:i])
            for i in range(len(commands)-1)]
    hit = sum(r['hit'] for r in rows)
    support = sum(r['supported'] for r in rows)
    return {'hit_fraction': hit / len(rows), 'opportunity_fraction': support / len(rows),
            'hit_given_opportunity': hit / support if support else None,
            'used_literals': sum(r['reused_in_next_command'] for r in rows),
            'transitions': rows}


def rotations(commands, outputs, exclude=()):
    return [score(commands, outputs[k:] + outputs[:k], exclude) for k in range(len(outputs))]


def main():
    out = HERE / 'results'
    out.mkdir(exist_ok=True)
    pairs = read(QUAL/'results/PAIR_AUDIT.json')
    sessions = read(QUAL/'results/SESSION_AUDIT.json')
    primary = read(QUAL/'results/MATCHED_FIRST5_SESSIONS.json')
    transitions = read(QUAL/'results/TRANSITION_AUDIT.json')
    selected = [s for s in sessions if s['eligible_relaxed']]
    common = {(s['benchmark'],s['task']) for s in selected if s['origin']=='H'} & {
        (s['benchmark'],s['task']) for s in selected if s['origin']=='A'}
    ids = {s['id'] for s in selected if (s['benchmark'],s['task']) in common}
    by_session = collections.defaultdict(list)
    for p in pairs:
        if p['id'] in ids:
            by_session[p['id']].append(p)
    needed = {(p['id'],p['index']):p for pp in by_session.values() for p in pp}
    loaded = {}
    sources = []

    def bound(item, key='sha256'):
        p = Path(item['local']); b = p.read_bytes()
        assert digest(b)==item[key] and len(b)==item['bytes'], str(p)
        sources.append({'path':str(p),'sha256':digest(b),'bytes':len(b)})
        return p

    def accept(sid, ix, command, response):
        key = sid, ix
        if key not in needed:
            return
        p = needed[key]
        assert digest(command.encode()) == p['command_sha256'], key
        assert response is not None and digest(response.encode()) == p['response_sha256'], key
        normalized, reason = normalize_output(response)
        if p['qualified']:
            assert reason is None, key
        loaded[key] = (command, normalized)

    raw = Path('C:/w/px120_lyptus_20261007')
    replay = read('C:/w/ai_operator_20261007/experiments/praxis_next/aivh_replay_20261007/results/REPLAY_RECORDS.json')
    manifest = {i['source']:i for i in read(raw/'human_manifest.json')}
    for r in replay:
        if r['id'] not in ids:
            continue
        _, ss = samples(bound(manifest[r['source']]))
        assert len(ss)==1
        logs = ss[0]['store']['HumanAgentState:logs']
        for p in by_session[r['id']]:
            c = r['commands'][p['index']]
            data = logs[c['log'][:-7]+'.output'].split('\n',1)[1].encode()
            span = p['response_span']
            accept(r['id'],p['index'],c['command'],data[span['start']:span['end']].decode())

    def ai_sample(s, model, benchmark):
        sid = family(model)+':'+benchmark+':'+str(s['id']).removesuffix('-one_day')
        if sid not in ids:
            return
        replies = {m['tool_call_id']:m for m in s['messages'] if m.get('role')=='tool'}
        ix = 0
        for m in s['messages']:
            for t in m.get('tool_calls') or []:
                if (sid,ix) in needed:
                    assert t['function']=='bash'
                    a = s.get('attachments',{})
                    accept(sid,ix,resolve_text(t['arguments']['cmd'],a),
                           resolve_text(replies[t['id']].get('content'),a))
                ix += 1

    for item in read(raw/'ai_manifest.json'):
        header, ss = samples(bound(item))
        for s in ss:
            ai_sample(s,header['eval']['model'],'intercode-ctf')
    for item in read('C:/w/px122_lyptus_20261007/MEMBER_MANIFEST.json'):
        sid = family(item['model'])+':'+item['benchmark']+':'+str(item['task_id']).removesuffix('-one_day')
        if sid in ids:
            ai_sample(read(bound(item,'member_sha256')),item['model'],item['benchmark'])
    assert set(loaded)==set(needed), set(needed)-set(loaded)

    result = []
    correction_rows = []
    for s in primary:
        bb = by_session[s['id']][:5]
        assert len(bb)==5 and all(b['qualified'] for b in bb)
        cc, rr = zip(*(loaded[s['id'],b['index']] for b in bb))
        scores = rotations(list(cc),list(rr))
        issues = [{'index':b['index'],'reason':'missed_truncation_wrapper'} for b,r in zip(bb,rr) if WRAPPER.search(r)]
        correction_rows.append({'id':s['id'],'benchmark':s['benchmark'],'task':s['task'],'origin':s['origin'],'issues':issues})
        assert sum(t['hit'] for t in scores[0]['transitions']) == s['first5_retained_history_hits']
        result.append({**{k:s[k] for k in ('id','origin','task','benchmark','family','group')},
            'rotations':scores,
            'aligned_hit_fraction':scores[0]['hit_fraction'],
            'rotated_mean_hit_fraction':statistics.mean(x['hit_fraction'] for x in scores[1:]),
            'alignment_excess':scores[0]['hit_fraction']-statistics.mean(x['hit_fraction'] for x in scores[1:]),
            'setup_literal_exclusion_rotations':rotations(list(cc),list(rr),SETUP_LITERALS)})
    invalid_tasks = {(r['benchmark'],r['task']) for r in correction_rows if r['issues']}
    corrected = [r for r in result if (r['benchmark'],r['task']) not in invalid_tasks]
    sensitivities = {}
    for label, cohort, field in [('wrapper_corrected',corrected,'rotations'),
                                  ('wrapper_corrected_setup_excluded',corrected,'setup_literal_exclusion_rotations')]:
        origin_means = {}
        for o in ('H','A'):
            ss = [r for r in cohort if r['origin']==o]
            aligned = statistics.mean(r[field][0]['hit_fraction'] for r in ss)
            rotated = statistics.mean(statistics.mean(x['hit_fraction'] for x in r[field][1:]) for r in ss)
            origin_means[o] = {'sessions':len(ss),'aligned_hit_fraction':aligned,
                'rotated_mean_hit_fraction':rotated,'alignment_excess':aligned-rotated}
        sensitivities[label] = {'origin_means':origin_means,'ai_minus_human':{
            k:origin_means['A'][k]-origin_means['H'][k] for k in ('aligned_hit_fraction','alignment_excess')}}
    save(out/'QUALIFICATION_CORRECTION.json',{'checked_sessions':correction_rows,
        'removed_tasks':[list(t) for t in sorted(invalid_tasks)],
        'rule':'Remove incomplete/truncated first-five session; remove unmatched counterpart, no replacement task.',
        'sensitivity_setup_literals':sorted(SETUP_LITERALS),'sensitivities':sensitivities})
    task_results = []
    for task in sorted({(s['benchmark'],s['task']) for s in result}):
        origins = {}
        for origin in ('H','A'):
            ss = [s for s in result if (s['benchmark'],s['task'])==task and s['origin']==origin]
            origins[origin] = {k:statistics.mean(s[k] for s in ss) for k in
                ('aligned_hit_fraction','rotated_mean_hit_fraction','alignment_excess')}
            origins[origin]['opportunity_fraction'] = statistics.mean(s['rotations'][0]['opportunity_fraction'] for s in ss)
        task_results.append({'benchmark':task[0],'task':task[1],'origins':origins,
            'ai_minus_human':{k:origins['A'][k]-origins['H'][k] for k in origins['H']}})
    contrast = {k:{'mean':statistics.mean(t['ai_minus_human'][k] for t in task_results),
                  'per_task':[t['ai_minus_human'][k] for t in task_results],
                  'leave_one_task_out_means':[statistics.mean(t['ai_minus_human'][k] for j,t in enumerate(task_results) if j!=i) for i in range(len(task_results))]}
                for k in task_results[0]['ai_minus_human']}

    strata = collections.defaultdict(list)
    for t in transitions:
        if t['id'] in ids:
            strata[t['origin'],t['benchmark'],t['both_px125_observable'],t['hit']].append(t)
    chosen = {}
    for key, tt in strata.items():
        t = min(tt,key=lambda t:digest((t['id']+':'+str(t['index'])).encode()))
        chosen[t['id'],t['index']] = t
    primary_ids = {s['id'] for s in primary}
    for t in transitions:
        if t['id'] in primary_ids and t['prefix_noncontrol_index']<4 and t['hit']:
            chosen[t['id'],t['index']] = t
    packet = []; public = []
    for key,t in sorted(chosen.items()):
        bb = by_session[t['id']]
        pos = next(i for i,b in enumerate(bb) if b['index']==t['index'])
        cmd, response = loaded[key]
        nextcmd = loaded[t['id'],t['next_index']][0]
        history_commands = [loaded[t['id'],b['index']][0] for b in bb[:pos+1]]
        history_results = [loaded[t['id'],b['index']][1] for b in bb[:pos] if loaded[t['id'],b['index']][1] is not None]
        observed = set().union(*(entities(c) for c in history_commands+history_results))
        new = entities(response)-observed
        used = new & entities(nextcmd)
        measured = uptake(response,history_commands,nextcmd,history_results)
        assert all(t[k]==v for k,v in measured.items()), key
        row = {**t,'command_sha256':needed[key]['command_sha256'],
               'response_sha256':needed[key]['response_sha256'],
               'is_primary_positive':t['id'] in primary_ids and t['prefix_noncontrol_index']<4 and t['hit']}
        public.append(row)
        # Full text remains local; concise context is used for internal inspection.
        packet.append({**row,'command':cmd,'response':response,'next_command':nextcmd,
                       'new_literals':sorted(new),'used_literals':sorted(used)})
    save(HERE/'private/REVIEW_PACKET.json',packet)
    save(HERE/'private/PRIMARY_RAW.json',[{'id':s['id'],'pairs':[{'index':b['index'],
        'command':loaded[s['id'],b['index']][0],'result':loaded[s['id'],b['index']][1]}
        for b in by_session[s['id']][:5]]} for s in primary])
    save(out/'REVIEW_SELECTION.json',public)
    save(out/'SESSION_RESULTS.json',result)
    save(out/'TASK_RESULTS.json',task_results)
    save(out/'SOURCE_BINDINGS.json',sources)
    summary = {'source_commit':'1621cc5','sessions':len(result),'tasks':len(task_results),
               'bound_raw_files':len(sources),'rehydrated_pairs':len(loaded),'review_cases':len(packet),
               'review_strata':len(strata),'new_model_fits':0,'task_paired_contrasts':contrast,
               'qualification_correction_and_sensitivities':sensitivities,
               'origin_means':{o:{k:statistics.mean(s[k] for s in result if s['origin']==o)
                   for k in ('aligned_hit_fraction','rotated_mean_hit_fraction','alignment_excess')}
                   for o in ('H','A')}}
    save(out/'SUMMARY.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
