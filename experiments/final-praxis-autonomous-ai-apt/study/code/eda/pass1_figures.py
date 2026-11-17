"""EDA Pass 1, figures (handoff sections 5 and 9): E2, E3, E4, E6.

Every figure is drawn from the CSV tables in reports/eda/tables/ and from nothing else
(handoff rule 8), so each plotted number can be traced. PNG at 300 dpi and SVG.

Style (handoff section 9): 6.2 in wide; human blue, AI orange with a diagonal hatch;
humans first; four stage-group colors, always labeled; one blue ramp for magnitude;
no pie or donut chart and no second y-axis. Text is 9 pt in the file so that it stays
at or above 8 pt when the figure is placed 5.6 in wide.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import eda_common as E

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

WIDTH_IN = 6.2
FS = 9.0
INK = "#1f1f1f"
MUTED = "#5f5f5f"
GRID = "#d9d9d9"
NO_DATA = "#e4e3df"
CLASS_COLOR = {"human": "#2a78d6", "ai": "#eb6834"}
CLASS_HATCH = {"human": None, "ai": "////"}
STAGE_COLOR = {"1-4": "#1baf7a", "5": "#eda100", "6": "#e87ba4", "7": "#008300"}
STAGE_TEXT = {"1-4": INK, "5": INK, "6": INK, "7": "#ffffff"}
RAMP = LinearSegmentedColormap.from_list("blue_ramp", ["#cde2fb", "#0d366b"])

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": FS, "axes.titlesize": FS + 0.5, "axes.labelsize": FS,
    "xtick.labelsize": FS, "ytick.labelsize": FS, "legend.fontsize": FS,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK, "ytick.labelcolor": INK,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "hatch.linewidth": 0.7, "svg.hashsalt": "study3-eda", "svg.fonttype": "path",
    "figure.dpi": 100, "savefig.dpi": 300,
})


def fmt(n):
    return "{:,}".format(int(n))


def n_sessions(n):
    return "1 session" if int(n) == 1 else "%d sessions" % int(n)


def save(fig, name):
    os.makedirs(E.FIGURES, exist_ok=True)
    fig.savefig(os.path.join(E.FIGURES, name + ".png"), dpi=300, metadata={"Software": None})
    fig.savefig(os.path.join(E.FIGURES, name + ".svg"), metadata={"Date": None, "Creator": "study 3 EDA"})
    plt.close(fig)


def sessions_from_t1():
    rows = [r for r in E.read_table("T1_dataset_summary_by_session.csv") if r["row_type"] == "session"]
    ypos, y, prev = {}, 0.0, None
    for r in rows:                                   # humans first; a gap before the AI sessions
        if prev is not None and r["class"] != prev:
            y += 0.55
        ypos[r["session"]] = y
        y += 1.0
        prev = r["class"]
    return rows, ypos


def class_bar(ax, y, value, cls, height=0.72):
    ax.barh(y, value, height=height, color=CLASS_COLOR[cls], hatch=CLASS_HATCH[cls],
            edgecolor="#ffffff", linewidth=0.0, zorder=3)


def clean_axes(ax, keep=("left", "bottom")):
    for side in ("left", "right", "top", "bottom"):
        ax.spines[side].set_visible(side in keep)


def group_labels(ax, rows, ypos, x=-0.155):
    """Class names beside the session labels, so class never rests on color alone."""
    for cls in E.CLASSES:
        ys = [ypos[r["session"]] for r in rows if r["class"] == cls]
        ax.text(x, (min(ys) + max(ys)) / 2.0, E.CLASS_LABEL[cls], rotation=90, ha="center", va="center",
                transform=ax.get_yaxis_transform(), fontsize=FS, color=INK)


# ------------------------------------------------------------------------------------------ E2
def fig_e2():
    rows, ypos = sessions_from_t1()
    ov = {r["item"]: r for r in E.read_table("E2_overview.csv")}
    fig = plt.figure(figsize=(WIDTH_IN, 2.95))
    ax_t = fig.add_axes([0.012, 0.06, 0.325, 0.83])
    ax_b = fig.add_axes([0.445, 0.155, 0.27, 0.735])
    ax_c = fig.add_axes([0.81, 0.155, 0.18, 0.735])

    # left: text block
    ax_t.set_axis_off()
    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(0, 1)
    ax_t.add_patch(Rectangle((0, 0), 1, 1, facecolor="#f6f5f2", edgecolor="none", zorder=0))
    ax_t.text(0.04, 0.955, "Dataset overview", fontsize=FS + 0.5, fontweight="bold", va="top")
    pending = "Pass 2"
    lines = [
        ("Sessions", fmt(ov["sessions"]["all"]), False),
        ("human / AI", "%s / %s" % (ov["sessions"]["human"], ov["sessions"]["ai"]), True),
        ("Logins used", fmt(ov["logins_used"]["all"]), False),
        ("human / AI", "%s / %s" % (ov["logins_used"]["human"], ov["logins_used"]["ai"]), True),
        ("Raw records", fmt(ov["raw_records"]["all"]), False),
        ("Classifier input", fmt(ov["classifier_input_records"]["all"]), False),
        ("Kept windows", fmt(ov["kept_windows_30s"]["all"]), False),
        ("human / AI", "%s / %s" % (ov["kept_windows_30s"]["human"], ov["kept_windows_30s"]["ai"]), True),
        ("Window length", "%s s" % ov["window_length_s"]["all"], False),
        ("Feature columns", ov["feature_columns_by_tier"]["all"] or pending, False),
        ("Undefined columns", ov["columns_with_undefined_values"]["all"] or pending, False),
    ]
    y, step = 0.845, 0.0745
    for label, value, sub in lines:
        ax_t.text(0.10 if sub else 0.04, y, label, va="center", color=MUTED if sub else INK)
        ax_t.text(0.96, y, value, va="center", ha="right", color=MUTED if (sub or value == pending) else INK,
                  fontweight="normal" if (sub or value == pending) else "bold")
        y -= step

    # middle: kept windows per session
    top = max(int(r["kept_30s"]) for r in rows)
    for r in rows:
        v = int(r["kept_30s"])
        class_bar(ax_b, ypos[r["session"]], v, r["class"])
        ax_b.text(v + top * 0.025, ypos[r["session"]], fmt(v), va="center", ha="left")
    ax_b.set_yticks([ypos[r["session"]] for r in rows])
    ax_b.set_yticklabels([r["session"] for r in rows])
    ax_b.set_ylim(max(ypos.values()) + 0.6, -0.6)
    ax_b.set_xlim(0, top * 1.22)
    ax_b.set_xticks([0, 100, 200])
    ax_b.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax_b.set_axisbelow(True)
    ax_b.tick_params(axis="y", length=0)
    clean_axes(ax_b, keep=("bottom",))
    ax_b.set_xlabel("Kept 30 s windows")
    ax_b.set_title("Kept windows per session", loc="left", pad=6)
    for cls in E.CLASSES:
        ys = [ypos[r["session"]] for r in rows if r["class"] == cls]
        ax_b.text(top * 1.2, max(ys) - 0.5 if cls == "human" else min(ys) + 1.0, E.CLASS_LABEL[cls],
                  ha="right", va="center", color=INK, fontweight="bold")

    # right: class distribution
    n = {c: int(ov["kept_windows_30s"][c]) for c in E.CLASSES}
    p = {c: ov["kept_windows_30s_pct"][c] for c in E.CLASSES}
    for i, c in enumerate(E.CLASSES):
        ax_c.bar(i, n[c], width=0.62, color=CLASS_COLOR[c], hatch=CLASS_HATCH[c], edgecolor="#ffffff",
                 linewidth=0.0, zorder=3)
        ax_c.text(i, n[c] + max(n.values()) * 0.02, "%s\n%s%%" % (fmt(n[c]), p[c]), ha="center", va="bottom",
                  linespacing=1.15)
    ax_c.set_xticks([0, 1])
    ax_c.set_xticklabels([E.CLASS_LABEL[c] for c in E.CLASSES])
    ax_c.set_xlim(-0.55, 1.55)
    ax_c.set_ylim(0, max(n.values()) * 1.27)
    ax_c.set_yticks([0, 200, 400, 600])
    ax_c.yaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax_c.set_axisbelow(True)
    ax_c.tick_params(axis="x", length=0)
    clean_axes(ax_c, keep=("bottom",))
    ax_c.set_title("Class distribution", loc="left", pad=6)
    save(fig, "E2_dataset_summary")


# ------------------------------------------------------------------------------------------ E3, E6 grid
GRID_AXES = [0.118, 0.275, 0.632, 0.635]          # shared by E3 and E6 so they can be stacked
SIDE_AXES = [0.775, 0.275, 0.215, 0.635]
GRID_FIGSIZE = (WIDTH_IN, 2.95)


def grid_frame(fig, rows, ypos, grid):
    ax = fig.add_axes(GRID_AXES)
    bin_min = int(grid[0]["bin_minutes"])
    n_cols = max(int(g["bin_index"]) for g in grid) + 1
    ax.set_xlim(0, n_cols)
    ax.set_ylim(max(ypos.values()) + 0.5, -0.5)
    step = 30 // bin_min
    ax.set_xticks(list(range(0, n_cols + 1, step)))
    ax.set_xticklabels([str(i * bin_min) for i in range(0, n_cols + 1, step)])
    ax.set_xlabel("Elapsed working time (minutes), logins used laid end to end")
    ax.set_yticks([ypos[r["session"]] for r in rows])
    ax.set_yticklabels([r["session"] for r in rows])
    ax.tick_params(axis="y", length=0)
    clean_axes(ax, keep=("bottom",))
    group_labels(ax, rows, ypos)
    return ax, bin_min, n_cols


def fig_e3():
    rows, ypos = sessions_from_t1()
    grid = E.read_table("E3_E6_grid.csv")
    fig = plt.figure(figsize=GRID_FIGSIZE)
    ax, bin_min, n_cols = grid_frame(fig, rows, ypos, grid)
    cap = 10.0
    for g in grid:
        n = int(g["kept_windows"])
        color = NO_DATA if n == 0 else RAMP((min(n, cap) - 1) / (cap - 1))
        ax.add_patch(Rectangle((int(g["bin_index"]), ypos[g["session"]] - 0.4), 1, 0.8, facecolor=color,
                               edgecolor="#ffffff", linewidth=0.4))
    ax.set_title("Kept 30 s windows in each %d-minute bin" % bin_min, loc="left", pad=6)

    # key for the ramp, under the grid
    key = fig.add_axes([GRID_AXES[0], 0.04, 0.40, 0.058])
    key.set_xlim(0, 16.0)
    key.set_ylim(0, 1)
    key.set_axis_off()
    key.text(0.35, 0.5, "0", ha="center", va="center")
    key.add_patch(Rectangle((0.9, 0), 1, 1, facecolor=NO_DATA, edgecolor="#ffffff", linewidth=0.4))
    key.text(3.25, 0.5, "1", ha="center", va="center")
    for i in range(1, 11):
        key.add_patch(Rectangle((2.8 + i, 0), 1, 1, facecolor=RAMP((i - 1) / 9.0), edgecolor="#ffffff", linewidth=0.4))
    key.text(14.55, 0.5, "10", ha="center", va="center")
    fig.text(GRID_AXES[0] + 0.40 * (15.5 / 16.0), 0.069, "kept windows in the bin", ha="left", va="center")

    # right: kept windows per session, logged minutes as text
    ax2 = fig.add_axes(SIDE_AXES)
    top = max(int(r["kept_30s"]) for r in rows)
    for r in rows:
        v = int(r["kept_30s"])
        class_bar(ax2, ypos[r["session"]], v, r["class"], height=0.8)
        ax2.text(v + top * 0.04, ypos[r["session"]], "%d min" % round(float(r["logged_minutes"])),
                 va="center", ha="left")
    ax2.set_ylim(max(ypos.values()) + 0.5, -0.5)
    ax2.set_xlim(0, top * 1.75)
    ax2.set_xticks([0, 100, 200])
    ax2.set_yticks([])
    ax2.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax2.set_axisbelow(True)
    clean_axes(ax2, keep=("bottom",))
    ax2.set_xlabel("Kept windows")
    ax2.set_title("Session totals", loc="left", pad=6)
    save(fig, "E3_activity_by_elapsed_time")


def fig_e6():
    rows, ypos = sessions_from_t1()
    grid = E.read_table("E3_E6_grid.csv")
    ticks = E.read_table("E6_stage_acceptances.csv")
    fig = plt.figure(figsize=GRID_FIGSIZE)
    ax, bin_min, n_cols = grid_frame(fig, rows, ypos, grid)
    for g in grid:
        color = STAGE_COLOR[g["dominant_stage_group"]] if g["dominant_stage_group"] else NO_DATA
        ax.add_patch(Rectangle((int(g["bin_index"]), ypos[g["session"]] - 0.4), 1, 0.8, facecolor=color,
                               edgecolor="#ffffff", linewidth=0.4))
    for t in ticks:
        if t["elapsed_working_min"] == "":
            continue                                  # accepted in a login that is not used: not on this clock
        x = float(t["elapsed_working_min"]) / bin_min
        y = ypos[t["session"]]
        line, = ax.plot([x, x], [y - 0.5, y - 0.02], color="#000000", linewidth=1.0, solid_capstyle="butt", zorder=5)
        line.set_path_effects([patheffects.Stroke(linewidth=2.2, foreground="#ffffff"), patheffects.Normal()])
    ax.set_title("Stage group worked in most of each %d-minute bin's kept windows" % bin_min, loc="left", pad=6)

    handles = [Patch(facecolor=STAGE_COLOR[g], edgecolor="none", label=E.STAGE_GROUP_LABEL[g]) for g in E.STAGE_GROUPS]
    handles.append(Patch(facecolor=NO_DATA, edgecolor="none", label="No kept window"))
    handles.append(Line2D([0], [0], color="#000000", linewidth=1.0, marker="|", markersize=9, linestyle="none",
                          markeredgewidth=1.0, label="Stage accepted"))
    lax = fig.add_axes(SIDE_AXES)
    lax.set_axis_off()
    lax.legend(handles=handles, loc="upper left", bbox_to_anchor=(-0.02, 1.0), frameon=False, borderaxespad=0.0,
               handlelength=1.2, handleheight=1.0, labelspacing=0.75, handletextpad=0.6)
    fig.text(0.012, 0.094, "P009: the used login starts at stage 5; stages 1\u20134 were accepted in a login that is not used.",
             ha="left", va="center", color=MUTED)
    fig.text(0.012, 0.036, "P010: the three used logins are laid end to end; a validator outage separated them.",
             ha="left", va="center", color=MUTED)
    save(fig, "E6_stage_timeline")


# ------------------------------------------------------------------------------------------ E4
def fig_e4():
    rows, ypos = sessions_from_t1()
    t2s = {r["session"]: r for r in E.read_table("T2_kept_windows_by_stage_group_session.csv")
           if r["window_s"] == "30" and r["row_type"] == "session"}
    t2c = [r for r in E.read_table("T2_kept_windows_by_stage_group_class.csv") if r["window_s"] == "30"]
    fig = plt.figure(figsize=(WIDTH_IN, 3.15))
    ax = fig.add_axes([0.118, 0.255, 0.515, 0.66])
    top = max(int(r["kept_total"]) for r in t2s.values())
    for r in rows:
        s, left = r["session"], 0
        for g in E.STAGE_GROUPS:
            v = int(t2s[s]["kept_stage_" + g])
            if v == 0:
                continue
            ax.barh(ypos[s], v, left=left, height=0.74, color=STAGE_COLOR[g], edgecolor="#ffffff", linewidth=0.9, zorder=3)
            if v >= 0.085 * top:
                ax.text(left + v / 2.0, ypos[s], str(v), ha="center", va="center", color=STAGE_TEXT[g], zorder=4)
            left += v
        ax.text(left + top * 0.02, ypos[s], fmt(left), va="center", ha="left", fontweight="bold")
    ax.set_yticks([ypos[r["session"]] for r in rows])
    ax.set_yticklabels([r["session"] for r in rows])
    ax.set_ylim(max(ypos.values()) + 0.6, -0.6)
    ax.set_xlim(0, top * 1.14)
    ax.set_xticks([0, 50, 100, 150, 200])
    ax.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    clean_axes(ax, keep=("bottom",))
    group_labels(ax, rows, ypos, x=-0.19)
    ax.set_xlabel("Kept 30 s windows")
    ax.set_title("Kept windows per session, by stage group", loc="left", pad=6)

    ax2 = fig.add_axes([0.735, 0.255, 0.255, 0.66])
    for i, c in enumerate(E.CLASSES):
        bottom = 0.0
        for g in E.STAGE_GROUPS:
            row = next(r for r in t2c if r["class"] == c and r["stage_group"] == g)
            share = float(row["pct_of_class"])
            ax2.bar(i, share, bottom=bottom, width=0.6, color=STAGE_COLOR[g], edgecolor="#ffffff", linewidth=0.9, zorder=3)
            if share >= 6.0:
                ax2.text(i, bottom + share / 2.0, "%.0f%%" % share, ha="center", va="center", color=STAGE_TEXT[g], zorder=4)
            else:
                ax2.annotate("%.0f%%" % share, xy=(i + 0.3, bottom + share / 2.0), xytext=(i + 0.36, bottom + share / 2.0),
                             ha="left", va="center")
            bottom += share
    totals = {c: next(r for r in t2c if r["class"] == c and r["stage_group"] == "all")["kept_windows"] for c in E.CLASSES}
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["%s\nn = %s" % (E.CLASS_LABEL[c], fmt(totals[c])) for c in E.CLASSES])
    ax2.set_xlim(-0.5, 1.72)
    ax2.set_ylim(0, 100)
    ax2.set_yticks([0, 25, 50, 75, 100])
    ax2.set_ylabel("Share of the class's kept windows (%)")
    ax2.tick_params(axis="x", length=0)
    clean_axes(ax2, keep=("left",))
    ax2.set_title("Stage share by class", loc="left", pad=6)

    handles = [Patch(facecolor=STAGE_COLOR[g], edgecolor="none", label=E.STAGE_GROUP_LABEL[g]) for g in E.STAGE_GROUPS]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.118, 0.012), ncol=4, frameon=False,
               handlelength=1.2, handleheight=1.0, columnspacing=1.6, handletextpad=0.5, borderaxespad=0.0)
    save(fig, "E4_windows_by_stage_group")


# ------------------------------------------------------------------------------------------ captions
def captions():
    rows, _ = sessions_from_t1()
    ov = {r["item"]: r for r in E.read_table("E2_overview.csv")}
    grid = E.read_table("E3_E6_grid.csv")
    t2c = {(r["class"], r["stage_group"]): r for r in E.read_table("T2_kept_windows_by_stage_group_class.csv")
           if r["window_s"] == "30"}
    bin_min = grid[0]["bin_minutes"]
    n_all, n_h, n_a = (ov["kept_windows_30s"][k] for k in ("all", "human", "ai"))
    lines = [
        "# EDA Pass 1: figure captions",
        "",
        "Drawn from the tables in `reports/eda/tables/`. Sessions are labeled as in Table 4-1; humans first.",
        "",
        "**E2. Statistical summary of the dataset.** Left: overview. Middle: kept 30-second windows per session "
        "(human blue, AI orange with hatch). Right: class distribution. n = %s kept windows (%s human, %s AI) from "
        "%s sessions. The two feature-column lines are filled in during Pass 2."
        % (fmt(n_all), fmt(n_h), fmt(n_a), ov["sessions"]["all"]),
        "",
        "**E3. Activity by elapsed working time.** One row per session, one column per %s-minute bin of elapsed "
        "working time (the logins used, laid end to end). Cell: kept 30-second windows in the bin, 1 to 10; gray: "
        "no window kept. Right: kept windows per session, with logged minutes. n = %s kept windows. Clock time is "
        "not plotted: it is removed when windows are built because it identifies the session."
        % (bin_min, fmt(n_all)),
        "",
        "**E4. Kept windows by stage group.** Left: kept 30-second windows per session, split by stage group. "
        "Right: stage share of each class (human n = %s, AI n = %s). Stage 6 holds %s human windows from %s "
        "and %s AI windows from %s."
        % (fmt(n_h), fmt(n_a), t2c[("human", "6")]["kept_windows"], n_sessions(t2c[("human", "6")]["sessions_supplying"]),
           t2c[("ai", "6")]["kept_windows"], n_sessions(t2c[("ai", "6")]["sessions_supplying"])),
        "",
        "**E6. Stage timeline per session.** Same grid as E3. Cell color: the stage group worked in most of the "
        "bin's kept windows (ties go to the later stage); gray: no window kept. Ticks mark the operator's own "
        "accepted stages. P009's used login starts at stage 5; its stages 1 to 4 were accepted in a login that is "
        "not used, so it has no ticks. P010's three used logins are laid end to end; in the session they were "
        "separated by a validator outage. n = %s kept windows." % fmt(n_all),
        "",
    ]
    with open(os.path.join(E.FIGURES, "captions_pass1.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    fig_e2()
    fig_e3()
    fig_e4()
    fig_e6()
    captions()
    names = sorted(n for n in os.listdir(E.FIGURES) if n.startswith(("E2_", "E3_", "E4_", "E6_", "captions_pass1")))
    log = {"pass": "EDA Pass 1 (figures)", "eda_version": E.EDA_VERSION,
           "drawn_from": "reports/eda/tables/ only",
           "libraries": {"matplotlib": matplotlib.__version__},
           "figures": {n: E.sha256_file(os.path.join(E.FIGURES, n)) for n in names}}
    E.write_json(os.path.join(E.OUT, "pass1_figures_log.json"), log)
    print("COMPLETE: Pass 1 figures", len(names), "files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
