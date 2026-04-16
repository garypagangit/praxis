#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${HOME}/SageMaker/praxis-storage/data/unraveled/network-flows}"
TARGET_DIR="${TARGET_DIR:-${REPO_DIR}/imports/unraveled/data/network-flows}"

mkdir -p "$(dirname "${TARGET_DIR}")"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Dataset source directory not found: ${SOURCE_DIR}"
  echo "Upload the Unraveled dataset there first, then rerun this script."
  exit 1
fi

if [[ -L "${TARGET_DIR}" ]]; then
  CURRENT_TARGET="$(readlink "${TARGET_DIR}")"
  if [[ "${CURRENT_TARGET}" == "${SOURCE_DIR}" ]]; then
    echo "Dataset link already points to ${SOURCE_DIR}"
    exit 0
  fi
  rm "${TARGET_DIR}"
fi

if [[ -e "${TARGET_DIR}" ]]; then
  echo "Target path already exists and is not a matching symlink: ${TARGET_DIR}"
  echo "Move it aside or remove it, then rerun this script."
  exit 1
fi

ln -s "${SOURCE_DIR}" "${TARGET_DIR}"
echo "Linked ${TARGET_DIR} -> ${SOURCE_DIR}"
