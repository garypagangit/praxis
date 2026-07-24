from scripts.run_px062_public_corpus_gate import build_cases, evaluate_case, metrics


def rows():
    clean = [{"path": "clean/SKILL.md"}]
    poisoned = [{"path": "poison/SKILL.md"}]
    return build_cases(clean, poisoned)


def test_provenance_allows_authentic_signed_poison():
    case = next(x for x in rows() if x["condition"] == "authentic_poison_signed")
    assert evaluate_case(case, "provenance_full")["allowed"]


def test_provenance_blocks_tamper_and_nonexistent():
    selected = [
        x for x in rows() if x["condition"] in {"poison_tampered", "nonexistent"}
    ]
    assert all(not evaluate_case(x, "provenance_full")["allowed"] for x in selected)


def test_allowlist_blocks_external_publisher_and_keeps_clean():
    evaluated = [evaluate_case(x, "provenance_plus_publisher_allowlist") for x in rows()]
    poison = next(x for x in evaluated if x["condition"] == "authentic_poison_signed")
    clean = next(x for x in evaluated if x["condition"] == "clean_exact")
    assert not poison["allowed"]
    assert clean["allowed"]


def test_metrics_reports_clean_utility():
    evaluated = [evaluate_case(x, "provenance_full") for x in rows()]
    result = metrics(evaluated)
    assert result["clean_false_reject_rate"] == 0.0
    assert result["conditions"]["authentic_poison_signed"]["allow_rate"] == 1.0
