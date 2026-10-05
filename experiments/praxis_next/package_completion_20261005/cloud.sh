#!/bin/bash
set -euo pipefail
base=/mnt/praxis-20260912-004
mountpoint -q "$base"
test "$(df --output=avail -B1 "$base" | tail -1)" -gt 10000000000
input_url="$1"; input_sha="$2"; output_url="$3"; run_name="$4"
mkdir -p "$base/$run_name"
cd "$base/$run_name"
mkdir -p outputs wheels tmp
export TMPDIR="$PWD/tmp"
publish() {
  rc=$?
  echo "$rc" > outputs/WORKER_EXIT.txt
  if test -n "${dockerd_pid:-}"; then kill "$dockerd_pid" || true; fi
  tar -czf result.tar.gz outputs
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  aws s3 cp result.tar.gz "$output_url/result.tar.gz" --only-show-errors || true
  aws s3 cp result.sha256 "$output_url/result.sha256" --only-show-errors || true
  exit "$rc"
}
trap publish EXIT
aws s3 cp "$input_url" bundle.tar.gz --only-show-errors
echo "$input_sha  bundle.tar.gz" | sha256sum -c -
tar -xzf bundle.tar.gz
export DOCKER_HOST="unix://$PWD/docker.sock"
dockerd --host="$DOCKER_HOST" --data-root="$PWD/docker-data" --exec-root="$PWD/docker-exec" --pidfile="$PWD/docker.pid" --bridge=none --iptables=false --ip-forward=false --ip-masq=false > outputs/dockerd.log 2>&1 &
dockerd_pid=$!
for attempt in $(seq 1 40); do docker info > outputs/docker_info.txt 2>&1 && break; sleep 1; done
docker info > outputs/docker_info.txt
docker pull python:3.11-slim > outputs/image_pull.txt 2>&1
docker image inspect python:3.11-slim > outputs/image_identity.json
export PRAXIS_DOCKER_IMAGE="$(docker image inspect python:3.11-slim --format '{{.Id}}')"
python3 -m pip download --no-deps --only-binary=:all: --platform manylinux2014_x86_64 --python-version 311 --implementation cp --abi cp311 numpy==2.2.6 -d wheels > outputs/wheel_download.txt 2>&1
sha256sum wheels/* > outputs/wheel_hashes.txt
timeout --signal=TERM --kill-after=10s 900 python3 -u sandbox_pilot.py > outputs/run.log 2>&1
