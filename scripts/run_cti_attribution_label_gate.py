from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def attack_external_id(obj: dict[str, Any]) -> str:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return str(ref.get("external_id") or "")
    return ""


def active(obj: dict[str, Any]) -> bool:
    return not obj.get("revoked", False) and not obj.get("x_mitre_deprecated", False)


def summarize_attack(path: Path) -> dict[str, Any]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    objects = [obj for obj in bundle["objects"] if active(obj)]
    by_id = {obj["id"]: obj for obj in objects}

    groups = {
        obj["id"]: {
            "name": obj.get("name", ""),
            "external_id": attack_external_id(obj),
        }
        for obj in objects
        if obj.get("type") == "intrusion-set"
    }
    techniques = {
        obj["id"]: {
            "name": obj.get("name", ""),
            "external_id": attack_external_id(obj),
            "is_subtechnique": bool(obj.get("x_mitre_is_subtechnique", False)),
            "tactics": sorted(
                {
                    phase.get("phase_name", "")
                    for phase in obj.get("kill_chain_phases", [])
                    if phase.get("kill_chain_name") == "mitre-attack"
                }
            ),
        }
        for obj in objects
        if obj.get("type") == "attack-pattern"
    }

    group_to_techniques: dict[str, set[str]] = defaultdict(set)
    technique_to_groups: dict[str, set[str]] = defaultdict(set)
    group_tech_edges = []
    for obj in objects:
        if obj.get("type") != "relationship":
            continue
        if obj.get("relationship_type") != "uses":
            continue
        source = obj.get("source_ref")
        target = obj.get("target_ref")
        if source in groups and target in techniques:
            group_to_techniques[source].add(target)
            technique_to_groups[target].add(source)
            group_tech_edges.append((source, target))

    group_support = sorted(
        [len(group_to_techniques[group_id]) for group_id in groups], reverse=True
    )
    technique_support = sorted(
        [len(technique_to_groups[technique_id]) for technique_id in techniques],
        reverse=True,
    )

    top_groups = []
    for group_id, tech_ids in sorted(
        group_to_techniques.items(), key=lambda item: len(item[1]), reverse=True
    )[:10]:
        group = groups[group_id]
        top_groups.append(
            {
                "name": group["name"],
                "external_id": group["external_id"],
                "technique_count": len(tech_ids),
            }
        )

    return {
        "path": str(path),
        "intrusion_sets": len(groups),
        "techniques": len(techniques),
        "relationships_group_uses_technique": len(group_tech_edges),
        "groups_with_1plus_techniques": sum(count >= 1 for count in group_support),
        "groups_with_3plus_techniques": sum(count >= 3 for count in group_support),
        "groups_with_5plus_techniques": sum(count >= 5 for count in group_support),
        "groups_with_10plus_techniques": sum(count >= 10 for count in group_support),
        "techniques_with_1plus_groups": sum(count >= 1 for count in technique_support),
        "techniques_with_3plus_groups": sum(count >= 3 for count in technique_support),
        "top_groups_by_technique_count": top_groups,
        "object_type_counts": dict(Counter(obj.get("type", "unknown") for obj in objects)),
    }


def summarize_annoctr(root: Path) -> dict[str, Any]:
    split_dir = root / "AnnoCTR" / "linking_mitre_only"
    split_summary = {}
    all_rows: list[dict[str, Any]] = []
    for split in ["train", "dev", "test"]:
        rows = read_jsonl(split_dir / f"{split}.jsonl")
        split_summary[split] = {
            "rows": len(rows),
            "documents": len({row.get("document") for row in rows}),
            "unique_label_titles": len({row.get("label_title") for row in rows}),
            "entity_types": dict(Counter(str(row.get("entity_type")) for row in rows)),
        }
        all_rows.extend(rows)

    label_counts = Counter(str(row.get("label_title")) for row in all_rows)
    document_counts = Counter(str(row.get("document")) for row in all_rows)
    entity_type_counts = Counter(str(row.get("entity_type")) for row in all_rows)
    class_counts = Counter(str(row.get("entity_class")) for row in all_rows)

    return {
        "path": str(root),
        "rows": len(all_rows),
        "documents": len(document_counts),
        "unique_label_titles": len(label_counts),
        "unique_label_links": len({row.get("label_link") for row in all_rows}),
        "split_summary": split_summary,
        "entity_type_counts": dict(entity_type_counts),
        "entity_class_counts": dict(class_counts),
        "top_labels": label_counts.most_common(15),
        "top_documents_by_mentions": document_counts.most_common(10),
    }


