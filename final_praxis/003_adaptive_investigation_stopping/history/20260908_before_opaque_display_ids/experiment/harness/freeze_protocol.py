"""One-time pre-outcome seal; refuses to overwrite an existing freeze."""
import datetime
import json
try:
    from .cases import ROOT,canonical,digest
except ImportError:
    from cases import ROOT,canonical,digest

def main():
    destination=ROOT/"FROZEN_PROTOCOL.json"
    if destination.exists():raise FileExistsError("Protocol already frozen; use a dated amendment for changes.")
    paths=list((ROOT/"harness").glob("*.py"))+list((ROOT/"configs").glob("*.json"))+list((ROOT/"configs").glob("*.jsonl"))+[
        ROOT/"PREREGISTRATION_v1.md",ROOT/"NOVELTY_REVIEW.md",ROOT/"AMENDMENT_20260908_PRE_OUTCOME_OPERATIONAL_FREEZE.md",
        ROOT/"003_METHODS_AND_SAMPLE_SIZE_GATE_20260908.md",ROOT/"FIXTURE_GATE.json",ROOT/"artifacts/fixtures/traces.jsonl"]
    for path in paths:
        if not path.exists():raise FileNotFoundError(path)
    fixture=json.loads((ROOT/"FIXTURE_GATE.json").read_text())
    for rel,value in fixture["harness_sha256"].items():
        if digest(ROOT/rel)!=value:raise ValueError(f"Harness changed after fixture validation: {rel}")
    files={str(path.relative_to(ROOT)).replace('\\','/'):digest(path) for path in sorted(paths)}
    for name in ("model_adapter.py","inference_server.py"):
        files["../shared/"+name]=digest(ROOT.parent/"shared"/name)
    seal={"schema":"fp003-frozen-protocol-v1","experiment_id":"final-praxis-003",
          "frozen_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"pre_outcome":True,
          "scientific_outcomes_inspected":False,"files":files}
    destination.write_bytes(canonical(seal));print(json.dumps({"status":"FROZEN","sha256":digest(destination),"files":len(files)},indent=2))

if __name__=="__main__":main()
