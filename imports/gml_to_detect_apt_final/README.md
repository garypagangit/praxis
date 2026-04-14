# GML To Detect APT Final

Imported from the zip:

- `C:\Users\garyp\Downloads\GML To Detect APT Final.zip`

What is in this folder:

- `GML_To_Detect_APT_Final_v0_02_Multi_Class_.ipynb`
- `gml_to_detect_apt_final.py`
- `.env.example`
- `requirements.txt`

Import notes:

- The notebook was imported with outputs and execution counts cleared to keep the repo smaller and avoid carrying runtime artifacts.
- The original zip contained an `env` file with AWS credentials. That file was intentionally not imported.
- The imported notebook and script were then patched to use local CSV data instead of AWS/S3.
- Use `scripts/import_dapt2020_data.ps1` to copy the 10 raw CSV files into `data/raw/dapt2020/` and build `data/processed/dapt2020/combined_flows.csv`.
- `.env.example` is kept only as a minimal placeholder reference. The current local-data workflow does not require it.
- The exported Python file is a script-friendly version of the notebook code. Notebook shell commands were converted into comments.

Local data paths used by the patched code:

- `data/raw/dapt2020/`
- `data/processed/dapt2020/combined_flows.csv`
- `data/processed/dapt2020/summary.json`

Security note:

- Because the original archive contained live-looking AWS credentials, rotate or revoke those credentials if they are still active.
