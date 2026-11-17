"""Study 3, H2, the "why": Layer 3 for the five classifiers, one figure.

    python3 -I -B code/h2_features/fig_h2_features_five.py

Drawn from results_h2_features/five_classifiers/tables/T_five_by_stage.csv and from
nothing else. PNG at 300 dpi and SVG, in the Pass 1 figure style (through
fig_h2_features.py, which imports the frozen constants).
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fig_h2_features as G                                  # style, labels, ink_on

plt, Rectangle = G.plt, G.Rectangle
W, FS, INK, MUTED, RAMP = G.W, G.FS, G.INK, G.MUTED, G.RAMP
OUT = os.path.join(G.OUT, "five_classifiers")
MODELS = [("lr", "LR"), ("rf", "RF"), ("gb", "GB"), ("hgb", "HGB"), ("xgb", "XGBoost")]
GROUPS = [("1_4", "D"), ("5", "E"), ("7", "L")]
LABEL = dict(G.LABEL)
LABEL.update({"cmd_count": "Commands in window*", "ctx_cmd_count": "Commands, last 2 min", "gap_min": "Shortest gap",
              "exec_distinct": "Distinct programs started", "prog_distinct": "Distinct program names",
              "exec_count": "Programs started, window", "gap_max": "Longest gap", "gap_mean": "Mean gap",
              "gap_median": "Median gap", "proc_depth_max": "Deepest process chain"})
LABEL = {k: v.replace(", last 2 min", ", 2 min") for k, v in LABEL.items()}      # narrower label column here
VMAX = 0.30


def main():
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    with open(os.path.join(OUT, "tables", "T_five_by_stage.csv"), encoding="utf-8", newline="") as f:
        feats = list(csv.DictReader(f))
    n = len(feats)
    rh, cw, gap = 0.245, 0.245, 0.06
    LW = 1.72 + 0.42
    top, bottom = 0.62, 0.78
    H = top + n * rh + bottom
    fig = plt.figure(figsize=(W, H))
    y0 = bottom / H
    lab = fig.add_axes([0.09 / W, y0, LW / W, n * rh / H])
    lab.set_xlim(0, 1)
    lab.set_ylim(n, 0)
    lab.axis("off")
    for i, r in enumerate(feats):
        lab.text(0.0, i + 0.53, LABEL.get(r["column"], r["column"]), ha="left", va="center", fontsize=FS - 0.5, color=INK)
        lab.text(0.985, i + 0.53, G.TIER[r["tier"]], ha="right", va="center", fontsize=FS - 1.5, color=MUTED)
    lab.text(0.985, -0.2, "Tier", ha="right", va="bottom", fontsize=FS - 2, color=INK)
    for bi, (m, mname) in enumerate(MODELS):
        x0 = (0.09 + LW + bi * (3 * cw + gap)) / W
        ax = fig.add_axes([x0, y0, 3 * cw / W, n * rh / H])
        ax.set_xlim(0, 3)
        ax.set_ylim(n, 0)
        ax.axis("off")
        for i, r in enumerate(feats):
            for j, (g, _) in enumerate(GROUPS):
                k = "%s_s%s" % (m, g)
                v, rank, sep = float(r[k + "_share"]), int(r[k + "_rank"]), float(r[k + "_mean_shap_ai_minus_human"])
                t = min(1.0, v / VMAX)
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=RAMP(t), edgecolor="#ffffff", linewidth=1.3))
                ax.text(j + 0.5, i + 0.53, "%d%s" % (round(100 * v), "†" if (sep < 0 and rank <= 10) else ""), ha="center", va="center",
                        fontsize=FS - 2, color=G.ink_on(RAMP(t)), fontweight="bold" if rank <= 5 else "normal")
        for j, (_, gl) in enumerate(GROUPS):
            ax.text(j + 0.5, -0.2, gl, ha="center", va="bottom", fontsize=FS - 2, color=MUTED)
        ax.text(1.5, -1.05, mname, ha="center", va="bottom", fontsize=FS - 0.5, color=INK)
    fig.text(0.09 / W, 1 - 0.07 / H, "Layer 3 for the five classifiers: share of mean |SHAP| by stage group, %",
             ha="left", va="top", fontsize=FS, color=INK)
    fig.text(0.09 / W, 0.07 / H,
             "D discovery, E execution, L lateral movement and collection.   2 min: over the last two minutes.\n"
             "Bold: in that classifier's top five for the stage group.   Rows: every column in any classifier's top five.\n"
             "†: on balance the column moves AI windows toward human (marked in a classifier's top ten).\n"
             "* For LR and GB this row includes their added input, \"the window has commands\".",
             ha="left", va="bottom", fontsize=FS - 2, color=MUTED, linespacing=1.35)
    fig.savefig(os.path.join(OUT, "figures", "H2_features_five_classifiers.png"), dpi=300, metadata={"Software": None})
    fig.savefig(os.path.join(OUT, "figures", "H2_features_five_classifiers.svg"), metadata={"Date": None, "Creator": "study 3"})
    plt.close(fig)
    print("figure written:", n, "rows")


if __name__ == "__main__":
    main()
