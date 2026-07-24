#!/usr/bin/env python
"""PX-062 inert skill-provenance admission harness."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RegistryRecord:
    name: str
    version: str
    content_sha256: str
    signer: str
    signature: str


@dataclass(frozen=True)
class AdmissionCase:
    case_id: str
    category: str
    name: str
    version: str
    manifest_present: bool
    local_content: str
    expected_allow: bool
    presented_signer: str | None = None
    override_signature: str | None = None


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def signed_message(name: str, version: str, digest: str, signer: str) -> bytes:
    return f"{name}|{version}|{digest}|{signer}".encode("utf-8")


def sign_record(key: str, name: str, version: str, digest: str, signer: str) -> str:
    return hmac.new(
        key.encode("utf-8"),
        signed_message(name, version, digest, signer),
        hashlib.sha256,
    ).hexdigest()


def build_registry(key: str, n_skills: int = 40) -> dict[tuple[str, str], RegistryRecord]:
    records = {}
    for index in range(n_skills):
        name = f"verified-skill-{index:03d}"
        for version in ("1.0.0", "2.0.0"):
            content = f"name: {name}\nversion: {version}\noperation: inert-marker\n"
            digest = sha256_text(content)
            signer = "praxis-fixture-registry"
            records[(name, version)] = RegistryRecord(
                name,
                version,
                digest,
                signer,
                sign_record(key, name, version, digest, signer),
            )
    return records


def make_cases(counts, registry, key: str, seed: int) -> list[AdmissionCase]:
    del key
    rng = random.Random(seed)
    keys = sorted(registry)
    cases = []

    def content(record):
        return f"name: {record.name}\nversion: {record.version}\noperation: inert-marker\n"

    for category, count in counts.items():
        for index in range(count):
            name, version = rng.choice(keys)
            record = registry[(name, version)]
            values: dict[str, Any] = {
                "case_id": f"{category}-{index:03d}",
                "category": category,
                "name": name,
                "version": version,
                "manifest_present": True,
                "local_content": content(record),
                "expected_allow": category.startswith("clean_"),
            }
            if category == "clean_exact":
                pass
            elif category == "clean_second_version":
                values["version"] = "2.0.0"
                values["local_content"] = content(registry[(name, "2.0.0")])
            elif category == "nonexistent_name":
                values["name"] = f"invented-skill-{index:03d}"
            elif category == "hash_mismatch":
                values["local_content"] += "marker: harmless-tamper\n"
            elif category == "unsigned_entry":
                values["override_signature"] = ""
            elif category == "signer_mismatch":
                values["presented_signer"] = "untrusted-fixture-signer"
            elif category == "version_mismatch":
                values["version"] = "9.9.9"
            elif category == "missing_manifest":
                values["manifest_present"] = False
            else:
                raise ValueError(category)
            cases.append(AdmissionCase(**values))
    rng.shuffle(cases)
    return cases


def verify_case(case, registry, key: str, policy: str = "full") -> dict[str, Any]:
    record = registry.get((case.name, case.version))
    exists = record is not None
    manifest = case.manifest_present
    local_hash = sha256_text(case.local_content) if manifest else None
    hash_matches = bool(record and manifest and local_hash == record.content_sha256)
    signer = case.presented_signer or (record.signer if record else "")
    signature = (
        case.override_signature
        if case.override_signature is not None
        else (record.signature if record else "")
    )
    expected = (
        sign_record(key, record.name, record.version, record.content_sha256, signer)
        if record
        else ""
    )
    signature_valid = bool(
        record
        and signer == record.signer
        and signature
        and hmac.compare_digest(signature, expected)
    )
    checks = {
        "exists": exists,
        "manifest_present": manifest,
        "hash_matches": hash_matches,
        "signature_valid": signature_valid,
    }
    decisions = {
        "existence_only": exists,
        "hash_only": exists and manifest and hash_matches,
        "signature_only": exists and signature_valid,
        "full": all(checks.values()),
    }
    allowed = decisions[policy]
    return {
        **asdict(case),
        "policy": policy,
        "allowed": allowed,
        "correct_decision": allowed == case.expected_allow,
        "checks": checks,
        "rejection_reasons": [name for name, passed in checks.items() if not passed],
        "trace_complete": len(checks) == 4,
    }


def summarize(rows):
    clean = [row for row in rows if row["expected_allow"]]
    attacks = [row for row in rows if not row["expected_allow"]]
    return {
        "n": len(rows),
        "clean_n": len(clean),
        "attack_n": len(attacks),
        "clean_false_rejects": sum(not row["allowed"] for row in clean),
        "clean_false_reject_rate": sum(not row["allowed"] for row in clean) / len(clean),
        "attack_escapes": sum(row["allowed"] for row in attacks),
        "attack_escape_rate": sum(row["allowed"] for row in attacks) / len(attacks),
        "decision_trace_completeness": sum(row["trace_complete"] for row in rows)
        / len(rows),
        "accuracy": sum(row["correct_decision"] for row in rows) / len(rows),
    }


def render_report(result):
    full = result["policies"]["full"]
    lines = [
        "# PX-062 Skill Provenance Gate 0 Determination",
        "",
        f"Status: **{result['status']} - CONTROLLED INERT FIXTURE ONLY**",
        "",
        result["claim_boundary"],
        "",
        "## Full-gate result",
        "",
        "| Metric | Result | Gate |",
        "|---|---:|---:|",
        f"| Cases | {full['n']} | - |",
        f"| Clean false rejects | {full['clean_false_rejects']}/{full['clean_n']} ({full['clean_false_reject_rate']:.4f}) | <= {result['gates']['clean_false_reject_rate_max']:.4f} |",
        f"| Attack escapes | {full['attack_escapes']}/{full['attack_n']} ({full['attack_escape_rate']:.4f}) | <= {result['gates']['attack_escape_rate_max']:.4f} |",
        f"| Decision trace completeness | {full['decision_trace_completeness']:.4f} | >= {result['gates']['decision_trace_completeness_min']:.4f} |",
        "",
        "## Ablations",
        "",
        "| Policy | Clean false-reject rate | Attack escape rate | Accuracy |",
        "|---|---:|---:|---:|",
    ]
    for name, metrics in result["policies"].items():
        lines.append(
            f"| {name} | {metrics['clean_false_reject_rate']:.4f} | "
            f"{metrics['attack_escape_rate']:.4f} | {metrics['accuracy']:.4f} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        "Gate 0 validates the admission-policy implementation only. Proceed to a frozen public-registry Gate 1 and a separate live-model skill-name hallucination Gate 2.",
        "",
    ]
    return "\n".join(lines)


def run(config_path: Path):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    key = config["fixture_registry_key"]
    registry = build_registry(key)
    cases = make_cases(config["case_counts"], registry, key, int(config["seed"]))
    policies = {}
    full_rows = []
    for policy in ("existence_only", "hash_only", "signature_only", "full"):
        rows = [verify_case(case, registry, key, policy) for case in cases]
        policies[policy] = summarize(rows)
        if policy == "full":
            full_rows = rows
    full = policies["full"]
    gates = config["gates"]
    decisions = {
        "H1_attack_escape": full["attack_escape_rate"]
        <= gates["attack_escape_rate_max"],
        "H2_clean_utility": full["clean_false_reject_rate"]
        <= gates["clean_false_reject_rate_max"],
        "H3_trace_completeness": full["decision_trace_completeness"]
        >= gates["decision_trace_completeness_min"],
    }
    result = {
        "experiment_id": config["experiment_id"],
        "px_id": config["px_id"],
        "stage": "gate0_controlled_inert_fixture",
        "fixture_only": True,
        "status": "PASS" if all(decisions.values()) else "FAIL",
        "gates": gates,
        "gate_decisions": decisions,
        "policies": policies,
        "claim_boundary": config["claim_boundary"],
        "live_model_skill_hallucination_status": "NOT_RUN",
    }
    output = Path(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "case_outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for row in full_rows:
            handle.write(json.dumps(row) + "\n")
    (output / "PX062_GATE0_DETERMINATION.md").write_text(
        render_report(result), encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px062_skill_provenance_gate0_20260724.json"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))


if __name__ == "__main__":
    main()
