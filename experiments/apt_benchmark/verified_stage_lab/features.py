"""Allowlisted transport and strictly earlier instrumented-event summaries."""
from __future__ import annotations

from collections import defaultdict
import numpy as np

KINDS = ('authentication', 'remote_job', 'file_write', 'request_end')
CONDITIONS = ('clean', 'drop_remote', 'drop_file', 'delay50ms', 'role_permutation')
CURRENT_NAMES = ('log_request_body_bytes', 'log_response_body_bytes', 'status200', 'status401', 'status500',
                 'log_prior_record_count', 'prior_records_observed', 'earlier_wrong_source_exists', 'remote_channel_available', 'file_channel_available')
HISTORY_NAMES = tuple(f'prior_{kind}_{field}' for kind in KINDS for field in ('log_count', 'log_success_count', 'log_bytes'))


def build(flows, telemetry):
    """Truth records are deliberately not accepted by this feature interface."""
    current = sorted([f for f in flows if f['phase'] == 'current'], key=lambda f:f['start_ns'])
    if len({f['episode'] for f in current}) != len(current):
        raise ValueError('Duplicate current flow')
    events = defaultdict(list)
    for e in telemetry:
        if e['kind'] not in KINDS or e['time_ns'] > e['controllerarrival_ns']:
            raise ValueError('Invalid observable event')
        events[e['episode']].append(e)
    hosts = ['worker_0','worker_1','worker_2']  # Predeclared topology, not learned from future traffic.
    if any(f['src'] not in hosts or f['dst'] not in hosts for f in flows):
        raise ValueError('Unknown process endpoint')
    role = {h:i for i,h in enumerate(hosts)}
    n = len(current)
    roles = np.column_stack([np.eye(3)[[role[f['src']] for f in current]], np.eye(3)[[role[f['dst']] for f in current]]])
    donor = np.full(n, -1, dtype=int)
    earlier = defaultdict(list)
    for i,f in enumerate(current):
        for j in reversed(earlier[f['block']]):
            if current[j]['src'] != f['src'] and current[j]['end_ns'] < f['start_ns']:
                donor[i] = j; break
        earlier[f['block']].append(i)
    arrays = {'episode':np.asarray([f['episode'] for f in current]), 'block':np.asarray([f['block'] for f in current]),
              'src':np.asarray([f['src'] for f in current]), 'dst':np.asarray([f['dst'] for f in current]),
              'start_ns':np.asarray([f['start_ns'] for f in current], dtype=np.int64), 'end_ns':np.asarray([f['end_ns'] for f in current], dtype=np.int64),
              'donor':donor, 'roles':roles, 'timing':np.log1p(np.asarray([f['end_ns']-f['start_ns'] for f in current],dtype=float)/1e6)[:,None],
              'current_names':np.asarray(CURRENT_NAMES), 'history_names':np.asarray(HISTORY_NAMES)}
    for condition in CONDITIONS:
        x, history, latest = np.zeros((n,len(CURRENT_NAMES))), np.zeros((n,len(HISTORY_NAMES))), np.full(n,-1,dtype=np.int64)
        for i,f in enumerate(current):
            selected = []
            for e in events[f['episode']]:
                arrival = e['controllerarrival_ns'] + (50_000_000 if condition == 'delay50ms' else 0)
                if e['phase'] != 'prior' or e['time_ns'] >= f['start_ns'] or arrival >= f['start_ns']:
                    continue
                if condition == 'drop_remote' and e['kind'] == 'remote_job': continue
                if condition == 'drop_file' and e['kind'] == 'file_write': continue
                selected.append(e); latest[i] = max(latest[i],arrival)
            for k,kind in enumerate(KINDS):
                ee=[e for e in selected if e['kind']==kind]
                history[i,3*k:3*k+3]=np.log1p([len(ee),sum(bool(e['success']) for e in ee),sum(e['bytes'] for e in ee)])
            x[i]=[np.log1p(f['request_bytes']),np.log1p(f['response_bytes']),float(f['status']==200),float(f['status']==401),float(f['status']==500),
                  np.log1p(len(selected)),float(bool(selected)),float(donor[i]>=0),float(condition!='drop_remote'),float(condition!='drop_file')]
        wrong=np.zeros_like(history)
        at=donor>=0;wrong[at]=history[donor[at]]
        arrays[condition+'__current']=x;arrays[condition+'__history']=history;arrays[condition+'__wrong_history']=wrong
        arrays[condition+'__latest_arrival']=latest
        arrays[condition+'__roles']=np.column_stack([np.roll(roles[:,:3],1,axis=1),np.roll(roles[:,3:],1,axis=1)]) if condition=='role_permutation' else roles.copy()
        if np.any(latest>=arrays['start_ns']):raise ValueError('Future history')
    return arrays


def views(d,condition):
    c,h,w,r=(d[condition+'__'+k] for k in ('current','history','wrong_history','roles'))
    return {'current':c,'current_roles':np.column_stack([c,r]),'current_history':np.column_stack([c,h]),
            'current_roles_history':np.column_stack([c,r,h]),'current_roles_wrong_history':np.column_stack([c,r,w]),
            'history_only':np.column_stack([c[:,5:],h]),'timing_diagnostic':np.column_stack([c,r,h,d['timing']])}
