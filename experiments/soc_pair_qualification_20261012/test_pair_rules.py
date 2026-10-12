import unittest
from pair_rules import terminal_span,normalize_output,resolve_text,uptake,joined_transition,classify_control

class PairTests(unittest.TestCase):
    def test_correct_span_and_next_boundary(self):
        raw=b'abc\x1b[?2004l\ranswer\r\n\x1b[?2004hprompt'
        c={'output_end_before_enter':3,'confirmation_output_end':12}
        r,m=terminal_span(raw,c,{'output_end_before_enter':35})
        self.assertEqual(r,'\ranswer\r\n');self.assertIsNone(m['reason'])
    def test_crossing_next_submission_rejected(self):
        raw=b'\x1b[?2004lanswer\x1b[?2004h'
        r,m=terminal_span(raw,{'output_end_before_enter':0,'confirmation_output_end':8},{'output_end_before_enter':10})
        self.assertIsNone(r);self.assertEqual(m['reason'],'crosses_next_submission')
    def test_missing_boundary(self):
        self.assertIsNone(terminal_span(b'no shell markers',{'output_end_before_enter':0,'confirmation_output_end':16})[0])
    def test_utf8_not_silently_replaced(self):
        raw=b'\x1b[?2004l\xff\x1b[?2004h'
        self.assertEqual(terminal_span(raw,{'output_end_before_enter':0,'confirmation_output_end':8})[1]['reason'],'invalid_utf8')
    def test_sgr_only_normalization(self):
        self.assertEqual(normalize_output('\r\x1b[31merror\x1b[0m\r\n'),('error\n',None))
    def test_cursor_motion_and_backspace_rejected(self):
        for value in ('one\rTWO','x\bY','\x1b[2Jhidden','\x1b]0;title\x07'):
            self.assertEqual(normalize_output(value)[1],'terminal_control_requires_rendering')
    def test_empty_not_missing(self):
        self.assertEqual(normalize_output(''),('',None));self.assertEqual(normalize_output(None),(None,'missing'))
    def test_prompt_and_wrapper_rejected(self):
        self.assertEqual(normalize_output('root@lab:/tmp# ')[1],'prompt_or_terminal_frame')
        self.assertEqual(normalize_output('Output truncated')[1],'possible_truncation_or_tool_wrapper')
    def test_attachments_and_mixed_content(self):
        self.assertEqual(resolve_text('attachment://a',{'a':'text'}),'text')
        self.assertIsNone(resolve_text('attachment://missing',{}))
        self.assertIsNone(resolve_text([{'type':'text','text':'x'},{'type':'image','data':'z'}],{}))
    def test_information_use_positive(self):
        r=uptake('result.txt\n',['ls'],'cat result.txt')
        self.assertTrue(r['hit']);self.assertEqual(r['new_to_retained_history'],1)
    def test_echoed_argument_is_not_new_information(self):
        r=uptake('cat: result.txt: missing',['cat result.txt'],'cat result.txt')
        self.assertFalse(r['supported']);self.assertFalse(r['hit'])
    def test_previously_seen_output_is_not_new(self):
        r=uptake('result.txt',['ls'],'cat result.txt',['result.txt'])
        self.assertFalse(r['supported'])
    def test_no_substring_entity_match(self):
        self.assertFalse(uptake('result.txt',['ls'],'cat myresult.txt')['hit'])
    def test_adjacency_gap_and_cross_terminal_rejected(self):
        a={'qualified':True,'origin':'H','index':0,'log':'a'}
        b={'qualified':True,'origin':'H','index':2,'log':'a'}
        self.assertFalse(joined_transition(a,b));b['index']=1;b['log']='b'
        self.assertFalse(joined_transition(a,b))
    def test_parallel_ai_calls_rejected(self):
        a={'qualified':True,'origin':'A','index':0,'reply_message':4}
        b={'qualified':True,'origin':'A','index':1,'call_message':3}
        self.assertFalse(joined_transition(a,b));b['call_message']=5
        self.assertTrue(joined_transition(a,b))
    def test_whole_compound_submission_not_control(self):
        self.assertFalse(classify_control('ls && cat result.txt'))
        self.assertTrue(classify_control('task show'));self.assertTrue(classify_control('flag submit value'))

if __name__=='__main__':unittest.main(verbosity=2)
