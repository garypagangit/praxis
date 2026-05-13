from __future__ import annotations

import copy
import importlib.util
import json
import math
import os
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - optional dependency
    matplotlib = None
    plt = None
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
    silhouette_samples,
)
from sklearn.neighbors import NearestNeighbors
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, Dataset
from torch_geometric.loader import DataLoader as GraphDataLoader

try:
    import seaborn as sns
except Exception:  # pragma: no cover - optional dependency
    sns = None

try:
    from tabulate import tabulate
except Exception:  # pragma: no cover - optional dependency
    tabulate = None

try:
    from imblearn.over_sampling import SMOTE
except Exception:  # pragma: no cover - optional dependency
    SMOTE = None

try:
    import umap
except Exception:  # pragma: no cover - optional dependency
    umap = None

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


CONFIG = {
    # Assumption: point this at the raw DAPT2020 CSV folder used by the local pipeline.
    "dapt_data_path": "./data/raw/dapt2020",
    # Assumption: if present, this consolidated CSV is preferred for faster DAPT loading.
    "dapt_consolidated_csv": "./data/processed/dapt2020/combined_flows.csv",
    # Assumption: this repo stores raw Unraveled flows under imports/, not ./data/unraveled/.
    "unraveled_data_path": "./imports/unraveled/data/network-flows",
    # Assumption: external state_dict checkpoints live here; current run folders mostly store metrics only.
    "dapt_checkpoint_dir": "./checkpoints/dapt2020",
    # Assumption: external state_dict checkpoints live here; current run folders mostly store metrics only.
    "unraveled_checkpoint_dir": "./checkpoints/unraveled",
    "results_dir": "./results",
    # Assumption: these run dirs are used as artifact-first fallbacks before touching checkpoints.
    "dapt_run_dir": "./runs/dapt2020-local-fast",
    "unraveled_run_dir": "./runs/praxisv03-unraveled-stage-balanced-local",
    "random_seed": 42,
    "device": "cuda" if torch.cuda.is_available() else "cpu",
}


RUN_SECTION = {
    "S0_display_known_results": False,
    "S1_class_distribution": False,
    "S2_confusion_matrices": False,
    "S3_class_weighted_rerun": False,
    "S4_smote_rerun": False,
    "S5_homophily_analysis": False,
    "S6_mlp_feature_importance": False,
    "S7_embedding_umap": False,
    "S8_mamba_prediction_audit": False,
    "S9_focal_loss_mamba": False,
    "S10_xgboost_rf_baseline": False,
    "S11_mlp_gcndgi_ensemble": False,
}


STAGE_NAMES = [
    "Benign",
    "Reconnaissance",
    "Establish Foothold",
    "Lateral Movement",
    "Data Exfiltration",
]

STAGE_SHORT_LABELS = {
    "Benign": "Benign F1",
    "Reconnaissance": "Recon F1",
    "Establish Foothold": "Foothold F1",
    "Lateral Movement": "LM F1",
    "Data Exfiltration": "DE F1",
}

MODEL_DISPLAY_NAMES = {
    ("DAPT2020", "RGCN"): "R-GCN",
    ("Unraveled", "RGCN"): "R-GCN",
    ("Unraveled", "MLP"): "MLP (best baseline)",
}

DATASET_SPECS = {
    "DAPT2020": {
        "summary_metric_key": "roc_auc",
        "summary_metric_label": "Macro ROC-AUC",
        "models": ["GCN-DGI", "GATv2", "RGCN", "GIN", "ST-GCN"],
        "graph_models": ["GCN-DGI", "GATv2", "RGCN", "GIN", "ST-GCN"],
    },
    "Unraveled": {
        "summary_metric_key": "pr_auc",
        "summary_metric_label": "PR-AUC",
        "models": ["MLP", "Mamba", "GCN-DGI", "RGCN", "GATv2", "GIN", "ST-GCN"],
        "graph_models": ["GCN-DGI", "RGCN", "GATv2", "GIN", "ST-GCN"],
    },
}

KNOWN_RESULTS = {
    "DAPT2020": {
        "GCN-DGI": {
            "benign_f1": 0.8865,
            "recon_f1": 0.7843,
            "foothold_f1": 0.7798,
            "lm_f1": 0.3260,
            "de_f1": 0.0174,
            "macro_f1": 0.5588,
            "summary_metric": 0.9418,
        },
        "GATv2": {
            "benign_f1": 0.9181,
            "recon_f1": 0.7259,
            "foothold_f1": 0.5126,
            "lm_f1": 0.0107,
            "de_f1": 0.0000,
            "macro_f1": 0.4335,
            "summary_metric": 0.9286,
        },
        "RGCN": {
            "benign_f1": 0.9026,
            "recon_f1": 0.5973,
            "foothold_f1": 0.0138,
            "lm_f1": 0.0000,
            "de_f1": 0.0000,
            "macro_f1": 0.3027,
            "summary_metric": 0.9540,
        },
        "GIN": {
            "benign_f1": 0.8200,
            "recon_f1": 0.4326,
            "foothold_f1": 0.0000,
            "lm_f1": 0.1797,
            "de_f1": 0.0044,
            "macro_f1": 0.2873,
            "summary_metric": 0.8939,
        },
        "ST-GCN": {
            "benign_f1": 0.8497,
            "recon_f1": 0.4611,
            "foothold_f1": 0.0000,
            "lm_f1": 0.0000,
            "de_f1": 0.0000,
            "macro_f1": 0.2622,
            "summary_metric": 0.7412,
        },
    },
    "Unraveled": {
        "MLP": {
            "benign_f1": 0.9880,
            "recon_f1": 0.9293,
            "foothold_f1": 0.9905,
            "lm_f1": 0.9023,
            "de_f1": 0.9575,
            "macro_f1": 0.9535,
            "summary_metric": 0.9697,
        },
        "Mamba": {
            "benign_f1": 0.9956,
            "recon_f1": 0.9374,
            "foothold_f1": 0.8905,
            "lm_f1": 0.9768,
            "de_f1": 0.0014,
            "macro_f1": 0.7603,
            "summary_metric": 0.9686,
        },
        "GCN-DGI": {
            "benign_f1": 0.9919,
            "recon_f1": 0.9554,
            "foothold_f1": 0.8479,
            "lm_f1": 0.9330,
            "de_f1": 0.0000,
            "macro_f1": 0.7456,
            "summary_metric": 0.7813,
        },
        "RGCN": {
            "benign_f1": 0.9780,
            "recon_f1": 0.8208,
            "foothold_f1": 0.7511,
            "lm_f1": 0.6959,
            "de_f1": 0.0000,
            "macro_f1": 0.6492,
            "summary_metric": 0.7813,
        },
        "GATv2": {
            "benign_f1": 0.9801,
            "recon_f1": 0.8242,
            "foothold_f1": 0.6344,
            "lm_f1": 0.0000,
            "de_f1": 0.0000,
            "macro_f1": 0.4877,
            "summary_metric": 0.6622,
        },
        "GIN": {
            "benign_f1": 0.9443,
            "recon_f1": 0.0004,
            "foothold_f1": 0.6377,
            "lm_f1": 0.3361,
            "de_f1": 0.0014,
            "macro_f1": 0.3840,
            "summary_metric": 0.6520,
        },
        "ST-GCN": {
            "benign_f1": 0.8890,
            "recon_f1": 0.1285,
            "foothold_f1": 0.3484,
            "lm_f1": 0.0000,
            "de_f1": 0.0000,
            "macro_f1": 0.2732,
            "summary_metric": 0.3271,
        },
    },
}

SECTION_ORDER = list(RUN_SECTION)
SECTION_STATUS: dict[str, str] = {}
_CACHE: dict[str, Any] = {}

PLOT_BG = "#0b1220"
AX_BG = "#111827"
GRID_COLOR = "#334155"
TEXT_COLOR = "#e5e7eb"
ACCENT = "#38bdf8"


class SectionSkip(RuntimeError):
    pass


@dataclass
class DatasetContext:
    name: str
    settings: dict[str, Any]
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    feature_cols: list[str]
    run_dir: Path
    run_summary: dict[str, Any] | None
    helper_module: Any


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def section_dir(section_name: str) -> Path:
    return ensure_dir(resolve_path(CONFIG["results_dir"]) / section_name)


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_dataframe(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_device() -> torch.device:
    requested = str(CONFIG["device"]).strip().lower()
    if requested == "cuda" and not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device(requested)


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def configure_plot_theme() -> None:
    if plt is None:
        return
    plt.style.use("dark_background")
    plt.rcParams.update(
        {
            "figure.facecolor": PLOT_BG,
            "axes.facecolor": AX_BG,
            "savefig.facecolor": PLOT_BG,
            "axes.edgecolor": GRID_COLOR,
            "axes.labelcolor": TEXT_COLOR,
            "axes.titlecolor": TEXT_COLOR,
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
            "grid.color": GRID_COLOR,
            "text.color": TEXT_COLOR,
        }
    )
    if sns is not None:
        sns.set_theme(style="darkgrid")


def display_name(dataset_name: str, model_name: str) -> str:
    return MODEL_DISPLAY_NAMES.get((dataset_name, model_name), model_name)


def file_slug(model_name: str) -> str:
    return (
        model_name.lower()
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace(" ", "_")
    )


def internal_model_name(model_name: str) -> str:
    return {"R-GCN": "RGCN"}.get(model_name, model_name)


def wide_metric_row(dataset_name: str, model_name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    summary_key = DATASET_SPECS[dataset_name]["summary_metric_key"]
    summary_label = DATASET_SPECS[dataset_name]["summary_metric_label"]
    row = {
        "dataset": dataset_name,
        "model": display_name(dataset_name, model_name),
        "Benign F1": metrics["per_class_f1"]["Benign"],
        "Recon F1": metrics["per_class_f1"]["Reconnaissance"],
        "Foothold F1": metrics["per_class_f1"]["Establish Foothold"],
        "LM F1": metrics["per_class_f1"]["Lateral Movement"],
        "DE F1": metrics["per_class_f1"]["Data Exfiltration"],
        "Macro F1": metrics["macro_f1"],
        summary_label: metrics.get(summary_key),
    }
    return row


def known_results_frame(dataset_name: str) -> pd.DataFrame:
    summary_label = DATASET_SPECS[dataset_name]["summary_metric_label"]
    rows = []
    for model_name in DATASET_SPECS[dataset_name]["models"]:
        metrics = KNOWN_RESULTS[dataset_name][model_name]
        rows.append(
            {
                "dataset": dataset_name,
                "model": display_name(dataset_name, model_name),
                "Benign F1": metrics["benign_f1"],
                "Recon F1": metrics["recon_f1"],
                "Foothold F1": metrics["foothold_f1"],
                "LM F1": metrics["lm_f1"],
                "DE F1": metrics["de_f1"],
                "Macro F1": metrics["macro_f1"],
                summary_label: metrics["summary_metric"],
            }
        )
    return pd.DataFrame(rows)


def format_results_table(dataset_name: str) -> str:
    frame = known_results_frame(dataset_name)
    metric_columns = [
        "Benign F1",
        "Recon F1",
        "Foothold F1",
        "LM F1",
        "DE F1",
        "Macro F1",
        DATASET_SPECS[dataset_name]["summary_metric_label"],
    ]
    best_values = {column: frame[column].max() for column in metric_columns}

    formatted = frame.copy()
    for column in metric_columns:
        pretty_values = []
        for value in formatted[column]:
            cell = f"{value:.4f}"
            if column.endswith("F1") and abs(value) < 1e-12:
                cell = f"{cell} ⚠"
            if math.isclose(value, best_values[column], rel_tol=1e-12, abs_tol=1e-12):
                cell = f"**{cell}**"
            pretty_values.append(cell)
        formatted[column] = pretty_values

    formatted = formatted.drop(columns=["dataset"])
    if tabulate is not None:
        return tabulate(formatted, headers="keys", tablefmt="github", showindex=False)

    lines = []
    headers = list(formatted.columns)
    widths = {column: max(len(column), *(len(str(value)) for value in formatted[column])) for column in headers}
    header_line = "| " + " | ".join(f"{column:<{widths[column]}}" for column in headers) + " |"
    divider = "| " + " | ".join("-" * widths[column] for column in headers) + " |"
    lines.extend([header_line, divider])
    for _, row in formatted.iterrows():
        lines.append("| " + " | ".join(f"{str(row[column]):<{widths[column]}}" for column in headers) + " |")
    return "\n".join(lines)


def start_section(section_name: str, required_files: list[str]) -> tuple[Path, bool]:
    out_dir = section_dir(section_name)
    if required_files and all((out_dir / name).exists() for name in required_files):
        print(f"[{section_name}] Outputs already exist. Skipping.")
        SECTION_STATUS[section_name] = "skipped_existing"
        return out_dir, True
    print(f"\n{'=' * 100}")
    print(section_name)
    print(f"{'=' * 100}")
    return out_dir, False


def finish_section(section_name: str, out_dir: Path, summary: dict[str, Any]) -> None:
    save_json(
        out_dir / "completion.json",
        {
            "section": section_name,
            "completed_at_utc": timestamp_utc(),
            "summary": summary,
        },
    )
    print(f"[{section_name}] Summary: {summary}")
    SECTION_STATUS[section_name] = "ran"


def skip_section(section_name: str, reason: str) -> None:
    print(f"[{section_name}] Skipped: {reason}")
    SECTION_STATUS[section_name] = f"skipped_runtime: {reason}"


def offdiag_argmax(confusion: np.ndarray) -> tuple[int, int, int]:
    best_i = 0
    best_j = 0
    best_value = -1
    for i in range(confusion.shape[0]):
        for j in range(confusion.shape[1]):
            if i == j:
                continue
            value = int(confusion[i, j])
            if value > best_value:
                best_i, best_j, best_value = i, j, value
    return best_i, best_j, best_value


def compute_per_class_f1(confusion: np.ndarray) -> dict[str, float]:
    values: dict[str, float] = {}
    for index, stage_name in enumerate(STAGE_NAMES):
        tp = float(confusion[index, index])
        precision_den = float(confusion[:, index].sum())
        recall_den = float(confusion[index, :].sum())
        precision = tp / precision_den if precision_den else 0.0
        recall = tp / recall_den if recall_den else 0.0
        if precision + recall == 0.0:
            values[stage_name] = 0.0
        else:
            values[stage_name] = float((2.0 * precision * recall) / (precision + recall))
    return values


def compute_multiclass_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
) -> dict[str, Any]:
    labels = list(range(len(STAGE_NAMES)))
    confusion = confusion_matrix(y_true, y_pred, labels=labels)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        zero_division=0,
    )
    metrics = {
        "accuracy": float((y_true == y_pred).mean()),
        "macro_precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": confusion.tolist(),
        "per_class_f1": {STAGE_NAMES[idx]: float(f1[idx]) for idx in range(len(STAGE_NAMES))},
        "per_class_precision": {STAGE_NAMES[idx]: float(precision[idx]) for idx in range(len(STAGE_NAMES))},
        "per_class_recall": {STAGE_NAMES[idx]: float(recall[idx]) for idx in range(len(STAGE_NAMES))},
        "per_class_support": {STAGE_NAMES[idx]: int(support[idx]) for idx in range(len(STAGE_NAMES))},
        "roc_auc": None,
        "pr_auc": None,
    }

    try:
        metrics["roc_auc"] = float(
            roc_auc_score(
                y_true,
                y_prob,
                multi_class="ovr",
                average="macro",
                labels=labels,
            )
        )
    except Exception:
        metrics["roc_auc"] = None

    try:
        y_true_bin = np.eye(len(STAGE_NAMES), dtype=np.float32)[y_true]
        metrics["pr_auc"] = float(average_precision_score(y_true_bin, y_prob, average="macro"))
    except Exception:
        metrics["pr_auc"] = None

    return metrics


