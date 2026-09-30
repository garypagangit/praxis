"""Publish completed statuses without changing historical experiment protocols."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=root/'REGISTRY.json';d=json.loads(p.read_text())
findings={
'PX-088':('COMPLETE_EXPLORATORY_REPLAY','Selective calibration completed; low review budgets leave unresolved attacks; no human detection credit assumed.'),
'PX-089':('COMPLETE_EXPLORATORY_REPLAY','Chronological recalibration with simulated label delays recovers warnings at very high false-alert cost; no deployment guarantee.'),
'PX-090':('COMPLETE_ADAPTED_EXPERIMENT','Six matched expert-score fits; monotonicity alone did not prevent demotion; explicit union veto retained constituent warnings with more false alerts.'),
'PX-091':('QUALIFICATION_COMPLETE_REPLICATION_BLOCKED','Renewed data qualification complete; no newly qualified independent four-class/two-evidence release. Windows-APT metadata requests remain inaccessible.')}
for e in d['experiments']:
    if e['id'] not in findings:continue
    status,finding=findings[e['id']];e.update(status=status,finding=finding,protocol='closeout_20260930/PROTOCOL.md',results='closeout_20260930/RESULTS.md',qualification='closeout_20260930/QUALIFICATION.md',batch='20260930-closeout')
    (root/e['directory']/'README.md').write_text(f"# {e['id']}: {e['title']}\n\nStatus: {status}.\n\n{finding}\n\n[Results and interpretation](../closeout_20260930/RESULTS.md) | [Frozen protocol](../closeout_20260930/PROTOCOL.md) | [Audit](../closeout_20260930/AUDIT.json) | [Data and literature qualification](../closeout_20260930/QUALIFICATION.md)\n\nNovelty remains unconfirmed. These are exposed-data development studies; no independent efficacy confirmation is claimed.\n",encoding='utf-8')
p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
p=root/'README.md';s=p.read_text(encoding='utf-8');s=s.replace('PX-088--091 remain registered with explicit qualification requirements.','[PX-088--090 closeout results](closeout_20260930/RESULTS.md) are complete (PX-090 uses an explicit expert-score adaptation). PX-091 qualification is complete; exact replication remains data-blocked.');p.write_text(s,encoding='utf-8')
p=root/'warning_control_20260930/README.md';s=p.read_text(encoding='utf-8')
for a,b in [('Registered; requires selective protocol and stage support','Complete exploratory replay; see closeout'),('Registered; requires qualified windows and label timing','Complete simulated-delay replay; see closeout'),('Registered; requires justified feature directions','Complete expert-score adaptation; see closeout'),('Registered; requires new qualified data','Qualification complete; exact replication data-blocked')]:s=s.replace(a,b)
s+='\n## Subsequent closeout\n\n[PX-088--091 results, audit and qualification](../closeout_20260930/README.md). The original frozen protocol and completed PX-085--087 outputs remain preserved.\n';p.write_text(s,encoding='utf-8')
