async page => {
  const text = String.raw`from pathlib import Path
import traceback

print("Patching Praxisv04 runtime source and restarting the run...")

p = Path("/content/praxisv04_runtime/references/APT_Praxis_Colab_Experiment.py")
t = p.read_text(encoding="utf-8")
t = t.replace("import glob\n\nimport pandas as pd\n", "import csv\nimport glob\n\nimport pandas as pd\n")

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
print("Patched:", p)

from praxis.praxisv04 import load_default_runner
runner = load_default_runner(Path("/content/praxisv04_runtime"))
print("Reloaded runner from patched runtime source.")

try:
    runner.run_blocks(list(range(0, 20)))
    print("Praxisv04 full-paper run completed.")
except Exception:
    traceback.print_exc()
    raise`;

  await page.getByRole('button', { name: /Code Insert code cell below/ }).click();
  await page.waitForTimeout(1000);

  const cell = page.getByRole('region', { name: /Code cell:/ }).last();
  const editor = page.getByRole('textbox', { name: /Editor content/ }).last();

  await editor.click({ force: true });
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  await page.keyboard.insertText(text);
  await cell.getByRole('button', { name: 'Run cell' }).click();
  await page.waitForTimeout(15000);

  const cellText = await cell.textContent();
  if (/SyntaxError|Traceback|KeyError|ModuleNotFoundError|AssertionError/.test(cellText || '')) {
    throw new Error((cellText || '').slice(0, 4000));
  }
}
