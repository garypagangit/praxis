#!/usr/bin/env bash
set -euo pipefail

MAGIC_REPO_URL="${MAGIC_REPO_URL:-https://github.com/FDUDSDE/MAGIC.git}"
PIDSM_REPO_URL="${PIDSM_REPO_URL:-https://github.com/ubc-provenance/PIDSMaker.git}"

mkdir -p external results/praxis05

if [ ! -d external/MAGIC/.git ]; then
  git clone "$MAGIC_REPO_URL" external/MAGIC
fi

if [ ! -d external/PIDSMaker/.git ]; then
  git clone "$PIDSM_REPO_URL" external/PIDSMaker
fi

python -m pip install -r requirements-praxis05.txt

python - <<'PY'
import json
import pathlib
import platform
import subprocess

def commit(path):
    return subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"], text=True).strip()

payload = {
    "python": platform.python_version(),
    "platform": platform.platform(),
    "magic_commit": commit("external/MAGIC"),
    "pidsmaker_commit": commit("external/PIDSMaker"),
}
try:
    import sae_lens
    payload["sae_lens_version"] = getattr(sae_lens, "__version__", "unknown")
except Exception as exc:
    payload["sae_lens_error"] = str(exc)

path = pathlib.Path("results/praxis05/env.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
PY

