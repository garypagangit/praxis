import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eligibility import EvidenceContext, check_eligibility
from make_fixture import fixture
from replay import FIXTURE_SCOPE, evaluate
from scorers import LinearSVMScorer


class ReplayTests(unittest.TestCase):
    def test_finite_denominators_and_predicate_veto(self):
        data = fixture()
        result, decisions = evaluate(data)
        self.assertEqual(result["calibration_attack_records"], 300)
        self.assertEqual(len(decisions), 200)
        for decision in decisions:
            self.assertFalse(decision["keep_all"])
            if not decision["eligible"]:
                self.assertFalse(decision["pac_score_and_predicates"])
        for name, metric in result["metrics"].items():
            count = sum(row[name] and row["attack"] for row in decisions)
            self.assertEqual(metric["empirical_attack_suppression_fraction"], count/100)
            self.assertEqual(metric["test_non_attack_count"], 100)
        self.assertFalse(result["simultaneous_certification"])

    def test_leakage_nonfinite_and_false_scope_are_rejected(self):
        original = fixture()
        changes = (
            lambda d: d.update(scope="REAL_DATA"),
            lambda d: d["records"][-1].update(group_id=d["records"][0]["group_id"]),
            lambda d: d["records"][-1].update(record_id=d["records"][0]["record_id"]),
            lambda d: d["records"][0].update(benignness=float("nan")),
            lambda d: d["records"][0].update(eligible="False"),
        )
        for change in changes:
            data = copy.deepcopy(original)
            change(data)
            with self.assertRaises(ValueError):
                evaluate(data)

    def test_scorer_evidence_and_replay_connect(self):
        # Intentionally repetitive, separable software fixture; NEVER evidence
        # for independence, attack detection, or SOC utility.
        benign = {"req_body": "scheduled health check", "method": "GET"}
        attack = {"req_body": "malicious exploit payload", "method": "POST"}
        scorer = LinearSVMScorer().fit([benign]*4+[attack]*4, [0]*4+[1]*4)
        benign_score, attack_score = scorer.score([benign, attack])
        evidence = {"host": "h", "user": "u", "rule_id": "r", "severity": "low",
                    "timestamp": "2026-09-20T00:00:00+00:00"}
        context = EvidenceContext(raw_event=evidence, independent_source_verified=True,
                                  raw_reference="fixture", allowed_rule_ids=frozenset({"r"}),
                                  incident_context_complete=True, cluster_member=False)
        eligible = check_eligibility(evidence, context)["eligible"]
        records = [{"record_id": f"cal-{i}", "group_id": f"cal-{i}", "role": "calibration",
                    "attack": True, "eligible": eligible, "benignness": float(attack_score)}
                   for i in range(299)]
        for i, is_attack, score, is_eligible in ((0, True, attack_score, True),
                                                (1, False, benign_score, True),
                                                (2, False, benign_score, False)):
            records.append({"record_id": f"test-{i}", "group_id": f"test-{i}", "role": "test",
                            "attack": is_attack, "eligible": is_eligible, "benignness": float(score)})
        document = {"scope": FIXTURE_SCOPE, "scorer_contract": scorer.metadata(),
                    "predicate_contract": {"fixture": True}, "records": records}
        _, decisions = evaluate(document)
        self.assertEqual([r["pac_score_and_predicates"] for r in decisions], [False, True, False])


if __name__ == "__main__":
    unittest.main()
