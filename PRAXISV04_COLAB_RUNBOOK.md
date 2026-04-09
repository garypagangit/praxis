# Praxisv04 Colab Runbook

This runbook is the recommended execution guide for [Praxisv04_Colab.ipynb](C:/Users/garyp/OneDrive/Documents/codex/Praxisv04_Colab.ipynb).

## Purpose

`Praxisv04` keeps the original APT experiment intact while making it modular enough to run block-by-block in Colab. The goal is to let you:

- run the shared setup once
- rerun individual models without repeating the whole notebook
- generate visuals and explanations at the block level
- choose between a baseline-only, novelty-only, or full-paper execution path

## Key Dependency Rules

- Blocks `0-8` are the shared preparation pipeline.
- Blocks `9-15` are the baseline model family.
- Block `15` creates the sequence datasets used by blocks `17` and `18`.
- Block `16` is the decision checkpoint after the baseline family.
- Block `19` assumes both baseline and novelty model results are already in the tracker.
- Do not run block `19` in a fresh session unless the required baseline and novelty blocks have both been executed in that same session.

## Shared Start For Every Run

Open [Praxisv04_Colab.ipynb](C:/Users/garyp/OneDrive/Documents/codex/Praxisv04_Colab.ipynb), run the setup cell, then use one of the execution orders below.

Common prep command:

```python
runner.run_blocks(range(0, 9))
```

That covers:

- `0` installation
- `1` configuration, seeds, and Drive mount
- `2` data loading
- `3` EDA
- `4` feature treatment
- `5` temporal split
- `6` graph construction
- `7` loss functions
- `8` results tracker

## Baseline-Only Run

Use this when you want the strongest non-novel foundation first and want the decision gate before committing to the new architectures.

Recommended order:

```python
runner.run_blocks(range(0, 9))
runner.run_blocks(range(9, 17))
```

Expanded block order:

1. `0-8` shared preparation
2. `9` MLP baseline + SHAP
3. `10` GATv2
4. `11` R-GCN
5. `12` GIN
6. `13` GCN-DGI
7. `14` ST-GCN
8. `15` Mamba baseline
9. `16` decision gate

What you get:

- EDA plots
- split distribution figure
- SHAP plots and SHAP feature table
- per-model confusion matrices
- training curves per baseline model
- a baseline comparison table from the tracker
- the decision-gate recommendation for whether the novelty phase is justified

What to avoid:

- Do not run block `19` yet. Its final hypothesis section expects the novelty models to exist in the tracker too.

## Novelty-Only Run

Use this when baseline evidence already exists and you want to focus on the sequential novelty phase with the minimum safe recomputation.

Recommended order in a fresh Colab session:

```python
runner.run_blocks(range(0, 9))
runner.run_block(15)
runner.run_block(16)
runner.run_blocks([17, 18])
```

Why this order:

- `15` is required because it builds the sequence datasets and loaders used by the novelty models.
- `16` is still useful as the local checkpoint before interpreting novelty gains.
- `17` and `18` are the actual novelty blocks.

What you get:

- Mamba baseline outputs for the same sequence representation
- APT-MAMBA results and visuals
- KC-CWT results and attention-map artifact
- training curves and confusion matrices for the novelty models

Important limitation:

- Do not run block `19` in novelty-only mode unless you have also run the graph baselines in the same session.
- In the current `Praxisv04` design, block `19` computes cross-family hypotheses and can fail or mislead when the tracker only contains sequence models.

## Full-Paper Run

Use this when you want the complete end-to-end experiment, all paper tables, and all paper figures in one tracker state.

Recommended order:

```python
runner.run_blocks(range(0, 20))
```

Expanded block order:

1. `0-8` shared preparation
2. `9-15` baseline family
3. `16` decision gate
4. `17` APT-MAMBA GMR-2
5. `18` KC-CWT
6. `19` final comparison tables and visualisations

What you get:

- everything from the baseline-only and novelty-only runs
- final cross-model comparison tables
- per-stage heatmap
- grouped model comparison chart
- ablation waterfall
- final hypothesis evaluation text
- exported `.csv` and `.png` artifacts saved from block `19`

## Recommended Practical Workflow

If you are running on limited Colab time, use this progression:

1. Run `baseline-only` first.
2. Inspect block `16`.
3. If the baseline evidence supports novelty, rerun from a clean session with `full-paper`.

If you are iterating on only the novel architectures:

1. Keep the baseline results from a prior documented run.
2. Use `novelty-only` for faster iteration.
3. Reserve `full-paper` for the final paper-grade rerun.

## Useful Colab Shortcuts

Run a single block:

```python
runner.run_block(15)
```

Run a selected block list:

```python
runner.run_blocks([15, 17, 18])
```

Regenerate the final paper artifacts after a full run:

```python
runner.run_block(19)
```

## File Map

- Notebook: [Praxisv04_Colab.ipynb](C:/Users/garyp/OneDrive/Documents/codex/Praxisv04_Colab.ipynb)
- Runner: [praxisv04.py](C:/Users/garyp/OneDrive/Documents/codex/src/praxis/praxisv04.py)
- Notebook generator: [build_praxisv04_notebook.py](C:/Users/garyp/OneDrive/Documents/codex/scripts/build_praxisv04_notebook.py)
- Source experiment: [APT_Praxis_Colab_Experiment.py](C:/Users/garyp/OneDrive/Documents/codex/references/APT_Praxis_Colab_Experiment.py)
