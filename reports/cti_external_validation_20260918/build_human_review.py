"""Create a deterministic review packet without released labels or model results."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    return [json.loads(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def rank(identifier):
    return hashlib.sha256(("20260918|" + identifier).encode("utf-8")).hexdigest()


def write(name, rows):
    raw = ("\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows) + "\n").encode("utf-8")
    path = ROOT / name
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("Refusing to overwrite changed review artifact: " + name)
    path.write_bytes(raw)
    return {"rows": len(rows), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    inputs = read("test_inputs.jsonl")
    metadata = read("sealed_labels.jsonl")
    by_id = {row["id"]: row for row in inputs}
    if len(by_id) != 1247 or {r["id"] for r in metadata} != set(by_id):
        raise ValueError("Review input join mismatch")
    groups = defaultdict(list)
    # Only identity/source fields influence sampling; published answers are
    # deliberately never inspected by this program.
    for row in metadata:
        groups[row["source"]].append(row["id"])
    if len(groups) != 10 or any(len(ids) < 5 for ids in groups.values()):
        raise ValueError("Expected ten source families with at least five items")
    selected = [(identifier, family) for family, ids in groups.items()
                for identifier in sorted(ids, key=rank)[:5]]
    selected.sort(key=lambda item: rank(item[0]))
    packet, template, key = [], [], []
    for number, (identifier, family) in enumerate(selected, start=1):
        review_id = f"CTI-H{number:03d}"
        original = by_id[identifier]
        packet.append({"review_id": review_id, "question": original["question"],
                       "options": original["options"], "evidence": original["evidence"]})
        template.append({"review_id": review_id, "reviewer": "", "date": "", "answer": "", "citation": "",
                         "applicability": "", "ambiguity": "", "notes": ""})
        key.append({"review_id": review_id, "dataset_id": identifier, "source_family": family,
                    "selection_sha256": rank(identifier)})
    if Counter(row["source_family"] for row in key) != {family: 5 for family in groups}:
        raise ValueError("Review source-family sampling mismatch")
    receipts = {"human_review_packet.jsonl": write("human_review_packet.jsonl", packet),
                "human_review_template.jsonl": write("human_review_template.jsonl", template),
                "human_review_identity_key.jsonl": write("human_review_identity_key.jsonl", key)}
    status = {"status": "PENDING_ACTUAL_HUMAN_REVIEW", "created_utc": datetime.now(timezone.utc).isoformat(),
              "selected_items": 50, "source_families": 10, "items_per_family": 5,
              "completed_human_reviews": 0, "human_validation_claimed": False,
              "selection": "Five lowest SHA256('20260918|' + dataset_id) items within each coarse source family; packet interleaved by the same hash.",
              "released_answers_used_for_selection": False, "model_outputs_opened": False,
              "reviewer_packet_excludes": ["released answer", "dataset ID", "source family", "model outputs", "checker decisions"],
              "artifacts": receipts, "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT / "HUMAN_REVIEW_STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
