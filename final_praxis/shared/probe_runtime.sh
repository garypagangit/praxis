#!/usr/bin/env bash
set -eu
date -u
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
df -h / /opt/dlami/nvme
ps -eo pid,comm,etime | grep -E 'python|vllm' || true
find /opt/dlami/nvme/praxis/venvs -maxdepth 3 -type f -name pyvenv.cfg -print 2>/dev/null | head -15
find /opt/dlami/nvme/praxis/hf-cache -maxdepth 3 -type d -name 'models--Qwen*' -print 2>/dev/null | head -10
find /opt/dlami/nvme/praxis/hf-cache -maxdepth 4 -type d -name snapshots -print 2>/dev/null | head -15
ls -d /opt/pytorch /home/ubuntu/anaconda3/envs/* /opt/dlami/nvme/praxis/venvs/* /opt/praxis/* 2>/dev/null || true
