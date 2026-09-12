set -eu
export TMPDIR=/mnt/praxis-20260912-004/tmp
export PIP_CACHE_DIR=/mnt/praxis-20260912-004/pip-cache
python3 -m venv /mnt/praxis-20260912-004/venv
/mnt/praxis-20260912-004/venv/bin/python -m pip install --disable-pip-version-check boto3==1.43.55 swebench==4.1.0 pytest==8.3.5
/mnt/praxis-20260912-004/venv/bin/python -m pip freeze > /mnt/praxis-20260912-004/environment.freeze.txt
DOCKER_HOST=unix:///run/praxis-docker-20260912.sock /mnt/praxis-20260912-004/venv/bin/python -c 'import docker,swebench,boto3; print(docker.from_env().ping()); print(boto3.__version__)'
