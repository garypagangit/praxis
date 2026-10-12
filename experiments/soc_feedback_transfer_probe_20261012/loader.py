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


def load_data():
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

    return by_session, loaded, sessions, sources
