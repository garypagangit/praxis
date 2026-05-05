from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from praxis.praxis04.experiment import run_experiment


TUNING_SPACE = {
    "rf_n_estimators": "int[24, 160], step=8",
    "rf_max_depth": "categorical[8, 12, 16, 24, null]",
    "mlp_hidden_layers": "categorical[[64], [128], [128, 64], [256, 128]]",
    "mlp_max_iter": "int[30, 150], step=10",
    "bilstm_hidden_dim": "categorical[8, 16, 32, 64]",
    "bilstm_epochs": "int[1, 6]",
    "router_init_metric": "categorical[macro_f1, nll]",
    "router_init_temperature": "log_float[0.02, 0.50]",
    "router_stage_scale": "float[0.5, 4.0]",
    "router_epochs": "categorical[0, 10, 30, 60]",
    "min_train_rows_per_label": "categorical[0, 25, 50, 100]",
    "min_val_rows_per_label": "categorical[0, 10, 25, 50]",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Optuna tuning harness for Praxis 04.")
    parser.add_argument("--base-config", default="configs/praxis04-representative-pilot.json")
    parser.add_argument("--model", default="Treatment-Stage")
    parser.add_argument("--n-trials", type=int, default=12)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--output-root", default="runs/praxis04-optuna")
    parser.add_argument("--study-name", default="praxis04-stage-router")
    parser.add_argument("--storage", default=None, help="Optional Optuna storage URL, e.g. sqlite:///runs/praxis04-optuna/study.db")
    parser.add_argument("--show-space", action="store_true")
    args = parser.parse_args()

    if args.show_space:
        print(json.dumps(TUNING_SPACE, indent=2))
        return

    try:
        import optuna
    except Exception as exc:
        raise SystemExit("Install optuna first: python -m pip install 'optuna>=3.6,<5'") from exc

    base = json.loads(Path(args.base_config).read_text(encoding="utf-8"))
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "tuning_space.json").write_text(json.dumps(TUNING_SPACE, indent=2), encoding="utf-8")

    study = optuna.create_study(
        direction="maximize",
        study_name=args.study_name,
        storage=args.storage,
        load_if_exists=bool(args.storage),
        sampler=optuna.samplers.TPESampler(seed=args.seed),
    )

    def objective(trial: optuna.Trial) -> float:
        config = deepcopy(base)
        config.update(model_config(args.model))
        config["seed"] = int(args.seed)
        config["name"] = f"praxis04-optuna-{trial.number:03d}"
        config["rf_n_estimators"] = trial.suggest_int("rf_n_estimators", 24, 160, step=8)
        config["rf_max_depth"] = trial.suggest_categorical("rf_max_depth", [8, 12, 16, 24, None])
        config["mlp_hidden_layers"] = trial.suggest_categorical(
            "mlp_hidden_layers",
            [[64], [128], [128, 64], [256, 128]],
        )
        config["mlp_max_iter"] = trial.suggest_int("mlp_max_iter", 30, 150, step=10)
        config["bilstm_hidden_dim"] = trial.suggest_categorical("bilstm_hidden_dim", [8, 16, 32, 64])
        config["bilstm_epochs"] = trial.suggest_int("bilstm_epochs", 1, 6)
        config["router_init_metric"] = trial.suggest_categorical("router_init_metric", ["macro_f1", "nll"])
        config["router_init_temperature"] = trial.suggest_float("router_init_temperature", 0.02, 0.50, log=True)
        config["router_stage_scale"] = trial.suggest_float("router_stage_scale", 0.5, 4.0)
        config["router_epochs"] = trial.suggest_categorical("router_epochs", [0, 10, 30, 60])
        config["min_train_rows_per_label"] = trial.suggest_categorical("min_train_rows_per_label", [0, 25, 50, 100])
        config["min_val_rows_per_label"] = trial.suggest_categorical("min_val_rows_per_label", [0, 10, 25, 50])

        run_dir = output_root / f"trial_{trial.number:03d}"
        payload = run_experiment(config, run_dir)
        metrics = payload["metrics"]
        trial.set_user_attr("run_dir", str(run_dir))
        trial.set_user_attr("router_entropy_mean", metrics.get("router_entropy_mean"))
        trial.set_user_attr("expert_metrics", payload.get("expert_metrics", {}))
        return float(metrics["macro_f1"])

    study.optimize(objective, n_trials=args.n_trials)
    trials_df = study.trials_dataframe()
    trials_df.to_csv(output_root / "trials.csv", index=False)
    (output_root / "best_trial.json").write_text(
        json.dumps(
            {
                "best_value": study.best_value,
                "best_params": study.best_params,
                "best_trial": study.best_trial.number,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"best_value": study.best_value, "best_params": study.best_params}, indent=2))


def model_config(model: str) -> dict:
    if model == "Treatment-Stage":
        return {
            "model": "Treatment-Stage",
            "submodels": ["RF", "MLP", "BiLSTM"],
            "router_input": ["features", "predicted_stage_logits"],
        }
    if model == "Ablation-OracleStage":
        return {
            "model": "Ablation-OracleStage",
            "submodels": ["RF", "MLP", "BiLSTM"],
            "router_input": ["features", "ground_truth_stage_onehot"],
        }
    if model == "Baseline-TSE":
        return {
            "model": "Baseline-TSE",
            "submodels": ["RF", "MLP", "BiLSTM"],
            "router_input": ["features"],
        }
    raise ValueError(f"Unsupported tunable model: {model}")


if __name__ == "__main__":
    main()
