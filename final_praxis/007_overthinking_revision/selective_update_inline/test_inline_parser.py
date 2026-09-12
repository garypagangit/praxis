"""No inference: focused regression tests for the prospective inline amendment."""
import copy
import inspect
import json
import unittest
from inline_parser import parse_inline_terminal, rescore_inline_terminal

class InlineTerminalTests(unittest.TestCase):
    def parse(self,text,truncated=False):
        return parse_inline_terminal(text,truncated=truncated)["answer"]
    def test_exact_original_newline_and_start_forms(self):
        for label in ("TRUE","FALSE"):
            for text in ("FINAL: "+label, "A short explanation.\nFINAL: "+label,
                         "A short explanation.\nFINAL: "+label+"\n\n"):
                with self.subTest(text=text):self.assertEqual(self.parse(text),label)
    def test_unique_inline_whitespace_marker(self):
        for label in ("TRUE","FALSE"):
            for whitespace in (" ","\t","\r","\v","\u00a0"):
                text="One sentence."+whitespace+"FINAL: "+label
                with self.subTest(text=repr(text)):
                    result=parse_inline_terminal(text)
                    self.assertEqual(result["answer"],label)
                    self.assertEqual(result["boundary"],"whitespace")
                    self.assertIn("terminal_whitespace_boundary",result["normalization"])
    def test_inline_and_original_balanced_wrapper_whitelist(self):
        wrappers=(("**","**"),("`","`"),("``","``"),("**`","`**"),
                  ("**``","``**"),("`**","**`"),("``**","**``"))
        for left,right in wrappers:
            for prefix in ("","Explanation. ","Explanation.\n"):
                text=prefix+left+"FINAL: FALSE"+right
                with self.subTest(text=text):
                    result=parse_inline_terminal(text)
                    self.assertEqual(result["answer"],"FALSE")
                    self.assertEqual(result["normalized_text"],prefix+"FINAL: FALSE")
    def test_truncation_is_never_repaired(self):
        for text in ("FINAL: TRUE","Explanation. FINAL: TRUE","Explanation. **FINAL: FALSE**"):
            self.assertIsNone(self.parse(text,truncated=True))
            self.assertEqual(parse_inline_terminal(text,truncated=True)["invalid_reason"],"truncated")
    def test_internal_marker_not_at_end_is_rejected(self):
        for text in ("FINAL: TRUE followed by explanation",
                     "Explanation FINAL: TRUE. More words",
                     "Explanation FINAL: TRUE.","FINAL: FALSE!","FINAL: TRUE\nConclusion"):
            with self.subTest(text=text):self.assertIsNone(self.parse(text))
    def test_multiple_marker_variants_are_rejected(self):
        for text in ("FINAL: TRUE\nFINAL: FALSE",
                     "Earlier FINAL: FALSE and now FINAL: TRUE",
                     "Earlier Final : FALSE. FINAL: TRUE",
                     "FINAL\n: FALSE. **FINAL: TRUE**"):
            with self.subTest(text=text):self.assertIsNone(self.parse(text))
    def test_nonwhitespace_prefix_is_not_a_boundary(self):
        for prefix in ("word","(",":","/",'"',"\u200b"):
            with self.subTest(prefix=prefix):self.assertIsNone(self.parse(prefix+"FINAL: TRUE"))
    def test_malformed_or_unlisted_wrappers_are_rejected(self):
        for text in ("**FINAL: TRUE","FINAL: TRUE**","***FINAL: TRUE***",
                     "_FINAL: TRUE_","[FINAL: TRUE]","```FINAL: TRUE```",
                     "**FINAL: TRUE`","Explanation. **FINAL: TRUE** extra"):
            with self.subTest(text=text):self.assertIsNone(self.parse(text))
    def test_case_colon_spacing_and_label_vocabulary_unchanged(self):
        for marker in ("final: TRUE","Final: FALSE","FINAL: true","FINAL : TRUE",
                       "FINAL:TRUE","FINAL:  TRUE","FINAL: A","FINAL: MAYBE","FINAL: TRUE/FALSE"):
            with self.subTest(marker=marker):self.assertIsNone(self.parse("Explanation. "+marker))
    def test_single_whole_json_string_decode_preserved(self):
        text=json.dumps("A sentence. **FINAL: FALSE**")
        result=parse_inline_terminal(text)
        self.assertEqual(result["answer"],"FALSE")
        self.assertIn("json_string_decoded_once",result["normalization"])
        self.assertIsNone(self.parse(json.dumps(json.dumps("FINAL: FALSE"))))
        self.assertIsNone(self.parse(json.dumps({"answer":"FINAL: FALSE"})))
    def test_no_implicit_or_gold_assisted_extraction(self):
        self.assertEqual(set(inspect.signature(parse_inline_terminal).parameters),{"text","truncated"})
        for text in ("TRUE","The answer is FALSE.",'{"answer":"TRUE"}',"","","No answer"):
            with self.subTest(text=text):self.assertIsNone(self.parse(text))
    def test_rescore_retains_original_decision_usage_and_does_not_mutate(self):
        old={"answer":None,"truncated":False,"finish_reason":"end_turn","output_tokens":41,
             "normalized_text":"A sentence. FINAL: TRUE","normalization":[]}
        saved=copy.deepcopy(old)
        result=rescore_inline_terminal("A sentence. FINAL: TRUE",old)
        self.assertEqual(old,saved);self.assertEqual(result["original_answer"],None)
        self.assertEqual(result["answer"],"TRUE");self.assertEqual(result["output_tokens"],41)
        self.assertEqual(result["finish_reason"],"end_turn");self.assertFalse(result["truncated"])
    def test_rescore_requires_original_truncation_flag(self):
        for old in ({},{"truncated":None},{"truncated":"False"},{"truncated":0}):
            with self.subTest(old=old),self.assertRaises(ValueError):
                rescore_inline_terminal("FINAL: TRUE",old)
    def test_recorded_truncation_and_original_answer_are_retained(self):
        old={"answer":None,"truncated":True,"finish_reason":"max_tokens","output_tokens":256}
        result=rescore_inline_terminal("An answer. FINAL: TRUE",old)
        self.assertIsNone(result["answer"]);self.assertTrue(result["truncated"])
        self.assertEqual(result["finish_reason"],"max_tokens")
    def test_whitespace_only_indentation_is_formatting_only(self):
        self.assertEqual(self.parse("  FINAL: FALSE"),"FALSE")
        self.assertEqual(self.parse("Explanation.\n\tFINAL: TRUE"),"TRUE")

if __name__=="__main__":unittest.main()

