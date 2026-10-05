"""Development-only coverage repair: blank/comment-only shell regions have no actions.

This does not repair PX-069 in place, adjudicate package validity, or certify
remaining extracted candidates. Mixed/comment-plus-command regions are unchanged.
"""
import hashlib,json,sys,time,collections,dataclasses
from pathlib import Path
HERE=Path(__file__).resolve().parent;PRIVATE=Path('C:/w/px116_20261005')
sys.path.insert(0,str(PRIVATE/'historical/scripts'))
import px069_independent_adjudicator as a
original=a.bashlex.parse
def comment_only(text):
    return all(not line.strip() or line.lstrip().startswith('#') for line in text.splitlines())
controls=[('# pip install impossible',True),('\n  # note\n',True),('echo "# note"',False),
          ('# note\npip install numpy',False),('# note\n$(echo example)',False)]
assert all(comment_only(s)==expected for s,expected in controls)
def repaired_parse(text,*args,**kwargs):
    return [] if comment_only(text) else original(text,*args,**kwargs)
packet=Path('C:/Users/garyp/OneDrive/Documents/codex/runs/px069/gate-blind-audit/packets.private.jsonl')
rows=[json.loads(x) for x in packet.read_text(encoding='utf-8').splitlines()]
summary={'id':'PX-116','scope':'EXPOSED DEVELOPMENT PARSER COVERAGE ONLY; not independent package labels or efficacy',
 'packet_sha256':hashlib.sha256(packet.read_bytes()).hexdigest(),'packets':len(rows),'focused_controls_passed':len(controls),'arms':{}}
for label,parser in [('unchanged',original),('comment_only_prefilter',repaired_parse)]:
    a.bashlex.parse=parser; failures=[]; affected=set();count=0; start=time.monotonic();fingerprint=hashlib.sha256()
    for row in rows:
        errors=[]
        found=a.extract_commands(row['blind_response_id'],row['response_text'],internal_failure_sink=errors)
        fingerprint.update(json.dumps([dataclasses.asdict(x) for x in found],sort_keys=True).encode())
        count+=len(found)
        if errors: affected.add(row['blind_response_id'])
        failures.extend(errors)
    summary['arms'][label]={'candidate_count':count,'affected_responses':len(affected),'affected_rate':len(affected)/len(rows),
      'failure_regions':len(failures),'exception_classes':dict(collections.Counter(r['exception_class'] for r in failures)),
      'candidate_sha256':fingerprint.hexdigest(),'seconds':time.monotonic()-start}
    (PRIVATE/f'audit_{label}_failures.json').write_text(json.dumps(failures,indent=2))
a.bashlex.parse=original
summary['identical_extracted_candidates']=summary['arms']['unchanged']['candidate_sha256']==summary['arms']['comment_only_prefilter']['candidate_sha256']
(HERE/'AUDIT_REPAIR_RESULTS.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
