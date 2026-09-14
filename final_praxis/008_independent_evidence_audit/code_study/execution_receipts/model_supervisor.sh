set -euo pipefail
ROOT=/mnt/praxis-20260912-004/008-code-study-20260914
DEST=s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/008-code-study/20260914
cd "$ROOT"
aws s3 cp "$DEST/inputs/model_code.tar.gz" model_code.tar.gz --only-show-errors
printf '%s  %s\n' 962b88b0c3e7bd7af19bb61dd6f4ef63d84ac94c3b93d4b72772abede05111b9 model_code.tar.gz | sha256sum -c -
mkdir -p model_code study
python3 - <<'SAFE'
import tarfile
from pathlib import Path
root=Path('model_code').resolve()
with tarfile.open('model_code.tar.gz') as tar:
 for member in tar.getmembers():
  if not (root/member.name).resolve().is_relative_to(root) or not (member.isfile() or member.isdir()):raise ValueError('Unsafe model source archive')
 tar.extractall(root)
SAFE
bash -n model_code/run_study.sh
bash -n model_code/run_generated_docker.sh
printf '%s\n' 'Both Linux shell syntax checks passed' > setup/model-shell-syntax.txt
set +e
timeout --signal=TERM --kill-after=60s 21600s bash model_code/run_study.sh "$ROOT" 11b620786e74a374158c93181024e1bfec216fc8edfa3c4178bbd12bd234610a > model_study.log 2>&1 &
model_job_pid=$!
checkpoint_tick=0
while kill -0 "$model_job_pid" 2>/dev/null; do
  python3 - <<'HEARTBEAT'
import datetime,json,os
from pathlib import Path
root=Path.cwd();out=root/'study';budget=None
if (out/'budget.json').exists():
 try:
  ledger=json.loads((out/'budget.json').read_text());budget={'attempts':len(ledger['entries']),'accounted_usd_estimate':sum(r['accounted_usd'] for r in ledger['entries'].values()),'limit_usd':ledger['limit_usd']}
 except Exception:pass
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'durable_proposal_records':len(list((out/'proposals').glob('*.json'))),'durable_decision_records':len(list((out/'decisions').glob('*.json'))),'budget':budget,'aggregates_present':sorted(p.name for p in out.glob('*.jsonl')),'model_log_tail':(root/'model_study.log').read_text(errors='replace')[-1800:]}
tmp=root/'MODEL_PROGRESS.tmp';tmp.write_text(json.dumps(report,indent=2)+'\n');os.replace(tmp,root/'MODEL_PROGRESS.json')
HEARTBEAT
  aws s3 cp MODEL_PROGRESS.json "$DEST/MODEL_PROGRESS.json" --only-show-errors
  aws s3 cp model_study.log "$DEST/model_study.log" --only-show-errors
  checkpoint_tick=$((checkpoint_tick+1))
  if [ "$checkpoint_tick" -ge 10 ]; then
    checkpoint_tick=0
    paths=(study)
    for name in generated_development generated_heldout; do if [ -d "$name" ]; then paths+=("$name"); fi; done
    tar -czf study_checkpoint.tar.gz "${paths[@]}" 2> setup/checkpoint-tar.log
    aws s3 cp study_checkpoint.tar.gz "$DEST/study_checkpoint.tar.gz" --only-show-errors
  fi
  sleep 30
done
wait "$model_job_pid"
model_exit=$?
paths=(study)
for name in generated_development generated_heldout; do if [ -d "$name" ]; then paths+=("$name"); fi; done
tar -czf model_study_archive.tar.gz "${paths[@]}"
aws s3 cp model_study_archive.tar.gz "$DEST/model_study_archive.tar.gz" --only-show-errors
aws s3 cp model_study.log "$DEST/model_study.log" --only-show-errors
aws s3 cp study/STUDY_PROCESS_STATUS.json "$DEST/STUDY_PROCESS_STATUS.json" --only-show-errors
sha256sum model_study_archive.tar.gz
cat study/STUDY_PROCESS_STATUS.json
exit "$model_exit"