def summarize_aptnotes(path: Path) -> dict[str, Any]:
    rows = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    years = Counter(str(row.get("Year", "")).strip() for row in rows)
    sources = Counter(str(row.get("Source", "")).strip() for row in rows)
    return {
        "path": str(path),
        "rows": len(rows),
        "years": len([year for year in years if year]),
        "min_year": min((int(year) for year in years if year.isdigit()), default=None),
        "max_year": max((int(year) for year in years if year.isdigit()), default=None),
        "top_sources": sources.most_common(10),
        "has_actor_column": any(
            any(token in key.lower() for token in ["actor", "group", "adversary"])
            for row in rows[:1]
            for key in row.keys()
        ),
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    attack = summary["mitre_attack"]
    annoctr = summary["annoctr"]
    aptnotes = summary["aptnotes"]
    decisions = summary["decisions"]

    lines = [
        "# CTI Attribution Label Sufficiency Gate",
        "",
        "Generated: 2026-05-10",
        "",
        "## Decision",
        "",
        "| Experiment | Gate result | Rationale |",
        "|---|---|---|",
    ]
    for decision in decisions:
        lines.append(
            "| {experiment} | {status} | {rationale} |".format(**decision)
        )

    lines.extend(
        [
            "",
            "## MITRE ATT&CK Enterprise Graph",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Intrusion-set groups | {attack['intrusion_sets']} |",
            f"| Techniques / subtechniques | {attack['techniques']} |",
            f"| Group uses technique edges | {attack['relationships_group_uses_technique']} |",
            f"| Groups with >= 1 technique | {attack['groups_with_1plus_techniques']} |",
            f"| Groups with >= 3 techniques | {attack['groups_with_3plus_techniques']} |",
            f"| Groups with >= 5 techniques | {attack['groups_with_5plus_techniques']} |",
            f"| Groups with >= 10 techniques | {attack['groups_with_10plus_techniques']} |",
            f"| Techniques used by >= 1 group | {attack['techniques_with_1plus_groups']} |",
            f"| Techniques used by >= 3 groups | {attack['techniques_with_3plus_groups']} |",
            "",
            "Top groups by ATT&CK technique support:",
            "",
            "| Group | ATT&CK ID | Technique count |",
            "|---|---:|---:|",
        ]
    )
    for row in attack["top_groups_by_technique_count"]:
        lines.append(
            f"| {row['name']} | {row['external_id']} | {row['technique_count']} |"
        )

    lines.extend(
        [
            "",
            "## AnnoCTR MITRE Linking Labels",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Labeled mention rows | {annoctr['rows']} |",
            f"| Documents | {annoctr['documents']} |",
            f"| Unique label titles | {annoctr['unique_label_titles']} |",
            f"| Unique label links | {annoctr['unique_label_links']} |",
            "",
            "| Split | Rows | Documents | Unique labels | Entity types |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for split, row in annoctr["split_summary"].items():
        lines.append(
            f"| {split} | {row['rows']} | {row['documents']} | "
            f"{row['unique_label_titles']} | {row['entity_types']} |"
        )

    lines.extend(
        [
            "",
            "Top AnnoCTR MITRE labels:",
            "",
            "| Label | Mentions |",
            "|---|---:|",
        ]
    )
    for label, count in annoctr["top_labels"]:
        lines.append(f"| {label} | {count} |")

    lines.extend(
        [
            "",
            "## APTNotes Timeline",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Report rows | {aptnotes['rows']} |",
            f"| Year span | {aptnotes['min_year']} to {aptnotes['max_year']} |",
            f"| Has explicit actor/group column | {aptnotes['has_actor_column']} |",
            "",
            "## Stop Conditions",
            "",
            "- TTP graph embeddings can proceed because ATT&CK has enough group-technique supervision.",
            "- Few-shot group attribution can proceed only as an ATT&CK TTP-set simulation until report-to-group labels are added or derived.",
            "- LLM threat-intelligence fusion remains blocked for publishable early-warning claims because the local sources expose timelines and CTI labels, not success/failure outcome labels.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--attack-json",
        type=Path,
        default=Path(
            "external/datasets/mitre-attack/enterprise-attack/enterprise-attack.json"
        ),
    )
    parser.add_argument(
        "--annoctr-root", type=Path, default=Path("external/datasets/annoctr")
    )
    parser.add_argument(
        "--aptnotes-summary",
        type=Path,
        default=Path("external/datasets/aptnotes/APTnotes_summary.csv"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs/cti-attribution-label-gate-20260510"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/cti_attribution_label_sufficiency/ATTACK_ANNOCTR_LABEL_GATE_20260510.md"
        ),
    )
    args = parser.parse_args()

    attack = summarize_attack(args.attack_json)
    annoctr = summarize_annoctr(args.annoctr_root)
    aptnotes = summarize_aptnotes(args.aptnotes_summary)

    gnn_ready = (
        attack["relationships_group_uses_technique"] >= 500
        and attack["groups_with_5plus_techniques"] >= 50
        and attack["techniques_with_1plus_groups"] >= 200
    )
    few_shot_sim_ready = attack["groups_with_3plus_techniques"] >= 50
    report_labels_ready = aptnotes["has_actor_column"]
    fusion_ground_truth_ready = False

    decisions = [
        {
            "experiment": "GNN Attribution - TTP Graph Embeddings",
            "status": "DATA READY" if gnn_ready else "BLOCKED",
            "rationale": (
                "ATT&CK has enough intrusion-set to technique edges for a graph embedding pilot."
                if gnn_ready
                else "ATT&CK group-technique graph is too sparse for a defensible graph pilot."
            ),
        },
        {
            "experiment": "Few-Shot APT Group Attribution",
            "status": "PARTIAL DATA READY" if few_shot_sim_ready else "BLOCKED",
            "rationale": (
                "ATT&CK supports held-out group few-shot simulation, but APTNotes lacks explicit group labels for document attribution."
                if not report_labels_ready
                else "ATT&CK and APTNotes both expose group labels."
            ),
        },
        {
            "experiment": "LLM Threat Intelligence Fusion",
            "status": "BLOCKED",
            "rationale": (
                "Local NVD/APTNotes/AnnoCTR sources support retrieval and extraction, but not early-warning success/failure outcomes."
                if not fusion_ground_truth_ready
                else "Outcome labels are available."
            ),
        },
    ]

    summary = {
        "mitre_attack": attack,
        "annoctr": annoctr,
        "aptnotes": aptnotes,
        "decisions": decisions,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    render_report(args.report, summary)
    print(json.dumps({"report": str(args.report), "decisions": decisions}, indent=2))


if __name__ == "__main__":
    main()
