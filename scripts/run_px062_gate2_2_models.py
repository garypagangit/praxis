#!/usr/bin/env python
"""Collect PX-062 Gate 2.2 structured skill-selection traces.

The collector is deliberately answer-key blind.  It reads only the frozen
task prompts and clean registry catalog.  Correctness is computed later by an
independent adjudicator from a separately sealed answer key.

One JSONL row is written for each (model, task) pair.  Each row contains the
single open-text answer (arm A), two direct structured selections (B/C), and
two repair branches (D/E).  D and E reuse the exact A response bytes.  They
only call the model when A is rejected by the deterministic existence/parser
gate; otherwise both controllers pass A through unchanged.
"""

from __future__ import annotations

import argparse
import base64
import gc
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def strict_initial_parse(text: str, registry_names: set[str]) -> dict[str, Any]:
    """Apply the frozen exact-output parser to arm A.

    Whitespace around the complete response is ignored.  Markdown fences,
    prose, aliases, case drift, punctuation, and nonexistent names are all
    rejected.  This preserves the Gate 2.1 failure mode instead of silently
    repairing it in the parser.
    """

    candidate = text.strip()
    if candidate == "NONE":
        return {
            "status": "explicit_none",
            "candidate": None,
            "selection": None,
        }
    if candidate in registry_names:
        return {
            "status": "valid_skill",
            "candidate": candidate,
            "selection": candidate,
        }
    return {
        "status": "invalid",
        "candidate": candidate or None,
        "selection": None,
    }


def validate_option_map(
    option_map: list[dict[str, Any]], registry_names: set[str]
) -> None:
    if len(option_map) != len(registry_names) + 1:
        raise ValueError("option map must contain every registry skill plus NONE")
    expected_ids = {f"S{index:03d}" for index in range(1, len(option_map) + 1)}
    observed_ids = {row.get("id") for row in option_map}
    if observed_ids != expected_ids:
        raise ValueError("option map IDs are not the complete local-ID set")
    skills = [row.get("skill") for row in option_map]
    if skills.count(None) != 1 or {item for item in skills if item is not None} != registry_names:
        raise ValueError("option map does not contain the frozen registry exactly once")


def option_lookup(option_map: list[dict[str, Any]]) -> dict[str, str | None]:
    return {str(row["id"]): row.get("skill") for row in option_map}


def structured_responses(option_map: list[dict[str, Any]]) -> dict[str, str]:
    """Map each exact allowed response to its local option ID."""

    return {
        json.dumps({"choice": row["id"]}, separators=(",", ":")): str(row["id"])
        for row in option_map
    }


def render_catalog(
    option_map: list[dict[str, Any]],
    descriptions: dict[str, str],
    *,
    include_descriptions: bool,
) -> str:
    lines = []
    for row in option_map:
        option_id = row["id"]
        skill = row.get("skill")
        if skill is None:
            label = "NONE — no suitable registered skill"
        elif include_descriptions:
            label = f"{skill} — {descriptions[skill]}"
        else:
            label = skill
        lines.append(f"{option_id}: {label}")
    return "\n".join(lines)


def arm_a_messages(config: dict[str, Any], task: dict[str, Any]) -> list[dict[str, str]]:
    templates = config["message_templates"]
    return [
        {"role": "system", "content": templates["open_system"]},
        {
            "role": "user",
            "content": templates["open_user"].format(task=task["prompt"]),
        },
    ]


def direct_messages(
    config: dict[str, Any],
    task: dict[str, Any],
    catalog: str,
    *,
    include_descriptions: bool,
) -> list[dict[str, str]]:
    templates = config["message_templates"]
    key = "direct_catalog_user" if include_descriptions else "direct_names_user"
    return [
        {"role": "system", "content": templates["structured_system"]},
        {
            "role": "user",
            "content": templates[key].format(task=task["prompt"], catalog=catalog),
        },
    ]


