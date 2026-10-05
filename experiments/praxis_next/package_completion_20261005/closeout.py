"""Preserve the bounded qualification results only after verified AWS shutdown."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = [Path('C:/w/px116_aws_20261005'), Path('C:/w/px116_aws_20261005_attempt2')]

def main():
    receipts = [json.loads((p/'COMPUTE.json').read_text()) for p in RUNS]
    assert all(r['status'] == 'CLOSED_VERIFIED_STOPPED' for r in receipts)
    assert all(json.loads((p/'NETWORK_RESTORED.json').read_text())['restored'] for p in RUNS)
    out = RUNS[-1]/'collected/outputs'
    assert (out/'WORKER_EXIT.txt').read_text().strip() == '0'
    evidence = HERE/'evidence'
    evidence.mkdir(exist_ok=True)
    names = sorted(p.name for p in out.glob('task_*.json'))
    assert len(names) == 48
    names += ['WORKER_EXIT.txt', 'image_identity.json', 'wheel_hashes.txt']
    for name in names:
        shutil.copyfile(out/name, evidence/name)
    shutil.copyfile(out/'PILOT_RESULTS.json', HERE/'PILOT_RESULTS.json')
    manifests = []
    for p in RUNS:
        archive = p/'result.tar.gz'
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        assert digest == (p/'result.sha256').read_text().strip()
        manifests.append({'run':p.name, 'archive_sha256':digest,
                          'private_archive':str(archive)})
    (HERE/'COMPUTE_SUMMARY.json').write_text(json.dumps({
        'attempts':receipts, 'approximate_compute_usd':sum(r['approximate_compute_usd'] for r in receipts),
        'is_invoice':False, 'scope':'EC2 instance time only; storage/transfer incidental costs not invoiced here',
        'instance_stopped':True, 'original_security_groups_restored':True,
        'worker':'i-07178e293e8df2a60',
    }, indent=2)+'\n')
    (HERE/'EVIDENCE_MANIFEST.json').write_text(json.dumps({
        'archives':manifests,
        'preserved_files':{str(p.relative_to(HERE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(evidence.iterdir())},
        'limitations':'Authored installation forms and author solutions; no fresh model output. '
          'Install/test process evidence recorded; independent installed-distribution inventory '
          'and complete registry-based label adjudication remain required for confirmation.'
    },indent=2)+'\n')
    registry = HERE.parent/'REGISTRY.json'
    data = json.loads(registry.read_text())
    matches = [r for value in data.values() if isinstance(value,list) for r in value
               if isinstance(r,dict) and r.get('id')=='PX-116']
    assert len(matches)==1
    matches[0].update({
        'status':'QUALIFICATION_COMPLETE_CANDIDATE_NOT_READY_FOR_CONFIRMATION',
        'finding':'AWS: 12 author tasks x 4 install forms; 10 reference-qualified, 40/48 actual passes. '
          'Registry-only, PX-050 and PX-067 each preserve 30/40 qualified cases (75%); '
          'requirements-file form loses all 10. PX-067 admits one unresolvable-version control. '
          'Historical parser affected responses 147/4500 -> 16/4500 with 3086 candidates unchanged. '
          'No PackMonitor/AgentSpec efficacy run or novelty/superiority claim. Full confirmation stopped at readiness gate.',
        'results':'package_completion_20261005/FINDINGS.txt'
    })
    registry.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'status':'evidence preserved; AWS stopped',
                      'approximate_compute_usd':sum(r['approximate_compute_usd'] for r in receipts)}))

if __name__=='__main__':
    main()
