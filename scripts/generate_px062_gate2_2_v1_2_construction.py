#!/usr/bin/env python
"""Deterministically derive PX-062 Gate 2.2 v1.2 construction artifacts.

Only the ten-row union rejected by the sealed v1.1 dual label audit is
replaced.  The generator consumes no Qwen or Mistral target-model outcome and
refuses any drift in the v1.1 corpus, audit pair, or invalidation seal.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.build_px062_gate2_2_v12_benchmark import (
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        build_artifacts,
    )
except ImportError:  # direct execution from scripts/
    from build_px062_gate2_2_v12_benchmark import (  # type: ignore[no-redef]
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        build_artifacts,
    )


ROOT = Path(__file__).resolve().parents[1]
V11_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-1-20260728"
V12_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-2-20260728"
V11_SEED = Path("manifests/px062_gate2_2_v1_1_20260728/task_seed_bank.json")
V11_LINEAGE = Path("manifests/px062_gate2_2_v1_1_20260728/task_lineage.json")
V11_CONFIG = Path("configs/px062_skill_selection_gate2_2_v1_1_20260728.json")
V11_GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728"
)
V11_FROZEN = V11_GATE / "frozen_inputs"
V11_AUDIT_1 = V11_GATE / "label_audit_1_predictions.jsonl"
V11_AUDIT_2 = V11_GATE / "label_audit_2_predictions.jsonl"
V11_INVALIDATION = V11_GATE / "label_audit_invalidation.json"
V11_CONFLICTS = V11_GATE / "label_audit_conflicts.jsonl"
V11_PAIR_MANIFEST = V11_GATE / "label_audit_evidence_manifest.json"

V12_SEED = Path("manifests/px062_gate2_2_v1_2_20260728/task_seed_bank.json")
V12_LINEAGE = Path("manifests/px062_gate2_2_v1_2_20260728/task_lineage.json")
V12_CONFIG = Path("configs/px062_skill_selection_gate2_2_v1_2_20260728.json")
V12_GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728"
)
V12_FROZEN = V12_GATE / "frozen_inputs"
V12_PROTOCOL = V12_GATE / "LABEL_AUDIT_PROTOCOL_V1_2_20260728.md"
V12_RUNNER = Path("scripts/run_px062_gate2_2_v12_blind_audit.py")
V12_TESTS = Path("tests/test_px062_gate2_2_v12_blind_audit.py")

EXPECTED_V11_HASHES = {
    V11_SEED.as_posix(): "83e557925bb4d4f9cc38f9f1ab2de40f73769dcb8af287643870de914d2cdc89",
    V11_LINEAGE.as_posix(): "f3ad547ce00a09f9f9aa49823404ad6b9b688d1340155010da8d958ff23e107a",
    V11_CONFIG.as_posix(): "24f7260197d53dd68657f2558aac6d5aaca8512ad2bbc988c46251c666fc0117",
    (V11_FROZEN / "tasks.jsonl").as_posix(): "68f776fe51ce3d2bd7eef42124448a1a6f58c0b0c6213fbd34b4b1e1e155ddbb",
    (V11_FROZEN / "answer_key.jsonl").as_posix(): "2c2b1561b2beeb72584df3ed9dfe3a848e40b5f4bc4c74b2773e15038f616e38",
    (V11_FROZEN / "registry_catalog.json").as_posix(): "ec12c41e14c086f41a2bb42ddff8b7e137ba15d89bb12fb7645f6440a09f5d8b",
    (V11_FROZEN / "benchmark_manifest.json").as_posix(): "bbf7c24d9a8bb661f82edb3f3ebe553ad3d3cb8bafa508cfce6ef22eb9559518",
    V11_AUDIT_1.as_posix(): "9a13e76908616017330f6f5a4c95052c699a1eeddf9625271e241c57b807efcd",
    (V11_GATE / "label_audit_1_run.json").as_posix(): "c565f261a55bb65302ec56e058a6643ed252e27aa3e4f2476c950cfa24587d84",
    V11_AUDIT_2.as_posix(): "2687bcb826353f0606bef7f68c4f645cb823872d8e1c5c036b6810345ada6bc8",
    (V11_GATE / "label_audit_2_run.json").as_posix(): "dab26de3e3d33f278190bc937493734cf0b2dff713839e0310b78d346bdacfd6",
    V11_PAIR_MANIFEST.as_posix(): "5ad6e4631d82095d60bc46d736a795b330d27742018554e4b6fff1954a562654",
    V11_INVALIDATION.as_posix(): "5fb5e72d9db7cde210041baea33ab551b89a43772580ccf7d74391a50ba4f09e",
    V11_CONFLICTS.as_posix(): "bf89fd32a617e90315bd9f3aaa08aee3cbf4ab8f2e47db08455c249233bdeea6",
}


@dataclass(frozen=True)
class Replacement:
    collection: str
    owner: str
    field: str
    index: int
    old_task_id: str
    new_task_id: str
    old_request: str
    new_request: str
    semantic_boundary: str

    @property
    def seed_location(self) -> str:
        return f"{self.collection}/{self.owner}/{self.field}[{self.index}]"


R = Replacement
REPLACEMENTS = (
    R(
        "skill_scenarios",
        "figma-implement-design",
        "misleading_requests",
        1,
        "g22-025e0d91f08447ad6b56",
        "g22-d13ef9177f21766c2247",
        "Match the reference interface precisely in code, including spacing, states, and breakpoints.",
        "Implement the supplied Figma frame as production React components with pixel-accurate spacing, states, and responsive breakpoints.",
        "Make the frozen Figma-source prerequisite explicit.",
    ),
    R(
        "unsupported_domains",
        "microsoft-word",
        "misleading_scenarios",
        1,
        "g22-090cf3dbcfda1374058e",
        "g22-30e5c6841145d39c80c0",
        "Replace manual font formatting with named styles across the entire policy document.",
        "In Microsoft Word, replace manual font formatting with named paragraph and character styles and save the editable .docx.",
        "Specify a Word-native editable-document operation outside the PDF workflow.",
    ),
    R(
        "unsupported_domains",
        "microsoft-word",
        "requests",
        0,
        "g22-34f70a7c6824f712d531",
        "g22-d08cbcea5f5e2172230c",
        "Apply consistent heading styles throughout this Microsoft Word .docx manuscript without changing its wording.",
        "Use Microsoft Word's Styles pane to redefine Heading 1 through Heading 3 in this editable .docx and refresh its automatic table of contents.",
        "Specify Word-only style and table-of-contents controls outside the PDF workflow.",
    ),
    R(
        "unsupported_domains",
        "jira-project-management",
        "requests",
        4,
        "g22-3c32b30f73db5c8c604d",
        "g22-52be56561ec321f8a169",
        "Build a dashboard showing sprint progress, aging blockers, and defects by component.",
        "Build a Jira dashboard showing sprint progress, aging blockers, and defects grouped by component.",
        "Identify Jira explicitly so the request is not misread as Linear work.",
    ),
    R(
        "unsupported_domains",
        "redis-data-store",
        "requests",
        5,
        "g22-4916f14d99b5770e0a99",
        "g22-f2d8b040fe58589432d2",
        "Build a publish and subscribe channel for short-lived application notifications.",
        "Implement a Redis Pub/Sub channel for short-lived application notifications, including subscriber reconnect handling.",
        "Identify Redis explicitly so the request is outside ASP.NET Core SignalR.",
    ),
    R(
        "skill_scenarios",
        "figma-implement-design",
        "misleading_requests",
        2,
        "g22-bd27c1476142d5a78ab6",
        "g22-270a8d5b611c01dc8790",
        "Translate this approved mobile flow into accessible production components and navigation.",
        "Translate the linked Figma mobile flow into accessible production components and navigation while matching every screen and state.",
        "Make the frozen Figma-source prerequisite explicit.",
    ),
    R(
        "skill_scenarios",
        "render-deploy",
        "misleading_requests",
        1,
        "g22-d2415b909af629557321",
        "g22-a3d30ca7826f77d575cb",
        "Configure the web service, worker, database connection, and environment values for release.",
        "Update this Render Blueprint so its web service and worker share the managed database connection and environment group before deployment.",
        "Identify the frozen Render deployment platform and Blueprint workflow.",
    ),
    R(
        "skill_scenarios",
        "plugin-creator",
        "requests",
        7,
        "g22-e7f3ef2a5e2330274261",
        "g22-002376b0b2382bbaa705",
        "Prepare an existing local plugin for a cache-busted reinstall during development.",
        "Add the missing optional capability folders to this existing Codex plugin and update its repo-root marketplace entry for ordering and availability.",
        "Align the task with the frozen plugin structure and marketplace-entry scope.",
    ),
    R(
        "unsupported_domains",
        "jira-project-management",
        "requests",
        6,
        "g22-f66eb19f297bf8044a57",
        "g22-34675d06cad55d9e3cae",
        "Set component leads and default assignees for the newly reorganized engineering areas.",
        "In Jira, set component leads and default assignees for the newly reorganized engineering areas.",
        "Identify Jira explicitly so the request is not misread as Linear work.",
    ),
    R(
        "unsupported_domains",
        "microsoft-teams",
        "misleading_scenarios",
        0,
        "g22-f6970c9769c63fa33cee",
        "g22-2057edd26372c2fd55d5",
        "Create a team from the approved template and assign the two designated owners.",
        "Create a Microsoft Teams team from the approved template and assign the two designated owners.",
        "Identify Microsoft Teams explicitly so the request is not misread as Linear work.",
    ),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def jsonl(raw: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


def verify_v11_sources(root: Path) -> None:
    for relative, expected in EXPECTED_V11_HASHES.items():
        actual = sha256((root / relative).read_bytes())
        if actual != expected:
            raise ValueError(f"v1.1 source drift: {relative}: {actual} != {expected}")


def verify_v11_conflicts(root: Path) -> dict[str, dict[str, Any]]:
    answers = jsonl((root / V11_FROZEN / "answer_key.jsonl").read_bytes())
    audit_1 = jsonl((root / V11_AUDIT_1).read_bytes())
    audit_2 = jsonl((root / V11_AUDIT_2).read_bytes())
    task_ids = [row["task_id"] for row in answers]
    if [row["task_id"] for row in audit_1] != task_ids:
        raise ValueError("v1.1 audit 1 task order drift")
    if [row["task_id"] for row in audit_2] != task_ids:
        raise ValueError("v1.1 audit 2 task order drift")
    truth = {row["task_id"]: row["expected_skill"] for row in answers}
    first = {row["task_id"]: row for row in audit_1}
    second = {row["task_id"]: row for row in audit_2}
    d1 = {task_id for task_id in task_ids if first[task_id]["predicted_skill"] != truth[task_id]}
    d2 = {task_id for task_id in task_ids if second[task_id]["predicted_skill"] != truth[task_id]}
    cross = {task_id for task_id in task_ids if first[task_id]["predicted_skill"] != second[task_id]["predicted_skill"]}
    union = d1 | d2 | cross
    expected = {item.old_task_id for item in REPLACEMENTS}
    if (len(d1), len(d2), len(cross), len(union)) != (3, 9, 8, 10):
        raise ValueError("v1.1 semantic disagreement counts drift")
    if union != expected:
        raise ValueError("v1.2 replacements are not the complete v1.1 conflict union")
    ledger = jsonl((root / V11_CONFLICTS).read_bytes())
    if {row["task_id"] for row in ledger} != union or len(ledger) != 10:
        raise ValueError("v1.1 conflict ledger does not equal the recomputed union")
    invalidation = json.loads((root / V11_INVALIDATION).read_text(encoding="utf-8"))
    gate = invalidation.get("semantic_gate", {})
    if (
        invalidation.get("status") != "INVALIDATED_LABEL_AUDIT_SEMANTIC_GATE_FAILED"
        or gate.get("audit_1_disagreements_with_frozen_answer") != 3
        or gate.get("audit_2_disagreements_with_frozen_answer") != 9
        or gate.get("cross_audit_disagreement_rows") != 8
        or gate.get("union_nonunanimous_rows") != 10
        or gate.get("three_way_unanimous_rows") != 1022
    ):
        raise ValueError("v1.1 invalidation semantic gate drift")
    return {row["task_id"]: row for row in ledger}


def replace_seed(seed: dict[str, Any]) -> dict[str, Any]:
    revised = copy.deepcopy(seed)
    by_skill = {row["skill"]: row for row in revised["skill_scenarios"]}
    by_domain = {row["slug"]: row for row in revised["unsupported_domains"]}
    for item in REPLACEMENTS:
        owner = (by_skill if item.collection == "skill_scenarios" else by_domain)[item.owner]
        slot = owner[item.field][item.index]
        if item.field == "misleading_scenarios":
            if slot["request"] != item.old_request:
                raise ValueError(f"v1.1 seed request drift: {item.seed_location}")
            slot["request"] = item.new_request
        else:
            if slot != item.old_request:
                raise ValueError(f"v1.1 seed request drift: {item.seed_location}")
            owner[item.field][item.index] = item.new_request
    revised["experiment_stage"] = (
        "PX-062 Gate 2.2 v1.2 context-preserving structured selection"
    )
    revised["authoring_note"] += (
        " Version v1.2 prospectively replaces the complete ten-row union "
        "rejected by the v1.1 dual label audit; the revision is "
        "label-audit-informed but Qwen/Mistral-target-outcome-blind."
    )
    governance = revised["label_governance"]
    governance.update(
        {
            "required_independent_label_audits": 2,
            "completed_independent_label_audits": 0,
            "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
            "audit_resolution": (V12_GATE / "label_audit_resolution.json").as_posix(),
            "audit_1_status": "PENDING",
            "audit_2_status": "PENDING",
            "audit_resolution_status": "PENDING",
        }
    )
    revised["revision_lineage"] = {
        "revision": "v1.2",
        "source_experiment_id": V11_EXPERIMENT_ID,
        "source_tasks_sha256": EXPECTED_V11_HASHES[(V11_FROZEN / "tasks.jsonl").as_posix()],
        "source_invalidation": V11_INVALIDATION.as_posix(),
        "source_invalidation_sha256": EXPECTED_V11_HASHES[V11_INVALIDATION.as_posix()],
        "source_pair_manifest_sha256": EXPECTED_V11_HASHES[V11_PAIR_MANIFEST.as_posix()],
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "replaced_prompt_ids": 10,
        "retained_prompt_ids": 1022,
    }
    return revised


def build_config(old: dict[str, Any], files: dict[str, bytes], root: Path) -> dict[str, Any]:
    config = copy.deepcopy(old)
    config["experiment_id"] = V12_EXPERIMENT_ID
    config["protocol_version"] = "2.2.2"
    config["seed"] = "px062-gate2-2-confirmatory-20260728-v3"
    config["parent_experiment_id"] = V11_EXPERIMENT_ID
    config["status"] = "REDESIGN_PENDING_FRESH_CORPUS_AND_DUAL_LABEL_AUDIT"
    config["revision_lineage"] = {
        "source_experiment_id": V11_EXPERIMENT_ID,
        "source_invalidation": V11_INVALIDATION.as_posix(),
        "source_invalidation_sha256": EXPECTED_V11_HASHES[V11_INVALIDATION.as_posix()],
        "source_conflicts": V11_CONFLICTS.as_posix(),
        "source_conflicts_sha256": EXPECTED_V11_HASHES[V11_CONFLICTS.as_posix()],
        "source_pair_manifest_sha256": EXPECTED_V11_HASHES[V11_PAIR_MANIFEST.as_posix()],
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "target_model_outcomes_available_at_revision": False,
        "replaced_prompt_ids": 10,
        "retained_prompt_ids": 1022,
    }
    config["frozen_inputs"] = {
        name.removesuffix(".jsonl").removesuffix(".json"): (V12_FROZEN / name).as_posix()
        for name in (
            "tasks.jsonl",
            "answer_key.jsonl",
            "registry_catalog.json",
            "benchmark_manifest.json",
        )
    }
    config["collection_output_dir"] = "outputs/px062_gate2_2_v1_2"
    config["source_integrity"] = {
        "tasks_sha256": sha256(files["tasks.jsonl"]),
        "answer_key_sha256": sha256(files["answer_key.jsonl"]),
        "registry_catalog_sha256": sha256(files["registry_catalog.json"]),
        "benchmark_manifest_sha256": sha256(files["benchmark_manifest.json"]),
    }
    audit_sources = {
        "protocol_sha256": V12_PROTOCOL,
        "runner_sha256": V12_RUNNER,
        "tests_sha256": V12_TESTS,
    }
    for field, path in audit_sources.items():
        source = root / path
        if not source.is_file():
            raise ValueError(f"v1.2 audit source is not frozen: {path.as_posix()}")
        config["label_audit_protocol"][field] = sha256(source.read_bytes())
    return config


def construction(root: Path) -> dict[Path, bytes]:
    verify_v11_sources(root)
    conflict_ledger = verify_v11_conflicts(root)
    old_seed = json.loads((root / V11_SEED).read_text(encoding="utf-8"))
    revised_seed = replace_seed(old_seed)
    seed_raw = pretty(revised_seed)
    files = build_artifacts(
        root=root,
        seed_bank_path=root / V12_SEED,
        registry_path=root / DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=root / DEFAULT_PRIOR_TASKS,
        seed_bank_override=revised_seed,
        seed_bank_raw_override=seed_raw,
    )
    old_tasks = {row["task_id"]: row for row in jsonl((root / V11_FROZEN / "tasks.jsonl").read_bytes())}
    old_answers = {row["task_id"]: row for row in jsonl((root / V11_FROZEN / "answer_key.jsonl").read_bytes())}
    new_tasks = {row["task_id"]: row for row in jsonl(files["tasks.jsonl"])}
    new_answers = {row["task_id"]: row for row in jsonl(files["answer_key.jsonl"])}
    old_ids, new_ids = set(old_tasks), set(new_tasks)
    if (
        len(old_ids & new_ids) != 1022
        or len(old_ids - new_ids) != 10
        or len(new_ids - old_ids) != 10
    ):
        raise ValueError("v1.2 lineage cardinality drift")
    if old_ids - new_ids != {item.old_task_id for item in REPLACEMENTS}:
        raise ValueError("v1.2 did not replace the complete frozen conflict union")
    lineage_rows = []
    for item in REPLACEMENTS:
        if item.old_task_id not in old_tasks or item.old_task_id in new_tasks:
            raise ValueError(f"old task lineage drift: {item.old_task_id}")
        if item.new_task_id not in new_tasks or item.new_task_id in old_tasks:
            raise ValueError(f"new task lineage drift: {item.new_task_id}")
        old_answer = old_answers[item.old_task_id]
        new_answer = new_answers[item.new_task_id]
        if (old_answer["task_type"], old_answer["expected_skill"]) != (
            new_answer["task_type"], new_answer["expected_skill"]
        ):
            raise ValueError(f"label semantic drift: {item.seed_location}")
        source_conflict = conflict_ledger[item.old_task_id]
        lineage_rows.append(
            {
                "seed_location": item.seed_location,
                "old_task_id": item.old_task_id,
                "new_task_id": item.new_task_id,
                "task_type": old_answer["task_type"],
                "expected_skill": old_answer["expected_skill"],
                "source_audit_1_predicted_skill": source_conflict["audit_1"]["predicted_skill"],
                "source_audit_2_predicted_skill": source_conflict["audit_2"]["predicted_skill"],
                "semantic_boundary": item.semantic_boundary,
                "old_request": item.old_request,
                "new_request": item.new_request,
            }
        )
    old_catalog = json.loads((root / V11_FROZEN / "registry_catalog.json").read_text(encoding="utf-8"))
    new_catalog = json.loads(files["registry_catalog.json"])
    if old_catalog["names"] != new_catalog["names"] or old_catalog["entries"] != new_catalog["entries"]:
        raise ValueError("v1.2 changed frozen registry semantics")
    manifest = json.loads(files["benchmark_manifest.json"])
    lineage = {
        "schema_version": "px062-gate2.2-v1.2-task-lineage-v1",
        "experiment_id": V12_EXPERIMENT_ID,
        "status": "PROSPECTIVE_LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "source": {
            "experiment_id": V11_EXPERIMENT_ID,
            "tasks_sha256": EXPECTED_V11_HASHES[(V11_FROZEN / "tasks.jsonl").as_posix()],
            "invalidation_path": V11_INVALIDATION.as_posix(),
            "invalidation_sha256": EXPECTED_V11_HASHES[V11_INVALIDATION.as_posix()],
            "conflicts_path": V11_CONFLICTS.as_posix(),
            "conflicts_sha256": EXPECTED_V11_HASHES[V11_CONFLICTS.as_posix()],
            "audit_pair_manifest_path": V11_PAIR_MANIFEST.as_posix(),
            "audit_pair_manifest_sha256": EXPECTED_V11_HASHES[V11_PAIR_MANIFEST.as_posix()],
        },
        "target": {
            "seed_bank_sha256": sha256(seed_raw),
            "tasks_sha256": sha256(files["tasks.jsonl"]),
            "answer_key_sha256": sha256(files["answer_key.jsonl"]),
            "registry_catalog_sha256": sha256(files["registry_catalog.json"]),
            "benchmark_manifest_sha256": sha256(files["benchmark_manifest.json"]),
        },
        "invariants": {
            "old_tasks": len(old_ids),
            "new_tasks": len(new_ids),
            "retained_prompt_ids": len(old_ids & new_ids),
            "replaced_prompt_ids": len(old_ids - new_ids),
            "new_prompt_ids": len(new_ids - old_ids),
            "registered_labels": manifest["counts"]["expected_registered_skill"],
            "none_labels": manifest["counts"]["expected_none"],
            "task_type_counts": manifest["counts"]["by_type"],
            "lexical_balanced_accuracy": manifest["anti_lexical_leakage"]["shallow_grouped_classifier"]["balanced_accuracy"],
            "lexical_balanced_accuracy_limit_exclusive": 0.85,
            "all_construction_gates_passed": True,
            "two_fresh_full_1032_row_audits_required": True,
            "source_audits_reusable_for_acceptance": False,
        },
        "replacements": lineage_rows,
    }
    old_config = json.loads((root / V11_CONFIG).read_text(encoding="utf-8"))
    config = build_config(old_config, files, root)
    outputs: dict[Path, bytes] = {
        V12_SEED: seed_raw,
        V12_LINEAGE: pretty(lineage),
        V12_CONFIG: pretty(config),
    }
    outputs.update({V12_FROZEN / name: raw for name, raw in files.items()})
    return outputs


def write_exclusive(root: Path, outputs: dict[Path, bytes]) -> None:
    collisions = [path for path in outputs if (root / path).exists()]
    if collisions:
        raise FileExistsError(f"refusing to overwrite v1.2 outputs: {collisions}")
    for path, raw in outputs.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw)


def verify_existing(root: Path, outputs: dict[Path, bytes]) -> None:
    for path, raw in outputs.items():
        target = root / path
        if not target.is_file() or target.read_bytes() != raw:
            raise ValueError(f"generated v1.2 artifact drift: {path.as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify-existing", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = construction(root)
    if args.write:
        write_exclusive(root, outputs)
    if args.verify_existing:
        verify_existing(root, outputs)
    print(
        json.dumps(
            {
                "mode": "write" if args.write else "check-only",
                "verified_existing": args.verify_existing,
                "files": {
                    path.as_posix(): {"bytes": len(raw), "sha256": sha256(raw)}
                    for path, raw in sorted(outputs.items(), key=lambda item: item[0].as_posix())
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
