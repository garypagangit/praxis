#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 4 ]; then
  echo 'Usage: run_docker.sh IMAGE BUNDLE_DIRECTORY RESULT_DIRECTORY pilot|full' >&2
  exit 2
fi
image="$1"
bundle="$(realpath "$2")"
result="$3"
mode="$4"
case "$mode" in pilot|full) ;; *) exit 2 ;; esac
mkdir -p "$result"
result="$(realpath "$result")"
chown 10001:10001 "$result"
chmod 0770 "$result"
image_id="$(docker image inspect --format '{{.Id}}' "$image")"
timeout --signal=TERM --kill-after=30s 21600s docker run --rm \
  --name "praxis008-qualification-${mode}" \
  --network none --user 10001:10001 --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --cpus 3 --memory 12g --memory-swap 12g --pids-limit 128 --ulimit core=0 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=512m \
  --env PRAXIS_ISOLATED_EXECUTION=1 --env "PRAXIS_IMAGE_ID=$image_id" \
  --mount "type=bind,source=$bundle/data,target=/data,readonly" \
  --mount "type=bind,source=$bundle/BUNDLE_MANIFEST.json,target=/manifest.json,readonly" \
  --mount "type=bind,source=$result,target=/output" \
  "$image" --mode "$mode" --workers 3
