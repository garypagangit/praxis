set -eu
date -u
uname -a
python3 --version
command -v python3.11 || true
command -v python3.10 || true
command -v aws || true
command -v uv || true
df -h /
lsblk --json --output PATH,SERIAL,SIZE,FSTYPE,MOUNTPOINT,TYPE
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader
python3 -c 'import importlib.util,json; print(json.dumps({m:bool(importlib.util.find_spec(m)) for m in ["boto3","torch","transformers","venv"]}))'
shutdown --show || true