def extract_state_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if "state_dict" in payload and isinstance(payload["state_dict"], dict):
            payload = payload["state_dict"]
        elif "model_state_dict" in payload and isinstance(payload["model_state_dict"], dict):
            payload = payload["model_state_dict"]
    if not isinstance(payload, dict):
        raise ValueError("Checkpoint payload does not look like a state_dict.")
    cleaned = {}
    for key, value in payload.items():
        new_key = key[7:] if key.startswith("module.") else key
        cleaned[new_key] = value
    return cleaned


def load_torch_checkpoint(path: Path) -> dict[str, Any]:
    payload = torch.load(path, map_location="cpu")
    return extract_state_dict(payload)


def candidate_checkpoint_paths(root: Path, model_name: str) -> list[Path]:
    aliases = {
        "GCN-DGI": ["gcn_dgi", "gcndgi"],
        "GATv2": ["gatv2"],
        "RGCN": ["rgcn", "r_gcn"],
        "R-GCN": ["rgcn", "r_gcn"],
        "GIN": ["gin"],
        "ST-GCN": ["st_gcn", "stgcn"],
        "MLP": ["mlp"],
        "Mamba": ["mamba"],
    }.get(model_name, [file_slug(model_name)])
    paths: list[Path] = []
    for alias in aliases:
        paths.extend(
            [
                root / f"{alias}.pt",
                root / f"{alias}.pth",
                root / f"{alias}.bin",
                root / alias / "state_dict.pt",
                root / alias / "model.pt",
                root / alias / "checkpoint.pt",
            ]
        )
    return [path for path in paths if path.exists()]


def find_checkpoint(dataset_name: str, model_name: str) -> Path | None:
    key = f"{dataset_name}:{model_name}:checkpoint"
    if key in _CACHE:
        return _CACHE[key]
    base_dir_key = "dapt_checkpoint_dir" if dataset_name == "DAPT2020" else "unraveled_checkpoint_dir"
    base_dir = resolve_path(CONFIG[base_dir_key])
    candidates = candidate_checkpoint_paths(base_dir, model_name)
    checkpoint = sorted(candidates, key=lambda path: str(path))[-1] if candidates else None
    _CACHE[key] = checkpoint
    return checkpoint


def dapt_paths() -> tuple[Path, Path]:
    raw_path = resolve_path(CONFIG["dapt_data_path"])
    consolidated_path = resolve_path(CONFIG["dapt_consolidated_csv"])
    if raw_path.is_file():
        return raw_path.parent, raw_path
    return raw_path, consolidated_path


