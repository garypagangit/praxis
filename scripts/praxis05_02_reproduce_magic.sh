#!/usr/bin/env bash
set -euo pipefail

if [ ! -d external/MAGIC/.git ]; then
  echo "external/MAGIC is missing. Run scripts/praxis05_01_setup.sh first." >&2
  exit 2
fi

if [ -z "${MAGIC_REPRO_COMMAND:-}" ]; then
  echo "Set MAGIC_REPRO_COMMAND to the upstream MAGIC E3-CADETS train/eval command before running." >&2
  echo "Example: MAGIC_REPRO_COMMAND='python ...' bash scripts/praxis05_02_reproduce_magic.sh" >&2
  exit 2
fi

mkdir -p results/praxis05/replication
(
  cd external/MAGIC
  echo "MAGIC commit: $(git rev-parse HEAD)"
  echo "Command: $MAGIC_REPRO_COMMAND"
  bash -lc "$MAGIC_REPRO_COMMAND"
) 2>&1 | tee results/praxis05/replication/magic_e3cadets_reproduction.log

cat > results/praxis05/replication/README.md <<'EOF'
# Praxis 05 MAGIC Replication

Review `magic_e3cadets_reproduction.log` and record AUROC/F1 here.
Phase A SAE training must not start unless MAGIC is within 2 absolute points of the published metric target.
EOF

