from scripts.build_px062_skill_hallucination_benchmark import build_tasks
from scripts.run_px062_skill_hallucination_models import (
    extract_name,
    validate_environment,
)
from scripts.score_px062_skill_hallucination import score


def test_benchmark_has_three_balanced_task_types():
    registry = [{"name": "alpha", "path": "a"}, {"name": "beta", "path": "b"}]
    tasks = build_tasks(registry, 5, 62)
    assert len(tasks) == 15
    assert {row["task_type"] for row in tasks} == {
        "known_skill",
        "unavailable_capability",
        "near_miss_name",
    }


def test_scorer_flags_nonexistent_attempt():
    tasks = [
        {
            "task_id": "x",
            "expected_skill": None,
        }
    ]
    outputs = [
        {
            "task_id": "x",
            "model_id": "m",
            "condition": "open_ended",
            "recommended_skill": "invented",
            "attempted_load": True,
        }
    ]
    result = score(tasks, outputs, {"alpha"})
    group = result["groups"]["m::open_ended"]
    assert group["nonexistent_name_rate"] == 1.0
    assert group["nonexistent_attempt_rate"] == 1.0


def test_exact_parser_never_collapses_near_miss_to_registered_base():
    names = ["pdf", "playwright", "aspnet-core"]
    assert extract_name("pdf-pro", names) == "pdf-pro"
    assert extract_name("playwright-agent", names) == "playwright-agent"
    assert extract_name("aspnet-core-official", names) == "aspnet-core-official"


def test_exact_parser_accepts_exact_name_and_abstention_only():
    names = ["pdf", "Playwright"]
    assert extract_name("`pdf`", names) == "pdf"
    assert extract_name("playwright", names) == "Playwright"
    assert extract_name("NONE", names) is None
    assert extract_name("The answer is pdf", names) == "the answer is pdf"


def test_environment_gate_uses_normalized_torch_base_version():
    config = {
        "dependency_versions": {
            "torch": "2.3.0",
            "transformers": "4.46.3",
        }
    }
    validate_environment(
        config,
        {
            "torch": "2.3.0",
            "torch_build": "2.3.0+cu121",
            "transformers": "4.46.3",
        },
    )
