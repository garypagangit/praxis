#!/usr/bin/env bash
set -euxo pipefail

exec > >(tee -a /var/log/praxis-gpu-runner-bootstrap.log) 2>&1

if command -v snap >/dev/null 2>&1; then
  snap install amazon-ssm-agent --classic || true
  systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service || true
  systemctl restart snap.amazon-ssm-agent.amazon-ssm-agent.service || true
else
  systemctl enable amazon-ssm-agent || true
  systemctl restart amazon-ssm-agent || true
fi

mkdir -p /opt/praxis/jobs /opt/praxis/venvs
chown -R ubuntu:ubuntu /opt/praxis || true
