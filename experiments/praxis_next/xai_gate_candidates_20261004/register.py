"""Register development proposals without overwriting prior experimental findings."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root.parent / 'REGISTRY.json'
registry = json.loads(path.read_text(encoding='utf-8'))
entries = [
    ('PX-108', 'Testing evidence-validity gates for exfiltration triage', 'FIDELITY_CANDIDATE.txt'),
    ('PX-109', 'Testing explanation-based review gates under valid exfiltration traffic changes', 'ROBUSTNESS_CANDIDATE.txt'),
]
for number, title, detail in entries:
    entry = {'id': number, 'title': title, 'directory': root.name,
             'status': 'PROPOSED_SOURCE_QUALIFICATION_INCOMPLETE',
             'protocol': root.name + '/EXPERIMENT_PLAN.txt',
             'candidate_review': root.name + '/' + detail,
             'results': root.name + '/FINDINGS.txt',
             'novelty': 'BROAD_IDEA_HAS_DIRECT_PRIOR_ART_NARROW_INCREMENTAL_BENEFIT_UNPROVEN',
             'budget': 'Shared $50 feasibility ceiling for PX-108/109 within existing $1,000 total authorization',
             'finding': 'Literature review and benign-source qualification completed; no fitted efficacy result. '
                        'Attack downloads, independent execution labels and recovery headroom still required.'}
    existing = next((x for x in registry['experiments'] if x['id'] == number), None)
    if existing is not None:
        if existing.get('directory') != root.name:
            raise ValueError('Experiment number already belongs to another directory')
        existing.update(entry)
    else:
        registry['experiments'].append(entry)
px107 = next(x for x in registry['experiments'] if x['id'] == 'PX-107')
px107['fresh_source_qualification'] = root.name + '/CIC_INVENTORY.json'
path.write_text(json.dumps(registry, indent=2) + '\n', encoding='utf-8')
print('Registered PX-108 and PX-109; retained PX-107 outcome.')