def contextual_repair_messages(
    config: dict[str, Any],
    initial_messages: list[dict[str, str]],
    initial_response: str,
    catalog: str,
) -> list[dict[str, str]]:
    templates = config["message_templates"]
    return [
        *initial_messages,
        {"role": "assistant", "content": initial_response},
        {
            "role": "user",
            "content": templates["contextual_repair_user"].format(catalog=catalog),
        },
    ]


def decontextualized_repair_messages(
    config: dict[str, Any], initial_response: str, catalog: str
) -> list[dict[str, str]]:
    templates = config["message_templates"]
    return [
        {"role": "system", "content": templates["open_system"]},
        # Keep the role count/order identical to D while withholding only the
        # task text.  The rejected completion remains in the assistant role
        # and the repair instruction is byte-identical across D and E.
        {
            "role": "user",
            "content": templates["decontextualized_task_placeholder"],
        },
        {"role": "assistant", "content": initial_response},
        {
            "role": "user",
            "content": templates["contextual_repair_user"].format(catalog=catalog),
        },
    ]


def validate_sources(
    config: dict[str, Any],
    tasks_path: Path,
    catalog_path: Path,
    manifest_path: Path,
) -> None:
    observed = {
        "tasks_sha256": sha256_file(tasks_path),
        "registry_catalog_sha256": sha256_file(catalog_path),
        "benchmark_manifest_sha256": sha256_file(manifest_path),
    }
    expected = config["source_integrity"]
    for key, value in observed.items():
        if value != expected[key]:
            raise ValueError(f"source integrity failure for {key}: {value} != {expected[key]}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("benchmark_status") != "AUDITED_CONFIRMATORY_INPUTS_READY_TO_FREEZE":
        raise ValueError("benchmark manifest is not independently audited and release-ready")
    registered = manifest.get("artifacts", {})
    manifest_hashes = {
        "tasks_sha256": registered.get("tasks.jsonl", {}).get("sha256"),
        "answer_key_sha256": registered.get("answer_key.jsonl", {}).get("sha256"),
        "registry_catalog_sha256": registered.get("registry_catalog.json", {}).get("sha256"),
    }
    for key, value in manifest_hashes.items():
        if value != expected[key]:
            raise ValueError(f"benchmark manifest binding failure for {key}")


def validate_frozen_inputs(
    config: dict[str, Any],
    tasks: list[dict[str, Any]],
    catalog_payload: dict[str, Any],
) -> tuple[list[str], dict[str, str]]:
    if len(tasks) != int(config["expected_tasks"]):
        raise ValueError(f"expected {config['expected_tasks']} tasks, found {len(tasks)}")
    if len({row.get("task_id") for row in tasks}) != len(tasks):
        raise ValueError("duplicate task ID")
    if any("expected_skill" in row or "label" in row for row in tasks):
        raise ValueError("collector task file contains answer-key fields")
    entries = catalog_payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("registry catalog entries are missing")
    names = [row.get("name") for row in entries]
    if len(names) != int(config["expected_registry_names"]):
        raise ValueError("registry name count mismatch")
    if len(set(names)) != len(names) or any(not isinstance(name, str) for name in names):
        raise ValueError("registry names are missing or duplicated")
    descriptions: dict[str, str] = {}
    for row in entries:
        name = row.get("name")
        description = row.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"registry description is missing for {name}")
        descriptions[str(name)] = description
    registry_names = set(str(name) for name in names)
    for task in tasks:
        if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
            raise ValueError(f"task prompt is missing: {task.get('task_id')}")
        option_map = task.get("option_map")
        if not isinstance(option_map, list):
            raise ValueError(f"task option map is missing: {task.get('task_id')}")
        validate_option_map(option_map, registry_names)
    return [str(name) for name in names], descriptions


def runtime_environment(torch: Any) -> dict[str, Any]:
    build = str(torch.__version__)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": build.split("+", 1)[0],
        "torch_build": build,
        "transformers": __import__("transformers").__version__,
        "accelerate": importlib.metadata.version("accelerate"),
        "jinja2": importlib.metadata.version("jinja2"),
        "numpy": importlib.metadata.version("numpy"),
        "protobuf": importlib.metadata.version("protobuf"),
        "safetensors": importlib.metadata.version("safetensors"),
        "sentencepiece": importlib.metadata.version("sentencepiece"),
        "cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "gpu_names": [
            torch.cuda.get_device_name(index)
            for index in range(torch.cuda.device_count())
        ],
    }


