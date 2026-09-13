from pathlib import Path
import hashlib, json, sys, urllib.request
from urllib.parse import quote
SHA = "082dcbf5304329ef1ff08f5830e4116256b00a59"
ROOT = Path(__file__).resolve().parent
FILES = ["evaluation/answer_analysis.py", "evaluation/data_compare.py", "evaluation/q_execution.py", "dataset-all - all_purposes.csv", "CoT.rerun/answer_1-154_gt.json"]
manifest = {"repository": "https://github.com/LanLi2017/LLM4DC", "revision": SHA, "files": []}
for filename in FILES:
    url = "https://raw.githubusercontent.com/LanLi2017/LLM4DC/" + SHA + "/" + quote(filename)
    request = urllib.request.Request(url, headers={"User-Agent": "Praxis-artifact-audit-readonly"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise RuntimeError("Unexpected source size: " + filename)
    target = ROOT / "source" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != raw:
        raise RuntimeError("Pinned source content changed: " + filename)
    target.write_bytes(raw)
    manifest["files"].append({"path": filename, "url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
(ROOT / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2))
