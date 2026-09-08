"""Meaningful end-to-end policy fixtures and adversarial verifier mutations."""
import copy
import json
try:
    from .cases import ROOT,canonical,digest,build_cases
    from .generate_fixtures import fixtures
    from .evaluate_policies import analyze,cp_upper
    from .independent_verify import verify_data
    from .trace_schema import disposition,validate_trace
    from .run_traces import messages_for
except ImportError:
    from cases import ROOT,canonical,digest,build_cases
    from generate_fixtures import fixtures
    from evaluate_policies import analyze,cp_upper
    from independent_verify import verify_data
    from trace_schema import disposition,validate_trace
    from run_traces import messages_for

def main():
    data=fixtures();cases=[row["case"] for row in data];traces={row["case"]["case_id"]:row["trace"] for row in data}
    for row in data:validate_trace(row["case"],row["trace"])
    result=analyze(cases,traces)
    assert result["classification"]=="FIXTURE_ONLY"
    assert result["arms"]["A2"]["harm_cases"]==10
    assert result["arms"]["A2"]["prevented_cases"]==10
    assert result["arms"]["A4"]["harm_cases"]==10
    assert result["arms"]["A4"]["review_rate"]==.5
    assert result["arms"]["A4"]["abstain_rate"]==.375
    assert result["degradation_events"]==50 and result["degradation_cases"]==20
    assert result==analyze(cases,traces),"nondeterministic replay"
    assert cp_upper(0,400)<.04 and cp_upper(8,400)<.04 and cp_upper(9,400)>.02
    verify_data(cases,traces,result)
    rejected=0
    for mutation in ("remove_round","duplicate_case","change_review","hide_harm","wrong_tokens","evidence_order","fabricated_positive","gate_tamper"):
        broken_cases=copy.deepcopy(cases);broken_traces=copy.deepcopy(traces);broken_result=copy.deepcopy(result)
        cid=cases[0]["case_id"]
        if mutation=="remove_round":broken_traces[cid].pop()
        elif mutation=="duplicate_case":broken_cases[-1]=broken_cases[0]
        elif mutation=="change_review":broken_result["case_results"][50]["arms"]["A4"]["reviewed"]=False
        elif mutation=="hide_harm":broken_result["arms"]["A4"]["harm_cases"]=0
        elif mutation=="wrong_tokens":broken_traces[cid][0]["token_count"]=-1
        elif mutation=="evidence_order":broken_traces[cid][2]["evidence_ids"].reverse()
        elif mutation=="fabricated_positive":broken_result["classification"]="Bounded Positive"
        elif mutation=="gate_tamper":broken_result["gates"]["H4_harm"]=not broken_result["gates"]["H4_harm"]
        try:verify_data(broken_cases,broken_traces,broken_result)
        except AssertionError:rejected+=1
    assert rejected==8
    for text in ("I cannot answer", "{}", '[1]', '{"disposition":"unknown"}', 'benign'):
        assert disposition(text)=="abstain"
    display_ids=set()
    for case in build_cases():
        messages=messages_for(case,8,[])
        payload=json.loads(messages[1]["content"])
        assert case["case_id"] not in messages[1]["content"]
        assert set(payload)=={"round","maximum_rounds","evidence","previous_dispositions"}
        for raw,shown in zip(case["evidence"],payload["evidence"]):
            assert raw["evidence_id"] not in messages[1]["content"]
            assert len(shown["id"])==16 and all(c in "0123456789abcdef" for c in shown["id"])
            assert shown["id"] not in display_ids
            display_ids.add(shown["id"])
    assert len(display_ids)==3200
    path=ROOT/"artifacts/fixtures/traces.jsonl";path.parent.mkdir(parents=True,exist_ok=True)
    payload=b"".join(canonical(row) for row in data)
    if path.exists() and path.read_bytes()!=payload:raise FileExistsError(path)
    path.write_bytes(payload)
    files={str(file.relative_to(ROOT)).replace('\\','/'):digest(file) for file in sorted((ROOT/"harness").glob("*.py"))}
    marker={"status":"PASS","evidence_kind":"fixture_only","traces":80,"rounds":640,
            "families":8,"malformed_responses_checked":5,"adversarial_mutations_rejected":rejected,
            "fixture_sha256":digest(path),"harness_sha256":files,"opaque_display_ids_verified":3200}
    (ROOT/"FIXTURE_GATE.json").write_bytes(canonical(marker))
    (ROOT/"FIXTURE_GATE.md").write_text("# Fixture gate\n\nPASS: 80 synthetic traces / 640 rounds across eight trajectory families; "
        "eight corrupted inputs rejected; five malformed/refused responses count as abstentions; deterministic replay and independent counters pass. "
        "All 3,200 visible evidence IDs are unique opaque hashes; indexed private IDs and ground-truth fields are absent from model payloads. "
        "These are fixture checks, not scientific model results.\n",encoding="utf-8")
    print(json.dumps(marker,indent=2))

if __name__=="__main__":main()
