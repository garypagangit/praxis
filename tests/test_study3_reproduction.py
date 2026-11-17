import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "study3_reproduction.py"
spec = importlib.util.spec_from_file_location("study3_reproduction", MODULE_PATH)
study3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study3)


class Study3ReproductionTests(unittest.TestCase):
    def test_prepare_and_verify_and_detect_changed_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            for name in ("code", "data", "reports", "results_h1_h3", "results_h2_stage"):
                (source / name).mkdir(parents=True)
            (source / "real_lab3_preprocessing_design.md").write_text("design", encoding="utf-8")
            (source / "code" / "f.py").write_text("pass\n", encoding="utf-8")
            (source / "data" / "input.csv").write_text("x\n", encoding="utf-8")
            for name in ("results_h1_h3/RULES_AS_DECIDED.md",
                         "results_h2_stage/H2_RULE_BEFORE_RUN.md"):
                (source / name).write_text("rule", encoding="utf-8")
            for freeze, name in (("FREEZE_1.json", "code/f.py"),
                                 ("FREEZE_2.json", "data/input.csv")):
                record = {"files": {name: {"sha256": study3.digest(source / name)}}}
                (source / "reports" / freeze).write_text(json.dumps(record), encoding="utf-8")
            dest = root / "prepared"
            study3.prepare(source, dest, "rescore")
            self.assertFalse((dest / "results").exists())
            (dest / "data" / "input.csv").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing or changed"):
                study3.verify(dest)
            self.assertEqual((source / "data" / "input.csv").read_text(), "x\n")

    def test_refuses_overlap_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            with self.assertRaisesRegex(ValueError, "contain one another"):
                study3.prepare(source, source / "copy", "raw")
            dest = Path(tmp) / "destination"
            dest.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                study3.prepare(source, dest, "raw")

    def test_refuses_unprepared_and_repository_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Not a prepared"):
                study3.load_marker(Path(tmp))
        with self.assertRaisesRegex(ValueError, "outside the Git repository"):
            study3.load_marker(study3.REPOSITORY / "private-study")

    def test_probe_rejects_mismatched_frozen_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / study3.MARKER).write_text('{"mode":"rescore"}', encoding="utf-8")
            (root / "reports").mkdir()
            for name in ("FREEZE_1.json", "FREEZE_2.json"):
                (root / "reports" / name).write_text('{"files":{}}', encoding="utf-8")

            def fake_run(*args, **kwargs):
                result = root / "results" / "trials" / "main__lr.json"
                result.parent.mkdir(parents=True)
                result.write_text('{"matches_plumbing":false}', encoding="utf-8")

            with mock.patch.object(study3.subprocess, "run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "fit hash differs"):
                    study3.probe(root)


if __name__ == "__main__":
    unittest.main()
