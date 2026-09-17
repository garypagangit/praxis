"""Direct paired recount from public observations; imports no study analysis code."""
import collections
import datetime
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform

REPO = Path(__file__).resolve().parents[4]
STUDY = REPO / "final_praxis/008_independent_evidence_audit/code_study"
PACKAGE = STUDY / "completed_models/schema_extension_v2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path):
    return [json.loads(row) for row in gzip.decompress(path.read_bytes()).splitlines() if row]


def main():
    rows = load_rows(PACKAGE / "DECISIONS.jsonl.gz")
    model = json.loads((PACKAGE / "MODEL_RESULTS.json").read_text(encoding="utf-8"))
    reviewers = ["qwen.qwen3-coder-next", "mistral.devstral-2-123b"]
    primary = []
    generated = []
    for reviewer in reviewers:
        for hypothesis, left, right, enforced in [("H1", "selected_w", "uniform_w", False),
                                                   ("H2", "uniform_a", "hybrid", True)]:
            arms = {}
            for arm in [left, right]:
                selected = [r for r in rows if r["eligible"] and r["cohort"] == "native"
                            and r["split"] == "heldout" and r["direction"] == "harmful"
                            and r["replicate"] == 0 and r["reviewer"] == reviewer and r["arm"] == arm]
                assert len(selected) == len({r["task_id"] for r in selected}) == 101
                arms[arm] = {r["task_id"]: bool(r["model_valid"] and r["decision"] == "accept"
                                              and (not enforced or not r["authenticated_failure"])) for r in selected}
            assert set(arms[left]) == set(arms[right])
            paired = collections.Counter((arms[left][task], arms[right][task]) for task in arms[left])
            plus, minus = paired[(True, False)], paired[(False, True)]
            n = plus + minus
            p = Fraction(sum(math.comb(n, j) for j in range(plus, n + 1)), 2**n)
            count_left, count_right = sum(arms[left].values()), sum(arms[right].values())
            primary.append(dict(hypothesis=hypothesis, reviewer=reviewer, left=left, right=right,
                                layer="enforced" if enforced else "reviewer_only", tasks=101,
                                left_accepts=count_left, right_accepts=count_right,
                                paired_cells=dict(both_accept=paired[(True, True)], left_only_accept=plus,
                                                  right_only_accept=minus, neither_accept=paired[(False, False)]),
                                exact_effect=str(Fraction(count_left-count_right,101)),
                                effect=float(Fraction(count_left-count_right,101)),
                                exact_one_sided_p=str(p), raw_one_sided_p=float(p)))
        arms = {}
        for arm in ["selected_w", "uniform_w"]:
            selected = [r for r in rows if r["eligible"] and r["cohort"] == "generated"
                        and r["split"] == "heldout" and r["direction"] == "harmful"
                        and r["replicate"] == 0 and r["reviewer"] == reviewer and r["arm"] == arm]
            assert len(selected) == len({r["task_id"] for r in selected}) == 34
            arms[arm] = {r["task_id"]: bool(r["model_valid"] and r["decision"] == "accept") for r in selected}
        assert arms["selected_w"] == arms["uniform_w"]
        generated.append(dict(reviewer=reviewer, harmful_tasks=34,
                              selected_accepts=sum(arms["selected_w"].values()),
                              uniform_accepts=sum(arms["uniform_w"].values()), discordances=0))
    ordered = sorted(range(4), key=lambda i: primary[i]["raw_one_sided_p"])
    previous = 0.0
    for rank, index in enumerate(ordered):
        previous = max(previous, min(1.0, (4-rank)*primary[index]["raw_one_sided_p"]))
        primary[index]["holm4_adjusted_p"] = previous
    for row in primary:
        published = next(r for r in model["primary_hypotheses"]
                         if r["hypothesis"] == row["hypothesis"] and r["reviewer"] == row["reviewer"])
        assert row["effect"] == published["difference"]
        assert row["raw_one_sided_p"] == published["raw_one_sided_exact_p"]
        assert row["holm4_adjusted_p"] == published["holm4_adjusted_p"]
    cohort = [r for r in rows if r["eligible"] and r["cohort"] == "generated"
              and r["split"] == "heldout" and r["replicate"] == 0
              and r["reviewer"] == reviewers[0] and r["arm"] == "selected_w"]
    assert len(cohort) == len({r["proposal_id"] for r in cohort}) == 193
    assert len({r["task_id"] for r in cohort}) == 100
    directions = dict(collections.Counter(r["direction"] for r in cohort))
    assert directions == {"harmful":34, "useful":90, "other":69}
    native = [r for r in rows if r["eligible"] and r["cohort"] == "native" and r["split"] == "heldout"
              and r["direction"] == "harmful" and r["replicate"] == 0 and r["reviewer"] == reviewers[0]
              and r["arm"] == "selected_w"]
    feasible = sum(r["supplier_feasible"] for r in native)
    assert feasible == 60
    receipt = dict(status="PASS", checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   independent_of_study_analysis_imports=True, model_calls=0, candidate_programs_executed=0,
                   python=platform.python_version(), primary=primary, generated_harmful_disclosure=generated,
                   generated_heldout=dict(admitted_proposals=193, source_tasks=100, directions=directions),
                   native_two_passing_witnesses_feasible=dict(numerator=feasible, denominator=101),
                   input_sha256={str(p.relative_to(REPO)).replace("\\", "/"):sha(p) for p in
                                 [PACKAGE / "DECISIONS.jsonl.gz",PACKAGE / "MODEL_RESULTS.json"]},
                   script_sha256=sha(Path(__file__)),
                   limitations="Recounts retained observations, not new inference, bootstrap intervals, prompt replay, or semantic reexecution.")
    output = Path(__file__).parent / "INDEPENDENT_RECOUNT.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status":"PASS","primary_hypotheses":4,"generated_contrasts":2,"model_calls":0}))


if __name__ == "__main__":
    main()
