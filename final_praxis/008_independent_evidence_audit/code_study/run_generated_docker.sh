#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 7 ]; then
  echo 'Usage: run_generated_docker.sh IMAGE CODE_STUDY_DIRECTORY BUNDLE_DIRECTORY QUALIFICATION_FULL_DIRECTORY PROPOSALS_JSONL REFERENCE_MANIFEST_JSON RESULT_DIRECTORY' >&2
  exit 2
fi
image="$1"
study="$(realpath "$2")"
bundle="$(realpath "$3")"
qualification="$(realpath "$4")"
proposals="$(realpath "$5")"
references="$(realpath "$6")"
mkdir -p "$7"
result="$(realpath "$7")"
chown 10001:10001 "$result"
chmod 0770 "$result"
image_id="$(docker image inspect --format '{{.Id}}' "$image")"
timeout --signal=TERM --kill-after=30s 21600s docker run --rm \
  --name praxis008-generated-execution \
  --network none --user 10001:10001 --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --cpus 3 --memory 12g --memory-swap 12g --pids-limit 128 --ulimit core=0 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=512m \
  --env PRAXIS_ISOLATED_EXECUTION=1 --env "PRAXIS_IMAGE_ID=$image_id" \
  --mount "type=bind,source=$study,target=/app_study,readonly" \
  --mount "type=bind,source=$bundle/data,target=/data,readonly" \
  --mount "type=bind,source=$qualification/private,target=/qualification_private,readonly" \
  --mount "type=bind,source=$qualification/public/SUMMARY.json,target=/qualification_summary.json,readonly" \
  --mount "type=bind,source=$proposals,target=/proposals.jsonl,readonly" \
  --mount "type=bind,source=$references,target=/reference_manifest.json,readonly" \
  --mount "type=bind,source=$result,target=/output" \
  --entrypoint python "$image" /app_study/generated_execution.py \
  --proposals /proposals.jsonl --reference-manifest /reference_manifest.json --workers 3
