import importlib.util
from pathlib import Path, PurePosixPath
import unittest

spec = importlib.util.spec_from_file_location('repair', Path(__file__).with_name('resume_evaluation.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RepairTests(unittest.TestCase):
    def test_only_missing_judge_and_report_are_scheduled(self):
        commands = m.stage_commands('/original/python', PurePosixPath('/old/run.py'), PurePosixPath('/old/outputs'))
        self.assertEqual(commands, [
            ['/original/python', '/old/run.py', 'judge', '--judge', 'md', '--out', '/old/outputs'],
            ['/original/python', '/old/run.py', 'report', '--out', '/old/outputs']])
        self.assertTrue(all(word not in {'all', 'train', 'evaluate', 'distill', 'analyze'}
                            for command in commands for word in command))

    def test_deadline_is_original_not_relative_extension(self):
        self.assertEqual(m.STOP.isoformat(), '2026-09-12T15:55:49.634894+00:00')


if __name__ == '__main__':
    unittest.main()
