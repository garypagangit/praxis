async page => {
  const text = String.raw`from pathlib import Path
import os
import subprocess
import traceback

print("Patching Praxisv04 runtime source and restarting the run...")

DRIVE_ROOT = Path("/content/drive/MyDrive/apt_praxis")
RESULTS_DIR = DRIVE_ROOT / "results"
DATA_REPO = Path("/content/unraveled-repo")
DATA_ROOT = DATA_REPO / "data" / "network-flows"

def sh(*cmd):
    print("+", " ".join(str(x) for x in cmd))
    subprocess.check_call([str(x) for x in cmd])

try:
    DRIVE_ROOT.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_ROOT.exists():
        if DATA_REPO.exists() and not (DATA_REPO / ".git").exists():
            raise RuntimeError(f"{DATA_REPO} exists but is not a git repo.")
        if not DATA_REPO.exists():
            sh(
                "git", "clone",
                "--depth", "1",
                "--filter=blob:none",
                "--sparse",
                "https://gitlab.com/asu22/unraveled.git",
                DATA_REPO,
            )
        sh("git", "-C", DATA_REPO, "sparse-checkout", "set", "data/network-flows")
        try:
            sh("git", "-C", DATA_REPO, "pull", "--ff-only")
        except Exception as pull_error:
            print("Non-fatal git pull warning:", pull_error)

    assert DATA_ROOT.exists(), f"Dataset path missing: {DATA_ROOT}"

    os.environ["PRAXISV04_DRIVE_ROOT"] = str(DRIVE_ROOT)
    os.environ["PRAXISV04_RESULTS_DIR"] = str(RESULTS_DIR)
    os.environ["PRAXISV04_DATA_ROOT"] = str(DATA_ROOT)
    os.environ["PRAXISV04_OPTUNA_TRIALS"] = "25"
    os.environ["PRAXISV04_TRAIN_EPOCHS"] = "100"
    os.environ["PRAXISV04_PATIENCE"] = "10"

    p = Path("/content/praxisv04_runtime/references/APT_Praxis_Colab_Experiment.py")
    t = p.read_text(encoding="utf-8")
    t = t.replace("import glob\n\nimport pandas as pd\n", "import csv\nimport glob\n\nimport pandas as pd\n")
    t = t.replace(
        'drive.mount("/content/drive")',
        'if not os.path.isdir("/content/drive/MyDrive"):\n    drive.mount("/content/drive")\nelse:\n    print("Drive already mounted at /content/drive")',
    )

    if "TAIL_LABEL_COLUMNS" not in t:
        t = t.replace(
            "import pandas as pd\n\n\ndef load_unraveled(data_root: str) -> pd.DataFrame:\n",
            """import pandas as pd


TAIL_LABEL_COLUMNS = ["Activity", "Stage", "DefenderResponse", "Signature"]
FLEX_TEXT_COLUMNS = [
    "requested_server_name",
    "client_fingerprint",
    "server_fingerprint",
    "user_agent",
    "content_type",
]


def _normalize_csv_row(row: list[str], header_len: int) -> list[str]:
    if len(row) == header_len:
        return row
    if len(row) < header_len:
        return row + ["nan"] * (header_len - len(row))

    fixed_prefix_len = header_len - len(FLEX_TEXT_COLUMNS) - len(TAIL_LABEL_COLUMNS)
    label_tail = row[-len(TAIL_LABEL_COLUMNS):]
    middle = row[fixed_prefix_len:-len(TAIL_LABEL_COLUMNS)]
    repaired_middle = [",".join(middle)] + ["nan"] * (len(FLEX_TEXT_COLUMNS) - 1)
    return row[:fixed_prefix_len] + repaired_middle + label_tail


def _read_unraveled_csv(fpath: str) -> pd.DataFrame:
    with open(fpath, "r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [_normalize_csv_row(row, len(header)) for row in reader]

    return pd.DataFrame(rows, columns=header)


def load_unraveled(data_root: str) -> pd.DataFrame:
""",
        )

    t = t.replace(
        "df_tmp = pd.read_csv(fpath, low_memory=False)",
        "df_tmp = _read_unraveled_csv(fpath)",
    )

    t = t.replace(
        'if "APT Stage" in df_raw.columns:\n    df_raw.rename(columns={"APT Stage": "APT_Stage"}, inplace=True)\nelif "Label" in df_raw.columns:\n    df_raw.rename(columns={"Label": "APT_Stage"}, inplace=True)\n',
        'if "APT Stage" in df_raw.columns:\n    df_raw.rename(columns={"APT Stage": "APT_Stage"}, inplace=True)\nelif "Stage" in df_raw.columns:\n    df_raw.rename(columns={"Stage": "APT_Stage"}, inplace=True)\nelif "Label" in df_raw.columns:\n    df_raw.rename(columns={"Label": "APT_Stage"}, inplace=True)\n',
    )

    p.write_text(t, encoding="utf-8")

    from praxis.praxisv04 import load_default_runner
    runner = load_default_runner(Path("/content/praxisv04_runtime"))

    print("Drive root:", os.environ["PRAXISV04_DRIVE_ROOT"])
    print("Data root:", os.environ["PRAXISV04_DATA_ROOT"])
    print("Patched:", p)
    print("Reloaded runner from patched runtime source.")

    runner.run_blocks(list(range(0, 20)))
    print("Praxisv04 full-paper run completed.")
except Exception:
    traceback.print_exc()
    raise`;

  await page.evaluate((textValue) => {
    const editors = window.monaco.editor.getEditors();
    const target =
      editors.find(editor => editor.getModel()?.getValue()?.includes('Patching Praxisv04 runtime source')) ||
      editors[0];
    if (!target)
      throw new Error('Target recovery editor not found.');
    target.getModel().setValue(textValue);
    target.focus();
  }, text);

  const cell = page.getByRole('region', { name: /Cell 2: Code cell:/ });
  await cell.getByRole('button', { name: 'Run cell' }).click();
  await page.waitForTimeout(3000);
}
