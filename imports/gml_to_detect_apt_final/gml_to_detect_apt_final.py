# Imported from GML To Detect APT Final.zip
# Notebook outputs were removed during import.
# Notebook shell commands were converted into comments for script safety.

# Multi-Classification Evaluations Models: GATv2, R-GCN, ST-GCN, GIN, GCN-DGI

# -*- coding: utf-8 -*-
# Install required packages (uncomment when needed)
# NOTEBOOK COMMAND: !pip install pandas numpy matplotlib seaborn scikit-learn -q
# NOTEBOOK COMMAND: !pip install torch-geometric==2.4.0 -q
# NOTEBOOK COMMAND: !pip install optuna optuna-dashboard -q
# NOTEBOOK COMMAND: !pip install kaleido -q


import os
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
import json
import random
from collections import defaultdict, Counter
warnings.filterwarnings('ignore')

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import optuna
from optuna.visualization import plot_optimization_history, plot_param_importances


import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import GCNConv, GATConv, GATv2Conv, GINConv, RGCNConv

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.neighbors import NearestNeighbors
from sklearn.manifold import TSNE

# Try to import networkx for graph visualizations
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("âš  NetworkX not available - install with: !pip install networkx")

print("âœ“ Imports complete!")

# ========================================
# GLOBAL RANDOM SEED
# ========================================

GLOBAL_SEED = 42