def validate_environment(config: dict[str, Any], environment: dict[str, Any]) -> None:
    for package, expected in config["dependency_versions"].items():
        if environment.get(package) != expected:
            raise ValueError(
                f"dependency version mismatch for {package}: "
                f"{environment.get(package)} != {expected}"
            )
    if config.get("require_cuda", True) and not environment.get("cuda_available"):
        raise ValueError("CUDA is required by the frozen protocol")


def render_chat(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def generate_open(
    tokenizer: Any,
    verification_tokenizer: Any,
    model: Any,
    messages: list[dict[str, str]],
    max_new_tokens: int,
) -> dict[str, Any]:
    import torch

    rendered = render_chat(tokenizer, messages)
    inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output[0, inputs["input_ids"].shape[1] :]
    token_ids = [int(item) for item in generated.tolist()]
    return decoded_completion_record(tokenizer, verification_tokenizer, token_ids)


def decoded_completion_record(
    tokenizer: Any, verification_tokenizer: Any, token_ids: list[int]
) -> dict[str, Any]:
    """Preserve and independently reconstruct the exact untrimmed completion.

    Token IDs include every generated ID, including EOS.  Both the live
    tokenizer and a separately reloaded frozen tokenizer must decode the same
    UTF-8 bytes.  This makes empty/arbitrary-ID trace mutation detectable by
    the independent adjudicator.
    """

    if not token_ids:
        raise ValueError("generation returned no completion token IDs")
    if any(
        not isinstance(token, int) or isinstance(token, bool) or token < 0
        for token in token_ids
    ):
        raise ValueError("generation returned invalid completion token IDs")
    decode_kwargs = {
        "skip_special_tokens": True,
        "clean_up_tokenization_spaces": False,
    }
    raw = tokenizer.decode(token_ids, **decode_kwargs)
    reconstructed = verification_tokenizer.decode(token_ids, **decode_kwargs)
    raw_bytes = raw.encode("utf-8")
    if reconstructed.encode("utf-8") != raw_bytes:
        raise ValueError("frozen tokenizer independently decoded different bytes")
    return {
        "raw_response": raw,
        "raw_response_utf8_base64": base64.b64encode(raw_bytes).decode("ascii"),
        "raw_response_bytes": len(raw_bytes),
        "raw_response_sha256": sha256_bytes(raw_bytes),
        "generated_token_ids": token_ids,
        "tokenizer_reconstruction_verified": True,
    }


def _allowed_next_tokens(
    generated: tuple[int, ...], sequences: list[tuple[int, ...]], eos_token_id: int
) -> list[int]:
    matching = [sequence for sequence in sequences if sequence[: len(generated)] == generated]
    if not matching:
        return [eos_token_id]
    allowed = {
        sequence[len(generated)]
        for sequence in matching
        if len(sequence) > len(generated)
    }
    if any(len(sequence) == len(generated) for sequence in matching):
        allowed.add(eos_token_id)
    return sorted(allowed)


def generate_constrained(
    tokenizer: Any,
    verification_tokenizer: Any,
    model: Any,
    messages: list[dict[str, str]],
    allowed_raw: Iterable[str],
) -> dict[str, Any]:
    """Greedily decode within a prefix trie of exact JSON responses."""

    import torch

    allowed = sorted(set(allowed_raw))
    if not allowed:
        raise ValueError("constrained choice set is empty")
    if tokenizer.eos_token_id is None:
        raise ValueError("tokenizer has no EOS token")
    sequences: list[tuple[int, ...]] = []
    for raw in allowed:
        token_ids = tuple(tokenizer.encode(raw, add_special_tokens=False))
        if not token_ids or tokenizer.decode(
            token_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        ) != raw:
            raise ValueError(f"choice does not round-trip through tokenizer: {raw}")
        sequences.append(token_ids)
    if len(set(sequences)) != len(sequences):
        raise ValueError("distinct structured choices share a token sequence")

    rendered = render_chat(tokenizer, messages)
    inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
    prompt_length = int(inputs["input_ids"].shape[1])
    eos = int(tokenizer.eos_token_id)

    def prefix_allowed_tokens_fn(_batch_id: int, input_ids: Any) -> list[int]:
        generated = tuple(int(item) for item in input_ids[prompt_length:].tolist())
        return _allowed_next_tokens(generated, sequences, eos)

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max(len(sequence) for sequence in sequences) + 1,
            do_sample=False,
            pad_token_id=eos,
            eos_token_id=eos,
            prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
        )
    generated = output[0, prompt_length:]
    token_ids = [int(item) for item in generated.tolist()]
    completion = decoded_completion_record(
        tokenizer, verification_tokenizer, token_ids
    )
    raw = completion["raw_response"]
    return {
        **completion,
        "decoder_escape": raw not in allowed,
        "choice_set_sha256": canonical_json_sha256(allowed),
    }


