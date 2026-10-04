#!/bin/bash
set -euo pipefail
df -h
if test -d /opt/praxis/ollama-017; then
  test "$(readlink -f /opt/praxis/ollama-017)" = /opt/praxis/ollama-017
  test -d /mnt/praxis-20260912-004
  recovery_dir=/mnt/praxis-20260912-004/assurance-recovery-20261004
  mkdir -p "$recovery_dir"
  test ! -e "$recovery_dir/ollama-017-attempt2"
  mv -- /opt/praxis/ollama-017 "$recovery_dir/ollama-017-attempt2"
fi
df -h