def set_global_seeds(seed: int = GLOBAL_SEED) -> None:
    """
    Fix all sources of randomness so that results are reproducible
    across notebook runs.  Call this once at startup and again inside
    any function that re-initialises models or data loaders.

    Covers:
      â€¢ Python built-in random
      â€¢ NumPy
      â€¢ PyTorch (CPU and CUDA)
      â€¢ CuDNN determinism flag
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)          # multi-GPU safety
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark     = False
    print(f"âœ“ Global seeds set to {seed}")

# ========================================
# MOUNT GOOGLE DRIVE & LOCAL DATA PATHS
# ========================================

# Mount Google Drive
try:
    from google.colab import drive
    drive.mount('/content/drive')
    print("âœ“ Google Drive mounted")
    IS_COLAB = True

    # Create results directory in Drive
    import os
    results_dir = '/content/drive/My Drive/DAPT2020_Results'
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(f'{results_dir}/edge_similarity_analysis', exist_ok=True)
    print(f"Results directory created: {results_dir}")

except:
    print("Not running in Colab - skipping Drive mount")
    IS_COLAB = False

DRIVE_BASE = '/content/drive/My Drive/DAPT2020_Results'
REPO_ROOT = Path(__file__).resolve().parents[2] if '__file__' in globals() else Path.cwd()
LOCAL_RUN_OUTPUT_DIR = Path(
    os.getenv(
        'DAPT2020_LOCAL_OUTPUT_DIR',
        str(REPO_ROOT / 'runs' / 'dapt2020-local-fast'),
    )
)
LOCAL_RUN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    return float(value)


DEFAULT_EXECUTION_PROFILE = os.getenv(
    'DAPT2020_EXECUTION_PROFILE',
    'full' if IS_COLAB else 'local-fast',
).strip().lower()

PROFILE_DEFAULTS = {
    'full': {
        'max_files': None,
        'sample_rate': 1.0,
        'flows_per_graph': 1000,
        'batch_size': 4,
        'n_blocks': 10,
        'train_epochs': 50,
        'dgi_pretrain_epochs': 50,
        'run_dgi_pretraining': True,
        'run_optuna_optimization': True,
        'optuna_trials': 100,
        'fresh_study': True,
    },
    'local-fast': {
        'max_files': None,
        'sample_rate': 1.0,
        'flows_per_graph': 1000,
        'batch_size': 4,
        'n_blocks': 10,
        'train_epochs': 5,
        'dgi_pretrain_epochs': 5,
        'run_dgi_pretraining': True,
        'run_optuna_optimization': True,
        'optuna_trials': 1,
        'fresh_study': True,
    },
}


def resolve_runtime_profile(max_files=None, sample_rate=None) -> dict:
    profile_name = DEFAULT_EXECUTION_PROFILE
    defaults = PROFILE_DEFAULTS.get(profile_name, PROFILE_DEFAULTS['local-fast']).copy()

    defaults['profile'] = profile_name
    defaults['max_files'] = max_files if max_files is not None else defaults['max_files']
    defaults['sample_rate'] = sample_rate if sample_rate is not None else defaults['sample_rate']
    defaults['flows_per_graph'] = env_int(
        'DAPT2020_FLOWS_PER_GRAPH', defaults['flows_per_graph']
    )
    defaults['batch_size'] = env_int(
        'DAPT2020_BATCH_SIZE', defaults['batch_size']
    )
    defaults['n_blocks'] = env_int(
        'DAPT2020_N_BLOCKS', defaults['n_blocks']
    )
    defaults['train_epochs'] = env_int(
        'DAPT2020_TRAIN_EPOCHS', defaults['train_epochs']
    )
    defaults['dgi_pretrain_epochs'] = env_int(
        'DAPT2020_DGI_PRETRAIN_EPOCHS', defaults['dgi_pretrain_epochs']
    )
    defaults['run_dgi_pretraining'] = env_flag(
        'DAPT2020_RUN_DGI_PRETRAINING', defaults['run_dgi_pretraining']
    )
    defaults['run_optuna_optimization'] = env_flag(
        'DAPT2020_RUN_OPTUNA', defaults['run_optuna_optimization']
    )
    defaults['optuna_trials'] = env_int(
        'DAPT2020_OPTUNA_TRIALS', defaults['optuna_trials']
    )
    defaults['fresh_study'] = env_flag(
        'DAPT2020_FRESH_STUDY', defaults['fresh_study']
    )
    return defaults


def colab_path(relative: str) -> str:
    if IS_COLAB:
        full = Path(DRIVE_BASE) / relative
    else:
        full = LOCAL_RUN_OUTPUT_DIR / relative
    full.parent.mkdir(parents=True, exist_ok=True)
    return str(full)

LOCAL_DATA_DIR = Path(
    os.getenv('DAPT2020_LOCAL_DATA_DIR', str(REPO_ROOT / 'data' / 'raw' / 'dapt2020'))
)
LOCAL_PROCESSED_DIR = Path(
    os.getenv('DAPT2020_LOCAL_PROCESSED_DIR', str(REPO_ROOT / 'data' / 'processed' / 'dapt2020'))
)
LOCAL_CONSOLIDATED_CSV = Path(
    os.getenv(
        'DAPT2020_LOCAL_CONSOLIDATED_CSV',
        str(LOCAL_PROCESSED_DIR / 'combined_flows.csv'),
    )
)

KNOWN_DAPT2020_FILES = [
    'enp0s3-monday.pcap_Flow.csv',
    'enp0s3-public-tuesday.pcap_Flow.csv',
    'enp0s3-public-wednesday.pcap_Flow.csv',
    'enp0s3-public-thursday.pcap_Flow.csv',
    'enp0s3-tcpdump-friday.pcap_Flow.csv',
    'enp0s3-monday-pvt.pcap_Flow.csv',
    'enp0s3-pvt-tuesday.pcap_Flow.csv',
    'enp0s3-pvt-wednesday.pcap_Flow.csv',
    'enp0s3-pvt-thursday.pcap_Flow.csv',
    'enp0s3-tcpdump-pvt-friday.pcap_Flow.csv',
]

# ========================================
# MULTI-CLASS CONFIGURATION
# ========================================

NUM_CLASSES = 5
NUM_TEMPORAL_FEATS = 2   # flow_rank + inter_flow_gap, always appended last by graph builders

# Canonical stage names  (index == class label)
STAGE_NAMES = [
    'Benign',           # 0  (~76 % of data)
    'Reconnaissance',   # 1
    'Establish Foothold',  # 2
    'Lateral Movement', # 3
    'Data Exfiltration',   # 4
]

# Colour palette for per-stage visualisations
STAGE_COLORS = [
    '#2196F3',  # 0 Benign          â€” blue
    '#FF9800',  # 1 Reconnaissance  â€” orange
    '#F44336',  # 2 Establish Foothold â€” red
    '#9C27B0',  # 3 Lateral Movement  â€” purple
    '#4CAF50',  # 4 Data Exfiltration â€” green
]

# Keyword â†’ class-index mapping (lower-case, longest match wins)
_STAGE_KEYWORD_MAP = [
    ('data exfiltration',   4),
    ('dataexfiltration',    4),
    ('exfiltration',        4),
    ('lateral movement',    3),
    ('lateralmovement',     3),
    ('establish foothold',  2),
    ('establishfoothold',   2),
    ('reconnaissance',      1),
    ('cover up',            0),   # post-exploitation noise â†’ benign bucket
    ('coverup',             0),
    ('maintain access',     0),
    ('maintainaccess',      0),
]

def stage_to_multiclass(stage_label: object) -> int:
    """
    Map a raw DAPT-2020 Stage string to its integer class index (0â€“4).

    Uses longest-match-first keyword scanning so that composite strings
    (e.g. 'Establish Foothold â€“ Lateral Movement') fall to the first
    matching keyword in priority order.

    No leakage risk: this is a pure deterministic transformation applied
    identically to every row before any split is performed.
    """
    if pd.isna(stage_label):
        return 0
    s = str(stage_label).lower().strip()
    if s == '' or s == 'benign':
        return 0
    for keyword, idx in _STAGE_KEYWORD_MAP:
        if keyword in s:
            return idx
    return 0  # unknown â†’ treat as benign

# Expected 85 columns as per DAPT2020 specification
EXPECTED_COLUMNS = [
    'Flow ID', 'Src IP', 'Src Port', 'Dst IP', 'Dst Port',
    'Protocol', 'Timestamp', 'Flow Duration', 'Total Fwd Packet',
    'Total Bwd packets', 'Total Length of Fwd Packet', 'Total Length of Bwd Packet',
    'Fwd Packet Length Max', 'Fwd Packet Length Min', 'Fwd Packet Length Mean',
    'Fwd Packet Length Std', 'Bwd Packet Length Max', 'Bwd Packet Length Min',
    'Bwd Packet Length Mean', 'Bwd Packet Length Std', 'Flow Bytes/s',
    'Flow Packets/s', 'Flow IAT Mean', 'Flow IAT Std', 'Flow IAT Max',
    'Flow IAT Min', 'Fwd IAT Total', 'Fwd IAT Mean', 'Fwd IAT Std',
    'Fwd IAT Max', 'Fwd IAT Min', 'Bwd IAT Total', 'Bwd IAT Mean',
    'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min', 'Fwd PSH Flags',
    'Bwd PSH Flags', 'Fwd URG Flags', 'Bwd URG Flags', 'Fwd Header Length',
    'Bwd Header Length', 'Fwd Packets/s', 'Bwd Packets/s', 'Packet Length Min',
    'Packet Length Max', 'Packet Length Mean', 'Packet Length Std',
    'Packet Length Variance', 'FIN Flag Count', 'SYN Flag Count',
    'RST Flag Count', 'PSH Flag Count', 'ACK Flag Count', 'URG Flag Count',
    'CWR Flag Count', 'ECE Flag Count', 'Down/Up Ratio', 'Average Packet Size',
    'Fwd Segment Size Avg', 'Bwd Segment Size Avg', 'Fwd Bytes/Bulk Avg',
    'Fwd Packet/Bulk Avg', 'Fwd Bulk Rate Avg', 'Bwd Bytes/Bulk Avg',
    'Bwd Packet/Bulk Avg', 'Bwd Bulk Rate Avg', 'Subflow Fwd Packets',
    'Subflow Fwd Bytes', 'Subflow Bwd Packets', 'Subflow Bwd Bytes',
    'FWD Init Win Bytes', 'Bwd Init Win Bytes', 'Fwd Act Data Pkts',
    'Fwd Seg Size Min', 'Active Mean', 'Active Std', 'Active Max',
    'Active Min', 'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min',
    'Activity', 'Stage'
]

# Identifier columns (7)
IDENTIFIER_COLUMNS = ['Flow ID', 'Src IP', 'Src Port', 'Dst IP', 'Dst Port', 'Protocol', 'Timestamp']

# Label columns (2)
LABEL_COLUMNS = ['Activity', 'Stage']

def infer_network_type(file_name: str) -> str:
    """Infer whether a raw CSV came from the public or private capture set."""
    name = file_name.lower()
    if (
        'public' in name
        or ('enp0s3-monday.pcap' in name and 'pvt' not in name)
        or ('enp0s3-tcpdump-friday.pcap' in name and 'pvt' not in name)
    ):
        return 'public'
    if 'pvt' in name or 'private' in name:
        return 'private'
    return 'unknown'


def infer_capture_day(file_name: str) -> str:
    """Infer capture day from the file name."""
    name = file_name.lower()
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if day in name:
            return day
    return 'unknown'


def read_local_csv_with_header_fallback(csv_path: Path) -> tuple[pd.DataFrame, list[str], bool]:
    """
    Read a local DAPT2020 CSV, handling the known case where one file is missing the header row.
    Returns the dataframe, the detected column list, and a flag indicating whether fallback was used.
    """
    df_chunk = pd.read_csv(csv_path, low_memory=False)
    actual_columns = df_chunk.columns.tolist()
    overlap = len([col for col in actual_columns if col in EXPECTED_COLUMNS])
    fallback_used = False

    if overlap < max(10, len(EXPECTED_COLUMNS) // 2):
        df_chunk = pd.read_csv(
            csv_path,
            low_memory=False,
            header=None,
            names=EXPECTED_COLUMNS,
        )
        actual_columns = df_chunk.columns.tolist()
        fallback_used = True

    return df_chunk, actual_columns, fallback_used


print(f"\n{'='*80}")
print("DAPT2020 â€” GATv2 + R-GCN + ST-GCN + GIN + GCN-DGI (5-Model Pipeline)")
print(f"{'='*80}")
print(f"Local raw data dir: {LOCAL_DATA_DIR}")
print(f"Local consolidated CSV: {LOCAL_CONSOLIDATED_CSV}")
print(f"Local output dir: {LOCAL_RUN_OUTPUT_DIR}")
print("âœ“ Network-aware processing (public/private)")
print("âœ“ Stratified temporal splitting")
print("âœ“ Proper normalization (fit on train only)")
print("âœ“ Reduced graph connectivity")
print("âœ“ Case-insensitive label handling")
print(f"{'='*80}\n")

# ========================================
# DATA LOADING WITH NETWORK CONTEXT
# ========================================

def load_dapt2020_with_network_context(max_files=None, sample_rate=1.0, merge_networks=False):
    """
    Load DAPT2020 dataset with network type awareness

    Args:
        max_files: Limit number of files (for testing)
        sample_rate: Sample percentage of flows (0.0-1.0)
        merge_networks: If True, combine public/private. If False, keep separate
    """

    print(f"\n{'='*80}")
    print("LOADING DAPT2020 DATASET (LOCAL / NETWORK-AWARE)")
    print(f"{'='*80}")
    print(f"  Raw data directory: {LOCAL_DATA_DIR}")
    print(f"  Consolidated CSV: {LOCAL_CONSOLIDATED_CSV}")
    print(f"  Merge networks flag: {merge_networks}")

    raw_csv_files = [LOCAL_DATA_DIR / name for name in KNOWN_DAPT2020_FILES if (LOCAL_DATA_DIR / name).exists()]
    use_consolidated = LOCAL_CONSOLIDATED_CSV.exists() and max_files is None and sample_rate == 1.0

    if max_files:
        raw_csv_files = raw_csv_files[:max_files]

    print(f"\nâœ“ Found {len(raw_csv_files)} local CSV files total")
    if raw_csv_files:
        for csv_path in raw_csv_files:
            print(f"    Found: {csv_path.name}")

    # (Binary is_apt kept for audit / backward compatibility only â€”
    #  the pipeline now uses MultiLabel for all classification.)
    apt_keywords = [
        'reconnaissance', 'lateral movement', 'lateralmovement',
        'establish foothold', 'establishfoothold',
        'data exfiltration', 'dataexfiltration', 'exfiltration',
        'cover up', 'coverup', 'maintain access', 'maintainaccess'
    ]

    def is_apt(stage_label):
        """Binary APT flag â€” kept for audit printouts only."""
        if pd.isna(stage_label):
            return 0
        label_lower = str(stage_label).lower().strip()
        if label_lower == 'benign' or label_lower == '':
            return 0
        return 1 if any(keyword in label_lower for keyword in apt_keywords) else 0

    if not raw_csv_files and not use_consolidated:
        raise ValueError(
            "No local DAPT2020 CSV files found. Run scripts\\import_dapt2020_data.ps1 first."
        )

    if use_consolidated:
        print("\nLoading consolidated local CSV...")
        df = pd.read_csv(LOCAL_CONSOLIDATED_CSV, low_memory=False)
        print(f"âœ“ Total flows loaded from consolidated CSV: {len(df):,}")
    else:
        if LOCAL_CONSOLIDATED_CSV.exists() and (max_files is not None or sample_rate < 1.0):
            print(
                "\nConsolidated CSV exists, but raw-file mode is being used because "
                "max_files/sample_rate overrides were requested."
            )

        all_data = []
        header = None

        print("\nLoading local CSV files and preserving temporal order...")
        start_time = datetime.now()

        for idx, csv_path in enumerate(raw_csv_files):
            if idx % 5 == 0 and idx > 0:
                print(f"  File {idx}/{len(raw_csv_files)}")

            try:
                df_chunk, actual_columns, fallback_used = read_local_csv_with_header_fallback(csv_path)

                if idx == 0:
                    print(f"\n--- Column Analysis (First File) ---")
                    print(f"  Actual columns in CSV: {len(actual_columns)}")
                    print(f"  Expected columns: {len(EXPECTED_COLUMNS)}")

                    unexpected = [col for col in actual_columns if col not in EXPECTED_COLUMNS]
                    if unexpected:
                        print(f"    Unexpected columns found ({len(unexpected)}): {unexpected[:10]}...")

                    missing = [col for col in EXPECTED_COLUMNS if col not in actual_columns]
                    if missing:
                        print(f"    Missing expected columns ({len(missing)}): {missing}")

                    print(f"  âœ“ Filtering to expected columns only")
                elif fallback_used:
                    print(f"  Header fallback used for {csv_path.name}")

                valid_columns = [col for col in EXPECTED_COLUMNS if col in actual_columns]
                df_chunk = df_chunk[valid_columns]

                if header is None:
                    header = valid_columns
                    print(f"\nâœ“ Using {len(header)} validated columns")
                    print(f"  First 15: {header[:15]}")
                    print(f"  Last 10: {header[-10:]}")

                if sample_rate < 1.0:
                    df_chunk = df_chunk.sample(frac=sample_rate, random_state=42)

                df_chunk['network_type'] = infer_network_type(csv_path.name)
                df_chunk['day'] = infer_capture_day(csv_path.name)
                df_chunk['source_file'] = csv_path.name

                all_data.append(df_chunk)

            except Exception as e:
                print(f"  Error loading {csv_path.name}: {e}")
                continue

        if not all_data:
            raise ValueError("No local data loaded. Check the raw CSV files in the data directory.")

        print(f"\nCombining {len(all_data)} dataframes...")
        df = pd.concat(all_data, ignore_index=True)
        print(f"âœ“ Total flows loaded: {len(df):,}")

    # Normalize Stage labels (case-insensitive)
    print(f"\n{'='*80}")
    print("LABEL NORMALIZATION")
    print(f"{'='*80}")

    print(f"\nOriginal Stage values:")
    print(df['Stage'].value_counts())

    # Multi-class label
    df['MultiLabel'] = df['Stage'].apply(stage_to_multiclass)

    # Binary label for audit
    df['BinaryLabel'] = df['Stage'].apply(is_apt)

    print(f"\nâœ“ Multi-class labels created (5 stages):")
    for cls_idx, cls_name in enumerate(STAGE_NAMES):
        cnt = (df['MultiLabel'] == cls_idx).sum()
        print(f"  [{cls_idx}] {cls_name:<25}: {cnt:,} ({cnt/len(df)*100:.2f}%)")

    apt_count = (df['BinaryLabel'] == 1).sum()
    benign_count = (df['BinaryLabel'] == 0).sum()
    print(f"\n  Binary audit â€” APT: {apt_count:,}  Benign: {benign_count:,}")

    # Identify feature columns using expected column lists
    print(f"\n{'='*80}")
    print("FEATURE IDENTIFICATION")
    print(f"{'='*80}")

    # Metadata columns we added
    metadata_cols = ['network_type', 'day', 'source_file', 'BinaryLabel', 'MultiLabel', 'timestamp_sort']

    # Feature columns = Expected columns - Identifiers - Labels - Metadata
    feature_cols = [col for col in df.columns
                   if col in EXPECTED_COLUMNS
                   and col not in IDENTIFIER_COLUMNS
                   and col not in LABEL_COLUMNS
                   and col not in metadata_cols]

    # All columns to exclude from features
    exclude_cols = IDENTIFIER_COLUMNS + LABEL_COLUMNS + metadata_cols

    print(f"\nColumn categorization:")
    print(f"  Total columns in dataframe: {len(df.columns)}")
    print(f"  Identifiers: {len(IDENTIFIER_COLUMNS)} - {IDENTIFIER_COLUMNS}")
    print(f"  Labels: {len(LABEL_COLUMNS)} - {LABEL_COLUMNS}")
    print(f"  Metadata: {len(metadata_cols)} - {metadata_cols}")
    print(f"  Features: {len(feature_cols)}")

    # Validate RAW DAPT feature count
    expected_feature_count = 76  # raw DAPT2020 features only
    if len(feature_cols) != expected_feature_count:
        print(f"\n  INFO: Expected {expected_feature_count} raw DAPT features but found {len(feature_cols)}")
        print(f"   This may indicate column naming issues in the CSV files")
        print(f"   (temporal features are added separately â€” this check is raw-only)")
    else:
        print(f"\nâœ“ Raw DAPT feature count matches expected: {expected_feature_count}")

    print(f"\nSample feature columns:")
    print(f"  {feature_cols[:10]}")
    print(f"  ...")
    print(f"  {feature_cols[-5:]}")

    # Convert features to numeric
    print(f"\nConverting {len(feature_cols)} features to numeric...")
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.fillna(0)
    df = df.replace([np.inf, -np.inf], 0)

    # Parse timestamps for temporal ordering
    print(f"\nParsing timestamps...")
    if 'Timestamp' in df.columns:
        try:
            df['timestamp_sort'] = pd.to_datetime(df['Timestamp'], errors='coerce', dayfirst=True)
        except:
            df['timestamp_sort'] = pd.to_datetime(
                df['Timestamp'],
                format='mixed',
                errors='coerce',
                dayfirst=True,
            )

    # Sort by timestamp
    df = df.sort_values('timestamp_sort').reset_index(drop=True)

    # Network type distribution
    print(f"\n{'='*80}")
    print("NETWORK TYPE DISTRIBUTION")
    print(f"{'='*80}")
    print(df.groupby(['network_type', 'MultiLabel']).size().unstack(fill_value=0))

    print(f"\nâœ“ Dataset ready: {df.shape[0]:,} flows Ã— {df.shape[1]} columns")
    print(f"  Feature vector: {len(feature_cols)} raw DAPT cols (6 temporal cols added post-split)")
    print(f"  â†’ actual node feature dim fed to models = {len(feature_cols) + 6 + 2}")
    print(f"{'='*80}\n")

    return df, feature_cols, IDENTIFIER_COLUMNS


# ========================================
# SPLIT-AWARE TEMPORAL FEATURE ENGINEERING
# ========================================

def compute_temporal_features_split_aware(train_df, val_df, test_df, feature_cols):
    """
    Compute six temporal features without data leakage across splits: Cyclic sin/cos of hour-of-day, Cyclic sin/cos of day-of-week, delta_src, delta_dst
    """

    print(f"\n{'='*80}")
    print("COMPUTING SPLIT-AWARE TEMPORAL FEATURES (no leakage)")
    print(f"{'='*80}")

    new_cols = ['tod_sin', 'tod_cos', 'dow_sin', 'dow_cos', 'delta_src', 'delta_dst']

    # Cyclic time features
    def _add_cyclic(df):
        df = df.copy()
        ts   = df['timestamp_sort']
        hour = ts.dt.hour + ts.dt.minute / 60.0
        dow  = ts.dt.dayofweek.astype(float)
        df['tod_sin'] = np.sin(2 * np.pi * hour / 24).astype(np.float32)
        df['tod_cos'] = np.cos(2 * np.pi * hour / 24).astype(np.float32)
        df['dow_sin'] = np.sin(2 * np.pi * dow  /  7).astype(np.float32)
        df['dow_cos'] = np.cos(2 * np.pi * dow  /  7).astype(np.float32)
        return df

    #Delta features seeded from a prior split
    def _add_deltas(df, seed_last_src, seed_last_dst):
        df = df.copy().sort_values('timestamp_sort').reset_index(drop=True)

        delta_src = np.zeros(len(df), dtype=np.float32)
        delta_dst = np.zeros(len(df), dtype=np.float32)

        # Running "last seen" dicts
        last_src = dict(seed_last_src)
        last_dst = dict(seed_last_dst)

        for i, row in df.iterrows():
            src = row['Src IP']
            dst = row['Dst IP']
            ts  = row['timestamp_sort']

            if src in last_src:
                delta_src[i] = max((ts - last_src[src]).total_seconds(), 0.0)
            # else: first time this IP is seen â†’ delta stays 0
            last_src[src] = ts

            if dst in last_dst:
                delta_dst[i] = max((ts - last_dst[dst]).total_seconds(), 0.0)
            last_dst[dst] = ts

        df['delta_src'] = delta_src
        df['delta_dst'] = delta_dst

        return df, last_src, last_dst

    #Cyclic features: derived from each flow's own timestamp
    train_df = _add_cyclic(train_df)
    val_df   = _add_cyclic(val_df)
    test_df  = _add_cyclic(test_df)
    print(f"  âœ“ tod_sin / tod_cos   cyclic hour-of-day  range [-1, 1]  (all splits)")
    print(f"  âœ“ dow_sin / dow_cos   cyclic day-of-week  range [-1, 1]  (all splits)")

    #Delta features: each split seeds from end of the prior split
    # Train empty seeds
    print(f"\n  Computing delta_src / delta_dst (row-by-row, leak-free)...")
    print(f"  â†’ Train split ({len(train_df):,} rows)...")
    train_df, last_src_after_train, last_dst_after_train = _add_deltas(
        train_df, seed_last_src={}, seed_last_dst={}
    )

    # Val seeds from end of train
    print(f"  â†’ Val split   ({len(val_df):,} rows, seeded from train)...")
    val_df, last_src_after_val, last_dst_after_val = _add_deltas(
        val_df,
        seed_last_src=last_src_after_train,
        seed_last_dst=last_dst_after_train
    )

    # Test seeds from end of train+val
    print(f"  â†’ Test split  ({len(test_df):,} rows, seeded from train+val)...")
    test_df, _, _ = _add_deltas(
        test_df,
        seed_last_src=last_src_after_val,
        seed_last_dst=last_dst_after_val
    )

    # Diagnostic
    for split_name, split_df in [('Train', train_df), ('Val', val_df), ('Test', test_df)]:
        nz_src = split_df['delta_src'][split_df['delta_src'] > 0]
        nz_dst = split_df['delta_dst'][split_df['delta_dst'] > 0]
        src_med = f"{nz_src.median():.1f}s" if len(nz_src) > 0 else "n/a"
        dst_med = f"{nz_dst.median():.1f}s" if len(nz_dst) > 0 else "n/a"
        print(f"  âœ“ {split_name:<6}  delta_src median={src_med}  "
              f"delta_dst median={dst_med}")

    #Register new columns
    feature_cols = feature_cols + new_cols

    print(f"\n  Temporal features added  : {len(new_cols)} "
          f"({', '.join(new_cols)})")
    print(f"  Total feature_cols now   : {len(feature_cols)}"
          f"  ({len(feature_cols) - len(new_cols)} raw DAPT"
          f" + {len(new_cols)} temporal)")
    print(f"  Graph-local features (appended at build time, not scaled):")
    print(f"    flow_rank      â€” rank/graph_size âˆˆ [0, 1]")
    print(f"    inter_flow_gap â€” (T_i - T_min) / window_duration âˆˆ [0, 1]")
    print(f"  â†’ Final node feature dim fed to all models = {len(feature_cols) + 2}")
    print(f"{'='*80}\n")

    return train_df, val_df, test_df, feature_cols


# ========================================
# STRATIFIED TEMPORAL SPLIT (From DAPT2021)
# ========================================

def _hybrid_stratified_split_three_way(df, val_size, test_size, n_blocks):
    """
    Hybrid stratified temporal three-way split between train, val, test.

    Within each temporal block the samples are ordered chronologically
    and sliced from the tail:
    """
    print(f"\n  Using HYBRID STRATIFIED THREE-WAY strategy")
    print(f"  Target split: "
          f"{(1-val_size-test_size)*100:.0f}% train / "
          f"{val_size*100:.0f}% val / "
          f"{test_size*100:.0f}% test")

    block_size = len(df) // n_blocks
    train_indices = []
    val_indices   = []
    test_indices  = []

    # per_block[cls] accumulates sample count for each stage class across blocks
    per_block = {cls: [] for cls in range(NUM_CLASSES)}

    for i in range(n_blocks):
        start_idx    = i * block_size
        end_idx      = (i + 1) * block_size if i < n_blocks - 1 else len(df)
        block_indices = list(range(start_idx, end_idx))

        #  Multi-class stratification (5 stages)
        # TEMPORAL SAFETY: labels are read from the pre-split df which is already sorted chronologically.
        block_labels = df.iloc[block_indices]['MultiLabel'].values
        class_indices = {cls: [] for cls in range(NUM_CLASSES)}
        for idx, lbl in zip(block_indices, block_labels):
            class_indices[lbl].append(idx)

        for cls in range(NUM_CLASSES):
            per_block[cls].append(len(class_indices[cls]))

        for cls, cls_idx_list in class_indices.items():
            n = len(cls_idx_list)
            if n == 0:
                continue

            # Ensure at least 1 sample in val and test when the class exists
            n_test = max(1, int(n * test_size))
            n_val  = max(1, int(n * val_size))

            # Guard: never let val+test consume the whole block
            if n_val + n_test >= n:
                n_val  = max(0, n // 4)
                n_test = max(0, n // 4)

            # Slice from the tail (most recent = test, then val, then train)
            # This preserves chronological ordering within each class.
            test_part  = cls_idx_list[-n_test:]                         if n_test > 0 else []
            val_part   = cls_idx_list[-(n_test + n_val):-n_test]        if n_val  > 0 else []
            train_part = cls_idx_list[:-(n_test + n_val)]               if (n_test + n_val) < n else []

            train_indices.extend(train_part)
            val_indices.extend(val_part)
            test_indices.extend(test_part)

    for cls, cls_name in enumerate(STAGE_NAMES):
        print(f"  {cls_name:<25} samples per block: {per_block[cls]}")

    train_indices.sort()
    val_indices.sort()
    test_indices.sort()

    return (df.iloc[train_indices].copy(),
            df.iloc[val_indices].copy(),
            df.iloc[test_indices].copy())


def _hybrid_stratified_split(df, test_size, n_blocks):
    """
    Calls the three-way version with val_size=0 so behavior is identical
    to the original for that code path.
    """
    train_df, _, test_df = _hybrid_stratified_split_three_way(
        df, val_size=0.0, test_size=test_size, n_blocks=n_blocks
    )
    return train_df, test_df


def stratified_temporal_split_by_network(df, feature_cols,
                                          val_size=0.15, test_size=0.15,
                                          n_blocks=10, strategy='hybrid'):
    """
    Stratified temporal THREE-WAY 70%/15%/15% split for each network type separately.
    train_df â€” used for model training and DGI pretraining
    val_df   â€” used ONLY inside Optuna trials (hyperparameter signal)
    test_df  â€” held out completely; evaluated once after final training
    """

    print(f"\n{'='*80}")
    print(f"NETWORK-AWARE STRATIFIED TEMPORAL SPLIT  (3-way)")
    print(f"{'='*80}")
    print(f"  Target: {(1-val_size-test_size)*100:.0f}% train  /  "
          f"{val_size*100:.0f}% val  /  {test_size*100:.0f}% test")

    public_df  = df[df['network_type'] == 'public'].copy()
    private_df = df[df['network_type'] == 'private'].copy()

    print(f"\nOriginal Distribution:")
    print(f"  Public:  {len(public_df):,} flows")
    print(f"  Private: {len(private_df):,} flows")

    # Fallback to two-way split if one network type is absent
    if len(public_df) == 0 or len(private_df) == 0:
        print("\n  Warning: One network type has no data! Using unified split...")
        train_df, val_df, test_df = _hybrid_stratified_split_three_way(
            df, val_size=val_size, test_size=test_size, n_blocks=n_blocks
        )
    else:
        print(f"\n{'='*40}")
        print("SPLITTING PUBLIC NETWORK")
        print(f"{'='*40}")
        pub_train, pub_val, pub_test = _hybrid_stratified_split_three_way(
            public_df, val_size=val_size, test_size=test_size, n_blocks=n_blocks
        )

        print(f"\n{'='*40}")
        print("SPLITTING PRIVATE NETWORK")
        print(f"{'='*40}")
        priv_train, priv_val, priv_test = _hybrid_stratified_split_three_way(
            private_df, val_size=val_size, test_size=test_size, n_blocks=n_blocks
        )

        train_df = pd.concat([pub_train, priv_train], ignore_index=True)
        val_df   = pd.concat([pub_val,   priv_val],   ignore_index=True)
        test_df  = pd.concat([pub_test,  priv_test],  ignore_index=True)

    # Sort all three by timestamp to preserve temporal ordering
    for frame in [train_df, val_df, test_df]:
        frame.sort_values('timestamp_sort', inplace=True)
        frame.reset_index(drop=True, inplace=True)

    # Print split quality
    print(f"\n{'='*80}")
    print("COMBINED SPLIT QUALITY")
    print(f"{'='*80}")

    def _stats(label, frame, total):
        pub  = (frame['network_type'] == 'public').sum()
        priv = (frame['network_type'] == 'private').sum()
        n    = max(len(frame), 1)
        print(f"\n{label} Set  ({len(frame)/total*100:.1f}% of data):")
        print(f"  Total:   {len(frame):,} flows")
        for cls_idx, cls_name in enumerate(STAGE_NAMES):
            cnt = (frame['MultiLabel'] == cls_idx).sum()
            print(f"  [{cls_idx}] {cls_name:<25}: {cnt:,} ({cnt/n*100:.2f}%)")
        print(f"  Public:  {pub:,} ({pub/n*100:.2f}%)")
        print(f"  Private: {priv:,} ({priv/n*100:.2f}%)")

    total = len(train_df) + len(val_df) + len(test_df)
    _stats("Training",   train_df, total)
    _stats("Validation", val_df,   total)
    _stats("Test",       test_df,  total)

    # Split-aware temporal feature engineering
    train_df, val_df, test_df, feature_cols = compute_temporal_features_split_aware(
        train_df, val_df, test_df, feature_cols
    )

    # Feature normalization
    print(f"\n{'='*80}")
    print("FEATURE NORMALIZATION")
    print(f"{'='*80}")
    print(f"âœ“ Fitting StandardScaler on TRAINING data only...")

    scaler = StandardScaler()
    train_df[feature_cols] = scaler.fit_transform(train_df[feature_cols])

    print(f"âœ“ Transforming VALIDATION data with training statistics...")
    val_df[feature_cols]  = scaler.transform(val_df[feature_cols])

    print(f"âœ“ Transforming TEST data with training statistics...")
    test_df[feature_cols] = scaler.transform(test_df[feature_cols])

    print(f"âœ“ No normalisation leakage â€” val and test scaled with train stats only")
    print(f"{'='*80}\n")

    # feature_cols is returned so callers receive the updated list that
    # includes the 6 temporal columns added by compute_temporal_features_split_aware.
    return train_df, val_df, test_df, scaler, feature_cols

# ========================================
# GRAPH BUILDER
# ========================================

def create_network_aware_graphs_with_k(df, feature_cols, flows_per_graph=1000, k=5,
                                       for_rgcn=False):
    """
    Create network-aware graphs with custom k value for KNN.

    for_rgcn=False: will call build_graph_with_custom_k (original, no edge_type)
    for_rgcn=True: call build_graph_with_custom_k_rgcn (adds edge_type tensor)
    """

    builder_fn = build_graph_with_custom_k_rgcn if for_rgcn else build_graph_with_custom_k
    print(f"  Creating graphs with k={k} neighbors "
          f"({'RGCN edge-typed' if for_rgcn else 'standard'})...")

    public_df  = df[df['network_type'] == 'public'].copy()
    private_df = df[df['network_type'] == 'private'].copy()

    if len(public_df) == 0 or len(private_df) == 0:
        print("\n  Warning: One network type has no data!")
        all_graphs = []
        for i in range(0, len(df), flows_per_graph):
            chunk = df.iloc[i:i+flows_per_graph]
            if len(chunk) < 100:
                continue
            graph = builder_fn(chunk, feature_cols, k=k)
            if graph is not None:
                all_graphs.append(graph)
        return all_graphs, [], []

    public_graphs  = []
    private_graphs = []

    for i in range(0, len(public_df), flows_per_graph):
        chunk = public_df.iloc[i:i+flows_per_graph]
        if len(chunk) < 100:
            continue
        graph = builder_fn(chunk, feature_cols, k=k)
        if graph is not None:
            graph.network_type = 'public'
            public_graphs.append(graph)

    for i in range(0, len(private_df), flows_per_graph):
        chunk = private_df.iloc[i:i+flows_per_graph]
        if len(chunk) < 100:
            continue
        graph = builder_fn(chunk, feature_cols, k=k)
        if graph is not None:
            graph.network_type = 'private'
            private_graphs.append(graph)

    all_graphs = public_graphs + private_graphs
    return all_graphs, public_graphs, private_graphs


def build_graph_with_custom_k(df_chunk, feature_cols, k=5):
    """
    Build a single graph with custom k value.
    """
    from sklearn.neighbors import NearestNeighbors

    df_indexed = df_chunk.reset_index(drop=True)
    num_nodes = len(df_indexed)

    if num_nodes < 10:
        return None

    node_features = df_indexed[feature_cols].values.astype(np.float32)
    # MultiLabel: 0=Benign,1=Recon,2=Foothold,3=Lateral,4=Exfil
    node_labels = df_indexed['MultiLabel'].values.astype(np.int64)

    # Data is pre-scaled globally â€” no local scaler needed
    edge_list = []

    # IP-based edges
    if 'Src IP' in df_indexed.columns:
        src_ip_groups = df_indexed.groupby('Src IP').groups
        for ip, indices in src_ip_groups.items():
            indices = list(indices)
            if len(indices) > 1:
                max_connections = min(len(indices) - 1, 5)
                for i in range(max_connections):
                    edge_list.append([indices[i], indices[i+1]])

    if 'Dst IP' in df_indexed.columns:
        dst_ip_groups = df_indexed.groupby('Dst IP').groups
        for ip, indices in dst_ip_groups.items():
            indices = list(indices)
            if len(indices) > 1:
                max_connections = min(len(indices) - 1, 5)
                for i in range(max_connections):
                    edge_list.append([indices[i], indices[i+1]])

    # KNN-based edges with CUSTOM k value
    if num_nodes > k:
        knn = NearestNeighbors(n_neighbors=min(k+1, num_nodes), metric='euclidean')
        knn.fit(node_features)
        distances, indices = knn.kneighbors(node_features)

        for i in range(num_nodes):
            for j in indices[i, 1:]:  # Skip self
                edge_list.append([i, int(j)])

    edge_list = list(set([tuple(sorted(e)) for e in edge_list]))

    if len(edge_list) == 0:
        for i in range(0, num_nodes - 1, 10):
            edge_list.append([i, min(i+10, num_nodes-1)])

    # flow_rank: relative position of this flow within the snapshot window.
    flow_rank = (np.arange(num_nodes) / max(num_nodes - 1, 1)).astype(np.float32)

    # inter_flow_gap: time elapsed since the first flow in this window,
    if 'timestamp_sort' in df_indexed.columns:
        ts_vals = df_indexed['timestamp_sort']
        t_min   = ts_vals.min()
        t_max   = ts_vals.max()
        window_dur = max((t_max - t_min).total_seconds(), 1.0)  # avoid /0
        gap_raw    = (ts_vals - t_min).dt.total_seconds().values
        inter_flow_gap = (gap_raw / window_dur).astype(np.float32)
    else:
        inter_flow_gap = np.zeros(num_nodes, dtype=np.float32)

    # Concatenate: [scaled_global_features | flow_rank | inter_flow_gap]
    temporal_local = np.stack([flow_rank, inter_flow_gap], axis=1)  # (N, 2)
    node_features  = np.concatenate([node_features, temporal_local], axis=1)

    x = torch.tensor(node_features, dtype=torch.float)
    edge_index = torch.tensor([[e[0], e[1]] for e in edge_list], dtype=torch.long).t().contiguous()
    y = torch.tensor(node_labels, dtype=torch.long)

    from torch_geometric.data import Data
    graph = Data(x=x, edge_index=edge_index, y=y, num_nodes=num_nodes)

    return graph


def build_graph_with_custom_k_rgcn(df_chunk, feature_cols, k=5):
    """
    Build a single graph for R-GCN with typed edges.

    Edge types
    0  Same Source IP   â€” flows originating from the same host.
    1  Same Destination IP â€” flows targeting the same host.
    2  KNN feature similarity â€” flows with similar statistical profiles
    """
    from sklearn.neighbors import NearestNeighbors

    df_indexed = df_chunk.reset_index(drop=True)
    num_nodes  = len(df_indexed)

    if num_nodes < 10:
        return None

    node_features = df_indexed[feature_cols].values.astype(np.float32)
    # MultiLabel: 0=Benign,1=Recon,2=Foothold,3=Lateral,4=Exfil
    node_labels   = df_indexed['MultiLabel'].values.astype(np.int64)

    # Data is pre-scaled globally â€” no local scaler needed.
    # Double-scaling would corrupt KNN edge topology and node features.
    # edge_dict maps (min_node, max_node) â†’ relation_type (int).
    edge_dict = {}   # { (u, v): relation_type }

    #Relation 0: Same Source IP
    if 'Src IP' in df_indexed.columns:
        for _, indices in df_indexed.groupby('Src IP').groups.items():
            indices = list(indices)
            if len(indices) > 1:
                for i in range(min(len(indices) - 1, 5)):
                    u, v = indices[i], indices[i + 1]
                    key  = (min(u, v), max(u, v))
                    if key not in edge_dict:
                        edge_dict[key] = 0   # relation: same source IP

    #Relation 1: Same Destination IP
    if 'Dst IP' in df_indexed.columns:
        for _, indices in df_indexed.groupby('Dst IP').groups.items():
            indices = list(indices)
            if len(indices) > 1:
                for i in range(min(len(indices) - 1, 5)):
                    u, v = indices[i], indices[i + 1]
                    key  = (min(u, v), max(u, v))
                    if key not in edge_dict:
                        edge_dict[key] = 1   # relation: same destination IP

    #Relation 2: KNN feature similarity
    if num_nodes > k:
        knn = NearestNeighbors(
            n_neighbors=min(k + 1, num_nodes), metric='euclidean'
        )
        knn.fit(node_features)
        _, nbr_indices = knn.kneighbors(node_features)

        for i in range(num_nodes):
            for j in nbr_indices[i, 1:]:   # skip self (index 0)
                u, v = int(i), int(j)
                key  = (min(u, v), max(u, v))
                if key not in edge_dict:
                    edge_dict[key] = 2   # relation: KNN similarity

    #Fallback: sequential chain if no edges were produced
    if len(edge_dict) == 0:
        for i in range(0, num_nodes - 1, 10):
            u, v = i, min(i + 10, num_nodes - 1)
            edge_dict[(u, v)] = 2

    # flow_rank: relative position of flow within this snapshot [0, 1].
    flow_rank = (np.arange(num_nodes) / max(num_nodes - 1, 1)).astype(np.float32)

    # inter_flow_gap: normalised time since first flow in window [0, 1].
    if 'timestamp_sort' in df_indexed.columns:
        ts_vals    = df_indexed['timestamp_sort']
        t_min      = ts_vals.min()
        t_max      = ts_vals.max()
        window_dur = max((t_max - t_min).total_seconds(), 1.0)
        gap_raw    = (ts_vals - t_min).dt.total_seconds().values
        inter_flow_gap = (gap_raw / window_dur).astype(np.float32)
    else:
        inter_flow_gap = np.zeros(num_nodes, dtype=np.float32)

    # Concatenate: [scaled_global_features | flow_rank | inter_flow_gap]
    temporal_local = np.stack([flow_rank, inter_flow_gap], axis=1)  # (N, 2)
    node_features  = np.concatenate([node_features, temporal_local], axis=1)

    pairs      = list(edge_dict.keys())
    rel_types  = [edge_dict[p] for p in pairs]

    edge_index = torch.tensor(
        [[p[0] for p in pairs], [p[1] for p in pairs]],
        dtype=torch.long
    )
    edge_type  = torch.tensor(rel_types, dtype=torch.long)
    x          = torch.tensor(node_features, dtype=torch.float)
    y          = torch.tensor(node_labels,   dtype=torch.long)

    from torch_geometric.data import Data
    graph = Data(
        x          = x,
        edge_index = edge_index,
        edge_type  = edge_type,
        y          = y,
        num_nodes  = num_nodes
    )

    return graph

def build_graph_with_custom_k_stgnn(df_chunk, feature_cols, k=5, temporal_k=4):
    """
    ST-GCN-specific graph builder.

    Differences from the standard builder:
      1. Temporal sort order â€” flows are ranked by timestamp_sort within the chunk and temporal_sort_order is stored on the Data object. The raw timestamp is NEVER stored as a node feature.
      2. Temporal window edges â€” in addition to the KNN+IP spatial edges, each
         flow is connected to its temporal_k nearest predecessors and successors
         in sorted time.
      3. Delta-t edge attribute â€” the normalised absolute time-gap between flows is stored in temporal_edge_attr on the Data object and not consumed
    Node feature shape is UNCHANGED
    """
    from sklearn.neighbors import NearestNeighbors

    df_indexed = df_chunk.reset_index(drop=True)
    num_nodes  = len(df_indexed)

    if num_nodes < 10:
        return None

    node_features = df_indexed[feature_cols].values.astype(np.float32)
    node_labels   = df_indexed['MultiLabel'].values.astype(np.int64)

    # Temporal ordering
    # Compute the argsort of timestamp_sort.
    if 'timestamp_sort' in df_indexed.columns:
        ts_vals  = df_indexed['timestamp_sort']
        temp_ord = np.argsort(ts_vals.values, kind='stable').astype(np.int64)

        # Delta-t between sorted consecutive flows, normalised to [0, 1].
        sorted_ts  = ts_vals.iloc[temp_ord].values
        # Convert to float seconds relative to first flow in the chunk.
        t0         = sorted_ts[0]
        diffs_sec  = ((sorted_ts - t0) / np.timedelta64(1, 's')).astype(np.float64)
        window_dur = max(diffs_sec[-1], 1.0)
        gap_norm   = (diffs_sec / window_dur).astype(np.float32)          # [0, 1]
        delta_t_sorted = np.diff(gap_norm, prepend=0.0).astype(np.float32)
    else:
        temp_ord       = np.arange(num_nodes, dtype=np.int64)
        delta_t_sorted = np.zeros(num_nodes, dtype=np.float32)

    # Spatial edges (KNN + IP, identical to base builder)
    edge_list = []

    if 'Src IP' in df_indexed.columns:
        for ip, indices in df_indexed.groupby('Src IP').groups.items():
            indices = list(indices)
            if len(indices) > 1:
                max_con = min(len(indices) - 1, 5)
                for i in range(max_con):
                    edge_list.append([indices[i], indices[i + 1]])

    if 'Dst IP' in df_indexed.columns:
        for ip, indices in df_indexed.groupby('Dst IP').groups.items():
            indices = list(indices)
            if len(indices) > 1:
                max_con = min(len(indices) - 1, 5)
                for i in range(max_con):
                    edge_list.append([indices[i], indices[i + 1]])

    if num_nodes > k:
        knn = NearestNeighbors(n_neighbors=min(k + 1, num_nodes), metric='euclidean')
        knn.fit(node_features)
        _, knn_idx = knn.kneighbors(node_features)
        for i in range(num_nodes):
            for j in knn_idx[i, 1:]:
                edge_list.append([i, int(j)])

    edge_set = list(set([tuple(sorted(e)) for e in edge_list]))
    if len(edge_set) == 0:
        for i in range(0, num_nodes - 1, 10):
            edge_set.append([i, min(i + 10, num_nodes - 1)])

    # Temporal window edges
    temp_edge_src = []
    temp_edge_dst = []
    temp_edge_dt  = []

    for pos_i in range(num_nodes):
        node_i = int(temp_ord[pos_i])
        lo = max(0, pos_i - temporal_k)
        hi = min(num_nodes, pos_i + temporal_k + 1)
        for pos_j in range(lo, hi):
            if pos_j == pos_i:
                continue
            node_j = int(temp_ord[pos_j])
            dt_ij  = abs(float(delta_t_sorted[pos_i]) - float(delta_t_sorted[pos_j]))
            temp_edge_src.append(node_i)
            temp_edge_dst.append(node_j)
            temp_edge_dt.append(dt_ij)

    # Merge spatial + temporal edges into a single edge_index.
    # Temporal edges are directed (srcâ†’dst) to preserve ordering signal for GAT.
    all_src = [e[0] for e in edge_set] + [e[1] for e in edge_set] + temp_edge_src
    all_dst = [e[1] for e in edge_set] + [e[0] for e in edge_set] + temp_edge_dst

    # Node features (same as base builder)
    flow_rank = (np.arange(num_nodes) / max(num_nodes - 1, 1)).astype(np.float32)

    if 'timestamp_sort' in df_indexed.columns:
        ts_v   = df_indexed['timestamp_sort']
        t_min  = ts_v.min()
        t_max  = ts_v.max()
        w_dur  = max((t_max - t_min).total_seconds(), 1.0)
        g_raw  = (ts_v - t_min).dt.total_seconds().values
        inter_flow_gap = (g_raw / w_dur).astype(np.float32)
    else:
        inter_flow_gap = np.zeros(num_nodes, dtype=np.float32)

    temporal_local = np.stack([flow_rank, inter_flow_gap], axis=1)
    node_features  = np.concatenate([node_features, temporal_local], axis=1)

    x          = torch.tensor(node_features, dtype=torch.float)
    edge_index = torch.tensor([all_src, all_dst], dtype=torch.long)
    y          = torch.tensor(node_labels, dtype=torch.long)

    from torch_geometric.data import Data
    graph = Data(x=x, edge_index=edge_index, y=y, num_nodes=num_nodes)

    # temporal_sort_order: node-level attribute.
    graph.temporal_sort_order = torch.tensor(temp_ord, dtype=torch.long)

    # Store temporal edge attrs separately for interpretability.
    if len(temp_edge_dt) > 0:
        graph.temporal_edge_attr = torch.tensor(temp_edge_dt, dtype=torch.float32)

    return graph


def create_stgnn_graphs_with_k(df, feature_cols, flows_per_graph=1000,
                                k=5, temporal_k=4):
    """
    Network-aware graph builder specifically for ST-GCN. Mirrors the structure of create_network_aware_graphs_with_k but calls build_graph_with_custom_k_stgnn so each Data object carries temporal_sort_order and enriched edge_index.
    """
    print(f"\n  Creating ST-GCN graphs (k={k}, temporal_k={temporal_k})...")

    public_df  = df[df['network_type'] == 'public'].copy()
    private_df = df[df['network_type'] == 'private'].copy()

    if len(public_df) == 0 or len(private_df) == 0:
        print("  Warning: one network type has no data â€” falling back to unified.")
        all_graphs = []
        for i in range(0, len(df), flows_per_graph):
            chunk = df.iloc[i:i + flows_per_graph]
            if len(chunk) < 100:
                continue
            g = build_graph_with_custom_k_stgnn(chunk, feature_cols,
                                                 k=k, temporal_k=temporal_k)
            if g is not None:
                all_graphs.append(g)
        return all_graphs, [], []

    public_graphs  = []
    private_graphs = []

    for i in range(0, len(public_df), flows_per_graph):
        chunk = public_df.iloc[i:i + flows_per_graph]
        if len(chunk) < 100:
            continue
        g = build_graph_with_custom_k_stgnn(chunk, feature_cols,
                                             k=k, temporal_k=temporal_k)
        if g is not None:
            g.network_type = 'public'
            public_graphs.append(g)

    for i in range(0, len(private_df), flows_per_graph):
        chunk = private_df.iloc[i:i + flows_per_graph]
        if len(chunk) < 100:
            continue
        g = build_graph_with_custom_k_stgnn(chunk, feature_cols,
                                             k=k, temporal_k=temporal_k)
        if g is not None:
            g.network_type = 'private'
            private_graphs.append(g)

    all_graphs = public_graphs + private_graphs
    print(f"  âœ“ ST-GCN graphs: {len(public_graphs)} public + "
          f"{len(private_graphs)} private = {len(all_graphs)} total")
    return all_graphs, public_graphs, private_graphs


def create_network_aware_graphs(df, feature_cols, flows_per_graph=1000):
    """
    Create separate graph families for public and private networks
    """

    print(f"\n{'='*80}")
    print("CREATING NETWORK-AWARE GRAPHS (SEPARATE FAMILIES)")
    print(f"{'='*80}")

    # Split by network type
    public_df = df[df['network_type'] == 'public'].copy()
    private_df = df[df['network_type'] == 'private'].copy()

    print(f"\nNetwork Type Distribution:")
    print(f"  Public network:  {len(public_df):,} flows")
    print(f"  Private network: {len(private_df):,} flows")

    if len(public_df) == 0 or len(private_df) == 0:
        print("\n  Warning: One network type has no data!")
        print("   Falling back to unified graph construction...")
        return create_flow_level_graphs(df, feature_cols, flows_per_graph), [], []

    # Create PUBLIC network graphs
    print(f"\n--- Building PUBLIC Network Graphs ---")
    public_graphs = []
    chunk_size = flows_per_graph

    for i in range(0, len(public_df), chunk_size):
        chunk = public_df.iloc[i:i+chunk_size]

        if len(chunk) < 100:
            continue

        graph = build_graph_with_custom_k(chunk, feature_cols, k=5)

        if graph is not None:
            graph.network_type = 'public'
            public_graphs.append(graph)

        if len(public_graphs) % 50 == 0 and len(public_graphs) > 0:
            print(f"  Created {len(public_graphs)} public graphs...")

    print(f"âœ“ Created {len(public_graphs)} PUBLIC graphs")

    # Create PRIVATE network graphs
    print(f"\n--- Building PRIVATE Network Graphs ---")
    private_graphs = []

    for i in range(0, len(private_df), chunk_size):
        chunk = private_df.iloc[i:i+chunk_size]

        if len(chunk) < 100:
            continue

        graph = build_graph_with_custom_k(chunk, feature_cols, k=5)

        if graph is not None:
            graph.network_type = 'private'
            private_graphs.append(graph)

        if len(private_graphs) % 50 == 0 and len(private_graphs) > 0:
            print(f"  Created {len(private_graphs)} private graphs...")

    print(f"âœ“ Created {len(private_graphs)} PRIVATE graphs")

    # Combine graphs (chronologically interleaved)
    all_graphs = public_graphs + private_graphs

    # Calculate statistics â€” per-stage counts (5-class)
    def _stage_counts(graphs):
        nodes = sum(g.num_nodes for g in graphs)
        counts = {cls: sum((g.y == cls).sum().item() for g in graphs)
                  for cls in range(NUM_CLASSES)}
        return nodes, counts

    total_nodes,   total_counts   = _stage_counts(all_graphs)
    public_nodes,  public_counts  = _stage_counts(public_graphs)
    private_nodes, private_counts = _stage_counts(private_graphs)

    def _print_net_stats(label, graphs, nodes, counts):
        print(f"\n{label} Network:")
        print(f"  Graphs: {len(graphs)}")
        print(f"  Nodes:  {nodes:,}")
        safe_n = max(nodes, 1)
        for cls_idx, cls_name in enumerate(STAGE_NAMES):
            c = counts[cls_idx]
            print(f"  [{cls_idx}] {cls_name:<25}: {c:,} ({c/safe_n*100:.2f}%)")
        if len(graphs) > 0:
            avg_edges = np.mean([g.edge_index.shape[1] for g in graphs])
            print(f"  Avg edges per graph: {avg_edges:.0f}")

    print(f"\n{'='*80}")
    print("GRAPH STATISTICS BY NETWORK TYPE")
    print(f"{'='*80}")
    _print_net_stats("PUBLIC",  public_graphs,  public_nodes,  public_counts)
    _print_net_stats("PRIVATE", private_graphs, private_nodes, private_counts)

    print(f"\nCOMBINED:")
    print(f"  Total graphs: {len(all_graphs)}")
    print(f"  Total nodes:  {total_nodes:,}")
    safe_total = max(total_nodes, 1)
    for cls_idx, cls_name in enumerate(STAGE_NAMES):
        c = total_counts[cls_idx]
        print(f"  [{cls_idx}] {cls_name:<25}: {c:,} ({c/safe_total*100:.2f}%)")
    print(f"{'='*80}\n")

    return all_graphs, public_graphs, private_graphs

# ========================================
# GNN MODELS
# ========================================

class NodeLevelGATv2(nn.Module):
    def __init__(self, num_features, hidden_dim=128, heads=8,
                 dropout=0.5, attention_dropout=0.2,
                 num_classes=NUM_CLASSES):
        super(NodeLevelGATv2, self).__init__()

        # Layer 1: Input â†’ Hidden (multi-head, concat=True)
        # Output dim = hidden_dim * heads = 128 * 8 = 1024
        self.conv1 = GATv2Conv(
            num_features,
            hidden_dim,
            heads=heads,
            dropout=attention_dropout,
            add_self_loops=True,
            concat=True
        )
        self.bn1 = nn.BatchNorm1d(hidden_dim * heads)

        # Layer 2: Hidden â†’ Hidden (keep multi-head)
        self.conv2 = GATv2Conv(
            hidden_dim * heads,
            hidden_dim,
            heads=heads,
            dropout=attention_dropout,
            add_self_loops=True,
            concat=True
        )
        self.bn2 = nn.BatchNorm1d(hidden_dim * heads)

        # Layer 3: Collapse to single head for final representation
        self.conv3 = GATv2Conv(
            hidden_dim * heads,
            hidden_dim,
            heads=1,
            dropout=attention_dropout,
            add_self_loops=True,
            concat=False
        )
        self.bn3 = nn.BatchNorm1d(hidden_dim)

        # Classifier head: hidden_dim â†’ hidden_dim â†’ hidden_dim//2 â†’ num_classes
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes)
        )

        self.dropout = dropout

    def forward(self, x, edge_index, batch=None, temporal_sort_order=None):
        # Layer 1: Dynamic multi-head attention
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv1(x, edge_index)
        x = self.bn1(x)
        x = F.elu(x)

        # Layer 2: Refined dynamic attention
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index)
        x = self.bn2(x)
        x = F.elu(x)

        # Layer 3: Final aggregation, single head
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv3(x, edge_index)
        x = self.bn3(x)
        x = F.elu(x)

        logits = self.classifier(x)
        return logits


class GatedCausalTCN(nn.Module):
    """
    Gated causal 1-D temporal convolution (STGCN-style GLU).

    Causality: left-only padding ensures position t sees only t-(k-1)â€¦t.
    Gating:    out = tanh(W_p Â· x) âŠ™ sigmoid(W_q Â· x)
               The sigmoid gate suppresses irrelevant temporal positions,
               giving the model soft selection over its causal receptive field.
    Residual:  output is added back to the input for gradient stability on
               the short sequences typical of a single graph chunk.
    """
    def __init__(self, channels, kernel_size=3, dropout=0.3):
        super(GatedCausalTCN, self).__init__()
        self.kernel_size = kernel_size
        self.causal_pad  = kernel_size - 1

        # Single conv outputs 2C so we can split for tanh/sigmoid gating.
        self.conv = nn.Conv1d(channels, 2 * channels,
                              kernel_size=kernel_size, padding=0, bias=True)
        self.bn   = nn.BatchNorm1d(channels)
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        """
        Args:
            x : (1, C, L) â€” L nodes in temporal order for one graph.
        Returns:
            (1, C, L) â€” gated causal output + identity residual.
        """
        padded = F.pad(x, (self.causal_pad, 0))   # left-only causal padding
        raw    = self.conv(padded)                  # (1, 2C, L)
        p, q   = raw.chunk(2, dim=1)               # each (1, C, L)
        gated  = torch.tanh(p) * torch.sigmoid(q)  # GLU
        gated  = self.bn(gated)
        gated  = self.drop(gated)
        return gated + x                           # residual


class STConvBlock(nn.Module):
    """
    True ST-GCN spatial-temporal conv block (Yu et al. 2018).

    Architecture â€” temporal-spatial-temporal sandwich: 1. GatedCausalTCN, 2.  GATConv (spatial), 3. GatedCausalTCN
    """
    def __init__(self, hidden_dim, dropout=0.5, kernel_size=3):
        super(STConvBlock, self).__init__()
        self.kernel_size = kernel_size

        # Temporal 1 - before spatial
        self.tcn1 = GatedCausalTCN(hidden_dim, kernel_size=kernel_size,
                                   dropout=dropout * 0.6)

        # Spatial: multi-head GAT - unchanged from prior architecture
        self.spatial_conv    = GATConv(hidden_dim, hidden_dim, heads=4,
                                       concat=True, dropout=dropout)
        self.spatial_bn      = nn.BatchNorm1d(hidden_dim * 4)
        self.spatial_project = nn.Linear(hidden_dim * 4, hidden_dim)

        # Temporal 2 - after spatial
        self.tcn2 = GatedCausalTCN(hidden_dim, kernel_size=kernel_size,
                                   dropout=dropout * 0.6)

        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.dropout    = nn.Dropout(dropout)

    def forward(self, x, edge_index, temporal_sort_order=None, batch=None):
        residual = x   # skip from BLOCK INPUT â€” not from temporal branch (Bug 2 fix)

        # Temporal 1
        t1 = self._apply_tcn(self.tcn1, x,  temporal_sort_order, batch)

        # Spatial
        s  = F.relu(self.spatial_bn(self.spatial_conv(t1, edge_index)))
        s  = self.spatial_project(s)

        # Temporal 2
        t2 = self._apply_tcn(self.tcn2, s,  temporal_sort_order, batch)

        #  Residual from block input (Bug 2 fix)
        out = self.layer_norm(t2 + residual)
        return self.dropout(out)

    def _apply_tcn(self, tcn_module, x, temporal_sort_order, batch):
        """
        Apply tcn_module per graph in the batch, honouring each graph's temporal ordering independently.
        """
        out = torch.zeros_like(x)

        if batch is None:
            sort_idx = (temporal_sort_order
                        if temporal_sort_order is not None
                        else torch.arange(x.shape[0], device=x.device))
            sorted_x = x[sort_idx]
            seq      = sorted_x.unsqueeze(0).transpose(1, 2)   # (1, C, N)
            tcn_out  = tcn_module(seq).transpose(1, 2).squeeze(0)
            inv_idx  = torch.argsort(sort_idx)
            return tcn_out[inv_idx]

        num_graphs = int(batch.max().item()) + 1
        ptr        = 0
        for g in range(num_graphs):
            mask = (batch == g)
            x_g  = x[mask]
            N_g  = x_g.shape[0]
            if N_g == 0:
                continue

            sort_g = (temporal_sort_order[ptr: ptr + N_g]
                      if temporal_sort_order is not None
                      else torch.arange(N_g, device=x.device))
            ptr += N_g

            if N_g < tcn_module.kernel_size:
                out[mask] = x_g   # graph too short for conv â€” identity pass
                continue

            sorted_x = x_g[sort_g]
            seq      = sorted_x.unsqueeze(0).transpose(1, 2)   # (1, C, N_g)
            tcn_out  = tcn_module(seq).transpose(1, 2).squeeze(0)
            inv_idx  = torch.argsort(sort_g)
            out[mask] = tcn_out[inv_idx]

        return out


class NodeLevelSTGCN(nn.Module):
    """
    True Spatial-Temporal GCN for node-level 5-class APT stage classification.

    Architecture:
        x_s = spatial_input_proj(x[:, :-2])   # 76 flow statistics
        x_t = temporal_input_proj(x[:, -2:])  # flow_rank, inter_flow_gap
        x   = x_s + x_t
        for each STConvBlock:
            x = GatedTCN1 â†’ GATConv â†’ GatedTCN2  (+ input residual)
        logits = classifier(output_pool(x))
    """
    def __init__(self, num_features, hidden_dim=128, num_st_blocks=3,
                 dropout=0.5, num_classes=NUM_CLASSES,
                 num_temporal_feats=NUM_TEMPORAL_FEATS):
        super(NodeLevelSTGCN, self).__init__()
        self.num_temporal_feats = num_temporal_feats
        num_spatial_feats       = num_features - num_temporal_feats

        #  Bug 3 fix: separate input projections
        self.spatial_input_proj = nn.Sequential(
            nn.Linear(num_spatial_feats, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        self.temporal_input_proj = nn.Sequential(
            nn.Linear(num_temporal_feats, hidden_dim),
            nn.ReLU()
        )

        #  ST-Conv blocks (temporal-spatial-temporal sandwich)
        self.st_blocks = nn.ModuleList([
            STConvBlock(hidden_dim=hidden_dim, dropout=dropout)
            for _ in range(num_st_blocks)
        ])

        #  Output pool
        self.output_pool = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh()
        )

        #  Classifier head
        # classifier[0] is Linear(hidden_dim, hidden_dim//2) â†’
        # classifier[0].weight.shape[1] == hidden_dim, so the hidden_dim
        # correctness check in main() continues to pass unchanged.
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 4, num_classes)
        )

    def forward(self, x, edge_index, batch=None, temporal_sort_order=None):
        """
        temporal_sort_order: (N,) LongTensor â€” per-node temporal rank within each graph, produced by build_graph_with_custom_k_stgnn.
        """
        # Bug 3 fix: route temporal features separately
        x_s = self.spatial_input_proj(x[:, :-self.num_temporal_feats])
        x_t = self.temporal_input_proj(x[:, -self.num_temporal_feats:])
        x   = x_s + x_t    # additive fusion preserves both gradient paths

        # ST-Conv blocks
        for st_block in self.st_blocks:
            x = st_block(x, edge_index,
                         temporal_sort_order=temporal_sort_order,
                         batch=batch)

        # Classify
        x = self.output_pool(x)
        return self.classifier(x)


class NodeLevelGIN(nn.Module):
    def __init__(self, num_features, hidden_dim=128, dropout=0.5,
                 num_classes=NUM_CLASSES):
        super(NodeLevelGIN, self).__init__()

        # Layer 1: Input â†’ Hidden
        self.conv1 = GINConv(
            nn=nn.Sequential(
                nn.Linear(num_features, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim)
            ),
            train_eps=True
        )
        self.bn1 = nn.BatchNorm1d(hidden_dim)

        # Layer 2: Hidden â†’ Hidden
        self.conv2 = GINConv(
            nn=nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim)
            ),
            train_eps=True
        )
        self.bn2 = nn.BatchNorm1d(hidden_dim)

        # Layer 3: Hidden â†’ Hidden
        self.conv3 = GINConv(
            nn=nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim)
            ),
            train_eps=True
        )

        # Classifier head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes)
        )

        self.dropout = nn.Dropout(dropout)

    def forward(self, x, edge_index, batch=None, temporal_sort_order=None):
        # Layer 1
        x = F.relu(self.bn1(self.conv1(x, edge_index)))
        x = self.dropout(x)

        # Layer 2
        x = F.relu(self.bn2(self.conv2(x, edge_index)))
        x = self.dropout(x)

        # Layer 3
        x = self.conv3(x, edge_index)

        # Classification
        logits = self.classifier(x)
        return logits


# ========================================
# DGI â€” DEEP GRAPH INFOMAX (Self-Supervised Pretraining)
# ========================================

class DGIEncoder(nn.Module):
    def __init__(self, num_features, hidden_dim=128):
        super(DGIEncoder, self).__init__()

        self.conv1 = GCNConv(num_features, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.conv3 = GCNConv(hidden_dim, hidden_dim)
        self.bn1   = nn.BatchNorm1d(hidden_dim)
        self.bn2   = nn.BatchNorm1d(hidden_dim)

    def forward(self, x, edge_index):
        """
        Returns node embeddings, DeepGraphInfomax calls this directly as encoder(x, edge_index).
        """
        x = F.relu(self.bn1(self.conv1(x, edge_index)))
        x = F.relu(self.bn2(self.conv2(x, edge_index)))
        x = self.conv3(x, edge_index)
        return x


def pretrain_with_dgi(train_loader, num_features, device,
                      hidden_dim=128, epochs=50, lr=1e-3,
                      patience=10, verbose=True):
    from torch_geometric.nn import DeepGraphInfomax

    print(f"\n{'='*80}")
    print("DGI PRETRAINING â€” SELF-SUPERVISED ENCODER LEARNING")
    print(f"{'='*80}")
    print(f"  Architecture:  3-layer GCN encoder (hidden_dim={hidden_dim})")
    print(f"  Epochs:        up to {epochs} (early stopping patience={patience})")
    print(f"  Learning rate: {lr}")
    print(f"  Labels used:   NONE â€” purely self-supervised")
    print(f"  Corruption:    random node-feature shuffle per batch")
    print(f"{'='*80}\n")

    # Corruption function: shuffle node features across nodes in the graph.
    def corruption(x, edge_index):
        return x[torch.randperm(x.size(0), device=x.device)], edge_index

    # Summary function: mean-pool node embeddings creates scalar graph summary.
    def summary_fn(z, *args, **kwargs):
        return torch.sigmoid(z.mean(dim=0))

    encoder = DGIEncoder(num_features=num_features, hidden_dim=hidden_dim).to(device)

    dgi = DeepGraphInfomax(
        hidden_channels=hidden_dim,
        encoder=encoder,
        summary=summary_fn,
        corruption=corruption
    ).to(device)

    optimizer = torch.optim.Adam(dgi.parameters(), lr=lr)

    best_loss     = float('inf')
    patience_ctr  = 0
    best_state    = None

    for epoch in range(1, epochs + 1):
        dgi.train()
        total_loss  = 0.0
        total_batches = 0

        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()

            # pos_z: embeddings of real graph
            # neg_z: embeddings of corrupted graph
            pos_z, neg_z, summary = dgi(batch.x, batch.edge_index)
            loss = dgi.loss(pos_z, neg_z, summary)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(dgi.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss    += loss.item()
            total_batches += 1

        avg_loss = total_loss / max(total_batches, 1)

        # Early stopping on DGI loss
        if avg_loss < best_loss:
            best_loss    = avg_loss
            patience_ctr = 0
            # Deep-copy the encoder state at the best point
            best_state = {k: v.clone() for k, v in encoder.state_dict().items()}
        else:
            patience_ctr += 1

        if verbose and epoch % 10 == 0:
            print(f"  DGI Epoch {epoch:3d}/{epochs}: Loss={avg_loss:.4f}  "
                  f"(best={best_loss:.4f}, patience={patience_ctr}/{patience})")

        if patience_ctr >= patience:
            if verbose:
                print(f"  Early stopping at epoch {epoch} "
                      f"(no improvement for {patience} epochs)")
            break

    # Restore best encoder weights
    if best_state is not None:
        encoder.load_state_dict(best_state)

    print(f"\nâœ“ DGI pretraining complete")
    print(f"  Best DGI loss: {best_loss:.4f}")
    print(f"  Encoder is ready for weight transfer into NodeLevelGCN_DGI\n")

    return encoder


class NodeLevelGCN_DGI(nn.Module):
    def __init__(self, num_features, hidden_dim=128, dropout=0.5,
                 pretrained_encoder=None, num_classes=NUM_CLASSES):
        super(NodeLevelGCN_DGI, self).__init__()

        # Convolutional layers
        self.conv1 = GCNConv(num_features, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.conv3 = GCNConv(hidden_dim, hidden_dim)
        self.bn1   = nn.BatchNorm1d(hidden_dim)
        self.bn2   = nn.BatchNorm1d(hidden_dim)

        # Classifier head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes)
        )
        self.dropout = nn.Dropout(dropout)

        #Weight transfer from pretrained encoder
        if pretrained_encoder is not None:
            enc_state = pretrained_encoder.state_dict()
            own_state = self.state_dict()

            transferred, skipped = 0, 0
            for name, param in enc_state.items():
                if name in own_state and own_state[name].shape == param.shape:
                    own_state[name].copy_(param)
                    transferred += 1
                else:
                    skipped += 1

            self.load_state_dict(own_state)
            print(f"  âœ“ GCN-DGI: transferred {transferred} weight tensors "
                  f"from pretrained encoder ({skipped} skipped â€” classifier head)")

    def forward(self, x, edge_index, batch=None, temporal_sort_order=None):
        x = F.relu(self.bn1(self.conv1(x, edge_index)))
        x = self.dropout(x)
        x = F.relu(self.bn2(self.conv2(x, edge_index)))
        x = self.dropout(x)
        x = self.conv3(x, edge_index)
        logits = self.classifier(x)
        return logits


# ========================================
# R-GCN â€” RELATIONAL GRAPH CONVOLUTIONAL NETWORK
# ========================================

class NodeLevelRGCN(nn.Module):
    NUM_RELATIONS = 3   # src-IP=0, dst-IP=1, KNN=2

    def __init__(self, num_features, hidden_dim=128, dropout=0.5,
                 num_relations=None, num_classes=NUM_CLASSES):
        super(NodeLevelRGCN, self).__init__()

        # Allow override but default to the class constant
        nr = num_relations if num_relations is not None else self.NUM_RELATIONS

        # Layer 1: Input
        self.conv1 = RGCNConv(num_features, hidden_dim, num_relations=nr)
        self.bn1   = nn.BatchNorm1d(hidden_dim)

        # Layer 2: Hidden
        self.conv2 = RGCNConv(hidden_dim, hidden_dim, num_relations=nr)
        self.bn2   = nn.BatchNorm1d(hidden_dim)

        # Layer 3: Hidden
        self.conv3 = RGCNConv(hidden_dim, hidden_dim, num_relations=nr)

        # Classifier head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes)
        )

        self.dropout = nn.Dropout(dropout)

    def forward(self, x, edge_index, batch=None, edge_type=None):
        if edge_type is None:
            raise ValueError(
                "NodeLevelRGCN.forward() requires edge_type. "
                "Ensure graphs were built with build_graph_with_custom_k_rgcn "
                "and that for_rgcn=True was passed to the graph builder."
            )

        # Layer 1: Relational message passing + BN + ELU
        x = self.conv1(x, edge_index, edge_type)
        x = F.elu(self.bn1(x))
        x = self.dropout(x)

        # Layer 2: Relational message passing + BN + ELU
        x = self.conv2(x, edge_index, edge_type)
        x = F.elu(self.bn2(x))
        x = self.dropout(x)

        # Layer 3: Relational message passing (no BN, feeds into classifier)
        x = self.conv3(x, edge_index, edge_type)
        x = F.elu(x)

        logits = self.classifier(x)
        return logits

# ========================================
# TRAINING & EVALUATION
# ========================================

def train_node_level(model, train_loader, optimizer, criterion, device,
                     epochs=30, val_loader=None,
                     disable_early_stopping=False):
    """
    Train a node-level GNN model.
    """
    best_loss = float('inf')
    patience = 10
    patience_counter = 0

    for epoch in range(epochs):
        # Training pass
        model.train()
        total_loss = 0
        total_correct = 0
        total_nodes   = 0
        epoch_preds   = []
        epoch_labels  = []

        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            edge_type = getattr(batch, 'edge_type', None)
            tso       = getattr(batch, 'temporal_sort_order', None)
            if edge_type is not None:
                logits = model(batch.x, batch.edge_index, batch.batch, edge_type=edge_type)
            elif tso is not None:
                logits = model(batch.x, batch.edge_index, batch.batch, temporal_sort_order=tso)
            else:
                logits = model(batch.x, batch.edge_index, batch.batch)
            loss = criterion(logits, batch.y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item()
            pred = logits.argmax(dim=1)
            total_correct += (pred == batch.y).sum().item()
            total_nodes += batch.y.size(0)
            epoch_preds.extend(pred.cpu().tolist())
            epoch_labels.extend(batch.y.cpu().tolist())

        avg_train_loss = total_loss / len(train_loader)
        accuracy = total_correct / total_nodes
        # Macro-F1 across all 5 stages
        train_macro_f1 = f1_score(epoch_labels, epoch_preds,
                                   average='macro', zero_division=0)

        # Early-stopping signal: val loss if loader given, else train loss
        if val_loader is not None:
            model.eval()
            val_loss_total = 0
            with torch.no_grad():
                for vbatch in val_loader:
                    vbatch  = vbatch.to(device)
                    ve_type = getattr(vbatch, 'edge_type', None)
                    vtso    = getattr(vbatch, 'temporal_sort_order', None)
                    if ve_type is not None:
                        vlogits = model(vbatch.x, vbatch.edge_index, vbatch.batch, edge_type=ve_type)
                    elif vtso is not None:
                        vlogits = model(vbatch.x, vbatch.edge_index, vbatch.batch, temporal_sort_order=vtso)
                    else:
                        vlogits = model(vbatch.x, vbatch.edge_index, vbatch.batch)
                    val_loss_total += criterion(vlogits, vbatch.y).item()
            monitor_loss = val_loss_total / len(val_loader)
        else:
            monitor_loss = avg_train_loss

        if (epoch + 1) % 5 == 0:
            loss_label = 'Val' if val_loader is not None else 'Train'
            print(f'  Epoch {epoch+1:2d}: TrainLoss={avg_train_loss:.4f} | {loss_label}Loss={monitor_loss:.4f} | Acc={accuracy:.4f} | MacroF1={train_macro_f1:.3f}')

        # Early stopping
        if not disable_early_stopping:
            if monitor_loss < best_loss:
                best_loss = monitor_loss
                patience_counter = 0
            else:
                patience_counter += 1
            if patience_counter >= patience:
                loss_label = 'val' if val_loader is not None else 'train'
                print(f'  Early stopping at epoch {epoch+1} ({loss_label} loss plateau)')
                break


def evaluate_node_level_multiclass(model, test_loader, device, model_name="Model"):
    """
    Multi-class evaluation for 5-stage APT classification.
    """
    model.eval()
    all_preds  = []
    all_labels = []
    all_probs  = []

    with torch.no_grad():
        for batch in test_loader:
            batch     = batch.to(device)
            edge_type = getattr(batch, 'edge_type', None)
            tso       = getattr(batch, 'temporal_sort_order', None)
            if edge_type is not None:
                logits = model(batch.x, batch.edge_index, batch.batch,
                               edge_type=edge_type)
            elif tso is not None:
                logits = model(batch.x, batch.edge_index, batch.batch,
                               temporal_sort_order=tso)
            else:
                logits = model(batch.x, batch.edge_index, batch.batch)

            probs = F.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(batch.y.cpu().numpy())
            all_probs.append(probs.cpu().numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.vstack(all_probs)

    print(f"\n{'='*80}")
    print(f"EVALUATION RESULTS: {model_name}")
    print(f"{'='*80}")

    print(f"\nSample distribution:")
    for cls_idx, cls_name in enumerate(STAGE_NAMES):
        cnt = (all_labels == cls_idx).sum()
        print(f"  [{cls_idx}] {cls_name:<25}: {cnt:,}")

    present_classes = np.unique(all_labels)
    if len(present_classes) < 2:
        print(f"\nWARNING: Only {len(present_classes)} class(es) present in test set")
        return {'model_name': model_name, 'overall_score': 0.0}

    # Per-class classification report
    print(f"\nClassification Report:")
    print(classification_report(
        all_labels, all_preds,
        target_names=STAGE_NAMES,
        labels=list(range(NUM_CLASSES)),
        digits=3,
        zero_division=0
    ))

    # 5Ã—5 Confusion Matrix
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(NUM_CLASSES)))
    print("\n5Ã—5 Confusion Matrix (rows=Actual, cols=Predicted):")
    header = f"{'':>26}" + "".join(f"{n[:6]:>8}" for n in STAGE_NAMES)
    print(header)
    for i, row_name in enumerate(STAGE_NAMES):
        row_str = f"  {row_name:<24}" + "".join(f"{cm[i,j]:>8}" for j in range(NUM_CLASSES))
        print(row_str)

    #  Aggregate metrics
    accuracy          = (all_preds == all_labels).mean()
    macro_prec        = precision_score(all_labels, all_preds, average='macro',    zero_division=0)
    macro_rec         = recall_score(   all_labels, all_preds, average='macro',    zero_division=0)
    macro_f1          = f1_score(       all_labels, all_preds, average='macro',    zero_division=0)
    weighted_prec     = precision_score(all_labels, all_preds, average='weighted', zero_division=0)
    weighted_rec      = recall_score(   all_labels, all_preds, average='weighted', zero_division=0)
    weighted_f1       = f1_score(       all_labels, all_preds, average='weighted', zero_division=0)

    # Multi-class ROC-AUC: one-vs-rest, macro average
    macro_auc = None
    try:
        # roc_auc_score expects probabilities for all classes
        macro_auc = roc_auc_score(
            all_labels, all_probs,
            multi_class='ovr', average='macro',
            labels=list(range(NUM_CLASSES))
        )
    except Exception as e:
        print(f"  âš  ROC-AUC not computed: {e}")

    print(f"\n{'='*80}")
    print("AGGREGATE METRICS  (macro = equal weight per stage)")
    print(f"{'='*80}")
    print(f"{'Metric':<28} {'Score':<10}")
    print("-" * 40)
    print(f"{'Accuracy':<28} {accuracy:<10.4f}")
    print(f"{'Macro Precision':<28} {macro_prec:<10.4f}")
    print(f"{'Macro Recall':<28} {macro_rec:<10.4f}")
    print(f"{'Macro F1':<28} {macro_f1:<10.4f}")
    print(f"{'Weighted F1':<28} {weighted_f1:<10.4f}")
    if macro_auc is not None:
        print(f"{'Macro ROC-AUC (OvR)':<28} {macro_auc:<10.4f}")
    else:
        print(f"{'Macro ROC-AUC (OvR)':<28} {'N/A':<10}")
    print(f"{'='*80}")

    # Overall score (weighted combination)
    score_weights = {
        'macro_precision': 0.2,
        'macro_recall':    0.35,
        'macro_f1':        0.25,
        'macro_roc_auc':   0.2,
    }
    overall_score = 0.0
    total_weight  = 0.0
    for metric, w in score_weights.items():
        if metric == 'macro_precision':
            overall_score += macro_prec * w; total_weight += w
        elif metric == 'macro_recall':
            overall_score += macro_rec * w; total_weight += w
        elif metric == 'macro_f1':
            overall_score += macro_f1 * w; total_weight += w
        elif metric == 'macro_roc_auc' and macro_auc is not None:
            overall_score += macro_auc * w; total_weight += w

    overall_score = overall_score / total_weight if total_weight > 0 else 0.0

    print(f"\n{'='*80}")
    print(f"OVERALL MODEL SCORE: {overall_score:.4f}")
    print(f"{'='*80}\n")

    #  Per-class support counts
    per_class_support = {STAGE_NAMES[i]: int((all_labels == i).sum())
                         for i in range(NUM_CLASSES)}

    results = {
        'model_name':         model_name,
        'accuracy':           accuracy,
        'macro_precision':    macro_prec,
        'macro_recall':       macro_rec,
        'macro_f1':           macro_f1,
        'weighted_precision': weighted_prec,
        'weighted_recall':    weighted_rec,
        'weighted_f1':        weighted_f1,
        'confusion_matrix':   cm.tolist(),
        'per_class_support':  per_class_support,
        'overall_score':      overall_score,
        # Legacy aliases so downstream code referencing 'f1'/'precision'/'recall' still works
        'f1':        macro_f1,
        'precision': macro_prec,
        'recall':    macro_rec,
    }
    if macro_auc is not None:
        results['macro_roc_auc'] = macro_auc
        results['roc_auc']       = macro_auc   # legacy alias

    return results


#  keep the binary variant around for reference / ablation runs
def evaluate_node_level(model, test_loader, device, model_name="Model"):
    """
    DEPRECATED for multi-class pipeline.
    Calls evaluate_node_level_multiclass() so existing call-sites continue
    to work without modification.
    """
    return evaluate_node_level_multiclass(model, test_loader, device, model_name)


def evaluate_node_level_with_threshold(model, test_loader, device, threshold=0.5, model_name="Model"):
    """
    DEPRECATED â€” binary threshold-based evaluation.
    In the multi-class pipeline the decision function is argmax (no threshold).
    This wrapper simply calls evaluate_node_level_multiclass() so existing
    Optuna / evaluation call-sites continue to compile without modification.
    The `threshold` parameter is silently ignored.
    """
    return evaluate_node_level_multiclass(model, test_loader, device, model_name)


def _evaluate_node_level_with_threshold_binary_DEPRECATED(model, test_loader, device, threshold=0.5, model_name="Model"):
    """
    Original binary threshold evaluation â€” kept for reference / ablation.
    """
    model.eval()
    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device)
            edge_type = getattr(batch, 'edge_type', None)
            if edge_type is not None:
                logits = model(batch.x, batch.edge_index, batch.batch,
                               edge_type=edge_type)
            else:
                logits = model(batch.x, batch.edge_index, batch.batch)
            probs = F.softmax(logits, dim=1)[:, 1]
            preds = (probs >= threshold).long()

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(batch.y.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)

    print(f"\n{'='*80}")
    print(f"EVALUATION RESULTS: {model_name}")
    print(f"{'='*80}")
    print(f"Decision threshold: {threshold:.4f}")

    print(f"Total samples: {len(all_labels)}")
    print(f"  APT: {(all_labels==1).sum()}")
    print(f"  Benign: {(all_labels==0).sum()}")

    if len(np.unique(all_labels)) == 1:
        print(f"\nWARNING: Only one class in test set")
        return {'model_name': model_name, 'overall_score': 0.0, 'threshold': threshold}

    print(f"\n")
    print(classification_report(all_labels, all_preds,
                               target_names=['Benign', 'APT'],
                               labels=[0, 1],
                               digits=3,
                               zero_division=0))

    # Confusion Matrix
    cm = confusion_matrix(all_labels, all_preds, labels=[0, 1])
    print("\nConfusion Matrix:")
    print(f"              Predicted")
    print(f"             Benign  APT")
    print(f"Actual Benign  {cm[0,0]:>6}  {cm[0,1]:>5}")
    print(f"       APT     {cm[1,0]:>6}  {cm[1,1]:>5}")

    tn, fp, fn, tp = cm[0,0], cm[0,1], cm[1,0], cm[1,1]

    # Metrics
    precision = precision_score(all_labels, all_preds, average='binary', pos_label=1, zero_division=0)
    recall = recall_score(all_labels, all_preds, average='binary', pos_label=1, zero_division=0)
    f1 = f1_score(all_labels, all_preds, average='binary', pos_label=1, zero_division=0)
    accuracy = (all_preds == all_labels).mean()

    try:
        auc = roc_auc_score(all_labels, all_probs)
    except Exception as e:
        auc = None

    # Display key metrics in a formatted table
    print(f"\n{'='*80}")
    print("KEY METRICS")
    print(f"{'='*80}")
    print(f"{'Metric':<20} {'Score':<10}")
    print("-"*30)
    print(f"{'Accuracy':<20} {accuracy:<10.4f}")
    print(f"{'Precision (APT)':<20} {precision:<10.4f}")
    print(f"{'Recall (APT)':<20} {recall:<10.4f}")
    print(f"{'F1-Score (APT)':<20} {f1:<10.4f}")
    if auc is not None:
        print(f"{'ROC-AUC':<20} {auc:<10.4f}")
    else:
        print(f"{'ROC-AUC':<20} {'N/A':<10}")
    print(f"{'='*80}")

    # Compute overall score
    weights = {'precision': 0.2, 'recall': 0.35, 'f1': 0.25, 'roc_auc': 0.2}
    overall_score = 0.0
    total_weight = 0.0

    for metric, weight in weights.items():
        if metric == 'precision':
            overall_score += precision * weight
            total_weight += weight
        elif metric == 'recall':
            overall_score += recall * weight
            total_weight += weight
        elif metric == 'f1':
            overall_score += f1 * weight
            total_weight += weight
        elif metric == 'roc_auc' and auc is not None:
            overall_score += auc * weight
            total_weight += weight

    overall_score = overall_score / total_weight if total_weight > 0 else 0.0

    print(f"\n{'='*80}")
    print(f"OVERALL MODEL SCORE: {overall_score:.4f}")
    print(f"{'='*80}\n")

    results = {
        'model_name': model_name,
        'threshold': threshold,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'accuracy': accuracy,
        'confusion_matrix': cm.tolist(),
        'confusion_matrix_detailed': {
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_positives': int(tp)
        },
        'false_positives': int(fp),
        'false_negatives': int(fn),
        'support': {
            'benign': int((all_labels == 0).sum()),
            'apt': int((all_labels == 1).sum())
        },
        'overall_score': overall_score
    }

    if auc is not None:
        results['roc_auc'] = auc

    return results


# ========================================
# THRESHOLD OPTIMIZATION MODULE
# ========================================

class ThresholdOptimizer:
    """
    Find optimal decision threshold for binary classification on imbalanced data
    """

    def __init__(self):
        self.results = {}

    def get_predictions_and_labels(self, model, data_loader, device):
        """
        Get probability predictions and true labels from a trained model
        """
        model.eval()
        all_probs = []
        all_labels = []

        with torch.no_grad():
            for batch in data_loader:
                batch = batch.to(device)
                edge_type = getattr(batch, 'edge_type', None)
                if edge_type is not None:
                    logits = model(batch.x, batch.edge_index, batch.batch,
                                   edge_type=edge_type)
                else:
                    logits = model(batch.x, batch.edge_index, batch.batch)
                probs = F.softmax(logits, dim=1)[:, 1]

                all_probs.extend(probs.cpu().numpy())
                all_labels.extend(batch.y.cpu().numpy())

        return np.array(all_probs), np.array(all_labels)

    def evaluate_at_threshold(self, probs, labels, threshold):
        """
        Evaluate metrics at a specific threshold
        """
        preds = (probs >= threshold).astype(int)

        precision = precision_score(labels, preds, zero_division=0)
        recall = recall_score(labels, preds, zero_division=0)
        f1 = f1_score(labels, preds, zero_division=0)
        accuracy = (preds == labels).mean()

        try:
            roc_auc = roc_auc_score(labels, probs)
        except:
            roc_auc = 0.0

        cm = confusion_matrix(labels, preds)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

        # Additional metrics
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0

        # Balanced metric: harmonic mean of recall and (1 - FPR)
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        balanced_score = 2 * (recall * specificity) / (recall + specificity) if (recall + specificity) > 0 else 0

        return {
            'threshold': threshold,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'roc_auc': roc_auc,
            'balanced_score': balanced_score,
            'true_positives': int(tp),
            'false_positives': int(fp),
            'true_negatives': int(tn),
            'false_negatives': int(fn),
            'fpr': fpr,
            'fnr': fnr,
            'specificity': specificity
        }

    def optimize(self, model, data_loader, device,
                 metric='f1',
                 min_recall=None,
                 min_precision=None,
                 threshold_range=(0.1, 0.9),
                 num_thresholds=81,
                 verbose=True):
        """
        Find optimal threshold by testing many threshold values
        """
        if verbose:
            print(f"\n{'='*80}")
            print("THRESHOLD OPTIMIZATION")
            print(f"{'='*80}")
            print(f"Optimization metric: {metric}")
            if min_recall:
                print(f"Minimum recall constraint: {min_recall:.2f}")
            if min_precision:
                print(f"Minimum precision constraint: {min_precision:.2f}")
            print(f"Testing {num_thresholds} thresholds in range [{threshold_range[0]}, {threshold_range[1]}]")
            print(f"{'='*80}\n")

        # Get predictions
        if verbose:
            print("Generating predictions from model...")
        probs, labels = self.get_predictions_and_labels(model, data_loader, device)

        if verbose:
            print(f"âœ“ Generated predictions for {len(labels)} samples")
            print(f"  APT samples: {labels.sum()}")
            print(f"  Benign samples: {len(labels) - labels.sum()}")

        # Test different thresholds
        thresholds = np.linspace(threshold_range[0], threshold_range[1], num_thresholds)
        results = []

        for threshold in thresholds:
            result = self.evaluate_at_threshold(probs, labels, threshold)

            # Apply constraints
            if min_recall and result['recall'] < min_recall:
                continue
            if min_precision and result['precision'] < min_precision:
                continue

            results.append(result)

        if not results:
            print("\nâš  WARNING: No thresholds satisfied the constraints!")
            print("  Try relaxing min_recall or min_precision")
            # Return default threshold
            default_result = self.evaluate_at_threshold(probs, labels, 0.5)
            self.results = {0.5: default_result}
            return 0.5

        # Store all results
        self.results = {r['threshold']: r for r in results}

        # Select best threshold based on metric
        if metric == 'f1':
            best_result = max(results, key=lambda x: x['f1'])
        elif metric == 'balanced':
            best_result = max(results, key=lambda x: x['balanced_score'])
        elif metric == 'precision':
            best_result = max(results, key=lambda x: x['precision'])
        elif metric == 'recall':
            best_result = max(results, key=lambda x: x['recall'])
        else:
            raise ValueError(f"Unknown metric: {metric}")

        optimal_threshold = best_result['threshold']

        if verbose:
            self._print_results(best_result, metric, probs, labels)

        return optimal_threshold

    def _print_results(self, best_result, metric, probs, labels):
        """Print formatted optimization results"""
        print(f"\n{'='*80}")
        print(f"OPTIMIZATION RESULTS (Optimized for {metric.upper()})")
        print(f"{'='*80}")

        print(f"\n OPTIMAL THRESHOLD: {best_result['threshold']:.4f}")
        print(f"\n{'Metric':<25} {'Score':<10}")
        print("-" * 40)
        print(f"{'Accuracy':<25} {best_result['accuracy']:<10.4f}")
        print(f"{'Precision (APT)':<25} {best_result['precision']:<10.4f}")
        print(f"{'Recall (APT)':<25} {best_result['recall']:<10.4f}")
        print(f"{'F1-Score':<25} {best_result['f1']:<10.4f}")
        print(f"{'ROC-AUC':<25} {best_result['roc_auc']:<10.4f}")
        print(f"{'Balanced Score':<25} {best_result['balanced_score']:<10.4f}")

        print(f"\n CONFUSION MATRIX:")
        print(f"{'':>12} Predicted")
        print(f"{'':>12} Benign    APT")
        print(f"Actual Benign  {best_result['true_negatives']:>6}  {best_result['false_positives']:>6}")
        print(f"       APT     {best_result['false_negatives']:>6}  {best_result['true_positives']:>6}")

        print(f"\n  ERROR ANALYSIS:")
        print(f"{'False Positive Rate':<25} {best_result['fpr']:<10.4f}")
        print(f"{'False Negative Rate':<25} {best_result['fnr']:<10.4f}")
        print(f"{'Specificity':<25} {best_result['specificity']:<10.4f}")

        # Compare with default 0.5 threshold
        default_result = self.evaluate_at_threshold(probs, labels, 0.5)
        print(f"\n IMPROVEMENT vs DEFAULT (0.5 threshold):")
        print(f"{'Metric':<20} {'Default':<12} {'Optimized':<12} {'Change':<12}")
        print("-" * 60)

        for metric_name in ['f1', 'precision', 'recall', 'accuracy']:
            default_val = default_result[metric_name]
            optimal_val = best_result[metric_name]
            change = optimal_val - default_val
            change_pct = (change / default_val * 100) if default_val > 0 else 0

            change_str = f"+{change:.4f}" if change >= 0 else f"{change:.4f}"
            change_pct_str = f"({change_pct:+.1f}%)"

            print(f"{metric_name.upper():<20} {default_val:<12.4f} {optimal_val:<12.4f} {change_str:<12} {change_pct_str}")

        print(f"\n{'='*80}\n")

    def plot_threshold_analysis(self, save_path=None):
        """
        Create comprehensive visualization of threshold performance
        """
        if not self.results:
            print("âš  No results to plot. Run optimize() first.")
            return

        thresholds = sorted(self.results.keys())
        metrics_data = {
            'f1': [],
            'precision': [],
            'recall': [],
            'accuracy': [],
            'balanced_score': [],
            'fpr': []
        }

        for t in thresholds:
            r = self.results[t]
            for metric in metrics_data.keys():
                metrics_data[metric].append(r[metric])

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Threshold Optimization Analysis', fontsize=16, fontweight='bold')

        # Plot 1: Main metrics vs threshold
        ax1 = axes[0, 0]
        ax1.plot(thresholds, metrics_data['f1'], 'b-', linewidth=2, label='F1-Score', marker='o', markersize=2)
        ax1.plot(thresholds, metrics_data['precision'], 'g--', linewidth=2, label='Precision', marker='s', markersize=2)
        ax1.plot(thresholds, metrics_data['recall'], 'r--', linewidth=2, label='Recall', marker='^', markersize=2)
        ax1.plot(thresholds, metrics_data['balanced_score'], 'm-', linewidth=2, label='Balanced Score', marker='d', markersize=2)
        ax1.axvline(x=0.5, color='gray', linestyle=':', linewidth=2, label='Default (0.5)')

        # Mark optimal F1
        best_f1_idx = np.argmax(metrics_data['f1'])
        best_f1_threshold = thresholds[best_f1_idx]
        ax1.scatter([best_f1_threshold], [metrics_data['f1'][best_f1_idx]],
                   color='blue', s=200, marker='*', zorder=5,
                   edgecolors='black', linewidths=2, label=f'Best F1 (t={best_f1_threshold:.3f})')

        ax1.set_xlabel('Threshold', fontsize=12)
        ax1.set_ylabel('Score', fontsize=12)
        ax1.set_title('Performance Metrics vs Threshold', fontsize=14, fontweight='bold')
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([thresholds[0], thresholds[-1]])
        ax1.set_ylim([0, 1])

        # Plot 2: Precision-Recall tradeoff
        ax2 = axes[0, 1]
        ax2.plot(metrics_data['recall'], metrics_data['precision'], 'b-', linewidth=2, marker='o', markersize=2)
        ax2.scatter([metrics_data['recall'][best_f1_idx]], [metrics_data['precision'][best_f1_idx]],
                   color='red', s=200, marker='*', zorder=5,
                   edgecolors='black', linewidths=2, label=f'Best F1 (t={best_f1_threshold:.3f})')

        # Mark 0.5 threshold
        idx_05 = min(range(len(thresholds)), key=lambda i: abs(thresholds[i] - 0.5))
        ax2.scatter([metrics_data['recall'][idx_05]], [metrics_data['precision'][idx_05]],
                   color='gray', s=150, marker='D', zorder=4,
                   edgecolors='black', linewidths=2, label='Default (t=0.5)')

        ax2.set_xlabel('Recall', fontsize=12)
        ax2.set_ylabel('Precision', fontsize=12)
        ax2.set_title('Precision-Recall Tradeoff', fontsize=14, fontweight='bold')
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim([0, 1])
        ax2.set_ylim([0, 1])

        # Plot 3: FPR vs Threshold
        ax3 = axes[1, 0]
        ax3.plot(thresholds, metrics_data['fpr'], 'r-', linewidth=2, marker='o', markersize=2, label='False Positive Rate')
        ax3.axvline(x=0.5, color='gray', linestyle=':', linewidth=2, label='Default (0.5)')
        ax3.scatter([best_f1_threshold], [metrics_data['fpr'][best_f1_idx]],
                   color='blue', s=200, marker='*', zorder=5,
                   edgecolors='black', linewidths=2, label=f'Best F1 (t={best_f1_threshold:.3f})')

        ax3.set_xlabel('Threshold', fontsize=12)
        ax3.set_ylabel('False Positive Rate', fontsize=12)
        ax3.set_title('False Positive Rate vs Threshold', fontsize=14, fontweight='bold')
        ax3.legend(loc='best', fontsize=10)
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim([thresholds[0], thresholds[-1]])
        ax3.set_ylim([0, max(metrics_data['fpr']) * 1.1])

        # Plot 4: Summary metrics table
        ax4 = axes[1, 1]
        ax4.axis('off')

        # Create comparison table
        default_idx = idx_05
        table_data = []
        table_data.append(['Metric', 'Default (0.5)', f'Optimized ({best_f1_threshold:.3f})', 'Improvement'])

        for metric_name, display_name in [('f1', 'F1-Score'), ('precision', 'Precision'),
                                          ('recall', 'Recall'), ('accuracy', 'Accuracy')]:
            default_val = metrics_data[metric_name][default_idx]
            optimal_val = metrics_data[metric_name][best_f1_idx]
            improvement = optimal_val - default_val
            improvement_pct = (improvement / default_val * 100) if default_val > 0 else 0

            table_data.append([
                display_name,
                f'{default_val:.4f}',
                f'{optimal_val:.4f}',
                f'{improvement:+.4f} ({improvement_pct:+.1f}%)'
            ])

        table = ax4.table(cellText=table_data, cellLoc='center', loc='center',
                         colWidths=[0.25, 0.25, 0.25, 0.25])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)

        # Style header row
        for i in range(4):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')

        # Alternate row colors
        for i in range(1, len(table_data)):
            for j in range(4):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#f0f0f0')

        ax4.set_title('Performance Comparison', fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"âœ“ Plot saved to: {save_path}")

        plt.show()

        return fig


def optimize_thresholds_for_all_models(models_dict, test_loader, device,
                                      metric='f1', min_recall=None,
                                      save_dir=None, verbose=True,
                                      loaders_dict=None):
    """
    Optimize thresholds for multiple models at once
    """
    optimal_thresholds = {}
    all_results = {}

    print(f"\n{'='*80}")
    print(f"MULTI-MODEL THRESHOLD OPTIMIZATION")
    print(f"{'='*80}")
    print(f"Optimizing thresholds for {len(models_dict)} models")
    print(f"Optimization metric: {metric}")
    if min_recall:
        print(f"Minimum recall constraint: {min_recall:.2f}")
    print(f"{'='*80}\n")

    for model_name, model in models_dict.items():
        print(f"\n{'='*80}")
        print(f"MODEL: {model_name}")
        print(f"{'='*80}")

        # Use per-model loader if available, otherwise fall back to shared loader.
        loader_for_model = (
            loaders_dict[model_name]
            if (loaders_dict and model_name in loaders_dict)
            else test_loader
        )

        optimizer = ThresholdOptimizer()
        optimal_threshold = optimizer.optimize(
            model=model,
            data_loader=loader_for_model,
            device=device,
            metric=metric,
            min_recall=min_recall,
            verbose=verbose
        )

        optimal_thresholds[model_name] = optimal_threshold
        all_results[model_name] = optimizer.results

        # Create plot for this model
        if save_dir:
            import os
            os.makedirs(save_dir, exist_ok=True)
            plot_path = os.path.join(save_dir, f'{model_name}_threshold_analysis.png')
            optimizer.plot_threshold_analysis(save_path=plot_path)

    # Print summary
    print(f"\n{'='*80}")
    print("THRESHOLD OPTIMIZATION SUMMARY")
    print(f"{'='*80}")
    print(f"{'Model':<20} {'Optimal Threshold':<20}")
    print("-" * 40)
    for model_name, threshold in optimal_thresholds.items():
        print(f"{model_name:<20} {threshold:<20.4f}")
    print(f"{'='*80}\n")

    return optimal_thresholds, all_results

# ========================================
# VISUALIZATION FUNCTIONS
# ========================================

def plot_confusion_matrices(all_results):
    """Plot 5Ã—5 confusion matrices for all models"""
    num_models = len(all_results)
    # Each 5Ã—5 CM needs more space than a 2Ã—2
    fig, axes = plt.subplots(1, num_models, figsize=(7 * num_models, 6))

    if num_models == 1:
        axes = [axes]

    short_labels = ['Ben', 'Recon', 'Foot', 'Lat', 'Exfil']

    for idx, (model_name, results) in enumerate(all_results.items()):
        cm = np.array(results['confusion_matrix'])

        # Normalise rows to show recall per class (easier to read at 5Ã—5)
        cm_norm = cm.astype(float)
        row_sums = cm_norm.sum(axis=1, keepdims=True)
        cm_norm  = np.divide(cm_norm, row_sums, where=(row_sums != 0))

        sns.heatmap(cm_norm, annot=True, fmt='.2f', cmap='Blues',
                    ax=axes[idx],
                    xticklabels=short_labels,
                    yticklabels=short_labels,
                    vmin=0, vmax=1,
                    cbar=(idx == num_models - 1))   # only show colorbar on last plot
        axes[idx].set_title(f'{model_name}\n(Score: {results["overall_score"]:.3f})',
                             fontsize=11, fontweight='bold')
        axes[idx].set_ylabel('Actual')
        axes[idx].set_xlabel('Predicted')
        axes[idx].tick_params(axis='both', labelsize=8)

    fig.suptitle('Confusion Matrices â€” Row-Normalised Recall  (5-Stage Classification)',
                  fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig('dapt2020_confusion_matrices.png', dpi=300, bbox_inches='tight')
    print("âœ“ Confusion matrices saved to: dapt2020_confusion_matrices.png")
    plt.show()


def plot_model_comparison(all_results):
    """Enhanced comparison plot â€” macro metrics for 5-class classification"""
    models  = list(all_results.keys())
    metrics = ['accuracy', 'macro_precision', 'macro_recall', 'macro_f1', 'overall_score']

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, metric in enumerate(metrics):
        values = [all_results[model].get(metric, 0) for model in models]
        colors = ['#1f77b4' if metric != 'overall_score' else '#ff7f0e' for _ in models]

        axes[idx].bar(models, values, color=colors)
        axes[idx].set_title(f'{metric.replace("_", " ").title()}', fontsize=12, fontweight='bold')
        axes[idx].set_ylim([0, 1])
        axes[idx].set_ylabel('Score')
        axes[idx].grid(True, alpha=0.3, axis='y')

        for i, v in enumerate(values):
            axes[idx].text(i, v + 0.02, f'{v:.3f}', ha='center', va='bottom')

    # Overall score ranking
    overall_scores = [(model, all_results[model]['overall_score']) for model in models]
    overall_scores.sort(key=lambda x: x[1], reverse=True)

    rank_models = [m for m, _ in overall_scores]
    rank_scores = [s for _, s in overall_scores]

    axes[5].barh(rank_models, rank_scores, color='#2ca02c')
    axes[5].set_title('Overall Score Ranking', fontsize=12, fontweight='bold')
    axes[5].set_xlim([0, 1])
    axes[5].set_xlabel('Overall Score')
    axes[5].grid(True, alpha=0.3, axis='x')

    for i, v in enumerate(rank_scores):
        axes[5].text(v + 0.02, i, f'{v:.3f}', va='center')

    plt.tight_layout()
    plt.savefig('dapt2020_model_comparison.png', dpi=300, bbox_inches='tight')
    print("âœ“ Model comparison saved to: dapt2020_model_comparison.png")
    plt.show()


# ========================================
# FOCAL LOSS FOR CLASS IMBALANCE
# ========================================
#
class FocalLoss(nn.Module):
    """
    Multi-class Focal Loss for addressing severe class imbalance.

    Supports optional per-class weight tensor (like nn.CrossEntropyLoss's
    `weight` parameter) so it integrates cleanly with the 5-class setup.

    Args:
        alpha   : uniform focal modulation scalar (0â€“1).  Does NOT replace
                  per-class weighting â€” use the `weight` tensor for that.
        gamma   : focusing parameter.  gamma=0 reduces to weighted CE loss.
        weight  : optional FloatTensor of shape (NUM_CLASSES,) â€” per-class
                  inverse-frequency weights, same as nn.CrossEntropyLoss.
        reduction: 'mean' | 'sum' | 'none'
    """
    def __init__(self, alpha=0.75, gamma=2.0, reduction='mean', weight=None):
        super(FocalLoss, self).__init__()
        self.alpha     = alpha
        self.gamma     = gamma
        self.reduction = reduction
        self.weight    = weight   # per-class weight tensor (optional)

    def forward(self, inputs, targets):
        # Per-class weighted CE loss (unreduced)
        ce_loss = F.cross_entropy(inputs, targets,
                                  weight=self.weight,
                                  reduction='none')
        # Focal modulation: down-weight easy (high-probability) examples
        pt          = torch.exp(-ce_loss)
        focal_loss  = self.alpha * (1 - pt) ** self.gamma * ce_loss

        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

#Old optimization function before switching to optuna
'''# ========================================
# CLASS WEIGHT OPTIMIZATION MODULE
# ========================================

class WeightExperiment:
    """
    Systematically test different class weights and track performance
    """

    def __init__(self, model_class, num_features, device, model_name="GNN"):
        self.model_class = model_class
        self.num_features = num_features
        self.device = device
        self.model_name = model_name
        self.results = []

    def train_with_weight(self, weight_apt, train_loader, test_loader,
                         epochs=50, lr=0.001, verbose=True):
        """Train model with specific class weight and evaluate"""
        if verbose:
            print(f"\n{'='*60}")
            print(f"Testing APT Weight: {weight_apt:.2f}")
            print(f"{'='*60}")

        model = self.model_class(num_features=self.num_features).to(self.device)
        weight = torch.tensor([1.0, weight_apt], dtype=torch.float32).to(self.device)
        criterion = nn.CrossEntropyLoss(weight=weight)
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

        # Training
        model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch in train_loader:
                batch = batch.to(self.device)
                optimizer.zero_grad()
                edge_type = getattr(batch, 'edge_type', None)
                if edge_type is not None:
                    out = model(batch.x, batch.edge_index, batch.batch,
                                edge_type=edge_type)
                else:
                    out = model(batch.x, batch.edge_index, batch.batch)
                loss = criterion(out, batch.y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if verbose and (epoch + 1) % 10 == 0:
                avg_loss = total_loss / len(train_loader)
                print(f"  Epoch {epoch+1:3d}: Loss = {avg_loss:.4f}")

        # Evaluation
        results = self._evaluate(model, test_loader, weight_apt)
        self.results.append(results)

        if verbose:
            self._print_results(results)

        return results

    def _evaluate(self, model, test_loader, weight_apt):
        """Evaluate model and return metrics"""
        model.eval()

        all_preds = []
        all_probs = []
        all_labels = []

        with torch.no_grad():
            for batch in test_loader:
                batch = batch.to(self.device)
                edge_type = getattr(batch, 'edge_type', None)
                if edge_type is not None:
                    out = model(batch.x, batch.edge_index, batch.batch,
                                edge_type=edge_type)
                else:
                    out = model(batch.x, batch.edge_index, batch.batch)
                probs = F.softmax(out, dim=1)[:, 1]
                preds = (probs > 0.5).long()

                all_probs.extend(probs.cpu().numpy())
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(batch.y.cpu().numpy())

        all_preds = np.array(all_preds)
        all_probs = np.array(all_probs)
        all_labels = np.array(all_labels)

        accuracy = (all_preds == all_labels).mean()
        precision = precision_score(all_labels, all_preds, zero_division=0)
        recall = recall_score(all_labels, all_preds, zero_division=0)
        f1 = f1_score(all_labels, all_preds, zero_division=0)

        try:
            roc_auc = roc_auc_score(all_labels, all_probs)
        except:
            roc_auc = 0.0

        cm = confusion_matrix(all_labels, all_preds)
        tn, fp, fn, tp = cm.ravel()

        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0

        return {
            'weight_apt': weight_apt,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'roc_auc': roc_auc,
            'true_positives': int(tp),
            'false_positives': int(fp),
            'true_negatives': int(tn),
            'false_negatives': int(fn),
            'fpr': fpr,
            'fnr': fnr,
            'total_samples': len(all_labels),
            'apt_samples': int(all_labels.sum()),
            'benign_samples': int(len(all_labels) - all_labels.sum())
        }

    def _print_results(self, results):
        """Print formatted results"""
        print(f"\n RESULTS:")
        print(f"  Accuracy:   {results['accuracy']:.4f}")
        print(f"  Precision:  {results['precision']:.4f}  (â†‘ = fewer false alarms)")
        print(f"  Recall:     {results['recall']:.4f}  (â†‘ = catch more attacks)")
        print(f"  F1-Score:   {results['f1']:.4f}")
        print(f"  False Positives: {results['false_positives']} (benign â†’ APT)")
        print(f"  False Negatives: {results['false_negatives']} (APT â†’ benign)")

    def run_weight_sweep(self, weight_values, train_loader, test_loader, epochs=50, lr=0.001):
        """Test multiple weight values"""
        print(f"\n{'='*80}")
        print(f"CLASS WEIGHT OPTIMIZATION - {self.model_name}")
        print(f"{'='*80}")
        print(f"Testing {len(weight_values)} weights: {weight_values}")
        print(f"{'='*80}")

        for i, weight in enumerate(weight_values, 1):
            print(f"\n[{i}/{len(weight_values)}] ", end="")
            self.train_with_weight(weight, train_loader, test_loader, epochs, lr, verbose=True)

        return self.results

    def get_best_weights(self):
        """Get recommended weights"""
        if not self.results:
            return None

        df = pd.DataFrame(self.results)

        recommendations = {}

        # Best F1
        best_f1_idx = df['f1'].idxmax()
        recommendations['best_f1'] = {
            'weight': float(df.loc[best_f1_idx, 'weight_apt']),
            'f1': float(df.loc[best_f1_idx, 'f1']),
            'precision': float(df.loc[best_f1_idx, 'precision']),
            'recall': float(df.loc[best_f1_idx, 'recall'])
        }

        # Best precision at high recall
        df_high_recall = df[df['recall'] >= 0.95]
        if len(df_high_recall) > 0:
            best_prec_idx = df_high_recall['precision'].idxmax()
            recommendations['best_precision_high_recall'] = {
                'weight': float(df.loc[best_prec_idx, 'weight_apt']),
                'precision': float(df.loc[best_prec_idx, 'precision']),
                'recall': float(df.loc[best_prec_idx, 'recall']),
                'false_positives': int(df.loc[best_prec_idx, 'false_positives'])
            }

        return recommendations

    def print_summary(self):
        """Print summary table"""
        if not self.results:
            return

        df = pd.DataFrame(self.results)

        print(f"\n{'='*90}")
        print(f"OPTIMIZATION SUMMARY - {self.model_name}")
        print(f"{'='*90}")
        print(f"{'Weight':<10} {'Precision':<12} {'Recall':<12} {'F1':<12} {'FP Count':<12}")
        print("-" * 90)

        for _, row in df.iterrows():
            print(f"{row['weight_apt']:<10.2f} {row['precision']:<12.4f} "
                  f"{row['recall']:<12.4f} {row['f1']:<12.4f} {row['false_positives']:<12}")

        print(f"{'='*90}")

        # Show recommendations
        recs = self.get_best_weights()
        if recs:
            print(f"\n RECOMMENDATIONS:")
            print(f"  Best F1: Weight = {recs['best_f1']['weight']:.2f} "
                  f"(F1={recs['best_f1']['f1']:.3f}, P={recs['best_f1']['precision']:.3f}, R={recs['best_f1']['recall']:.3f})")
            if 'best_precision_high_recall' in recs:
                bpr = recs['best_precision_high_recall']
                print(f"  Best Precision @ Recallâ‰¥95%: Weight = {bpr['weight']:.2f} "
                      f"(P={bpr['precision']:.3f}, R={bpr['recall']:.3f}, FP={bpr['false_positives']})")
        print(f"{'='*90}\n")
'''

class GraphVisualizer:
    def __init__(self, output_dir='./graph_visualizations'):
        """Initialize visualizer"""
        self.output_dir = output_dir
        import os
        os.makedirs(output_dir, exist_ok=True)
        print(f"âœ“ Graph Visualizer initialized: {output_dir}")

    def visualize_all_edge_types(self, df_train, edge_index_ip, edge_index_knn,
                                   edge_index_hybrid, feature_cols, X_scaled, k=5,
                                   save_plots=True, display_plots=False):
        """Create comprehensive visualizations for all three edge types"""

        print("\n" + "="*80)
        print("GRAPH STRUCTURE VISUALIZATION - ALL EDGE TYPES")
        print("="*80)

        labels = df_train['MultiLabel'].values if 'MultiLabel' in df_train.columns else None

        self._create_edge_type_comparison(edge_index_ip, edge_index_knn, edge_index_hybrid, labels, save_plots, display_plots)
        print("\n Analyzing IP-based connectivity...")
        self._visualize_ip_edges(df_train, edge_index_ip, labels, save_plots, display_plots)
        print("\n Analyzing KNN-based connectivity...")
        self._visualize_knn_edges(edge_index_knn, X_scaled, feature_cols, labels, k, save_plots, display_plots)
        print("\n Analyzing Hybrid connectivity...")
        self._visualize_hybrid_edges(edge_index_ip, edge_index_knn, edge_index_hybrid, labels, save_plots, display_plots)

        if NETWORKX_AVAILABLE:
            print("\n Creating network structure visualizations...")
            self._visualize_network_structures(edge_index_ip, edge_index_knn, edge_index_hybrid, X_scaled, labels, save_plots, display_plots)

        # NEW: Detailed feature visualizations
        print("\n Creating detailed feature visualizations...")
        self._visualize_node_features(df_train, X_scaled, feature_cols, labels, save_plots, display_plots)

        print("\n Creating example connected flows...")
        self._visualize_example_connections(df_train, edge_index_ip, edge_index_knn, X_scaled, feature_cols, labels, save_plots, display_plots)

        self._print_summary_statistics(edge_index_ip, edge_index_knn, edge_index_hybrid, df_train, labels)

        print("\n" + "="*80)
        print(" VISUALIZATION COMPLETE!")
        print("="*80)
        if save_plots:
            print(f"\n All visualizations saved to: {self.output_dir}/")
        print("\n")

    def _create_edge_type_comparison(self, edge_index_ip, edge_index_knn, edge_index_hybrid, labels, save_plots, display_plots):
        """Create overview comparison of all three edge types"""
        print("\n [1/5] Creating edge type comparison...")

        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle('Graph Structure Comparison: Three Edge Construction Methods', fontsize=16, fontweight='bold', y=0.995)

        edge_types = [('IP-Based', edge_index_ip, 'blue'), ('KNN-Based', edge_index_knn, 'green'), ('Hybrid', edge_index_hybrid, 'purple')]

        for idx, (name, edge_index, color) in enumerate(edge_types):
            degrees = self._calculate_degrees(edge_index)
            axes[0, idx].hist(degrees, bins=50, color=color, alpha=0.7, edgecolor='black')
            axes[0, idx].set_xlabel('Node Degree', fontsize=11)
            axes[0, idx].set_ylabel('Frequency', fontsize=11)
            axes[0, idx].set_title(f'{name}\nDegree Distribution', fontsize=12, fontweight='bold')
            axes[0, idx].axvline(np.mean(degrees), color='red', linestyle='--', label=f'Mean: {np.mean(degrees):.1f}')
            axes[0, idx].legend()
            axes[0, idx].grid(True, alpha=0.3)

            stats = self._get_edge_stats(edge_index, labels)
            categories = ['Total\nEdges', 'Unique\nNodes', 'Avg\nDegree', 'Max\nDegree', 'Density\n(x1000)']
            values = [stats['num_edges']/1000, stats['num_nodes']/100, stats['avg_degree'], stats['max_degree']/10, stats['density']*1000000]

            bars = axes[1, idx].bar(categories, values, color=color, alpha=0.7, edgecolor='black')
            axes[1, idx].set_ylabel('Value (scaled)', fontsize=11)
            axes[1, idx].set_title(f'{name}\nGraph Statistics', fontsize=12, fontweight='bold')
            axes[1, idx].grid(True, alpha=0.3, axis='y')

            for bar, val, cat in zip(bars, values, categories):
                height = bar.get_height()
                if 'Edges' in cat:
                    label = f'{val*1000:.0f}'
                elif 'Nodes' in cat:
                    label = f'{val*100:.0f}'
                elif 'Max' in cat:
                    label = f'{val*10:.0f}'
                elif 'Density' in cat:
                    label = f'{val/1000000:.2e}'
                else:
                    label = f'{val:.1f}'
                axes[1, idx].text(bar.get_x() + bar.get_width()/2., height, label, ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        if save_plots:
            plt.savefig(f'{self.output_dir}/1_edge_type_comparison.png', dpi=300, bbox_inches='tight')
        if display_plots:
            plt.show()
        else:
            plt.close()
        print("  âœ“ Edge type comparison complete")

    def _visualize_ip_edges(self, df_train, edge_index_ip, labels, save_plots, display_plots):
        """Visualize IP-based connectivity patterns"""
        print("  Creating IP connectivity analysis...")

        fig, axes = plt.subplots(2, 2, figsize=(18, 14))
        fig.suptitle('IP-Based Graph Connectivity Analysis', fontsize=16, fontweight='bold', y=0.995)

        src_ip_counts = df_train['Src IP'].value_counts().head(20)
        axes[0, 0].barh(range(len(src_ip_counts)), src_ip_counts.values, color='steelblue', alpha=0.7)
        axes[0, 0].set_yticks(range(len(src_ip_counts)))
        axes[0, 0].set_yticklabels(src_ip_counts.index, fontsize=8)
        axes[0, 0].set_xlabel('Number of Flows', fontsize=11)
        axes[0, 0].set_title('Top 20 Source IPs by Flow Count', fontsize=12, fontweight='bold')
        axes[0, 0].invert_yaxis()
        axes[0, 0].grid(True, alpha=0.3, axis='x')

        dst_ip_counts = df_train['Dst IP'].value_counts().head(20)
        axes[0, 1].barh(range(len(dst_ip_counts)), dst_ip_counts.values, color='coral', alpha=0.7)
        axes[0, 1].set_yticks(range(len(dst_ip_counts)))
        axes[0, 1].set_yticklabels(dst_ip_counts.index, fontsize=8)
        axes[0, 1].set_xlabel('Number of Flows', fontsize=11)
        axes[0, 1].set_title('Top 20 Destination IPs by Flow Count', fontsize=12, fontweight='bold')
        axes[0, 1].invert_yaxis()
        axes[0, 1].grid(True, alpha=0.3, axis='x')

        src_nodes = edge_index_ip[0].numpy()
        edges_per_node = Counter(src_nodes)
        edge_counts = sorted(edges_per_node.values())

        axes[1, 0].hist(edge_counts, bins=50, color='mediumseagreen', alpha=0.7, edgecolor='black')
        axes[1, 0].set_xlabel('Number of Outgoing Edges per Node', fontsize=11)
        axes[1, 0].set_ylabel('Frequency', fontsize=11)
        axes[1, 0].set_title('IP-Based: Outgoing Edge Distribution', fontsize=12, fontweight='bold')
        axes[1, 0].axvline(np.mean(edge_counts), color='red', linestyle='--', label=f'Mean: {np.mean(edge_counts):.1f}')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        if labels is not None:
            src_labels_ip = labels[src_nodes]
            stage_ip_counts = [int(np.sum(src_labels_ip == cls)) for cls in range(NUM_CLASSES)]
            short_names_ip  = ['Ben', 'Recon', 'Foot', 'Lat', 'Exfil']

            bars = axes[1, 1].bar(short_names_ip, stage_ip_counts,
                                   color=STAGE_COLORS, alpha=0.7, edgecolor='black')
            axes[1, 1].set_ylabel('IP-Based Edges (by source stage)', fontsize=11)
            axes[1, 1].set_title('IP-Based Edge Count by Source Stage', fontsize=12, fontweight='bold')
            axes[1, 1].grid(True, alpha=0.3, axis='y')
            total_ip = max(sum(stage_ip_counts), 1)
            for bar, val in zip(bars, stage_ip_counts):
                height = bar.get_height()
                pct = (val / total_ip) * 100
                axes[1, 1].text(bar.get_x() + bar.get_width() / 2., height,
                                 f'{val:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8)

        plt.tight_layout()
        if save_plots:
            plt.savefig(f'{self.output_dir}/2_ip_based_connectivity.png', dpi=300, bbox_inches='tight')
        if display_plots:
            plt.show()
        else:
            plt.close()
        print("  âœ“ IP connectivity analysis complete")

    def _visualize_knn_edges(self, edge_index_knn, X_scaled, feature_cols, labels, k, save_plots, display_plots):
        """Visualize KNN-based connectivity patterns"""
        print("  Creating KNN connectivity analysis...")

        fig, axes = plt.subplots(2, 2, figsize=(18, 14))
        fig.suptitle(f'KNN-Based Graph Connectivity Analysis (k={k})', fontsize=16, fontweight='bold', y=0.995)

        degrees = self._calculate_degrees(edge_index_knn)
        axes[0, 0].hist(degrees, bins=50, color='mediumseagreen', alpha=0.7, edgecolor='black')
        axes[0, 0].set_xlabel('Node Degree', fontsize=11)
        axes[0, 0].set_ylabel('Frequency', fontsize=11)
        axes[0, 0].set_title(f'KNN Degree Distribution (expected ~{k} per node)', fontsize=12, fontweight='bold')
        axes[0, 0].axvline(np.mean(degrees), color='red', linestyle='--', label=f'Mean: {np.mean(degrees):.1f}')
        axes[0, 0].axvline(k, color='orange', linestyle='--', label=f'Expected: {k}')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        n_sample_edges = min(10000, edge_index_knn.shape[1])
        sample_idx = np.random.choice(edge_index_knn.shape[1], n_sample_edges, replace=False)
        src_nodes = edge_index_knn[0, sample_idx].numpy()
        dst_nodes = edge_index_knn[1, sample_idx].numpy()
        distances = np.linalg.norm(X_scaled[src_nodes] - X_scaled[dst_nodes], axis=1)

        axes[0, 1].hist(distances, bins=50, color='skyblue', alpha=0.7, edgecolor='black')
        axes[0, 1].set_xlabel('Euclidean Distance', fontsize=11)
        axes[0, 1].set_ylabel('Frequency', fontsize=11)
        axes[0, 1].set_title(f'KNN Edge Distance Distribution\n(sampled {n_sample_edges:,} edges)', fontsize=12, fontweight='bold')
        axes[0, 1].axvline(np.mean(distances), color='red', linestyle='--', label=f'Mean: {np.mean(distances):.3f}')
        axes[0, 1].axvline(np.median(distances), color='orange', linestyle='--', label=f'Median: {np.median(distances):.3f}')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        print("    Computing t-SNE (this may take a moment)...")
        n_sample_nodes = min(1000, X_scaled.shape[0])
        sample_node_idx = np.random.choice(X_scaled.shape[0], n_sample_nodes, replace=False)
        X_sample = X_scaled[sample_node_idx]

        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, n_sample_nodes-1))
        X_tsne = tsne.fit_transform(X_sample)

        if labels is not None:
            labels_sample = labels[sample_node_idx]
            colors = [STAGE_COLORS[int(l) % NUM_CLASSES] for l in labels_sample]
            axes[1, 0].scatter(X_tsne[:, 0], X_tsne[:, 1], c=colors, s=20, alpha=0.6, edgecolors='k', linewidth=0.5)
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor=STAGE_COLORS[i], edgecolor='k', label=STAGE_NAMES[i])
                                for i in range(NUM_CLASSES)]
            axes[1, 0].legend(handles=legend_elements, loc='best', fontsize=8)
        else:
            axes[1, 0].scatter(X_tsne[:, 0], X_tsne[:, 1], c='steelblue', s=20, alpha=0.6, edgecolors='k', linewidth=0.5)

        axes[1, 0].set_xlabel('t-SNE Dimension 1', fontsize=11)
        axes[1, 0].set_ylabel('t-SNE Dimension 2', fontsize=11)
        axes[1, 0].set_title(f'Feature Space Visualization (t-SNE)\n{n_sample_nodes} sampled nodes', fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3)

        if labels is not None:
            src_nodes_all = edge_index_knn[0].numpy()
            # Count edges where source node belongs to each stage
            src_labels_all = labels[src_nodes_all]
            stage_edge_counts = [int(np.sum(src_labels_all == cls)) for cls in range(NUM_CLASSES)]
            short_names = ['Ben', 'Recon', 'Foot', 'Lat', 'Exfil']

            bars = axes[1, 1].bar(short_names, stage_edge_counts,
                                   color=STAGE_COLORS, alpha=0.7, edgecolor='black')
            axes[1, 1].set_ylabel('KNN Edges (by source stage)', fontsize=11)
            axes[1, 1].set_title('KNN Edge Count by Source Stage', fontsize=12, fontweight='bold')
            axes[1, 1].grid(True, alpha=0.3, axis='y')
            total_edges = max(sum(stage_edge_counts), 1)
            for bar, count in zip(bars, stage_edge_counts):
                height = bar.get_height()
                pct = (count / total_edges) * 100
                axes[1, 1].text(bar.get_x() + bar.get_width() / 2., height,
                                 f'{count:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8)

        plt.tight_layout()
        if save_plots:
            plt.savefig(f'{self.output_dir}/3_knn_based_connectivity.png', dpi=300, bbox_inches='tight')
        if display_plots:
            plt.show()
        else:
            plt.close()
        print("  âœ“ KNN connectivity analysis complete")

    def _visualize_hybrid_edges(self, edge_index_ip, edge_index_knn, edge_index_hybrid, labels, save_plots, display_plots):
        """Visualize hybrid connectivity patterns"""
        print("  Creating Hybrid connectivity analysis...")

        fig, axes = plt.subplots(2, 2, figsize=(18, 14))
        fig.suptitle('Hybrid Graph Connectivity Analysis', fontsize=16, fontweight='bold', y=0.995)

        ip_edges = set(map(tuple, edge_index_ip.T.numpy()))
        knn_edges = set(map(tuple, edge_index_knn.T.numpy()))

        ip_only = len(ip_edges - knn_edges)
        knn_only = len(knn_edges - ip_edges)
        both = len(ip_edges & knn_edges)

        categories = ['IP Only', 'KNN Only', 'Shared\n(IP âˆ© KNN)']
        values = [ip_only, knn_only, both]
        colors_bars = ['steelblue', 'mediumseagreen', 'purple']

        bars = axes[0, 0].bar(categories, values, color=colors_bars, alpha=0.7, edgecolor='black')
        axes[0, 0].set_ylabel('Number of Edges', fontsize=11)
        axes[0, 0].set_title('Edge Overlap Between Methods', fontsize=12, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3, axis='y')

        total = sum(values)
        for bar, val in zip(bars, values):
            height = bar.get_height()
            pct = (val/total)*100
            axes[0, 0].text(bar.get_x() + bar.get_width()/2., height, f'{val:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=10)

        degrees_ip = self._calculate_degrees(edge_index_ip)
        degrees_knn = self._calculate_degrees(edge_index_knn)
        degrees_hybrid = self._calculate_degrees(edge_index_hybrid)

        axes[0, 1].hist(degrees_ip, bins=50, alpha=0.5, color='steelblue', label=f'IP (mean={np.mean(degrees_ip):.1f})')
        axes[0, 1].hist(degrees_knn, bins=50, alpha=0.5, color='mediumseagreen', label=f'KNN (mean={np.mean(degrees_knn):.1f})')
        axes[0, 1].hist(degrees_hybrid, bins=50, alpha=0.5, color='purple', label=f'Hybrid (mean={np.mean(degrees_hybrid):.1f})')
        axes[0, 1].set_xlabel('Node Degree', fontsize=11)
        axes[0, 1].set_ylabel('Frequency', fontsize=11)
        axes[0, 1].set_title('Degree Distribution Comparison', fontsize=12, fontweight='bold')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        methods = ['IP-Based', 'KNN-Based', 'Hybrid']
        edge_counts = [edge_index_ip.shape[1], edge_index_knn.shape[1], edge_index_hybrid.shape[1]]
        colors_bars = ['steelblue', 'mediumseagreen', 'purple']

        bars = axes[1, 0].bar(methods, edge_counts, color=colors_bars, alpha=0.7, edgecolor='black')
        axes[1, 0].set_ylabel('Total Number of Edges', fontsize=11)
        axes[1, 0].set_title('Total Edge Count by Method', fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3, axis='y')

        for bar, count in zip(bars, edge_counts):
            height = bar.get_height()
            axes[1, 0].text(bar.get_x() + bar.get_width()/2., height, f'{count:,}', ha='center', va='bottom', fontsize=11, fontweight='bold')

        unique_ip = len(np.unique(edge_index_ip.numpy()))
        unique_knn = len(np.unique(edge_index_knn.numpy()))
        unique_hybrid = len(np.unique(edge_index_hybrid.numpy()))

        unique_nodes = [unique_ip, unique_knn, unique_hybrid]
        bars = axes[1, 1].bar(methods, unique_nodes, color=colors_bars, alpha=0.7, edgecolor='black')
        axes[1, 1].set_ylabel('Number of Unique Nodes', fontsize=11)
        axes[1, 1].set_title('Nodes with Connections', fontsize=12, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3, axis='y')

        for bar, count in zip(bars, unique_nodes):
            height = bar.get_height()
            axes[1, 1].text(bar.get_x() + bar.get_width()/2., height, f'{count:,}', ha='center', va='bottom', fontsize=11, fontweight='bold')

        plt.tight_layout()
        if save_plots:
            plt.savefig(f'{self.output_dir}/4_hybrid_connectivity.png', dpi=300, bbox_inches='tight')
        if display_plots:
            plt.show()
        else:
            plt.close()
        print("  âœ“ Hybrid connectivity analysis complete")

    def _visualize_network_structures(self, edge_index_ip, edge_index_knn, edge_index_hybrid, X_scaled, labels, save_plots, display_plots):
        """Visualize actual network graph structures (sampled subgraphs)"""
        print("  Creating network structure visualizations...")

        fig, axes = plt.subplots(1, 3, figsize=(24, 8))
        fig.suptitle('Subgraph Structures (50 node samples)', fontsize=16, fontweight='bold', y=0.98)

        edge_types = [('IP-Based', edge_index_ip, 'steelblue'), ('KNN-Based', edge_index_knn, 'mediumseagreen'), ('Hybrid', edge_index_hybrid, 'purple')]

        n_sample = min(50, X_scaled.shape[0])
        sample_nodes = np.random.choice(X_scaled.shape[0], n_sample, replace=False)

        for idx, (name, edge_index, color) in enumerate(edge_types):
            ax = axes[idx]
            G = nx.Graph()
            G.add_nodes_from(sample_nodes)

            src_nodes = edge_index[0].numpy()
            dst_nodes = edge_index[1].numpy()

            for src, dst in zip(src_nodes, dst_nodes):
                if src in sample_nodes and dst in sample_nodes:
                    G.add_edge(src, dst)

            pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)

            if labels is not None:
                node_colors = [STAGE_COLORS[int(labels[node]) % NUM_CLASSES] for node in G.nodes()]
            else:
                node_colors = [color] * len(G.nodes())

            nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=200, alpha=0.7, ax=ax)
            nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.3, width=0.5, ax=ax)

            ax.set_title(f'{name}\n{G.number_of_nodes()} nodes, {G.number_of_edges()} edges', fontsize=12, fontweight='bold')
            ax.axis('off')

            if labels is not None and idx == 0:
                from matplotlib.patches import Patch
                legend_elements = [Patch(facecolor=STAGE_COLORS[i], label=STAGE_NAMES[i])
                                    for i in range(NUM_CLASSES)]
                ax.legend(handles=legend_elements, loc='upper left', fontsize=8)

        plt.tight_layout()
        if save_plots:
            plt.savefig(f'{self.output_dir}/5_network_structures.png', dpi=300, bbox_inches='tight')
        if display_plots:
            plt.show()
        else:
            plt.close()
        print("  âœ“ Network structure visualizations complete")

    def _calculate_degrees(self, edge_index):
        """Calculate node degrees from edge index"""
        nodes = np.concatenate([edge_index[0].numpy(), edge_index[1].numpy()])
        degrees = Counter(nodes)
        max_node = max(degrees.keys()) if degrees else 0
        degree_array = np.array([degrees.get(i, 0) for i in range(max_node + 1)])
        return degree_array

    def _get_edge_stats(self, edge_index, labels):
        """Calculate comprehensive edge statistics"""
        degrees = self._calculate_degrees(edge_index)
        num_nodes = len(degrees)
        num_edges = edge_index.shape[1]

        return {
            'num_edges': num_edges,
            'num_nodes': num_nodes,
            'avg_degree': np.mean(degrees),
            'max_degree': np.max(degrees),
            'min_degree': np.min(degrees),
            'density': num_edges / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0
        }

    def _visualize_node_features(self, df_train, X_scaled, feature_cols, labels, save_plots, display_plots):
        """Visualize actual node feature values - what nodes ARE made of"""
        print("  Creating node feature heatmaps...")

        fig = plt.figure(figsize=(24, 14))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        fig.suptitle('Node Composition: What Nodes Are Actually Made Of (76 Features)',
                     fontsize=16, fontweight='bold')

        # Select top varying features for visualization
        feature_vars = X_scaled.var(axis=0)
        top_20_features = np.argsort(feature_vars)[-20:]
        top_20_names = [feature_cols[i] for i in top_20_features]

        # 1. Feature value heatmap for sample nodes
        ax1 = fig.add_subplot(gs[0, :2])
        n_show = min(50, len(X_scaled))
        sample_idx = np.random.choice(len(X_scaled), n_show, replace=False)
        feature_matrix = X_scaled[sample_idx][:, top_20_features]

        im1 = ax1.imshow(feature_matrix.T, aspect='auto', cmap='RdYlBu_r', vmin=-2, vmax=2)
        ax1.set_xlabel('Node (Flow) Index', fontsize=11)
        ax1.set_ylabel('Feature', fontsize=11)
        ax1.set_title(f'Feature Values for {n_show} Sample Nodes\n(Top 20 Most Varying Features - Standardized)',
                     fontsize=12, fontweight='bold')
        ax1.set_yticks(range(len(top_20_names)))
        ax1.set_yticklabels(top_20_names, fontsize=8)
        cbar1 = plt.colorbar(im1, ax=ax1)
        cbar1.set_label('Standardized Value', fontsize=10)

        # Color-code node columns by stage class
        if labels is not None:
            sample_labels = labels[sample_idx]
            for i, label in enumerate(sample_labels):
                color = STAGE_COLORS[int(label) % NUM_CLASSES]
                ax1.axvline(i, color=color, alpha=0.25, linewidth=2)

        # 2. Feature distribution by stage (most-variant feature)
        ax2 = fig.add_subplot(gs[0, 2])
        if labels is not None:
            important_feat_idx = top_20_features[-1]
            for cls_idx, cls_name in enumerate(STAGE_NAMES):
                cls_mask   = labels == cls_idx
                cls_values = X_scaled[cls_mask, important_feat_idx]
                if len(cls_values) > 0:
                    ax2.hist(cls_values, bins=30, alpha=0.5,
                             color=STAGE_COLORS[cls_idx],
                             label=cls_name[:10], density=True)
            ax2.set_xlabel('Standardized Value', fontsize=11)
            ax2.set_ylabel('Density', fontsize=11)
            ax2.set_title(f'Feature Distribution\n{feature_cols[important_feat_idx]}',
                         fontsize=11, fontweight='bold')
            ax2.legend(fontsize=7)
            ax2.grid(True, alpha=0.3)

        # 3. Example node composition - show actual values for 5 nodes
        ax3 = fig.add_subplot(gs[1, :])
        n_examples = min(5, len(X_scaled))
        example_idx = np.random.choice(len(X_scaled), n_examples, replace=False)
        example_features = X_scaled[example_idx][:, top_20_features]

        x_pos = np.arange(len(top_20_names))
        bar_width = 0.15

        colors_nodes = ['lightblue', 'skyblue', 'steelblue', 'salmon', 'crimson']
        for i in range(n_examples):
            offset = (i - n_examples/2) * bar_width
            label_text = f"Node {example_idx[i]}"
            if labels is not None:
                class_name = "APT" if labels[example_idx[i]] == 1 else "Benign"
                label_text += f" ({class_name})"
            ax3.bar(x_pos + offset, example_features[i], bar_width,
                   label=label_text, alpha=0.8, color=colors_nodes[i])

        ax3.set_xlabel('Feature', fontsize=11)
        ax3.set_ylabel('Standardized Value', fontsize=11)
        ax3.set_title('Example Node Compositions: Actual Feature Values',
                     fontsize=12, fontweight='bold')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(top_20_names, rotation=45, ha='right', fontsize=8)
        ax3.legend(loc='upper right', fontsize=9)
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.axhline(0, color='black', linewidth=0.5)

        # 4. Feature importance for node identity
        ax4 = fig.add_subplot(gs[2, 0])
        feature_importance = feature_vars[top_20_features]
        ax4.barh(range(len(top_20_names)), feature_importance, color='teal', alpha=0.7)
        ax4.set_yticks(range(len(top_20_names)))
        ax4.set_yticklabels(top_20_names, fontsize=8)
        ax4.set_xlabel('Variance', fontsize=11)
        ax4.set_title('Feature Variance\n(Higher = More Distinguishing)',
                     fontsize=11, fontweight='bold')
        ax4.invert_yaxis()
        ax4.grid(True, alpha=0.3, axis='x')

        # 5. Class separation in feature space
        ax5 = fig.add_subplot(gs[2, 1:])
        if labels is not None:
            # Show top 3 most varying features
            top_3_idx = top_20_features[-3:]
            benign_mask = labels == 0
            apt_mask = labels == 1

            for i, feat_idx in enumerate(top_3_idx):
                benign_vals = X_scaled[benign_mask, feat_idx]
                apt_vals = X_scaled[apt_mask, feat_idx]

                pos = i * 2
                bp1 = ax5.boxplot([benign_vals], positions=[pos], widths=0.6,
                                  patch_artist=True, labels=[''])
                bp2 = ax5.boxplot([apt_vals], positions=[pos+0.7], widths=0.6,
                                  patch_artist=True, labels=[''])

                for patch in bp1['boxes']:
                    patch.set_facecolor('lightblue')
                for patch in bp2['boxes']:
                    patch.set_facecolor('salmon')

            ax5.set_xticks([i*2+0.35 for i in range(len(top_3_idx))])
            ax5.set_xticklabels([feature_cols[i] for i in top_3_idx], rotation=15, ha='right', fontsize=9)
            ax5.set_ylabel('Standardized Value', fontsize=11)
            ax5.set_title('Feature Distributions: Benign (Blue) vs APT (Red)\nTop 3 Most Varying Features',
                         fontsize=11, fontweight='bold')
            ax5.grid(True, alpha=0.3, axis='y')

            # Add legend
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='lightblue', label='Benign'),
                Patch(facecolor='salmon', label='APT')
            ]
            ax5.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()
        if save_plots:
            plt.savefig(f'{self.output_dir}/6_node_feature_composition.png', dpi=300, bbox_inches='tight')
        if display_plots:
            plt.show()
        else:
            plt.close()
        print("  âœ“ Node feature composition complete")

    def _visualize_example_connections(self, df_train, edge_index_ip, edge_index_knn,
                                       X_scaled, feature_cols, labels, save_plots, display_plots):
        """Show specific examples of WHY nodes are connected with actual values"""
        print("  Creating example connection analysis...")

        fig = plt.figure(figsize=(24, 16))
        gs = fig.add_gridspec(4, 2, hspace=0.4, wspace=0.3)
        fig.suptitle('Example Connections: Why Specific Nodes Are Connected',
                     fontsize=16, fontweight='bold')

        #IP-BASED CONNECTION EXAMPLES
        ax1 = fig.add_subplot(gs[0, :])
        ax1.axis('off')
        ax1.text(0.5, 0.9, ' IP-Based Edge Examples',
                ha='center', fontsize=14, fontweight='bold', transform=ax1.transAxes)

        # Find IP-based edges and categorize by connection type
        src_nodes = edge_index_ip[0].numpy()
        dst_nodes = edge_index_ip[1].numpy()

        # Separate examples by Source IP matches vs Destination IP matches
        src_ip_matches = []  # Edges where Source IPs match
        dst_ip_matches = []  # Edges where Destination IPs match

        for idx in range(len(src_nodes)):
            src = src_nodes[idx]
            dst = dst_nodes[idx]

            src_ip_src = df_train.iloc[src]['Src IP']
            src_ip_dst = df_train.iloc[src]['Dst IP']
            dst_ip_src = df_train.iloc[dst]['Src IP']
            dst_ip_dst = df_train.iloc[dst]['Dst IP']

            if src_ip_src == dst_ip_src:
                src_ip_matches.append((idx, src, dst, src_ip_src))
            if src_ip_dst == dst_ip_dst:
                dst_ip_matches.append((idx, src, dst, src_ip_dst))

        # Get examples - configurable number
        n_src_examples = min(3, len(src_ip_matches))  # â† CHANGE THIS NUMBER for more Source IP examples
        n_dst_examples = min(3, len(dst_ip_matches))  # â† CHANGE THIS NUMBER for more Dest IP examples

        text_y = 0.75

        # Show Source IP matches
        if len(src_ip_matches) > 0:
            ax1.text(0.05, text_y, ' Source IP Matches:', fontsize=11, fontweight='bold',
                    transform=ax1.transAxes, verticalalignment='top', color='darkblue')
            text_y -= 0.08

            src_ip_examples = np.random.choice(len(src_ip_matches), n_src_examples, replace=False)
            for i in src_ip_examples:
                _, src, dst, shared_ip = src_ip_matches[i]
                class_src = STAGE_NAMES[int(labels[src])] if labels is not None else "Unknown"
                class_dst = STAGE_NAMES[int(labels[dst])] if labels is not None else "Unknown"

                connection_text = f"  Node {src} ({class_src}) â†â†’ Node {dst} ({class_dst})"
                connection_text += f"\n    Both originate from: {shared_ip}"
                ax1.text(0.05, text_y, connection_text, fontsize=9, family='monospace',
                        transform=ax1.transAxes, verticalalignment='top')
                text_y -= 0.12

        # Show Destination IP matches
        if len(dst_ip_matches) > 0:
            text_y -= 0.05  # Extra spacing
            ax1.text(0.05, text_y, 'Destination IP Matches:', fontsize=11, fontweight='bold',
                    transform=ax1.transAxes, verticalalignment='top', color='darkgreen')
            text_y -= 0.08

            dst_ip_examples = np.random.choice(len(dst_ip_matches), n_dst_examples, replace=False)
            for i in dst_ip_examples:
                _, src, dst, shared_ip = dst_ip_matches[i]
                class_src = STAGE_NAMES[int(labels[src])] if labels is not None else "Unknown"
                class_dst = STAGE_NAMES[int(labels[dst])] if labels is not None else "Unknown"

                connection_text = f"  Node {src} ({class_src}) â†â†’ Node {dst} ({class_dst})"
                connection_text += f"\n    Both communicate with: {shared_ip}"
                ax1.text(0.05, text_y, connection_text, fontsize=9, family='monospace',
                        transform=ax1.transAxes, verticalalignment='top')
                text_y -= 0.12

        # ===== KNN-BASED CONNECTION EXAMPLES =====
        ax2 = fig.add_subplot(gs[1, :])
        ax2.axis('off')
        ax2.text(0.5, 0.95, ' KNN-Based Edge Examples',
                ha='center', fontsize=14, fontweight='bold', transform=ax2.transAxes)

        src_nodes_knn = edge_index_knn[0].numpy()
        dst_nodes_knn = edge_index_knn[1].numpy()

        # Get examples - configurable number
        n_examples_knn = min(5, len(src_nodes_knn))  # â† CHANGE THIS NUMBER for more KNN examples
        example_indices_knn = np.random.choice(len(src_nodes_knn), n_examples_knn, replace=False)

        text_y = 0.85
        for idx in example_indices_knn:
            src = src_nodes_knn[idx]
            dst = dst_nodes_knn[idx]

            # Calculate actual distance
            distance = np.linalg.norm(X_scaled[src] - X_scaled[dst])

            # Find top features contributing to similarity
            feature_diff = np.abs(X_scaled[src] - X_scaled[dst])
            similar_features_idx = np.argsort(feature_diff)[:5]  # Most similar features
            different_features_idx = np.argsort(feature_diff)[-5:]  # Most different features

            class_src = STAGE_NAMES[int(labels[src])] if labels is not None else "Unknown"
            class_dst = STAGE_NAMES[int(labels[dst])] if labels is not None else "Unknown"

            connection_text = f"Node {src} ({class_src}) â†â†’ Node {dst} ({class_dst})\n"
            #connection_text += f"  Distance: {distance:.4f} | "
            connection_text += f"Similar: {', '.join([feature_cols[i][:18] for i in similar_features_idx[:3]])}\n"
            connection_text += f"  Different: {', '.join([feature_cols[i][:18] for i in different_features_idx[-3:]])}"

            ax2.text(0.05, text_y, connection_text, fontsize=9, family='monospace',
                    transform=ax2.transAxes, verticalalignment='top')
            text_y -= 0.17  # Spacing between examples

        #FEATURE COMPARISON FOR KNN PAIR
        if len(example_indices_knn) > 0:
            idx = example_indices_knn[0]
            src = src_nodes_knn[idx]
            dst = dst_nodes_knn[idx]

            # Show top varying features
            feature_vars = X_scaled.var(axis=0)
            top_features = np.argsort(feature_vars)[-15:]
            top_names = [feature_cols[i] for i in top_features]

            ax3 = fig.add_subplot(gs[2, :])
            x_pos = np.arange(len(top_names))
            bar_width = 0.35

            src_values = X_scaled[src, top_features]
            dst_values = X_scaled[dst, top_features]

            ax3.bar(x_pos - bar_width/2, src_values, bar_width,
                   label=f'Node {src} ({STAGE_NAMES[int(labels[src])]})',
                   alpha=0.8, color='steelblue')
            ax3.bar(x_pos + bar_width/2, dst_values, bar_width,
                   label=f'Node {dst} ({STAGE_NAMES[int(labels[dst])]})',
                   alpha=0.8, color='coral')

            ax3.set_xlabel('Feature', fontsize=11)
            ax3.set_ylabel('Standardized Value', fontsize=11)
            ax3.set_title(f'Feature-by-Feature Comparison: KNN Connected Pair\nDistance: {np.linalg.norm(X_scaled[src] - X_scaled[dst]):.4f}',
                         fontsize=12, fontweight='bold')
            ax3.set_xticks(x_pos)
            ax3.set_xticklabels(top_names, rotation=45, ha='right', fontsize=8)
            ax3.legend()
            ax3.grid(True, alpha=0.3, axis='y')
            ax3.axhline(0, color='black', linewidth=0.5)

            #FEATURE DIFFERENCE HEATMAP
            ax4 = fig.add_subplot(gs[3, 0])
            feature_diff = np.abs(X_scaled[src] - X_scaled[dst])
            top_20_diff = np.argsort(feature_diff)[-20:]
            diff_values = feature_diff[top_20_diff]
            diff_names = [feature_cols[i] for i in top_20_diff]

            colors_diff = ['lightgreen' if d < 0.5 else 'orange' if d < 1.0 else 'red'
                          for d in diff_values]
            ax4.barh(range(len(diff_names)), diff_values, color=colors_diff, alpha=0.7)
            ax4.set_yticks(range(len(diff_names)))
            ax4.set_yticklabels(diff_names, fontsize=8)
            ax4.set_xlabel('Absolute Difference', fontsize=11)
            ax4.set_title('Feature Differences\n(Green=Similar, Red=Different)',
                         fontsize=11, fontweight='bold')
            ax4.invert_yaxis()
            ax4.grid(True, alpha=0.3, axis='x')

            #WHY THIS PAIR IS CONNECTED
            ax5 = fig.add_subplot(gs[3, 1])
            ax5.axis('off')

            distance = np.linalg.norm(X_scaled[src] - X_scaled[dst])
            similar_features_idx = np.argsort(feature_diff)[:10]

            explanation = f"Why Node {src} and Node {dst} are KNN-connected:\n\n"
            explanation += f"Overall Distance: {distance:.4f}\n"
            explanation += f"(Lower = more similar)\n\n"
            explanation += "Top 5 Most Similar Features:\n"
            for i, feat_idx in enumerate(similar_features_idx[:5], 1):
                feat_name = feature_cols[feat_idx]
                diff = feature_diff[feat_idx]
                val_src = X_scaled[src, feat_idx]
                val_dst = X_scaled[dst, feat_idx]
                explanation += f"{i}. {feat_name[:25]}\n"
                explanation += f"   Diff: {diff:.3f} | Values: {val_src:.2f}, {val_dst:.2f}\n"

            ax5.text(0.05, 0.95, explanation, fontsize=9, family='monospace',
                    transform=ax5.transAxes, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.tight_layout()
        if save_plots:
            plt.savefig(f'{self.output_dir}/7_example_connections.png', dpi=300, bbox_inches='tight')
        if display_plots:
            plt.show()
        else:
            plt.close()
        print("  âœ“ Example connections complete")

    def _print_summary_statistics(self, edge_index_ip, edge_index_knn, edge_index_hybrid, df_train, labels):
        """Print comprehensive summary statistics"""
        print("\n" + "="*80)
        print("GRAPH STRUCTURE SUMMARY STATISTICS")
        print("="*80)

        print("\n Dataset Overview:")
        print(f"  â€¢ Total flows: {len(df_train):,}")
        if labels is not None:
            for cls_idx, cls_name in enumerate(STAGE_NAMES):
                cnt = np.sum(labels == cls_idx)
                print(f"  â€¢ [{cls_idx}] {cls_name:<25}: {cnt:,} ({cnt/len(labels)*100:.1f}%)")

        methods = [('IP-Based', edge_index_ip), ('KNN-Based', edge_index_knn), ('Hybrid', edge_index_hybrid)]

        for name, edge_index in methods:
            print(f"\n {name} Statistics:")
            stats = self._get_edge_stats(edge_index, labels)
            print(f"  â€¢ Total edges: {stats['num_edges']:,}")
            print(f"  â€¢ Unique nodes: {stats['num_nodes']:,}")
            print(f"  â€¢ Average degree: {stats['avg_degree']:.2f}")
            print(f"  â€¢ Max degree: {stats['max_degree']:.0f}")
            print(f"  â€¢ Graph density: {stats['density']:.6f}")

        ip_edges = set(map(tuple, edge_index_ip.T.numpy()))
        knn_edges = set(map(tuple, edge_index_knn.T.numpy()))
        overlap = len(ip_edges & knn_edges)

        print(f"\n Edge Overlap Analysis:")
        print(f"  â€¢ IP-only edges: {len(ip_edges - knn_edges):,}")
        print(f"  â€¢ KNN-only edges: {len(knn_edges - ip_edges):,}")
        print(f"  â€¢ Shared edges: {overlap:,}")
        print(f"  â€¢ Overlap percentage: {overlap/max(len(ip_edges), len(knn_edges))*100:.2f}%")
        print("\n" + "="*80)


def create_graph_visualizations_integrated(train_df, feature_cols, scaler, output_dir=None):
    print(f"\n{'='*80}")
    print("CREATING GRAPH STRUCTURE VISUALIZATIONS")
    print(f"{'='*80}")
    print("\nGenerating visualizations for three edge construction methods:")
    print("  1. IP-based connectivity (shared IPs)")
    print("  2. KNN-based connectivity (feature similarity)")
    print("  3. Hybrid connectivity (IP + KNN combined)")
    print(f"{'='*80}\n")

    # Determine output directory
    if output_dir is None:
        output_dir = colab_path('graph_visualizations')

    # Sample data if too large
    max_flows = 5000
    if len(train_df) > max_flows:
        print(f" Sampling {max_flows:,} flows from {len(train_df):,} total for visualization")
        sample_df = train_df.sample(n=max_flows, random_state=42).copy()
    else:
        sample_df = train_df.copy()

    X = sample_df[feature_cols].values
    X_scaled = scaler.transform(X)
    print(f"âœ“ Prepared {len(sample_df):,} flows with {len(feature_cols)} features")

    # Create IP-based edges
    print("\n Creating IP-based edges...")
    edge_list_ip = []
    sample_df_indexed = sample_df.reset_index(drop=True)

    src_ip_groups = sample_df_indexed.groupby('Src IP').groups
    for src_ip, indices in src_ip_groups.items():
        indices = list(indices)
        for i in range(len(indices) - 1):
            edge_list_ip.append([indices[i], indices[i+1]])
            edge_list_ip.append([indices[i+1], indices[i]])

    dst_ip_groups = sample_df_indexed.groupby('Dst IP').groups
    for dst_ip, indices in dst_ip_groups.items():
        indices = list(indices)
        for i in range(len(indices) - 1):
            edge_list_ip.append([indices[i], indices[i+1]])
            edge_list_ip.append([indices[i+1], indices[i]])

    edge_list_ip = list(set(map(tuple, edge_list_ip)))
    edge_index_ip = torch.tensor(list(edge_list_ip), dtype=torch.long).t().contiguous()
    print(f"  âœ“ Created {edge_index_ip.shape[1]:,} IP-based edges")

    # Create KNN-based edges
    print("\n Creating KNN-based edges...")
    k = 5
    knn = NearestNeighbors(n_neighbors=k+1, metric='euclidean')
    knn.fit(X_scaled)
    distances, indices = knn.kneighbors(X_scaled)

    edge_list_knn = []
    for i in range(len(X_scaled)):
        for j in indices[i, 1:]:
            edge_list_knn.append([i, j])

    edge_index_knn = torch.tensor(edge_list_knn, dtype=torch.long).t().contiguous()
    print(f"  âœ“ Created {edge_index_knn.shape[1]:,} KNN-based edges (k={k})")

    # Create Hybrid edges
    print("\n Creating Hybrid edges...")
    edge_set_hybrid = set(map(tuple, edge_list_ip)) | set(map(tuple, edge_list_knn))
    edge_index_hybrid = torch.tensor(list(edge_set_hybrid), dtype=torch.long).t().contiguous()
    print(f"  âœ“ Created {edge_index_hybrid.shape[1]:,} Hybrid edges")

    # Generate visualizations
    print(f"\n{'='*80}")
    print("GENERATING VISUALIZATIONS")
    print(f"{'='*80}")
    print("\nThis will create 7 comprehensive visualization files...")
    print("(This may take 2-3 minutes due to t-SNE computation)")

    try:
        visualizer = GraphVisualizer(output_dir=output_dir)
        visualizer.visualize_all_edge_types(
            df_train=sample_df_indexed,
            edge_index_ip=edge_index_ip,
            edge_index_knn=edge_index_knn,
            edge_index_hybrid=edge_index_hybrid,
            feature_cols=feature_cols,
            X_scaled=X_scaled,
            k=k,
            save_plots=True,
            display_plots=False
        )

        print(f"\n{'='*80}")
        print(" GRAPH VISUALIZATIONS COMPLETE!")
        print(f"{'='*80}")
        print(f"\n All visualizations saved to: {output_dir}/")
        print("\nGenerated files:")
        print("  1. edge_type_comparison.png - Overview of all 3 methods")
        print("  2. ip_based_connectivity.png - IP connectivity analysis")
        print("  3. knn_based_connectivity.png - KNN connectivity analysis")
        print("  4. hybrid_connectivity.png - Hybrid method analysis")
        if NETWORKX_AVAILABLE:
            print("  5. network_structures.png - Actual graph visualizations")
        print("  6. node_feature_composition.png - What nodes ARE (76 features)")
        print("  7. example_connections.png - Why specific nodes connect")
        print(f"\n{'='*80}\n")

    except Exception as e:
        print(f"\n  Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()

# ========================================
# MAIN EXECUTION
# ========================================

def main(max_files=None, sample_rate=None, strategy='hybrid', merge_networks=False):
    """Main execution pipeline for DAPT2020"""

    # Reset all RNG sources at pipeline entry
    # across repeated runs and multi-seed experiments.
    set_global_seeds(GLOBAL_SEED)

    runtime_profile = resolve_runtime_profile(max_files=max_files, sample_rate=sample_rate)

    config = {
        'execution_profile': runtime_profile['profile'],
        'max_files': runtime_profile['max_files'],
        'sample_rate': runtime_profile['sample_rate'],
        'flows_per_graph': runtime_profile['flows_per_graph'],
        'batch_size': runtime_profile['batch_size'],
        'learning_rate': 0.0005,
        'epochs': runtime_profile['train_epochs'],
        'optuna_trials': runtime_profile['optuna_trials'],
        'run_optuna_optimization': runtime_profile['run_optuna_optimization'],
        'fresh_study': runtime_profile['fresh_study'],
        'run_dgi_pretraining': runtime_profile['run_dgi_pretraining'],
        'dgi_pretrain_epochs': runtime_profile['dgi_pretrain_epochs'],
        'split_strategy': strategy,
        'n_blocks': runtime_profile['n_blocks'],
        'merge_networks': merge_networks,
        'device': torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    }

    print(f"\n{'='*80}")
    print("DAPT2020 GNN PIPELINE - 5 MODELS")
    print(f"{'='*80}")
    print(f"Device: {config['device']}")
    print(f"Profile: {config['execution_profile']}")
    print(f"Max files: {'ALL' if config['max_files'] is None else config['max_files']}")
    print(f"Sample rate: {config['sample_rate']*100:.0f}%")
    print(f"Split strategy: {strategy}")
    print(f"Merge networks: {merge_networks}")
    print(f"Train epochs: {config['epochs']}")
    print(f"DGI pretraining: {config['run_dgi_pretraining']} ({config['dgi_pretrain_epochs']} epochs)")
    print(f"Optuna enabled: {config['run_optuna_optimization']}")
    if config['run_optuna_optimization']:
        print(f"Optuna trials per model: {config['optuna_trials']}")
    print(f"Run output directory: {LOCAL_RUN_OUTPUT_DIR}")
    print(f"{'='*80}\n")

    try:
        # Load data
        df, feature_cols, identifier_cols = load_dapt2020_with_network_context(
            max_files=config['max_files'],
            sample_rate=config['sample_rate'],
            merge_networks=config['merge_networks']
        )
        '''#EDA
        generate_figures_1_and_2(df, save_dir=results_dir)
        plot_figure_6(df)
        generate_figures_7_8_9(df)
        generate_figures_10_11_12(df)
        generate_figures_13_to_17(df)'''

        # Stratified temporal split BY NETWORK TYPE
        # Three-way split: train / val / test
        train_df, val_df, test_df, scaler, feature_cols = stratified_temporal_split_by_network(
            df,
            feature_cols,
            val_size=0.15,
            test_size=0.15,
            n_blocks=config['n_blocks'],
            strategy=config['split_strategy']
        )

        # Create network-aware graphs (SEPARATE FAMILIES)
        train_graphs, train_public, train_private = create_network_aware_graphs(
            train_df,
            feature_cols,
            flows_per_graph=config['flows_per_graph']
        )

        val_graphs, val_public, val_private = create_network_aware_graphs(
            val_df,
            feature_cols,
            flows_per_graph=config['flows_per_graph']
        )

        test_graphs, test_public, test_private = create_network_aware_graphs(
            test_df,
            feature_cols,
            flows_per_graph=config['flows_per_graph']
        )

        # Data loaders â€” generator pins shuffle ordering to GLOBAL_SEED
        _g = torch.Generator()
        _g.manual_seed(GLOBAL_SEED)
        train_loader = DataLoader(train_graphs, batch_size=config['batch_size'],
                                  shuffle=True,  generator=_g)
        val_loader   = DataLoader(val_graphs,   batch_size=config['batch_size'],
                                  shuffle=False)
        test_loader  = DataLoader(test_graphs,  batch_size=config['batch_size'],
                                  shuffle=False)

        print(f"\n{'='*80}")
        print("DATA LOADERS READY")
        print(f"{'='*80}")
        print(f"Training batches:   {len(train_loader)}")
        print(f"  Public graphs:    {len(train_public)}")
        print(f"  Private graphs:   {len(train_private)}")
        print(f"Validation batches: {len(val_loader)}")
        print(f"  Public graphs:    {len(val_public)}")
        print(f"  Private graphs:   {len(val_private)}")
        print(f"Test batches:       {len(test_loader)}  â† sealed until final eval")
        print(f"  Public graphs:    {len(test_public)}")
        print(f"  Private graphs:   {len(test_private)}")
        print(f"{'='*80}\n")

        device = config['device']
        num_features = train_graphs[0].x.shape[1]
        print(f"âœ“ num_features = {num_features}  "
              f"({len(feature_cols)} global-scaled + 2 graph-local temporal)")

        # DGI PRETRAINING (runs once before Optuna/training)
        # Set RUN_DGI_PRETRAINING = False to skip and fall back torandom init for GCN-DGI
        RUN_DGI_PRETRAINING = config['run_dgi_pretraining']

        if RUN_DGI_PRETRAINING:
            print(f"\n{'='*80}")
            print("PHASE 0: DGI SELF-SUPERVISED PRETRAINING")
            print(f"{'='*80}")
            print("Pretraining a GCN encoder on graph structure BEFORE")
            print("any supervised training begins. No labels are used.")
            print("The pretrained weights will initialise GCN-DGI only.")
            print("All other 4 models are completely unaffected.")
            print(f"{'='*80}\n")

            # This value is used in THREE places that must stay in sync: 1. pretrain_with_dgi(), 2. Optuna trials for GCN-DGI, 3. Final training of GCN-DGI
            DGI_PRETRAIN_HIDDEN_DIM = 128

            dgi_pretrained_encoder = pretrain_with_dgi(
                train_loader   = train_loader,
                num_features   = num_features,
                device         = device,
                hidden_dim     = DGI_PRETRAIN_HIDDEN_DIM,
                epochs         = config['dgi_pretrain_epochs'],
                lr             = 1e-3,
                patience       = 10,
                verbose        = True
            )

            # Save encoder weights so Optuna trials can reload them
            dgi_encoder_path = colab_path('dgi_pretrained_encoder.pt')
            torch.save(dgi_pretrained_encoder.state_dict(), dgi_encoder_path)
            print(f"âœ“ Pretrained encoder weights saved to: {dgi_encoder_path}")

        else:
            print(f"\n{'='*80}")
            print("DGI PRETRAINING SKIPPED")
            print(f"{'='*80}")
            print("GCN-DGI will use random initialisation (same as plain GCN).")
            print("Set RUN_DGI_PRETRAINING = True to enable pretraining.")
            print(f"{'='*80}\n")

            dgi_pretrained_encoder = None
            dgi_encoder_path       = None
            DGI_PRETRAIN_HIDDEN_DIM = 128   # default; not used for pretraining since it's skipped

        # 5 models to train
        models_config = [
            {'name': 'GATv2',    'class': NodeLevelGATv2},
            {'name': 'RGCN',     'class': NodeLevelRGCN},
            {'name': 'ST-GCN',   'class': NodeLevelSTGCN},
            {'name': 'GIN',      'class': NodeLevelGIN},
            {'name': 'GCN-DGI', 'class': NodeLevelGCN_DGI},
        ]

        all_results = {}

        RUN_OPTUNA_OPTIMIZATION = config['run_optuna_optimization']

        # FRESH_STUDY
        # Controls whether Optuna starts from a clean slate or loads prior
        # trial history from the SQLite DB on Drive.
        FRESH_STUDY = config['fresh_study']

        # Dictionary to store optimal parameters for each model
        all_optuna_results = {}

        if RUN_OPTUNA_OPTIMIZATION:
            print(f"\n{'='*80}")

        if RUN_OPTUNA_OPTIMIZATION:
            print(f"\n{'='*80}")
            print(" OPTUNA OPTIMIZATION - ENHANCED WITH 8 HYPERPARAMETERS")
            print(f"{'='*80}")
            print("\nThis will optimize hyperparameters separately for each model:")
            print("  â€¢ GATv2     (Graph Attention Network v2 â€” dynamic attention)")
            print("  â€¢ RGCN      (Relational GCN â€” typed edges: src-IP, dst-IP, KNN)")
            print("  â€¢ ST-GCN    (Spatial-Temporal GNN)")
            print("  â€¢ GIN       (Graph Isomorphism Network)")
            print("  â€¢ GCN-DGI   (GCN with DGI-pretrained weights)")
            print("\nEach model optimizes 8 hyperparameters:")
            print("  â€¢ Class Weights (APT Weight)")
            print("  â€¢ KNN k-value")
            print("  â€¢ Learning Rate")
            print("  â€¢ Dropout Rate")
            print("  â€¢ Decision Threshold")
            print("  â€¢ Hidden Dimension")
            print("  â€¢ Batch Size")
            print("  â€¢ Weight Decay")
            total_trials = config['optuna_trials'] * len(models_config)
            print(f"\nOptimization: {config['optuna_trials']} trial(s) per model ({total_trials} total)")
            print(f"{'='*80}\n")

            # Models to optimize
            models_to_optimize = [
                {'name': 'GATv2',    'class': NodeLevelGATv2},
                {'name': 'RGCN',     'class': NodeLevelRGCN},
                {'name': 'ST-GCN',   'class': NodeLevelSTGCN},
                {'name': 'GIN',      'class': NodeLevelGIN},
                {'name': 'GCN-DGI', 'class': NodeLevelGCN_DGI},
            ]

            # Optimize each model separately
            for model_idx, model_info in enumerate(models_to_optimize):
                model_name = model_info['name']
                model_class = model_info['class']

                print(f"\n{'='*80}")
                print(f"OPTIMIZING MODEL {model_idx+1}/5: {model_name}")
                print(f"{'='*80}")
                print(f"Progress: Model {model_idx+1} of 5")
                print(f"Trials per model: {config['optuna_trials']}")
                print(f"Hyperparameters: 8 (5 original + 3 new)")
                print(f"{'='*80}\n")

                try:
                    # Define model-specific objective function
                    def create_objective_for_model(m_class, m_name, enc_path=None):
                        """Create objective function for specific model.

                        enc_path: path to saved DGI encoder weights (GCN-DGI only).
                                  If supplied, each trial loads these weights before
                                  fine-tuning â€” no retraining of the encoder per trial.

                        TEMPORAL LEAKAGE NOTES
                        â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                        â€¢ Graphs are built only from train_df / val_df â€” test_df is sealed.
                        â€¢ Class weights are derived from train_df labels ONLY.  Val / test
                          label frequencies never influence the weight tensor.
                        â€¢ `decision_threshold` (binary) has been removed; multi-class uses
                          argmax, which requires no threshold parameter.
                        """
                        def optuna_objective(trial):
                            # â”€â”€ HYPERPARAMETER SUGGESTIONS (7 TOTAL) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                            # Removed: apt_weight (binary), decision_threshold (binary)
                            # Added:   minority_weight_scale (multi-class generalisation)

                            # Scale factor applied to all non-benign class weights.
                            # Base weights are inverse-frequency from train_df labels only.
                            minority_weight_scale = trial.suggest_float(
                                'minority_weight_scale', 1.0, 15.0, log=True)

                            k_value       = trial.suggest_int('k_value', 3, 20)
                            learning_rate = trial.suggest_float('learning_rate', 1e-4, 1e-2, log=True)
                            dropout_rate  = trial.suggest_float('dropout_rate', 0.2, 0.7)
                            hidden_dim    = trial.suggest_categorical('hidden_dim', [64, 128, 256])
                            batch_size    = trial.suggest_categorical('batch_size', [2, 4, 8, 16])
                            weight_decay  = trial.suggest_float('weight_decay', 1e-5, 1e-2, log=True)

                            # ST-GCN only: temporal window width (number of predecessors
                            # and successors each flow sees in sorted time).
                            if m_name == 'ST-GCN':
                                temporal_k = trial.suggest_int('temporal_k', 2, 8)
                            else:
                                temporal_k = 4  # unused default for other models

                            # GCN-DGI: encoder was pretrained with DGI_PRETRAIN_HIDDEN_DIM.
                            if m_name == 'GCN-DGI':
                                hidden_dim = DGI_PRETRAIN_HIDDEN_DIM

                            print(f"\n[{m_name} Trial {trial.number}]")
                            print(f"  Minority Weight Scale: {minority_weight_scale:.3f}")
                            print(f"  K-value:       {k_value}")
                            if m_name == 'ST-GCN':
                                print(f"  Temporal K:    {temporal_k}")
                            print(f"  Learning Rate: {learning_rate:.6f}")
                            print(f"  Dropout:       {dropout_rate:.3f}")
                            print(f"  Hidden Dim:    {hidden_dim}")
                            print(f"  Batch Size:    {batch_size}")
                            print(f"  Weight Decay:  {weight_decay:.6f}")

                            try:
                                # BUILD GRAPHS WITH SUGGESTED K-VALUE
                                # ST-GCN: use the dedicated builder (temporal edges +
                                #   temporal_sort_order).
                                # RGCN:   needs typed edges from the dedicated builder.
                                # Others: standard KNN+IP builder.
                                is_rgcn   = (m_name == 'RGCN')
                                is_stgcn  = (m_name == 'ST-GCN')
                                if is_stgcn:
                                    print(f"  Building ST-GCN graphs with "
                                          f"k={k_value}, temporal_k={temporal_k}...")
                                    train_graphs_trial, _, _ = create_stgnn_graphs_with_k(
                                        train_df, feature_cols,
                                        flows_per_graph=config['flows_per_graph'],
                                        k=k_value, temporal_k=temporal_k
                                    )
                                    val_graphs_trial, _, _ = create_stgnn_graphs_with_k(
                                        val_df, feature_cols,
                                        flows_per_graph=config['flows_per_graph'],
                                        k=k_value, temporal_k=temporal_k
                                    )
                                else:
                                    print(f"  Building graphs with k={k_value}"
                                          f"{' (RGCN typed edges)' if is_rgcn else ''}...")
                                    train_graphs_trial, _, _ = create_network_aware_graphs_with_k(
                                        train_df, feature_cols,
                                        flows_per_graph=config['flows_per_graph'],
                                        k=k_value, for_rgcn=is_rgcn
                                    )
                                    # test_df is sealed and only evaluated after Optuna selects the best hyperparameters.
                                    val_graphs_trial, _, _ = create_network_aware_graphs_with_k(
                                        val_df, feature_cols,
                                        flows_per_graph=config['flows_per_graph'],
                                        k=k_value, for_rgcn=is_rgcn
                                    )

                                # CREATE DATA LOADERS WITH SUGGESTED BATCH SIZE
                                _trial_g = torch.Generator()
                                # Fixed seed: every trial uses identical batch order to isolate hyperparameter signal
                                _trial_g.manual_seed(GLOBAL_SEED)
                                train_loader_trial = DataLoader(
                                    train_graphs_trial,
                                    batch_size=batch_size,
                                    shuffle=True,
                                    generator=_trial_g
                                )
                                val_loader_trial = DataLoader(
                                    val_graphs_trial,
                                    batch_size=batch_size,
                                    shuffle=False
                                )

                                # INITIALIZE MODEL WITH SUGGESTED HIDDEN_DIM: GCN-DGI: reload the pretrained encoder weights
                                if m_name == 'GCN-DGI' and enc_path is not None:
                                    trial_encoder = DGIEncoder(
                                        num_features=num_features,
                                        hidden_dim=hidden_dim
                                    )
                                    trial_encoder.load_state_dict(
                                        torch.load(enc_path, map_location='cpu',
                                                   weights_only=True)
                                    )
                                    model_trial = m_class(
                                        num_features=num_features,
                                        hidden_dim=hidden_dim,
                                        dropout=dropout_rate,
                                        pretrained_encoder=trial_encoder
                                    ).to(device)
                                else:
                                    model_trial = m_class(
                                        num_features=num_features,
                                        hidden_dim=hidden_dim,
                                        dropout=dropout_rate
                                    ).to(device)

                                # â”€â”€ CLASS WEIGHTS â€” derived from train_df only (no leakage) â”€â”€
                                # Base: inverse-frequency over the 5 stages in the training split.
                                # Scale: Optuna-suggested multiplier boosts minority classes further.
                                # TEMPORAL SAFETY: only train_df labels are used here.  val_df and
                                # test_df label distributions never influence this tensor.
                                _train_lbl_counts = np.bincount(
                                    train_df['MultiLabel'].values, minlength=NUM_CLASSES
                                ).astype(float)
                                _safe_counts   = np.where(_train_lbl_counts > 0, _train_lbl_counts, 1.0)
                                _inv_freq      = 1.0 / _safe_counts
                                _inv_freq_norm = _inv_freq / _inv_freq.sum() * NUM_CLASSES
                                _cw            = _inv_freq_norm.copy()
                                _cw[1:]       *= minority_weight_scale   # amplify non-benign classes
                                class_weights_trial = torch.tensor(_cw, dtype=torch.float32).to(device)
                                criterion_trial = nn.CrossEntropyLoss(weight=class_weights_trial)
                                optimizer_trial = torch.optim.AdamW(
                                    model_trial.parameters(),
                                    lr=learning_rate,
                                    weight_decay=weight_decay
                                )

                                # ========================================
                                # TRAIN MODEL
                                # ========================================
                                print(f"  Training model...")
                                train_node_level(
                                    model_trial, train_loader_trial,
                                    optimizer_trial, criterion_trial, device,
                                    epochs=config['epochs'],
                                    disable_early_stopping=True  # all trials run full budget
                                )

                                # â”€â”€ EVALUATE ON VALIDATION SET (test is sealed) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                                # Multi-class: argmax prediction, no threshold needed.
                                print(f"  Evaluating on val set (macro-F1)...")
                                results_trial = evaluate_node_level_multiclass(
                                    model_trial, val_loader_trial, device,
                                    model_name=f"{m_name}_Trial_{trial.number}"
                                )

                                macro_f1_trial = results_trial['macro_f1']

                                print(f"  âœ“ MacroF1={macro_f1_trial:.4f}  "
                                      f"MacroPrec={results_trial['macro_precision']:.4f}  "
                                      f"MacroRec={results_trial['macro_recall']:.4f}")

                                # Report intermediate value for Optuna pruner
                                trial.report(macro_f1_trial, 50)

                                if trial.should_prune():
                                    raise optuna.TrialPruned()

                                return macro_f1_trial

                            except Exception as e:
                                print(f" FAILED: {e}")
                                return 0.0

                        return optuna_objective

                    # Create objective for this model
                    objective_func = create_objective_for_model(
                        model_class, model_name,
                        enc_path=dgi_encoder_path  # None for non-DGI models
                    )

                    # ========================================
                    # CREATE OPTUNA STUDY
                    # ========================================
                    study_name = f"dapt2020_{model_name.lower()}_optimization_8params"
                    # colab_path() redirects the DB to Drive in Colab so it
                    _db_path = colab_path(f"optuna_dbs/dapt2020_optuna_{model_name.lower()}_8params.db")

                    if FRESH_STUDY and os.path.exists(_db_path):
                        os.remove(_db_path)
                        print(f"  âœ“ FRESH_STUDY: removed existing DB â†’ "
                              f"{os.path.basename(_db_path)}")
                    elif not FRESH_STUDY and os.path.exists(_db_path):
                        import sqlite3
                        conn = sqlite3.connect(_db_path)
                        prior_trials = conn.execute(
                            "SELECT COUNT(*) FROM trials"
                        ).fetchone()[0]
                        conn.close()
                        print(f"  â„¹ FRESH_STUDY=False: loading {prior_trials} "
                              f"prior trial(s) from existing DB")
                    else:
                        print(f"  â„¹ No existing DB found â€” starting fresh regardless")

                    study = optuna.create_study(
                        direction="maximize",
                        sampler=optuna.samplers.TPESampler(seed=42),
                        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10),
                        study_name=study_name,
                        storage=f"sqlite:///{_db_path}",
                        load_if_exists=not FRESH_STUDY
                    )

                    # ========================================
                    # RUN OPTIMIZATION (100 TRIALS)
                    # ========================================
                    print(f"\n Starting Optuna optimization for {model_name}...")
                    study.optimize(
                        objective_func,
                        n_trials=config['optuna_trials'],
                        timeout=None,
                        show_progress_bar=True,
                        n_jobs=1
                    )

                    # ========================================
                    # DISPLAY BEST RESULTS
                    # ========================================
                    best_params   = study.best_params
                    best_macro_f1 = study.best_value

                    print(f"\n{'='*80}")
                    print(f"âœ“ {model_name} OPTIMIZATION COMPLETE")
                    print(f"{'='*80}")
                    print(f"\n Best Macro-F1: {best_macro_f1:.4f}")
                    print(f"\n Best Parameters for {model_name}:")
                    print(f"  {'Parameter':<28} {'Value':<20}")
                    print(f"  {'-'*48}")
                    print(f"  {'Minority Weight Scale':<28} {best_params['minority_weight_scale']:.4f}")
                    print(f"  {'K-value':<28} {best_params['k_value']}")
                    if model_name == 'ST-GCN':
                        print(f"  {'Temporal K':<28} {best_params.get('temporal_k', 4)}")
                    print(f"  {'Learning Rate':<28} {best_params['learning_rate']:.6f}")
                    print(f"  {'Dropout Rate':<28} {best_params['dropout_rate']:.4f}")
                    print(f"  {'Hidden Dim':<28} {best_params['hidden_dim']}")
                    print(f"  {'Batch Size':<28} {best_params['batch_size']}")
                    print(f"  {'Weight Decay':<28} {best_params['weight_decay']:.6f}")
                    print(f"{'='*80}\n")

                    # â”€â”€ SAVE RESULTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                    all_optuna_results[model_name] = {
                        'best_macro_f1':         best_macro_f1,
                        'minority_weight_scale':  best_params['minority_weight_scale'],
                        'k_value':               best_params['k_value'],
                        'learning_rate':         best_params['learning_rate'],
                        'dropout':               best_params['dropout_rate'],
                        'hidden_dim':            best_params['hidden_dim'],
                        'batch_size':            best_params['batch_size'],
                        'weight_decay':          best_params['weight_decay'],
                    }
                    # ST-GCN only: store optimised temporal window width
                    if model_name == 'ST-GCN':
                        all_optuna_results[model_name]['temporal_k'] = \
                            best_params.get('temporal_k', 4)

                    # Save model-specific results â€” colab_path() ensures Drive persistence
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    _opt_json = colab_path(f"optuna_results/{model_name}_best_params_{timestamp}_8params.json")
                    with open(_opt_json, 'w') as f:
                        json.dump(all_optuna_results[model_name], f, indent=2)

                    _opt_csv = colab_path(f"optuna_results/{model_name}_trials_{timestamp}_8params.csv")
                    df_trials = study.trials_dataframe()
                    df_trials.to_csv(_opt_csv, index=False)

                    print(f"âœ“ {model_name} results saved to: {os.path.dirname(_opt_json)}/")

                    # ========================================
                    # OPTUNA VISUALIZATIONS
                    # kaleido is required for write_image() â€” installed at top of notebook
                    # ========================================
                    try:
                        from optuna.visualization import plot_optimization_history, plot_param_importances

                        _hist_path = colab_path(f"optuna_results/{model_name}_optimization_history.png")
                        fig = plot_optimization_history(study)
                        fig.write_image(_hist_path)

                        _imp_path = colab_path(f"optuna_results/{model_name}_param_importances.png")
                        fig = plot_param_importances(study)
                        fig.write_image(_imp_path)

                        print(f"âœ“ Visualizations saved for {model_name}")
                    except Exception as viz_error:
                        print(f"âš  Could not generate visualizations: {viz_error}")

                except Exception as e:
                    print(f"\n {model_name} OPTIMIZATION FAILED: {e}")
                    import traceback
                    traceback.print_exc()

                    # Use defaults for this model
                    all_optuna_results[model_name] = {
                        'best_macro_f1':        0.0,
                        'minority_weight_scale': 3.0,  # neutral default
                        'k_value':              5,
                        'learning_rate':        0.001,
                        'dropout':              0.5,
                        'hidden_dim':           128,   # Default
                        'batch_size':           4,     # Default
                        'weight_decay':         0.01   # Default
                    }
                    if model_name == 'ST-GCN':
                        all_optuna_results[model_name]['temporal_k'] = 4

            # ========================================
            # SUMMARY OF ALL MODELS
            # ========================================
            print(f"\n{'='*80}")
            print(" ALL MODEL OPTIMIZATIONS COMPLETE!")
            print(f"{'='*80}")
            print(f"\n SUMMARY - OPTIMAL PARAMETERS BY MODEL (8 hyperparameters):")
            print(f"{'='*80}\n")

            # Summary table â€” multi-class columns
            print(f"{'Model':<12} {'MacroF1':<10} {'MinWtSc':<10} {'K':<5} {'LR':<12} {'Dropout':<10} {'HidDim':<10} {'Batch':<8} {'WD':<12}")
            print("-" * 100)
            for model_name in ['GATv2', 'RGCN', 'ST-GCN', 'GIN', 'GCN-DGI']:
                    r = all_optuna_results[model_name]
                    print(f"{model_name:<12} {r['best_macro_f1']:<10.4f} "
                          f"{r['minority_weight_scale']:<10.4f} "
                          f"{r['k_value']:<5} {r['learning_rate']:<12.6f} {r['dropout']:<10.4f} "
                          f"{r['hidden_dim']:<10} {r['batch_size']:<8} {r['weight_decay']:<12.6f}")
            print(f"{'='*80}\n")

            # Save combined results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            _all_models_path = colab_path(f"optuna_results/ALL_MODELS_best_params_{timestamp}_8params.json")
            with open(_all_models_path, 'w') as f:
                json.dump(all_optuna_results, f, indent=2)

            print(f"âœ“ Combined results saved to {_all_models_path}\n")

        else:
            print(f"\n{'='*80}")
            print("OPTUNA OPTIMIZATION SKIPPED")
            print(f"{'='*80}")
            print("Set RUN_OPTUNA_OPTIMIZATION = True to enable per-model optimization")
            print(f"{'='*80}\n")

            # Use defaults for all models
            for model_name in ['GATv2', 'RGCN', 'ST-GCN', 'GIN', 'GCN-DGI']:
                all_optuna_results[model_name] = {
                    'best_macro_f1':        0.0,
                    'minority_weight_scale': 3.0,  # neutral default
                    'k_value':              5,
                    'learning_rate':        0.001,
                    'dropout':              0.5,
                    'hidden_dim':           128,
                    'batch_size':           4,
                    'weight_decay':         0.01
                }
                if model_name == 'ST-GCN':
                    all_optuna_results[model_name]['temporal_k'] = 4

        # ========================================
        # PREPARE FOR FINAL TRAINING WITH PER-MODEL PARAMETERS
        # ========================================

        print(f"\n{'='*80}")
        print("TRAINING EACH MODEL WITH ITS OWN OPTIMAL PARAMETERS")
        print(f"{'='*80}")
        print("\nEach model will use its own optimized hyperparameters:")
        print("  â€¢ GATv2     â†’ GATv2-specific optimal params")
        print("  â€¢ RGCN      â†’ RGCN-specific optimal params + typed edge graphs")
        print("  â€¢ ST-GCN    â†’ ST-GCN-specific optimal params")
        print("  â€¢ GIN       â†’ GIN-specific optimal params")
        print("  â€¢ GCN-DGI   â†’ GCN-DGI-specific optimal params + pretrained init")
        print(f"{'='*80}\n")

        train_val_df = pd.concat([train_df, val_df], ignore_index=True)
        print(f"\n{'='*80}")
        print("TRAIN + VAL COMBINED FOR FINAL TRAINING")
        print(f"{'='*80}")
        print(f"  Train:    {len(train_df):,} flows")
        print(f"  Val:      {len(val_df):,} flows")
        print(f"  Combined: {len(train_val_df):,} flows")
        print(f"  Test:     {len(test_df):,} flows  <- still sealed")
        print(f"{'='*80}\n")

        _tv_graphs_default, _, _ = create_network_aware_graphs_with_k(
            train_val_df, feature_cols,
            flows_per_graph=config['flows_per_graph'], k=5
        )
        _tv_gen = torch.Generator()
        _tv_gen.manual_seed(GLOBAL_SEED)
        train_val_loader_default = DataLoader(
            _tv_graphs_default, batch_size=config['batch_size'],
            shuffle=True, generator=_tv_gen
        )
        print(f"  train_val_loader_default: {len(_tv_graphs_default)} graphs (k=5)")

        # Train all models with optimal parameters.
        trained_models             = {}
        trained_models_loaders     = {}
        trained_models_val_loaders = {}
        all_results                = {}

        for model_config in models_config:
                model_name  = model_config['name']
                model_class = model_config['class']

                print(f"\n{'='*80}")
                print(f"TRAINING {model_name} WITH ITS OPTIMAL PARAMETERS")
                print(f"{'='*80}")

                # Get this model's Optuna-optimised parameters
                model_params = all_optuna_results[model_name]

                # Convenience aliases
                opt_minority_scale = model_params['minority_weight_scale']
                opt_k              = model_params['k_value']
                opt_temporal_k     = model_params.get('temporal_k', 4)  # ST-GCN only
                opt_lr             = model_params['learning_rate']
                opt_dropout        = model_params['dropout']
                opt_hidden_dim     = model_params['hidden_dim']
                opt_batch_size     = model_params['batch_size']
                opt_weight_decay   = model_params['weight_decay']

                print(f"  Using {model_name}-specific parameters:")
                print(f"    Minority Weight Scale: {opt_minority_scale:.4f}")
                print(f"    K-value:               {opt_k}")
                if model_name == 'ST-GCN':
                    print(f"    Temporal K:            {opt_temporal_k}")
                print(f"    Learning Rate:         {opt_lr:.6f}")
                print(f"    Dropout:               {opt_dropout:.4f}")
                print(f"    Hidden Dim:            {opt_hidden_dim}")
                print(f"    Batch Size:            {opt_batch_size}")
                print(f"    Weight Decay:          {opt_weight_decay:.6f}")
                print(f"{'='*80}\n")

                # GCN-DGI: the encoder must be pretrained with the same hidden_dim
                # that will be used for fine-tuning.
                if model_name == 'GCN-DGI' and RUN_DGI_PRETRAINING:
                    if opt_hidden_dim != DGI_PRETRAIN_HIDDEN_DIM:
                        print(f"  GCN-DGI optimal hidden_dim ({opt_hidden_dim}) differs from "
                              f"pretraining dim ({DGI_PRETRAIN_HIDDEN_DIM}).")
                        print(f"  Re-pretraining DGI encoder with hidden_dim={opt_hidden_dim}...")
                        dgi_encoder_for_training = pretrain_with_dgi(
                            train_loader = train_val_loader_default,  # train+val, no test leakage
                            num_features = num_features,
                            device       = device,
                            hidden_dim   = opt_hidden_dim,
                            epochs       = config['dgi_pretrain_epochs'],
                            lr           = 1e-3,
                            patience     = 10,
                            verbose      = True
                        )
                        print(f"  Re-pretraining complete with hidden_dim={opt_hidden_dim}")
                    else:
                        # Reuse the encoder already pretrained above
                        dgi_encoder_for_training = dgi_pretrained_encoder
                else:
                    dgi_encoder_for_training = dgi_pretrained_encoder

                # Build graphs with this model's optimal k-value.
                # ST-GCN uses the dedicated builder; RGCN uses typed edges; others standard.
                is_rgcn  = (model_name == 'RGCN')
                is_stgcn = (model_name == 'ST-GCN')

                if is_stgcn:
                    print(f"Building ST-GCN graphs with k={opt_k}, "
                          f"temporal_k={opt_temporal_k} for {model_name}...")
                    train_graphs_model, _, _ = create_stgnn_graphs_with_k(
                        train_val_df, feature_cols,
                        flows_per_graph=config['flows_per_graph'],
                        k=opt_k, temporal_k=opt_temporal_k
                    )
                    val_graphs_model, _, _ = create_stgnn_graphs_with_k(
                        val_df, feature_cols,
                        flows_per_graph=config['flows_per_graph'],
                        k=opt_k, temporal_k=opt_temporal_k
                    )
                    test_graphs_model, _, _ = create_stgnn_graphs_with_k(
                        test_df, feature_cols,
                        flows_per_graph=config['flows_per_graph'],
                        k=opt_k, temporal_k=opt_temporal_k
                    )
                else:
                    print(f"Building graphs with k={opt_k} for {model_name}"
                          f"{' (typed edges)' if is_rgcn else ''}...")
                    train_graphs_model, _, _ = create_network_aware_graphs_with_k(
                        train_val_df, feature_cols,
                        flows_per_graph=config['flows_per_graph'],
                        k=opt_k,
                        for_rgcn=is_rgcn
                    )
                    val_graphs_model, _, _ = create_network_aware_graphs_with_k(
                        val_df, feature_cols,
                        flows_per_graph=config['flows_per_graph'],
                        k=opt_k,
                        for_rgcn=is_rgcn
                    )
                    test_graphs_model, _, _ = create_network_aware_graphs_with_k(
                        test_df, feature_cols,
                        flows_per_graph=config['flows_per_graph'],
                        k=opt_k,
                        for_rgcn=is_rgcn
                    )

                # Use the Optuna-optimised batch size
                _final_g = torch.Generator()
                _final_g.manual_seed(GLOBAL_SEED)
                train_loader_model = DataLoader(
                    train_graphs_model,
                    batch_size=opt_batch_size,
                    shuffle=True,
                    generator=_final_g
                )
                val_loader_model = DataLoader(
                    val_graphs_model,
                    batch_size=opt_batch_size,
                    shuffle=False
                )
                test_loader_model = DataLoader(
                    test_graphs_model,
                    batch_size=opt_batch_size,
                    shuffle=False
                )

                # Re-seed model weights so each model starts from the same random state regardless of order in the loop
                set_global_seeds(GLOBAL_SEED)

                # Initialize model with its optimal hidden_dim AND dropout.
                if model_name == 'GCN-DGI' and dgi_encoder_for_training is not None:
                    model = model_class(
                        num_features=num_features,
                        hidden_dim=opt_hidden_dim,
                        dropout=opt_dropout,
                        pretrained_encoder=dgi_encoder_for_training,
                        num_classes=NUM_CLASSES
                    ).to(device)
                elif model_name == 'RGCN':
                    model = model_class(
                        num_features=num_features,
                        hidden_dim=opt_hidden_dim,
                        dropout=opt_dropout,
                        num_relations=NodeLevelRGCN.NUM_RELATIONS,
                        num_classes=NUM_CLASSES
                    ).to(device)
                else:
                    model = model_class(
                        num_features=num_features,
                        hidden_dim=opt_hidden_dim,
                        dropout=opt_dropout,
                        num_classes=NUM_CLASSES
                    ).to(device)

                # Setup training with Optuna-optimised parameters.
                # Class weights derived from train_val_df labels only â€” test labels never
                # consulted (temporal safety).  Mirror the same inverse-frequency +
                # minority amplification logic used inside Optuna trials, but now using
                # the full train+val set (Optuna trials used train only).
                _tv_counts = np.bincount(
                    train_val_df['MultiLabel'].values, minlength=NUM_CLASSES
                ).astype(float)
                _tv_safe   = np.where(_tv_counts > 0, _tv_counts, 1.0)
                _tv_inv    = 1.0 / _tv_safe
                _tv_norm   = _tv_inv / _tv_inv.sum() * NUM_CLASSES   # scale to sumâ†’NUM_CLASSES
                _tv_cw     = _tv_norm.copy()
                _tv_cw[1:] *= opt_minority_scale                      # amplify non-benign
                class_weights = torch.tensor(_tv_cw, dtype=torch.float32).to(device)
                criterion = nn.CrossEntropyLoss(weight=class_weights)
                print(f"  Class weights (train+val, minority_scale={opt_minority_scale:.3f}):")
                for _ci, (_cw_val, _cn) in enumerate(zip(_tv_cw, STAGE_NAMES)):
                    print(f"    [{_ci}] {_cn:<25}: {_cw_val:.4f}")
                optimizer = torch.optim.AdamW(
                    model.parameters(),
                    lr=opt_lr,
                    weight_decay=opt_weight_decay    # â† was hardcoded 0.01
                )

                #Checking Optuna hyperparameter are actually applied
                print(f"\n  Correctness checks for {model_name}:")

                _sample_batch = next(iter(train_loader_model))
                _actual_bs = _sample_batch.num_graphs
                assert _actual_bs == opt_batch_size, (
                    f"  BATCH SIZE MISMATCH â€” loader produced {_actual_bs} "
                    f"graphs/batch, expected {opt_batch_size}"
                )
                print(f"  âœ“ Batch size:   {_actual_bs} == {opt_batch_size}")

                # 2. Weight decay â€”
                _actual_wd = optimizer.param_groups[0]['weight_decay']
                assert abs(_actual_wd - opt_weight_decay) < 1e-12, (
                    f"  WEIGHT DECAY MISMATCH â€” optimizer has {_actual_wd}, "
                    f"expected {opt_weight_decay}"
                )
                print(f"  âœ“ Weight decay: {_actual_wd:.6f} == {opt_weight_decay:.6f}")

                # 3. Hidden dim
                _inferred_hd = model.classifier[0].weight.shape[1]
                assert _inferred_hd == opt_hidden_dim, (
                    f"  HIDDEN DIM MISMATCH â€” model architecture has "
                    f"hidden_dim={_inferred_hd}, expected {opt_hidden_dim}"
                )
                print(f"  âœ“ Hidden dim:   {_inferred_hd} == {opt_hidden_dim}")

                # Train the model
                print(f"Training {model_name} for {config['epochs']} epochs...")
                train_node_level(
                    model, train_loader_model, optimizer, criterion, device,
                    epochs=config['epochs'],
                    val_loader=val_loader_model,  # monitors val loss, not train loss
                    disable_early_stopping=True   # fixed budget matches Optuna trial conditions
                )

                # Evaluate â€” multi-class uses argmax, no threshold needed
                print(f"Evaluating {model_name} (5-class, argmax)...")
                results = evaluate_node_level_multiclass(
                    model, test_loader_model, device,
                    model_name=model_name
                )

                trained_models[model_name]             = model
                trained_models_loaders[model_name]     = test_loader_model
                trained_models_val_loaders[model_name] = val_loader_model
                all_results[model_name]                = results

                print(f"\nâœ“ {model_name} Results (5-class):")
                print(f"  Accuracy:           {results.get('accuracy', 0):.4f}")
                print(f"  Weighted Precision: {results.get('weighted_precision', 0):.4f}")
                print(f"  Weighted Recall:    {results.get('weighted_recall', 0):.4f}")
                print(f"  Weighted F1:        {results['weighted_f1']:.4f}")
                print(f"  Macro ROC-AUC:      {results.get('macro_roc_auc', 0):.4f}")

        # Final Results Table (single consolidated table)
        print(f"\n{'='*80}")
        print("FINAL RESULTS - ALL MODELS (5-CLASS)")
        print(f"{'='*80}")
        col_w = 14
        print(f"{'Model':<15} {'Accuracy':<{col_w}} {'Wt Precision':<{col_w}} {'Wt Recall':<{col_w}} {'Wt F1':<{col_w}} {'Macro ROC-AUC':<{col_w}}")
        print("-" * (15 + col_w * 5))
        for model_name, results in all_results.items():
            print(f"{model_name:<15} "
                  f"{results.get('accuracy', 0):<{col_w}.4f}"
                  f"{results.get('weighted_precision', 0):<{col_w}.4f}"
                  f"{results.get('weighted_recall', 0):<{col_w}.4f}"
                  f"{results['weighted_f1']:<{col_w}.4f}"
                  f"{results.get('macro_roc_auc', 0):<{col_w}.4f}")
        print(f"{'='*80}\n")

        # Visualizations
        plot_confusion_matrices(all_results)
        plot_model_comparison(all_results)

        # Edge Similarity Analysis
        print(f"\n{'='*80}")
        print("EDGE SIMILARITY ANALYSIS")
        print(f"{'='*80}")
        print("Analyzing why flows are connected in the KNN graph...")

        # Set output directory â€” colab_path() routes to Drive in Colab
        edge_output_dir = colab_path('edge_similarity_analysis')

        # Run edge similarity analysis on training data
        edge_analysis_results = create_edge_visualizations(
            df=train_df,
            feature_cols=feature_cols,
            k=5,
            output_dir=edge_output_dir,
            display_plots=True,
            save_plots=True
        )

        print(f"âœ“ Edge similarity analysis complete!")
        print(f"  Visualizations saved to: {edge_output_dir}")

        # Display images directly in Colab notebook
        if IS_COLAB:
            from IPython.display import Image, display
            # import os  # Already imported globally
            print("\n Displaying visualizations in notebook:")
            for i in range(1, 7):
                img_files = {
                    1: "1_distance_distribution.png",
                    2: "2_tsne_feature_space.png",
                    3: "3_pca_feature_space.png",
                    4: "4_feature_importance.png",
                    5: "5_connected_vs_random.png",
                    6: "6_similarity_heatmap.png"
                }
                img_path = os.path.join(edge_output_dir, img_files[i])
                if os.path.exists(img_path):
                    print(f"\n{img_files[i]}:")
                    display(Image(img_path, width=800))

        print(f"{'='*80}\n")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = colab_path(f'dapt2020_results_{timestamp}.json')

        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'config': {k: str(v) for k, v in config.items()},
                'results': all_results,
                'dataset_stats': {
                    'total_flows': len(df),
                    'per_stage_counts': {
                        STAGE_NAMES[i]: int((df['MultiLabel'] == i).sum())
                        for i in range(NUM_CLASSES)
                    }
                },
                'edge_analysis': {
                    'output_dir': edge_output_dir,
                    'k_neighbors': 5,
                    'analysis_completed': True
                }
            }, f, indent=2, default=str)

        print(f"âœ“ Results saved to: {results_file}")
        print(f"\n{'='*80}")
        print("EXECUTION COMPLETE!")
        print(f"{'='*80}\n")

        return all_results

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()
        return None

# ========================================
# QUICK TEST FUNCTION
# ========================================

def quick_test(max_files=5, sample_rate=0.3, strategy='hybrid'):
    """Quick test with subset of data"""
    print(f"\n{'='*80}")
    print("QUICK TEST - DAPT2020")
    print(f"{'='*80}")
    print(f"Processing {max_files} files at {sample_rate*100:.0f}% sampling")
    print(f"Strategy: {strategy}")
    print(f"{'='*80}\n")

    return main(max_files=max_files, sample_rate=sample_rate, strategy=strategy)

# ========================================
# EXECUTION BLOCK
# ========================================

if __name__ == "__main__":
    print(f"\n{'='*80}")
    print("DAPT2020 GNN PIPELINE")
    print(f"{'='*80}")

    print("\nMODELS TRAINED:")
    print("  â€¢ GATv2     (Graph Attention Network v2 â€” dynamic attention)")
    print("  â€¢ RGCN      (Relational GCN â€” typed edges: src-IP, dst-IP, KNN)")
    print("  â€¢ ST-GCN    (Spatial-Temporal Graph Neural Network)")
    print("  â€¢ GIN       (Graph Isomorphism Network)")
    print("  â€¢ GCN-DGI   (GCN pretrained via Deep Graph Infomax)")

    print(f"\n{'='*80}\n")

    # Uncomment to auto-execute:
    # results = quick_test(max_files=5, sample_rate=0.3)
    results = main()

