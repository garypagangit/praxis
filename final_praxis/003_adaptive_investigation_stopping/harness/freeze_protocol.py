"""One-time pre-outcome seal; refuses to overwrite an existing freeze."""
import datetime
import json
import argparse
from pathlib import Path
try:
    from .cases import ROOT,canonical,digest
except ImportError:
    from cases import ROOT,canonical,digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--parent-freeze",type=Path);parser.add_argument("--amendment",type=Path)
    args=parser.parse_args()
    destination=ROOT/"FROZEN_PROTOCOL.json"
    if destination.exists():
        if not args.parent_freeze or not args.amendment:raise FileExistsError("Protocol already frozen; use a dated amendment for changes.")
        if digest(destination)!=digest(args.parent_freeze):raise ValueError("Historical parent freeze mismatch")
        if not args.amendment.resolve().is_relative_to(ROOT):raise ValueError("Amendment must belong to experiment")
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
    if args.amendment:files[args.amendment.resolve().relative_to(ROOT).as_posix()]=digest(args.amendment)
    seal={"schema":"fp003-frozen-protocol-v1","experiment_id":"final-praxis-003",
          "frozen_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"pre_outcome":True,
          "scientific_outcomes_inspected":False,"files":files}
    if args.parent_freeze:
        seal.update(schema="fp003-frozen-protocol-v2",parent_protocol_sha256=digest(args.parent_freeze),
                    amendment=args.amendment.resolve().relative_to(ROOT).as_posix(),
                    prior_pilot_eligible_for_discovery=False)
    destination.write_bytes(canonical(seal));print(json.dumps({"status":"FROZEN","sha256":digest(destination),"files":len(files)},indent=2))

if __name__=="__main__":main()
