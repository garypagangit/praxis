#!/usr/bin/env bash
set -eu
WORK=/opt/dlami/nvme/praxis-final/20260908
date -u
nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader
for log in "$WORK/logs/fp002-discovery-v1.log" "$WORK/logs/fp003-discovery-v2.log" "$WORK/logs/fp001-discovery-agent-v2.log" "$WORK/logs/fp001-discovery-judge-v2.log"; do
  if [ -f "$log" ]; then printf '%s\n' "$log"; tail -3 "$log"; fi
done
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/opt/dlami/nvme/praxis-final/20260908')
for source in ('source-v1','source-v2'):
 for folder in (root/source/'final_praxis').glob('00*'):
  for raw in folder.glob('artifacts/discovery/*/raw.jsonl'):
   print(json.dumps({'file':str(raw.relative_to(root)),'rows':sum(1 for _ in raw.open())}))
  for records in folder.glob('runs/*/records'):
   print(json.dumps({'folder':str(records.relative_to(root)),'records':len(list(records.glob('*.json')))}))
PY
