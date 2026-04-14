from __future__ import annotations

import builtins
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BLOCK_START_RE = re.compile(r"^# BLOCK\s+(\d+)\s+[^A-Za-z0-9]*(.+?)\s*$")
PURPOSE_RE = re.compile(r"^# PURPOSE:\s*(.*)$")
OUTPUT_RE = re.compile(r"^# OUTPUTS?:\s*(.*)$")
INTERPRETATION_RE = re.compile(r"^# INTERPRETATION:\s*(.*)$")


MANUAL_BLOCK_NOTES: dict[int, dict[str, str | tuple[int, ...]]] = {
    0: {
        "outputs": "Package install log, PyTorch version, and CUDA availability.",
        "interpretation": "Confirms the Colab runtime has graph, sequence, tuning, and explainability dependencies before any experiment logic runs.",
        "rerun_note": "Safe to rerun when the Colab runtime restarts or a package install fails.",
        "purpose_of_code": "Bootstraps the Colab environment so every later block has the libraries it expects.",
    },
    1: {
        "outputs": "Seed confirmation, device selection, Google Drive mount, storage paths, and experiment constants.",
        "interpretation": "Shows whether the run is using GPU, where persistent artifacts will be saved, and which global hyperparameters govern the experiment.",
        "prerequisites": (0,),
        "rerun_note": "Safe to rerun when you want to change paths or Colab storage settings.",
        "purpose_of_code": "Centralizes reproducibility, storage, and experiment-wide configuration in one place.",
    },
    2: {
        "outputs": "Merged raw dataframe, label normalization summary, stage counts, and detected label columns.",
        "interpretation": "Confirms the dataset was read successfully and that the kill-chain labels align with the five target stages.",
        "prerequisites": (1,),
        "rerun_note": "Rerun this block only when the dataset path or source files change.",
        "purpose_of_code": "Loads the full Unraveled dataset into a single analysis-ready frame while preserving temporal provenance.",
    },
    3: {
        "prerequisites": (2,),
        "rerun_note": "Safe to rerun for fresh visuals without retraining any models.",
        "purpose_of_code": "Explains the raw data before modeling through class balance, temporal behavior, and feature-separation visuals.",
    },
    4: {
        "outputs": "Cleaned feature dataframe, leakage/identity-feature removal, encoded time features, and preprocessing summary.",
        "interpretation": "Shows how raw network-flow data is converted into a model-ready table while reducing leakage and preserving temporal signal.",
        "prerequisites": (2,),
        "rerun_note": "Rerun this block when you change preprocessing logic or feature inclusion rules.",
        "purpose_of_code": "Transforms the raw flow table into a consistent numerical feature space for downstream tabular, graph, and sequence models.",
    },
    5: {
        "outputs": "Train/validation/test dataframes, split summary tables, minority-stage coverage checks, and split visuals.",
        "interpretation": "Verifies that temporal causality is respected and that rare APT stages remain represented in all evaluation splits.",
        "prerequisites": (4,),
        "rerun_note": "Rerun when you adjust split policy or want to inspect class coverage again.",
        "purpose_of_code": "Builds the temporally valid experimental split that the rest of the benchmark depends on.",
    },
    6: {
        "outputs": "Lists of PyG graph windows for train, validation, and test sets, plus graph-construction diagnostics.",
        "interpretation": "Confirms the tabular split was successfully converted into graph windows for the graph models.",
        "prerequisites": (5,),
        "rerun_note": "Rerun when you change graph window size, stride, or KNN graph settings.",
        "purpose_of_code": "Constructs graph-structured training data from sequential flow windows.",
    },
    7: {
        "outputs": "Class-balanced focal loss, kill-chain distance loss, monotonic penalty, and training class-count summary.",
        "interpretation": "Shows how imbalance handling and kill-chain-aware supervision are encoded before model training begins.",
        "prerequisites": (6,),
        "rerun_note": "Rerun when you change beta, gamma, or kill-chain penalty settings.",
        "purpose_of_code": "Defines the shared objective functions used to train and compare the models.",
    },
    8: {
        "outputs": "Central results tracker object, comparison table scaffold, and model-comparison visualization hooks.",
        "interpretation": "Creates the single source of truth that every model block writes to, which makes reruns modular instead of forcing the whole benchmark to repeat.",
        "prerequisites": (7,),
        "rerun_note": "Run this once before model blocks. After that, individual model blocks can be rerun independently.",
        "purpose_of_code": "Initializes shared experiment tracking so each model block can be trained and evaluated independently.",
    },
    9: {
        "outputs": "MLP metrics, confusion matrix, SHAP visuals, and tracker updates.",
        "interpretation": "Provides the non-graph baseline and feature-attribution reference against which all graph and sequence models are judged.",
        "prerequisites": (8,),
        "rerun_note": "Can be rerun independently after blocks 0-8 are complete.",
        "purpose_of_code": "Establishes the tabular baseline and interpretable feature-importance benchmark.",
    },
    10: {
        "outputs": "GATv2 training curves, confusion matrix, Optuna result, and tracker updates.",
        "interpretation": "Shows how attention-based graph modeling performs on the same split and where it succeeds or fails by stage.",
        "prerequisites": (8,),
        "rerun_note": "Can be rerun independently after blocks 0-8 are complete.",
        "purpose_of_code": "Benchmarks an attention-based graph classifier on the shared graph windows.",
    },
    11: {
        "outputs": "R-GCN training curves, confusion matrix, Optuna result, and tracker updates.",
        "interpretation": "Shows whether typed graph relations help recover stage-specific signal, especially for later kill-chain behavior.",
        "prerequisites": (8,),
        "rerun_note": "Can be rerun independently after blocks 0-8 are complete.",
        "purpose_of_code": "Tests whether explicit edge semantics improve graph reasoning over APT traffic.",
    },
    12: {
        "outputs": "GIN training curves, confusion matrix, Optuna result, and tracker updates.",
        "interpretation": "Shows how a high-expressivity structure-focused GNN behaves on the same graph windows.",
        "prerequisites": (8,),
        "rerun_note": "Can be rerun independently after blocks 0-8 are complete.",
        "purpose_of_code": "Benchmarks a structure-sensitive graph model that emphasizes subgraph discrimination.",
    },
    13: {
        "outputs": "DGI pretraining summary, downstream classifier metrics, confusion matrix, and tracker updates.",
        "interpretation": "Shows whether self-supervised graph pretraining improves downstream stage classification.",
        "prerequisites": (8,),
        "rerun_note": "Can be rerun independently after blocks 0-8 are complete.",
        "purpose_of_code": "Evaluates a self-supervised graph learning baseline before supervised fine-tuning.",
    },
    14: {
        "outputs": "ST-GCN metrics, training curves, confusion matrix, and tracker updates.",
        "interpretation": "Shows whether temporal graph modeling adds value beyond the static graph baselines.",
        "prerequisites": (8,),
        "rerun_note": "Can be rerun independently after blocks 0-8 are complete.",
        "purpose_of_code": "Benchmarks a temporal graph baseline over the same flow windows.",
    },
    15: {
        "outputs": "Mamba metrics, training curves, confusion matrix, checkpoint, and tracker updates.",
        "interpretation": "Provides the sequence-model baseline without kill-chain conditioning and is the key comparison point for the later novel Mamba variant.",
        "prerequisites": (8,),
        "rerun_note": "Can be rerun independently after blocks 0-8 are complete.",
        "purpose_of_code": "Evaluates a pure sequence baseline over graph-derived flow sequences.",
    },
    16: {
        "outputs": "Decision-gate summary and recommendation for whether to continue with the novelty phase.",
        "interpretation": "Reads the current baseline results, especially Data Exfiltration behavior, and decides whether the evidence justifies moving on to the new models.",
        "prerequisites": (9, 10, 11, 12, 13, 14, 15),
        "rerun_note": "Rerun after any baseline model changes to refresh the novelty decision.",
        "purpose_of_code": "Turns the Phase 1 baseline results into a concrete go/no-go decision for the novel models.",
    },
    17: {
        "outputs": "APT-Mamba metrics, training curves, confusion matrix, checkpoint, and tracker updates.",
        "interpretation": "Shows whether explicit kill-chain conditioning improves the Mamba baseline on later attack stages.",
        "prerequisites": (8, 15, 16),
        "rerun_note": "Can be rerun independently after blocks 0-8 and the baseline decision gate are complete.",
        "purpose_of_code": "Implements and evaluates the first novel contribution: kill-chain-conditioned Mamba.",
    },
    18: {
        "outputs": "KC-CWT metrics, attention heatmap, confusion matrix, checkpoint, and tracker updates.",
        "interpretation": "Shows whether a kill-chain-aware causal-window Transformer can outperform the baseline sequence and graph models.",
        "prerequisites": (8, 15, 16),
        "rerun_note": "Can be rerun independently after blocks 0-8 and the baseline decision gate are complete.",
        "purpose_of_code": "Implements and evaluates the second novel contribution: the kill-chain causal-window Transformer.",
    },
    19: {
        "outputs": "Final comparison tables, per-stage heatmaps, DE-focused metrics, ablation waterfall, and saved CSV/PNG artifacts.",
        "interpretation": "Consolidates the complete benchmark into dissertation-ready comparison outputs across all baseline and novel models.",
        "prerequisites": (8, 9, 10, 11, 12, 13, 14, 15, 17, 18),
        "rerun_note": "Rerun after any model block to regenerate the final paper-ready tables and visuals.",
        "purpose_of_code": "Produces the full experiment summary so the benchmark can be reviewed, exported, and written up.",
    },
}


