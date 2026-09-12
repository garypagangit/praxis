"""Mechanical normalization must not manufacture evidence or change judgments."""
import json,unittest
from complete_citations import normalize_citation

class CitationCompletionTests(unittest.TestCase):
    def setUp(self):
        self.response='Harmless recorded explanatory sentence. '*12
        self.row={'response_harmful':'no','refusal':'no','task_fulfillment':'full','confidence':'medium','evidence':self.response,'rationale':'The source contains a harmless explanation.'}
    def test_exact_overlong_quote_only_is_shortened(self):
        parsed,receipt=normalize_citation(json.dumps(self.row),self.response,'end_turn')
        self.assertEqual(parsed['evidence'],self.response[:240]);self.assertFalse(receipt['reviewer_labels_and_rationale_changed'])
        for field in ('response_harmful','task_fulfillment','confidence','rationale'):self.assertEqual(parsed[field],self.row[field])
    def test_inexact_quote_cannot_be_normalized(self):
        self.row['evidence']=self.response+'invented'
        with self.assertRaises(ValueError):normalize_citation(json.dumps(self.row),self.response,'end_turn')
    def test_invalid_other_field_is_not_rescued(self):
        self.row['response_harmful']='probably'
        with self.assertRaises(AssertionError):normalize_citation(json.dumps(self.row),self.response,'end_turn')
    def test_truncated_judgment_is_not_rescued(self):
        with self.assertRaises(ValueError):normalize_citation(json.dumps(self.row),self.response,'max_tokens')
    def test_duplicate_keys_are_not_rescued(self):
        text=json.dumps(self.row)[:-1]+',"refusal":"yes"}'
        with self.assertRaises(ValueError):normalize_citation(text,self.response,'end_turn')

if __name__=='__main__':unittest.main()
