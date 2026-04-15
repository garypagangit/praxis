#!/usr/bin/env bash
set -euo pipefail

S3_BUCKET="${S3_BUCKET:?Set S3_BUCKET to your Praxis bucket name}"
S3_PREFIX="${S3_PREFIX:-datasets/unraveled/network-flows}"
TARGET_DIR="${TARGET_DIR:-/mnt/praxis/data/unraveled/network-flows}"

mkdir -p "${TARGET_DIR}"

echo "Syncing s3://${S3_BUCKET}/${S3_PREFIX} -> ${TARGET_DIR}"
aws s3 sync "s3://${S3_BUCKET}/${S3_PREFIX}" "${TARGET_DIR}" --no-progress

echo "Dataset sync complete."
