from __future__ import annotations

import base64
import json
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from praxis.praxisv04 import load_default_runner


NOTEBOOK_PATH = REPO_ROOT / "Praxisv04_Colab.ipynb"
PRAxisV04_MODULE_PATH = REPO_ROOT / "src" / "praxis" / "praxisv04.py"
EXPERIMENT_SOURCE_PATH = REPO_ROOT / "references" / "APT_Praxis_Colab_Experiment.py"


def markdown_cell(text: str) -> dict:
    clean = textwrap.dedent(text).strip()
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in clean.splitlines()],
    }


def code_cell(text: str) -> dict:
    clean = textwrap.dedent(text).strip()
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in clean.splitlines()],
    }


def build_notebook() -> dict:
    runner = load_default_runner(REPO_ROOT)
    runner_source_b64 = base64.b64encode(
        PRAxisV04_MODULE_PATH.read_text(encoding="utf-8").encode("utf-8")
    ).decode("ascii")
    experiment_source_b64 = base64.b64encode(
        EXPERIMENT_SOURCE_PATH.read_text(encoding="utf-8").encode("utf-8")
    ).decode("ascii")
    cells: list[dict] = []

    cells.append(
        markdown_cell(
            """
            # Praxisv04 Colab Experiment Runner

            This notebook turns the original `APT_Praxis_Colab_Experiment.py` into a modular Praxisv04 workflow.

            ## Purpose Of This Notebook

            - run the original experiment block-by-block inside Colab
            - keep each block modular so individual model sections can be rerun without redoing every model
            - show the purpose of each block before execution
            - preserve the experiment outputs, visuals, and interpretation notes from the source experiment

            ## How To Use It

            1. Open this notebook from the repo root in Colab.
            2. Run the setup cell once.
            3. See `PRAXISV04_COLAB_RUNBOOK.md` for the recommended baseline-only, novelty-only, and full-paper execution orders.
            4. Run blocks `0-8` to prepare the environment, data, splits, graphs, and tracker.
            5. Rerun any model block `9-18` independently as needed.
            6. Run block `19` whenever you want refreshed comparison tables and visuals.

            This notebook is self-contained for Colab upload: the setup cell writes the Praxisv04 runner and the source experiment into the runtime automatically.
            """
        )
    )

    cells.append(
        code_cell(
            f"""
            import base64
            import sys
            from pathlib import Path

            RUNTIME_ROOT = Path("/content/praxisv04_runtime")
            SRC_ROOT = RUNTIME_ROOT / "src"
            PKG_ROOT = SRC_ROOT / "praxis"
            REF_ROOT = RUNTIME_ROOT / "references"
            PKG_ROOT.mkdir(parents=True, exist_ok=True)
            REF_ROOT.mkdir(parents=True, exist_ok=True)

            (PKG_ROOT / "__init__.py").write_text("", encoding="utf-8")
            (PKG_ROOT / "praxisv04.py").write_text(
                base64.b64decode({runner_source_b64!r}).decode("utf-8"),
                encoding="utf-8",
            )
            (REF_ROOT / "APT_Praxis_Colab_Experiment.py").write_text(
                base64.b64decode({experiment_source_b64!r}).decode("utf-8"),
                encoding="utf-8",
            )

            if str(SRC_ROOT) not in sys.path:
                sys.path.insert(0, str(SRC_ROOT))

            from praxis.praxisv04 import load_default_runner

            runner = load_default_runner(RUNTIME_ROOT)
            runner.display_catalog()
            """
        )
    )

    cells.append(
        markdown_cell(
            """
            ## Modular Rerun Guide

            - Blocks `0-8` are the shared preparation pipeline.
            - Blocks `9-18` are model or decision blocks and can be rerun independently after preparation is complete.
            - Block `15` prepares the sequence datasets used by blocks `17` and `18`.
            - Block `19` rebuilds the final comparison visuals and tables from the current tracker state and is intended for full-paper runs.
            """
        )
    )

    for block_number, block in runner.blocks.items():
        cells.append(markdown_cell(runner.render_block_markdown(block_number)))
        cells.append(code_cell(f"runner.run_block({block_number})"))

    cells.append(
        markdown_cell(
            """
            ## Example Targeted Reruns

            Use any of these in a new code cell after the notebook has been initialized:

            ```python
            runner.run_block(15)  # rerun Mamba baseline only
            runner.run_block(17)  # rerun APT-Mamba only
            runner.run_block(18)  # rerun KC-CWT only
            runner.run_block(19)  # regenerate final tables and visuals
            ```
            """
        )
    )

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    notebook = build_notebook()
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    print(f"Wrote {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
