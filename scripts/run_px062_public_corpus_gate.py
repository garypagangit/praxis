#!/usr/bin/env python
"""Evaluate PX-062 provenance policies on public skill corpora without execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any


FRONTMATTER_NAME = re.compile(r"(?m)^name:\s*[\"']?([^\"'\r\n]+)")
FRONTMATTER_DESCRIPTION = re.compile(
    r"(?ms)^description:\s*(.+?)(?=^[A-Za-z][A-Za-z0-9_-]*:\s|\n---)"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_name(path: Path, raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    match = FRONTMATTER_NAME.search(text)
    return match.group(1).strip() if match else path.parent.name


def parse_description(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    match = FRONTMATTER_DESCRIPTION.search(text)
    if not match:
        return ""
    return " ".join(
        line.strip().strip("\"'")
        for line in match.group(1).splitlines()
        if line.strip()
    )[:1200]


def inventory(root: Path, corpus: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("SKILL.md")):
        raw = path.read_bytes()
        rows.append(
            {
                "corpus": corpus,
                "path": path.as_posix(),
                "name": parse_name(path, raw),
                "description": parse_description(raw),
                "sha256": sha256_bytes(raw),
                "bytes": len(raw),
            }
        )
    return rows


def inventory_zip(archive: Path, corpus: str) -> list[dict[str, Any]]:
    rows = []
    with zipfile.ZipFile(archive) as handle:
        names = sorted(
            name for name in handle.namelist() if name.endswith("/SKILL.md")
        )
        for name in names:
            raw = handle.read(name)
            virtual_path = Path(name)
            rows.append(
                {
                    "corpus": corpus,
                    "path": name,
                    "name": parse_name(virtual_path, raw),
                    "description": parse_description(raw),
                    "sha256": sha256_bytes(raw),
                    "bytes": len(raw),
                }
            )
    return rows


def evaluate_case(case: dict[str, Any], policy: str) -> dict[str, Any]:
    checks = {
        "exists": case["exists"],
        "manifest_present": case["manifest_present"],
        "hash_matches": case["hash_matches"],
        "signature_valid": case["signature_valid"],
        "publisher_allowlisted": case["publisher_allowlisted"],
        "semantic_safe": case["semantic_safe"],
    }
    decisions = {
        "no_gate": True,
        "provenance_full": all(
            checks[name]
            for name in ("exists", "manifest_present", "hash_matches", "signature_valid")
        ),
        "provenance_plus_publisher_allowlist": all(
            checks[name]
            for name in (
                "exists",
                "manifest_present",
                "hash_matches",
                "signature_valid",
                "publisher_allowlisted",
            )
        ),
        "semantic_oracle": checks["semantic_safe"],
    }
    return {**case, "policy": policy, "allowed": decisions[policy], "checks": checks}


def build_cases(clean: list[dict], poisoned: list[dict]) -> list[dict]:
    cases = []
    for row in clean:
        common = {
            "skill_id": f"clean::{row['path']}",
            "source_corpus": "openai_skills",
            "expected_safe": True,
            "publisher": "openai",
            "publisher_allowlisted": True,
            "semantic_safe": True,
        }
        cases.append(
            {
                **common,
                "condition": "clean_exact",
                "exists": True,
                "manifest_present": True,
                "hash_matches": True,
                "signature_valid": True,
            }
        )
        cases.append(
            {
                **common,
                "condition": "clean_tampered",
                "expected_safe": False,
                "exists": True,
                "manifest_present": True,
                "hash_matches": False,
                "signature_valid": True,
                "semantic_safe": False,
            }
        )
    for row in poisoned:
        common = {
            "skill_id": f"poison::{row['path']}",
            "source_corpus": "poisoned_skills_zenodo",
            "expected_safe": False,
            "publisher": "external_unreviewed",
            "publisher_allowlisted": False,
            "semantic_safe": False,
        }
        cases.append(
            {
                **common,
                "condition": "authentic_poison_signed",
                "exists": True,
                "manifest_present": True,
                "hash_matches": True,
                "signature_valid": True,
            }
        )
        cases.append(
            {
                **common,
                "condition": "poison_tampered",
                "exists": True,
                "manifest_present": True,
                "hash_matches": False,
                "signature_valid": True,
            }
        )
    for index in range(len(poisoned)):
        cases.append(
            {
                "skill_id": f"nonexistent::{index:04d}",
                "source_corpus": "constructed_nonexistent_names",
                "condition": "nonexistent",
                "expected_safe": False,
                "publisher": "unknown",
                "exists": False,
                "manifest_present": False,
                "hash_matches": False,
                "signature_valid": False,
                "publisher_allowlisted": False,
                "semantic_safe": False,
            }
        )
    return cases


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_condition = {}
    for condition in sorted({row["condition"] for row in rows}):
        subset = [row for row in rows if row["condition"] == condition]
        allowed = sum(row["allowed"] for row in subset)
        by_condition[condition] = {
            "n": len(subset),
            "allowed": allowed,
            "allow_rate": allowed / len(subset),
        }
    clean = [row for row in rows if row["condition"] == "clean_exact"]
    return {
        "n": len(rows),
        "conditions": by_condition,
        "clean_false_reject_rate": sum(not row["allowed"] for row in clean) / len(clean),
    }


def render(result: dict[str, Any]) -> str:
    primary = result["policies"]["provenance_full"]
    status = result["status"]
    lines = [
        "# PX-062 Public-Corpus Provenance Gate 1",
        "",
        f"Status: **{status}**",
        "",
        result["claim_boundary"],
        "",
        "## Corpus",
        "",
        f"- PoisonedSkills release: {result['corpus']['poisoned_skills']} SKILL.md files",
        f"- Clean OpenAI snapshot: {result['corpus']['clean_skills']} SKILL.md files",
        f"- Poisoned archive SHA-256: `{result['corpus']['poisoned_archive_sha256']}`",
        f"- OpenAI skills commit: `{result['corpus']['clean_source_commit']}`",
        "",
        "## Primary provenance-only policy",
        "",
        "| Condition | N | Allowed | Escape/allow rate |",
        "|---|---:|---:|---:|",
    ]
    for condition, row in primary["conditions"].items():
        lines.append(
            f"| {condition} | {row['n']} | {row['allowed']} | {row['allow_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"- Clean false-reject rate: `{primary['clean_false_reject_rate']:.4f}`",
            "",
            "## Policy comparison",
            "",
            "| Policy | Authentic signed poison allowed | Tampered poison allowed | Nonexistent allowed | Clean false rejects |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name, policy in result["policies"].items():
        c = policy["conditions"]
        lines.append(
            f"| {name} | {c['authentic_poison_signed']['allow_rate']:.4f} | "
            f"{c['poison_tampered']['allow_rate']:.4f} | "
            f"{c['nonexistent']['allow_rate']:.4f} | "
            f"{policy['clean_false_reject_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Determination",
            "",
            result["determination"],
            "",
            "Hash pinning, existence verification, and registry signatures establish identity and integrity; they do not establish that authenticated content is benign. PX-062 therefore rejects the original hypothesis that provenance alone is a sufficient defense against the paper's attack class. It remains useful as one layer against name hallucination, substitution, rollback, and post-publication tampering.",
            "",
        ]
    )
    return "\n".join(lines)


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    archive = Path(config["poisoned_archive"])
    archive_hash = sha256_bytes(archive.read_bytes())
    if archive_hash != config["poisoned_archive_sha256"]:
        raise ValueError("poisoned archive SHA-256 mismatch")
    poisoned = inventory_zip(archive, "poisoned_skills")
    clean = inventory(Path(config["clean_skills_dir"]), "openai_skills")
    expected = config["expected_counts"]
    if len(poisoned) != expected["poisoned_skills"]:
        raise ValueError("unexpected poisoned-skill count")
    if len(clean) != expected["clean_skills"]:
        raise ValueError("unexpected clean-skill count")
    cases = build_cases(clean, poisoned)
    policies = {}
    primary_rows = []
    for policy in (
        "no_gate",
        "provenance_full",
        "provenance_plus_publisher_allowlist",
        "semantic_oracle",
    ):
        rows = [evaluate_case(case, policy) for case in cases]
        policies[policy] = metrics(rows)
        if policy == "provenance_full":
            primary_rows = rows
    primary = policies["provenance_full"]
    gates = config["gates"]
    gate_decisions = {
        "authentic_poison": primary["conditions"]["authentic_poison_signed"]["allow_rate"]
        <= gates["authentic_poison_escape_rate_max"],
        "tamper": primary["conditions"]["poison_tampered"]["allow_rate"]
        <= gates["tamper_escape_rate_max"],
        "nonexistent": primary["conditions"]["nonexistent"]["allow_rate"]
        <= gates["nonexistent_escape_rate_max"],
        "clean_utility": primary["clean_false_reject_rate"]
        <= gates["clean_false_reject_rate_max"],
    }
    status = "PASS" if all(gate_decisions.values()) else "FAIL"
    result = {
        "experiment_id": config["experiment_id"],
        "px_id": config["px_id"],
        "stage": "gate1_public_corpus_offline",
        "status": status,
        "gate_decisions": gate_decisions,
        "gates": gates,
        "corpus": {
            "poisoned_skills": len(poisoned),
            "clean_skills": len(clean),
            "poisoned_source_doi": config["poisoned_source_doi"],
            "poisoned_source_license": config["poisoned_source_license"],
            "poisoned_archive_sha256": archive_hash,
            "clean_source_repo": config["clean_source_repo"],
            "clean_source_commit": config["clean_source_commit"],
        },
        "policies": policies,
        "determination": (
            "FAIL for provenance-only defense against authentic poisoned skills: all "
            f"{len(poisoned)} correctly identified, hash-matching, signed poisoned skills "
            "remain admissible. PASS for tamper and nonexistent-name rejection, with no "
            "false rejects on the clean snapshot."
        ),
        "claim_boundary": config["claim_boundary"],
    }
    out = Path(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (out / "source_inventory.jsonl").open("w", encoding="utf-8") as handle:
        for row in clean + poisoned:
            handle.write(json.dumps(row) + "\n")
    with (out / "primary_policy_outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for row in primary_rows:
            handle.write(json.dumps(row) + "\n")
    (out / "PX062_GATE1_PUBLIC_CORPUS_DETERMINATION.md").write_text(
        render(result), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px062_public_corpus_gate1_20260724.json"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))


if __name__ == "__main__":
    main()
