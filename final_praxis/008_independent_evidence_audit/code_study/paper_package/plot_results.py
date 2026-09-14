"""Render published estimates directly; no new tests, subsets or fitted models."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(path, output, label):
    payload = path.read_bytes()
    report = json.loads(payload)
    flow_path = path.with_name('FLOW_AND_COSTS.json')
    flow = json.loads(flow_path.read_bytes())
    rows = report["primary_hypotheses"]
    if len(rows) != 4:
        raise ValueError("The four registered primary comparisons are required")
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8), sharey=True)
    names = {"qwen.qwen3-coder-next": "Qwen3 Coder Next", "mistral.devstral-2-123b": "Devstral 2"}
    models = report["configuration"]["reviewers"]
    for ax, hypothesis, title in zip(axes, ("H1", "H2"),
                                    ("H1: selective witness effect", "H2: hybrid verification effect")):
        part = [r for r in rows if r["hypothesis"].startswith(hypothesis)]
        if len(part) != 2:
            raise ValueError("Expected one contrast per reviewer")
        bounds = [0.0]
        ax.axvline(0, color="#777777", linestyle="--", linewidth=.8)
        for r in part:
            y = models.index(r["reviewer"])
            valid = flow['technical_gates']['native_heldout']['models'][r['reviewer']]['valid']
            if valid == 0:
                ax.text(0, y, 'No valid heldout reviews', ha='center', va='center', color='#666666')
                continue
            if r["difference"] is None or r["ci95"] is None:
                ax.text(0, y, "No eligible estimate", ha="center", va="center")
                continue
            estimate = r["difference"] * 100
            lo, hi = [v * 100 for v in r["ci95"]]
            bounds.extend([lo, hi])
            ax.errorbar(estimate, y, xerr=[[max(0, estimate - lo)], [max(0, hi - estimate)]],
                        fmt="o", color="#24526d", markersize=6, linewidth=1.5, capsize=4)
            ax.annotate(f"{estimate:+.1f} pp; adjusted p={r['holm4_adjusted_p']:.3g}",
                        (estimate, y), xytext=(0, 15), textcoords="offset points", ha="center", fontsize=8)
        span = max(10, max(bounds) - min(bounds))
        ax.set_xlim(min(bounds) - .25 * span, max(bounds) + .25 * span)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Harmful acceptance increase (pp)" if hypothesis == "H1" else "Harmful acceptance reduction (pp)")
        ax.set_yticks(range(len(models)), [names.get(m, m) for m in models])
        ax.set_ylim(-.5, len(models) - .35)
        ax.grid(axis="x", color="#e4e7e9", linewidth=.6)
    axes[0].invert_yaxis()
    fig.suptitle(label, fontsize=13, y=.97)
    fig.text(.5, .025, "Points: paired differences. Bars: 95% task-cluster bootstrap intervals. Holm correction includes all four tests.\nH1 uses reviewer decisions; H2 includes the same authenticated-failure veto in both arms.", ha="center", fontsize=8)
    fig.subplots_adjust(left=.16, right=.98, top=.78, bottom=.24, wspace=.2)
    fig.savefig(output / "primary_effects.png", dpi=220)
    fig.savefig(output / "primary_effects.svg", metadata={"Date": None})
    plt.close(fig)
    receipt = {"source_results_sha256": hashlib.sha256(payload).hexdigest(),
               "source_flow_sha256": hashlib.sha256(flow_path.read_bytes()).hexdigest(),
               "plot_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "matplotlib_version": matplotlib.__version__, "analysis_recomputed": False,
               "outputs": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in ("primary_effects.png", "primary_effects.svg")}}
    (output / "PLOT_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("results", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument('--label', default='Schema extension: registered heldout native-code comparisons')
    args = p.parse_args()
    plot(args.results, args.output, args.label)
