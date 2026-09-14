set -euo pipefail
ROOT=/mnt/praxis-20260912-004/008-code-study-20260914
DEST=s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/008-code-study/20260914
cd "$ROOT"
aws s3 cp "$DEST/inputs/model_code_v2.tar.gz" model_code_v2.tar.gz --only-show-errors
printf '%s  %s\n' 5b939d1b1af090a510afe3f6278ab23f2d162cc69a92775fa1afacf94e852205 model_code_v2.tar.gz | sha256sum -c -
mkdir -p model_code_v2 study_v2
python3 - <<'SAFE'
import tarfile
from pathlib import Path
root=Path('model_code_v2').resolve()
with tarfile.open('model_code_v2.tar.gz') as tar:
 for member in tar.getmembers():
  if not (root/member.name).resolve().is_relative_to(root) or not (member.isfile() or member.isdir()):raise ValueError('Unsafe extension source archive')
 tar.extractall(root)
SAFE
bash -n model_code_v2/run_generated_docker.sh
export PRAXIS_PREREG_SHA256=9e6ba43fd988b47273c13ae4a5dc569640d210d2178103afaab964ed2bf236c3
export PYTHONUNBUFFERED=1
set +e
timeout --signal=TERM --kill-after=60s 18000s orchestrator_env/bin/python model_code_v2/technical_extension/run_extension.py --campaign-root "$ROOT" > extension_study.log 2>&1 &
extension_job_pid=$!
checkpoint_tick=0
while kill -0 "$extension_job_pid" 2>/dev/null; do
  python3 - <<'HEARTBEAT'
import datetime,json,os
from pathlib import Path
root=Path.cwd();out=root/'study_v2';budget=None
if (out/'budget.json').exists():
 try:
  ledger=json.loads((out/'budget.json').read_text());budget={'attempts':len(ledger['entries']),'accounted_usd_estimate':sum(r['accounted_usd'] for r in ledger['entries'].values()),'limit_usd':ledger['limit_usd']}
 except Exception:pass
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'durable_proposal_records':len(list((out/'proposals').glob('*.json'))),'durable_decision_records':len(list((out/'decisions').glob('*.json'))),'budget':budget,'aggregates_present':sorted(p.name for p in out.glob('*.jsonl')),'warmup_receipt_present':(out/'SCHEMA_WARMUP.json').exists(),'log_tail':(root/'extension_study.log').read_text(errors='replace')[-1800:]}
tmp=root/'V2_MODEL_PROGRESS.tmp';tmp.write_text(json.dumps(report,indent=2)+'\n');os.replace(tmp,root/'V2_MODEL_PROGRESS.json')
HEARTBEAT
  aws s3 cp V2_MODEL_PROGRESS.json "$DEST/V2_MODEL_PROGRESS.json" --only-show-errors
  aws s3 cp extension_study.log "$DEST/extension_study.log" --only-show-errors
  checkpoint_tick=$((checkpoint_tick+1))
  if [ "$checkpoint_tick" -ge 10 ]; then
    checkpoint_tick=0
    paths=(study_v2)
    if [ -d generated_v2_heldout ]; then paths+=(generated_v2_heldout); fi
    tar -czf study_v2_checkpoint.tar.gz "${paths[@]}" 2> setup/v2-checkpoint-tar.log
    aws s3 cp study_v2_checkpoint.tar.gz "$DEST/study_v2_checkpoint.tar.gz" --only-show-errors
  fi
  sleep 30
done
wait "$extension_job_pid"
extension_exit=$?
paths=(study_v2)
if [ -d generated_v2_heldout ]; then paths+=(generated_v2_heldout); fi
tar -czf model_study_v2_archive.tar.gz "${paths[@]}"
aws s3 cp model_study_v2_archive.tar.gz "$DEST/model_study_v2_archive.tar.gz" --only-show-errors
aws s3 cp extension_study.log "$DEST/extension_study.log" --only-show-errors
if [ -f study_v2/EXTENSION_PROCESS_STATUS.json ]; then
  aws s3 cp study_v2/EXTENSION_PROCESS_STATUS.json "$DEST/EXTENSION_PROCESS_STATUS.json" --only-show-errors
  cat study_v2/EXTENSION_PROCESS_STATUS.json
fi
sha256sum model_study_v2_archive.tar.gz
exit "$extension_exit"
