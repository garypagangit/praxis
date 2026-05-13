#!/usr/bin/env bash
set -euo pipefail

BUCKET="${BUCKET:-praxis-garypagan-272615233626-us-east-1}"
ROOT="${ROOT:-/opt/praxis-data}"
LOG_DIR="${ROOT}/logs"
RAW_DIR="${ROOT}/raw"
HOME="${HOME:-/root}"

mkdir -p "${LOG_DIR}" "${RAW_DIR}"

exec > >(tee -a "${LOG_DIR}/large-dataset-mirror.log") 2>&1

echo "Started large dataset mirror at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Bucket: ${BUCKET}"
echo "Root: ${ROOT}"

if command -v dnf >/dev/null 2>&1; then
  dnf install -y python3 python3-pip git tar gzip unzip awscli
fi

python3 -m pip install --user --upgrade pip
python3 -m pip install --user --upgrade gdown
export PATH="${HOME}/.local/bin:${PATH}"

aws sts get-caller-identity
df -h "${ROOT}" || true

mirror_folder() {
  local name="$1"
  local url="$2"
  local local_dir="$3"
  local s3_prefix="$4"

  echo ""
  echo "==== ${name} ===="
  echo "URL: ${url}"
  echo "Local: ${local_dir}"
  echo "S3: s3://${BUCKET}/${s3_prefix}"
  mkdir -p "${local_dir}"

  # gdown handles public Google Drive folders and can resume partial folder mirrors.
  python3 -m gdown --folder "${url}" --output "${local_dir}" --remaining-ok

  echo "Syncing ${name} to S3..."
  aws s3 sync "${local_dir}" "s3://${BUCKET}/${s3_prefix}" --no-progress

  echo "Writing manifest for ${name}..."
  find "${local_dir}" -type f -printf '%P\t%s\n' | sort > "${local_dir}/_manifest_files.tsv"
  aws s3 cp "${local_dir}/_manifest_files.tsv" "s3://${BUCKET}/${s3_prefix}manifests/_manifest_files.tsv" --no-progress
}

mirror_folder \
  "DARPA TC Engagement 5 full public release" \
  "https://drive.google.com/drive/folders/1okt4AYElyBohW4XiOBqmsvjwXsnUjLVf" \
  "${RAW_DIR}/darpa-tc/e5" \
  "datasets/darpa-tc/raw/engagement-5/"

mirror_folder \
  "DARPA TC Engagement 3 full public release" \
  "https://drive.google.com/open?id=1QlbUFWAGq3Hpl8wVdzOdIoZLFxkII4EK" \
  "${RAW_DIR}/darpa-tc/e3" \
  "datasets/darpa-tc/raw/engagement-3/"

mirror_folder \
  "OpTC full public release" \
  "https://drive.google.com/drive/u/0/folders/1n3kkS3KR31KUegn42yk3-e6JkZvf0Caa" \
  "${RAW_DIR}/optc" \
  "datasets/optc/raw/full-drive-mirror/"

echo ""
echo "Completed large dataset mirror at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
