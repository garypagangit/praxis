"""Plan a native-label PX-082-style contrast; never fit or change a failed split."""
from __future__ import annotations
import hashlib
import numpy as np


def identities(values, name):
    """Reject absent IDs before NumPy could coerce them to nonempty strings."""
    a = np.asarray(values, dtype=object)
    if a.ndim != 1: raise ValueError(f'{name}: one-dimensional identities required')
    valid_strings = all(isinstance(v,str) and bool(v.strip()) for v in a)
    valid_integers = all(isinstance(v,(int,np.integer)) and not isinstance(v,(bool,np.bool_)) for v in a)
    if not (valid_strings or valid_integers):
        raise ValueError(f'{name}: nonempty strings or non-Boolean integers required, with no mixed types')
    return np.asarray(list(a))


def fingerprints(current):
    x = np.asarray(current, dtype='<f8').copy()
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError('Qualified finite current features required')
    x[x == 0] = 0
    return np.asarray([hashlib.sha256(row.tobytes()).hexdigest() for row in x])


def plan(*, current, labels, class_names, benign_index, row_ids, event_hashes,
         groups, starts, ends, splits, clock_validated, groups_validated,
         benign_cap=20000, stage_cap=5000):
    """splits=0 past fit,1 reserved calibration,2 later evaluation.

    Split boundaries must be supplied by a source-qualified adapter, before
    outcomes. This function refuses fabricated temporal/group metadata and
    reports unsupported classes instead of moving boundaries or dropping labels.
    """
    if any(not isinstance(v,(bool,np.bool_)) or not v for v in [clock_validated,groups_validated]):
        raise ValueError('Source clock and real grouping metadata must be qualified')
    classes = list(class_names)
    if len(classes)<2 or any(not isinstance(v,str) or not v.strip() for v in classes) or len(set(classes)) != len(classes):
        raise ValueError('Unique native class names required')
    if isinstance(benign_index,(bool,np.bool_)) or not isinstance(benign_index, (int,np.integer)) or not 0 <= benign_index < len(classes):
        raise ValueError('Explicit valid benign mapping required')
    y = np.asarray(labels)
    if y.ndim != 1 or not np.issubdtype(y.dtype,np.integer):
        raise ValueError('Integer labels in native class order required')
    if len(y)==0 or np.any(y<0) or np.any(y>=len(classes)):
        raise ValueError('Unknown or empty labels')
    fields = [identities(row_ids,'row_ids'),identities(event_hashes,'event_hashes'),identities(groups,'groups')]
    fields += [np.asarray(a) for a in (starts,ends,splits)]
    if any(a.ndim!=1 or len(a)!=len(y) for a in fields):
        raise ValueError('Row-aligned metadata required')
    ids,keys,g,start,end,split = fields
    if len(np.unique(ids)) != len(ids) or any(not str(v).strip() for v in ids):
        raise ValueError('Unique nonempty row identities required')
    if any(not str(v).strip() for v in g) or any(not str(v).strip() for v in keys):
        raise ValueError('Nonempty source group and event identities required')
    if not np.isfinite(start).all() or not np.isfinite(end).all() or np.any(end<start):
        raise ValueError('Invalid event intervals')
    if not np.issubdtype(split.dtype,np.integer) or not np.isin(split,[0,1,2]).all() or not (split==0).any() or not (split==2).any():
        raise ValueError('Past fitting and later evaluation split roles required')
    fp = fingerprints(current)
    if len(fp) != len(y): raise ValueError('Feature row mismatch')
    if max(end[split==0]) >= min(start[split==2]):
        raise ValueError('Every past fitting event must finish before the later evaluation begins')
    # Capture/group and native-label stratification reproduces PX-082.
    anchor = []
    for group in np.unique(g[split==2]):
        for k in range(len(classes)):
            ix = np.flatnonzero((split==2)&(g==group)&(y==k))
            ix = ix[np.lexsort((ids[ix].astype(str),keys[ix].astype(str)))]
            anchor.extend(ix[:(len(ix)+1)//2])
    anchor = np.sort(np.asarray(anchor,dtype=np.int64))
    in_anchor = np.zeros(len(y),dtype=bool); in_anchor[anchor] = True
    overlaps = np.isin(fp,fp[anchor])
    past = np.flatnonzero((split==0)&~overlaps)
    mixed = np.flatnonzero((split!=1)&~in_anchor&~overlaps)
    pc = np.bincount(y[past],minlength=len(classes))
    mc = np.bincount(y[mixed],minlength=len(classes))
    ac = np.bincount(y[anchor],minlength=len(classes))
    caps = np.full(len(classes),stage_cap,dtype=np.int64); caps[benign_index]=benign_cap
    if np.any(caps<2): raise ValueError('Declared fitting caps must permit at least two examples')
    matched = np.minimum(np.minimum(pc,mc),caps)
    reasons = []
    later_pool_rows = int((split[mixed]==2).sum())
    if later_pool_rows==0:
        reasons.append({'scope':'contrast','reason':'no_later_non_anchor_rows_after_purge'})
    for k,name in enumerate(classes):
        if matched[k]<2: reasons.append({'class':name,'reason':'fewer_than_two_matched_fitting_rows'})
        if ac[k]==0: reasons.append({'class':name,'reason':'no_later_anchor_support'})
    summary = {'eligible_closed_set_contrast':not reasons,'ineligibility_reasons':reasons,
        'class_names':classes,'benign_index':int(benign_index),'rows':len(y),
        'past_pool_before_purge':int((split==0).sum()),'past_pool_after_purge':len(past),
        'later_non_anchor_pool_after_purge':later_pool_rows,
        'mixed_pool_after_purge':len(mixed),'anchor_rows':len(anchor),
        'anchor_counts':ac.tolist(),'matched_fit_counts':matched.tolist(),
        'past_counts':pc.tolist(),'mixed_counts':mc.tolist(),
        'anchor_group_count':len(np.unique(g[anchor])),
        'current_fingerprint_overlap_after_purge':0,
        'interpretation':'Unsupported stages are reported; no split movement, label dropping or chronology repair performed.'}
    return {'summary':summary,'anchor':anchor,'past_pool':past,'mixed_pool':mixed,
            'matched_counts':matched,'fingerprints':fp}
