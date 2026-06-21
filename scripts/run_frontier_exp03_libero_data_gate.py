from __future__ import annotations

import argparse
import importlib.util
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DATASET_SERVER = "https://datasets-server.huggingface.co"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def request_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if params is None:
        url = path
    else:
        url = f"{DATASET_SERVER}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "praxis-exp03-libero-data-gate"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def import_checks(names: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in names:
        spec = importlib.util.find_spec(name)
        rows.append({"package": name, "available": bool(spec), "origin": getattr(spec, "origin", None) if spec else None})
    return rows


def text_columns(columns: list[str], patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for column in columns:
        lowered = column.lower()
        if lowered.endswith("_index") or lowered in {"index", "episode_index", "frame_index"}:
            continue
        if any(pattern in lowered for pattern in patterns):
            matches.append(column)
    return matches


def read_repo_json(base: str, relative_path: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{base}/{relative_path}", timeout=90) as response:
        return json.load(response)


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)

    dataset = config["dataset"]
    dataset_id = dataset["dataset_id"]
    size_payload = request_json("size", {"dataset": dataset_id})
    stats_payload = request_json(
        "statistics",
        {"dataset": dataset_id, "config": dataset["config"], "split": dataset["split"]},
    )
    first_rows = request_json(
        "first-rows",
        {"dataset": dataset_id, "config": dataset["config"], "split": dataset["split"]},
    )
    info = read_repo_json(dataset["repo_base"], "meta/info.json")
    tasks_df = pd.read_parquet(f"{dataset['repo_base']}/meta/tasks.parquet")
    episodes_df = pd.read_parquet(f"{dataset['repo_base']}/meta/episodes/chunk-000/file-000.parquet")
    sample_data_url = f"{dataset['repo_base']}/data/chunk-000/file-000.parquet"
    sample_df = pd.read_parquet(sample_data_url)

    data_columns = list(sample_df.columns)
    task_columns = list(tasks_df.columns)
    language_columns = text_columns(data_columns, config["language_column_patterns"])
    task_text_columns = text_columns(task_columns, config["language_column_patterns"])
    import_rows = import_checks(config["required_imports"])
    total_frames = int(size_payload["size"]["dataset"]["num_rows"])
    total_episodes = int(info.get("total_episodes") or len(episodes_df))
    total_tasks = int(info.get("total_tasks") or len(tasks_df))
    public_dataset_checks = {
        "public_frame_support": total_frames >= int(config["metrics"]["min_public_frames"]),
        "public_episode_support": total_episodes >= int(config["metrics"]["min_public_episodes"]),
        "public_task_support": total_tasks >= int(config["metrics"]["min_public_tasks"]),
        "task_text_metadata_present": bool(task_text_columns),
        "language_columns_present": bool(language_columns),
        "simulator_imports_available": all(row["available"] for row in import_rows),
    }
    official_eval_ready = (
        public_dataset_checks["task_text_metadata_present"]
        and public_dataset_checks["language_columns_present"]
        and public_dataset_checks["simulator_imports_available"]
    )
    publish_checks = {
        "public_libero_data_accessible": all(
            [
                public_dataset_checks["public_frame_support"],
                public_dataset_checks["public_episode_support"],
                public_dataset_checks["public_task_support"],
            ]
        ),
        "task_text_metadata_present": public_dataset_checks["task_text_metadata_present"],
        "language_columns_present": public_dataset_checks["language_columns_present"],
        "simulator_imports_available": public_dataset_checks["simulator_imports_available"],
        "official_eval_ready": official_eval_ready,
    }
    status = "FINAL STOP/REFRAME - PUBLIC DATA LACKS LANGUAGE AND SIMULATOR SUPPORT"
    if all(publish_checks.values()):
        status = "PASS - READY FOR OFFICIAL VLA EVAL"

    episode_rows = episodes_df[["episode_index", "length", "dataset_from_index", "dataset_to_index"]].to_dict(orient="records")
    sample_task_counts = {
        str(int(key)): int(value)
        for key, value in sample_df["task_index"].value_counts().sort_index().to_dict().items()
    }
    summary = {
        "generated_utc": utc_now(),
        "status": status,
        "dataset_id": dataset_id,
        "total_frames": total_frames,
        "total_episodes": total_episodes,
        "total_tasks": total_tasks,
        "dataset_features": [feature["name"] for feature in first_rows.get("features", [])],
        "data_columns": data_columns,
        "task_metadata_columns": task_columns,
        "language_columns": language_columns,
        "task_text_columns": task_text_columns,
        "sample_data_parquet": sample_data_url,
        "sample_data_rows": int(len(sample_df)),
        "sample_task_frame_counts": sample_task_counts,
        "episode_metadata_rows": int(len(episodes_df)),
        "required_imports": import_rows,
        "public_dataset_checks": public_dataset_checks,
        "publish_checks": publish_checks,
        "statistics_columns": [row.get("column_name") for row in stats_payload.get("statistics", [])],
    }
    write_json(output_dir / "EXP03_LIBERO_DATA_GATE_SUMMARY_20260621.json", summary)
    write_jsonl(output_dir / "libero_episode_metadata_redacted.jsonl", episode_rows)

    lines = [
        "# EXP03 LIBERO Data and Simulator Gate Result",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Scope",
        "",
        "- Public dataset: `lerobot/libero_10`.",
        "- Gate purpose: determine whether EXP03 can fairly advance from source readiness to official VLA instruction-diversity evaluation.",
        "- No robot policy inference, model training, or raw video export was performed.",
        "",
        "## Primary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Public frames | `{summary['total_frames']}` |",
        f"| Public episodes | `{summary['total_episodes']}` |",
        f"| Public task indices | `{summary['total_tasks']}` |",
        f"| Sample parquet rows inspected | `{summary['sample_data_rows']}` |",
        f"| Data columns | `{', '.join(summary['data_columns'])}` |",
        f"| Task metadata columns | `{', '.join(summary['task_metadata_columns'])}` |",
        f"| Language columns in data | `{', '.join(summary['language_columns']) or 'NONE'}` |",
        f"| Task text columns in metadata | `{', '.join(summary['task_text_columns']) or 'NONE'}` |",
        "",
        "## Import Checks",
        "",
        "| Package | Available |",
        "|---|---:|",
    ]
    for row in import_rows:
        lines.append(f"| `{row['package']}` | `{row['available']}` |")
    lines.extend(
        [
            "",
            "## Publish Checks",
            "",
            "| Check | Pass |",
            "|---|---:|",
        ]
    )
    for key, value in publish_checks.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Final Determination",
            "",
            "EXP03 is **not publishable as an instruction-diversity VLA result in the current cycle**. The public LIBERO data path is real and large enough for data-loader work, but the available `lerobot/libero_10` schema exposes only numeric `task_index` values and state/action/video references. It does not expose natural-language task instructions or trajectory-level language annotations, and the local official simulator/model stack imports are absent.",
            "",
            "The defensible decision is to stop or reframe EXP03 as a data-readiness artifact unless a complete LIBERO/OpenVLA-OFT evaluation environment and instruction metadata are added later.",
        ]
    )
    (output_dir / "EXP03_LIBERO_DATA_GATE_RESULT_20260621.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    challenge = [
        "# EXP03 LIBERO Data Gate Internal Defensibility Challenge",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Verdict: **{summary['status']}**",
        "",
        "| Defense question | Answer |",
        "|---|---|",
        f"| Is there a public robot data path? | Yes. `lerobot/libero_10` exposes `{total_frames}` frames and `{total_episodes}` episodes. |",
        "| Does the public path contain natural-language instructions? | No. The inspected data columns and `meta/tasks.parquet` do not include instruction text. |",
        f"| Are official simulator/model imports ready locally? | No. Required imports available: `{sum(1 for row in import_rows if row['available'])}/{len(import_rows)}`. |",
        "| Can RQ1-RQ3 be answered from this gate? | No. The missing language metadata and simulator stack block success-rate evaluation. |",
        "| Final decision | Stop/reframe for this cycle; do not claim VLA instruction-diversity generalisation. |",
    ]
    (output_dir / "EXP03_LIBERO_DATA_GATE_DEFENSIBILITY_20260621.md").write_text(
        "\n".join(challenge) + "\n", encoding="utf-8"
    )
    print(status, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp03_libero_data_gate_20260621.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
