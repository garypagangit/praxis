from __future__ import annotations

import csv

from praxis.praxis04.data_loader import load_preprocessed_split
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


def test_uniform_sampler_reaches_late_rows(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rows = []
    for repeat in range(40):
        rows.append(
            {
                "Flow Duration": repeat,
                "Tot Fwd Pkts": repeat % 3,
                "Tot Bwd Pkts": repeat % 5,
                "Init_Win_bytes_forward": 1,
                "Label": "Benign",
            }
        )
    for repeat in range(40):
        rows.append(
            {
                "Flow Duration": 1000 + repeat,
                "Tot Fwd Pkts": repeat % 3,
                "Tot Bwd Pkts": repeat % 5,
                "Init_Win_bytes_forward": 1,
                "Label": "Bot",
            }
        )
    write_day(data_dir / "Friday-02-03-2018_TrafficForML_CICFlowMeter.csv", rows)
    write_day(data_dir / "Friday-16-02-2018_TrafficForML_CICFlowMeter.csv", rows)

    head = load_preprocessed_split(data_dir, sample_rows_per_file=20, chunksize=10, sample_strategy="head")
    uniform = load_preprocessed_split(
        data_dir,
        sample_rows_per_file=20,
        chunksize=10,
        sample_strategy="uniform",
        sample_seed=13,
    )

    assert set(head.train["attack_label"].unique()) == {"Benign"}
    assert "Bot" in set(uniform.train["attack_label"].unique())


def test_support_floor_moves_unseen_test_labels_to_train(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_day(
        data_dir / "Friday-02-03-2018_TrafficForML_CICFlowMeter.csv",
        [
            {
                "Flow Duration": idx,
                "Tot Fwd Pkts": idx % 3,
                "Tot Bwd Pkts": idx % 5,
                "Init_Win_bytes_forward": 1,
                "Label": "Bot",
            }
            for idx in range(12)
        ],
    )
    write_day(
        data_dir / "Friday-16-02-2018_TrafficForML_CICFlowMeter.csv",
        [
            {
                "Flow Duration": idx,
                "Tot Fwd Pkts": idx % 3,
                "Tot Bwd Pkts": idx % 5,
                "Init_Win_bytes_forward": 1,
                "Label": "Benign",
            }
            for idx in range(12)
        ],
    )

    strict = load_preprocessed_split(data_dir)
    support = load_preprocessed_split(data_dir, min_train_rows_per_label=3, min_val_rows_per_label=2, sample_seed=13)

    assert "Bot" not in set(strict.train["attack_label"].unique())
    assert support.train["attack_label"].value_counts().to_dict()["Bot"] == 3
    assert support.val["attack_label"].value_counts().to_dict()["Bot"] == 2
    assert support.summary["support_floor_moves"][0]["attack_label"] == "Bot"
