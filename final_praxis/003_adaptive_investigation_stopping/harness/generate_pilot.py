"""Two disjoint infrastructure-only cases, frozen before the adapter pilot."""
try:
    from .cases import ROOT,canonical
except ImportError:
    from cases import ROOT,canonical

def main():
    cases=[]
    for i in range(2):
        cid=f"fp003-infrastructure-pilot-{i}"
        actual=f"pilot-actor-{i}";allowed=actual if i==0 else "different-pilot-actor"
        texts=["Inert infrastructure-check alert: an account accessed a test archive.",
            f"Signed audit: actual actor={actual}, asset=pilot-archive, minute=700; approval permits actor={allowed}, asset=pilot-archive, inclusive minute interval=690..710. Action executed; no simulation; no other approval or activity.",
            "A weak anomaly alert reported an unusual time; it is not an authoritative record.",
            "The target remained available.","No additional alert fired.","An unverified note says routine.",
            "Authentication succeeded, which alone does not establish approval.","The signed audit is unchanged."]
        cases.append({"case_id":cid,"family":"infrastructure_only","label":"benign" if i==0 else "malicious",
            "protected_high_impact":bool(i),"minimum_review_round":2,
            "evidence":[{"evidence_id":f"{cid}-e{r}","round":r,"text":text} for r,text in enumerate(texts,1)]})
    path=ROOT/"configs/pilot_cases.jsonl"
    if path.exists():raise FileExistsError("Pilot cases are already frozen.")
    path.write_bytes(b"".join(canonical(case) for case in cases));print("Frozen 2 separate infrastructure pilot cases")

if __name__=="__main__":main()
