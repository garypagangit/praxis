from __future__ import annotations

import csv

from praxis.praxis04.experiment import run_experiment


def write_day(path, rows):
    fieldnames = ["Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts", "Init_Win_bytes_forward", "Label"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_praxis04_full_tiny_csv_run(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    labels = ["Benign", "Bot", "FTP-BruteForce", "DoS-Hulk"]
    for day_idx, day in enumerate(["01-01-2018", "01-02-2018", "01-03-2018"]):
        rows = []
        for label_idx, label in enumerate(labels):
            for repeat in range(12):
                base = label_idx * 10 + repeat
                rows.append(
                    {
                        "Flow Duration": base + day_idx,
                        "Tot Fwd Pkts": base % 7 + label_idx,
                        "Tot Bwd Pkts": base % 5 + day_idx,
                        "Init_Win_bytes_forward": 1 + repeat,
                        "Label": label,
                    }
                )
        write_day(data_dir / f"{day}.csv", rows)

    config = {
        "name": "tiny-full",
        "model": "Treatment-Stage",
        "seed": 7,
        "seed_torch": False,
        "data_dir": str(data_dir),
        "submodels": ["RF", "MLP", "BiLSTM"],
        "router_input": ["features", "predicted_stage_logits"],
        "rf_n_estimators": 8,
        "mlp_max_iter": 20,
        "bilstm_epochs": 1,
        "router_epochs": 5,
        "stage_max_iter": 50,
    }
    payload = run_experiment(config, tmp_path / "run")
    assert payload["config_name"] == "tiny-full"
    assert "macro_f1" in payload["metrics"]
    assert (tmp_path / "run" / "predictions.npz").exists()
    assert (tmp_path / "run" / "predictions_preview.json").exists()
