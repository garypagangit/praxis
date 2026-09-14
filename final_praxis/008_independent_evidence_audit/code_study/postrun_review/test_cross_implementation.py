"""Authorship-independent synthetic integration of separately written arithmetic.

Only validator-authored records are passed to the frozen analysis functions;
no dataset or model-result files are read. Bootstrap regeneration remains outside
the postrun checker; this control checks interfaces and reported arithmetic.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import analysis
import offline_analysis
from statistical_checks import audit_statistics, REVIEWERS
from audit_results import sha_file


class CrossImplementationControl(unittest.TestCase):
    def test_nonempty_missing_and_paired_report_matches_separate_implementation(self):
        expected=[]
        for reviewer in REVIEWERS:
            for task in ("synthetic-a","synthetic-b"):
                for direction,y0,y1 in (("harmful",True,False),("useful",False,True)):
                    for arm in ("selected_w","uniform_w","uniform_a","hybrid","edit"):
                        expected.append(dict(task_id=task,split="heldout",cohort="native",reviewer=reviewer,
                            proposer=None,intent="native_"+direction,proposal_id=direction,arm=arm,replicate=0,
                            y0=y0,y1=y1,direction=direction,eligible=True,eligibility_reasons=[],
                            supplier_feasible=task=="synthetic-a",proposal_status="native",model_valid=True,
                            authenticated_failure=direction=="harmful" and arm=="hybrid",
                            decision="accept" if arm!="uniform_w" or direction=="useful" else "keep"))
        observed=copy.deepcopy(expected[1:])  # An explicitly missing assigned call.
        offline_expected=[]
        for task in ("synthetic-a","synthetic-b"):
            for replicate in range(20):
                for policy in ("fixed","uniform","edit","complement","hybrid"):
                    offline_expected.append(dict(task_id=task,split="heldout",cohort="native",proposer=None,
                        intent="native_harmful",proposal_id="harmful",direction="harmful",eligible=True,
                        eligibility_reasons=[],policy=policy,budget=8,replicate=replicate,
                        detected=(policy=="hybrid" or replicate%3==0),logical_supplier_executions=16,
                        logical_independent_executions=8,supplier_feasible=True))
        offline_observed=copy.deepcopy(offline_expected[1:])
        model=analysis.analyze(observed,REVIEWERS,expected_assignments=expected)
        acquisition=offline_analysis.analyze(offline_observed,expected_assignments=offline_expected)
        checks=audit_statistics(observed,expected,offline_observed,offline_expected,model,acquisition)
        failures=[check for check in checks if not check["passed"]]
        self.assertEqual(failures,[])
        self.assertGreater(len(checks),500)
        model["primary_hypotheses"][0]["holm4_adjusted_p"]=.123456
        corrupted=audit_statistics(observed,expected,offline_observed,offline_expected,model,acquisition)
        self.assertTrue(any(not check["passed"] and "holm4_adjusted_p" in check["check"] for check in corrupted))
        self.__class__.checks=len(checks)


if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CrossImplementationControl))
    report=dict(scope="Authorship-independent synthetic integration only; no main-study result files read",
                tests_run=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors),
                arithmetic_checks=getattr(CrossImplementationControl,"checks",None),
                failures=[str(t) for t,_ in result.failures],errors=[str(t) for t,_ in result.errors],
                source_sha256={name:sha_file(ROOT/name) for name in ("analysis.py","offline_analysis.py","postrun_review/statistical_checks.py")},
                control_sha256=sha_file(Path(__file__)))
    Path(__file__).with_name("CROSS_IMPLEMENTATION_REVIEW.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
