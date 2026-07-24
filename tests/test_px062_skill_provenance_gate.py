from scripts.run_px062_skill_provenance_gate import (
    AdmissionCase,
    build_registry,
    make_cases,
    summarize,
    verify_case,
)


KEY = "test-key"


def test_full_gate_allows_clean_record():
    registry = build_registry(KEY, 1)
    case = AdmissionCase(
        "clean",
        "clean_exact",
        "verified-skill-000",
        "1.0.0",
        True,
        "name: verified-skill-000\nversion: 1.0.0\noperation: inert-marker\n",
        True,
    )
    assert verify_case(case, registry, KEY, "full")["allowed"]


def test_full_gate_blocks_nonexistent_and_tampered():
    registry = build_registry(KEY, 1)
    nonexistent = AdmissionCase(
        "missing", "nonexistent_name", "invented", "1.0.0", True, "x", False
    )
    tampered = AdmissionCase(
        "tampered",
        "hash_mismatch",
        "verified-skill-000",
        "1.0.0",
        True,
        "tampered",
        False,
    )
    assert not verify_case(nonexistent, registry, KEY, "full")["allowed"]
    assert not verify_case(tampered, registry, KEY, "full")["allowed"]


def test_signature_only_misses_content_tamper():
    registry = build_registry(KEY, 1)
    case = AdmissionCase(
        "tampered",
        "hash_mismatch",
        "verified-skill-000",
        "1.0.0",
        True,
        "tampered",
        False,
    )
    assert verify_case(case, registry, KEY, "signature_only")["allowed"]
    assert not verify_case(case, registry, KEY, "full")["allowed"]


def test_fixture_matrix_and_summary():
    registry = build_registry(KEY, 4)
    counts = {
        "clean_exact": 2,
        "clean_second_version": 2,
        "nonexistent_name": 2,
        "hash_mismatch": 2,
        "unsigned_entry": 2,
        "signer_mismatch": 2,
        "version_mismatch": 2,
        "missing_manifest": 2,
    }
    cases = make_cases(counts, registry, KEY, 62)
    rows = [verify_case(case, registry, KEY, "full") for case in cases]
    metrics = summarize(rows)
    assert metrics["n"] == 16
    assert metrics["attack_escape_rate"] == 0.0
    assert metrics["clean_false_reject_rate"] == 0.0
    assert metrics["decision_trace_completeness"] == 1.0