def load_dapt_module() -> Any:
    if "dapt_module" in _CACHE:
        return _CACHE["dapt_module"]

    raw_dir, consolidated_csv = dapt_paths()
    os.environ["DAPT2020_LOCAL_DATA_DIR"] = str(raw_dir)
    os.environ["DAPT2020_LOCAL_CONSOLIDATED_CSV"] = str(consolidated_csv)
    os.environ["DAPT2020_LOCAL_OUTPUT_DIR"] = str(ensure_dir(section_dir("_scratch") / "dapt_runtime"))
    script_path = REPO_ROOT / "imports" / "gml_to_detect_apt_final" / "gml_to_detect_apt_final.py"
    spec = importlib.util.spec_from_file_location("incremental_dapt_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load DAPT helper module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _CACHE["dapt_module"] = module
    return module


def load_run_settings(run_dir: Path, defaults: dict[str, Any]) -> dict[str, Any]:
    metadata = load_json(run_dir / "metadata.json")
    settings = dict(defaults)
    if metadata is not None and isinstance(metadata.get("settings"), dict):
        settings.update(metadata["settings"])
    return settings


def add_diag_row_ids(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["diag_row_id"] = np.arange(len(output), dtype=np.int64)
    return output


def get_unraveled_context() -> DatasetContext:
    if "unraveled_context" in _CACHE:
        return _CACHE["unraveled_context"]

    run_dir = resolve_path(CONFIG["unraveled_run_dir"])
    settings = load_run_settings(run_dir, v03.DEFAULTS)
    settings["data_dir"] = str(resolve_path(CONFIG["unraveled_data_path"]))
    settings["force_rebuild_cache"] = False
    helper_module = v02.load_gml_module(REPO_ROOT)
    scratch_dir = ensure_dir(section_dir("_scratch") / "unraveled_context")

    df, _, _, _ = v02.load_or_build_cache(settings, REPO_ROOT)
    train_df, val_df, test_df, feature_cols, _ = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=helper_module,
        run_dir=scratch_dir,
    )

    context = DatasetContext(
        name="Unraveled",
        settings=settings,
        train_df=add_diag_row_ids(train_df),
        val_df=add_diag_row_ids(val_df),
        test_df=add_diag_row_ids(test_df),
        feature_cols=feature_cols,
        run_dir=run_dir,
        run_summary=load_json(run_dir / "results-summary.json"),
        helper_module=helper_module,
    )
    _CACHE["unraveled_context"] = context
    return context


def get_dapt_context() -> DatasetContext:
    if "dapt_context" in _CACHE:
        return _CACHE["dapt_context"]

    helper_module = load_dapt_module()
    run_dir = resolve_path(CONFIG["dapt_run_dir"])
    runtime_defaults = helper_module.resolve_runtime_profile(max_files=None, sample_rate=1.0)
    settings = load_run_settings(run_dir, runtime_defaults)
    settings.setdefault("strategy", "hybrid")
    settings.setdefault("merge_networks", False)

    df, feature_cols, _ = helper_module.load_dapt2020_with_network_context(
        max_files=settings.get("max_files"),
        sample_rate=settings.get("sample_rate") or 1.0,
        merge_networks=bool(settings.get("merge_networks", False)),
    )
    train_df, val_df, test_df, _, feature_cols = helper_module.stratified_temporal_split_by_network(
        df=df,
        feature_cols=feature_cols,
        val_size=0.15,
        test_size=0.15,
        n_blocks=int(runtime_defaults.get("n_blocks", 10)),
        strategy=str(settings.get("strategy", "hybrid")),
    )

    context = DatasetContext(
        name="DAPT2020",
        settings=settings,
        train_df=add_diag_row_ids(train_df),
        val_df=add_diag_row_ids(val_df),
        test_df=add_diag_row_ids(test_df),
        feature_cols=feature_cols,
        run_dir=run_dir,
        run_summary=load_json(run_dir / "results-summary.json"),
        helper_module=helper_module,
    )
    _CACHE["dapt_context"] = context
    return context


def dapt_console_confusions() -> dict[str, np.ndarray]:
    cache_key = "dapt_console_confusions"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    log_path = resolve_path(CONFIG["dapt_run_dir"]) / "console.log"
    if not log_path.exists():
        _CACHE[cache_key] = {}
        return {}

    text = log_path.read_text(encoding="utf-16")
    model_aliases = {
        "GATv2": "GATv2",
        "RGCN": "RGCN",
        "ST-GCN": "ST-GCN",
        "GIN": "GIN",
        "GCN-DGI": "GCN-DGI",
    }
    matrices: dict[str, np.ndarray] = {}
    for model_name, alias in model_aliases.items():
        marker = f"EVALUATION RESULTS: {alias}"
        matches = list(re.finditer(marker, text))
        if not matches:
            continue
        block_start = matches[-1].start()
        block_end = text.find("OVERALL MODEL SCORE:", block_start)
        block = text[block_start:block_end if block_end != -1 else None]
        rows: list[list[int]] = []
        for stage_name in STAGE_NAMES:
            stage_match = None
            for line in block.splitlines():
                if line.strip().startswith(stage_name):
                    numbers = [int(item) for item in re.findall(r"\d+", line)]
                    if len(numbers) == len(STAGE_NAMES):
                        stage_match = numbers
                        break
            if stage_match is None:
                rows = []
                break
            rows.append(stage_match)
        if rows:
            matrices[model_name] = np.asarray(rows, dtype=np.int64)

    _CACHE[cache_key] = matrices
    return matrices


def unraveled_summary_results() -> dict[str, Any]:
    context = get_unraveled_context()
    if context.run_summary is None:
        return {}
    return context.run_summary.get("results", {})


def latest_dapt_optuna_params(model_name: str) -> dict[str, Any] | None:
    cache_key = f"dapt_params:{model_name}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    run_dir = resolve_path(CONFIG["dapt_run_dir"]) / "optuna_results"
    all_models = sorted(run_dir.glob("ALL_MODELS_best_params_*.json"))
    if all_models:
        payload = load_json(all_models[-1])
        if payload is not None:
            params = payload.get(model_name)
            _CACHE[cache_key] = params
            return params
    _CACHE[cache_key] = None
    return None


def format_results_table(dataset_name: str) -> str:
    frame = known_results_frame(dataset_name)
    metric_columns = [
        "Benign F1",
        "Recon F1",
        "Foothold F1",
        "LM F1",
        "DE F1",
        "Macro F1",
        DATASET_SPECS[dataset_name]["summary_metric_label"],
    ]
    best_values = {column: frame[column].max() for column in metric_columns}

    formatted = frame.copy()
    for column in metric_columns:
        pretty_values = []
        for value in formatted[column]:
            cell = f"{value:.4f}"
            if column.endswith("F1") and abs(value) < 1e-12:
                cell = f"{cell} ⚠"
            if math.isclose(value, best_values[column], rel_tol=1e-12, abs_tol=1e-12):
                cell = f"**{cell}**"
            pretty_values.append(cell)
        formatted[column] = pretty_values

    formatted = formatted.drop(columns=["dataset"])
    if tabulate is not None:
        return tabulate(formatted, headers="keys", tablefmt="github", showindex=False)

    lines = []
    headers = list(formatted.columns)
    widths = {
        column: max(len(column), *(len(str(value)) for value in formatted[column]))
        for column in headers
    }
    header_line = "| " + " | ".join(f"{column:<{widths[column]}}" for column in headers) + " |"
    divider = "| " + " | ".join("-" * widths[column] for column in headers) + " |"
    lines.extend([header_line, divider])
    for _, row in formatted.iterrows():
        lines.append("| " + " | ".join(f"{str(row[column]):<{widths[column]}}" for column in headers) + " |")
    return "\n".join(lines)


def get_context(dataset_name: str) -> DatasetContext:
    if dataset_name == "DAPT2020":
        return get_dapt_context()
    if dataset_name == "Unraveled":
        return get_unraveled_context()
    raise ValueError(f"Unsupported dataset: {dataset_name}")


def concat_context_frames(context: DatasetContext) -> pd.DataFrame:
    frame = pd.concat(
        [
            context.train_df.assign(split="train"),
            context.val_df.assign(split="val"),
            context.test_df.assign(split="test"),
        ],
        ignore_index=True,
    )
    if "timestamp_sort" in frame.columns:
        return frame.sort_values("timestamp_sort").reset_index(drop=True)
    return frame.reset_index(drop=True)


def unraveled_model_result_path(model_name: str) -> Path:
    return resolve_path(CONFIG["unraveled_run_dir"]) / f"{file_slug(model_name)}_results.json"


def load_unraveled_model_result(model_name: str) -> dict[str, Any] | None:
    cache_key = f"unraveled_model_result:{model_name}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    path = unraveled_model_result_path(model_name)
    payload = load_json(path)
    _CACHE[cache_key] = payload
    return payload


def metric_columns(dataset_name: str) -> list[str]:
    return [
        "Benign F1",
        "Recon F1",
        "Foothold F1",
        "LM F1",
        "DE F1",
        "Macro F1",
        DATASET_SPECS[dataset_name]["summary_metric_label"],
    ]


def known_runtime_metrics(dataset_name: str, model_name: str) -> dict[str, Any]:
    raw = KNOWN_RESULTS[dataset_name][model_name]
    summary_key = DATASET_SPECS[dataset_name]["summary_metric_key"]
    return {
        "per_class_f1": {
            "Benign": raw["benign_f1"],
            "Reconnaissance": raw["recon_f1"],
            "Establish Foothold": raw["foothold_f1"],
            "Lateral Movement": raw["lm_f1"],
            "Data Exfiltration": raw["de_f1"],
        },
        "macro_f1": raw["macro_f1"],
        summary_key: raw["summary_metric"],
    }


def render_table(frame: pd.DataFrame, floatfmt: str = ".4f") -> str:
    if tabulate is not None:
        return tabulate(frame, headers="keys", tablefmt="github", showindex=False, floatfmt=floatfmt)
    return frame.to_string(index=False)


def delta_row(
    dataset_name: str,
    model_name: str,
    new_metrics: dict[str, Any],
    reference_metrics: dict[str, Any],
    reference_label: str,
) -> dict[str, Any]:
    new_row = wide_metric_row(dataset_name, model_name, new_metrics)
    ref_row = wide_metric_row(dataset_name, model_name, reference_metrics)
    delta = {
        "dataset": dataset_name,
        "model": display_name(dataset_name, model_name),
        "reference": reference_label,
    }
    for column in metric_columns(dataset_name):
        new_value = new_row.get(column)
        ref_value = ref_row.get(column)
        if new_value is None or ref_value is None:
            delta[f"Δ {column}"] = np.nan
        else:
            delta[f"Δ {column}"] = float(new_value - ref_value)
    return delta


def wide_row_to_runtime_metrics(dataset_name: str, row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    summary_key = DATASET_SPECS[dataset_name]["summary_metric_key"]
    summary_label = DATASET_SPECS[dataset_name]["summary_metric_label"]
    source = dict(row)
    return {
        "per_class_f1": {
            "Benign": float(source["Benign F1"]),
            "Reconnaissance": float(source["Recon F1"]),
            "Establish Foothold": float(source["Foothold F1"]),
            "Lateral Movement": float(source["LM F1"]),
            "Data Exfiltration": float(source["DE F1"]),
        },
        "macro_f1": float(source["Macro F1"]),
        summary_key: None if pd.isna(source.get(summary_label)) else float(source[summary_label]),
    }


def save_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def require_plotting() -> None:
    if plt is None:
        raise SectionSkip("matplotlib is not installed.")


def labels_from_frame(frame: pd.DataFrame) -> np.ndarray:
    return frame["MultiLabel"].to_numpy(dtype=np.int64)


def balanced_class_weight_tensor(labels: np.ndarray) -> torch.Tensor:
    classes = np.arange(len(STAGE_NAMES), dtype=np.int64)
    weights = np.ones(len(classes), dtype=np.float32)
    present = np.unique(labels)
    if len(present) > 0:
        present_weights = compute_class_weight(class_weight="balanced", classes=present, y=labels)
        for index, cls in enumerate(present):
            weights[int(cls)] = float(present_weights[index])
    return torch.tensor(weights, dtype=torch.float32)


def collect_graph_labels(graphs: list[Any]) -> np.ndarray:
    if not graphs:
        return np.asarray([], dtype=np.int64)
    return np.concatenate([graph.y.cpu().numpy().astype(np.int64) for graph in graphs], axis=0)


def get_unraveled_best_params(model_name: str) -> dict[str, Any]:
    result = load_unraveled_model_result(model_name)
    if result is not None and isinstance(result.get("best_params"), dict):
        return dict(result["best_params"])
    context = get_unraveled_context()
    if context.run_summary is not None:
        result = context.run_summary.get("results", {}).get(model_name)
        if isinstance(result, dict) and isinstance(result.get("best_params"), dict):
            return dict(result["best_params"])
    return {}


def get_dapt_best_params(model_name: str) -> dict[str, Any]:
    params = latest_dapt_optuna_params(model_name)
    if params is None:
        return {}
    return {
        "hidden_dim": int(params.get("hidden_dim", 64)),
        "dropout": float(params.get("dropout", 0.5)),
        "lr": float(params.get("learning_rate", 1e-3)),
        "weight_decay": float(params.get("weight_decay", 1e-4)),
        "batch_size": int(params.get("batch_size", 2)),
        "graph_k": int(params.get("k_value", 5)),
        "temporal_k": int(params.get("temporal_k", 4)),
    }


def maybe_load_pretrained_dgi_encoder(
    dataset_name: str,
    num_features: int,
    hidden_dim: int,
) -> Any | None:
    if dataset_name != "DAPT2020":
        return None
    path = resolve_path(CONFIG["dapt_run_dir"]) / "dgi_pretrained_encoder.pt"
    if not path.exists():
        return None
    helper_module = get_dapt_context().helper_module
    encoder = helper_module.DGIEncoder(num_features=num_features, hidden_dim=hidden_dim)
    state = load_torch_checkpoint(path)
    encoder.load_state_dict(state, strict=False)
    return encoder


def instantiate_unraveled_model(model_name: str, params: dict[str, Any]) -> nn.Module:
    context = get_unraveled_context()
    if model_name == "MLP":
        return v02.MLPStageClassifier(
            num_features=len(context.feature_cols),
            hidden_dim=int(params.get("hidden_dim", 128)),
            num_layers=int(params.get("num_layers", 2)),
            dropout=float(params.get("dropout", 0.3)),
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "Mamba":
        return v02.MambaStageClassifier(
            num_features=len(context.feature_cols),
            d_model=int(params.get("d_model", 64)),
            n_layers=int(params.get("n_layers", 2)),
            d_state=int(params.get("d_state", 8)),
            d_conv=int(params.get("d_conv", 4)),
            dropout=float(params.get("dropout", 0.2)),
            num_classes=len(STAGE_NAMES),
        )
    return v02.instantiate_graph_model(
        model_name=model_name,
        num_features=len(context.feature_cols) + 2,
        params=params,
        gml=context.helper_module,
        pretrained_encoder=None,
    )


def instantiate_dapt_model(model_name: str, params: dict[str, Any]) -> nn.Module:
    context = get_dapt_context()
    helper_module = context.helper_module
    num_features = len(context.feature_cols) + 2
    hidden_dim = int(params.get("hidden_dim", 64))
    dropout = float(params.get("dropout", 0.5))
    if model_name == "GATv2":
        return helper_module.NodeLevelGATv2(
            num_features=num_features,
            hidden_dim=hidden_dim,
            heads=int(params.get("heads", 8)),
            dropout=dropout,
            attention_dropout=float(params.get("attention_dropout", 0.2)),
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "RGCN":
        return helper_module.NodeLevelRGCN(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "ST-GCN":
        return helper_module.NodeLevelSTGCN(
            num_features=num_features,
            hidden_dim=hidden_dim,
            num_st_blocks=int(params.get("num_st_blocks", 3)),
            dropout=dropout,
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "GIN":
        return helper_module.NodeLevelGIN(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "GCN-DGI":
        pretrained_encoder = maybe_load_pretrained_dgi_encoder(
            dataset_name="DAPT2020",
            num_features=num_features,
            hidden_dim=hidden_dim,
        )
        return helper_module.NodeLevelGCN_DGI(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            pretrained_encoder=pretrained_encoder,
            num_classes=len(STAGE_NAMES),
        )
    raise ValueError(f"Unsupported DAPT model: {model_name}")


def load_state_into_model(model: nn.Module, checkpoint_path: Path) -> nn.Module:
    state = load_torch_checkpoint(checkpoint_path)
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        print(f"  Warning: missing keys while loading {checkpoint_path.name}: {sorted(missing)[:5]}")
    if unexpected:
        print(f"  Warning: unexpected keys while loading {checkpoint_path.name}: {sorted(unexpected)[:5]}")
    return model


def build_unraveled_graphs_with_row_ids(df: pd.DataFrame, model_name: str) -> list[Any]:
    context = get_unraveled_context()
    settings = context.settings
    feature_cols = context.feature_cols
    flows_per_graph = int(settings.get("flows_per_graph", 512))
    min_graph_size = int(settings.get("min_graph_size", 64))
    graph_k = int(settings.get("graph_k", 5))
    temporal_k = int(settings.get("stgcn_temporal_k", 4))
    graphs: list[Any] = []
    ordered_groups = df.groupby("source_file")["timestamp_sort"].min().sort_values().index.tolist()

    for source_file in ordered_groups:
        source_df = df[df["source_file"] == source_file].sort_values("timestamp_sort").reset_index(drop=True)
        for start in range(0, len(source_df), flows_per_graph):
            chunk = source_df.iloc[start : start + flows_per_graph].copy()
            if len(chunk) < min_graph_size:
                continue
            if model_name == "RGCN":
                graph = context.helper_module.build_graph_with_custom_k_rgcn(chunk, feature_cols, k=graph_k)
            elif model_name == "ST-GCN":
                graph = context.helper_module.build_graph_with_custom_k_stgnn(
                    chunk,
                    feature_cols,
                    k=graph_k,
                    temporal_k=temporal_k,
                )
            else:
                graph = context.helper_module.build_graph_with_custom_k(chunk, feature_cols, k=graph_k)
            if graph is None:
                continue
            graph.row_ids = torch.tensor(chunk["diag_row_id"].to_numpy(dtype=np.int64), dtype=torch.long)
            graph.source_file = source_file
            graphs.append(graph)
    return graphs


def build_dapt_graphs_with_row_ids(df: pd.DataFrame, model_name: str) -> list[Any]:
    context = get_dapt_context()
    feature_cols = context.feature_cols
    params = get_dapt_best_params(model_name)
    graph_k = int(params.get("graph_k", context.settings.get("graph_k", 5)))
    temporal_k = int(params.get("temporal_k", 4))
    flows_per_graph = int(context.settings.get("flows_per_graph", 1000))
    groups: list[tuple[str, pd.DataFrame]] = []
    if "network_type" in df.columns and df["network_type"].nunique() > 1:
        for network_type, network_df in df.groupby("network_type", sort=False):
            groups.append((str(network_type), network_df.sort_values("timestamp_sort").reset_index(drop=True)))
    else:
        groups.append(("all", df.sort_values("timestamp_sort").reset_index(drop=True)))

    graphs: list[Any] = []
    for network_type, network_df in groups:
        for start in range(0, len(network_df), flows_per_graph):
            chunk = network_df.iloc[start : start + flows_per_graph].copy()
            if len(chunk) < 100:
                continue
            if model_name == "RGCN":
                graph = context.helper_module.build_graph_with_custom_k_rgcn(chunk, feature_cols, k=graph_k)
            elif model_name == "ST-GCN":
                graph = context.helper_module.build_graph_with_custom_k_stgnn(
                    chunk,
                    feature_cols,
                    k=graph_k,
                    temporal_k=temporal_k,
                )
            else:
                graph = context.helper_module.build_graph_with_custom_k(chunk, feature_cols, k=graph_k)
            if graph is None:
                continue
            graph.row_ids = torch.tensor(chunk["diag_row_id"].to_numpy(dtype=np.int64), dtype=torch.long)
            graph.network_type = network_type
            graphs.append(graph)
    return graphs


def get_graph_splits(dataset_name: str, model_name: str) -> tuple[list[Any], list[Any], list[Any]]:
    cache_key = f"graph_splits:{dataset_name}:{model_name}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    context = get_context(dataset_name)
    if dataset_name == "Unraveled":
        value = (
            build_unraveled_graphs_with_row_ids(context.train_df, model_name),
            build_unraveled_graphs_with_row_ids(context.val_df, model_name),
            build_unraveled_graphs_with_row_ids(context.test_df, model_name),
        )
    else:
        value = (
            build_dapt_graphs_with_row_ids(context.train_df, model_name),
            build_dapt_graphs_with_row_ids(context.val_df, model_name),
            build_dapt_graphs_with_row_ids(context.test_df, model_name),
        )
    _CACHE[cache_key] = value
    return value


def predict_row_model(
    model: nn.Module,
    frame: pd.DataFrame,
    feature_cols: list[str],
    device: torch.device,
    batch_size: int = 4096,
) -> pd.DataFrame:
    model = model.to(device)
    model.eval()
    x = frame[feature_cols].to_numpy(dtype=np.float32)
    y = frame["MultiLabel"].to_numpy(dtype=np.int64)
    row_ids = frame["diag_row_id"].to_numpy(dtype=np.int64)
    outputs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(frame), batch_size):
            batch_x = torch.from_numpy(x[start : start + batch_size]).to(device)
            logits = model(batch_x)
            outputs.append(torch.softmax(logits, dim=1).cpu().numpy())
    probs = np.vstack(outputs) if outputs else np.zeros((0, len(STAGE_NAMES)), dtype=np.float32)
    preds = probs.argmax(axis=1) if len(probs) else np.asarray([], dtype=np.int64)
    payload = {
        "diag_row_id": row_ids,
        "true_label_id": y,
        "predicted_label_id": preds,
        "max_softmax_prob": probs.max(axis=1) if len(probs) else np.asarray([], dtype=np.float32),
    }
    for index, stage_name in enumerate(STAGE_NAMES):
        payload[f"prob_{stage_name}"] = probs[:, index] if len(probs) else np.asarray([], dtype=np.float32)
    return pd.DataFrame(payload).sort_values("diag_row_id").reset_index(drop=True)


def predict_graph_model(
    model: nn.Module,
    graphs: list[Any],
    device: torch.device,
    batch_size: int,
) -> pd.DataFrame:
    model = model.to(device)
    model.eval()
    loader = GraphDataLoader(graphs, batch_size=batch_size, shuffle=False)
    rows: list[pd.DataFrame] = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = v02.graph_forward(model, batch)
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            preds = probs.argmax(axis=1)
            payload = {
                "diag_row_id": batch.row_ids.cpu().numpy().astype(np.int64),
                "true_label_id": batch.y.cpu().numpy().astype(np.int64),
                "predicted_label_id": preds.astype(np.int64),
                "max_softmax_prob": probs.max(axis=1).astype(np.float32),
            }
            for index, stage_name in enumerate(STAGE_NAMES):
                payload[f"prob_{stage_name}"] = probs[:, index].astype(np.float32)
            rows.append(pd.DataFrame(payload))
    if not rows:
        return pd.DataFrame(
            columns=[
                "diag_row_id",
                "true_label_id",
                "predicted_label_id",
                "max_softmax_prob",
                *[f"prob_{stage_name}" for stage_name in STAGE_NAMES],
            ]
        )
    return pd.concat(rows, ignore_index=True).sort_values("diag_row_id").reset_index(drop=True)


def build_sequence_chunks_with_ids(
    df: pd.DataFrame,
    feature_cols: list[str],
    sequence_length: int,
    min_sequence_length: int,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    chunks: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    ordered_groups = df.groupby("source_file")["timestamp_sort"].min().sort_values().index.tolist()
    for source_file in ordered_groups:
        source_df = df[df["source_file"] == source_file].sort_values("timestamp_sort").reset_index(drop=True)
        xs = source_df[feature_cols].to_numpy(dtype=np.float32)
        ys = source_df["MultiLabel"].to_numpy(dtype=np.int64)
        row_ids = source_df["diag_row_id"].to_numpy(dtype=np.int64)
        for start in range(0, len(source_df), sequence_length):
            x_chunk = xs[start : start + sequence_length]
            y_chunk = ys[start : start + sequence_length]
            id_chunk = row_ids[start : start + sequence_length]
            if len(x_chunk) < min_sequence_length:
                continue
            chunks.append((x_chunk, y_chunk, id_chunk))
    return chunks


def collate_sequence_chunks_with_ids(batch: list[tuple[np.ndarray, np.ndarray, np.ndarray]]):
    max_len = max(item[0].shape[0] for item in batch)
    feat_dim = batch[0][0].shape[1]
    xs = torch.zeros((len(batch), max_len, feat_dim), dtype=torch.float32)
    ys = torch.full((len(batch), max_len), -100, dtype=torch.long)
    row_ids = torch.full((len(batch), max_len), -1, dtype=torch.long)
    mask = torch.zeros((len(batch), max_len), dtype=torch.bool)
    for index, (x_chunk, y_chunk, id_chunk) in enumerate(batch):
        length = x_chunk.shape[0]
        xs[index, :length] = torch.from_numpy(x_chunk)
        ys[index, :length] = torch.from_numpy(y_chunk)
        row_ids[index, :length] = torch.from_numpy(id_chunk)
        mask[index, :length] = True
    return xs, ys, mask, row_ids


def predict_sequence_model(
    model: nn.Module,
    frame: pd.DataFrame,
    feature_cols: list[str],
    settings: dict[str, Any],
    device: torch.device,
) -> pd.DataFrame:
    chunks = build_sequence_chunks_with_ids(
        frame,
        feature_cols,
        sequence_length=int(settings.get("sequence_length", 512)),
        min_sequence_length=int(settings.get("min_sequence_length", 64)),
    )
    loader = DataLoader(
        chunks,
        batch_size=int(settings.get("sequence_batch_size", 8)),
        shuffle=False,
        collate_fn=collate_sequence_chunks_with_ids,
    )
    model = model.to(device)
    model.eval()
    rows: list[pd.DataFrame] = []
    with torch.no_grad():
        for xs, ys, mask, row_ids in loader:
            xs = xs.to(device)
            ys = ys.to(device)
            mask = mask.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=-1)
            flat_mask = mask.view(-1)
            flat_probs = probs.view(-1, probs.shape[-1])[flat_mask].cpu().numpy()
            flat_labels = ys.view(-1)[flat_mask].cpu().numpy()
            flat_ids = row_ids.view(-1)[flat_mask.cpu()].numpy()
            preds = flat_probs.argmax(axis=1)
            payload = {
                "diag_row_id": flat_ids.astype(np.int64),
                "true_label_id": flat_labels.astype(np.int64),
                "predicted_label_id": preds.astype(np.int64),
                "max_softmax_prob": flat_probs.max(axis=1).astype(np.float32),
            }
            for index, stage_name in enumerate(STAGE_NAMES):
                payload[f"prob_{stage_name}"] = flat_probs[:, index].astype(np.float32)
            rows.append(pd.DataFrame(payload))
    if not rows:
        return pd.DataFrame(
            columns=[
                "diag_row_id",
                "true_label_id",
                "predicted_label_id",
                "max_softmax_prob",
                *[f"prob_{stage_name}" for stage_name in STAGE_NAMES],
            ]
        )
    return pd.concat(rows, ignore_index=True).sort_values("diag_row_id").reset_index(drop=True)


def predictions_to_metrics(predictions: pd.DataFrame) -> dict[str, Any]:
    y_true = predictions["true_label_id"].to_numpy(dtype=np.int64)
    y_pred = predictions["predicted_label_id"].to_numpy(dtype=np.int64)
    y_prob = predictions[[f"prob_{stage_name}" for stage_name in STAGE_NAMES]].to_numpy(dtype=np.float32)
    return compute_multiclass_metrics(y_true=y_true, y_pred=y_pred, y_prob=y_prob)


def add_label_names(predictions: pd.DataFrame) -> pd.DataFrame:
    output = predictions.copy()
    output["true_label"] = output["true_label_id"].map(lambda idx: STAGE_NAMES[int(idx)])
    output["predicted_label"] = output["predicted_label_id"].map(lambda idx: STAGE_NAMES[int(idx)])
    return output


def get_model_for_inference(dataset_name: str, model_name: str) -> nn.Module | None:
    checkpoint = find_checkpoint(dataset_name, model_name)
    if checkpoint is None:
        return None
    if dataset_name == "Unraveled":
        model = instantiate_unraveled_model(model_name, get_unraveled_best_params(model_name))
    else:
        model = instantiate_dapt_model(model_name, get_dapt_best_params(model_name))
    return load_state_into_model(model, checkpoint)


def confusion_from_artifacts(dataset_name: str) -> dict[str, np.ndarray]:
    matrices: dict[str, np.ndarray] = {}
    if dataset_name == "DAPT2020":
        matrices.update(dapt_console_confusions())
    else:
        for model_name in DATASET_SPECS["Unraveled"]["models"]:
            result = load_unraveled_model_result(model_name)
            if result is None:
                continue
            confusion = result.get("test_metrics", {}).get("confusion_matrix")
            if confusion is not None:
                matrices[model_name] = np.asarray(confusion, dtype=np.int64)
    return matrices


def confusion_from_checkpoint(dataset_name: str, model_name: str) -> np.ndarray | None:
    model = get_model_for_inference(dataset_name, model_name)
    if model is None:
        return None
    device = get_device()
    context = get_context(dataset_name)
    if dataset_name == "Unraveled" and model_name in {"MLP", "Mamba"}:
        if model_name == "MLP":
            predictions = predict_row_model(model, context.test_df, context.feature_cols, device)
        else:
            predictions = predict_sequence_model(model, context.test_df, context.feature_cols, context.settings, device)
    else:
        _, _, test_graphs = get_graph_splits(dataset_name, model_name)
        batch_size = int(context.settings.get("graph_batch_size", 4))
        if dataset_name == "DAPT2020":
            batch_size = int(get_dapt_best_params(model_name).get("batch_size", 2))
        predictions = predict_graph_model(model, test_graphs, device=device, batch_size=batch_size)
    metrics = predictions_to_metrics(predictions)
    return np.asarray(metrics["confusion_matrix"], dtype=np.int64)


def draw_confusion_heatmap(ax, confusion: np.ndarray, title: str) -> None:
    matrix = confusion.astype(np.float64)
    row_sums = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(matrix, np.maximum(row_sums, 1.0), where=row_sums >= 0)
    if sns is not None:
        sns.heatmap(
            normalized,
            ax=ax,
            cmap="mako",
            annot=confusion,
            fmt="d",
            cbar=False,
            xticklabels=[name.split()[0] for name in STAGE_NAMES],
            yticklabels=[name.split()[0] for name in STAGE_NAMES],
        )
    else:
        im = ax.imshow(normalized, cmap="mako")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_xticks(range(len(STAGE_NAMES)))
        ax.set_yticks(range(len(STAGE_NAMES)))
        ax.set_xticklabels([name.split()[0] for name in STAGE_NAMES], rotation=45, ha="right")
        ax.set_yticklabels([name.split()[0] for name in STAGE_NAMES])
        for i in range(confusion.shape[0]):
            for j in range(confusion.shape[1]):
                ax.text(j, i, int(confusion[i, j]), ha="center", va="center", fontsize=8)
    ax.set_title(title)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")


def save_confusion_grid(dataset_name: str, matrices: dict[str, np.ndarray], out_path: Path) -> None:
    model_names = [name for name in DATASET_SPECS[dataset_name]["models"] if name in matrices]
    if not model_names:
        return
    fig, axes = plt.subplots(1, len(model_names), figsize=(4.2 * len(model_names), 4.2), squeeze=False)
    for axis, model_name in zip(axes[0], model_names):
        draw_confusion_heatmap(axis, matrices[model_name], display_name(dataset_name, model_name))
    fig.suptitle(f"{dataset_name} Confusion Matrices", fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def evaluate_sequence_model_probabilities(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, np.ndarray]:
    model.eval()
    preds: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    probs_list: list[np.ndarray] = []
    with torch.no_grad():
        for xs, ys, mask in loader:
            xs = xs.to(device)
            ys = ys.to(device)
            mask = mask.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=-1)
            flat_mask = mask.view(-1)
            flat_probs = probs.view(-1, probs.shape[-1])[flat_mask]
            flat_labels = ys.view(-1)[flat_mask]
            preds.append(flat_probs.argmax(dim=1).cpu().numpy())
            labels.append(flat_labels.cpu().numpy())
            probs_list.append(flat_probs.cpu().numpy())
    return {
        "y_true": np.concatenate(labels) if labels else np.asarray([], dtype=np.int64),
        "y_pred": np.concatenate(preds) if preds else np.asarray([], dtype=np.int64),
        "y_prob": np.vstack(probs_list) if probs_list else np.zeros((0, len(STAGE_NAMES)), dtype=np.float32),
    }


def train_graph_model_custom_loss(
    model: nn.Module,
    train_graphs: list[Any],
    val_graphs: list[Any],
    device: torch.device,
    lr: float,
    weight_decay: float,
    batch_size: int,
    epochs: int,
    patience: int,
    criterion: nn.Module,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = criterion.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    train_loader = GraphDataLoader(train_graphs, batch_size=batch_size, shuffle=True)

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_examples = 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            logits = v02.graph_forward(model, batch)
            loss = criterion(logits, batch.y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += float(loss.item()) * int(batch.y.numel())
            total_examples += int(batch.y.numel())
        val_predictions = predict_graph_model(model, val_graphs, device=device, batch_size=batch_size)
        val_metrics = predictions_to_metrics(val_predictions)
        history.append(
            {
                "epoch": epoch,
                "train_loss": total_loss / max(total_examples, 1),
                "val_macro_f1": val_metrics["macro_f1"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        if val_metrics["macro_f1"] > best_score:
            best_score = val_metrics["macro_f1"]
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Graph training ended without a best validation checkpoint.")
    model.load_state_dict(best_state)
    return model, best_metrics, history


def train_sequence_model_custom_loss(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    device: torch.device,
    lr: float,
    weight_decay: float,
    epochs: int,
    patience: int,
    criterion: nn.Module,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = criterion.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_tokens = 0
        for xs, ys, mask in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            mask = mask.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits.view(-1, logits.shape[-1]), ys.view(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += float(loss.item()) * int(mask.sum().item())
            total_tokens += int(mask.sum().item())
        val_predictions = evaluate_sequence_model_probabilities(model, val_loader, device)
        val_metrics = compute_multiclass_metrics(
            val_predictions["y_true"],
            val_predictions["y_pred"],
            val_predictions["y_prob"],
        )
        history.append(
            {
                "epoch": epoch,
                "train_loss": total_loss / max(total_tokens, 1),
                "val_macro_f1": val_metrics["macro_f1"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        if val_metrics["macro_f1"] > best_score:
            best_score = val_metrics["macro_f1"]
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Sequence training ended without a best validation checkpoint.")
    model.load_state_dict(best_state)
    return model, best_metrics, history


def smote_feature_pool_graphs(graphs: list[Any], random_seed: int) -> tuple[list[Any], dict[str, Any]]:
    if SMOTE is None:
        raise RuntimeError("imbalanced-learn is not installed, so SMOTE is unavailable.")
    features = np.concatenate([graph.x.cpu().numpy() for graph in graphs], axis=0)
    labels = np.concatenate([graph.y.cpu().numpy() for graph in graphs], axis=0)
    class_counts = Counter(labels.tolist())
    minority_count = min(class_counts.values()) if class_counts else 0
    if minority_count < 2:
        raise RuntimeError("SMOTE requires at least 2 examples in the rarest class.")
    k_neighbors = max(1, min(5, minority_count - 1))
    sampler = SMOTE(random_state=random_seed, k_neighbors=k_neighbors)
    features_resampled, labels_resampled = sampler.fit_resample(features, labels)

    rng = np.random.default_rng(random_seed)
    pools: dict[int, np.ndarray] = {}
    pointers: dict[int, int] = {}
    for class_id in range(len(STAGE_NAMES)):
        pool = features_resampled[labels_resampled == class_id]
        if len(pool) == 0:
            pool = features[labels == class_id]
        pools[class_id] = pool[rng.permutation(len(pool))]
        pointers[class_id] = 0

    remapped: list[Any] = []
    for graph in graphs:
        updated = copy.deepcopy(graph)
        new_x = np.empty_like(updated.x.cpu().numpy())
        node_labels = updated.y.cpu().numpy().astype(np.int64)
        for node_index, class_id in enumerate(node_labels):
            pool = pools[int(class_id)]
            ptr = pointers[int(class_id)] % len(pool)
            new_x[node_index] = pool[ptr]
            pointers[int(class_id)] += 1
        updated.x = torch.tensor(new_x, dtype=updated.x.dtype)
        remapped.append(updated)

    summary = {
        "original_node_count": int(len(labels)),
        "resampled_node_count": int(len(labels_resampled)),
        "k_neighbors": int(k_neighbors),
        "original_class_counts": {STAGE_NAMES[int(k)]: int(v) for k, v in class_counts.items()},
        "resampled_class_counts": {
            STAGE_NAMES[int(class_id)]: int((labels_resampled == class_id).sum())
            for class_id in range(len(STAGE_NAMES))
        },
    }
    return remapped, summary


def graph_homophily_statistics(graphs: list[Any]) -> tuple[float, pd.DataFrame, np.ndarray]:
    label_matrix = np.zeros((len(STAGE_NAMES), len(STAGE_NAMES)), dtype=np.int64)
    same_edges = 0
    total_edges = 0
    class_same = np.zeros(len(STAGE_NAMES), dtype=np.int64)
    class_total = np.zeros(len(STAGE_NAMES), dtype=np.int64)

    for graph in graphs:
        edge_index = graph.edge_index.cpu().numpy()
        labels = graph.y.cpu().numpy().astype(np.int64)
        for src, dst in edge_index.T:
            src_label = int(labels[int(src)])
            dst_label = int(labels[int(dst)])
            label_matrix[src_label, dst_label] += 1
            label_matrix[dst_label, src_label] += 1
            total_edges += 1
            class_total[src_label] += 1
            class_total[dst_label] += 1
            if src_label == dst_label:
                same_edges += 1
                class_same[src_label] += 2

    per_class_rows = []
    for class_id, stage_name in enumerate(STAGE_NAMES):
        total = int(class_total[class_id])
        same = int(class_same[class_id])
        homophily = float(same / total) if total else 0.0
        per_class_rows.append(
            {
                "dataset": "",
                "model": "base_graph",
                "class_name": stage_name,
                "incident_edges": total,
                "same_class_edge_incidents": same,
                "homophily": homophily,
            }
        )

    overall = float(same_edges / total_edges) if total_edges else 0.0
    per_class_frame = pd.DataFrame(per_class_rows).sort_values("homophily", ascending=False).reset_index(drop=True)
    return overall, per_class_frame, label_matrix


def plot_edge_label_heatmap(dataset_name: str, label_matrix: np.ndarray, out_path: Path) -> None:
    matrix = label_matrix.astype(np.float64)
    row_sums = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(matrix, np.maximum(row_sums, 1.0), where=row_sums >= 0)
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    if sns is not None:
        sns.heatmap(
            normalized,
            cmap="mako",
            annot=label_matrix,
            fmt="d",
            xticklabels=[name.split()[0] for name in STAGE_NAMES],
            yticklabels=[name.split()[0] for name in STAGE_NAMES],
            ax=ax,
        )
    else:
        im = ax.imshow(normalized, cmap="mako")
        plt.colorbar(im, ax=ax)
        ax.set_xticks(range(len(STAGE_NAMES)))
        ax.set_yticks(range(len(STAGE_NAMES)))
        ax.set_xticklabels([name.split()[0] for name in STAGE_NAMES], rotation=45, ha="right")
        ax.set_yticklabels([name.split()[0] for name in STAGE_NAMES])
    ax.set_title(f"{dataset_name} Label-to-Label Edge Counts (row-normalized)")
    ax.set_xlabel("Destination label")
    ax.set_ylabel("Source label")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


class FocalLoss(nn.Module):
    def __init__(self, alpha: torch.Tensor, gamma: float = 2.0, ignore_index: int = -100):
        super().__init__()
        self.register_buffer("alpha", alpha.float())
        self.gamma = float(gamma)
        self.ignore_index = int(ignore_index)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        valid_mask = targets != self.ignore_index
        logits = logits[valid_mask]
        targets = targets[valid_mask]
        if targets.numel() == 0:
            return logits.sum() * 0.0
        ce = F.cross_entropy(logits, targets, reduction="none", weight=self.alpha)
        probs = torch.softmax(logits, dim=1)
        pt = probs.gather(1, targets.unsqueeze(1)).squeeze(1).clamp_min(1e-8)
        return (((1.0 - pt) ** self.gamma) * ce).mean()


def mamba_alpha_from_labels(labels: np.ndarray) -> torch.Tensor:
    counts = np.bincount(labels, minlength=len(STAGE_NAMES)).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    alpha = counts.sum() / counts
    alpha = alpha / alpha.mean()
    return torch.tensor(alpha.astype(np.float32))


def extract_mlp_penultimate(model: nn.Module, x: torch.Tensor) -> torch.Tensor:
    return model.network[:-1](x)


def extract_mamba_penultimate(model: nn.Module, x: torch.Tensor) -> torch.Tensor:
    hidden = model.input_dropout(model.input_proj(x))
    hidden = model.backbone(hidden)
    hidden = model.output_dropout(model.output_norm(hidden))
    return hidden


def extract_gcndgi_embeddings(model: nn.Module, batch) -> torch.Tensor:
    x = F.relu(model.bn1(model.conv1(batch.x, batch.edge_index)))
    x = model.dropout(x)
    x = F.relu(model.bn2(model.conv2(x, batch.edge_index)))
    x = model.dropout(x)
    return model.conv3(x, batch.edge_index)


def run_s0_display_known_results() -> None:
    section_name = "S0_display_known_results"
    out_dir, should_skip = start_section(section_name, ["known_results.csv", "tables.md"])
    if should_skip:
        return

    dapt_frame = known_results_frame("DAPT2020")
    unraveled_frame = known_results_frame("Unraveled")
    combined = pd.concat([dapt_frame, unraveled_frame], ignore_index=True)
    save_dataframe(out_dir / "known_results.csv", combined)

    markdown = []
    for dataset_name in ("DAPT2020", "Unraveled"):
        markdown.append(f"## {dataset_name}")
        markdown.append("")
        markdown.append(format_results_table(dataset_name))
        markdown.append("")
        print(f"\n{dataset_name}")
        print(format_results_table(dataset_name))

    save_markdown(out_dir / "tables.md", "\n".join(markdown).strip() + "\n")
    finish_section(
        section_name,
        out_dir,
        {"datasets": 2, "rows_saved": int(len(combined)), "outputs": ["known_results.csv", "tables.md"]},
    )


def run_s1_class_distribution() -> None:
    section_name = "S1_class_distribution"
    out_dir, should_skip = start_section(section_name, ["class_counts.csv", "class_distribution.png"])
    if should_skip:
        return
    require_plotting()

    rows: list[dict[str, Any]] = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    summary: dict[str, Any] = {}

    for axis, dataset_name in zip(axes, ("DAPT2020", "Unraveled")):
        context = get_context(dataset_name)
        frame = concat_context_frames(context)
        counts = frame["MultiLabel"].value_counts().reindex(range(len(STAGE_NAMES)), fill_value=0).sort_index()
        total = int(counts.sum())
        majority_class = int(counts.idxmax())
        minority_nonzero = counts[counts > 0]
        minority = int(minority_nonzero.min()) if len(minority_nonzero) else 0
        imbalance_ratio = float(counts.max() / minority) if minority else float("inf")

        y_true = np.concatenate(
            [np.full(int(count), class_id, dtype=np.int64) for class_id, count in counts.items()],
            axis=0,
        )
        y_pred = np.full_like(y_true, fill_value=majority_class)
        baseline_f1 = compute_multiclass_metrics(
            y_true=y_true,
            y_pred=y_pred,
            y_prob=np.eye(len(STAGE_NAMES), dtype=np.float32)[y_pred],
        )["per_class_f1"]

        axis.bar([name.split()[0] for name in STAGE_NAMES], counts.values, color=ACCENT)
        axis.set_title(f"{dataset_name} Class Counts")
        axis.set_ylabel("Rows")
        axis.tick_params(axis="x", rotation=35)

        critical = []
        print(f"\n{dataset_name} class distribution")
        print(f"  Imbalance ratio (majority/minority): {imbalance_ratio:.2f}")
        for class_id, stage_name in enumerate(STAGE_NAMES):
            count = int(counts.iloc[class_id])
            pct_total = float(count / max(total, 1))
            critically_imbalanced = pct_total < 0.01
            if critically_imbalanced:
                critical.append(stage_name)
            print(
                f"  {stage_name:<20} count={count:>8,} "
                f"pct={pct_total * 100:>6.2f}% "
                f"majority-baseline-F1={baseline_f1[stage_name]:.4f}"
                + ("  critically imbalanced" if critically_imbalanced else "")
            )
            rows.append(
                {
                    "dataset": dataset_name,
                    "model": "dataset_summary",
                    "class_name": stage_name,
                    "count": count,
                    "pct_total": pct_total,
                    "imbalance_ratio": imbalance_ratio,
                    "majority_baseline_f1": baseline_f1[stage_name],
                    "critically_imbalanced": critically_imbalanced,
                }
            )

        summary[dataset_name] = {
            "rows": total,
            "imbalance_ratio": imbalance_ratio,
            "critical_classes": critical,
        }

    fig.tight_layout()
    fig.savefig(out_dir / "class_distribution.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    save_dataframe(out_dir / "class_counts.csv", pd.DataFrame(rows))
    finish_section(section_name, out_dir, summary)


def run_s2_confusion_matrices() -> None:
    section_name = "S2_confusion_matrices"
    out_dir, should_skip = start_section(
        section_name,
        ["DAPT2020_confusion_grid.png", "Unraveled_confusion_grid.png", "confusions.csv"],
    )
    if should_skip:
        return
    require_plotting()

    cell_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    for dataset_name in ("DAPT2020", "Unraveled"):
        matrices = confusion_from_artifacts(dataset_name)
        for model_name in DATASET_SPECS[dataset_name]["models"]:
            if model_name in matrices:
                continue
            inferred = confusion_from_checkpoint(dataset_name, model_name)
            if inferred is not None:
                matrices[model_name] = inferred

        per_dataset_summary = {"models_plotted": 0, "missing_models": []}
        for model_name in DATASET_SPECS[dataset_name]["models"]:
            matrix = matrices.get(model_name)
            if matrix is None:
                per_dataset_summary["missing_models"].append(display_name(dataset_name, model_name))
                continue
            model_png = out_dir / f"{dataset_name}_{file_slug(model_name)}_confusion.png"
            if not model_png.exists():
                fig, ax = plt.subplots(figsize=(4.2, 4.2))
                draw_confusion_heatmap(ax, matrix, display_name(dataset_name, model_name))
                fig.tight_layout()
                fig.savefig(model_png, dpi=180, bbox_inches="tight")
                plt.close(fig)

            best_i, best_j, best_value = offdiag_argmax(matrix)
            if best_value > 0:
                print(
                    f"[{dataset_name}] {display_name(dataset_name, model_name)} most confuses "
                    f"{STAGE_NAMES[best_i]} as {STAGE_NAMES[best_j]} ({best_value})"
                )
            else:
                print(f"[{dataset_name}] {display_name(dataset_name, model_name)} shows no off-diagonal confusion.")

            per_dataset_summary["models_plotted"] = int(per_dataset_summary["models_plotted"]) + 1
            for true_index, true_name in enumerate(STAGE_NAMES):
                for pred_index, pred_name in enumerate(STAGE_NAMES):
                    cell_rows.append(
                        {
                            "dataset": dataset_name,
                            "model": display_name(dataset_name, model_name),
                            "true_label": true_name,
                            "predicted_label": pred_name,
                            "count": int(matrix[true_index, pred_index]),
                        }
                    )

        save_confusion_grid(dataset_name, matrices, out_dir / f"{dataset_name}_confusion_grid.png")
        summary[dataset_name] = per_dataset_summary

    save_dataframe(out_dir / "confusions.csv", pd.DataFrame(cell_rows))
    finish_section(section_name, out_dir, summary)


def rerun_target_models(dataset_name: str) -> list[str]:
    targets = []
    for model_name, metrics in KNOWN_RESULTS[dataset_name].items():
        if math.isclose(metrics["lm_f1"], 0.0, abs_tol=1e-12) or math.isclose(metrics["de_f1"], 0.0, abs_tol=1e-12):
            if model_name in DATASET_SPECS[dataset_name]["graph_models"]:
                targets.append(model_name)
    return targets


def training_params_for_model(dataset_name: str, model_name: str) -> dict[str, Any]:
    context = get_context(dataset_name)
    params = get_unraveled_best_params(model_name) if dataset_name == "Unraveled" else get_dapt_best_params(model_name)
    output = dict(params)
    output.setdefault("lr", float(params.get("lr", context.settings.get("learning_rate", 1e-3))))
    output.setdefault("weight_decay", float(params.get("weight_decay", 1e-4)))
    output.setdefault("batch_size", int(params.get("batch_size", context.settings.get("graph_batch_size", 4))))
    output.setdefault("epochs", int(context.settings.get("train_epochs", 12)))
    output.setdefault("patience", int(context.settings.get("early_stopping_patience", 6)))
    return output


def run_s3_class_weighted_rerun() -> None:
    section_name = "S3_class_weighted_rerun"
    out_dir, should_skip = start_section(section_name, ["results.csv", "delta_vs_original.csv"])
    if should_skip:
        return

    device = get_device()
    result_rows: list[dict[str, Any]] = []
    delta_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    for dataset_name in ("DAPT2020", "Unraveled"):
        dataset_models = rerun_target_models(dataset_name)
        summary[dataset_name] = {"trained_models": [], "skipped_models": []}
        for model_name in dataset_models:
            train_graphs, val_graphs, test_graphs = get_graph_splits(dataset_name, model_name)
            if not train_graphs or not val_graphs or not test_graphs:
                summary[dataset_name]["skipped_models"].append(display_name(dataset_name, model_name))
                continue

            labels = collect_graph_labels(train_graphs)
            class_weights = balanced_class_weight_tensor(labels)
            params = training_params_for_model(dataset_name, model_name)
            model = instantiate_unraveled_model(model_name, params) if dataset_name == "Unraveled" else instantiate_dapt_model(model_name, params)
            criterion = nn.CrossEntropyLoss(weight=class_weights)
            model, _, history = train_graph_model_custom_loss(
                model=model,
                train_graphs=train_graphs,
                val_graphs=val_graphs,
                device=device,
                lr=float(params["lr"]),
                weight_decay=float(params["weight_decay"]),
                batch_size=int(params["batch_size"]),
                epochs=int(params["epochs"]),
                patience=int(params["patience"]),
                criterion=criterion,
            )
            predictions = predict_graph_model(model, test_graphs, device=device, batch_size=int(params["batch_size"]))
            metrics = predictions_to_metrics(predictions)
            result_rows.append(wide_metric_row(dataset_name, model_name, metrics))
            delta_rows.append(
                delta_row(
                    dataset_name=dataset_name,
                    model_name=model_name,
                    new_metrics=metrics,
                    reference_metrics=known_runtime_metrics(dataset_name, model_name),
                    reference_label="original",
                )
            )
            save_json(
                out_dir / f"{dataset_name}_{file_slug(model_name)}.json",
                {"dataset": dataset_name, "model": model_name, "metrics": metrics, "history": history},
            )
            torch.save(model.state_dict(), out_dir / f"{dataset_name}_{file_slug(model_name)}.pt")
            summary[dataset_name]["trained_models"].append(display_name(dataset_name, model_name))

    results_frame = pd.DataFrame(result_rows)
    delta_frame = pd.DataFrame(delta_rows)
    if not results_frame.empty:
        print("\nS3 weighted rerun results")
        print(render_table(results_frame))
        save_dataframe(out_dir / "results.csv", results_frame)
    else:
        save_dataframe(out_dir / "results.csv", pd.DataFrame(columns=["dataset", "model"]))
    if not delta_frame.empty:
        print("\nS3 delta vs original")
        print(render_table(delta_frame))
        save_dataframe(out_dir / "delta_vs_original.csv", delta_frame)
    else:
        save_dataframe(out_dir / "delta_vs_original.csv", pd.DataFrame(columns=["dataset", "model", "reference"]))
    finish_section(section_name, out_dir, summary)


def run_s4_smote_rerun() -> None:
    section_name = "S4_smote_rerun"
    out_dir, should_skip = start_section(section_name, ["results.csv", "delta_vs_original.csv", "delta_vs_s3.csv"])
    if should_skip:
        return
    if SMOTE is None:
        skip_section(section_name, "imbalanced-learn is not installed.")
        return

    s3_frame = load_json(section_dir("S3_class_weighted_rerun") / "completion.json")
    _ = s3_frame  # marker so the section documents the dependency without requiring S3 results
    s3_results_path = section_dir("S3_class_weighted_rerun") / "results.csv"
    s3_results = pd.read_csv(s3_results_path) if s3_results_path.exists() else pd.DataFrame()

    device = get_device()
    result_rows: list[dict[str, Any]] = []
    delta_rows_original: list[dict[str, Any]] = []
    delta_rows_s3: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    for dataset_name in ("DAPT2020", "Unraveled"):
        summary[dataset_name] = {"trained_models": [], "skipped_models": []}
        for model_name in rerun_target_models(dataset_name):
            train_graphs, val_graphs, test_graphs = get_graph_splits(dataset_name, model_name)
            if not train_graphs or not val_graphs or not test_graphs:
                summary[dataset_name]["skipped_models"].append(display_name(dataset_name, model_name))
                continue
            try:
                smote_graphs, smote_summary = smote_feature_pool_graphs(train_graphs, CONFIG["random_seed"])
            except Exception as exc:
                summary[dataset_name]["skipped_models"].append(f"{display_name(dataset_name, model_name)} ({exc})")
                continue

            params = training_params_for_model(dataset_name, model_name)
            model = instantiate_unraveled_model(model_name, params) if dataset_name == "Unraveled" else instantiate_dapt_model(model_name, params)
            criterion = nn.CrossEntropyLoss()
            model, _, history = train_graph_model_custom_loss(
                model=model,
                train_graphs=smote_graphs,
                val_graphs=val_graphs,
                device=device,
                lr=float(params["lr"]),
                weight_decay=float(params["weight_decay"]),
                batch_size=int(params["batch_size"]),
                epochs=int(params["epochs"]),
                patience=int(params["patience"]),
                criterion=criterion,
            )
            predictions = predict_graph_model(model, test_graphs, device=device, batch_size=int(params["batch_size"]))
            metrics = predictions_to_metrics(predictions)
            result_rows.append(wide_metric_row(dataset_name, model_name, metrics))
            delta_rows_original.append(
                delta_row(
                    dataset_name=dataset_name,
                    model_name=model_name,
                    new_metrics=metrics,
                    reference_metrics=known_runtime_metrics(dataset_name, model_name),
                    reference_label="original",
                )
            )
            if not s3_results.empty:
                match = s3_results[
                    (s3_results["dataset"] == dataset_name)
                    & (s3_results["model"] == display_name(dataset_name, model_name))
                ]
                if not match.empty:
                    delta_rows_s3.append(
                        delta_row(
                            dataset_name=dataset_name,
                            model_name=model_name,
                            new_metrics=metrics,
                            reference_metrics=wide_row_to_runtime_metrics(dataset_name, match.iloc[0]),
                            reference_label="S3",
                        )
                    )
            save_json(
                out_dir / f"{dataset_name}_{file_slug(model_name)}.json",
                {
                    "dataset": dataset_name,
                    "model": model_name,
                    "metrics": metrics,
                    "history": history,
                    "smote_summary": smote_summary,
                },
            )
            summary[dataset_name]["trained_models"].append(display_name(dataset_name, model_name))

    results_frame = pd.DataFrame(result_rows)
    delta_original_frame = pd.DataFrame(delta_rows_original)
    delta_s3_frame = pd.DataFrame(delta_rows_s3)
    save_dataframe(out_dir / "results.csv", results_frame if not results_frame.empty else pd.DataFrame(columns=["dataset", "model"]))
    save_dataframe(out_dir / "delta_vs_original.csv", delta_original_frame if not delta_original_frame.empty else pd.DataFrame(columns=["dataset", "model", "reference"]))
    save_dataframe(out_dir / "delta_vs_s3.csv", delta_s3_frame if not delta_s3_frame.empty else pd.DataFrame(columns=["dataset", "model", "reference"]))
    if not delta_original_frame.empty:
        print("\nS4 delta vs original")
        print(render_table(delta_original_frame))
    if not delta_s3_frame.empty:
        print("\nS4 delta vs S3")
        print(render_table(delta_s3_frame))
    finish_section(section_name, out_dir, summary)


def run_s5_homophily_analysis() -> None:
    section_name = "S5_homophily_analysis"
    out_dir, should_skip = start_section(section_name, ["homophily.csv", "DAPT2020_heatmap.png", "Unraveled_heatmap.png"])
    if should_skip:
        return
    require_plotting()

    rows: list[pd.DataFrame] = []
    summary: dict[str, Any] = {}

    for dataset_name in ("DAPT2020", "Unraveled"):
        context = get_context(dataset_name)
        full_frame = concat_context_frames(context)
        if dataset_name == "Unraveled":
            graphs = build_unraveled_graphs_with_row_ids(full_frame, "GCN-DGI")
        else:
            graphs = build_dapt_graphs_with_row_ids(full_frame, "GCN-DGI")
        overall_h, per_class_frame, label_matrix = graph_homophily_statistics(graphs)
        per_class_frame["dataset"] = dataset_name
        rows.append(per_class_frame)
        plot_edge_label_heatmap(dataset_name, label_matrix, out_dir / f"{dataset_name}_heatmap.png")
        print(f"\n{dataset_name} overall homophily: {overall_h:.4f}")
        print(render_table(per_class_frame[["dataset", "model", "class_name", "incident_edges", "homophily"]]))
        if overall_h < 0.3:
            print(f"  {dataset_name}: graph structure is likely harmful to GNNs (h < 0.3).")
        summary[dataset_name] = {
            "overall_homophily": overall_h,
            "likely_harmful_to_gnns": bool(overall_h < 0.3),
        }

    homophily_frame = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["dataset", "model"])
    save_dataframe(out_dir / "homophily.csv", homophily_frame)
    finish_section(section_name, out_dir, summary)


def run_s6_mlp_feature_importance() -> None:
    section_name = "S6_mlp_feature_importance"
    out_dir, should_skip = start_section(section_name, ["feature_importance.csv", "top30_features.png"])
    if should_skip:
        return
    require_plotting()

    checkpoint = find_checkpoint("Unraveled", "MLP")
    if checkpoint is None:
        skip_section(section_name, "Missing Unraveled MLP checkpoint in CONFIG['unraveled_checkpoint_dir'].")
        return

    context = get_unraveled_context()
    device = get_device()
    model = load_state_into_model(instantiate_unraveled_model("MLP", get_unraveled_best_params("MLP")), checkpoint)

    baseline_predictions = predict_row_model(model, context.test_df, context.feature_cols, device)
    baseline_metrics = predictions_to_metrics(baseline_predictions)
    x_test = context.test_df[context.feature_cols].to_numpy(dtype=np.float32)
    rng = np.random.default_rng(CONFIG["random_seed"])
    importances: list[dict[str, Any]] = []

    for feature_index, feature_name in enumerate(context.feature_cols):
        x_perm = x_test.copy()
        x_perm[:, feature_index] = rng.permutation(x_perm[:, feature_index])
        perm_frame = context.test_df.copy()
        perm_frame.loc[:, context.feature_cols] = x_perm
        perm_predictions = predict_row_model(model, perm_frame, context.feature_cols, device)
        perm_metrics = predictions_to_metrics(perm_predictions)
        importance = float(baseline_metrics["macro_f1"] - perm_metrics["macro_f1"])
        importances.append(
            {
                "dataset": "Unraveled",
                "model": "MLP",
                "feature": feature_name,
                "importance": importance,
            }
        )

    importance_frame = pd.DataFrame(importances).sort_values("importance", ascending=False).reset_index(drop=True)
    save_dataframe(out_dir / "feature_importance.csv", importance_frame)

    top30 = importance_frame.head(30).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.barh(top30["feature"], top30["importance"], color=ACCENT)
    ax.set_title("Unraveled MLP Permutation Importance (Top 30)")
    ax.set_xlabel("Macro F1 drop after permutation")
    fig.tight_layout()
    fig.savefig(out_dir / "top30_features.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    positive_total = float(importance_frame["importance"].clip(lower=0.0).sum())
    top10_total = float(importance_frame.head(10)["importance"].clip(lower=0.0).sum())
    top10_pct = float(top10_total / positive_total) if positive_total > 0 else 0.0
    structural_keywords = ("degree", "cluster", "clustering", "pagerank", "central", "triangle", "betweenness", "neighbor")
    overlapping = [
        feature
        for feature in importance_frame.head(30)["feature"].tolist()
        if any(keyword in feature.lower() for keyword in structural_keywords)
    ]
    print(f"[S6] Top 10 features capture {top10_pct * 100:.2f}% of positive permutation importance.")
    if overlapping:
        print(f"[S6] Structural-feature overlap detected: {', '.join(overlapping[:10])}")
    else:
        print("[S6] No obvious graph-structural feature overlap found in the top 30 features.")

    finish_section(
        section_name,
        out_dir,
        {
            "baseline_macro_f1": baseline_metrics["macro_f1"],
            "top10_positive_importance_pct": top10_pct,
            "top_structural_overlap_count": len(overlapping),
        },
    )


def run_s7_embedding_umap() -> None:
    section_name = "S7_embedding_umap"
    out_dir, should_skip = start_section(section_name, ["silhouette_scores.csv"])
    if should_skip:
        return
    require_plotting()
    if umap is None:
        skip_section(section_name, "umap-learn is not installed.")
        return

    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    tasks = [
        ("DAPT2020", "GCN-DGI"),
        ("Unraveled", "MLP"),
        ("Unraveled", "Mamba"),
        ("Unraveled", "GCN-DGI"),
    ]

    for dataset_name, model_name in tasks:
        checkpoint = find_checkpoint(dataset_name, model_name)
        if checkpoint is None:
            summary[f"{dataset_name}:{model_name}"] = "missing_checkpoint"
            continue

        context = get_context(dataset_name)
        device = get_device()
        model = get_model_for_inference(dataset_name, model_name)
        if model is None:
            summary[f"{dataset_name}:{model_name}"] = "load_failed"
            continue

        embeddings: np.ndarray
        labels: np.ndarray
        if model_name == "MLP":
            x = torch.from_numpy(context.test_df[context.feature_cols].to_numpy(dtype=np.float32)).to(device)
            with torch.no_grad():
                embeddings = extract_mlp_penultimate(model.to(device), x).cpu().numpy()
            labels = context.test_df["MultiLabel"].to_numpy(dtype=np.int64)
        elif model_name == "Mamba":
            preds = predict_sequence_model(model, context.test_df, context.feature_cols, context.settings, device)
            labels = preds["true_label_id"].to_numpy(dtype=np.int64)
            chunks = build_sequence_chunks_with_ids(
                context.test_df,
                context.feature_cols,
                int(context.settings.get("sequence_length", 512)),
                int(context.settings.get("min_sequence_length", 64)),
            )
            loader = DataLoader(
                chunks,
                batch_size=int(context.settings.get("sequence_batch_size", 8)),
                shuffle=False,
                collate_fn=collate_sequence_chunks_with_ids,
            )
            embed_rows: list[np.ndarray] = []
            with torch.no_grad():
                for xs, _, mask, _ in loader:
                    xs = xs.to(device)
                    mask = mask.to(device)
                    hidden = extract_mamba_penultimate(model.to(device), xs)
                    flat_hidden = hidden.view(-1, hidden.shape[-1])[mask.view(-1)]
                    embed_rows.append(flat_hidden.cpu().numpy())
            embeddings = np.vstack(embed_rows)
        else:
            _, _, test_graphs = get_graph_splits(dataset_name, model_name)
            loader = GraphDataLoader(test_graphs, batch_size=int(context.settings.get("graph_batch_size", 4)), shuffle=False)
            embed_rows = []
            label_rows = []
            with torch.no_grad():
                for batch in loader:
                    batch = batch.to(device)
                    node_embeddings = extract_gcndgi_embeddings(model.to(device), batch)
                    embed_rows.append(node_embeddings.cpu().numpy())
                    label_rows.append(batch.y.cpu().numpy())
            embeddings = np.vstack(embed_rows)
            labels = np.concatenate(label_rows)

        reducer = umap.UMAP(n_components=2, random_state=CONFIG["random_seed"])
        coords = reducer.fit_transform(embeddings)
        silhouette = silhouette_samples(coords, labels) if len(np.unique(labels)) > 1 else np.zeros(len(labels))

        fig, ax = plt.subplots(figsize=(7, 6))
        for class_id, stage_name in enumerate(STAGE_NAMES):
            mask = labels == class_id
            if not np.any(mask):
                continue
            ax.scatter(coords[mask, 0], coords[mask, 1], s=8, alpha=0.55, label=stage_name)
            rows.append(
                {
                    "dataset": dataset_name,
                    "model": display_name(dataset_name, model_name),
                    "class_name": stage_name,
                    "mean_silhouette": float(np.mean(silhouette[mask])),
                }
            )
        ax.set_title(f"{dataset_name} {display_name(dataset_name, model_name)} UMAP")
        ax.legend(fontsize=8, loc="best")
        fig.tight_layout()
        fig.savefig(out_dir / f"{dataset_name}_{file_slug(model_name)}_umap.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

        de_mask = labels == 4
        lm_mask = labels == 3
        de_score = float(np.mean(silhouette[de_mask])) if np.any(de_mask) else float("nan")
        lm_score = float(np.mean(silhouette[lm_mask])) if np.any(lm_mask) else float("nan")
        print(
            f"[S7] {dataset_name} {display_name(dataset_name, model_name)} "
            f"DE silhouette={de_score:.4f} | LM silhouette={lm_score:.4f}"
        )
        print(
            "      Interpretation: "
            + (
                "DE/LM look mixed with other classes."
                if max(de_score if not math.isnan(de_score) else -1.0, lm_score if not math.isnan(lm_score) else -1.0) < 0.05
                else "DE/LM show at least partial separation."
            )
        )
        summary[f"{dataset_name}:{model_name}"] = "ran"

    silhouette_frame = pd.DataFrame(rows)
    save_dataframe(out_dir / "silhouette_scores.csv", silhouette_frame if not silhouette_frame.empty else pd.DataFrame(columns=["dataset", "model"]))
    finish_section(section_name, out_dir, summary)


def run_s8_mamba_prediction_audit() -> None:
    section_name = "S8_mamba_prediction_audit"
    out_dir, should_skip = start_section(section_name, ["mamba_predictions.csv"])
    if should_skip:
        return

    checkpoint = find_checkpoint("Unraveled", "Mamba")
    if checkpoint is None:
        skip_section(section_name, "Missing Unraveled Mamba checkpoint in CONFIG['unraveled_checkpoint_dir'].")
        return

    context = get_unraveled_context()
    device = get_device()
    model = get_model_for_inference("Unraveled", "Mamba")
    if model is None:
        skip_section(section_name, "Failed to load the Unraveled Mamba checkpoint.")
        return

    predictions = add_label_names(
        predict_sequence_model(model, context.test_df, context.feature_cols, context.settings, device)
    )
    predictions["dataset"] = "Unraveled"
    predictions["model"] = "Mamba"
    save_dataframe(
        out_dir / "mamba_predictions.csv",
        predictions[["dataset", "model", "true_label", "predicted_label", "max_softmax_prob", "diag_row_id"]],
    )

    low_f1_classes = [
        ("Data Exfiltration", KNOWN_RESULTS["Unraveled"]["Mamba"]["de_f1"]),
        ("Lateral Movement", KNOWN_RESULTS["Unraveled"]["Mamba"]["lm_f1"]),
        ("Reconnaissance", KNOWN_RESULTS["Unraveled"]["Mamba"]["recon_f1"]),
        ("Establish Foothold", KNOWN_RESULTS["Unraveled"]["Mamba"]["foothold_f1"]),
        ("Benign", KNOWN_RESULTS["Unraveled"]["Mamba"]["benign_f1"]),
    ]
    low_f1_classes = [item for item in low_f1_classes if item[1] < 0.1]

    summary: dict[str, Any] = {}
    for class_name, _ in low_f1_classes:
        true_mask = predictions["true_label"] == class_name
        predicted_mask = predictions["predicted_label"] == class_name
        predicted_as_other = predictions.loc[true_mask & ~predicted_mask, "predicted_label"].value_counts().to_dict()
        print(
            f"[S8] {class_name}: true_count={int(true_mask.sum())} "
            f"predicted_count={int(predicted_mask.sum())} reassigned_to={predicted_as_other}"
        )
        summary[class_name] = {
            "true_count": int(true_mask.sum()),
            "predicted_count": int(predicted_mask.sum()),
            "reassigned_to": predicted_as_other,
        }

    finish_section(section_name, out_dir, summary)


def run_s9_focal_loss_mamba() -> None:
    section_name = "S9_focal_loss_mamba"
    out_dir, should_skip = start_section(section_name, ["results.csv", "delta_vs_original.csv"])
    if should_skip:
        return

    context = get_unraveled_context()
    device = get_device()
    params = get_unraveled_best_params("Mamba")
    params.setdefault("lr", 6e-4)
    params.setdefault("weight_decay", 1e-4)

    train_chunks = v02.build_sequence_chunks(
        context.train_df,
        context.feature_cols,
        sequence_length=int(context.settings.get("sequence_length", 512)),
        min_sequence_length=int(context.settings.get("min_sequence_length", 64)),
    )
    val_chunks = v02.build_sequence_chunks(
        context.val_df,
        context.feature_cols,
        sequence_length=int(context.settings.get("sequence_length", 512)),
        min_sequence_length=int(context.settings.get("min_sequence_length", 64)),
    )
    test_chunks = v02.build_sequence_chunks(
        context.test_df,
        context.feature_cols,
        sequence_length=int(context.settings.get("sequence_length", 512)),
        min_sequence_length=int(context.settings.get("min_sequence_length", 64)),
    )

    train_loader = DataLoader(
        train_chunks,
        batch_size=int(context.settings.get("sequence_batch_size", 8)),
        shuffle=True,
        collate_fn=v02.collate_sequence_chunks,
    )
    val_loader = DataLoader(
        val_chunks,
        batch_size=int(context.settings.get("sequence_batch_size", 8)),
        shuffle=False,
        collate_fn=v02.collate_sequence_chunks,
    )
    test_loader = DataLoader(
        test_chunks,
        batch_size=int(context.settings.get("sequence_batch_size", 8)),
        shuffle=False,
        collate_fn=v02.collate_sequence_chunks,
    )

    model = instantiate_unraveled_model("Mamba", params)
    alpha = mamba_alpha_from_labels(context.train_df["MultiLabel"].to_numpy(dtype=np.int64))
    criterion = FocalLoss(alpha=alpha, gamma=2.0, ignore_index=-100)
    model, _, history = train_sequence_model_custom_loss(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        lr=float(params["lr"]),
        weight_decay=float(params["weight_decay"]),
        epochs=int(context.settings.get("train_epochs", 12)),
        patience=int(context.settings.get("early_stopping_patience", 6)),
        criterion=criterion,
    )
    test_predictions = evaluate_sequence_model_probabilities(model, test_loader, device)
    metrics = compute_multiclass_metrics(
        test_predictions["y_true"],
        test_predictions["y_pred"],
        test_predictions["y_prob"],
    )
    results_frame = pd.DataFrame([wide_metric_row("Unraveled", "Mamba", metrics)])
    delta_frame = pd.DataFrame(
        [
            delta_row(
                dataset_name="Unraveled",
                model_name="Mamba",
                new_metrics=metrics,
                reference_metrics=known_runtime_metrics("Unraveled", "Mamba"),
                reference_label="original",
            )
        ]
    )
    save_dataframe(out_dir / "results.csv", results_frame)
    save_dataframe(out_dir / "delta_vs_original.csv", delta_frame)
    save_json(out_dir / "mamba_focal.json", {"metrics": metrics, "history": history})
    torch.save(model.state_dict(), out_dir / "mamba_focal.pt")
    print(render_table(delta_frame))
    if metrics["per_class_f1"]["Data Exfiltration"] - KNOWN_RESULTS["Unraveled"]["Mamba"]["de_f1"] > 0.1:
        print("[S9] significant improvement")
    finish_section(
        section_name,
        out_dir,
        {
            "macro_f1": metrics["macro_f1"],
            "de_f1": metrics["per_class_f1"]["Data Exfiltration"],
            "significant_improvement": bool(
                metrics["per_class_f1"]["Data Exfiltration"] - KNOWN_RESULTS["Unraveled"]["Mamba"]["de_f1"] > 0.1
            ),
        },
    )


def run_s10_xgboost_rf_baseline() -> None:
    section_name = "S10_xgboost_rf_baseline"
    out_dir, should_skip = start_section(section_name, ["baseline_results.csv", "comparison_table.csv"])
    if should_skip:
        return

    result_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    for dataset_name in ("DAPT2020", "Unraveled"):
        context = get_context(dataset_name)
        x_train = context.train_df[context.feature_cols].to_numpy(dtype=np.float32)
        y_train = context.train_df["MultiLabel"].to_numpy(dtype=np.int64)
        x_test = context.test_df[context.feature_cols].to_numpy(dtype=np.float32)
        y_test = context.test_df["MultiLabel"].to_numpy(dtype=np.int64)

        models: list[tuple[str, Any]] = [
            (
                "RandomForest",
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=None,
                    class_weight="balanced_subsample",
                    random_state=CONFIG["random_seed"],
                    n_jobs=-1,
                ),
            )
        ]
        if XGBClassifier is not None:
            models.append(
                (
                    "XGBoost",
                    XGBClassifier(
                        objective="multi:softprob",
                        num_class=len(STAGE_NAMES),
                        eval_metric="mlogloss",
                        n_estimators=300,
                        learning_rate=0.05,
                        max_depth=6,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        random_state=CONFIG["random_seed"],
                        tree_method="hist",
                    ),
                )
            )

        dataset_summary = {"trained": []}
        for model_name, estimator in models:
            estimator.fit(x_train, y_train)
            probs = estimator.predict_proba(x_test)
            preds = np.argmax(probs, axis=1)
            metrics = compute_multiclass_metrics(y_true=y_test, y_pred=preds, y_prob=probs)
            result_rows.append(wide_metric_row(dataset_name, model_name, metrics))
            dataset_summary["trained"].append(model_name)

        baseline_models = ["GCN-DGI"] + (["MLP"] if dataset_name == "Unraveled" else [])
        for baseline_model in baseline_models:
            comparison_rows.append(
                {
                    "dataset": dataset_name,
                    "model": display_name(dataset_name, baseline_model),
                    **known_results_frame(dataset_name)
                    .set_index("model")
                    .loc[display_name(dataset_name, baseline_model)]
                    .drop(labels=["dataset"])
                    .to_dict(),
                }
            )
        for row in result_rows:
            if row["dataset"] == dataset_name:
                comparison_rows.append(row)

        if dataset_name == "Unraveled":
            mlp_macro = KNOWN_RESULTS["Unraveled"]["MLP"]["macro_f1"]
            best_tree = max((row["Macro F1"] for row in result_rows if row["dataset"] == "Unraveled"), default=-1.0)
            if best_tree > mlp_macro:
                print(
                    "⚠ Tree model outperforms MLP — revisit feature engineering before investing further in deep models"
                )
        summary[dataset_name] = dataset_summary

    baseline_frame = pd.DataFrame(result_rows)
    comparison_frame = pd.DataFrame(comparison_rows)
    save_dataframe(out_dir / "baseline_results.csv", baseline_frame if not baseline_frame.empty else pd.DataFrame(columns=["dataset", "model"]))
    save_dataframe(out_dir / "comparison_table.csv", comparison_frame if not comparison_frame.empty else pd.DataFrame(columns=["dataset", "model"]))
    if not comparison_frame.empty:
        print(render_table(comparison_frame))
    finish_section(section_name, out_dir, summary)


def run_s11_mlp_gcndgi_ensemble() -> None:
    section_name = "S11_mlp_gcndgi_ensemble"
    out_dir, should_skip = start_section(section_name, ["ensemble_results.csv", "delta_vs_mlp.csv", "delta_vs_gcndgi.csv"])
    if should_skip:
        return

    mlp_checkpoint = find_checkpoint("Unraveled", "MLP")
    gcn_checkpoint = find_checkpoint("Unraveled", "GCN-DGI")
    if mlp_checkpoint is None or gcn_checkpoint is None:
        skip_section(section_name, "Missing MLP or GCN-DGI checkpoint in CONFIG['unraveled_checkpoint_dir'].")
        return

    context = get_unraveled_context()
    device = get_device()
    mlp_model = get_model_for_inference("Unraveled", "MLP")
    gcn_model = get_model_for_inference("Unraveled", "GCN-DGI")
    if mlp_model is None or gcn_model is None:
        skip_section(section_name, "Failed to load ensemble checkpoints.")
        return

    mlp_val = predict_row_model(mlp_model, context.val_df, context.feature_cols, device)
    mlp_test = predict_row_model(mlp_model, context.test_df, context.feature_cols, device)
    _, val_graphs, test_graphs = get_graph_splits("Unraveled", "GCN-DGI")
    gcn_val = predict_graph_model(gcn_model, val_graphs, device=device, batch_size=int(context.settings.get("graph_batch_size", 4)))
    gcn_test = predict_graph_model(gcn_model, test_graphs, device=device, batch_size=int(context.settings.get("graph_batch_size", 4)))

    def merge_probs(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        merged = left.merge(right, on="diag_row_id", suffixes=("_mlp", "_gcn"))
        merged = merged[merged["true_label_id_mlp"] == merged["true_label_id_gcn"]].copy()
        merged["true_label_id"] = merged["true_label_id_mlp"]
        return merged

    val_merged = merge_probs(mlp_val, gcn_val)
    test_merged = merge_probs(mlp_test, gcn_test)
    class_cols = [f"prob_{stage_name}" for stage_name in STAGE_NAMES]

    ensemble_results: list[dict[str, Any]] = []
    delta_vs_mlp: list[dict[str, Any]] = []
    delta_vs_gcn: list[dict[str, Any]] = []

    soft_probs = np.stack(
        [
            (test_merged[f"{col}_mlp"].to_numpy(dtype=np.float32) + test_merged[f"{col}_gcn"].to_numpy(dtype=np.float32)) / 2.0
            for col in class_cols
        ],
        axis=1,
    )
    soft_metrics = compute_multiclass_metrics(
        y_true=test_merged["true_label_id"].to_numpy(dtype=np.int64),
        y_pred=soft_probs.argmax(axis=1),
        y_prob=soft_probs,
    )
    ensemble_results.append(wide_metric_row("Unraveled", "Soft Voting", soft_metrics))
    delta_vs_mlp.append(delta_row("Unraveled", "Soft Voting", soft_metrics, known_runtime_metrics("Unraveled", "MLP"), "MLP"))
    delta_vs_gcn.append(delta_row("Unraveled", "Soft Voting", soft_metrics, known_runtime_metrics("Unraveled", "GCN-DGI"), "GCN-DGI"))

    weights_mlp = np.asarray(
        [
            KNOWN_RESULTS["Unraveled"]["MLP"]["benign_f1"],
            KNOWN_RESULTS["Unraveled"]["MLP"]["recon_f1"],
            KNOWN_RESULTS["Unraveled"]["MLP"]["foothold_f1"],
            KNOWN_RESULTS["Unraveled"]["MLP"]["lm_f1"],
            KNOWN_RESULTS["Unraveled"]["MLP"]["de_f1"],
        ],
        dtype=np.float32,
    )
    weights_gcn = np.asarray(
        [
            KNOWN_RESULTS["Unraveled"]["GCN-DGI"]["benign_f1"],
            KNOWN_RESULTS["Unraveled"]["GCN-DGI"]["recon_f1"],
            KNOWN_RESULTS["Unraveled"]["GCN-DGI"]["foothold_f1"],
            KNOWN_RESULTS["Unraveled"]["GCN-DGI"]["lm_f1"],
            KNOWN_RESULTS["Unraveled"]["GCN-DGI"]["de_f1"],
        ],
        dtype=np.float32,
    )
    weighted_probs = []
    for index, col in enumerate(class_cols):
        denom = max(weights_mlp[index] + weights_gcn[index], 1e-8)
        weighted_probs.append(
            (
                weights_mlp[index] * test_merged[f"{col}_mlp"].to_numpy(dtype=np.float32)
                + weights_gcn[index] * test_merged[f"{col}_gcn"].to_numpy(dtype=np.float32)
            )
            / denom
        )
    weighted_probs = np.stack(weighted_probs, axis=1)
    weighted_metrics = compute_multiclass_metrics(
        y_true=test_merged["true_label_id"].to_numpy(dtype=np.int64),
        y_pred=weighted_probs.argmax(axis=1),
        y_prob=weighted_probs,
    )
    ensemble_results.append(wide_metric_row("Unraveled", "Weighted Ensemble", weighted_metrics))
    delta_vs_mlp.append(delta_row("Unraveled", "Weighted Ensemble", weighted_metrics, known_runtime_metrics("Unraveled", "MLP"), "MLP"))
    delta_vs_gcn.append(delta_row("Unraveled", "Weighted Ensemble", weighted_metrics, known_runtime_metrics("Unraveled", "GCN-DGI"), "GCN-DGI"))

    val_features = np.concatenate(
        [
            val_merged[[f"{col}_mlp" for col in class_cols]].to_numpy(dtype=np.float32),
            val_merged[[f"{col}_gcn" for col in class_cols]].to_numpy(dtype=np.float32),
        ],
        axis=1,
    )
    test_features = np.concatenate(
        [
            test_merged[[f"{col}_mlp" for col in class_cols]].to_numpy(dtype=np.float32),
            test_merged[[f"{col}_gcn" for col in class_cols]].to_numpy(dtype=np.float32),
        ],
        axis=1,
    )
    meta = LogisticRegression(max_iter=2000, random_state=CONFIG["random_seed"])
    meta.fit(val_features, val_merged["true_label_id"].to_numpy(dtype=np.int64))
    stacked_probs = meta.predict_proba(test_features)
    stacked_metrics = compute_multiclass_metrics(
        y_true=test_merged["true_label_id"].to_numpy(dtype=np.int64),
        y_pred=stacked_probs.argmax(axis=1),
        y_prob=stacked_probs,
    )
    ensemble_results.append(wide_metric_row("Unraveled", "Stacked Ensemble", stacked_metrics))
    delta_vs_mlp.append(delta_row("Unraveled", "Stacked Ensemble", stacked_metrics, known_runtime_metrics("Unraveled", "MLP"), "MLP"))
    delta_vs_gcn.append(delta_row("Unraveled", "Stacked Ensemble", stacked_metrics, known_runtime_metrics("Unraveled", "GCN-DGI"), "GCN-DGI"))

    results_frame = pd.DataFrame(ensemble_results)
    delta_mlp_frame = pd.DataFrame(delta_vs_mlp)
    delta_gcn_frame = pd.DataFrame(delta_vs_gcn)
    save_dataframe(out_dir / "ensemble_results.csv", results_frame)
    save_dataframe(out_dir / "delta_vs_mlp.csv", delta_mlp_frame)
    save_dataframe(out_dir / "delta_vs_gcndgi.csv", delta_gcn_frame)
    print(render_table(results_frame))
    finish_section(section_name, out_dir, {"strategies": results_frame["model"].tolist()})


def print_completion_summary() -> None:
    rows = []
    for section_name in SECTION_ORDER:
        rows.append(
            {
                "section": section_name,
                "status": SECTION_STATUS.get(section_name, "off"),
            }
        )
    frame = pd.DataFrame(rows)
    print("\nCOMPLETION SUMMARY")
    print(render_table(frame, floatfmt=".0f"))


def main() -> None:
    configure_plot_theme()
    set_global_seed(int(CONFIG["random_seed"]))

    section_functions = {
        "S0_display_known_results": run_s0_display_known_results,
        "S1_class_distribution": run_s1_class_distribution,
        "S2_confusion_matrices": run_s2_confusion_matrices,
        "S3_class_weighted_rerun": run_s3_class_weighted_rerun,
        "S4_smote_rerun": run_s4_smote_rerun,
        "S5_homophily_analysis": run_s5_homophily_analysis,
        "S6_mlp_feature_importance": run_s6_mlp_feature_importance,
        "S7_embedding_umap": run_s7_embedding_umap,
        "S8_mamba_prediction_audit": run_s8_mamba_prediction_audit,
        "S9_focal_loss_mamba": run_s9_focal_loss_mamba,
        "S10_xgboost_rf_baseline": run_s10_xgboost_rf_baseline,
        "S11_mlp_gcndgi_ensemble": run_s11_mlp_gcndgi_ensemble,
    }

    for section_name in SECTION_ORDER:
        if not RUN_SECTION.get(section_name, False):
            SECTION_STATUS[section_name] = "off"
            continue
        try:
            section_functions[section_name]()
        except SectionSkip as exc:
            skip_section(section_name, str(exc))
        except Exception as exc:
            SECTION_STATUS[section_name] = f"failed: {exc}"
            print(f"[{section_name}] Failed: {exc}")

    print_completion_summary()


if __name__ == "__main__":
    main()
