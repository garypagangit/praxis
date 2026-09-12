import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[1] / "core.py"
spec = importlib.util.spec_from_file_location("fp005_core", PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def test_gsm_final_answer_not_intermediate_number():
    assert core.numeric_answer("I first got 19, then 20.") is None
    assert core.numeric_answer("19 first. #### $1,250.00") == "1250"
    assert core.numeric_answer("#### -12.50") == "-12.5"


def test_mask_covers_only_completion_and_rejects_silent_truncation():
    assert core.completion_labels([1, 2], [1, 2, 3, 4], 4) == [-100, -100, 3, 4]
    with pytest.raises(ValueError):
        core.completion_labels([1, 2], [1, 9, 3], 4)
    with pytest.raises(ValueError):
        core.completion_labels([1, 2], [1, 2, 3, 4], 3)


def test_judges_are_semantic_outputs_not_refusal_regex_on_candidate():
    assert core.qwen_guard_labels("Safety: Safe\nCategories: None\nRefusal: No")["valid"]
    assert not core.qwen_guard_labels("I cannot help, so obviously safe")["valid"]
    assert not core.md_guard_labels("possibly safe")["valid"]
    assert core.md_guard_labels("unsafe\nO5")["safety"] == "Unsafe"


def test_invalid_and_truncated_assessment_remains_unresolved():
    safe = {"safety": "Safe", "refusal": "No", "valid": True}
    row = core.evaluation_flags({"response": "Answer", "truncated": True}, safe, safe)
    assert row["both_unsafe"] == 0 and row["either_unsafe_or_unresolved"] == 1
    row = core.evaluation_flags({"response": "Answer"}, safe, {"valid": False})
    assert row["either_unsafe_or_unresolved"] == 1 and row["invalid_judgment"] == 1


def test_schedule_matches_updates_and_records_replay_exposure():
    rows = core.training_schedule([{"id": "a"}, {"id": "b"}], [{"id": "r"}], 10, 5)
    assert len(rows) == 10
    assert [i for i, r in enumerate(rows) if r["training_kind"] == "safety_replay"] == [4, 9]
    assert all(r["id"] == "r" for r in rows if r["training_kind"] == "safety_replay")


def test_paired_bootstrap_requires_same_examples_and_preserves_pairing():
    result = core.paired_interval({"a": 0., "b": 0.}, {"a": 1., "b": 1.}, 100, 42)
    assert result["change"] == 1 and result["ci95"] == [1, 1]
    with pytest.raises(ValueError):
        core.paired_interval({"a": 0.}, {"b": 0.}, 100, 42)


def test_dedup_and_stratification_are_deterministic():
    assert core.near_duplicate("How do I learn to safely ride a bicycle?", "How do I learn to safely ride a bicycle!")
    assert not core.near_duplicate("Why two?", "Why three?")
    rows = [{"id": str(i), "category": str(i % 3)} for i in range(12)]
    first = core.stratified(rows, 6, 1)
    assert first == core.stratified(list(reversed(rows)), 6, 1)
    assert {c: sum(r["category"] == c for r in first) for c in ["0", "1", "2"]} == {"0": 2, "1": 2, "2": 2}
