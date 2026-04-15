#!/usr/bin/env bash
set -euo pipefail

PRAXIS_ROOT="${PRAXIS_ROOT:-/mnt/praxis}"
REPO_URL="${REPO_URL:-https://github.com/garypagangit/praxis.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
REPO_DIR="${REPO_DIR:-${PRAXIS_ROOT}/repo}"
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-datasets/unraveled/network-flows}"
TARGET_DIR="${TARGET_DIR:-${PRAXIS_ROOT}/data/unraveled/network-flows}"
START_JUPYTER="${START_JUPYTER:-1}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8888}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

if [[ "${USER:-}" == "cloudshell-user" ]] || [[ "${AWS_EXECUTION_ENV:-}" == *"CloudShell"* ]]; then
  echo "This script is for the EC2 instance, not AWS CloudShell."
  echo "Open EC2 -> Instances -> Connect -> Session Manager, then run it there."
  exit 1
fi

if [[ -z "${GITHUB_TOKEN}" ]]; then
  read -rsp "GitHub token for garypagangit/praxis: " GITHUB_TOKEN
  echo
fi

if [[ -z "${GITHUB_TOKEN}" ]]; then
  echo "A GitHub token is required because garypagangit/praxis is private."
  exit 1
fi

SUDO=""
if [[ "${EUID}" -ne 0 ]]; then
  SUDO="sudo"
fi

AUTH_REPO_URL="${REPO_URL}"
if [[ "${REPO_URL}" =~ ^https://github\.com/ ]]; then
  AUTH_REPO_URL="${REPO_URL/https:\/\/github.com\//https://x-access-token:${GITHUB_TOKEN}@github.com/}"
fi

echo "Preparing Praxis under ${PRAXIS_ROOT}"

${SUDO} apt-get update
${SUDO} DEBIAN_FRONTEND=noninteractive apt-get install -y \
  awscli \
  build-essential \
  git \
  htop \
  python3-venv \
  tmux \
  unzip

${SUDO} mkdir -p "${PRAXIS_ROOT}"
${SUDO} chown -R "${USER}:${USER}" "${PRAXIS_ROOT}"

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  rm -rf "${REPO_DIR}"
  git clone --branch "${REPO_BRANCH}" "${AUTH_REPO_URL}" "${REPO_DIR}"
else
  git -C "${REPO_DIR}" remote set-url origin "${AUTH_REPO_URL}"
  git -C "${REPO_DIR}" fetch origin "${REPO_BRANCH}"
  git -C "${REPO_DIR}" checkout "${REPO_BRANCH}"
  git -C "${REPO_DIR}" pull --ff-only origin "${REPO_BRANCH}"
fi

git -C "${REPO_DIR}" remote set-url origin "${REPO_URL}"

cd "${REPO_DIR}"
chmod +x \
  scripts/bootstrap_aws_gpu_ubuntu.sh \
  scripts/start_jupyter_aws.sh \
  scripts/sync_unraveled_from_s3.sh

GITHUB_TOKEN="${GITHUB_TOKEN}" \
PRAXIS_ROOT="${PRAXIS_ROOT}" \
REPO_URL="${REPO_URL}" \
REPO_BRANCH="${REPO_BRANCH}" \
./scripts/bootstrap_aws_gpu_ubuntu.sh

unset GITHUB_TOKEN

if [[ -n "${S3_BUCKET}" ]]; then
  S3_BUCKET="${S3_BUCKET}" \
  S3_PREFIX="${S3_PREFIX}" \
  TARGET_DIR="${TARGET_DIR}" \
  ./scripts/sync_unraveled_from_s3.sh
else
  echo "S3_BUCKET not set, skipping dataset sync."
  echo "Later, rerun with:"
  echo "  S3_BUCKET=your-bucket-name ./scripts/sync_unraveled_from_s3.sh"
fi

if [[ "${START_JUPYTER}" == "1" ]]; then
  PRAXIS_ROOT="${PRAXIS_ROOT}" \
  REPO_DIR="${REPO_DIR}" \
  HOST="${HOST}" \
  PORT="${PORT}" \
  ./scripts/start_jupyter_aws.sh

  sleep 3
  if command -v tmux >/dev/null 2>&1; then
    echo
    echo "Recent Jupyter output:"
    tmux capture-pane -pt praxis-jupyter | tail -n 20 || true
  fi
fi

echo
echo "Praxis AWS setup complete."
echo "Repo: ${REPO_DIR}"
echo "Activate env: source ${REPO_DIR}/.venv/bin/activate"
echo "Train:"
echo "  python -m praxis.train --config configs/praxisv03-unraveled-aws-mamba-proper.json"