def structured_arm(
    *,
    tokenizer: Any,
    verification_tokenizer: Any,
    model: Any,
    messages: list[dict[str, str]],
    option_map: list[dict[str, Any]],
    triggered: bool = True,
    pass_through_selection: str | None = None,
    source_initial_sha256: str | None = None,
) -> dict[str, Any]:
    mapping = option_lookup(option_map)
    choices = structured_responses(option_map)
    if not triggered:
        return {
            "triggered": False,
            "generated": False,
            "messages": None,
            "messages_sha256": None,
            "raw_response": None,
            "raw_response_utf8_base64": None,
            "raw_response_bytes": None,
            "raw_response_sha256": None,
            "generated_token_ids": [],
            "tokenizer_reconstruction_verified": None,
            "decoder_escape": False,
            "choice_set_sha256": canonical_json_sha256(sorted(choices)),
            "choice_id": None,
            "selection": pass_through_selection,
            "canonical_decision": json.dumps(
                {"skill": pass_through_selection}, separators=(",", ":")
            ),
            "source_initial_sha256": source_initial_sha256,
        }
    generated = generate_constrained(
        tokenizer, verification_tokenizer, model, messages, choices
    )
    raw = generated["raw_response"]
    choice_id = choices.get(raw)
    selection = mapping.get(choice_id) if choice_id is not None else None
    return {
        "triggered": True,
        "generated": True,
        "messages": messages,
        "messages_sha256": canonical_json_sha256(messages),
        **generated,
        "choice_id": choice_id,
        "selection": selection,
        "canonical_decision": json.dumps({"skill": selection}, separators=(",", ":")),
        "source_initial_sha256": source_initial_sha256,
    }


def tokenizer_key(model_id: str, revision: str) -> str:
    return "tokenizer-" + sha256_bytes(f"{model_id}@{revision}".encode("utf-8"))[:16]


