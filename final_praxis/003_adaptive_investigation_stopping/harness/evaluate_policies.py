"""Paired policy analysis; synthetic fixtures can never obtain a scientific label."""
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta
try:
    from .policies import ARMS, select
except ImportError:
    from policies import ARMS, select

def cp_upper(k, n):
    return 1.0 if k == n else float(beta.ppf(.95, k + 1, n - k))

def cp_interval(k, n):
    if not n:
        return [None, None]
    return [0.0 if k == 0 else float(beta.ppf(.025, k, n-k+1)),
            1.0 if k == n else float(beta.ppf(.975, k+1, n-k))]

def analyze(cases, traces, scientific=False):
    rows = []
    for case in cases:
        trace = traces[case["case_id"]]
        truth = [x["disposition"] == case["label"] for x in trace]
        transitions = [r for r in range(7) if truth[r] and not truth[r+1]]
        row = {"case_id": case["case_id"], "family": case["family"],
               "degradation_events": len(transitions), "degradation_case": bool(transitions), "arms": {}}
        for arm in ARMS:
            selected = select(case, trace, arm)
            correct = selected["disposition"] == case["label"]
            later = truth[selected["round"]:]
            row["arms"][arm] = {**selected, "correct": correct,
                "harm": not correct and any(later),
                "prevented": bool(transitions) and correct and any(not value for value in later)}
        rows.append(row)
    n = len(rows)
    summaries = {}
    d = sum(row["degradation_case"] for row in rows)
    for arm in ARMS:
        vals = [row["arms"][arm] for row in rows]
        harm = sum(value["harm"] for value in vals)
        prevented = sum(value["prevented"] for value in vals)
        summaries[arm] = {
            "n": n, "correct": sum(value["correct"] for value in vals),
            "accuracy": sum(value["correct"] for value in vals)/n,
            "harm_cases": harm, "harm_rate": harm/n, "harm_upper_95": cp_upper(harm,n),
            "harm_gate": harm/n <= .02 and cp_upper(harm,n) <= .04,
            "prevented_cases": prevented, "prevention_rate": prevented/d if d else None,
            "prevention_ci_95": cp_interval(prevented,d),
            "review_rate": sum(value["reviewed"] for value in vals)/n,
            "abstain_rate": sum(value["abstained"] for value in vals)/n,
            "mean_rounds": sum(value["round"] for value in vals)/n,
            "total_tokens": sum(value["token_count"] for value in vals),
        }
    rng = np.random.default_rng(20260908)
    indices = rng.integers(0,n,size=(10000,n))
    correctness = {arm: np.array([int(row["arms"][arm]["correct"]) for row in rows]) for arm in ARMS}
    a4_round = np.array([row["arms"]["A4"]["round"] for row in rows])
    a4_tokens = np.array([row["arms"]["A4"]["token_count"] for row in rows])
    a1_tokens = np.array([row["arms"]["A1"]["token_count"] for row in rows])
    noninferiority = {arm: {"difference": float(np.mean(correctness["A4"]-correctness[arm])),
        "lower_97_5": float(np.quantile((correctness["A4"]-correctness[arm])[indices].mean(axis=1),.025))}
        for arm in ("A0","A1")}
    for arm in ARMS:
        summaries[arm]["round_saving"] = 1-summaries[arm]["mean_rounds"]/8
        summaries[arm]["token_saving"] = 1-summaries[arm]["total_tokens"]/summaries["A1"]["total_tokens"]
    a4,a2 = summaries["A4"],summaries["A2"]
    equivalent = abs(a4["accuracy"]-a2["accuracy"]) <= .01 and \
        abs(a4["token_saving"]-a2["token_saving"]) <= .05 and \
        abs(a4["round_saving"]-a2["round_saving"]) <= .05 and a4["harm_gate"] == a2["harm_gate"]
    gates = {"sample_400": n == 400,
             "H1_noninferiority": all(v["lower_97_5"] >= -.02 for v in noninferiority.values()),
             "H2_cost_reduction": a4["round_saving"] >= .20 and a4["token_saving"] >= .20,
             "H3_prevention": d > 0 and a4["prevention_rate"] >= .25,
             "H4_harm": a4["harm_gate"], "review_rate": a4["review_rate"] <= .20,
             "phenomenon_20": sum(row["degradation_events"] for row in rows) >= 20,
             "A4_not_equivalent_to_A2": not equivalent}
    label = "Bounded Positive" if all(gates.values()) else "Mixed" if equivalent and all(v for k,v in gates.items() if k != "A4_not_equivalent_to_A2") else "Negative"
    if not scientific:
        label = "FIXTURE_ONLY"
    elif n != 400:
        label = "Protocol Invalid"
    return {"classification": label,"scientific":scientific,"n":n,"degradation_cases":d,
            "degradation_events":sum(row["degradation_events"] for row in rows),
            "arms":summaries,"gates":gates,"noninferiority":noninferiority,
            "round_saving_ci_95":np.quantile(1-a4_round[indices].mean(axis=1)/8,[.025,.975]).tolist(),
            "token_saving_ci_95":np.quantile(1-a4_tokens[indices].sum(axis=1)/a1_tokens[indices].sum(axis=1),[.025,.975]).tolist(),
            "family_breakdown":{family:{"n":sum(row["family"]==family for row in rows),
                "a4_correct":sum(row["arms"]["A4"]["correct"] for row in rows if row["family"]==family)}
                for family in sorted({row["family"] for row in rows})}, "case_results":rows}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    receipt=json.loads((args.run_dir/"RUN_COMPLETE.json").read_text())
    pilot=receipt.get("run_kind")=="infrastructure_pilot"
    cases=[json.loads(line) for line in (root/("configs/pilot_cases.jsonl" if pilot else "configs/cases.jsonl")).read_text().splitlines()]
    if receipt.get("evidence_kind") != "real_model_inference":
        raise ValueError("Scientific analysis requires real inference receipt.")
    traces={case["case_id"]:[] for case in cases}
    for line in (args.run_dir/"raw.jsonl").read_text().splitlines():
        row=json.loads(line);traces[row["case_id"]].append(row)
    for trace in traces.values():trace.sort(key=lambda row:row["round"])
    result=analyze(cases,traces,scientific=not pilot)
    if pilot:result.update(classification="INFRASTRUCTURE_PILOT_ONLY",run_kind="infrastructure_pilot")
    path=args.run_dir/"analysis.json"
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:value for key,value in result.items() if key != "case_results"},indent=2))

if __name__ == "__main__":main()
