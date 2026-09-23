# Reproduction guide

Repository: [garypagangit/praxis](https://github.com/garypagangit/praxis), branch `praxis-next-20260923`. Run commands from the repository root. Preserve the recorded commits and file hashes when comparing results.

## Public verification

The released capture confusion matrices and actual bootstrap draws are sufficient to recompute paired metrics and intervals without access to private flows. They do not permit independent reassessment of labels or source preparation.

```powershell
python experiments/praxis_next/measurement_praxis/evidence/paired_reanalysis/verify_public.py
python experiments/praxis_next/measurement_praxis/verify_package.py
```

The first command uses independent NumPy confusion-matrix arithmetic. The second checks package hashes, original/new audit receipts, manuscript assembly, PDF/DOCX correspondence and local evidence links. Neither trains a model. Verification behavior and existing receipt handling are documented in each script.

## Tests

```powershell
python -m pytest experiments/praxis_next/d1_benchmark_audit experiments/praxis_next/measurement_praxis/evidence/paired_reanalysis/test_reanalysis.py experiments/praxis_next/measurement_praxis/evidence/paired_reanalysis/test_public_verifier.py experiments/praxis_next/measurement_praxis/evidence/qualification_audit/test_verify_qualification.py -q
```

The original experiment tests are also retained under their respective study directories. Tests exercise row pairing, missing classes, whole-capture resampling, invalid metadata, boundary ties, no-contrast cases and distinct support-sweep logic.

## Private-data recomputation

The [paired input inventory](evidence/paired_reanalysis/INPUTS.json) records the immutable prepared cohort and 66 selected probability archive identities. The [qualification record](../d1_benchmark_audit/QUALIFICATION.json) and independent verifier identify the exact source CSVs. Supply byte-identical artifacts at the recorded paths, or make an explicit reviewed portability adaptation in a separate checkout. Renaming a different dataset to the recorded filename does not satisfy the contract.

Use a separate output checkout for a fresh run. Existing frozen receipts are intentionally protected from overwrite. Preserve them before configuring a distinct reproduction output directory; do not overwrite the published evidence. The original committed scripts and before-execution commit identifiers are:

```powershell
python -m experiments.praxis_next.measurement_praxis.evidence.paired_reanalysis.reanalysis run --commit c0d884e
python experiments/praxis_next/measurement_praxis/evidence/qualification_audit/verify_qualification.py --commit e6b5799
```

These commands require the private source paths and fresh result destinations expected by the scripts; they are documentation of the recorded executions, not an instruction to erase checked-in receipts. The paired runner's frozen plan includes all 36 contrasts. There is no new tuning or reroll procedure.

## Rebuild the manuscript

Scientific build: Python with NumPy and Matplotlib. Document build: Python with python-docx, PyMuPDF and Pillow, plus LibreOffice. The Windows environment used for this package has scientific Python at `C:/w/tabular_batch_env_20260921/Scripts/python.exe`, base Python selected by `py`, and LibreOffice at `C:/Program Files/LibreOffice/program/soffice.exe`.

```powershell
python experiments/praxis_next/measurement_praxis/build_paper.py
python experiments/praxis_next/measurement_praxis/render_paper.py
```

The build reads audited aggregates and `PAPER_DATA.json`, writes the nine compact CSV tables and three figures, fills the complete Markdown template, and records input hashes. The renderer creates Word, converts it to PDF, and exports every page for inspection. Its Windows-specific paths can be adapted for another environment without changing scientific inputs. A rebuild changes document metadata and requires a new render/manifest receipt; identical numerical content need not yield an identical PDF byte hash.

## Interpretation and access

- Original main model environment: NumPy 2.2.6, LightGBM 4.6.0, scikit-learn 1.7.2. The new build and reanalysis receipts record their own versions and source bindings.
- Original bootstrap and new reanalysis intervals have different documented absent-class conventions; do not replace one with the other silently.
- Raw traces and row-level predictions are not redistributed in the public evidence ZIP. Dataset rights and availability remain source-specific.
- Verification establishes the calculations described in the manuscript. It cannot establish independent-campaign validity from a single campaign or qualify a source clock that lacks documentation.