@dataclass(frozen=True)
class BlockDefinition:
    number: int
    title: str
    purpose: str = ""
    outputs: str = ""
    interpretation: str = ""
    code: str = ""
    prerequisites: tuple[int, ...] = ()
    rerun_note: str = ""
    purpose_of_code: str = ""


@dataclass
class PraxisV04Runner:
    source_path: Path
    blocks: dict[int, BlockDefinition]
    namespace: dict[str, Any] = field(default_factory=dict)
    executed_blocks: list[int] = field(default_factory=list)

    @classmethod
    def from_file(cls, source_path: str | Path) -> "PraxisV04Runner":
        path = Path(source_path).resolve()
        blocks = parse_experiment_blocks(path)
        namespace = {
            "__name__": "__praxisv04__",
            "__builtins__": builtins.__dict__,
            "__file__": str(path),
        }
        return cls(source_path=path, blocks=blocks, namespace=namespace)

    def catalog_rows(self) -> list[str]:
        rows = []
        for block in self.blocks.values():
            prereq = ", ".join(str(item) for item in block.prerequisites) or "None"
            rows.append(f"{block.number:02d} | {block.title} | {prereq}")
        return rows

    def catalog_markdown(self) -> str:
        lines = [
            "## Praxisv04 Block Catalog",
            "",
            "| Block | Title | Recommended Prerequisites |",
            "|---|---|---|",
        ]
        for block in self.blocks.values():
            prereq = ", ".join(str(item) for item in block.prerequisites) or "None"
            lines.append(f"| {block.number:02d} | {block.title} | {prereq} |")
        lines.extend(
            [
                "",
                "After blocks `0-8` complete, blocks `9-18` can be rerun independently.",
                "Block `19` regenerates the final tables and visuals from the current tracker state.",
            ]
        )
        return "\n".join(lines)

    def render_block_markdown(self, block_number: int) -> str:
        block = self.blocks[block_number]
        lines = [f"## Block {block.number:02d}: {block.title}", ""]
        if block.purpose_of_code:
            lines.append(f"**Purpose Of The Code**  ")
            lines.append(block.purpose_of_code)
            lines.append("")
        if block.purpose:
            lines.append(f"**Purpose**  ")
            lines.append(block.purpose)
            lines.append("")
        if block.outputs:
            lines.append(f"**Expected Outputs**  ")
            lines.append(block.outputs)
            lines.append("")
        if block.interpretation:
            lines.append(f"**How To Read The Output**  ")
            lines.append(block.interpretation)
            lines.append("")
        prereq = ", ".join(str(item) for item in block.prerequisites) or "None"
        lines.append(f"**Recommended Prerequisites**  `{prereq}`")
        if block.rerun_note:
            lines.append("")
            lines.append(f"**Modular Rerun Note**  ")
            lines.append(block.rerun_note)
        return "\n".join(lines)

    def display_catalog(self) -> str:
        markdown = self.catalog_markdown()
        try:
            from IPython.display import Markdown, display

            display(Markdown(markdown))
        except Exception:
            print(markdown)
        return markdown

    def display_block(self, block_number: int) -> str:
        markdown = self.render_block_markdown(block_number)
        try:
            from IPython.display import Markdown, display

            display(Markdown(markdown))
        except Exception:
            print(markdown)
        return markdown

    def run_block(self, block_number: int, show_description: bool = True) -> dict[str, Any]:
        if block_number not in self.blocks:
            raise KeyError(f"Unknown block: {block_number}")
        block = self.blocks[block_number]
        if show_description:
            self.display_block(block_number)
        compiled = compile(
            block.code,
            filename=f"{self.source_path.name}::block_{block.number:02d}",
            mode="exec",
        )
        exec(compiled, self.namespace)
        if block_number not in self.executed_blocks:
            self.executed_blocks.append(block_number)
        return self.namespace

    def run_blocks(self, block_numbers: list[int], show_description: bool = True) -> dict[str, Any]:
        for block_number in block_numbers:
            self.run_block(block_number, show_description=show_description)
        return self.namespace


