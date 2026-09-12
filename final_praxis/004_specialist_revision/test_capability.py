"""Pure unit tests; fake responses are protocol tests, never experiment results."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import capability as cap


BASE = {"sympy/a.py":"def value():\n    return 1\n",
        "sympy/__init__.py":'"""SymPy."""\n'}
ISSUE = {"instance_id":"sympy__sympy-unit","repo":"sympy/sympy",
         "base_commit":"a"*40,"problem_statement":"Fix value returning one."}


def response(action, finish="end_turn"):
    return {"text":json.dumps(action),"finish_reason":finish}


class FakeCalls:
    def __init__(self, values):
        self.values=list(values)
        self.messages=[]

    def call(self,key,messages):
        self.messages.append(copy.deepcopy(messages))
        return self.values.pop(0)


class SourceTests(unittest.TestCase):
    def test_read_exact_raw_source(self):
        result=cap.SourceAccess(BASE).dispatch(
            {"action":"read","path":"sympy/a.py","start_line":1,"end_line":2})
        self.assertEqual(result["source"],BASE["sympy/a.py"])
        self.assertEqual(result["start_line"],1)

    def test_literal_search_and_bounded_list(self):
        access=cap.SourceAccess(BASE)
        self.assertEqual(access.dispatch({"action":"search","query":"return 1"})["matches"][0]["path"],
                         "sympy/a.py")
        self.assertEqual(access.dispatch({"action":"search","query":"return.*"})["matches"],[])
        self.assertEqual(len(access.dispatch({"action":"list","limit":1})["paths"]),1)

    def test_denied_paths_and_large_window(self):
        access=cap.SourceAccess(BASE)
        for action in [
            {"action":"read","path":"../secret","start_line":1,"end_line":1},
            {"action":"read","path":"sympy/a.py","start_line":1,"end_line":201},
            {"action":"shell","command":"echo x"},
        ]:
            with self.assertRaises(ValueError):
                access.dispatch(action)

    def test_response_bound_explicit_truncation(self):
        source={"sympy/a.py":"x = 1234567890\n"*200}
        result=cap.SourceAccess(source).dispatch(
            {"action":"read","path":"sympy/a.py","start_line":1,"end_line":200},cap=600)
        self.assertLessEqual(len(cap.encode(result)),600)
        self.assertTrue(result["truncated"])
        self.assertLess(result["end_line"],200)

    def test_private_issue_fields_rejected(self):
        with self.assertRaises(ValueError):
            cap.initial_messages(dict(ISSUE,patch="REFERENCE"),cap.SourceAccess(BASE))


class TrajectoryTests(unittest.TestCase):
    def test_invalid_edit_then_exact_repair_preserves_history(self):
        wrong={"action":"submit","decision":"REVISE","edits":[
            {"path":"sympy/a.py","old":"return  1","new":"return 2"}]}
        right={"action":"submit","decision":"REVISE","edits":[
            {"path":"sympy/a.py","old":"return 1","new":"return 2"}]}
        fake=FakeCalls([response(wrong),response(
            {"action":"read","path":"sympy/a.py","start_line":1,"end_line":2}),response(right)])
        with tempfile.TemporaryDirectory() as tmp:
            record=cap.solve_issue(ISSUE,BASE,fake,Path(tmp))
        self.assertTrue(record["submitted"])
        self.assertEqual(record["model_responses"],3)
        self.assertIn("-    return 1",record["candidate"]["patch"])
        history=fake.messages[1]
        self.assertEqual(history[-2]["content"],json.dumps(wrong))
        self.assertIn("exactly once",history[-1]["content"])
        self.assertIsNone(record["verification"])
        self.assertIsNone(record["scientific_resolution"])

    def test_six_access_turns_are_no_candidate_not_wrong(self):
        fake=FakeCalls([response({"action":"list"}) for _ in range(6)])
        with tempfile.TemporaryDirectory() as tmp:
            record=cap.solve_issue(ISSUE,BASE,fake,Path(tmp))
        self.assertFalse(record["submitted"])
        self.assertEqual(record["terminal_status"],"no_final_submission")
        self.assertEqual(record["model_responses"],6)
        self.assertIsNone(record["candidate"])
        self.assertIsNone(record["scientific_resolution"])

    def test_truncated_submission_not_accepted(self):
        keep={"action":"submit","decision":"KEEP","edits":[]}
        fake=FakeCalls([response(keep,"max_tokens"),response(keep)])
        with tempfile.TemporaryDirectory() as tmp:
            record=cap.solve_issue(ISSUE,BASE,fake,Path(tmp))
        self.assertTrue(record["submitted"])
        self.assertEqual(record["model_responses"],2)
        self.assertEqual(record["events"][0]["status"],"invalid_action_or_edit")
        self.assertIn("Truncated",record["events"][0]["operation_result"]["error"])


if __name__=="__main__":
    unittest.main()

