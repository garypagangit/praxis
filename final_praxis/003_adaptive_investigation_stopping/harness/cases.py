"""Inert benchmark generation; never generate model outcomes here."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260908
FAMILIES = {
    "identity": ("unusual account login", "account owner", "the login and session use"),
    "mail": ("message with an unusual attachment", "mail administrator", "the message and attachment"),
    "endpoint": ("rare executable launch", "endpoint administrator", "the executable and launch"),
    "egress": ("unusual outbound data transfer", "data owner", "the destination and transfer"),
    "cloud": ("cloud permission change", "cloud administrator", "the principal and permission change"),
    "service": ("new persistent service", "service owner", "the service installation"),
    "archive": ("large file archive creation", "records custodian", "the archive operation"),
    "remote_access": ("remote administration session", "system owner", "the remote session"),
}

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def build_cases():
    rng = random.Random(SEED)
    cases = []
    for family, (alert, owner, action) in FAMILIES.items():
        for i in range(50):
            malicious = i % 2 == 1
            label = "malicious" if malicious else "benign"
            case_id = f"fp003-{family}-{i:03d}"
            host = f"host-{rng.randrange(100000, 999999)}"
            ticket = f"CHG-{rng.randrange(1000000, 9999999)}"
            # Evidence timing varies before any response exists; labels are balanced per family.
            decisive_round = [2, 4, 6, 8][(i // 2) % 4]
            principal = f"operator-{rng.randrange(10000, 99999)}"
            minute = rng.randrange(600, 900)
            mismatch = (i // 2) % 3
            permitted_principal = principal + "-other" if malicious and mismatch == 0 else principal
            permitted_asset = host + "-other" if malicious and mismatch == 1 else host
            end_minute = minute - 1 if malicious and mismatch == 2 else minute + 10
            decisive = (
                f"Signed audit for {action}: event actor={principal}; asset={host}; minute={minute}. "
                f"The sole approved record {ticket}, verified by {owner}, permits actor={permitted_principal}; "
                f"asset={permitted_asset}; inclusive minute interval={minute - 10}..{end_minute}. "
                "The audit confirms actual execution, no simulation, no separate approval, and no other activity."
            )
            surface = [
                f"Initial detection: {alert} on {host}; rarity score {rng.randrange(70, 99)}/100. The detector can produce false alarms.",
                f"A provisional ticket {ticket} appears to describe maintenance, but its event linkage has not been checked.",
                "A threat-feed match involves shared infrastructure; the match alone does not establish malicious activity.",
                "An authenticated session was observed. Authentication proves credential use, not that the owner authorized this action.",
                "No additional alert fired in the next interval. Absence of an alert is not proof that the action was authorized.",
                "A copied operator note calls the activity routine. The note is unverified and does not override an authoritative audit.",
                "The affected asset remained available. Availability does not determine whether the action was authorized.",
            ]
            surface.insert(decisive_round - 1, decisive)
            evidence = [{"evidence_id": f"{case_id}-e{r}", "round": r, "text": text,
                         "source": "authoritative_audit" if text == decisive else "context_observation"}
                        for r, text in enumerate(surface, 1)]
            # Exactly 10% protected and a disjoint 10% delayed-completeness subset.
            cases.append({"case_id": case_id, "family": family, "label": label,
                          "protected_high_impact": i < 5, "minimum_review_round": 4 if 5 <= i < 10 else 2,
                          "ground_truth_provenance": "inert_generator_authoritative_audit_rule_v1",
                          "hidden_ground_truth": {"event_actor": principal, "allowed_actor": permitted_principal,
                              "event_asset": host, "allowed_asset": permitted_asset, "minute": minute,
                              "allowed_start": minute - 10, "allowed_end": end_minute},
                          "evidence": evidence})
    rng.shuffle(cases)
    return cases

def freeze_corpus():
    cases = build_cases()
    path = ROOT / "configs/cases.jsonl"
    if path.exists():
        raise FileExistsError("Frozen corpus already exists; never overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical(case) for case in cases))
    manifest = {"schema": "fp003-case-manifest-v1", "seed": SEED, "count": 400, "rounds": 8,
                "source": "generated_inert_security_benchmark", "scientific_responses": "not_generated",
                "case_sha256": digest(path), "generator_sha256": digest(__file__),
                "case_ids": [case["case_id"] for case in cases], "families": list(FAMILIES),
                "label_counts": {"benign": 200, "malicious": 200}}
    (ROOT / "configs/case_manifest.json").write_bytes(canonical(manifest))
    return manifest

if __name__ == "__main__":
    print(json.dumps(freeze_corpus(), indent=2))
