from scripts.build_px062_skill_hallucination_benchmark import build_tasks
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
