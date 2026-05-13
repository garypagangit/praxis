#!/usr/bin/env bash
set -euo pipefail

BUCKET="praxis-garypagan-272615233626-us-east-1"
RUN_ROOT="/home/ec2-user/tta-defense-hardening-20260513"
BUNDLE_S3="s3://${BUCKET}/experiments/tta-streaming-apt/cloud-bundles/praxis-tta-defense-hardening-20260513.tar.gz"
OUTPUT_S3="s3://${BUCKET}/experiments/tta-streaming-apt/runs/tta-defense-hardening-20260513"
SOURCE_RUN="runs/mlp-support-floor-7seed-extension-20260513"
CONFIG="configs/praxisv03-unraveled-support-floor-baseline-20260423.json"

echo "Starting Praxis 06 TTA defense hardening cloud job at $(date -u --iso-8601=seconds)"
rm -rf "${RUN_ROOT}"
mkdir -p "${RUN_ROOT}"
cd "${RUN_ROOT}"

echo "Downloading code bundle: ${BUNDLE_S3}"
aws s3 cp "${BUNDLE_S3}" bundle.tar.gz
mkdir -p repo
tar -xzf bundle.tar.gz -C repo
cd repo

echo "Creating Python environment"
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install numpy pandas scikit-learn imbalanced-learn matplotlib seaborn optuna mambapy
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install torch-geometric
python -m pip install -e .

echo "Fetching processed Unraveled cache"
mkdir -p data/processed/unraveled_v02
aws s3 cp "s3://${BUCKET}/datasets/unraveled/processed/v02/benchmark_cache.csv" data/processed/unraveled_v02/benchmark_cache.csv
aws s3 cp "s3://${BUCKET}/datasets/unraveled/processed/v02/benchmark_cache_metadata.json" data/processed/unraveled_v02/benchmark_cache_metadata.json

echo "Preparing combined 7-seed source run"
rm -rf "${SOURCE_RUN}"
cp -a runs/mlp-support-floor-3seed-ablation-20260423 "${SOURCE_RUN}"

echo "Training extra locked-recipe seeds 45-48"
python scripts/run_support_floor_mlp_ablation.py \
  --config "${CONFIG}" \
  --run-name "mlp-support-floor-7seed-extension-20260513" \
  --seeds "45,46,47,48" \
  --variants "adasyn_weighted_ce"

echo "Running defense hardening diagnostics across seeds 42-48"
python scripts/run_tta_defense_hardening.py \
  --config "${CONFIG}" \
  --source-run-dir "${SOURCE_RUN}" \
  --selection-run-dir "runs/tta-hybrid-gate-sweep-20260509" \
  --run-name "tta-defense-hardening-20260513" \
  --seeds "42,43,44,45,46,47,48" \
  --skip-dapt-shift

echo "Syncing cloud outputs to S3"
aws s3 sync "${SOURCE_RUN}" "${OUTPUT_S3}/source_run/"
aws s3 sync "runs/tta-defense-hardening-20260513" "${OUTPUT_S3}/diagnostics/"

echo "Completed Praxis 06 TTA defense hardening cloud job at $(date -u --iso-8601=seconds)"
