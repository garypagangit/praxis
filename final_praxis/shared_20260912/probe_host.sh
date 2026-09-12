set -eu
shutdown -P +470
mkdir -p /opt/praxis/campaign-20260912
date -u
uname -a
python3 --version
command -v python3.11 || true
command -v python3.10 || true
docker --version || true
df -h /opt
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader || true
python3 -c 'import importlib.util,json; print(json.dumps({m:bool(importlib.util.find_spec(m)) for m in ["boto3","torch","transformers","datasets","docker"]}))'
find /opt -maxdepth 3 -type d -name '*venv*' -print
shutdown --show || true
