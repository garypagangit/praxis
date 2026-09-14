#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo 'Usage: run_study.sh ABSOLUTE_CAMPAIGN_ROOT FROZEN_PROTOCOL_SHA256' >&2
  exit 2
fi
ROOT="$(realpath "$1")"
CODE="$ROOT/model_code"
PY="$ROOT/orchestrator_env/bin/python"
OUT="$ROOT/study"
export PRAXIS_PREREG_PATH="$CODE/MODEL_STUDY_PREREG.md"
export PRAXIS_PREREG_SHA256="$2"
mkdir -p "$OUT"
cd "$CODE"
phase=source_verification
closeout() {
  process_status=$?
  trap - EXIT
  "$PY" - "$OUT" "$phase" "$process_status" <<'CLOSEOUT'
import datetime,json,os,sys
from pathlib import Path
out=Path(sys.argv[1]);expected=['proposals_development.jsonl','proposals_heldout.jsonl']+[f'decisions_{cohort}_{split}.jsonl' for cohort in ('native','generated') for split in ('development','heldout')]
counts={name:sum(1 for line in (out/name).open() if line.strip()) if (out/name).exists() else None for name in expected}
report={'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':sys.argv[2],'exit_code':int(sys.argv[3]),'status':'finished' if sys.argv[3]=='0' else 'incomplete_requires_recovery','expected_review_assignments':9456,'expected_generated_proposals':328,'aggregate_row_counts':counts,'durable_decision_receipts':len(list((out/'decisions').glob('*.json'))),'durable_proposal_receipts':len(list((out/'proposals').glob('*.json'))),'paper_ready_claimed':False}
temporary=out/'STUDY_PROCESS_STATUS.tmp'
temporary.write_text(json.dumps(report,indent=2)+'\n')
os.replace(temporary,out/'STUDY_PROCESS_STATUS.json')
CLOSEOUT
  exit "$process_status"
}
trap closeout EXIT
"$PY" - <<'VERIFY'
import hashlib,json,os
from pathlib import Path
root=Path.cwd()
manifest=json.loads((root/'MODEL_SOURCE_FREEZE.json').read_text())
for relative,expected in manifest['files'].items():
    path=root/relative
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Source freeze mismatch:'+relative)
if hashlib.sha256(Path(os.environ['PRAXIS_PREREG_PATH']).read_bytes()).hexdigest()!=os.environ['PRAXIS_PREREG_SHA256']:raise ValueError('Protocol hash mismatch')
print('Model source freeze verified',flush=True)
VERIFY
if [ ! -f "$OUT/REFERENCE_MANIFEST.json" ]; then
  "$PY" generated_execution.py --tasks-file "$ROOT/bundle/data/tasks.jsonl" --qualification-private "$ROOT/full/private" --qualification-summary "$ROOT/full/public/SUMMARY.json" --prepare-reference-manifest "$OUT/REFERENCE_MANIFEST.json"
fi
for split in development heldout; do
  phase="proposals_${split}"
  "$PY" study_runner.py prepare-proposals --tasks "$ROOT/bundle/data/tasks.jsonl" --qualification "$ROOT/full" --output "$OUT" --split "$split"
  proposal_gate=()
  if [ "$split" = heldout ]; then
    "$PY" - "$OUT" <<'PROPOSER_GATE'
import sys
from pathlib import Path
from study_runner import read,save
from prompts import PROPOSER
root=Path(sys.argv[1]);checks={cohort:read(root/f'GATE_{cohort}_development.json')['models'][PROPOSER]['pass'] for cohort in ('native','generated')}
save(root/'PROPOSER_DEVELOPMENT_GATE.json',{'split':'development','proposer':PROPOSER,'checks':checks,'pass':all(checks.values())})
PROPOSER_GATE
    proposal_gate=(--gate "$OUT/PROPOSER_DEVELOPMENT_GATE.json")
  fi
  "$PY" study_runner.py infer-proposals --jobs "$OUT/proposal_jobs_${split}.jsonl" --output "$OUT" --split "$split" --workers 8 "${proposal_gate[@]}"
  phase="generated_execution_${split}"
  bash run_generated_docker.sh praxis008-qualification:20260914 "$CODE" "$ROOT/bundle" "$ROOT/full" "$OUT/proposals_${split}.jsonl" "$OUT/REFERENCE_MANIFEST.json" "$ROOT/generated_${split}"
  for cohort in native generated; do
    phase="prepare_${cohort}_${split}"
    extra=()
    if [ "$cohort" = generated ]; then
      extra=(--proposals "$OUT/proposals_${split}.jsonl" --evaluations "$ROOT/generated_${split}/public/PROPOSAL_RESULTS.jsonl" --evaluation-root "$ROOT/generated_${split}")
    fi
    "$PY" study_runner.py prepare-reviews --tasks "$ROOT/bundle/data/tasks.jsonl" --qualification "$ROOT/full" --output "$OUT" --split "$split" --cohort "$cohort" "${extra[@]}"
    gate=()
    if [ "$split" = heldout ]; then gate=(--gate "$OUT/GATE_${cohort}_development.json"); fi
    phase="inference_${cohort}_${split}"
    "$PY" study_runner.py infer-reviews --jobs "$OUT/review_jobs_${cohort}_${split}.jsonl" --output "$OUT" --split "$split" --cohort "$cohort" --workers 8 "${gate[@]}"
  done
done
phase=final_analysis
"$PY" finalize_results.py --study-root "$OUT" --protocol "$PRAXIS_PREREG_PATH" --protocol-sha256 "$PRAXIS_PREREG_SHA256"
phase=complete
