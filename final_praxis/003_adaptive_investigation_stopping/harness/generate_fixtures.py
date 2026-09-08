"""Eighty artificial traces, labelled exclusively as fixture evidence."""
import json
try:
    from .cases import ROOT, canonical
except ImportError:
    from cases import ROOT, canonical

PATTERNS={
 "stable_correct":["benign"]*8,
 "stable_wrong":["malicious"]*8,
 "correct_to_wrong":["benign"]*3+["malicious"]*5,
 "wrong_to_correct":["malicious"]*3+["benign"]*5,
 "oscillation":["benign","malicious"]*4,
 "protected_review":["benign"]*8,
 "low_evidence_review":["benign"]*8,
 "refusal_abstain":["abstain"]*8,
}

def fixtures():
    result=[]
    for family,pattern in PATTERNS.items():
        for i in range(10):
            cid=f"fixture-{family}-{i}"
            case={"case_id":cid,"family":family,"label":"benign",
                  "protected_high_impact":family=="protected_review",
                  "minimum_review_round":4 if family=="low_evidence_review" else 2,
                  "evidence":[{"evidence_id":f"{cid}-e{r}","round":r,"text":"inert fixture"} for r in range(1,9)]}
            trace=[{"case_id":cid,"round":r,"evidence_ids":[e["evidence_id"] for e in case["evidence"][:r]],
                    "disposition":answer,"raw_response":json.dumps({"disposition":answer}),
                    "correct":answer=="benign","token_count":10+r,"evidence_kind":"fixture"}
                   for r,answer in enumerate(pattern,1)]
            result.append({"case":case,"trace":trace,"evidence_kind":"fixture"})
    return result

if __name__ == "__main__":
    path=ROOT/"artifacts/fixtures/traces.jsonl";path.parent.mkdir(parents=True,exist_ok=True)
    data=b"".join(canonical(row) for row in fixtures())
    if path.exists() and path.read_bytes()!=data:raise FileExistsError("Existing fixtures differ.")
    path.write_bytes(data);print(f"80 fixture traces: {path}")
