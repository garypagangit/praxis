from scripts.run_px057_trace_collection import (
    build_prompt,
    extract_numeric_answer,
    normalize_numeric,
    parse_gsm8k_gold,
)


def test_extract_numeric_answer_prefers_explicit_final_answer() -> None:
    text = "I first thought 12, but after checking: Final answer: 18"
    assert extract_numeric_answer(text) == "18"


def test_extract_numeric_answer_handles_boxed_and_commas() -> None:
    assert extract_numeric_answer(r"Therefore \boxed{1,250}.") == "1250"


def test_parse_gsm8k_gold() -> None:
    assert parse_gsm8k_gold("Reasoning text\n#### 1,024") == "1024"


def test_reconsideration_prompt_preserves_question_and_previous() -> None:
    prompt = build_prompt("What is 2+2?", "Final answer: 5", 2)
    assert "What is 2+2?" in prompt
    assert "Final answer: 5" in prompt
    assert "Reconsideration round: 2" in prompt


def test_normalize_numeric() -> None:
    assert normalize_numeric("3.000") == "3"
