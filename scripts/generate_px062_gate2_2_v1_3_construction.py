#!/usr/bin/env python
"""Deterministically derive PX-062 Gate 2.2 v1.3 construction artifacts.

Only the nine-row union rejected by the sealed v1.2 dual label audit is
replaced. The revision consumes no Qwen or Mistral target-model outcome. It
also prospectively replaces the empirically brittle all-row unanimity rule
with a balanced four-pass, 3-of-4 consensus rule before target collection.
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
    from scripts.build_px062_gate2_2_v13_benchmark import (
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        PENDING_LABEL_STATUS,
        build_artifacts,
    )
    from scripts.generate_px062_gate2_2_v1_2_construction import (
        verify_v11_sources,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    from build_px062_gate2_2_v13_benchmark import (  # type: ignore[no-redef]
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        PENDING_LABEL_STATUS,
        build_artifacts,
    )
    from generate_px062_gate2_2_v1_2_construction import (  # type: ignore[no-redef]
        verify_v11_sources,
    )


ROOT = Path(__file__).resolve().parents[1]
V12_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-2-20260728"
V13_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-3-20260728"
V11_GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728"
)
V12_SEED = Path("manifests/px062_gate2_2_v1_2_20260728/task_seed_bank.json")
V12_LINEAGE = Path("manifests/px062_gate2_2_v1_2_20260728/task_lineage.json")
V12_CONFIG = Path("configs/px062_skill_selection_gate2_2_v1_2_20260728.json")
V12_GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728"
)
V12_FROZEN = V12_GATE / "frozen_inputs"
V12_AUDIT_1 = V12_GATE / "label_audit_1_predictions.jsonl"
V12_AUDIT_2 = V12_GATE / "label_audit_2_predictions.jsonl"
V12_INVALIDATION = V12_GATE / "label_audit_invalidation.json"
V12_CONFLICTS = V12_GATE / "label_audit_conflicts.jsonl"
V12_PAIR_MANIFEST = V12_GATE / "label_audit_evidence_manifest.json"

V13_SEED = Path("manifests/px062_gate2_2_v1_3_20260728/task_seed_bank.json")
V13_LINEAGE = Path("manifests/px062_gate2_2_v1_3_20260728/task_lineage.json")
V13_CONFIG = Path("configs/px062_skill_selection_gate2_2_v1_3_20260728.json")
V13_GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728"
)
V13_FROZEN = V13_GATE / "frozen_inputs"
V13_PROTOCOL = V13_GATE / "LABEL_AUDIT_PROTOCOL_V1_3_20260728.md"
V13_ADDENDUM = V13_GATE / "PX062_GATE2_2_V1_3_PREREG_ADDENDUM_20260728.md"
V13_RUNNER = Path("scripts/run_px062_gate2_2_v13_blind_audit.py")
V13_CORE_RUNNER = Path("scripts/run_px062_gate2_2_blind_audit.py")
V13_BUILDER = Path("scripts/build_px062_gate2_2_v13_benchmark.py")
V13_BASE_BUILDER = Path("scripts/build_px062_gate2_2_benchmark.py")
V13_V11_BUILDER = Path("scripts/build_px062_gate2_2_v11_benchmark.py")
V13_V11_RUNNER = Path("scripts/run_px062_gate2_2_v11_blind_audit.py")
V13_VERIFIER = Path("scripts/verify_px062_gate2_2_v13_label_audits.py")
V13_V11_VERIFIER = Path("scripts/verify_px062_gate2_2_v11_label_audits.py")
V13_FINALIZER = Path("scripts/finalize_px062_gate2_2_v13_labels.py")
V13_V11_FINALIZER = Path("scripts/finalize_px062_gate2_2_v11_labels.py")
V13_TESTS = Path("tests/test_px062_gate2_2_v13_blind_audit.py")

EXPECTED_V12_HASHES = {
    V12_SEED.as_posix(): "b504f37942c6bb4103cfa20ac9b89cc2bb56b6e49ad9187883cff9e3aa201cce",
    V12_LINEAGE.as_posix(): "36dbb89d20e38dab7ebfbde13008187306fa0275b025efe5627b1b42eb2b9835",
    V12_CONFIG.as_posix(): "8ccd093686dde9f977fc18fe9250c49a17555cd3a5a2f5b54532346957519ca5",
    (V12_FROZEN / "tasks.jsonl").as_posix(): "e9a4c387781b7299884d75ebbb59f3ba1dcd398599821fb586db95e02fabea16",
    (V12_FROZEN / "answer_key.jsonl").as_posix(): "c9fb2c8be3ee200050f709a046109c42884aea741e980371837bd58f741f3913",
    (V12_FROZEN / "registry_catalog.json").as_posix(): "90a6f8cd28a489a448fae49198fde3ff34514b2b4a2aab421f05314441523212",
    (V12_FROZEN / "benchmark_manifest.json").as_posix(): "93a126f0fed68d259caae32bd2a0eae8af4f656bbebdcda07dac880aa9e3eb57",
    V12_AUDIT_1.as_posix(): "6431735b6cbfb339cb63e3294f8cb0f8021bc81792b0e5d38ec19bda2ce0ea54",
    (V12_GATE / "label_audit_1_run.json").as_posix(): "d1887088bc166c7b353add988c8400a2f481c99f34cce8086fd400f3255be5fb",
    V12_AUDIT_2.as_posix(): "4dcf50715205e22eb220dd44d28dee85cbf9df127f1321b9c0394db942224cb8",
    (V12_GATE / "label_audit_2_run.json").as_posix(): "12c834e3390b603d52cac3d6c42e0f3ee480fa1d44511724386112af0bc333c2",
    V12_PAIR_MANIFEST.as_posix(): "f34151882216c35196bd0c26d80f7603bb371187efe3862fa6eacc96ef4b90c0",
    V12_INVALIDATION.as_posix(): "dc9a66283ad4a0a7cd7e5fd384f4d369232018aef1e4431bc2073cf8e23728fa",
    V12_CONFLICTS.as_posix(): "76188a8817ef236ef0a9afe7859d4e28546e08df388a5a553a337c6143780693",
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
        "plugin-creator",
        "misleading_requests",
        3,
        "g22-fad3a4ce2fca544b9b5f",
        "g22-05009a213453e7d6dff0",
        "Update this development extension, increment its cache marker, and prepare it for reinstall.",
        "Correct this local Codex plugin's `.codex-plugin/plugin.json`, then add its missing `.agents/plugins/marketplace.json` record with ordering and availability fields.",
        "State the frozen Codex plugin-manifest and marketplace-entry scope.",
    ),
    R(
        "skill_scenarios",
        "openai-docs",
        "misleading_requests",
        3,
        "g22-82761cfbfa94dfae99b2",
        "g22-7c684da2b061c269d0a3",
        "Check the official platform guidance for handling streaming events in this integration.",
        "Use current official OpenAI API documentation to identify the server-sent event types emitted while the Responses API streams output, and cite the relevant reference pages.",
        "Identify the OpenAI API and first-party documentation boundary explicitly.",
    ),
    R(
        "unsupported_domains",
        "jira-project-management",
        "requests",
        5,
        "g22-8b7b56e190f2312fb283",
        "g22-98530a80b5f25e0032d1",
        "Configure an automation rule that assigns new incidents according to the affected service.",
        "In Jira Service Management, configure an automation rule that looks up the owner of the selected Affected service asset and assigns each newly created incident to that owner.",
        "Identify Jira Service Management so the task cannot be treated as Linear work.",
    ),
    R(
        "unsupported_domains",
        "microsoft-word",
        "requests",
        6,
        "g22-bb0d7c7edce005804187",
        "g22-a714fb66f15b32e3c59e",
        "Create a protected Word form with text, date, checkbox, and dropdown controls.",
        "In Microsoft Word, create a repeating-section content control for line items, bind its child controls to custom XML, restrict editing to filling the form, and save the editable `.docx`.",
        "Specify Word-native editable DOCX controls outside the PDF workflow.",
    ),
    R(
        "unsupported_domains",
        "microsoft-word",
        "requests",
        0,
        "g22-d08cbcea5f5e2172230c",
        "g22-39d85e405d26fb74a7b8",
        "Use Microsoft Word's Styles pane to redefine Heading 1 through Heading 3 in this editable .docx and refresh its automatic table of contents.",
        "In Microsoft Word, insert a `STYLEREF` field in each section header so it automatically displays the nearest Heading 1 text in the editable `.docx`.",
        "Specify a Word-native dynamic field outside the PDF workflow.",
    ),
    R(
        "unsupported_domains",
        "confluence-wiki",
        "misleading_scenarios",
        2,
        "g22-d858bafd874846ce9561",
        "g22-5d1fc14574ec10e69e04",
        "Label and reorganize the incident retrospectives so they can be browsed by service.",
        "In Confluence Cloud, add a Service page property to each incident retrospective and configure a Page Properties Report macro that lets readers filter those pages by service.",
        "Identify Confluence-native properties and macros outside Notion capture.",
    ),
    R(
        "unsupported_domains",
        "microsoft-word",
        "misleading_scenarios",
        1,
        "g22-30e5c6841145d39c80c0",
        "g22-00775f6db2ed35aca4d5",
        "In Microsoft Word, replace manual font formatting with named paragraph and character styles and save the editable .docx.",
        "In Microsoft Word, link a custom multilevel list to the Heading 1, Heading 2, and Heading 3 styles so section numbers update automatically in the editable `.docx`.",
        "Specify Word-native multilevel-list behavior outside the PDF workflow.",
    ),
    R(
        "unsupported_domains",
        "microsoft-word",
        "misleading_scenarios",
        3,
        "g22-33dfe355b2fcd2f68dd9",
        "g22-46d79ad163f4d04440f5",
        "Turn this finished Microsoft Word report into a reusable .dotx template with locked branding elements.",
        "In Microsoft Word, save the approved legal clause as an AutoText Building Block in a reusable `.dotx` template, preserving its gallery and category metadata.",
        "Specify a Word-native DOTX Building Block operation outside PDF work.",
    ),
    R(
        "skill_scenarios",
        "notion-spec-to-implementation",
        "requests",
        5,
        "g22-a5ed94aa6c8c52b9e472",
        "g22-638ceef53d502be0613e",
        "Convert the feature requirements into a sequenced plan with ownership fields.",
        "Use the linked Notion feature specification to create workspace tasks, assign owners, record dependencies, group the work into milestones, and track delivery status.",
        "State the Notion feature-specification and tracked implementation scope.",
    ),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def jsonl(raw: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


def verify_v12_sources(root: Path) -> None:
    verify_v11_sources(root)
    for relative, expected in EXPECTED_V12_HASHES.items():
        path = root / relative
        if not path.is_file() or sha256(path.read_bytes()) != expected:
            raise ValueError(f"sealed v1.2 source drift: {relative}")


def verify_v12_conflicts(root: Path) -> dict[str, dict[str, Any]]:
    answers = jsonl((root / V12_FROZEN / "answer_key.jsonl").read_bytes())
    audit_1 = jsonl((root / V12_AUDIT_1).read_bytes())
    audit_2 = jsonl((root / V12_AUDIT_2).read_bytes())
    task_ids = [row["task_id"] for row in answers]
    if [row["task_id"] for row in audit_1] != task_ids:
        raise ValueError("v1.2 audit 1 order drift")
    if [row["task_id"] for row in audit_2] != task_ids:
        raise ValueError("v1.2 audit 2 order drift")
    truth = {row["task_id"]: row["expected_skill"] for row in answers}
    first = {row["task_id"]: row for row in audit_1}
    second = {row["task_id"]: row for row in audit_2}
    d1 = {task_id for task_id in task_ids if first[task_id]["predicted_skill"] != truth[task_id]}
    d2 = {task_id for task_id in task_ids if second[task_id]["predicted_skill"] != truth[task_id]}
    cross = {task_id for task_id in task_ids if first[task_id]["predicted_skill"] != second[task_id]["predicted_skill"]}
    union = d1 | d2 | cross
    expected = {item.old_task_id for item in REPLACEMENTS}
    if (len(d1), len(d2), len(cross), len(union)) != (2, 7, 9, 9):
        raise ValueError("v1.2 semantic disagreement counts drift")
    if union != expected:
        raise ValueError("v1.3 replacements are not the complete v1.2 conflict union")
    ledger = jsonl((root / V12_CONFLICTS).read_bytes())
    if [row["task_id"] for row in ledger] != [task_id for task_id in task_ids if task_id in union]:
        raise ValueError("v1.2 conflict ledger order/content drift")
    invalidation = json.loads((root / V12_INVALIDATION).read_text(encoding="utf-8"))
    gate = invalidation.get("semantic_gate", {})
    if (
        invalidation.get("status") != "INVALIDATED_LABEL_AUDIT_SEMANTIC_GATE_FAILED"
        or gate.get("audit_1_disagreements_with_frozen_answer") != 2
        or gate.get("audit_2_disagreements_with_frozen_answer") != 7
        or gate.get("cross_audit_disagreement_rows") != 9
        or gate.get("union_nonunanimous_rows") != 9
        or gate.get("three_way_unanimous_rows") != 1023
    ):
        raise ValueError("v1.2 invalidation semantic gate drift")
    return {row["task_id"]: row for row in ledger}


def verify_retained_row_stochasticity(root: Path) -> dict[str, Any]:
    """Recompute the evidence that motivated policy redesign, not prompt edits."""

    def keyed(path: Path) -> dict[str, dict[str, Any]]:
        return {row["task_id"]: row for row in jsonl((root / path).read_bytes())}

    old_tasks = keyed(V11_GATE / "frozen_inputs/tasks.jsonl")
    new_tasks = keyed(V12_FROZEN / "tasks.jsonl")
    retained = sorted(set(old_tasks).intersection(new_tasks))
    if len(retained) != 1022:
        raise ValueError("v1.1-to-v1.2 retained-row count drift")
    old_audits = [
        keyed(V11_GATE / f"label_audit_{slot}_predictions.jsonl") for slot in (1, 2)
    ]
    new_audits = [keyed(V12_GATE / f"label_audit_{slot}_predictions.jsonl") for slot in (1, 2)]
    old_answers = keyed(V11_GATE / "frozen_inputs/answer_key.jsonl")
    new_answers = keyed(V12_FROZEN / "answer_key.jsonl")
    changed = [
        [task_id for task_id in retained if old_audits[index][task_id]["predicted_skill"] != new_audits[index][task_id]["predicted_skill"]]
        for index in (0, 1)
    ]
    if [len(rows) for rows in changed] != [2, 5]:
        raise ValueError("retained-row auditor stochasticity evidence drift")
    if set(changed[0]).intersection(changed[1]):
        raise ValueError("unexpected overlap in retained-row changed decisions")
    changed_union = set(changed[0]).union(changed[1])
    previously_unanimous_with_key = {
        task_id
        for task_id in changed_union
        if old_audits[0][task_id]["predicted_skill"]
        == old_audits[1][task_id]["predicted_skill"]
        == old_answers[task_id]["expected_skill"]
        == new_answers[task_id]["expected_skill"]
    }
    if len(changed_union) != 7 or previously_unanimous_with_key != changed_union:
        raise ValueError(
            "retained-row changes were not all previously unanimous with a stable key"
        )
    return {
        "retained_prompts_compared": 1022,
        "sol_same_decisions": 1020,
        "sol_changed_decisions": 2,
        "terra_same_decisions": 1017,
        "terra_changed_decisions": 5,
        "changed_decision_union": len(changed_union),
        "previously_unanimous_with_key_rows": len(previously_unanimous_with_key),
        "all_changed_rows_were_previously_unanimous_with_key": (
            previously_unanimous_with_key == changed_union
        ),
        "interpretation": (
            "The old all-1032 two-pass unanimity gate is sensitive to isolated "
            "fresh-run label noise on unchanged prompts."
        ),
    }


def verify_retained_option_map_rotation(
    root: Path, new_tasks_raw: bytes
) -> dict[str, Any]:
    """Disclose rank-driven map rotations without calling them row retention."""

    old_tasks = {
        row["task_id"]: row
        for row in jsonl((root / V12_FROZEN / "tasks.jsonl").read_bytes())
    }
    new_tasks = {row["task_id"]: row for row in jsonl(new_tasks_raw)}
    retained = sorted(set(old_tasks).intersection(new_tasks))
    if len(retained) != 1023:
        raise ValueError("v1.2-to-v1.3 retained prompt-ID count drift")
    if any(old_tasks[task_id]["prompt"] != new_tasks[task_id]["prompt"] for task_id in retained):
        raise ValueError("a retained task ID changed prompt text")
    identical_full_rows = sum(
        old_tasks[task_id] == new_tasks[task_id] for task_id in retained
    )
    rotations: dict[int, int] = {}
    changed = 0
    for task_id in retained:
        old_map = [entry["skill"] for entry in old_tasks[task_id]["option_map"]]
        new_map = [entry["skill"] for entry in new_tasks[task_id]["option_map"]]
        if old_map == new_map:
            continue
        changed += 1
        offsets = [
            offset
            for offset in range(len(old_map))
            if new_map == old_map[offset:] + old_map[:offset]
        ]
        if len(offsets) != 1:
            raise ValueError("retained option-map change is not one pure cyclic rotation")
        rotations[offsets[0]] = rotations.get(offsets[0], 0) + 1
    if (
        identical_full_rows != 433
        or changed != 590
        or rotations != {1: 327, 2: 249, 3: 14}
    ):
        raise ValueError("retained option-map rotation disclosure drift")
    return {
        "retained_prompt_ids": 1023,
        "retained_prompt_text_unchanged": 1023,
        "byte_identical_full_task_rows": identical_full_rows,
        "option_map_rotated_rows": changed,
        "cyclic_rotation_offset_counts": {
            str(offset): count for offset, count in sorted(rotations.items())
        },
        "reason": (
            "Label-independent option maps are assigned from corpus-wide sorted "
            "prompt rank; replacing nine prompts changes some retained ranks."
        ),
        "construction_algorithm_changed": False,
    }


def replace_seed(seed: dict[str, Any]) -> dict[str, Any]:
    revised = copy.deepcopy(seed)
    by_skill = {row["skill"]: row for row in revised["skill_scenarios"]}
    by_domain = {row["slug"]: row for row in revised["unsupported_domains"]}
    for item in REPLACEMENTS:
        owner = (by_skill if item.collection == "skill_scenarios" else by_domain)[item.owner]
        slot = owner[item.field][item.index]
        if item.field == "misleading_scenarios":
            if slot["request"] != item.old_request:
                raise ValueError(f"v1.2 seed request drift: {item.seed_location}")
            slot["request"] = item.new_request
        else:
            if slot != item.old_request:
                raise ValueError(f"v1.2 seed request drift: {item.seed_location}")
            owner[item.field][item.index] = item.new_request
    revised["experiment_stage"] = (
        "PX-062 Gate 2.2 v1.3 context-preserving structured selection"
    )
    revised["authoring_note"] += (
        " Version v1.3 prospectively replaces the complete nine-row union "
        "rejected by the v1.2 dual label audit. It also freezes a balanced "
        "four-pass consensus gate before target-model collection."
    )
    old_governance = revised["label_governance"]
    revised["label_governance"] = {
        "scenario_origin": old_governance["scenario_origin"],
        "required_independent_label_audits": 4,
        "completed_independent_label_audits": 0,
        "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
        "audit_1_status": "PENDING",
        "audit_2_status": "PENDING",
        "audit_3_status": "PENDING",
        "audit_4_status": "PENDING",
        "audit_resolution_status": "PENDING",
        "audit_requirement": (
            "Four fresh full blinded passes: Sol slots 1/3 and Terra slots 2/4. "
            "Every row requires at least three key-matching votes and key support "
            "from both model families; any other row invalidates the version."
        ),
        "consensus_policy": {
            "slots": 4,
            "sol_slots": [1, 3],
            "terra_slots": [2, 4],
            "minimum_key_votes": 3,
            "require_key_support_from_each_model_family": True,
            "single_dissent_tolerated": True,
            "semantic_retry_permitted": False,
            "disputed_only_rerun_permitted": False,
            "same_version_prompt_edit_or_relabel_permitted": False,
        },
        "audit_resolution": (V13_GATE / "label_audit_resolution.json").as_posix(),
    }
    revised["revision_lineage"] = {
        "revision": "v1.3",
        "source_experiment_id": V12_EXPERIMENT_ID,
        "source_tasks_sha256": EXPECTED_V12_HASHES[(V12_FROZEN / "tasks.jsonl").as_posix()],
        "source_invalidation": V12_INVALIDATION.as_posix(),
        "source_invalidation_sha256": EXPECTED_V12_HASHES[V12_INVALIDATION.as_posix()],
        "source_pair_manifest_sha256": EXPECTED_V12_HASHES[V12_PAIR_MANIFEST.as_posix()],
        "source_conflicts_sha256": EXPECTED_V12_HASHES[V12_CONFLICTS.as_posix()],
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "replaced_prompt_ids": 9,
        "retained_prompt_ids": 1023,
        "governance_redesign": "BALANCED_FOUR_PASS_3_OF_4_WITH_FAMILY_SUPPORT",
    }
    return revised


def build_config(
    old: dict[str, Any],
    files: dict[str, bytes],
    root: Path,
    stochasticity: dict[str, Any],
    retained_projection: dict[str, Any],
) -> dict[str, Any]:
    config = copy.deepcopy(old)
    config["experiment_id"] = V13_EXPERIMENT_ID
    config["protocol_version"] = "2.2.3"
    config["seed"] = "px062-gate2-2-confirmatory-20260728-v4"
    config["parent_experiment_id"] = V12_EXPERIMENT_ID
    config["status"] = "REDESIGN_PENDING_FRESH_CORPUS_AND_BALANCED_FOUR_PASS_LABEL_AUDIT"
    config["revision_lineage"] = {
        "source_experiment_id": V12_EXPERIMENT_ID,
        "source_invalidation": V12_INVALIDATION.as_posix(),
        "source_invalidation_sha256": EXPECTED_V12_HASHES[V12_INVALIDATION.as_posix()],
        "source_conflicts": V12_CONFLICTS.as_posix(),
        "source_conflicts_sha256": EXPECTED_V12_HASHES[V12_CONFLICTS.as_posix()],
        "source_pair_manifest_sha256": EXPECTED_V12_HASHES[V12_PAIR_MANIFEST.as_posix()],
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "target_model_outcomes_available_at_revision": False,
        "replaced_prompt_ids": 9,
        "retained_prompt_ids": 1023,
    }
    config["frozen_inputs"] = {
        name.removesuffix(".jsonl").removesuffix(".json"): (V13_FROZEN / name).as_posix()
        for name in (
            "tasks.jsonl",
            "answer_key.jsonl",
            "registry_catalog.json",
            "benchmark_manifest.json",
        )
    }
    config["collection_output_dir"] = "outputs/px062_gate2_2_v1_3"
    config["source_integrity"] = {
        "tasks_sha256": sha256(files["tasks.jsonl"]),
        "answer_key_sha256": sha256(files["answer_key.jsonl"]),
        "registry_catalog_sha256": sha256(files["registry_catalog.json"]),
        "benchmark_manifest_sha256": sha256(files["benchmark_manifest.json"]),
    }
    for path in (
        V13_PROTOCOL,
        V13_RUNNER,
        V13_CORE_RUNNER,
        V13_BUILDER,
        V13_BASE_BUILDER,
        V13_V11_BUILDER,
        V13_V11_RUNNER,
        V13_VERIFIER,
        V13_V11_VERIFIER,
        V13_FINALIZER,
        V13_V11_FINALIZER,
        V13_TESTS,
    ):
        if not (root / path).is_file():
            raise ValueError(f"v1.3 audit source is not frozen: {path.as_posix()}")
    previous = config["label_audit_protocol"]
    config["label_audit_protocol"] = {
        **previous,
        "slot_models": {
            "1": "gpt-5.6-sol",
            "2": "gpt-5.6-terra",
            "3": "gpt-5.6-sol",
            "4": "gpt-5.6-terra",
        },
        "full_audit_passes": 4,
        "accepted_sessions_required": 172,
        "runner_sha256": sha256((root / V13_RUNNER).read_bytes()),
        "protocol_sha256": sha256((root / V13_PROTOCOL).read_bytes()),
        "tests_sha256": sha256((root / V13_TESTS).read_bytes()),
        "governance_code": {
            "runner_core": {
                "path": V13_CORE_RUNNER.as_posix(),
                "sha256": sha256((root / V13_CORE_RUNNER).read_bytes()),
            },
            "builder": {
                "path": V13_BUILDER.as_posix(),
                "sha256": sha256((root / V13_BUILDER).read_bytes()),
            },
            "builder_base": {
                "path": V13_BASE_BUILDER.as_posix(),
                "sha256": sha256((root / V13_BASE_BUILDER).read_bytes()),
            },
            "v11_builder": {
                "path": V13_V11_BUILDER.as_posix(),
                "sha256": sha256((root / V13_V11_BUILDER).read_bytes()),
            },
            "v11_runner": {
                "path": V13_V11_RUNNER.as_posix(),
                "sha256": sha256((root / V13_V11_RUNNER).read_bytes()),
            },
            "verifier": {
                "path": V13_VERIFIER.as_posix(),
                "sha256": sha256((root / V13_VERIFIER).read_bytes()),
            },
            "verifier_base": {
                "path": V13_V11_VERIFIER.as_posix(),
                "sha256": sha256((root / V13_V11_VERIFIER).read_bytes()),
            },
            "finalizer": {
                "path": V13_FINALIZER.as_posix(),
                "sha256": sha256((root / V13_FINALIZER).read_bytes()),
            },
            "finalizer_base": {
                "path": V13_V11_FINALIZER.as_posix(),
                "sha256": sha256((root / V13_V11_FINALIZER).read_bytes()),
            },
        },
        "filesystem_identity_policy": {
            "component_chain_symlink_junction_reparse_forbidden": True,
            "regular_file_hardlink_count_must_equal_one": True,
            "duplicate_stable_file_identities_forbidden": True,
            "canonical_evidence_directories_are_flat": True,
        },
        "prior_audit_session_blacklist": {
            "path": V12_PAIR_MANIFEST.as_posix(),
            "sha256": EXPECTED_V12_HASHES[V12_PAIR_MANIFEST.as_posix()],
            "accepted_session_count": 86,
            "accepted_session_ids_sha256": (
                "893d9aba0182f9bf5ba5a612d59eb826e9878c5d45d321805c09e5c1c9f6e632"
            ),
        },
        "slot_execution_order": [1, 2, 3, 4],
        "acceptance": (
            "for every one of 1032 rows the frozen answer receives at least 3 of "
            "4 votes, including at least one Sol and at least one Terra vote"
        ),
        "single_dissent_tolerated": True,
        "semantic_retry_permitted": False,
        "disputed_only_rerun_permitted": False,
    }
    config["label_audit_governance_rationale"] = {
        "classification": "PROSPECTIVE_GOVERNANCE_REDESIGN",
        "not_a_v1_2_rescue_or_reanalysis": True,
        "retained_row_stochasticity": stochasticity,
        "tradeoff": (
            "The rule no longer claims four-way unanimity; it requires a stable, "
            "model-family-balanced supermajority and preserves every dissent."
        ),
    }
    config["retained_task_projection"] = retained_projection
    return config


def construction(root: Path) -> dict[Path, bytes]:
    verify_v12_sources(root)
    conflict_ledger = verify_v12_conflicts(root)
    stochasticity = verify_retained_row_stochasticity(root)
    old_seed = json.loads((root / V12_SEED).read_text(encoding="utf-8"))
    revised_seed = replace_seed(old_seed)
    seed_raw = pretty(revised_seed)
    files = build_artifacts(
        root=root,
        seed_bank_path=root / V13_SEED,
        registry_path=root / DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=root / DEFAULT_PRIOR_TASKS,
        seed_bank_override=revised_seed,
        seed_bank_raw_override=seed_raw,
    )
    retained_projection = verify_retained_option_map_rotation(
        root, files["tasks.jsonl"]
    )
    old_tasks = {row["task_id"]: row for row in jsonl((root / V12_FROZEN / "tasks.jsonl").read_bytes())}
    old_answers = {row["task_id"]: row for row in jsonl((root / V12_FROZEN / "answer_key.jsonl").read_bytes())}
    new_tasks = {row["task_id"]: row for row in jsonl(files["tasks.jsonl"])}
    new_answers = {row["task_id"]: row for row in jsonl(files["answer_key.jsonl"])}
    old_ids, new_ids = set(old_tasks), set(new_tasks)
    if (
        len(old_ids & new_ids) != 1023
        or len(old_ids - new_ids) != 9
        or len(new_ids - old_ids) != 9
    ):
        raise ValueError("v1.3 lineage cardinality drift")
    if old_ids - new_ids != {item.old_task_id for item in REPLACEMENTS}:
        raise ValueError("v1.3 did not replace the complete frozen conflict union")
    lineage_rows = []
    for item in REPLACEMENTS:
        if item.new_task_id not in new_tasks:
            raise ValueError(f"new task-ID derivation drift: {item.seed_location}")
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
    old_catalog = json.loads((root / V12_FROZEN / "registry_catalog.json").read_text(encoding="utf-8"))
    new_catalog = json.loads(files["registry_catalog.json"])
    if old_catalog["names"] != new_catalog["names"] or old_catalog["entries"] != new_catalog["entries"]:
        raise ValueError("v1.3 changed frozen registry semantics")
    manifest = json.loads(files["benchmark_manifest.json"])
    if {row["label_audit_status"] for row in new_answers.values()} != {PENDING_LABEL_STATUS}:
        raise ValueError("v1.3 answer key is not uniformly pending four-pass consensus")
    lineage = {
        "schema_version": "px062-gate2.2-v1.3-task-lineage-v1",
        "experiment_id": V13_EXPERIMENT_ID,
        "status": "PROSPECTIVE_LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "source": {
            "experiment_id": V12_EXPERIMENT_ID,
            "tasks_sha256": EXPECTED_V12_HASHES[(V12_FROZEN / "tasks.jsonl").as_posix()],
            "invalidation_path": V12_INVALIDATION.as_posix(),
            "invalidation_sha256": EXPECTED_V12_HASHES[V12_INVALIDATION.as_posix()],
            "conflicts_path": V12_CONFLICTS.as_posix(),
            "conflicts_sha256": EXPECTED_V12_HASHES[V12_CONFLICTS.as_posix()],
            "audit_pair_manifest_path": V12_PAIR_MANIFEST.as_posix(),
            "audit_pair_manifest_sha256": EXPECTED_V12_HASHES[V12_PAIR_MANIFEST.as_posix()],
        },
        "target": {
            "seed_bank_sha256": sha256(seed_raw),
            "tasks_sha256": sha256(files["tasks.jsonl"]),
            "answer_key_sha256": sha256(files["answer_key.jsonl"]),
            "registry_catalog_sha256": sha256(files["registry_catalog.json"]),
            "benchmark_manifest_sha256": sha256(files["benchmark_manifest.json"]),
        },
        "governance_redesign": {
            "policy": "BALANCED_FOUR_PASS_3_OF_4_WITH_FAMILY_SUPPORT",
            "prospectively_frozen_before_target_collection": True,
            "target_model_outcomes_available": False,
            "retained_row_stochasticity": stochasticity,
        },
        "retained_task_projection": retained_projection,
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
            "four_fresh_full_1032_row_audits_required": True,
            "source_audits_reusable_for_acceptance": False,
        },
        "replacements": lineage_rows,
    }
    old_config = json.loads((root / V12_CONFIG).read_text(encoding="utf-8"))
    config = build_config(
        old_config,
        files,
        root,
        stochasticity,
        retained_projection,
    )
    outputs: dict[Path, bytes] = {
        V13_SEED: seed_raw,
        V13_LINEAGE: pretty(lineage),
        V13_CONFIG: pretty(config),
    }
    outputs.update({V13_FROZEN / name: raw for name, raw in files.items()})
    return outputs


def write_exclusive(root: Path, outputs: dict[Path, bytes]) -> None:
    collisions = [path for path in outputs if (root / path).exists()]
    if collisions:
        raise FileExistsError(f"refusing to overwrite v1.3 outputs: {collisions}")
    for path, raw in outputs.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw)


def verify_existing(root: Path, outputs: dict[Path, bytes]) -> None:
    for path, raw in outputs.items():
        target = root / path
        if not target.is_file() or target.read_bytes() != raw:
            raise ValueError(f"generated v1.3 artifact drift: {path.as_posix()}")


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
