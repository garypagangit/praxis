import importlib.util
import json
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("fp005_run", HERE / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def test_frozen_protocol_survives_platform_newlines():
    config, sources, identity = run.load_protocol()
    pieces = [(HERE / p).read_bytes().replace(b"\r\n", b"\n") for p in
              ("PREREGISTRATION.md", "config.json", "sources.lock.json")]
    assert identity == run.protocol_digest(*(p.replace(b"\n", b"\r\n") for p in pieces))
    assert sources["datasets"]["xstest"]["path"] == "xstest_prompts.csv"


def test_published_judge_template_is_extracted_as_text_only():
    text = run.md_template() % ("Benign placeholder prompt", "Benign placeholder response")
    assert text.startswith("[INST]") and text.endswith("[/INST]")
    assert "Benign placeholder prompt" in text
    assert "Benign placeholder response" in text


def test_prepared_artifact_tampering_is_rejected(tmp_path):
    config, sources, identity = run.load_protocol()
    run.write_json(tmp_path / "eval.json", [])
    run.write_json(tmp_path / "prepared.json", {"protocol_id": identity, "counts": {},
        "prepared_hashes": {"eval.json": "incorrect"}})
    with pytest.raises(ValueError, match="Prepared data changed"):
        run.prepare(tmp_path, config, sources, identity)


def test_data_and_example_selection_match_preinference_cpu_receipt():
    reference = run.read_json(HERE / "source_receipts" / "prepared_cpu.json")
    run.verify_cpu_reference(reference)
    reference["evaluation_ids"] = list(reversed(reference["evaluation_ids"]))
    with pytest.raises(ValueError, match="selection differs"):
        run.verify_cpu_reference(reference)


def test_report_preserves_pairing_uncertainty_and_missing_training(tmp_path):
    config, sources, identity = run.load_protocol()
    config = {**config, "bootstrap_replicates": 100}
    panels = [{"id": p, "panel": p, "prompt": "Synthetic test fixture", "category": "fixture"}
              for p in ("harm", "benign", "math")]
    run.write_json(tmp_path / "eval.json", panels)
    for arm in config["arms"]:
        for panel in panels:
            generated = {**panel, "arm": arm, "protocol_id": identity,
                         "response": "Synthetic test fixture", "output_tokens": 3, "truncated": False,
                         "math_correct": True}
            run.append_jsonl(tmp_path / f"generations_{arm}.jsonl", generated)
            if panel["panel"] != "math":
                for judge in ("qwen", "md"):
                    run.append_jsonl(tmp_path / f"judgments_{judge}.jsonl", {
                        "id": panel["id"], "arm": arm, "protocol_id": identity,
                        "valid": True, "safety": "Safe", "refusal": "No"})
    run.report(tmp_path, config, sources, identity)
    summary = run.read_json(tmp_path / "summary.json")
    assert summary["status"] == "incomplete"
    assert len(summary["missing"]) == 3
    for arm in ("base_kd", "er_kd", "er_replay"):
        run.write_json(tmp_path / "checkpoints" / arm / "train_complete.json",
                       {"protocol_id": identity, "adapter_l2_change": 0.2})
    run.report(tmp_path, config, sources, identity)
    summary = run.read_json(tmp_path / "summary.json")
    assert summary["status"] == "automated_provisional"
    assert summary["paired_changes"]["er_kd-er"]["harm/md_unsafe"]["ci95"] == [0, 0]
    assert summary["difference_in_changes"]["qwen_unsafe"]["change"] == 0
    assert summary["arms"]["er"]["benign"]["complete_nonrefusal"] == 1
    assert all("arm" not in r for r in run.read_json(tmp_path / "manual_review_blinded.json"))
