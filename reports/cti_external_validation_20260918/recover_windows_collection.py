"""Local-only recovery of one verified CTI archive onto a case-insensitive filesystem."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

PRIVATE = Path('C:/w/cti_external_private_20260918')
RENAME = {'outputs/RUNTIME.json': 'outputs/environment_runtime.json'}
MAX_BYTES = 512*1024**2


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def validate_members(members, destination):
    if len(members)>10000 or sum(m.size for m in members)>2*1024**3:
        raise ValueError('Archive expanded-size or file-count limit exceeded')
    original=set(); renamed={}; directories=set(); plan=[]
    for member in members:
        name=member.name.rstrip('/')
        parts=name.split('/')
        if not name or PurePosixPath(name).is_absolute() or parts[0]!='outputs':
            raise ValueError('Unexpected or absolute archive root')
        if '\\' in name or any(part in {'','.','..'} for part in parts):
            raise ValueError('Unsafe archive path')
        for part in parts:
            if any(ord(c)<32 or c in '<>:"|?*' for c in part) or part.rstrip(' .')!=part:
                raise ValueError('Unsafe Windows path segment')
            if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',part,re.I):
                raise ValueError('Reserved Windows path segment')
        if not (member.isdir() or member.isfile()) or member.size<0:
            raise ValueError('Archive links, special files, or invalid sizes are prohibited')
        if name in original: raise ValueError('Duplicate original archive path')
        original.add(name)
        mapped=RENAME.get(name,name)
        normalized=mapped.casefold()
        if normalized in renamed: raise ValueError('Case-insensitive collision after explicit mapping')
        renamed[normalized]=member
        if member.isdir(): directories.add(normalized)
        target=destination.joinpath(*mapped.split('/'))
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Extraction path escaped destination')
        plan.append((member,name,mapped,target))
    if not set(RENAME)<=original or 'outputs/runtime.json' not in original:
        raise ValueError('Expected specific Linux case collision is absent')
    if not renamed['outputs'].isdir(): raise ValueError('Outputs root must be a directory')
    for _member,_name,mapped,_target in plan:
        for parent in PurePosixPath(mapped).parents:
            key=parent.as_posix().casefold()
            if key in renamed and key not in directories:
                raise ValueError('File/directory conflict after mapping')
    return plan


def main():
    archive=PRIVATE/'results.tar.gz'; marker=PRIVATE/'results.sha256'
    attempt_path=PRIVATE/'LAUNCH_ATTEMPT.json'; destination=PRIVATE/'collected_windows'
    receipt_path=PRIVATE/'COLLECTION_RECOVERY.json'
    if destination.exists() or destination.is_symlink() or receipt_path.exists():
        raise FileExistsError('Recovery destination/receipt must be fresh')
    expected=marker.read_text(encoding='ascii').strip()
    if not re.fullmatch('[0-9a-f]{64}',expected) or archive.stat().st_size>MAX_BYTES or sha(archive)!=expected:
        raise ValueError('Archive marker, size, or SHA-256 check failed')
    attempt_sha=sha(attempt_path)
    attempt=json.loads(attempt_path.read_text(encoding='utf-8'))
    if attempt.get('collection',{}).get('error_type')!='FileExistsError':
        raise ValueError('Original collection failure differs from reviewed failure')
    manifest=[]
    with tarfile.open(archive,'r:gz') as tar:
        plan=validate_members(tar.getmembers(),destination)
        destination.mkdir(mode=0o700,exist_ok=False)
        for member,original,mapped,target in plan:
            if member.isdir():
                target.mkdir(parents=True,exist_ok=True)
                manifest.append({'archive_path':original,'extracted_path':mapped,'type':'directory','bytes':0})
                continue
            target.parent.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256(); count=0
            with tar.extractfile(member) as source, target.open('xb') as sink:
                for block in iter(lambda:source.read(1024*1024),b''):
                    count+=len(block);digest.update(block);sink.write(block)
            member_sha=digest.hexdigest(); extracted_sha=sha(target)
            if count!=member.size or target.stat().st_size!=member.size or member_sha!=extracted_sha:
                raise ValueError('Extracted member byte-integrity failure')
            manifest.append({'archive_path':original,'extracted_path':mapped,'type':'file','bytes':count,
                             'archive_member_sha256':member_sha,'extracted_sha256':extracted_sha,'bytes_identical':True})
    if sha(archive)!=expected or sha(attempt_path)!=attempt_sha:
        raise ValueError('Original archive or attempt record changed during recovery')
    out=destination/'outputs';runtime=json.loads((out/'runtime.json').read_text(encoding='utf-8'))
    supervisor=(out/'SUPERVISOR_EXIT.txt').read_text(encoding='ascii').strip()
    def inventory(filename,phase,expected_count):
        rows=[json.loads(line) for line in (out/filename).read_text(encoding='utf-8').splitlines() if line.strip()]
        ids={(row['id'],row['model'],row['condition']) for row in rows}
        return {'rows':len(rows),'unique_id_model_condition':len(ids),'expected_rows':expected_count,
                'counts_by_model':dict(Counter(row['model'] for row in rows)),
                'counts_by_model_condition':dict(Counter(row['model']+'/'+row['condition'] for row in rows)),
                'phase_matches':all(row['phase']==phase for row in rows),
                'complete_unique_inventory':len(rows)==len(ids)==expected_count}
    prediction_inventory=inventory('predictions.jsonl','test',4988)
    qualification_inventory=inventory('qualification.jsonl','qualification',32)
    receipt={'status':'RECOVERED_LOCAL_CASE_COLLISION_BYTES_VERIFIED','created_utc':datetime.now(timezone.utc).isoformat(),
             'helper_path':str(Path(__file__).resolve()),'helper_sha256':sha(Path(__file__)),
             'archive_path':str(archive),'archive_sha256':expected,'archive_bytes':archive.stat().st_size,
             'marker_path':str(marker),'original_failure':attempt['collection'],
             'original_attempt_path':str(attempt_path),'original_attempt_sha256':attempt_sha,
             'original_attempt_unchanged':True,'original_partial_collection_unchanged':True,
             'cause':'Linux case-distinct outputs/RUNTIME.json and outputs/runtime.json collide on Windows',
             'explicit_path_mapping':RENAME,'extraction_directory':str(destination),'members':manifest,
             'supervisor_exit':supervisor,'supervisor_success':supervisor=='0','worker_status':runtime.get('status'),
             'predictions':prediction_inventory,'qualification':qualification_inventory,
             'runtime_prediction_hash_matches':runtime.get('predictions_sha256')==sha(out/'predictions.jsonl'),
             'runtime_qualification_output_hash_matches':runtime.get('qualification_outputs_sha256')==sha(out/'qualification.jsonl'),
             'cloud_closeout':attempt.get('closeout'),'cloud_actions':0,'inference_calls':0,
             'scope':'Transport/extraction and inventory recovery only; no accuracy analysis or scientific-result classification'}
    with receipt_path.open('x',encoding='utf-8') as stream:stream.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'directory':str(out),'receipt':str(receipt_path),
                      'supervisor_exit':supervisor,'worker_status':runtime.get('status'),
                      'prediction_rows':prediction_inventory['rows'],'qualification_rows':qualification_inventory['rows'],
                      'archive_sha256':expected}))


if __name__=='__main__':main()
