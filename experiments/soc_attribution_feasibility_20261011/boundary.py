"""Defender-view projection for a serial managed session. No command execution.

Input is a recorder export, not a claim that an arbitrary source has equivalent
telemetry. Origin/provenance live outside the model view. Completeness is a gate.
"""
import math

VIEWS = ('commands', 'results', 'timing')
ORIGINS = {'H', 'S', 'A', 'M', 'U'}

def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0

def project(session, view, cutoff_ms, limit=5):
    if view not in VIEWS or not number(cutoff_ms):
        raise ValueError('unknown view or invalid cutoff')
    if type(limit) is not int or limit < 1:
        raise ValueError('positive integer limit required')
    if session.get('boundary') != 'managed_serial_session_v1':
        raise ValueError('source must be qualified against managed-session contract')
    if not isinstance(session.get('events'), list):
        raise ValueError('events must be a list')
    selected=[]; previous_end=None; previous_start=-1
    for event in session['events']:
        # Ignore every field not explicitly projected, including origin metadata.
        start=event.get('submitted_ms'); end=event.get('completed_ms')
        if not number(start) or start < previous_start:
            raise ValueError('invalid submission order/clock')
        previous_start=start
        if start > cutoff_ms or len(selected) == limit:
            break
        if previous_end is not None and start < previous_end:
            raise ValueError('parallel events require a separate observation contract')
        if not isinstance(event.get('command'),str):
            raise ValueError('command must be text')
        if end is not None and (not number(end) or end < start):
            raise ValueError('invalid completion clock')
        completed=end is not None and end <= cutoff_ms
        row={'command':event['command']}
        if view in ('results','timing'):
            # Completion-gated export: no later output/status or partial buffer.
            if completed:
                for field in ('stdout','stderr'):
                    if event.get(field) is not None and not isinstance(event[field],str):
                        raise ValueError('invalid output')
                if event.get('exit_code') is not None and type(event['exit_code']) is not int:
                    raise ValueError('invalid exit code')
                if type(event.get('truncated')) is not bool:
                    raise ValueError('explicit truncation status required')
            row.update(completed=completed,
                stdout=event.get('stdout') if completed else None,
                stderr=event.get('stderr') if completed else None,
                exit_code=event.get('exit_code') if completed else None,
                truncated=event.get('truncated') if completed else None)
        if view == 'timing':
            row['execution_ms']=end-start if completed else None
            row['gap_after_previous_completion_ms']=start-previous_end if previous_end is not None else None
        selected.append(row)
        if not completed:
            break  # serial session: no next submission can yet be observed
        previous_end=end
    return {'view':view,'events':selected}

def validate_origin(record):
    """No inference from behavior. Offline AI authorship is a separate axis."""
    category=record.get('origin')
    if category not in ORIGINS: return False
    if category=='U': return False
    if not record.get('origin_evidence_ref'): return False
    if record.get('synthetic_fixture',False): return False
    if record.get('runtime_ai') != (category in {'A','M'}): return False
    if record.get('offline_ai_assistance') not in ('yes','no','unknown'): return False
    if category=='H' and record['offline_ai_assistance']!='no': return False
    if category=='S' and record['offline_ai_assistance']!='no': return False
    return True

def design_gate(records):
    """Engineering readiness only. Does not certify truthful labels or efficacy."""
    failures=[]
    valid=[r for r in records if validate_origin(r)]
    if len(valid)!=len(records): failures.append('unqualified_origin_or_fixture_records')
    for origin in sorted(ORIGINS-{'U'}):
        if not any(r.get('origin')==origin for r in valid): failures.append('missing_'+origin)
    if not records: failures.append('no_records')
    revisions={r.get('recorder_revision') for r in records}
    if len(revisions)!=1 or None in revisions: failures.append('nonuniform_or_missing_recorder')
    if any(not r.get('capture_equivalence_verified',False) for r in records):
        failures.append('capture_equivalence_unverified')
    if any(r.get('prior_inspection_status')!='unseen' for r in records):
        failures.append('not_fresh_confirmation_data')
    tasks={o:{r.get('task_template') for r in valid if r['origin']==o and r.get('task_template')} for o in ORIGINS-{'U'}}
    shared=set.intersection(*tasks.values()) if tasks else set()
    if not shared: failures.append('no_four_arm_shared_tasks')
    if any(not r.get('actor_group') or not r.get('environment_group') for r in records):
        failures.append('missing_independence_groups')
    return {'engineering_ready':not failures,'failures':failures,
            'shared_task_templates':sorted(shared),
            'qualified_origins':{o:sum(r['origin']==o for r in valid) for o in sorted(ORIGINS)},
            'statistically_qualified':False,
            'note':'Independent sample size, provenance adjudication and split audits are separate requirements.'}

def split_audit(train, test, holdouts=('actor_group','task_template','environment_group')):
    failures={}
    for field in ('session_id','trace_hash')+tuple(holdouts):
        if any(not r.get(field) for r in train+test):
            failures[field]=['missing_group_or_identity']; continue
        overlap={r[field] for r in train}&{r[field] for r in test}
        if overlap: failures[field]=sorted(overlap)
    if not train or not test: failures['partitions']=['empty_partition']
    return {'pass':not failures,'overlap_or_missing':failures}
