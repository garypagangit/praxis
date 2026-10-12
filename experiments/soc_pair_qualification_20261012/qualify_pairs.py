"""Re-associate PX125 source bytes and audit a distinct comparison. No fits.
Existing human command reconstruction is an explicit inherited dependency.
"""
import argparse, collections, csv, gzip, hashlib, io, json, pathlib, re, zipfile
from pair_rules import resolve_text,terminal_span,normalize_output,uptake,classify_control,joined_transition

HERE=pathlib.Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def samples(path):
    data=path.read_bytes()
    z=zipfile.ZipFile(io.BytesIO(gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data))
    header=json.loads(z.read('header.json'))
    return header,[json.loads(z.read(n)) for n in z.namelist() if n.startswith('samples/') and n.endswith('.json')]
def family(model):return 'anthropic' if 'claude' in model else 'google' if 'gemini' in model else 'openai'

def run(raw, members, prior):
    out=HERE/'results';out.mkdir(exist_ok=True)
    provenance=[];checks=collections.Counter();errors=[]
    def read_json(path):
        b=path.read_bytes();provenance.append({'path':str(path),'sha256':sha(b),'bytes':len(b)})
        return json.loads(b)
    def bind(item,hash_key='sha256'):
        p=pathlib.Path(item['local']);b=p.read_bytes()
        ok=sha(b)==item[hash_key] and len(b)==item['bytes']
        provenance.append({'path':str(p),'sha256':sha(b),'bytes':len(b),'source_hash_match':ok,
                           'whole_source_archive_verified':item.get('archive_sha256_verified',True)})
        checks['source_hash_and_size_checks']+=1
        if not ok:raise ValueError('Source integrity failure '+str(p))
        return p
    human_manifest=read_json(raw/'human_manifest.json');ai_manifest=read_json(raw/'ai_manifest.json')
    member_manifest=read_json(members/'MEMBER_MANIFEST.json')
    replay=read_json(prior/'aivh_replay_20261007/results/REPLAY_RECORDS.json')
    old=read_json(prior/'aivh_response_20261007/results/RECORDS.json')
    oldmap=collections.defaultdict(list)
    for r in old:oldmap[r['id']].append(r)
    hm={}
    for item in human_manifest:
        p=bind(item);_,ss=samples(p)
        if len(ss)==1:hm[item['source']]=ss[0]
    ai=[]
    for item in ai_manifest:
        p=bind(item);header,ss=samples(p)
        ai.extend((s,header['eval']['model'],'intercode-ctf') for s in ss)
    for item in member_manifest:
        p=bind(item,'member_sha256');ai.append((json.loads(p.read_bytes()),item['model'],item['benchmark']))
    sessions=[];blocks=[];transitions=[];mismatches=[];event_disagreements=[]
    def finalize(meta,bb):
        # Same first-20 non-control horizon as PX125, but retain compound results.
        bb=[b for b in bb if not b['control']][:20]
        previous=oldmap[meta['id']]
        if len(previous)!=1:checks['ambiguous_prior_row_ids']+=1
        previous=previous[0] if len(previous)==1 else None
        oldblocks={b['index']:b for b in previous['blocks']} if previous else {}
        for b in bb:
            ob=oldblocks.get(b['index'])
            if ob is not None:
                same=ob['command']==b['_command'] and ob['response_sha256']==b['response_sha256']
                checks['prior_pair_hash_comparisons']+=1
                if not same:mismatches.append({'id':meta['id'],'index':b['index'],'command_equal':ob['command']==b['_command'],'response_hash_equal':ob['response_sha256']==b['response_sha256']})
                b['px125_syntax']=ob['syntax_status'];b['px125_observable']=ob['observable']
            else:b['px125_syntax']='not_in_prior_horizon';b['px125_observable']=False
            b['qualified']=not b['issues']
        current=[];history=[];prior_results=[];history_complete=True
        for i,b in enumerate(bb):
            history.append(b['_command'])
            if i+1==len(bb) or not joined_transition(b,bb[i+1]):
                if b['_normalized'] is not None:prior_results.append(b['_normalized'])
                history_complete=history_complete and b['qualified']
                continue
            nextb=bb[i+1]
            # Non-shell AI actions block adjacency through the original call index.
            event={**meta,'index':b['index'],'next_index':nextb['index'],
              'same_task':True,'prefix_noncontrol_index':i,
              'both_px125_observable':b['px125_observable'] and nextb['px125_observable'],
              **uptake(b['_normalized'],history,nextb['_command'],prior_results),
              'retained_history_complete':history_complete,
              'response_words':len(b['_normalized'].split()),
              'response_length':len(b['_normalized']),
              '_response':b['_normalized'],'_history':list(history),'_next':nextb['_command']}
            current.append(event)
            prior_results.append(b['_normalized']);history_complete=history_complete and b['qualified']
        complete_prefix=[]
        for b in bb:
            if not b['qualified']:break
            if complete_prefix and not joined_transition(complete_prefix[-1],b):break
            complete_prefix.append(b)
        sid={**meta,'blocks':len(bb),'associated':sum(b['response_sha256'] is not None for b in bb),
          'qualified_pairs':sum(b['qualified'] for b in bb),'qualified_transitions':len(current),
          'supported_transitions':sum(t['supported'] for t in current),'uptake_hits':sum(t['hit'] for t in current),
          'previous_eligible':previous['eligible'] if previous else None,
          'contiguous_qualified_prefix':len(complete_prefix),
          'first5_pairs_qualified':len(complete_prefix)>=5,
          'first3_pairs_qualified':len(complete_prefix)>=3,
          'first5_retained_history_supported':sum(t['supported'] and t['prefix_noncontrol_index']<4 and t['retained_history_complete'] for t in current),
          'first5_retained_history_hits':sum(t['hit'] and t['prefix_noncontrol_index']<4 and t['retained_history_complete'] for t in current),
          'eligible_relaxed':sum(b['qualified'] for b in bb)>=3 and len(current)>=2,
          'issues':dict(collections.Counter(issue for b in bb for issue in b['issues']))}
        sessions.append(sid);transitions.extend(current)
        for b in bb:blocks.append({**meta,**{k:v for k,v in b.items() if not k.startswith('_')}})
    for r in replay:
        if r['benchmark'] not in ('intercode-ctf','cybench','cvebench'):continue
        s=hm[r['source']];logs=s['store'].get('HumanAgentState:logs',{});bb=[]
        for i,c in enumerate(r['commands']):
            following=next((n for n in r['commands'][i+1:] if n['log']==c['log']),None)
            data=logs[c['log'][:-7]+'.output'].split('\n',1)[1].encode()
            response,span=terminal_span(data,c,following)
            normalized,reason=normalize_output(response);issues=[]
            if span['reason']:issues.append(span['reason'])
            if c['unknown_terminal_events_so_far']>0:issues.append('prior_unknown_terminal_event')
            if reason:issues.append(reason)
            bb.append({'origin':'H','index':i,'log':c['log'],
              'command_sha256':sha(c['command'].encode()),'response_sha256':sha(response.encode()) if response is not None else None,
              'response_chars':len(response) if response is not None else None,'issues':issues,
              'response_span':span,'control':classify_control(c['command']),
              'verified_exit_code':None,'equivalent_timing_qualified':False,
              '_command':c['command'],'_normalized':normalized})
        finalize({'id':r['id'],'task':r['task'],'benchmark':r['benchmark'],'family':'human','group':r['expert'],'origin':'H'},bb)
    for s,model,benchmark in ai:
        replies=collections.defaultdict(list);calls=collections.Counter();events=collections.defaultdict(list)
        for mi,m in enumerate(s['messages']):
            if m.get('role')=='tool':replies[m.get('tool_call_id')].append((mi,m))
            for t in m.get('tool_calls') or []:calls[t.get('id')]+=1
        for e in s.get('events',[]):
            if e.get('event')=='tool':events[e.get('id')].append(e)
        bb=[];action=0;attachments=s.get('attachments',{})
        for mi,m in enumerate(s['messages']):
            for t in m.get('tool_calls') or []:
                ix=action;action+=1
                if t.get('function')!='bash':continue
                command=resolve_text(t.get('arguments',{}).get('cmd'),attachments)
                rr=replies[t['id']];issues=[]
                valid=len(rr)==1 and rr[0][0]>mi and calls[t['id']]==1
                if not valid:issues.append('nonunique_or_misordered_call_reply')
                response=resolve_text(rr[0][1].get('content'),attachments) if valid else None
                if command is None:issues.append('missing_command')
                normalized,reason=normalize_output(response)
                if reason:issues.append(reason)
                # Do not mistake framework tool success/error for shell exit status.
                ee=events[t['id']]
                if len(ee)==1:
                    er=resolve_text(ee[0].get('result'),attachments)
                    checks['ai_event_result_comparisons']+=1
                    if er!=response:
                        checks['ai_event_result_differences']+=1
                        event_disagreements.append({'model':model,'benchmark':benchmark,'task':str(s['id']),'index':ix,
                          'event_result_type':type(ee[0].get('result')).__name__,
                          'event_result_sha256':sha(er.encode()) if er is not None else None,
                          'message_result_sha256':sha(response.encode()) if response is not None else None})
                        issues.append('event_message_result_disagreement')
                bb.append({'origin':'A','index':ix,'call_message':mi,'reply_message':rr[0][0] if valid else None,
                  'command_sha256':sha((command or '').encode()),'response_sha256':sha(response.encode()) if response is not None else None,
                  'response_chars':len(response) if response is not None else None,'issues':issues,
                  'reply_count':len(rr),'call_count':calls[t['id']],'control':classify_control(command or ''),
                  'verified_exit_code':None,'equivalent_timing_qualified':False,
                  '_command':command or '', '_normalized':normalized})
        fam=family(model);task=str(s['id']).removesuffix('-one_day');rid=fam+':'+benchmark+':'+task
        finalize({'id':rid,'task':task,'benchmark':benchmark,'family':fam,'group':rid,'origin':'A'},bb)
    # Readiness of a task-matched placebo; no origin classifier or performance score.
    for t in transitions:
        donors=[d for d in transitions if d['id']!=t['id'] and d['task']==t['task'] and d['benchmark']==t['benchmark'] and d['origin']==t['origin']]
        t['same_task_same_origin_other_session_donors']=len(donors)
        candidates=[d for d in donors if abs(d['response_length']-t['response_length'])<=max(16,t['response_length']*.25)]
        t['length_matched_donors']=len(candidates)
    matched={}
    for definition in ('eligible_relaxed','previous_eligible','first3_pairs_qualified','first5_pairs_qualified'):
        selected=[s for s in sessions if s[definition]]
        tasks={(s['benchmark'],s['task']) for s in selected if s['origin']=='H'}&{(s['benchmark'],s['task']) for s in selected if s['origin']=='A'}
        ss=[s for s in selected if (s['benchmark'],s['task']) in tasks]
        matched[definition]={'tasks':len(tasks),'human':sum(s['origin']=='H' for s in ss),'ai':sum(s['origin']=='A' for s in ss),'human_groups':len({s['group'] for s in ss if s['origin']=='H'})}
        if definition=='first5_pairs_qualified':
            matched[definition]['sessions_with_supported_first5']={o:sum(s['first5_retained_history_supported']>0 for s in ss if s['origin']==o) for o in ('H','A')}
            matched[definition]['sessions_with_hits_first5']={o:sum(s['first5_retained_history_hits']>0 for s in ss if s['origin']==o) for o in ('H','A')}
            ids={s['id'] for s in ss}
            dump(out/'MATCHED_FIRST5_SESSIONS.json',ss)
    cohorts={}
    for origin in ('H','A'):
        ss=[s for s in sessions if s['origin']==origin];bb=[b for b in blocks if b['origin']==origin];tt=[t for t in transitions if t['origin']==origin]
        cohorts[origin]={'sessions':len(ss),'blocks':len(bb),'associated_results':sum(b['response_sha256'] is not None for b in bb),
          'qualified_pairs':sum(b['qualified'] for b in bb),'qualified_transitions':len(tt),
          'transitions_both_px125_observable':sum(t['both_px125_observable'] for t in tt),
          'supported_transitions':sum(t['supported'] for t in tt),'uptake_hit_transitions':sum(t['hit'] for t in tt),
          'sessions_with_supported_transitions':sum(s['supported_transitions']>0 for s in ss),
          'sessions_with_uptake_hits':sum(s['uptake_hits']>0 for s in ss),
          'history_complete_supported_transitions':sum(t['supported'] and t['retained_history_complete'] for t in tt),
          'transitions_with_same_task_same_origin_other_session_donor':sum(t['same_task_same_origin_other_session_donors']>0 for t in tt),
          'transitions_with_length_matched_donor':sum(t['length_matched_donors']>0 for t in tt),
          'issue_counts':dict(collections.Counter(i for b in bb for i in b['issues']))}
    summary={'date':'2026-10-12','checks':dict(checks),'prior_hash_mismatches':mismatches,'event_result_disagreements':event_disagreements,
      'cohorts':cohorts,'matched_coverage':matched,
      'scope':'Existing first-20 non-control submissions in PX125 source populations. Conservative normalized submission-result pairs; compounds remain whole. No new model fits.',
      'cautions':['Human commands inherited from PX122 replay; no independent ground-truth reconstruction accuracy estimate.',
        'Member-only AI downloads have bound member hashes but not reverified entire remote archives.',
        'Prompt/terminal controls and tool wrappers excluded conservatively, not fully rendered.',
        'No comparable verified exit-status or timing channel qualified.',
        'Literal reuse is not proof of semantic reliance or AI origin; all data are exposed development.'],
      'new_model_fits':0,'new_participants':0,'errors':errors}
    dump(out/'QUALIFICATION.json',summary);dump(out/'SOURCES.json',provenance)
    dump(out/'PAIR_AUDIT.json',blocks);dump(out/'SESSION_AUDIT.json',sessions)
    dump(out/'TRANSITION_AUDIT.json',[{k:v for k,v in t.items() if not k.startswith('_')} for t in transitions])
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--raw',type=pathlib.Path,default=pathlib.Path('C:/w/px120_lyptus_20261007'))
    ap.add_argument('--members',type=pathlib.Path,default=pathlib.Path('C:/w/px122_lyptus_20261007'))
    ap.add_argument('--prior',type=pathlib.Path,default=pathlib.Path('C:/w/ai_operator_20261007/experiments/praxis_next'))
    a=ap.parse_args();run(a.raw,a.members,a.prior)
