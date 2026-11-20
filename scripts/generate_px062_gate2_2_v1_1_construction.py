#!/usr/bin/env python
"""Deterministically derive the PX-062 Gate 2.2 v1.1 construction artifacts.

The v1 inputs and failed label-audit evidence are immutable sources.  This
generator changes exactly the 33 requests rejected by the v1 dual label audit,
retains every other collection-visible prompt, and emits a complete lineage
map.  It never consumes Qwen or Mistral target-model outcomes; none exist.
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
    from scripts.build_px062_gate2_2_v11_benchmark import (
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        build_artifacts,
    )
except ImportError:  # direct execution from scripts/
    from build_px062_gate2_2_v11_benchmark import (  # type: ignore[no-redef]
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        build_artifacts,
    )


ROOT = Path(__file__).resolve().parents[1]
V1_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-0-20260728"
V1_1_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-1-20260728"
V1_SEED = Path("manifests/px062_gate2_2_20260728/task_seed_bank.json")
V1_CONFIG = Path("configs/px062_skill_selection_gate2_2_v1_0_20260728.json")
V1_GATE = Path(
    "reports/coding_agent_skill_provenance/gate2_2_context_structured_20260728"
)
V1_FROZEN = V1_GATE / "frozen_inputs"
V1_INVALIDATION = V1_GATE / "label_audit_invalidation.json"
V1_CONFLICTS = V1_GATE / "label_audit_conflicts.jsonl"
V1_1_SEED = Path(
    "manifests/px062_gate2_2_v1_1_20260728/task_seed_bank.json"
)
V1_1_LINEAGE = Path(
    "manifests/px062_gate2_2_v1_1_20260728/task_lineage.json"
)
V1_1_CONFIG = Path(
    "configs/px062_skill_selection_gate2_2_v1_1_20260728.json"
)
V1_1_GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728"
)
V1_1_FROZEN = V1_1_GATE / "frozen_inputs"
V1_1_AUDIT_ANCHORS = {
    "runner_sha256": Path("scripts/run_px062_gate2_2_v11_blind_audit.py"),
    "protocol_sha256": (
        V1_1_GATE / "LABEL_AUDIT_PROTOCOL_V1_1_20260728.md"
    ),
    "tests_sha256": Path("tests/test_px062_gate2_2_v11_blind_audit.py"),
}

EXPECTED_V1_HASHES = {
    V1_SEED.as_posix(): "661dcc6a64c5df42d6da2f1e3ae21d8c57430c5f6bf2437da59ac42bbcbdee11",
    (V1_FROZEN / "tasks.jsonl").as_posix(): "37c77a9eaa12a4102419591aa554f736494aff85a3e252fd284a20b95094bebc",
    (V1_FROZEN / "answer_key.jsonl").as_posix(): "1be338e7d9f1a56a08552bc6481409c87a3906a4d93d254fce2b5acf6ecd2ab3",
    (V1_FROZEN / "registry_catalog.json").as_posix(): "d775221aaa2d0bb11ee7b25c2236a241970175d97726fc70f55e47ca6589acde",
    (V1_FROZEN / "benchmark_manifest.json").as_posix(): "cabd97f3492119109b8f00834145054686ae1f4cfbafc277a3131da3c8f5ee73",
    V1_INVALIDATION.as_posix(): "3c0a3d83877ea2eb5b8fc829e92cd9661b72ac5cf8c016ae145a5fd3dd3a9e42",
    V1_CONFLICTS.as_posix(): "5b899e78cac1ee60c7fafbe37088c3ce58221c6f55680964235b896b1fc91c0c",
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

    @property
    def seed_location(self) -> str:
        return f"{self.collection}/{self.owner}/{self.field}[{self.index}]"


R = Replacement
REPLACEMENTS = (
    R("skill_scenarios", "figma", "requests", 2, "g22-92d80f9682adce850589", "g22-e2d6be6265ea1bee5c6b", "Take a visual capture of the specified design component and summarize its structure.", "Use the supplied design-node URL to fetch that component's screenshot and summarize its node structure."),
    R("skill_scenarios", "figma", "requests", 7, "g22-a1ecd2709addeb7c3213", "g22-0239bcbdc6f891e91180", "Extract the assets and layout information from this design document for a developer.", "Use the supplied design-node URL to extract the frame's assets and layout data for implementation."),
    R("skill_scenarios", "figma-generate-design", "misleading_requests", 2, "g22-ef9e8167b28abd9bf446", "g22-d7e062dcf8768ec81d39", "Create a refined dashboard design using the provided screenshot and interaction notes.", "Build a complete Figma dashboard screen from the provided application screenshot and interaction notes."),
    R("skill_scenarios", "netlify-deploy", "misleading_requests", 0, "g22-974e0818ae2e079065f3", "g22-5681a15c6071a7e67b50", "Publish the current static site to the connected hosting service and return its preview address.", "Publish the current static site through the Netlify CLI and return its preview address."),
    R("skill_scenarios", "netlify-deploy", "misleading_requests", 1, "g22-56db801b40d158cf6303", "g22-8eba1b7f5796b0fc62de", "Configure redirects, environment values, and the build command for this web release.", "Configure Netlify redirects, environment variables, and the build command for this web release."),
    R("skill_scenarios", "netlify-deploy", "misleading_requests", 2, "g22-72e0fbf98bcc5d15b6c6", "g22-70d74a12d97f57683d44", "Diagnose why the hosted preview fails during dependency installation and correct the project setup.", "Diagnose why this Netlify preview fails during dependency installation and correct the site configuration."),
    R("skill_scenarios", "netlify-deploy", "misleading_requests", 3, "g22-0c85529c4a5eb1156908", "g22-1c7ea44e1b9ab5f60348", "Promote the verified preview to production on the site's configured hosting platform.", "Promote the verified Netlify preview to production and confirm the site's configured custom domain."),
    R("skill_scenarios", "notion-research-documentation", "requests", 7, "g22-1ee32e6c679b5b1ae1a9", "g22-590ba0197678d1f051ef", "Investigate a project question using the workspace and publish the synthesis.", "Research a project question across several Notion workspace pages and publish a cited synthesis."),
    R("skill_scenarios", "notion-spec-to-implementation", "misleading_requests", 0, "g22-b8bad05668bc84c2f744", "g22-07e9e8fb099eabb655eb", "Convert the workspace product specification into milestones, implementation tasks, and dependencies.", "Convert the Notion product specification into milestones, implementation tasks, dependencies, and progress tracking."),
    R("skill_scenarios", "render-deploy", "misleading_requests", 2, "g22-d69057340619ca93a0fb", "g22-9b128295485e9b2cf023", "Diagnose the hosting build failure and adjust the start command to match this repository.", "Diagnose the Render build failure and adjust the start command to match this repository."),
    R("skill_scenarios", "render-deploy", "misleading_requests", 3, "g22-e90abfc40b81e4cbc98b", "g22-f86e4042264890e3a421", "Create a repeatable production release from the service blueprint and verify its health endpoint.", "Create a repeatable production release on Render from the service blueprint and verify its health endpoint."),
    R("skill_scenarios", "security-best-practices", "misleading_requests", 0, "g22-d6eca95c3973d7b1ecd6", "g22-ddab8b05f8e7d7e8bb6e", "Review this Java API for common secure-coding mistakes and propose safer defaults.", "Review this Go API for common secure-coding mistakes and propose safer defaults."),
    R("skill_scenarios", "vercel-deploy", "misleading_requests", 0, "g22-d95b8b2ed79f01b01bea", "g22-9e4951b038814f2c8ae4", "Publish this frontend to the selected edge hosting project and return its preview address.", "Publish this frontend to its linked Vercel project and return the preview address."),
    R("skill_scenarios", "vercel-deploy", "misleading_requests", 1, "g22-a8081b7ee7cea946fbb4", "g22-44b86de6b24a834ece04", "Connect the repository, set build variables, and create a branch preview for review.", "Connect the repository to its Vercel project, set build variables, and create a branch preview for review."),
    R("skill_scenarios", "vercel-deploy", "misleading_requests", 2, "g22-718d8136f16292299b23", "g22-fd858421cfd57ebdfa7f", "Diagnose why the hosted build cannot find the framework's generated output directory.", "Diagnose why the Vercel build cannot find the framework's generated output directory."),
    R("skill_scenarios", "vercel-deploy", "misleading_requests", 3, "g22-4ae1113c9c60e10916b1", "g22-383a481c83606f094b8a", "Promote the approved preview to production and verify the custom domain assignment.", "Promote the approved Vercel preview to production and verify its custom domain assignment."),
    R("skill_scenarios", "winui-app", "misleading_requests", 2, "g22-aaa3be5030fc98d92935", "g22-f862a544f8d143ff127b", "Repair window activation and sizing behavior in the packaged desktop application.", "Repair window activation and sizing behavior in this packaged WinUI 3 desktop application."),
    R("unsupported_domains", "microsoft-word", "requests", 0, "g22-39c1f43112deb4dd0659", "g22-34f70a7c6824f712d531", "Apply consistent heading styles throughout this Word manuscript without changing its wording.", "Apply consistent heading styles throughout this Microsoft Word .docx manuscript without changing its wording."),
    R("unsupported_domains", "microsoft-word", "misleading_scenarios", 3, "g22-e65d634ee2e85317b559", "g22-33dfe355b2fcd2f68dd9", "Turn this finished report into a reusable Word template with locked branding elements.", "Turn this finished Microsoft Word report into a reusable .dotx template with locked branding elements."),
    R("unsupported_domains", "google-docs", "requests", 2, "g22-77f276c0b83101afa140", "g22-463d15b12f029e3fd0a4", "Create a reusable meeting-notes template with owners, decisions, and follow-up sections.", "Create a reusable meeting-notes template in Google Docs with owners, decisions, and follow-up sections."),
    R("unsupported_domains", "microsoft-powerpoint", "requests", 7, "g22-8158873ed86af54499b3", "g22-64d00f31cb169ca33630", "Export a handout PDF with three slides per page and blank note lines for attendees.", "Create a PowerPoint custom slide show with separate executive and engineering sequences."),
    R("unsupported_domains", "jira-project-management", "requests", 2, "g22-87e1330cac35d16c477d", "g22-57204302c27e2fad7773", "Add a workflow transition that requires a resolution before an issue can be closed.", "Add a Jira workflow transition that requires a resolution before an issue can be closed."),
    R("unsupported_domains", "jira-project-management", "requests", 3, "g22-a474e10830c5a23a8d63", "g22-9cbeb07a74ed045ede55", "Bulk move these tickets to the platform project while preserving comments and attachments.", "Bulk move these Jira issues to the platform project while preserving comments and attachments."),
    R("unsupported_domains", "jira-project-management", "requests", 7, "g22-12eeba852225338d6594", "g22-4cf982cbb440e95f02f2", "Create the next sprint and carry over only unfinished work approved by the product owner.", "Create the next Jira sprint and carry over only unfinished work approved by the product owner."),
    R("unsupported_domains", "jira-project-management", "misleading_scenarios", 1, "g22-d783dbba6d1ee1cc1b40", "g22-4ca13b4ea211ecb150cd", "Find every ticket reopened twice that still lacks a root-cause field.", "Run a JQL query to find Jira issues reopened twice that still lack a root-cause field."),
    R("unsupported_domains", "jira-project-management", "misleading_scenarios", 2, "g22-e2ea5d9ad7292bf7a315", "g22-0489d693c893283ff466", "Route newly reported defects to teams based on component and customer severity.", "Configure Jira automation to route newly reported defects to teams by component and customer severity."),
    R("unsupported_domains", "jira-project-management", "misleading_scenarios", 3, "g22-276f1351567d6d152dae", "g22-336c0ba26aef2981bef3", "Create a Kanban board for operational work with expedite and standard swimlanes.", "Create a Jira Kanban board for operational work with expedite and standard swimlanes."),
    R("unsupported_domains", "confluence-wiki", "requests", 1, "g22-6f886d4358da4ad4ea16", "g22-3156d0e18ce6682e8362", "Turn these scattered runbooks into one indexed operations section with consistent labels.", "Turn these scattered Confluence runbooks into one indexed operations section with consistent labels."),
    R("unsupported_domains", "microsoft-teams", "requests", 3, "g22-f870f3ee7f2beb2d1ff2", "g22-c7e83f76ee66ea26804b", "Recover the meeting transcript and attendance report from yesterday's training session.", "Restore a deleted Microsoft Teams channel and reinstate its membership and moderation settings."),
    R("unsupported_domains", "react-development", "misleading_scenarios", 2, "g22-cab429a615753bc512f8", "g22-9a29ddd0532779c1d065", "Test keyboard navigation and asynchronous option loading in this component.", "Write React Testing Library unit tests for keyboard navigation and asynchronous option loading without launching a browser."),
    R("unsupported_domains", "vue-development", "misleading_scenarios", 2, "g22-bce8a566a96550773661", "g22-740cb24062952f98a51d", "Verify this dialog's validation, cancellation, and successful submission behavior.", "Write Vue Test Utils unit tests for this dialog's validation, cancellation, and emitted success event without launching a browser."),
    R("unsupported_domains", "nodejs-backend", "requests", 6, "g22-7a39b294932dde60da3b", "g22-63fd29d198d7d75b7b6b", "Handle multipart uploads while enforcing the stated file count and size limits.", "Handle multipart uploads in this Express service while enforcing the stated file count and size limits."),
    R("unsupported_domains", "go-development", "requests", 6, "g22-3336eb39c609ae8aadd3", "g22-70bc57f95fc8dfc23382", "Create a streaming gRPC method with backpressure and clean client disconnect handling.", "Create a streaming gRPC method in Go with backpressure and clean client disconnect handling."),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def jsonl(raw: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


def verify_v1_sources(root: Path) -> None:
    for relative, expected in EXPECTED_V1_HASHES.items():
        actual = sha256((root / relative).read_bytes())
        if actual != expected:
            raise ValueError(f"v1 source drift: {relative}: {actual} != {expected}")


def replace_seed(seed: dict[str, Any]) -> dict[str, Any]:
    revised = copy.deepcopy(seed)
    by_skill = {row["skill"]: row for row in revised["skill_scenarios"]}
    by_domain = {row["slug"]: row for row in revised["unsupported_domains"]}
    for item in REPLACEMENTS:
        owner = (by_skill if item.collection == "skill_scenarios" else by_domain)[item.owner]
        slot = owner[item.field][item.index]
        if item.field == "misleading_scenarios":
            if slot["request"] != item.old_request:
                raise ValueError(f"v1 seed request drift: {item.seed_location}")
            slot["request"] = item.new_request
        else:
            if slot != item.old_request:
                raise ValueError(f"v1 seed request drift: {item.seed_location}")
            owner[item.field][item.index] = item.new_request
    revised["experiment_stage"] = (
        "PX-062 Gate 2.2 v1.1 context-preserving structured selection"
    )
    revised["authoring_note"] += (
        " Version v1.1 prospectively replaces exactly 33 requests rejected by "
        "the v1 dual label audit; the revision is label-audit-informed but "
        "target-outcome-blind."
    )
    governance = revised["label_governance"]
    governance["audit_resolution"] = (
        V1_1_GATE / "label_audit_resolution.json"
    ).as_posix()
    revised["revision_lineage"] = {
        "revision": "v1.1",
        "source_experiment_id": V1_EXPERIMENT_ID,
        "source_tasks_sha256": EXPECTED_V1_HASHES[
            (V1_FROZEN / "tasks.jsonl").as_posix()
        ],
        "source_invalidation": V1_INVALIDATION.as_posix(),
        "source_invalidation_sha256": EXPECTED_V1_HASHES[V1_INVALIDATION.as_posix()],
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "replaced_prompt_ids": 33,
        "retained_prompt_ids": 999,
    }
    return revised


def build_config(
    old: dict[str, Any], files: dict[str, bytes], root: Path
) -> dict[str, Any]:
    config = copy.deepcopy(old)
    config["experiment_id"] = V1_1_EXPERIMENT_ID
    config["protocol_version"] = "2.2.1"
    config["seed"] = "px062-gate2-2-confirmatory-20260728-v2"
    config["parent_experiment_id"] = V1_EXPERIMENT_ID
    config["revision_lineage"] = {
        "source_experiment_id": V1_EXPERIMENT_ID,
        "source_invalidation": V1_INVALIDATION.as_posix(),
        "source_invalidation_sha256": EXPECTED_V1_HASHES[V1_INVALIDATION.as_posix()],
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "target_model_outcomes_available_at_revision": False,
        "replaced_prompt_ids": 33,
        "retained_prompt_ids": 999,
    }
    config["frozen_inputs"] = {
        name.removesuffix(".jsonl").removesuffix(".json"): (
            V1_1_FROZEN / name
        ).as_posix()
        for name in (
            "tasks.jsonl",
            "answer_key.jsonl",
            "registry_catalog.json",
            "benchmark_manifest.json",
        )
    }
    config["collection_output_dir"] = "outputs/px062_gate2_2_v1_1"
    config["source_integrity"] = {
        "tasks_sha256": sha256(files["tasks.jsonl"]),
        "answer_key_sha256": sha256(files["answer_key.jsonl"]),
        "registry_catalog_sha256": sha256(files["registry_catalog.json"]),
        "benchmark_manifest_sha256": sha256(files["benchmark_manifest.json"]),
    }
    for field, relative in V1_1_AUDIT_ANCHORS.items():
        path = root / relative
        if not path.is_file():
            raise ValueError(f"missing v1.1 audit anchor: {relative.as_posix()}")
        config["label_audit_protocol"][field] = sha256(path.read_bytes())
    return config


def construction(root: Path) -> dict[Path, bytes]:
    verify_v1_sources(root)
    old_seed = json.loads((root / V1_SEED).read_text(encoding="utf-8"))
    revised_seed = replace_seed(old_seed)
    seed_raw = pretty(revised_seed)
    files = build_artifacts(
        root=root,
        seed_bank_path=root / V1_1_SEED,
        registry_path=root / DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=root / DEFAULT_PRIOR_TASKS,
        seed_bank_override=revised_seed,
        seed_bank_raw_override=seed_raw,
    )
    for name in ("tasks.jsonl", "answer_key.jsonl", "registry_catalog.json"):
        source_hash = EXPECTED_V1_HASHES[(V1_FROZEN / name).as_posix()]
        if sha256(files[name]) == source_hash:
            raise ValueError(f"v1.1 requires a new {name} identity")
    old_tasks = {row["task_id"]: row for row in jsonl((root / V1_FROZEN / "tasks.jsonl").read_bytes())}
    old_answers = {row["task_id"]: row for row in jsonl((root / V1_FROZEN / "answer_key.jsonl").read_bytes())}
    new_tasks = {row["task_id"]: row for row in jsonl(files["tasks.jsonl"])}
    new_answers = {row["task_id"]: row for row in jsonl(files["answer_key.jsonl"])}
    old_ids, new_ids = set(old_tasks), set(new_tasks)
    if len(old_ids & new_ids) != 999 or len(old_ids - new_ids) != 33 or len(new_ids - old_ids) != 33:
        raise ValueError("v1.1 lineage cardinality drift")
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
        lineage_rows.append(
            {
                "seed_location": item.seed_location,
                "old_task_id": item.old_task_id,
                "new_task_id": item.new_task_id,
                "task_type": old_answer["task_type"],
                "expected_skill": old_answer["expected_skill"],
                "old_request": item.old_request,
                "new_request": item.new_request,
            }
        )
    manifest = json.loads(files["benchmark_manifest.json"])
    lineage = {
        "schema_version": "px062-gate2.2-v1.1-task-lineage-v1",
        "experiment_id": V1_1_EXPERIMENT_ID,
        "status": "PROSPECTIVE_LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "source": {
            "experiment_id": V1_EXPERIMENT_ID,
            "tasks_sha256": EXPECTED_V1_HASHES[(V1_FROZEN / "tasks.jsonl").as_posix()],
            "invalidation_path": V1_INVALIDATION.as_posix(),
            "invalidation_sha256": EXPECTED_V1_HASHES[V1_INVALIDATION.as_posix()],
            "conflicts_path": V1_CONFLICTS.as_posix(),
            "conflicts_sha256": EXPECTED_V1_HASHES[V1_CONFLICTS.as_posix()],
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
        },
        "replacements": lineage_rows,
    }
    old_config = json.loads((root / V1_CONFIG).read_text(encoding="utf-8"))
    config = build_config(old_config, files, root)
    outputs: dict[Path, bytes] = {
        V1_1_SEED: seed_raw,
        V1_1_LINEAGE: pretty(lineage),
        V1_1_CONFIG: pretty(config),
    }
    outputs.update({V1_1_FROZEN / name: raw for name, raw in files.items()})
    return outputs


def write_exclusive(root: Path, outputs: dict[Path, bytes]) -> None:
    collisions = [path for path in outputs if (root / path).exists()]
    if collisions:
        raise FileExistsError(f"refusing to overwrite v1.1 outputs: {collisions}")
    for path, raw in outputs.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw)


def verify_existing(root: Path, outputs: dict[Path, bytes]) -> None:
    for path, raw in outputs.items():
        target = root / path
        if not target.is_file() or target.read_bytes() != raw:
            raise ValueError(f"generated v1.1 artifact drift: {path.as_posix()}")


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
