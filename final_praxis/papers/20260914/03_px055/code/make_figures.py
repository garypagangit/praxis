"""Render scientific figures only from verified local reproduction outputs."""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__ == "__main__":
    source = ROOT / "results/RECOMPUTED_RESULTS.json"
    receipt = json.loads((ROOT / "results/REPRODUCTION_RECEIPT.json").read_text())
    assert receipt["pass"] and digest(source) == receipt["recomputed_results_sha256"]
    a = json.loads(source.read_text())
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(10.8, 3.6), sharey=True)
    for ax, m in zip(axes, a["models"]):
        for c, label, color in [("bnb_int8", "INT8", "#21618c"), ("bnb_nf4", "NF4", "#b85d1a")]:
            r = [r for r in m["e1_cells"] if r["condition"] == c]
            ax.plot([x["layer"] for x in r], [x["cosine_vs_fp16"] for x in r], "o-", ms=4, color=color, label=label)
        ax.axhline(.95, color="#555555", ls="--", lw=1)
        ax.set(title=m["model_key"].capitalize(), xlabel="FP16-selected layer", ylim=(.945, 1.002))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Signed cosine vs FP16")
    axes[0].legend(frameon=False, loc="lower left", bbox_to_anchor=(.015, .10))
    fig.suptitle("Geometry remains above the registered 0.95 threshold", y=1.02)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/geometry_stability.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 3.6))
    keys = ["qwen", "llama", "gemma"]
    x = np.arange(3)
    for i, (c, label, color) in enumerate([("fp16", "FP16", "#596d7d"), ("bnb_int8", "INT8", "#21618c"), ("bnb_nf4", "NF4", "#b85d1a")]):
        axes[0].bar(x + (i - 1) * .23, [a["behavior"][k][c]["utility_balanced_accuracy"] for k in keys], width=.22, color=color, label=label)
    axes[0].set_xticks(x, [k.capitalize() for k in keys])
    axes[0].set(ylim=(0, 1), ylabel="Lexicon-defined balanced accuracy", title="XSTest behavior: 450 prompts per cell")
    axes[0].legend(frameon=False, ncol=3, fontsize=9, loc="upper center", bbox_to_anchor=(.5, -.13))
    delta = [a["e4"]["models"][k]["restoration_delta"] * 100 for k in keys]
    ci = [a["e4"]["models"][k]["bootstrap_ci_95"] for k in keys]
    err = np.array([[delta[i] - ci[i][0] * 100 for i in range(3)], [ci[i][1] * 100 - delta[i] for i in range(3)]])
    axes[1].errorbar(x, delta, yerr=err, fmt="o", color="#21618c", capsize=5)
    axes[1].axhline(0, color="#555555", lw=1)
    axes[1].axhline(5, color="#b85d1a", ls="--", lw=1, label="Required effect: +5 points")
    axes[1].set_xticks(x, [k.capitalize() for k in keys])
    axes[1].set(ylabel="NF4 minus FP16, percentage points", title="E4 safe-text projection proxy (95% CI)", ylim=(-9, 9))
    axes[1].legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(.5, -.13))
    fig.tight_layout()
    fig.savefig(ROOT / "figures/behavior_and_proxy.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    (ROOT / "results/FIGURE_RECEIPT.json").write_text(json.dumps({"source_results_sha256": digest(source), "script_sha256": digest(Path(__file__)), "matplotlib": matplotlib.__version__, "figures": [{"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p)} for p in sorted((ROOT / "figures").glob("*.png"))]}, indent=2) + "\n")
