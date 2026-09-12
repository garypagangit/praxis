import hashlib, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from final_praxis.shared_20260912.bedrock_adapter import BedrockAdapter, BudgetLedger, BudgetExceeded

class Client:
    def __init__(self): self.calls=0
    def converse(self, **body):
        self.calls+=1
        return {'usage':{'inputTokens':20,'outputTokens':5},'output':{'message':{'content':[{'text':'answer'}]}},'stopReason':'end_turn'}

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.prereg=self.root/'prereg.md';self.prereg.write_text('RQ and frozen protocol',encoding='utf-8')
        self.env={'PRAXIS_PREREG_PATH':str(self.prereg),'PRAXIS_PREREG_SHA256':hashlib.sha256(self.prereg.read_bytes()).hexdigest()}
        self.client=Client()
    def tearDown(self):self.tmp.cleanup()
    def adapter(self,limit=1):
        return BedrockAdapter('qwen.qwen3-coder-next',client=self.client,receipt_dir=self.root/'calls',ledger=BudgetLedger(self.root/'budget.json',limit))
    def test_requires_unchanged_preregistration(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):self.adapter()
        with patch.dict(os.environ,self.env):
            self.prereg.write_text('changed',encoding='utf-8')
            with self.assertRaises(ValueError):self.adapter()
        self.assertEqual(self.client.calls,0)
    def test_resume_does_not_spend_again_and_content_mismatch_fails(self):
        with patch.dict(os.environ,self.env):
            a=self.adapter();first=a.generate([{'role':'user','content':'question'}],request_id='stable')
            resumed=a.generate([{'role':'user','content':'question'}],request_id='stable')
            self.assertEqual(first['text'],resumed['text']);self.assertTrue(resumed['recovered_from_cache'])
            with self.assertRaises(ValueError):a.generate([{'role':'user','content':'different'}],request_id='stable')
        self.assertEqual(self.client.calls,1)
    def test_budget_prevents_model_call(self):
        with patch.dict(os.environ,self.env):
            a=self.adapter(limit=0.000001)
            with self.assertRaises(BudgetExceeded):a.generate([{'role':'user','content':'question'}],request_id='over-budget')
        self.assertEqual(self.client.calls,0)
    def test_network_error_retains_uncertain_reservation(self):
        with patch.dict(os.environ,self.env):
            a=self.adapter()
            with patch.object(self.client,'converse',side_effect=TimeoutError('network')):
                with self.assertRaises(TimeoutError):a.generate([{'role':'user','content':'question'}],request_id='uncertain')
            state=a.ledger._read();entry=state['entries']['uncertain.attempt-1']
            self.assertGreater(entry['accounted_usd'],0)
            self.assertTrue(entry['status'].startswith('ERROR_'))

if __name__=='__main__':unittest.main()
