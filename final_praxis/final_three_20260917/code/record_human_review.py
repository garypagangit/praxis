"""Validate and append a human-submitted review without inferring approval."""
import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

ROLES = {"author", "advisor", "committee", "independent_reviewer"}
DECISIONS = {"accept_bounded_report", "revise", "decline", "unable_to_assess"}

def validate(data):
    if data.get("schema_version") != "1.0":
        raise ValueError("Unsupported review schema")
    for key in ("reviewer_name", "role", "review_date", "scope_selection", "rationale", "ai_policy_status", "next_action", "due_date_status"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing {key}")
    if data["role"] not in ROLES:
        raise ValueError("Invalid reviewer role")
    enums = {
        "scope_selection": {"cti", "008", "010_negative", "defer", "none", "outside_role"},
        "ai_policy_status": {"pending", "confirmed_with_reference", "requires_change", "outside_role"},
        "due_date_status": {"specified", "not_yet_set"},
        "author_understanding": {"not_recorded", "verified", "needs_work", "outside_role"},
    }
    for field, choices in enums.items():
        if data.get(field) not in choices:
            raise ValueError(f"Invalid {field}")
    if data["ai_policy_status"] == "confirmed_with_reference" and (not isinstance(data.get("policy_reference"), str) or not data["policy_reference"].strip()):
        raise ValueError("Confirmed requirements need a policy or approval reference")
    if data["author_understanding"] == "verified" and data["role"] != "author":
        raise ValueError("Only an author can attest their own understanding")
    date.fromisoformat(data["review_date"])
    if data.get("due_date"):
        date.fromisoformat(data["due_date"])
    if data["due_date_status"] == "specified" and not data.get("due_date"):
        raise ValueError("Specified due date is missing")
    if data.get("review_is_own") is not True:
        raise ValueError("Reviewer must attest this records their own review")
    for study in ("cti", "008", "010"):
        item = data.get("experiments", {}).get(study, {})
        if item.get("decision") not in DECISIONS or not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise ValueError(f"Missing decision or reason for {study}")
        if item.get("evidence_reviewed") not in {"yes", "partial", "no"}:
            raise ValueError(f"Missing evidence review state for {study}")
        if item["decision"] == "accept_bounded_report" and item["evidence_reviewed"] != "yes":
            raise ValueError(f"Acceptance of {study} requires reported evidence review")
    return data

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("human_reviews"))
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = validate(json.loads(raw.decode("utf-8-sig")))
    digest = hashlib.sha256(raw).hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    name = f"review_{data['review_date']}_{digest[:12]}.json"
    dest = args.output / name
    if dest.exists() and dest.read_bytes() != raw:
        raise ValueError("Destination collision; refusing overwrite")
    dest.write_bytes(raw)
    receipt = {
        "file": name, "sha256": digest, "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer_name": data["reviewer_name"], "role": data["role"],
        "review_date": data["review_date"], "provenance": "Self-reported human form; identity not independently authenticated",
        "institutional_acceptance_inferred": False,
    }
    receipt_path = args.output / (dest.stem + ".receipt.json")
    if not receipt_path.exists():
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipts = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(args.output.glob("*.receipt.json"))]
    (args.output / "INDEX.json").write_text(json.dumps({"reviews": receipts, "automatic_academic_approval": False}, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {name}; SHA-256 {digest}. No approval inferred.")

if __name__ == "__main__":
    main()
