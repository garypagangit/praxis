#!/usr/bin/env python
"""Reproducibly verify PX-062 Gate 2.2 tokenizer/context conformance.

This is a pre-launch integrity check, not a semantic experiment.  It binds the
replacement task corpus, complete task-local catalogs, exact A-E message
constructors, dependency versions, model revisions, allowed structured
responses, and saved tokenizer artifacts.  Every model/task/arm prompt is
rendered with both the pinned remote tokenizer and an independently reloaded
saved copy; their token IDs must agree exactly.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import platform
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.run_px062_gate2_2_models import (
        arm_a_messages,
        canonical_json_bytes,
        canonical_json_sha256,
        contextual_repair_messages,
        decontextualized_repair_messages,
        direct_messages,
        freeze_tokenizer,
        render_catalog,
        strict_initial_parse,
        structured_responses,
        validate_frozen_inputs,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from run_px062_gate2_2_models import (  # type: ignore[no-redef]
        arm_a_messages,
        canonical_json_bytes,
        canonical_json_sha256,
        contextual_repair_messages,
        decontextualized_repair_messages,
        direct_messages,
        freeze_tokenizer,
        render_catalog,
        strict_initial_parse,
        structured_responses,
        validate_frozen_inputs,
    )


EXPECTED_TASKS_SHA256 = (
    "37c77a9eaa12a4102419591aa554f736494aff85a3e252fd284a20b95094bebc"
)
EXPECTED_MODEL_REVISIONS = {
    "Qwen/Qwen2.5-7B-Instruct": "a09a35458c702b33eeacc393d103063234e8bc28",
    "mistralai/Mistral-7B-Instruct-v0.3": (
        "c170c708c41dac9275d15a8fff4eca08d52bab71"
    ),
}
EXPECTED_DEPENDENCIES = {
    "torch": "2.3.0",
    "transformers": "4.46.3",
    "accelerate": "1.1.1",
    "jinja2": "3.1.4",
    "numpy": "1.26.4",
    "protobuf": "5.28.3",
    "safetensors": "0.4.5",
    "sentencepiece": "0.2.0",
}
EXPECTED_ARMS = (
    "A_open_text",
    "B_structured_names",
    "C_structured_catalog",
    "D_contextual_repair",
    "E_decontextualized_repair",
)
CONTEXT_WINDOW_TOKENS = 32768
STRUCTURED_EOS_TOKENS = 1
COLLECTOR_SOURCE = Path("scripts/run_px062_gate2_2_models.py")
SEMANTIC_CONFIG_PROJECTION_SCHEMA = (
    "px062-gate2.2-semantic-config-projection-v1"
)
SEMANTIC_CONFIG_EXCLUDED_FIELDS = (
    "status",
    "source_integrity",
    "label_audit_protocol.runner_sha256",
    "label_audit_protocol.protocol_sha256",
    "label_audit_protocol.tests_sha256",
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys
    )
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line, object_pairs_hook=_no_duplicate_keys)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row is not an object: {path}:{line_number}")
            rows.append(value)
    return rows


def semantic_config_projection(config: dict[str, Any]) -> dict[str, Any]:
    """Return the acyclic conformance projection of the final config.

    Status and source hashes are finalized after the tokenizer run, and the
    audit code/document/test hashes change when their verifier is hardened.
    Registration validates those excluded values directly against final files.
    Every other config field remains in this projection.
    """

    if not isinstance(config, dict):
        raise ValueError("config projection input is not an object")
    projected = copy.deepcopy(config)
    for field in ("status", "source_integrity"):
        if field not in projected:
            raise ValueError(f"config projection field is missing: {field}")
        del projected[field]
    protocol = projected.get("label_audit_protocol")
    if not isinstance(protocol, dict) or not {
        "runner_sha256",
        "protocol_sha256",
        "tests_sha256",
    } <= set(protocol):
        raise ValueError("config projection audit-file bindings are missing")
    del protocol["runner_sha256"]
    del protocol["protocol_sha256"]
    del protocol["tests_sha256"]
    return projected


def semantic_config_projection_record(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SEMANTIC_CONFIG_PROJECTION_SCHEMA,
        "excluded_fields": list(SEMANTIC_CONFIG_EXCLUDED_FIELDS),
        "sha256": canonical_json_sha256(semantic_config_projection(config)),
    }


def validate_protocol(config: dict[str, Any], tasks_path: Path) -> dict[str, str]:
    observed_hash = sha256_file(tasks_path)
    if observed_hash != EXPECTED_TASKS_SHA256:
        raise ValueError(
            f"replacement task hash drift: {observed_hash} != {EXPECTED_TASKS_SHA256}"
        )
    if config.get("model_revisions") != EXPECTED_MODEL_REVISIONS:
        raise ValueError("model revisions differ from the pinned conformance contract")
    if config.get("models") != list(EXPECTED_MODEL_REVISIONS):
        raise ValueError("model order differs from the pinned conformance contract")
    if config.get("dependency_versions") != EXPECTED_DEPENDENCIES:
        raise ValueError("config dependency versions differ from the pinned contract")
    if config.get("arms") != list(EXPECTED_ARMS):
        raise ValueError("arm order differs from the pinned conformance contract")
    decoding = config.get("decoding", {})
    if (
        decoding.get("open_max_new_tokens") != 32
        or decoding.get("choice_count") != 44
        or decoding.get("structured_response_schema") != '{"choice":"Snnn"}'
    ):
        raise ValueError("decoding contract drift")
    return {"tasks_sha256": observed_hash}


def check_dependencies() -> dict[str, str]:
    observed: dict[str, str] = {}
    for package, expected in EXPECTED_DEPENDENCIES.items():
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as error:
            raise ValueError(f"pinned dependency is missing: {package}") from error
        observed[package] = version
        if version != expected:
            raise ValueError(
                f"dependency version mismatch for {package}: {version} != {expected}"
            )
    return observed


def build_exact_open_response_probe(tokenizer: Any, token_budget: int) -> str:
    """Construct deterministic text that re-encodes to the full token budget."""

    units = ("x ", "invalid ", "response ", "0 ", "z\n")
    for unit in units:
        for count in range(1, token_budget * 4 + 1):
            candidate = (unit * count).rstrip()
            ids = tokenizer.encode(candidate, add_special_tokens=False)
            if len(ids) == token_budget:
                if tokenizer.decode(
                    ids,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                ) != candidate:
                    continue
                return candidate
    raise ValueError(f"unable to construct an exact {token_budget}-token response probe")


def verify_choice_roundtrips(tokenizer: Any, choices: list[str]) -> dict[str, Any]:
    lengths: list[int] = []
    sequences: set[tuple[int, ...]] = set()
    failures: list[str] = []
    for raw in choices:
        token_ids = tuple(tokenizer.encode(raw, add_special_tokens=False))
        decoded = tokenizer.decode(
            token_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        if not token_ids or decoded != raw:
            failures.append(raw)
        lengths.append(len(token_ids))
        sequences.add(token_ids)
    if failures:
        raise ValueError(f"structured choices failed exact round-trip: {failures}")
    if len(sequences) != len(choices):
        raise ValueError("distinct structured choices share a token sequence")
    return {
        "choice_count": len(choices),
        "choice_set_sha256": canonical_json_sha256(choices),
        "choice_token_length_min": min(lengths),
        "choice_token_length_max": max(lengths),
        "choice_roundtrip_failures": 0,
    }


def render_token_ids(tokenizer: Any, messages: list[dict[str, str]]) -> list[int]:
    rendered = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    encoded = tokenizer(rendered, add_special_tokens=True)
    token_ids = encoded["input_ids"]
    if token_ids and isinstance(token_ids[0], list):
        token_ids = token_ids[0]
    if not isinstance(token_ids, list) or not token_ids:
        raise ValueError("rendered chat produced no prompt token IDs")
    return [int(token) for token in token_ids]


def construct_all_messages(
    config: dict[str, Any],
    task: dict[str, Any],
    descriptions: dict[str, str],
    rejected_response: str,
) -> dict[str, list[dict[str, str]]]:
    option_map = task["option_map"]
    names_catalog = render_catalog(
        option_map, descriptions, include_descriptions=False
    )
    full_catalog = render_catalog(option_map, descriptions, include_descriptions=True)
    try:
        a_messages = arm_a_messages(config, task)
        messages = {
            "A_open_text": a_messages,
            "B_structured_names": direct_messages(
                config, task, names_catalog, include_descriptions=False
            ),
            "C_structured_catalog": direct_messages(
                config, task, full_catalog, include_descriptions=True
            ),
            "D_contextual_repair": contextual_repair_messages(
                config, a_messages, rejected_response, full_catalog
            ),
            "E_decontextualized_repair": decontextualized_repair_messages(
                config, rejected_response, full_catalog
            ),
        }
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError(
            f"message template formatting failed for {task.get('task_id')}: {error}"
        ) from error
    if tuple(messages) != EXPECTED_ARMS:
        raise ValueError("message constructor arm order drift")
    d_messages = messages["D_contextual_repair"]
    e_messages = messages["E_decontextualized_repair"]
    expected_roles = ["system", "user", "assistant", "user"]
    if (
        [row.get("role") for row in d_messages] != expected_roles
        or [row.get("role") for row in e_messages] != expected_roles
        or d_messages[0] != e_messages[0]
        or d_messages[2:] != e_messages[2:]
        or d_messages[1] == e_messages[1]
        or d_messages[2].get("content") != rejected_response
    ):
        raise ValueError("D/E clean context-ablation message invariant failed")
    return messages


def _update_maximum(
    maxima: dict[str, int], task_ids: dict[str, list[str]], arm: str, count: int, task_id: str
) -> None:
    previous = maxima.get(arm, -1)
    if count > previous:
        maxima[arm] = count
        task_ids[arm] = [task_id]
    elif count == previous:
        task_ids.setdefault(arm, []).append(task_id)


def check_model(
    *,
    model_id: str,
    revision: str,
    tokenizer: Any,
    verifier: Any,
    tokenizer_record: dict[str, Any],
    config: dict[str, Any],
    tasks: list[dict[str, Any]],
    descriptions: dict[str, str],
) -> dict[str, Any]:
    choices = sorted(structured_responses(tasks[0]["option_map"]))
    choice_result = verify_choice_roundtrips(tokenizer, choices)
    verifier_choice_result = verify_choice_roundtrips(verifier, choices)
    if verifier_choice_result != choice_result:
        raise ValueError(f"saved tokenizer choice behavior drift: {model_id}")
    probe = build_exact_open_response_probe(
        tokenizer, int(config["decoding"]["open_max_new_tokens"])
    )
    probe_ids = tokenizer.encode(probe, add_special_tokens=False)
    if verifier.encode(probe, add_special_tokens=False) != probe_ids:
        raise ValueError(f"saved tokenizer response-probe behavior drift: {model_id}")
    registry_names = set(descriptions)
    if strict_initial_parse(probe, registry_names)["status"] != "invalid":
        raise ValueError("open-response budget probe is not rejected by arm A parser")

    maximum_prompt: dict[str, int] = {}
    maximum_prompt_tasks: dict[str, list[str]] = {}
    maximum_total: dict[str, int] = {}
    maximum_total_tasks: dict[str, list[str]] = {}
    evidence_digest = hashlib.sha256()
    rendered_sets = 0
    structured_response_tokens = choice_result["choice_token_length_max"] + (
        STRUCTURED_EOS_TOKENS
    )
    response_tokens = {
        "A_open_text": len(probe_ids),
        "B_structured_names": structured_response_tokens,
        "C_structured_catalog": structured_response_tokens,
        "D_contextual_repair": structured_response_tokens,
        "E_decontextualized_repair": structured_response_tokens,
    }
    for task in tasks:
        task_id = str(task["task_id"])
        messages_by_arm = construct_all_messages(
            config, task, descriptions, probe
        )
        for arm, messages in messages_by_arm.items():
            try:
                prompt_ids = render_token_ids(tokenizer, messages)
                verifier_ids = render_token_ids(verifier, messages)
            except Exception as error:
                raise ValueError(
                    f"chat-template rendering failed for {model_id}/{task_id}/{arm}: {error}"
                ) from error
            if prompt_ids != verifier_ids:
                raise ValueError(
                    f"saved tokenizer prompt IDs drift for {model_id}/{task_id}/{arm}"
                )
            prompt_count = len(prompt_ids)
            total_count = prompt_count + response_tokens[arm]
            if total_count >= CONTEXT_WINDOW_TOKENS:
                raise ValueError(
                    f"context limit reached for {model_id}/{task_id}/{arm}: {total_count}"
                )
            _update_maximum(
                maximum_prompt, maximum_prompt_tasks, arm, prompt_count, task_id
            )
            _update_maximum(
                maximum_total, maximum_total_tasks, arm, total_count, task_id
            )
            evidence_digest.update(
                canonical_json_bytes(
                    {
                        "arm": arm,
                        "messages_sha256": canonical_json_sha256(messages),
                        "model_id": model_id,
                        "prompt_token_ids_sha256": sha256_bytes(
                            canonical_json_bytes(prompt_ids)
                        ),
                        "task_id": task_id,
                    }
                )
            )
            rendered_sets += 1
    if rendered_sets != len(tasks) * len(EXPECTED_ARMS):
        raise ValueError("not every model/task/arm message set was rendered")
    artifact_aggregate = canonical_json_sha256(tokenizer_record["files"])
    return {
        "model_id": model_id,
        "revision": revision,
        "eos_token_id": tokenizer.eos_token_id,
        **choice_result,
        "open_response_budget_probe": {
            "token_budget": len(probe_ids),
            "text": probe,
            "utf8_sha256": sha256_bytes(probe.encode("utf-8")),
        },
        "maximum_prompt_tokens": maximum_prompt,
        "maximum_prompt_first_task_id": {
            arm: task_ids[0] for arm, task_ids in maximum_prompt_tasks.items()
        },
        "maximum_prompt_tie_count": {
            arm: len(task_ids) for arm, task_ids in maximum_prompt_tasks.items()
        },
        "maximum_prompt_plus_response_tokens": maximum_total,
        "maximum_prompt_plus_response_first_task_id": {
            arm: task_ids[0] for arm, task_ids in maximum_total_tasks.items()
        },
        "maximum_prompt_plus_response_tie_count": {
            arm: len(task_ids) for arm, task_ids in maximum_total_tasks.items()
        },
        "response_token_allowance_by_arm": response_tokens,
        "minimum_context_headroom_tokens": CONTEXT_WINDOW_TOKENS
        - max(maximum_total.values()),
        "rendered_model_task_arm_sets": rendered_sets,
        "rendered_evidence_sha256": evidence_digest.hexdigest(),
        "saved_tokenizer_artifacts": {
            "artifact_key": tokenizer_record["artifact_key"],
            "tokenizer_class": tokenizer_record["tokenizer_class"],
            "verification_tokenizer_class": tokenizer_record[
                "verification_tokenizer_class"
            ],
            "files": tokenizer_record["files"],
            "files_manifest_sha256": artifact_aggregate,
        },
    }


def run_check(
    *,
    config_path: Path,
    tasks_path: Path,
    catalog_path: Path,
    output_path: Path,
    checked_at_utc: str,
    local_files_only: bool,
) -> dict[str, Any]:
    from transformers import AutoTokenizer

    config = read_json(config_path)
    protocol = validate_protocol(config, tasks_path)
    dependencies = check_dependencies()
    tasks = read_jsonl(tasks_path)
    catalog = read_json(catalog_path)
    registry_names, descriptions = validate_frozen_inputs(config, tasks, catalog)
    if len(registry_names) != int(config["expected_registry_names"]):
        raise ValueError("validated registry-name count drift")
    if len(tasks) != int(config["expected_tasks"]):
        raise ValueError("validated task count drift")

    model_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="px062-g22-tokenizer-conformance-") as temp:
        stage = Path(temp)
        for model_id in config["models"]:
            revision = config["model_revisions"][model_id]
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                revision=revision,
                local_files_only=local_files_only,
            )
            verifier, tokenizer_record = freeze_tokenizer(
                tokenizer, AutoTokenizer, stage, model_id, revision
            )
            model_results.append(
                check_model(
                    model_id=model_id,
                    revision=revision,
                    tokenizer=tokenizer,
                    verifier=verifier,
                    tokenizer_record=tokenizer_record,
                    config=config,
                    tasks=tasks,
                    descriptions=descriptions,
                )
            )
    manifest = {
        "schema_version": "px062-gate2.2-tokenizer-conformance-v3",
        "checked_at_utc": checked_at_utc,
        "checker": {
            "path": "scripts/check_px062_gate2_2_tokenizer_conformance.py",
            "sha256": sha256_file(Path(__file__)),
        },
        "message_constructor_source": {
            "path": COLLECTOR_SOURCE.as_posix(),
            "sha256": sha256_file(COLLECTOR_SOURCE),
        },
        "python": platform.python_version(),
        "dependency_versions": dependencies,
        "config_sha256": sha256_file(config_path),
        "semantic_config_projection": semantic_config_projection_record(config),
        **protocol,
        "registry_catalog_sha256": sha256_file(catalog_path),
        "task_count": len(tasks),
        "option_maps_and_catalogs_validated": len(tasks),
        "structured_choices": 44,
        "structured_response_form": '{"choice":"Snnn"}',
        "open_response_max_new_tokens": 32,
        "arms": list(EXPECTED_ARMS),
        "models": model_results,
        "minimum_model_context_window_tokens": CONTEXT_WINDOW_TOKENS,
        "strict_context_comparison": "prompt_plus_response_tokens < 32768",
        "pass": True,
        "interpretation": (
            "All frozen replacement tasks, task-local option maps/catalogs, and "
            "exact A-E messages conform under both pinned tokenizers and saved "
            "artifact reloads. This is implementation integrity evidence, not a "
            "semantic result."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px062_skill_selection_gate2_2_v1_0_20260728.json"),
    )
    parser.add_argument(
        "--tasks",
        type=Path,
        default=Path(
            "reports/coding_agent_skill_provenance/"
            "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl"
        ),
    )
    parser.add_argument(
        "--registry-catalog",
        type=Path,
        default=Path(
            "reports/coding_agent_skill_provenance/"
            "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checked-at-utc", required=True)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    result = run_check(
        config_path=args.config,
        tasks_path=args.tasks,
        catalog_path=args.registry_catalog,
        output_path=args.output,
        checked_at_utc=args.checked_at_utc,
        local_files_only=not args.allow_network,
    )
    print(
        json.dumps(
            {
                "models": [row["model_id"] for row in result["models"]],
                "pass": result["pass"],
                "tasks_sha256": result["tasks_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
