import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('pilot',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ProtocolTests(unittest.TestCase):
    def test_terminal_and_truncation(self):
        self.assertEqual(m.parse('Reason.\nFINAL: A',['A','B']),'A')
        for text in ['FINAL: A\nFINAL: B','FINAL: A\nmore','final: A']:
            self.assertIsNone(m.parse(text,['A','B']))
        self.assertIsNone(m.parse('FINAL: A',['A','B'],True))
        self.assertIsNone(m.score({'text':'FINAL: A','finish_reason':'max_tokens','output_tokens':512},['A'],512)['answer'])
    def test_gold_and_evidence_withheld(self):
        item={'dataset':'aqua','id':'x','question':'Question sentinel','options':[{'label':'A','text':'One'},{'label':'B','text':'Two'}],'gold':'GOLD_SENTINEL','evidence':'EVIDENCE_SENTINEL'}
        for messages in [m.initial(item),m.revision(item,'original','solo'),m.revision(item,'original','neutral')]:
            text=json.dumps(messages);self.assertNotIn('GOLD_SENTINEL',text);self.assertNotIn('EVIDENCE_SENTINEL',text)
    def test_same_frozen_answer(self):
        item={'dataset':'exfever','id':'x','question':'Claim','options':[],'gold':'TRUE','evidence':'Evidence'}
        first='Exact\n bytes  \nFINAL: FALSE'
        for arm in m.ARMS:self.assertEqual(m.revision(item,first,arm)[1],{'role':'assistant','content':first})
        a=m.revision(item,first,'true_peer')[-1]['content'];b=m.revision(item,first,'false_peer')[-1]['content']
        self.assertEqual(a.replace('TRUE','LABEL'),b.replace('FALSE','LABEL'))
    def test_invalid_and_pending_counted(self):
        item={'dataset':'aqua','id':'x','gold':'A'}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);key=m.sha((m.MODELS[0]+':aqua:x').encode())[:20];d=out/'cells'/key
            m.write(d/'initial.json',{'score':{'answer':'A'}});m.write(d/'false_peer.json',{'score':{'answer':None}})
            result=m.report([item],out)['results'][m.MODELS[0]+'/aqua']['arms']
            self.assertEqual(result['false_peer']['invalid'],1);self.assertEqual(result['false_peer']['loss_including_invalid'],1)
            self.assertEqual(result['neutral']['pending'],1);self.assertEqual(result['false_peer'].get('C_W',0),0)
if __name__=='__main__':unittest.main()
