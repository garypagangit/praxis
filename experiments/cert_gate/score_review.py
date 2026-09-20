"""Score submitted HUMAN review answers; never fabricate a review or agreement."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from scipy.stats import beta


def _strict_json(raw):
    """Reject duplicate object keys instead of silently replacing submitted data."""
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON key: {key}")
            value[key] = item
        return value
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)


def _valid_id(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def run(key_path, response_path, output):
    if output.exists():
        raise ValueError("Do not overwrite a scored review")
    key_bytes = key_path.read_bytes()
    response_bytes = response_path.read_bytes()
    key = _strict_json(key_bytes)
    submission = _strict_json(response_bytes)
    if not isinstance(key, dict) or len(key) != 50:
        raise ValueError("Answer key must contain exactly 50 unique case IDs")
    if not all(_valid_id(case_id) and isinstance(label, str)
               and label in {"Attack", "Non-Attack"} for case_id, label in key.items()):
        raise ValueError("Answer key requires nonempty case IDs and valid binary labels")
    if not isinstance(submission, dict):
        raise ValueError("Review submission must be a JSON object")
    reviewer = submission.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("A nonempty reviewer name or study ID is required")
    answers = submission.get("responses")
    if not isinstance(answers, list) or len(answers) != 50:
        raise ValueError("Exactly 50 review responses are required")
    for response in answers:
        if not isinstance(response, dict) or not _valid_id(response.get("case_id")):
            raise ValueError("Each response must have a valid case ID")
        decision, reason = response.get("decision"), response.get("reason")
        if (not isinstance(decision, str)
                or decision not in {"Attack", "Non-Attack", "Unable to verify"}
                or not isinstance(reason, str) or not reason.strip()):
            raise ValueError("Each response requires an allowed decision and nonempty reason")
    response_ids = [response["case_id"] for response in answers]
    if len(set(response_ids)) != 50 or set(response_ids) != set(key):
        raise ValueError("Response IDs must uniquely match all 50 answer-key IDs")
    agree = sum(r["decision"] == key[r["case_id"]] for r in answers)
    unable = sum(r["decision"] == "Unable to verify" for r in answers)
    lo = 0.0 if agree == 0 else float(beta.ppf(0.025, agree, 51-agree))
    hi = 1.0 if agree == 50 else float(beta.ppf(0.975, agree+1, 50-agree))
    result = {"status": "SUBMITTED_REVIEW_SCORED_NOT_FULL_G0_APPROVAL", "scored_utc": datetime.now(timezone.utc).isoformat(),
              "reviewer_as_submitted": submission["reviewer"], "completed_utc_as_submitted": submission.get("completed_utc"),
              "responses": 50, "agreements": agree, "unable_to_verify": unable, "agreement": agree/50,
              "agreement_exact_95pct_interval": [lo, hi], "label_agreement_point_gate_pass": agree >= 45,
              "answer_key_file_sha256": hashlib.sha256(key_bytes).hexdigest(),
              "response_file_sha256": hashlib.sha256(response_bytes).hexdigest(),
              "limitations": "Submitted reviewer identity is not independently authenticated. Agreement with released labels is not independent raw-log truth. Other G0 data, provenance and independence requirements remain separate."}
    try:
        # Exclusive creation also prevents an intervening writer from being overwritten.
        with output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    except FileExistsError as exc:
        raise ValueError("Do not overwrite a scored review") from exc
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--answer-key", type=Path, required=True)
    p.add_argument("--responses", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.answer_key, a.responses, a.output)
