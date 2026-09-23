"""Test a packaging-only repair after preserving an unchanged-extraction result.

Adds the byte-identical downloaded ZIP at the README's linked location, then
reruns only the extracted package verifier. No original bundle file is edited.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil

from run_clean_room import GUARDED_RUNNER, HERE, PAPER, command, digest, dump


def main(path):
    prior=json.loads(path.read_text(encoding='utf-8'))
    if prior['status']!='FAIL':
        raise ValueError('Expected preserved failure from unchanged extraction')
    missing=prior['independent_relative_link_check']['missing']
    if missing != [{'file':'README.md','target':'apt_evaluation_praxis_evidence.zip','exists':False}]:
        raise ValueError('Repair applies only to the single known missing archive link')
    root=Path(prior['root']).resolve()
    extracted=root/'extracted'
    results=root/'results'
    before={str(p.relative_to(extracted)):digest(p) for p in extracted.rglob('*') if p.is_file()}
    downloaded=root/'public_evidence.zip'
    if digest(downloaded)!=prior['archive_sha256']:
        raise ValueError('Downloaded archive identity changed')
    target=(extracted/PAPER/'apt_evaluation_praxis_evidence.zip').resolve()
    target.relative_to(extracted.resolve())
    if target.exists():
        raise FileExistsError('Repair destination must be new')
    shutil.copyfile(downloaded,target)
    receipt=results/'REPAIRED_PACKAGE_VERIFICATION.json'
    audit=results/'REPAIRED_PACKAGE_FILE_ACCESS.json'
    if receipt.exists() or audit.exists():
        raise FileExistsError('Preserve prior repaired check receipts')
    runtime=prior['runtime']
    roots=[str(extracted),str(results),runtime['prefix'],runtime['base_prefix']]
    child_env=dict(os.environ)
    for name in ('PYTHONPATH','PYTHONHOME'):child_env.pop(name,None)
    run=command([runtime['executable'],'-I','-B','-c',GUARDED_RUNNER,
        str(extracted/PAPER/'verify_package.py'),str(receipt),str(audit),json.dumps(roots)],extracted,90,child_env)
    after={str(p.relative_to(extracted)):digest(p) for p in extracted.rglob('*') if p.is_file()}
    added=sorted(set(after)-set(before))
    changed=[name for name,sha in before.items() if after.get(name)!=sha]
    check=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
    log=json.loads(audit.read_text(encoding='utf-8')) if audit.exists() else None
    result=dict(schema_version=1,utc=datetime.now(timezone.utc).isoformat(),
        wrapper_sha256=digest(__file__),prior_receipt_sha256=digest(path),prior_status=prior['status'],
        repair='Copy byte-identical downloaded ZIP to its README-linked location; no original file edits',
        original_archive_sha256=prior['archive_sha256'],added_archive_sha256=digest(target),
        original_extracted_members_changed=changed,added_members=added,
        original_archive_unchanged=digest(Path(prior['original_archive']))==prior['archive_sha256'],
        verification_run=run,verification_receipt=check,
        open_audit=dict(sha256=digest(audit),events=len(log['open_events']),denied=log['denied']) if log else None,
        public_arithmetic_rerun=False,public_arithmetic_status=prior['verification_runs'][0]['receipt']['status'],
        new_model_fits=0,aws_used=False)
    result['status']='PASS' if (run['returncode']==0 and check and check['status']=='PASS' and not changed
        and added==[str(PAPER/'apt_evaluation_praxis_evidence.zip')] and log is not None and not log['denied']
        and result['original_archive_unchanged'] and digest(target)==prior['archive_sha256']) else 'FAIL'
    outfile=results/'LINK_REPAIR_RECEIPT.json'
    dump(outfile,result)
    for source in (receipt,audit,outfile):
        if source.exists():
            dest=HERE/source.name
            if dest.exists():raise FileExistsError('Do not overwrite '+str(dest))
            shutil.copyfile(source,dest)
    print(json.dumps(dict(status=result['status'],added_members=added,changed=changed,
        verifier_returncode=run['returncode'],stderr=run['stderr'])))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,default=HERE/'CLEAN_ROOM_RECEIPT.json')
    raise SystemExit(main(parser.parse_args().receipt))
