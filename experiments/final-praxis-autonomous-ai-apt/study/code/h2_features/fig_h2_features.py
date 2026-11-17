"""Study 3, H2, the "why": the one figure, three panels.

    python3 -I -B code/h2_features/fig_h2_features.py

Drawn from the CSV tables in results_h2_features/tables/ and from nothing else, so each
plotted number can be traced. PNG at 300 dpi and SVG, in the Pass 1 figure style (the
constants come from the frozen `code/eda/pass1_figures.py`, which is imported, not
edited): 6.2 in wide, text 9 pt or just under, one blue ramp for magnitude, no second
axis. Identity never rests on color alone: the three configurations of panel A differ
by marker shape and fill.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ROOT = os.path.dirname(CODE)
_LIBS = os.environ.get("S3_LIBS")
if _LIBS and _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)
sys.path.insert(0, os.path.join(CODE, "eda"))
import pass1_figures as P1                                   # frozen; style only

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

OUT = os.path.join(ROOT, "results_h2_features")
TABLES = os.path.join(OUT, "tables")
FIGURES = os.path.join(OUT, "figures")
W, FS, INK, MUTED, GRID, RAMP = P1.WIDTH_IN, P1.FS, P1.INK, P1.MUTED, P1.GRID, P1.RAMP
BLUE, RANGE = "#1c5cab", "#a9a8a3"
GROUPS = ["1-4", "5", "7"]
KEY = {"1-4": "s1_4", "5": "s5", "7": "s7"}
HEAD = {"1-4": "Discovery", "5": "Execution", "7": "Lateral\nmovement"}
ROWNAME = {"1-4": "Discovery\n(stages 1–4)", "5": "Execution\n(stage 5)", "7": "Lateral movement\nand collection (stage 7)"}
TIER = {"behavior": "behavior", "command_content": "content", "context": "context"}
LABEL = {
    "ctx_chars_submitted": "Command text, last 2 min", "ctx_cmd_len_max": "Longest command, last 2 min",
    "chars_submitted": "Command text, window", "output_bytes": "Program output, window",
    "ctx_exec_count": "Programs started, last 2 min", "ctx_output_bytes": "Program output, last 2 min",
    "ctx_active_windows": "Active windows, last 2 min", "exec_per_cmd": "Programs per command",
    "cmd_len_max": "Longest command, window", "pipes_per_cmd": "Pipes per command",
    "output_per_cmd_mean": "Output per command", "ctx_cmd_diversity": "Command diversity, last 2 min",
    "flags_per_cmd": "Flags per command", "cmd_len_mean": "Mean command length",
    "redirect_ratio": "Commands with a redirect", "chain_ratio": "Commands that chain",
    "gap_min": "Shortest gap between commands", "gap_max": "Longest gap between commands",
    "exec_distinct": "Distinct programs started",
}
CONFIG = [("main", "All 40 columns", dict(marker="o", mfc=BLUE)),
          ("no_context", "No context (32)", dict(marker="s", mfc="#ffffff")),
          ("no_command_content", "No command content (22)", dict(marker="^", mfc="#ffffff"))]


def rows(name):
    with open(os.path.join(TABLES, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(s):
    return None if s in ("", None) else float(s)


def panel_a(fig, box):
    ax = fig.add_axes(box)
    l2 = rows("L2_tiers_by_stage_group.csv")
    val = {}
    for r in l2:
        if r["stage_group"] in GROUPS:
            val[("main", r["model"], r["stage_group"])] = num(r["macro_f1_main"])
            other = "no_command_content" if r["difference"] == "command_content_adds" else "no_context"
            val[(other, r["model"], r["stage_group"])] = num(r["macro_f1_without"])
    models = sorted(set(k[1] for k in val))
    off = {"main": -0.25, "no_context": 0.0, "no_command_content": 0.25}
    for gi, g in enumerate(GROUPS):
        for cfg, _, mk in CONFIG:
            y = gi + off[cfg]
            five = [val[(cfg, m, g)] for m in models]
            ax.plot([min(five), max(five)], [y, y], color=RANGE, lw=2.0, solid_capstyle="round", zorder=2)
            x = val[(cfg, "xgb", g)]
            ax.plot([x], [y], ls="none", ms=6.0, mec=BLUE, mew=1.2, zorder=3, **mk)
            ax.text(1.045, y, "%.3f" % x, va="center", ha="left", fontsize=FS - 1.5, color=INK,
                    transform=ax.get_yaxis_transform())
    ax.set_ylim(len(GROUPS) - 0.5, -0.5)
    ax.set_yticks(range(len(GROUPS)))
    ax.set_yticklabels([ROWNAME[g] for g in GROUPS], fontsize=FS - 0.5)
    ax.text(1.045, -0.56, "XGBoost", va="center", ha="left", fontsize=FS - 1.5, color=MUTED,
            transform=ax.get_yaxis_transform())
    ax.set_xlim(0.5, 1.0)
    ax.set_xticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_xlabel("Held-out macro-F1 within the stage group", fontsize=FS - 0.5)
    ax.tick_params(axis="x", labelsize=FS - 1)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    P1.clean_axes(ax, keep=("bottom",))
    hand = [Line2D([0], [0], ls="none", ms=6.0, mec=BLUE, mew=1.2, **mk) for _, _, mk in CONFIG]
    hand.append(Line2D([0], [0], color=RANGE, lw=2.0))
    ax.legend(hand, [lab for _, lab, _ in CONFIG] + ["Range, five classifiers"], loc="center left",
              bbox_to_anchor=(1.27, 0.5), frameon=False, fontsize=FS - 1, handletextpad=0.5, labelspacing=0.7,
              title="Markers: XGBoost", title_fontsize=FS - 1, alignment="left")
    fig.text(0.09 / W, box[1] + box[3] + 0.21 / fig.get_figheight(),
             "A. Layer 2: held-out macro-F1 with all columns and with one tier removed", ha="left", va="bottom",
             fontsize=FS, color=INK)


def ink_on(rgba):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgba[:3]]
    return "#ffffff" if 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2] < 0.18 else INK


def heat(fig, x0, y0, cw, rh, feats, key, title, title2, sub, fmt, lo, hi, dagger):
    n = len(feats)
    ax = fig.add_axes([x0, y0, 3 * cw, n * rh])
    ax.set_xlim(0, 3)
    ax.set_ylim(n, 0)
    ax.axis("off")
    for i, r in enumerate(feats):
        for j, g in enumerate(GROUPS):
            v = num(r[KEY[g] + key[0]])
            rank = num(r[KEY[g] + key[1]])
            t = 0.0 if v is None else min(1.0, max(0.0, (v - lo) / (hi - lo)))
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=RAMP(t), edgecolor="#ffffff", linewidth=1.6))
            mark = "†" if (dagger and num(r[KEY[g] + "_L3_mean_shap_ai_minus_human"]) < 0) else ""
            ax.text(j + 0.5, i + 0.53, fmt(v) + mark, ha="center", va="center", fontsize=FS - 1.5,
                    color=ink_on(RAMP(t)), fontweight="bold" if rank is not None and rank <= 5 else "normal")
    for j, g in enumerate(GROUPS):
        ax.text(j + 0.5, -0.2, HEAD[g], ha="center", va="bottom", fontsize=FS - 2, color=INK, linespacing=1.0)
    ax.text(0, -2.85, title, ha="left", va="bottom", fontsize=FS, color=INK)
    ax.text(0, -2.15, title2, ha="left", va="bottom", fontsize=FS - 0.5, color=INK)
    ax.text(0, -1.5, sub, ha="left", va="bottom", fontsize=FS - 1.5, color=MUTED)
    return ax


def main():
    os.makedirs(FIGURES, exist_ok=True)
    t = rows("T_h2_features_by_stage.csv")
    feats = [r for r in t if r["row_type"] == "feature"]
    n = len(feats)
    H = 7.3
    fig = plt.figure(figsize=(W, H))
    panel_a(fig, [0.265, 1 - 1.62 / H, 0.335, 1.22 / H])
    rh = 0.232 / H
    cw = 0.575 / W
    y0 = 0.42 / H
    LW = 1.93 + 0.48
    xB = (0.09 + LW) / W
    xC = xB + 3 * cw + 0.18 / W
    heat(fig, xB, y0, cw, rh, feats, ("_L3_share", "_L3_rank"), "B. Layer 3", "What XGBoost relies on",
         "share of mean |SHAP|, %", lambda v: "%.1f" % (100 * v), 0.0, 0.22, True)
    heat(fig, xC, y0, cw, rh, feats, ("_L1_auc", "_L1_rank"), "C. Layer 1", "One column on its own",
         "AUC within the stage group", lambda v: "%.2f" % v, 0.5, 1.0, False)
    lab = fig.add_axes([0.09 / W, y0, LW / W, n * rh])
    lab.set_xlim(0, 1)
    lab.set_ylim(n, 0)
    lab.axis("off")
    for i, r in enumerate(feats):
        lab.text(0.0, i + 0.53, LABEL.get(r["name"], r["name"]), ha="left", va="center", fontsize=FS - 0.5, color=INK)
        lab.text(0.985, i + 0.53, TIER[r["tier"]], ha="right", va="center", fontsize=FS - 1.5, color=MUTED)
    lab.text(0.985, -0.2, "Tier", ha="right", va="bottom", fontsize=FS - 2, color=INK)
    fig.text(0.09 / W, 0.07 / H,
             "Bold: in the top five of that stage group.   †: on balance the column moves AI windows toward human.\n"
             "Rows: every column in the top five of a stage group in Layer 1 or Layer 3, by Layer 3 share over all windows.",
             ha="left", va="bottom", fontsize=FS - 1.5, color=MUTED, linespacing=1.35)
    fig.savefig(os.path.join(FIGURES, "H2_features_by_stage.png"), dpi=300, metadata={"Software": None})
    fig.savefig(os.path.join(FIGURES, "H2_features_by_stage.svg"), metadata={"Date": None, "Creator": "study 3"})
    plt.close(fig)
    print("figure written:", n, "feature rows")


if __name__ == "__main__":
    main()