def _deterministic_tar_gz(files: dict[str, bytes], output: Path) -> None:
    with output.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for name, payload in sorted(files.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    info.mode = 0o644
                    with tempfile.SpooledTemporaryFile() as handle:
                        handle.write(payload)
                        handle.seek(0)
                        tar.addfile(info, handle)


def freeze_tokenizer(
    tokenizer: Any,
    auto_tokenizer: Any,
    stage: Path,
    model_id: str,
    revision: str,
) -> tuple[Any, dict[str, Any]]:
    """Save, hash, and independently reload a tokenizer before generation."""

    key = tokenizer_key(model_id, revision)
    destination = stage / key
    if destination.exists():
        raise FileExistsError(f"tokenizer stage already exists: {destination}")
    destination.mkdir(parents=True)
    tokenizer.save_pretrained(destination)
    files: dict[str, Any] = {}
    for path in sorted(item for item in destination.rglob("*") if item.is_file()):
        relative = path.relative_to(destination).as_posix()
        files[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    if not files:
        raise ValueError(f"tokenizer emitted no frozen artifacts: {model_id}")
    verifier = auto_tokenizer.from_pretrained(destination, local_files_only=True)
    return verifier, {
        "artifact_key": key,
        "model_id": model_id,
        "revision": revision,
        "tokenizer_class": type(tokenizer).__name__,
        "verification_tokenizer_class": type(verifier).__name__,
        "eos_token_id": tokenizer.eos_token_id,
        "files": files,
    }


def build_tokenizer_archive(
    stage: Path, records: dict[str, dict[str, Any]], output: Path
) -> dict[str, Any]:
    manifest = {
        "schema_version": "px062-gate2.2-tokenizer-artifacts-v1",
        "decode_contract": {
            "skip_special_tokens": True,
            "clean_up_tokenization_spaces": False,
            "completion_token_ids_include_special_tokens": True,
            "empty_generated_token_ids_allowed": False,
        },
        "models": records,
    }
    manifest_raw = canonical_json_bytes(manifest)
    files = {"tokenizer_manifest.json": manifest_raw}
    for model_record in records.values():
        key = model_record["artifact_key"]
        for relative in model_record["files"]:
            path = stage / key / relative
            files[f"tokenizers/{key}/{relative}"] = path.read_bytes()
    _deterministic_tar_gz(files, output)
    return {
        "path": output.name,
        "sha256": sha256_file(output),
        "bytes": output.stat().st_size,
        "manifest_sha256": sha256_bytes(manifest_raw),
        "manifest": manifest,
    }


def collect(config_path: Path) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    config = json.loads(config_path.read_text(encoding="utf-8"))
    tasks_path = Path(config["frozen_inputs"]["tasks"])
    catalog_path = Path(config["frozen_inputs"]["registry_catalog"])
    manifest_path = Path(config["frozen_inputs"]["benchmark_manifest"])
    validate_sources(config, tasks_path, catalog_path, manifest_path)
    tasks = read_jsonl(tasks_path)
    catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    registry_names, descriptions = validate_frozen_inputs(config, tasks, catalog_payload)
    registry_set = set(registry_names)

    environment = runtime_environment(torch)
    validate_environment(config, environment)
    output_dir = Path(config["collection_output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "model_traces.jsonl"
    summary_path = output_dir / "collection_summary.json"
    if output_path.exists() or summary_path.exists():
        raise FileExistsError("Gate 2.2 collection outputs already exist")

    trace_count = 0
    generation_calls = 0
    constrained_escapes = 0
    tokenizer_records: dict[str, dict[str, Any]] = {}
    tokenizer_stage = output_dir / ".tokenizer-stage"
    tokenizer_stage.mkdir()
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        for model_id in config["models"]:
            revision = config["model_revisions"][model_id]
            tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
            verification_tokenizer, tokenizer_record = freeze_tokenizer(
                tokenizer,
                AutoTokenizer,
                tokenizer_stage,
                model_id,
                revision,
            )
            tokenizer_records[model_id] = tokenizer_record
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                revision=revision,
                torch_dtype=torch.bfloat16,
                device_map="auto",
            )
            model.eval()
            for task in tasks:
                option_map = task["option_map"]
                names_catalog = render_catalog(
                    option_map, descriptions, include_descriptions=False
                )
                full_catalog = render_catalog(
                    option_map, descriptions, include_descriptions=True
                )
                a_messages = arm_a_messages(config, task)
                initial_completion = generate_open(
                    tokenizer,
                    verification_tokenizer,
                    model,
                    a_messages,
                    int(config["decoding"]["open_max_new_tokens"]),
                )
                generation_calls += 1
                initial_raw = initial_completion["raw_response"]
                initial_sha = initial_completion["raw_response_sha256"]
                initial_parse = strict_initial_parse(initial_raw, registry_set)
                arm_a = {
                    "generated": True,
                    "messages": a_messages,
                    "messages_sha256": canonical_json_sha256(a_messages),
                    **initial_completion,
                    "parser_status": initial_parse["status"],
                    "parsed_candidate": initial_parse["candidate"],
                    "selection": initial_parse["selection"],
                }

                b_messages = direct_messages(
                    config, task, names_catalog, include_descriptions=False
                )
                arm_b = structured_arm(
                    tokenizer=tokenizer,
                    verification_tokenizer=verification_tokenizer,
                    model=model,
                    messages=b_messages,
                    option_map=option_map,
                )
                generation_calls += 1

                c_messages = direct_messages(
                    config, task, full_catalog, include_descriptions=True
                )
                arm_c = structured_arm(
                    tokenizer=tokenizer,
                    verification_tokenizer=verification_tokenizer,
                    model=model,
                    messages=c_messages,
                    option_map=option_map,
                )
                generation_calls += 1

                repair_triggered = initial_parse["status"] == "invalid"
                if repair_triggered:
                    d_messages = contextual_repair_messages(
                        config, a_messages, initial_raw, full_catalog
                    )
                    e_messages = decontextualized_repair_messages(
                        config, initial_raw, full_catalog
                    )
                else:
                    d_messages = []
                    e_messages = []
                arm_d = structured_arm(
                    tokenizer=tokenizer,
                    verification_tokenizer=verification_tokenizer,
                    model=model,
                    messages=d_messages,
                    option_map=option_map,
                    triggered=repair_triggered,
                    pass_through_selection=initial_parse["selection"],
                    source_initial_sha256=initial_sha,
                )
                arm_e = structured_arm(
                    tokenizer=tokenizer,
                    verification_tokenizer=verification_tokenizer,
                    model=model,
                    messages=e_messages,
                    option_map=option_map,
                    triggered=repair_triggered,
                    pass_through_selection=initial_parse["selection"],
                    source_initial_sha256=initial_sha,
                )
                if repair_triggered:
                    generation_calls += 2

                constrained_escapes += sum(
                    bool(arm["decoder_escape"]) for arm in (arm_b, arm_c, arm_d, arm_e)
                )
                row = {
                    "experiment_id": config["experiment_id"],
                    "protocol_version": config["protocol_version"],
                    "task_id": task["task_id"],
                    "model_id": model_id,
                    "model_revision": revision,
                    "tokenizer_artifact_key": tokenizer_record["artifact_key"],
                    "option_map": option_map,
                    "option_map_sha256": canonical_json_sha256(option_map),
                    "arms": {
                        "A_open_text": arm_a,
                        "B_structured_names": arm_b,
                        "C_structured_catalog": arm_c,
                        "D_contextual_repair": arm_d,
                        "E_decontextualized_repair": arm_e,
                    },
                }
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                trace_count += 1
            del model
            del tokenizer
            del verification_tokenizer
            gc.collect()
            torch.cuda.empty_cache()

    tokenizer_archive_path = output_dir / "tokenizer_artifacts.tar.gz"
    tokenizer_artifacts = build_tokenizer_archive(
        tokenizer_stage, tokenizer_records, tokenizer_archive_path
    )
    shutil.rmtree(tokenizer_stage)

    if trace_count != int(config["expected_traces"]):
        raise ValueError(
            f"expected {config['expected_traces']} traces, collected {trace_count}"
        )
    summary = {
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "models": config["models"],
        "model_revisions": config["model_revisions"],
        "expected_tasks": config["expected_tasks"],
        "expected_traces": config["expected_traces"],
        "observed_traces": trace_count,
        "generation_calls": generation_calls,
        "constrained_decoder_escapes": constrained_escapes,
        "tokenizer_artifacts": tokenizer_artifacts,
        "source_integrity": {
            "config_sha256": sha256_file(config_path),
            "tasks_sha256": sha256_file(tasks_path),
            "registry_catalog_sha256": sha256_file(catalog_path),
            "benchmark_manifest_sha256": sha256_file(manifest_path),
        },
        "environment": environment,
        "collector_pid": os.getpid(),
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(collect(args.config), indent=2))


if __name__ == "__main__":
    main()
