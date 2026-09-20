"""Score submitted HUMAN review answers; never fabricate a review or agreement."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from scipy.stats import beta


def run(key_path, response_path, output):
    key = json.loads(key_path.read_text(encoding="utf-8"))
    submission = json.loads(response_path.read_text(encoding="utf-8"))
    assert len(key) == 50
    assert isinstance(submission.get("reviewer"), str) and submission["reviewer"].strip()
    answers = submission["responses"]
    assert len(answers) == 50 and len({r["case_id"] for r in answers}) == 50
    assert {r["case_id"] for r in answers} == set(key)
    assert all(r["decision"] in ("Attack", "Non-Attack", "Unable to verify") and
               isinstance(r.get("reason"), str) and r["reason"].strip() for r in answers)
    agree = sum(r["decision"] == key[r["case_id"]] for r in answers)
    unable = sum(r["decision"] == "Unable to verify" for r in answers)
    lo = 0.0 if agree == 0 else float(beta.ppf(0.025, agree, 51-agree))
    hi = 1.0 if agree == 50 else float(beta.ppf(0.975, agree+1, 50-agree))
    result = {"status": "SUBMITTED_REVIEW_SCORED_NOT_FULL_G0_APPROVAL", "scored_utc": datetime.now(timezone.utc).isoformat(),
              "reviewer_as_submitted": submission["reviewer"], "completed_utc_as_submitted": submission.get("completed_utc"),
              "responses": 50, "agreements": agree, "unable_to_verify": unable, "agreement": agree/50,
              "agreement_exact_95pct_interval": [lo, hi], "label_agreement_point_gate_pass": agree >= 45,
              "response_file_sha256": hashlib.sha256(response_path.read_bytes()).hexdigest(),
              "limitations": "Submitted reviewer identity is not independently authenticated. Agreement with released labels is not independent raw-log truth. Other G0 data, provenance and independence requirements remain separate."}
    assert not output.exists(), "Do not overwrite a scored review"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--answer-key", type=Path, required=True)
    p.add_argument("--responses", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.answer_key, a.responses, a.output)
