"""Registered retrieval baselines; no labels, scoring, or source-file access."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import ntpath
from typing import Any


METHODS = (
    "name_nearest_time",
    "name_time_abstain",
    "exact_guid_join",
    "compact_guid_join",
)


def _basename(image: str | None) -> str:
    return ntpath.basename(image or "").casefold()


def _time(value: str | None) -> datetime | None:
    """Interpret the normalized UTC field, never a collection timestamp."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _has_guid(value: str | None) -> bool:
    return bool(value and value.replace("-", "").strip("0"))


def _signature(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        event["host"],
        event["guid"],
        (event.get("image") or "").casefold(),
        event.get("utc"),
        event.get("pid"),
    )


def build_index(creations: list[dict[str, Any]]) -> dict[str, Any]:
    """Index complete creation buckets and precompute metadata conflicts.

    Equivalent creation records remain available under their original refs.
    Query work counts bucket records examined; index construction is separate.
    """
    guid: dict[tuple[str, str], dict[str, Any]] = {}
    basename: dict[tuple[str, str], list[dict[str, Any]]] = {}
    times: dict[str, datetime | None] = {}
    seen_refs: set[str] = set()
    for source in creations:
        if source.get("kind") != "creation":
            raise ValueError("build_index accepts only creation records")
        event = dict(source)
        ref = event["ref"]
        if ref in seen_refs:
            raise ValueError(f"Duplicate source reference: {ref}")
        seen_refs.add(ref)
        times[ref] = _time(event.get("utc"))
        if _has_guid(event.get("guid")):
            key = (event["host"], event["guid"])
            group = guid.setdefault(key, {"rows": [], "signatures": set()})
            group["rows"].append(event)
            group["signatures"].add(_signature(event))
        name = _basename(event.get("image"))
        if name:
            basename.setdefault((event["host"], name), []).append(event)
    for group in guid.values():
        group["rows"].sort(key=lambda row: row["ref"])
        group["conflict"] = len(group.pop("signatures")) > 1
    for rows in basename.values():
        rows.sort(key=lambda row: row["ref"])
    return {"guid": guid, "basename": basename, "times": times}


def _evidence_bytes(evidence: list[dict[str, Any]], compact: bool) -> int:
    """Charge complete evidence, including the reversible GUID alias map."""
    if compact:
        guids = sorted({
            row[field]
            for row in evidence
            for field in ("guid", "parent_guid")
            if _has_guid(row.get(field))
        })
        to_alias = {guid: f"P{i + 1}" for i, guid in enumerate(guids)}
        rows = []
        for event in evidence:
            row = dict(event)
            for field in ("guid", "parent_guid"):
                if row.get(field) in to_alias:
                    row[field] = to_alias[row[field]]
            rows.append(row)
        payload = {
            "evidence": rows,
            "guid_aliases": {alias: guid for guid, alias in to_alias.items()},
        }
    else:
        payload = {"evidence": evidence}
    encoded = json.dumps(
        payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return len(encoded)


def retrieve(
    method: str,
    question: dict[str, Any],
    events: dict[str, dict[str, Any]],
    index: dict[str, Any],
    budget: int,
) -> dict[str, Any]:
    """Retrieve recorded evidence with anchor-inclusive record accounting.

    All methods reject conflicting selected identities. Name methods never use
    the target GUID. A cached GUID bucket incurs one lookup and one logical
    examination per returned bucket row per call; the supplied anchor is input.
    """
    if method not in METHODS:
        raise ValueError(f"Unregistered method: {method}")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise ValueError("Evidence budget must be a positive integer")
    anchor = events[question["anchor_ref"]]
    if anchor["ref"] != question["anchor_ref"]:
        raise ValueError("Anchor key and source reference disagree")
    if question["kind"] == "parent_creation":
        target_guid = anchor.get("parent_guid")
        target_image = anchor.get("parent_image")
    elif question["kind"] == "owner_creation":
        target_guid = anchor.get("guid")
        target_image = anchor.get("image")
    else:
        raise ValueError(f"Unregistered question kind: {question['kind']}")

    inspected_records = 0
    lookup_calls = 0
    cached: dict[tuple[str, str], dict[str, Any] | None] = {}

    def get_group(guid: str | None) -> dict[str, Any] | None:
        nonlocal inspected_records, lookup_calls
        if not _has_guid(guid):
            return None
        key = (anchor["host"], guid)
        if key not in cached:
            lookup_calls += 1
            group = index["guid"].get(key)
            if group is not None:
                inspected_records += len(group["rows"])
            cached[key] = group
        return cached[key]

    def finish(status: str, answer_ref: str | None = None) -> dict[str, Any]:
        refs = [anchor["ref"]]
        if answer_ref is not None and answer_ref not in refs:
            refs.append(answer_ref)
        if len(refs) > budget:
            status, answer_ref, refs = "INSUFFICIENT_EVIDENCE", None, refs[:1]
        evidence = [events[ref] for ref in refs]
        if any(row["ref"] != ref for row, ref in zip(evidence, refs)):
            raise ValueError("Evidence key and source reference disagree")
        return {
            "status": status,
            "evidence_refs": refs,
            "answer_ref": answer_ref,
            "inspected_records": inspected_records,
            "lookup_calls": lookup_calls,
            "serialized_bytes": _evidence_bytes(
                evidence, compact=method == "compact_guid_join",
            ),
        }

    if method in ("exact_guid_join", "compact_guid_join"):
        target_group = get_group(target_guid)
        if target_group is None:
            return finish("INSUFFICIENT_EVIDENCE")
        if target_group["conflict"]:
            return finish("AMBIGUOUS")
        # No timestamp filter: this endpoint retrieves the recorded identity.
        return finish("ANSWER", target_group["rows"][0]["ref"])

    name = _basename(target_image)
    anchor_time = _time(anchor.get("utc"))
    if not name or anchor_time is None:
        return finish("INSUFFICIENT_EVIDENCE")
    lookup_calls += 1
    rows = index["basename"].get((anchor["host"], name), [])
    inspected_records += len(rows)
    eligible = [
        row for row in rows
        if _has_guid(row.get("guid"))
        and index["times"][row["ref"]] is not None
        and index["times"][row["ref"]] <= anchor_time
    ]
    if not eligible:
        return finish("INSUFFICIENT_EVIDENCE")
    if method == "name_time_abstain":
        if len({row["guid"] for row in eligible}) > 1:
            return finish("AMBIGUOUS")
        selected = min(eligible, key=lambda row: row["ref"])
    else:
        latest = max(index["times"][row["ref"]] for row in eligible)
        selected = min(
            (row for row in eligible if index["times"][row["ref"]] == latest),
            key=lambda row: row["ref"],
        )
    selected_group = get_group(selected["guid"])
    if selected_group is None:
        return finish("INSUFFICIENT_EVIDENCE")
    if selected_group["conflict"]:
        return finish("AMBIGUOUS")
    return finish("ANSWER", selected["ref"])
