async page => {
  const cell = page.getByRole('region', { name: 'Cell 1: Code cell:' });
  const editor = cell.getByRole('textbox');
  const text = String.raw`from pathlib import Path
import os
import subprocess
import traceback

print("Starting Praxisv04 full-paper run...")

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

    print("Drive root:", os.environ["PRAXISV04_DRIVE_ROOT"])
    print("Results dir:", os.environ["PRAXISV04_RESULTS_DIR"])
    print("Data root:", os.environ["PRAXISV04_DATA_ROOT"])

    runner.run_blocks(list(range(0, 20)))
    print("Praxisv04 full-paper run completed.")
except Exception:
    traceback.print_exc()
    raise`;

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
