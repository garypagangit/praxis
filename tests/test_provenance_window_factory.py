from __future__ import annotations

import json
from pathlib import Path

from praxis.provenance import (
    WindowConfig,
    load_label_spans,
    load_node_labels,
    read_edges_jsonl,
    write_window_artifacts,
)


def write_edges(path: Path, count: int = 6) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx in range(count):
        rows.append(
            {
                "timestamp_nanos": 1000 + idx * 100,
                "sequence": idx,
                "record_index": idx,
                "datum_type": "EVENT_READ" if idx % 2 else "EVENT_WRITE",
                "source_file": "sample.avro.gz",
                "subject_uuid": f"subject-{idx % 2}",
                "object_uuid": f"object-{idx}",
                "properties": {"exec": "cmd.exe" if idx < 3 else "powershell.exe"},
            }
        )
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_window_factory_writes_feature_artifacts(tmp_path: Path) -> None:
    edges_path = tmp_path / "edges.jsonl"
    out_dir = tmp_path / "windows"
    write_edges(edges_path)

    manifest = write_window_artifacts(
        edges_path=edges_path,
        out_dir=out_dir,
        labels_path=None,
        config=WindowConfig(events_per_window=3, top_event_k=4, top_exec_k=4),
    )

    assert manifest["window_count"] == 2
    assert manifest["edge_rows"] == 6
    assert Path(manifest["artifacts"]["windows"]).exists()
    assert Path(manifest["artifacts"]["features"]).exists()

    frame = read_edges_jsonl(edges_path)
    assert len(frame) == 6
    assert set(frame["datum_type"]) == {"EVENT_READ", "EVENT_WRITE"}


def test_window_factory_attaches_node_labels(tmp_path: Path) -> None:
    edges_path = tmp_path / "edges.jsonl"
    labels_path = tmp_path / "node_labels.csv"
    out_dir = tmp_path / "windows"
    write_edges(edges_path)
    labels_path.write_text("subject-0,{'subject': 'None test'},1\n", encoding="utf-8")

    manifest = write_window_artifacts(
        edges_path=edges_path,
        out_dir=out_dir,
        labels_path=None,
        node_label_paths=[labels_path],
        config=WindowConfig(events_per_window=3, top_event_k=4, top_exec_k=4),
    )

    labels = load_node_labels([labels_path])
    assert len(labels) == 1
    assert manifest["node_label_count"] == 1
    assert manifest["node_labeled_window_count"] == 2


def test_window_factory_attaches_interval_labels(tmp_path: Path) -> None:
    edges_path = tmp_path / "edges.jsonl"
    labels_path = tmp_path / "labels.csv"
    out_dir = tmp_path / "windows"
    write_edges(edges_path)
    labels_path.write_text(
        "start_ns,end_ns,label\n1000,1250,recon\n1400,1600,exfil\n",
        encoding="utf-8",
    )

    manifest = write_window_artifacts(
        edges_path=edges_path,
        out_dir=out_dir,
        labels_path=labels_path,
        config=WindowConfig(events_per_window=3, top_event_k=4, top_exec_k=4),
    )

    labels = load_label_spans(labels_path)
    windows = json.loads(Path(manifest["artifacts"]["manifest"]).read_text(encoding="utf-8"))
    window_rows = (out_dir / "windows.csv").read_text(encoding="utf-8")
    assert len(labels) == 2
    assert windows["labeled_window_count"] == 2
    assert "recon" in window_rows
    assert "exfil" in window_rows
