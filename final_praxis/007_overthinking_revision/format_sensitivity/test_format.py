import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('format_sensitivity', Path(__file__).with_name('analyze_format.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FormatTests(unittest.TestCase):
    def test_plain_and_all_supported_wrappers(self):
        for text in ['FINAL: A', '**FINAL: A**', '`FINAL: A`', '``FINAL: A``',
                     '**`FINAL: A`**', '**``FINAL: A``**', '`**FINAL: A**`', '``**FINAL: A**``']:
            with self.subTest(text=text):
                self.assertEqual(m.sensitivity('Reason.\n'+text+'\n\n', ['A', 'B'])[0], 'A')

    def test_serialization_only_once(self):
        raw = 'Reason\n**FINAL: TRUE**'
        self.assertEqual(m.sensitivity(json.dumps(raw), ['TRUE', 'FALSE'])[0], 'TRUE')
        self.assertIsNone(m.sensitivity(json.dumps(json.dumps(raw)), ['TRUE', 'FALSE'])[0])
        for text in [json.dumps({'answer': raw}), json.dumps([raw]), '7', 'null']:
            self.assertIsNone(m.sensitivity(text, ['TRUE', 'FALSE'])[0])

    def test_ambiguity_truncation_vocabulary_unchanged(self):
        for text in ['FINAL: B\n**FINAL: A**', 'final : B\n**FINAL: A**',
                     '**FINAL: A**\nmore', '**FINAL:A**', '**final: A**',
                     '**FINAL: F**', ' **FINAL: A**', '**FINAL: A*',
                     '****FINAL: A****', '```FINAL: A```', '```\nFINAL: A\n```',
                     'Answer is A', 'Reason says FINAL: A']:
            with self.subTest(text=text):
                self.assertIsNone(m.sensitivity(text, ['A', 'B'])[0])
        self.assertIsNone(m.sensitivity('**FINAL: A**', ['B'])[0])
        self.assertIsNone(m.sensitivity('**FINAL: A**', ['A'], True)[0])

    def test_only_terminal_line_is_transformed(self):
        text = '**Reasoning**\n**FINAL: A**'
        normalized, trail = m.normalize(text)
        self.assertEqual(normalized, '**Reasoning**\nFINAL: A')
        self.assertEqual(trail, ['terminal_bold'])
        self.assertEqual(m.normalize('**Reasoning\nFINAL: A**')[0], '**Reasoning\nFINAL: A**')

    def test_provider_truncation_survives(self):
        score = m.original.score({'text': '**FINAL: A**', 'finish_reason': 'max_tokens', 'output_tokens': 512}, ['A'], 512)
        self.assertTrue(score['truncated'])
        self.assertIsNone(m.sensitivity('**FINAL: A**', ['A'], score['truncated'])[0])

    def synthetic(self):
        items = []
        for dataset in ['aqua', 'exfever']:
            for i in range(16):
                items.append({'dataset': dataset, 'id': str(i), 'question': 'Synthetic question',
                              'options': [{'label': 'A', 'text': 'a'}, {'label': 'B', 'text': 'b'}] if dataset == 'aqua' else [],
                              'gold': 'A' if dataset == 'aqua' else 'TRUE', 'evidence': 'Synthetic evidence'})
        expected = m.expected_cells(items)
        data = {}
        for relative, (model, item, arm) in expected.items():
            label = item['gold']
            if arm == 'false_peer':
                label = 'B' if item['dataset'] == 'aqua' else 'FALSE'
            text = 'FINAL: '+label
            if arm == 'neutral':
                text = '**'+text+'**'
            result = {'text': text, 'finish_reason': 'stop', 'output_tokens': 10}
            labels = [x['label'] for x in item['options']] or ['TRUE', 'FALSE']
            data[relative] = {'model': model, 'dataset': item['dataset'], 'id': item['id'], 'arm': arm,
                              'result': result, 'score': m.original.score(result, labels, 512 if arm == 'initial' else 768)}
        data['summary.json'] = m.local_report(items, data.copy(), 'score')
        return items, expected, data

    def test_exact_strict_report_and_sensitive_transitions_on_synthetic_384(self):
        items, expected, data = self.synthetic()
        snapshot = json.dumps(data, sort_keys=True)
        result = m.analyze(items, expected, data)
        self.assertEqual(json.dumps(data, sort_keys=True), snapshot)
        self.assertEqual(result['strict_summary'], data['summary.json'])
        self.assertEqual(len(result['cell_scores']), 384)
        self.assertEqual(len(result['strict_correct_to_wrong_audit_cases']), 64)
        strict = result['strict_summary']['results'][m.original.MODELS[0]+'/aqua']['arms']['neutral']
        relaxed = result['sensitivity_summary']['results'][m.original.MODELS[0]+'/aqua']['arms']['neutral']
        self.assertEqual(strict['invalid'], 16)
        self.assertEqual(strict['loss_including_invalid'], 16)
        self.assertEqual(relaxed['invalid'], 0)
        self.assertEqual(relaxed['C_C'], 16)

    def test_corrupted_stored_score_aborts(self):
        items, expected, data = self.synthetic()
        key = next(iter(expected))
        data[key]['score']['answer'] = None
        with self.assertRaisesRegex(ValueError, 'Stored strict score mismatch'):
            m.analyze(items, expected, data)

    def test_freeze_rejects_nonimmutable_reference_before_cloud(self):
        with self.assertRaises(ValueError):
            m.verify_freeze('HEAD')


if __name__ == '__main__':
    unittest.main()
