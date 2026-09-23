#!/usr/bin/env bash
# Invoked through the existing watchdog-protected controller after payload freeze.
set -euo pipefail
test "$#" -eq 5
bundle_uri="$1"
bundle_sha="$2"
output_uri="$3"
run_id="$4"
deadline_epoch="$5"
[[ "$bundle_uri" =~ ^s3:// ]]
[[ "$output_uri" =~ ^s3:// ]]
[[ "$bundle_sha" =~ ^[0-9a-f]{64}$ ]]
[[ "$run_id" =~ ^praxis-provics-[a-f0-9]{16}$ ]]
[[ "$deadline_epoch" =~ ^[0-9]+$ ]]
run_dir="/opt/praxis/runs/$run_id"
test ! -e "$run_dir"
mkdir -p "$run_dir/outputs/reports" "$run_dir/outputs/data"
cd "$run_dir"
export AWS_DEFAULT_REGION=us-east-1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
publish() {
  rc=$?
  trap - EXIT TERM INT
  cd "$run_dir"
  printf '%s\n' "$rc" > outputs/WORKER_EXIT.txt
  timeout --kill-after=5s 50 tar -czf result.tar.gz outputs || exit 90
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  timeout --kill-after=5s 90 aws s3 cp result.tar.gz "${output_uri}/result.tar.gz" --only-show-errors &&
    timeout --kill-after=5s 15 aws s3 cp result.sha256 "${output_uri}/result.sha256" --only-show-errors || rc=91
  exit "$rc"
}
trap publish EXIT
trap 'exit 124' TERM INT
bounded() {
  maximum="$1"; shift
  remaining=$((deadline_epoch - $(date +%s) - 165))
  test "$remaining" -ge 10
  if test "$maximum" -gt "$remaining"; then maximum="$remaining"; fi
  timeout --signal=TERM --kill-after=5s "${maximum}s" "$@"
}
bounded 90 aws s3 cp "$bundle_uri" bundle.tar.gz --only-show-errors
printf '%s  bundle.tar.gz\n' "$bundle_sha" | sha256sum -c -
bounded 10 python3 -c 'import sys; assert sys.version_info >= (3,9), "Bootstrap requires Python >= 3.9"' > outputs/BOOTSTRAP_PYTHON.log 2>&1
bounded 30 python3 - <<'PY'
import hashlib,json,tarfile
from pathlib import Path,PurePosixPath
root=Path.cwd().resolve()
with tarfile.open('bundle.tar.gz','r:gz') as archive:
    seen=set();total=0
    for member in archive.getmembers():
        parts=PurePosixPath(member.name).parts; target=(root/member.name).resolve()
        if (member.name in seen or '\\' in member.name or not parts or
            parts[0] not in {'repo','BUNDLE_CONTENTS.json'} or
            any(p in {'.','..'} for p in parts) or not member.isfile() or
            not target.is_relative_to(root)):
            raise ValueError('Invalid bundle member')
        seen.add(member.name);total+=member.size
        if len(seen)>8 or total>1_000_000:raise ValueError('Bundle exceeds bound')
    archive.extractall(root)
manifest=json.loads((root/'BUNDLE_CONTENTS.json').read_text())
if seen != set(manifest['files'])|{'BUNDLE_CONTENTS.json'}:raise ValueError('Whitelist mismatch')
for name,expected in manifest['files'].items():
    path=root/name
    if path.stat().st_size!=expected['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=expected['sha256']:
        raise ValueError('Member hash mismatch')
(root/'outputs'/'BUNDLE_CONTENTS.json').write_text(json.dumps(manifest,indent=2))
PY
python_bin=""
for candidate in \
 /opt/praxis/venvs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630/bin/python \
 /opt/praxis/venvs/falsecite-code-generation-gate-20260625/bin/python \
 /opt/pytorch/bin/python \
 /usr/bin/python3; do
  printf 'Checking %s\n' "$candidate" >> outputs/ENV_SELECTION.log
  if test -x "$candidate" && bounded 20 "$candidate" -c 'import sys,venv,ensurepip; print(sys.version); assert (3,10) <= sys.version_info < (3,14)' >> outputs/ENV_SELECTION.log 2>&1; then
    python_bin="$candidate"; break
  fi
done
test -n "$python_bin"
bounded 25 "$python_bin" - <<'PY' > outputs/SETUP_PREFLIGHT.json
import json,pathlib,shutil,urllib.request
disk=shutil.disk_usage(pathlib.Path.cwd())
if disk.free < 2_000_000_000:raise ValueError('At least 2 GB free space required for bounded acquisition')
with urllib.request.urlopen('https://pypi.org/simple/pandas/',timeout=15) as response:
    status=response.status
    if status != 200:raise ValueError('Ordinary PyPI access unavailable')
print(json.dumps({'free_disk_bytes':disk.free,'required_free_bytes':2_000_000_000,
                  'pypi_http_status':status,'shared_environment_modified':False},indent=2))
PY
bounded 60 "$python_bin" -m venv "$run_dir/venv" > outputs/VENV_SETUP.log 2>&1
python_bin="$run_dir/venv/bin/python"
bounded 180 "$python_bin" -m pip install --only-binary=:all: --no-input \
 --disable-pip-version-check --no-cache-dir --retries 1 --timeout 20 \
 --index-url https://pypi.org/simple numpy==2.2.6 pandas==2.3.3 requests==2.32.5 \
 > outputs/DEPENDENCIES.log 2>&1
bounded 15 "$python_bin" -m pip freeze > outputs/PIP_FREEZE.txt
bounded 20 "$python_bin" - <<'PY' > outputs/ENVIRONMENT.json
import datetime,importlib.metadata,json,platform,sys
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'python':sys.version,'platform':platform.platform(),'model_fits':0,'gpu_used':False,
 'packages':{x:importlib.metadata.version(x) for x in ['numpy','pandas','requests']}},indent=2))
PY
bounded 35 "$python_bin" - <<'PY' > outputs/SOURCE_REVISION.json
import datetime,json,re,requests
url='https://huggingface.co/api/datasets/trucyberlab/multimodal-ICS-provenance'
response=requests.get(url,timeout=(6,20));response.raise_for_status()
revision=response.json()['sha']
if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
    raise ValueError('Expected one immutable author-repository commit')
print(json.dumps({'metadata_url':url,'revision':revision,
                  'resolved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'same_revision_required_for_all_seven_files':True},indent=2))
PY
provics_revision="$(bounded 10 "$python_bin" -c 'import json; print(json.load(open("outputs/SOURCE_REVISION.json"))["revision"])')"
[[ "$provics_revision" =~ ^[0-9a-f]{40}$ ]]
bounded 480 "$python_bin" -u repo/experiments/praxis_next/data_qualification/acquire_provics.py \
 --data-root "$run_dir/outputs/data/provics" \
 --report-dir "$run_dir/outputs/reports" --revision "$provics_revision" > outputs/worker.log 2>&1
bounded 20 "$python_bin" - <<'PY'
import datetime,json,pathlib
p=pathlib.Path('outputs/reports/provics_qualification.json')
q=json.loads(p.read_text())
source=json.loads(pathlib.Path('outputs/SOURCE_REVISION.json').read_text())
receipts=json.loads(pathlib.Path('outputs/reports/provics_acquisition.json').read_text())
if not all(row['revision_requested']==source['revision'] for row in receipts['files']):
    raise ValueError('Mixed source revisions are prohibited')
pathlib.Path('outputs/WORKER_STATUS.json').write_text(json.dumps({
 'status':'QUALIFICATION_FINISHED','gate':q['gate'],'model_fits':0,'gpu_used':False,
 'dataset_revision':source['revision'],
 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2))
PY