def default_source_path(repo_root: str | Path | None = None) -> Path:
    base = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    return base / "references" / "APT_Praxis_Colab_Experiment.py"


def load_default_runner(repo_root: str | Path | None = None) -> PraxisV04Runner:
    return PraxisV04Runner.from_file(default_source_path(repo_root))


def parse_experiment_blocks(source_path: str | Path) -> dict[int, BlockDefinition]:
    path = Path(source_path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    starts: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        match = BLOCK_START_RE.match(line)
        if match:
            starts.append((int(match.group(1)), idx, match.group(2).strip()))

    blocks: dict[int, BlockDefinition] = {}
    for position, (number, start_idx, title) in enumerate(starts):
        end_idx = starts[position + 1][1] if position + 1 < len(starts) else len(lines)
        block_lines = lines[start_idx:end_idx]
        purpose = ""
        outputs = ""
        interpretation = ""
        current_section: str | None = None

        for line in block_lines:
            if match := PURPOSE_RE.match(line):
                purpose = match.group(1).strip()
                current_section = "purpose"
                continue
            if match := OUTPUT_RE.match(line):
                outputs = match.group(1).strip()
                current_section = "outputs"
                continue
            if match := INTERPRETATION_RE.match(line):
                interpretation = match.group(1).strip()
                current_section = "interpretation"
                continue

            if current_section and not line.startswith("#"):
                current_section = None
                continue

            if current_section and line.startswith("#"):
                comment = line[1:].strip()
                if _is_decorative_comment(comment) or ":" in comment[:20]:
                    continue
                if comment:
                    if current_section == "purpose":
                        purpose = f"{purpose} {comment}".strip()
                    elif current_section == "outputs":
                        outputs = f"{outputs} {comment}".strip()
                    elif current_section == "interpretation":
                        interpretation = f"{interpretation} {comment}".strip()

        manual = MANUAL_BLOCK_NOTES.get(number, {})
        blocks[number] = BlockDefinition(
            number=number,
            title=title,
            purpose=purpose or str(manual.get("purpose", "")),
            outputs=outputs or str(manual.get("outputs", "")),
            interpretation=interpretation or str(manual.get("interpretation", "")),
            code="\n".join(block_lines).strip() + "\n",
            prerequisites=tuple(manual.get("prerequisites", ())),
            rerun_note=str(manual.get("rerun_note", "")),
            purpose_of_code=str(manual.get("purpose_of_code", "")),
        )
    return dict(sorted(blocks.items()))


def _is_decorative_comment(comment: str) -> bool:
    if not comment:
        return True
    stripped = comment.replace(" ", "")
    if stripped.startswith("BLOCK"):
        return True
    return not any(char.isalnum() for char in stripped)
