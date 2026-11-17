"""EDA run 3, figures (rule file section 4): EDA01 to EDA12.

Every figure is drawn from CSV tables and from nothing else, so each plotted number can be
traced: the run 3 tables in reports/eda_run3/tables/ and the Pass 1 and Pass 2 tables in
reports/eda/tables/, each checked before it is read. PNG at 300 dpi and SVG.

Style is that of Pass 1 and Pass 2. Their figure code is imported for the style constants and
helpers and is never edited. EDA03 to EDA05 call the Pass 1 functions unchanged, with the stage
groups named as in the paper's Table 3-2 and the output folder set to run 3's.

No figure carries a study-internal name: figures are named EDA01 to EDA12, stage groups carry
their names, features carry plain labels, and nothing marks a column as flagged or as belonging
to a hypothesis.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import run3_common as R

C, E, np = R.C, R.E, R.np

import pass1_figures as P1                      # style and helpers; imported, never edited
import pass2_figures as P2

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

W, FS = P1.WIDTH_IN, P1.FS
INK, MUTED, GRID, NO_DATA = P1.INK, P1.MUTED, P1.GRID, P1.NO_DATA
CLASS_COLOR, CLASS_HATCH = P1.CLASS_COLOR, P1.CLASS_HATCH
STAGE_COLOR, RAMP = P1.STAGE_COLOR, P1.RAMP
DIVERGE, SHADE_ALL, SHADE_STAGE, GRAY3 = P2.DIVERGE, P2.SHADE_ALL, P2.SHADE_STAGE, P2.GRAY3
BY_STAGE = ["1-4", "5", "7"]
GROUP_KEY = {"1-4": "discovery", "5": "execution", "7": "lateral_collection"}
SCREEN = C.FLAG                                  # 0.95, the screening line of the single-feature AUC
NAME_OF = {"E3_activity_by_elapsed_time": "EDA03_activity_by_elapsed_time",
           "E4_windows_by_stage_group": "EDA04_windows_by_stage_group",
           "E6_stage_timeline": "EDA05_stage_timeline"}
TITLE_2L = {"cmd_len_mean": "Mean command length\n(characters)", "cmd_len_max": "Longest command\n(characters)",
            "flags_per_cmd": "Flags per command\n ", "pipes_per_cmd": "Pipes per command\n ",
            "chain_ratio": "Share of commands\nchained", "redirect_ratio": "Share of commands\nwith a redirect"}
EXAMPLE_HEAD = {"cmd_count": "Commands", "gap_median": "Median\ngap (s)", "exec_count": "Programs\nstarted",
                "output_bytes": "Output\n(bytes)", "cmd_len_mean": "Mean\ncommand\nlength", "flags_per_cmd": "Flags per\ncommand",
                "pipes_per_cmd": "Pipes per\ncommand", "chain_ratio": "Share\nchained", "redirect_ratio": "Share with\na redirect"}

EDA_TABLES_USED = ["T1_dataset_summary_by_session.csv", "T2_kept_windows_by_stage_group_class.csv",
                   "T2_kept_windows_by_stage_group_session.csv", "E3_E6_grid.csv", "E6_stage_acceptances.csv",
                   "E7_window_activity_by_class.csv", "E8_top_programs.csv", "E8_program_stage_heatmap.csv"]
INP = R.Inputs3([R.EDA_TABLES + n for n in EDA_TABLES_USED])
SAVED = []


def save(fig, name):
    name = NAME_OF.get(name, name)
    os.makedirs(R.FIGURES, exist_ok=True)
    fig.savefig(os.path.join(R.FIGURES, name + ".png"), dpi=300, metadata={"Software": None})
    fig.savefig(os.path.join(R.FIGURES, name + ".svg"), metadata={"Date": None, "Creator": "EDA figures"})
    plt.close(fig)
    SAVED.append(name)


def fmt_value(s):
    if s in ("", "undefined"):
        return "undefined"
    v = float(s)
    if abs(v - round(v)) < 1e-9:
        return "{:,}".format(int(round(v)))
    return ("%.1f" % v) if abs(v) >= 10 else ("%.2f" % v)


def sessions_ypos():
    rows = [r for r in INP.table("T1_dataset_summary_by_session.csv") if r["row_type"] == "session"]
    ypos, y, prev = {}, 0.0, None
    for r in rows:
        if prev is not None and r["class"] != prev:
            y += 0.55
        ypos[r["session"]] = y
        y += 1.0
        prev = r["class"]
    return rows, ypos


# ------------------------------------------------------------------------------------------ EDA01
def fig_data_example():
    rows = R.read_run3("R1_data_example.csv")
    cols = R.EXAMPLE_COLUMNS
    fig = plt.figure(figsize=(W, 3.15))
    ax = fig.add_axes([0.012, 0.03, 0.976, 0.94])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    x0 = 0.395
    xs = [x0 + (i + 1) * (0.995 - x0) / len(rows) for i in range(len(rows))]       # right edge of each session's column
    y_s, y_c, y_g = 0.925, 0.855, 0.785
    for y, h in ((y_s, "Session"), (y_c, "Class"), (y_g, "Stage group")):
        ax.text(0.0, y, h, va="center", fontweight="bold")
    for x, r in zip(xs, rows):
        ax.add_patch(Rectangle((x - 0.056, 0.972), 0.056, 0.022, facecolor=CLASS_COLOR[r["class"]],
                               hatch=CLASS_HATCH[r["class"]], edgecolor="#ffffff", linewidth=0.0))
        ax.text(x, y_s, r["session"], ha="right", va="center", fontweight="bold")
        ax.text(x, y_g, R.STAGE_ABBR[r["stage_group"]], ha="right", va="center")
    width = (0.995 - x0) / len(rows)
    for cls in E.CLASSES:
        mine = [x for x, r in zip(xs, rows) if r["class"] == cls]
        ax.text((min(mine) - width + 0.012 + max(mine)) / 2.0, y_c, "%s operators" % E.CLASS_LABEL[cls], ha="center",
                va="center")
    ax.plot([0, 1], [0.738, 0.738], color=MUTED, linewidth=0.7)
    y, step = 0.685, 0.069
    for c in cols:
        ax.text(0.0, y, R.LABEL[c], va="center")
        for x, r in zip(xs, rows):
            ax.text(x, y, fmt_value(r[c]), ha="right", va="center")
        y -= step
    ax.plot([0, 1], [y + step * 0.45, y + step * 0.45], color=MUTED, linewidth=0.7)
    ax.text(0.0, y - 0.035, "One 30 s training window of each session. Disc.: discovery. Exec.: execution.",
            va="center", color=MUTED)
    save(fig, "EDA01_data_example")


# ------------------------------------------------------------------------------------------ EDA02
def fig_dataset_summary():
    rows, ypos = sessions_ypos()
    ov = {r["item"]: r for r in R.read_run3("R2_overview.csv")}
    cs = R.read_run3("R2_class_by_stage_group.csv")
    fig = plt.figure(figsize=(W, 5.55))

    ax_t = fig.add_axes([0.012, 0.505, 0.30, 0.475])
    ax_t.set_axis_off()
    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(0, 1)
    ax_t.add_patch(Rectangle((0, 0), 1, 1, facecolor="#f6f5f2", edgecolor="none", zorder=0))
    ax_t.text(0.045, 0.955, "Dataset overview", fontsize=FS + 0.5, fontweight="bold", va="top")
    lines = [("Sessions", P1.fmt(ov["sessions"]["all"]), False),
             ("human / AI", "%s / %s" % (ov["sessions"]["human"], ov["sessions"]["ai"]), True),
             ("Logins used", P1.fmt(ov["logins_used"]["all"]), False),
             ("human / AI", "%s / %s" % (ov["logins_used"]["human"], ov["logins_used"]["ai"]), True),
             ("Raw records", P1.fmt(ov["raw_records"]["all"]), False),
             ("Classifier input", P1.fmt(ov["classifier_input_records"]["all"]), False),
             ("Kept windows", P1.fmt(ov["kept_windows_30s"]["all"]), False),
             ("human / AI", "%s / %s" % (ov["kept_windows_30s"]["human"], ov["kept_windows_30s"]["ai"]), True),
             ("Window length", "%s s" % ov["window_length_s"]["all"], False),
             ("Training windows", P1.fmt(ov["training_windows_30s"]["all"]), False),
             ("human / AI", "%s / %s" % (ov["training_windows_30s"]["human"], ov["training_windows_30s"]["ai"]), True)]
    y, step = 0.845, 0.0765
    for label, value, sub in lines:
        ax_t.text(0.11 if sub else 0.045, y, label, va="center", color=MUTED if sub else INK)
        ax_t.text(0.955, y, value, va="center", ha="right", color=MUTED if sub else INK,
                  fontweight="normal" if sub else "bold")
        y -= step

    ax_c = fig.add_axes([0.345, 0.505, 0.275, 0.475])
    ax_c.set_axis_off()
    ax_c.set_xlim(0, 1)
    ax_c.set_ylim(0, 1)
    ax_c.text(0.0, 0.955, "Column breakdown", fontsize=FS + 0.5, fontweight="bold", va="top")
    tiers = dict(p.strip().rsplit(" ", 1) for p in ov["feature_columns_by_tier"]["note"].split(";"))
    boxes = [("Identifier columns", ov["identifier_columns"]["all"], "#f3ead9"),
             ("Label columns", ov["label_columns"]["all"], "#ece3f1"),
             ("Feature columns", ov["feature_columns_by_tier"]["all"], "#e3efe3")]
    y = 0.80
    for label, value, color in boxes:
        ax_c.add_patch(Rectangle((0.0, y - 0.052), 1.0, 0.104, facecolor=color, edgecolor="none"))
        ax_c.text(0.045, y, label, va="center")
        ax_c.text(0.955, y, value, va="center", ha="right", fontweight="bold")
        y -= 0.125
    y += 0.02
    for label, key in (("Behavior", "behavior"), ("Command content", "command content"), ("Context", "context"),
                       ("Input channel", "input channel")):
        ax_c.text(0.11, y, label, va="center", color=MUTED)
        ax_c.text(0.955, y, tiers[key], va="center", ha="right", color=MUTED)
        y -= 0.0765
    y -= 0.012
    for label, value in (("Main configuration", ov["main_configuration_columns"]["all"]),
                         ("Can be undefined", ov["columns_with_undefined_values"]["all"])):
        ax_c.text(0.045, y, label, va="center")
        ax_c.text(0.955, y, value, va="center", ha="right", fontweight="bold")
        y -= 0.0765

    ax_b = fig.add_axes([0.715, 0.575, 0.272, 0.375])
    top = max(int(r["kept_30s"]) for r in rows)
    for r in rows:
        v = int(r["kept_30s"])
        P1.class_bar(ax_b, ypos[r["session"]], v, r["class"])
        ax_b.text(v + top * 0.03, ypos[r["session"]], P1.fmt(v), va="center", ha="left")
    ax_b.set_yticks([ypos[r["session"]] for r in rows])
    ax_b.set_yticklabels([r["session"] for r in rows])
    ax_b.set_ylim(max(ypos.values()) + 0.6, -0.6)
    ax_b.set_xlim(0, top * 1.3)
    ax_b.set_xticks([0, 100, 200])
    ax_b.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax_b.set_axisbelow(True)
    ax_b.tick_params(axis="y", length=0)
    P1.clean_axes(ax_b, keep=("bottom",))
    ax_b.set_xlabel("Kept 30 s windows")
    ax_b.set_title("Windows per session", loc="left", pad=6)

    ax_d = fig.add_axes([0.275, 0.085, 0.71, 0.33])
    top = max(int(r["kept_windows"]) for r in cs)
    yt, yl, y = [], [], 0.0
    for g in R.STAGE_GROUPS:
        for k, cls in enumerate(E.CLASSES):
            r = next(x for x in cs if x["class"] == cls and x["stage_group"] == g)
            v = int(r["kept_windows"])
            P1.class_bar(ax_d, y + k * 0.82, v, cls, height=0.72)
            ax_d.text(v + top * 0.012, y + k * 0.82, "%s  (%s%%)" % (P1.fmt(v), r["pct_of_class"]), va="center", ha="left")
        yt.append(y + 0.41)
        yl.append("%s\n(%s)" % (R.STAGE_NAME_2L[g], R.STAGES_OF[g]))
        y += 2.35
    ax_d.set_yticks(yt)
    ax_d.set_yticklabels(yl, linespacing=1.12)
    ax_d.set_ylim(y - 2.35 + 1.35, -0.55)
    ax_d.set_xlim(0, top * 1.3)
    ax_d.set_xticks([0, 100, 200, 300, 400])
    ax_d.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax_d.set_axisbelow(True)
    ax_d.tick_params(axis="y", length=0)
    P1.clean_axes(ax_d, keep=("bottom",))
    ax_d.set_xlabel("Kept 30 s windows")
    fig.text(0.012, 0.452, "Kept windows by class and stage group, with the share of the class's windows", fontsize=FS + 0.5, va="center")
    fig.legend(handles=P2.class_handles(), loc="lower left", bbox_to_anchor=(0.012, 0.012), ncol=2, frameon=False,
               handlelength=1.4, handleheight=1.0, columnspacing=1.4, handletextpad=0.5, borderaxespad=0.0)
    save(fig, "EDA02_dataset_summary")


# ------------------------------------------------------------------------------------------ EDA06
def fig_window_activity():
    act = INP.table("E7_window_activity_by_class.csv")
    nw = {c: next(r["class_windows"] for r in act if r["class"] == c) for c in E.CLASSES}
    fig = plt.figure(figsize=(W, 1.7))
    ax = fig.add_axes([0.125, 0.43, 0.56, 0.4])
    h = P2.stacked(ax, act, "window_type", ["quiet", "no_program", "programs"],
                   ["No command", "Only commands that started no program", "Commands that started programs"], GRAY3)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["%s\nn = %s" % (E.CLASS_LABEL[c], P1.fmt(nw[c])) for c in E.CLASSES], linespacing=1.15)
    ax.set_xlabel("Share of the class's training windows (%)")
    ax.set_title("What a 30 s window holds", loc="left", pad=6)
    fig.legend(handles=h, loc="center left", bbox_to_anchor=(0.705, 0.63), frameon=False, handlelength=1.2,
               handleheight=1.0, labelspacing=0.6, handletextpad=0.5, borderaxespad=0.0)
    for t in fig.legends[0].get_texts():
        t.set_text(t.get_text().replace("Only commands that started no program", "Only commands that\nstarted no program")
                   .replace("Commands that started programs", "Commands that\nstarted programs"))
    save(fig, "EDA06_window_activity")


# ------------------------------------------------------------------------------------------ EDA07
def fig_programs():
    top = INP.table("E8_top_programs.csv")
    heat = {(r["program"], r["class"], r["stage_group"]): r for r in INP.table("E8_program_stage_heatmap.csv")}
    n = len(top)
    fig = plt.figure(figsize=(W, 5.05))
    ax = fig.add_axes([0.268, 0.255, 0.285, 0.635])
    hx = fig.add_axes([0.612, 0.255, 0.376, 0.635])
    most = max(int(r["training_windows"]) for r in top)
    for i, r in enumerate(top):
        left = 0
        for g in R.STAGE_GROUPS:
            v = int(r["windows_stage_" + g])
            if v:
                ax.barh(i, v, left=left, height=0.7, color=STAGE_COLOR[g], edgecolor="#ffffff", linewidth=0.7, zorder=3)
            left += v
        ax.text(left + most * 0.025, i, str(left), va="center", ha="left")
    ax.set_yticks(range(n))
    ax.set_yticklabels([r["program"] for r in top])
    ax.set_ylim(n - 0.4, -0.6)
    ax.set_xlim(0, most * 1.17)
    ax.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    P1.clean_axes(ax, keep=("bottom",))
    ax.set_xlabel("Training windows")
    ax.set_title("Windows in which\nthe program started", loc="left", pad=17, linespacing=1.15)
    vmax = max(float(r["share_pct"]) for r in heat.values() if r["share_pct"] != "")
    x0 = {"human": 0.0, "ai": 4.6}
    for i, r in enumerate(top):
        for cls in E.CLASSES:
            for k, g in enumerate(R.STAGE_GROUPS):
                c = heat[(r["program"], cls, g)]
                if c["share_pct"] == "":
                    color, txt = NO_DATA, ""
                else:
                    v = float(c["share_pct"])
                    color = "#f6f5f2" if v == 0 else RAMP(v / vmax)
                    txt = "" if v == 0 else ("<1" if v < 0.5 else "%.0f" % v)
                hx.add_patch(Rectangle((x0[cls] + k, i - 0.5), 1, 1, facecolor=color, edgecolor="#ffffff", linewidth=0.6))
                if txt:
                    hx.text(x0[cls] + k + 0.5, i, txt, ha="center", va="center",
                            color="#ffffff" if float(c["share_pct"]) / vmax > 0.5 else INK)
            if r["only_class"] == cls:
                hx.add_patch(Rectangle((x0[cls] + 0.03, i - 0.47), 3.94, 0.94, facecolor="none", edgecolor=INK,
                                       linewidth=1.1, zorder=5))
    hx.set_xlim(0, 8.6)
    hx.set_ylim(n - 0.4, -0.6)
    hx.set_xticks([x0[c] + k + 0.5 for c in E.CLASSES for k in range(4)])
    hx.set_xticklabels([R.STAGE_ABBR[g] for _ in E.CLASSES for g in R.STAGE_GROUPS], rotation=90)
    hx.set_yticks([])
    hx.tick_params(axis="x", length=0)
    P1.clean_axes(hx, keep=())
    for cls in E.CLASSES:
        hx.text(x0[cls] + 2.0, -0.95, E.CLASS_LABEL[cls], ha="center", va="center", fontweight="bold")
    hx.set_title("Share of the class's windows\nin the stage group (%)", loc="left", pad=17, linespacing=1.15)
    handles = [Patch(facecolor=STAGE_COLOR[g], edgecolor="none", label="%s  %s" % (R.STAGE_ABBR[g], R.STAGE_NAME[g]))
               for g in R.STAGE_GROUPS]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.062), ncol=2, frameon=False,
               handlelength=1.2, handleheight=1.0, columnspacing=1.6, labelspacing=0.4, handletextpad=0.5,
               borderaxespad=0.0)
    h2 = [Patch(facecolor="none", edgecolor=INK, linewidth=1.1, label="Run by one class only"),
          Patch(facecolor=NO_DATA, edgecolor="none", label="The class has no training window in the stage group")]
    fig.legend(handles=h2, loc="lower left", bbox_to_anchor=(0.012, 0.012), ncol=2, frameon=False,
               handlelength=1.4, handleheight=1.0, columnspacing=1.2, handletextpad=0.5, borderaxespad=0.0)
    save(fig, "EDA07_programs_by_stage_group")


# ------------------------------------------------------------------------------------------ EDA08
def fig_correlation():
    pairs = R.read_run3("R9_spearman_main_top20.csv")
    name = {}
    for p in pairs:
        name[int(p["rank_a"])] = p["label_a"]
        name[int(p["rank_b"])] = p["label_b"]
    n = max(name)
    fig = plt.figure(figsize=(W, 6.25))
    cell = 0.925 / (n - 1)
    ax = fig.add_axes([0.055, 0.06, 0.925, cell * (n - 1) * W / 6.25])
    for p in pairs:
        a, b = int(p["rank_a"]), int(p["rank_b"])
        rho = R.num(p["spearman_rho"])
        if rho is None:
            ax.add_patch(Rectangle((b - 1, a - 2), 1, 1, facecolor=NO_DATA, edgecolor="#ffffff", linewidth=0.6))
            continue
        ax.add_patch(Rectangle((b - 1, a - 2), 1, 1, facecolor=DIVERGE((rho + 1) / 2.0), edgecolor="#ffffff", linewidth=0.6))
        ax.text(b - 0.5, a - 1.5, ("%d" % round(rho * 100)).replace("-", "−"), ha="center", va="center",
                color="#ffffff" if abs(rho) > 0.6 else INK, fontsize=FS - 0.3)
    ax.set_xlim(0, n - 1)
    ax.set_ylim(n - 1, 0)
    ax.set_xticks([i + 0.5 for i in range(n - 1)])
    ax.set_xticklabels([str(i + 1) for i in range(n - 1)])
    ax.set_yticks([i + 0.5 for i in range(n - 1)])
    ax.set_yticklabels([str(i + 2) for i in range(n - 1)])
    ax.tick_params(length=0)
    P1.clean_axes(ax, keep=())
    ax.set_xlabel("Feature (rank by single-feature AUC within the main configuration)")
    x_key, dy = 0.588, 0.0229
    fig.text(x_key, 0.972, "Rank and feature", fontweight="bold", va="center")
    for i in range(1, n + 1):
        fig.text(x_key + 0.028, 0.972 - i * dy, str(i), ha="right", va="center", color=MUTED)
        fig.text(x_key + 0.043, 0.972 - i * dy, name[i], va="center")
    cax = fig.add_axes([0.255, 0.925, 0.29, 0.016])
    for k in range(100):
        cax.add_patch(Rectangle((-100 + 2 * k, 0), 2.05, 1, facecolor=DIVERGE((k + 0.5) / 100.0), edgecolor="none"))
    cax.set_xlim(-100, 100)
    cax.set_ylim(0, 1)
    cax.set_yticks([])
    cax.set_xticks([-100, -50, 0, 50, 100])
    cax.set_xticklabels(["−100", "−50", "0", "50", "100"])
    cax.tick_params(length=2)
    for side in ("left", "right", "top", "bottom"):
        cax.spines[side].set_visible(False)
    fig.text(0.255, 0.958, "Spearman ρ × 100", va="center")
    save(fig, "EDA08_feature_correlation")


# ------------------------------------------------------------------------------------------ EDA09
def fig_auc():
    rows = [r for r in R.read_run3("R10_auc_main_configuration.csv") if r["main_top20_rank"] != ""]
    groups = []
    for t in R.TIERS_MAIN:
        fs = sorted([r for r in rows if r["tier"] == t], key=lambda r: int(r["main_top20_rank"]))
        if fs:
            groups.append((t, fs))
    row_h, gap, bottom_in, top_in = 0.185, 0.36, 0.86, 0.3
    height = bottom_in + top_in + len(rows) * row_h + (len(groups) - 1) * gap
    fig = plt.figure(figsize=(W, height))
    y, xlim = height - top_in, (0.36, 1.115)
    for k, (t, fs) in enumerate(groups):
        h = len(fs) * row_h
        ax = fig.add_axes([0.375, (y - h) / height, 0.61, h / height])
        for i, r in enumerate(fs):
            auc, cls = float(r["auc"]), r["higher_in"]
            ax.barh(i, auc - 0.5, left=0.5, height=0.64, color=CLASS_COLOR[cls], hatch=CLASS_HATCH[cls],
                    edgecolor="#ffffff", linewidth=0.0, zorder=3)
            lo, hi = float(r["auc_drop_min"]), float(r["auc_drop_max"])
            ax.plot([lo, hi], [i, i], color=INK, linewidth=0.9, zorder=4, solid_capstyle="butt")
            for x in (lo, hi):
                ax.plot([x, x], [i - 0.2, i + 0.2], color=INK, linewidth=0.9, zorder=4, solid_capstyle="butt")
            ax.text(xlim[1], i, "%.2f" % auc, va="center", ha="right")
        ax.axvline(0.5, color=MUTED, linewidth=0.7, zorder=2)
        ax.axvline(SCREEN, color=INK, linewidth=0.8, linestyle=(0, (4, 2)), zorder=2)
        ax.set_xlim(*xlim)
        ax.set_ylim(len(fs) - 0.45, -0.55)
        ax.set_yticks(range(len(fs)))
        ax.set_yticklabels([R.short_label(r["feature"]) for r in fs])
        ax.tick_params(axis="y", length=0)
        ax.set_xticks([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        ax.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)
        P1.clean_axes(ax, keep=("bottom",))
        ax.set_title("%s (%d of the top %d)" % (R.TIER_NAME[t], len(fs), len(rows)), loc="left", pad=4)
        if k < len(groups) - 1:
            ax.set_xticklabels([])
            ax.tick_params(axis="x", length=0)
        else:
            ax.set_xlabel("Single-feature AUC on training windows")
        y -= h + gap
    handles = [Patch(facecolor=CLASS_COLOR["human"], edgecolor="#ffffff", linewidth=0.0, label="Higher in human windows"),
               Patch(facecolor=CLASS_COLOR["ai"], hatch=CLASS_HATCH["ai"], edgecolor="#ffffff", linewidth=0.0,
                     label="Higher in AI windows"),
               Line2D([0], [0], color=INK, linewidth=0.9, marker="|", markersize=6, label="Range with one session left out"),
               Line2D([0], [0], color=INK, linewidth=0.8, linestyle=(0, (4, 2)), label="Screening line at 0.95")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.012), ncol=2, frameon=False, handlelength=1.6,
               handleheight=1.0, columnspacing=1.6, labelspacing=0.4, handletextpad=0.5, borderaxespad=0.0)
    save(fig, "EDA09_single_feature_auc")


# ------------------------------------------------------------------------------------------ EDA10
def fig_h1_by_class():
    pts = R.read_run3("R11_h1_points.csv")
    med = R.read_run3("R11_h1_session_medians.csv")
    prof = {r["feature"]: r for r in R.read_run3("R10_auc_main_configuration.csv")}
    sessions = {c: [] for c in E.CLASSES}
    for r in med:
        if r["session"] not in sessions[r["class"]]:
            sessions[r["class"]].append(r["session"])
    ncol = 3
    height, top_in, block, plot_h = 5.05, 0.66, 2.02, 1.2
    fig = plt.figure(figsize=(W, height))
    for k, f in enumerate(R.H1_COLUMNS):
        i, j = divmod(k, ncol)
        ax = fig.add_axes([0.072 + j * 0.318, (height - top_in - i * block - plot_h) / height, 0.245, plot_h / height])
        vals = {c: np.array([float(p["value"]) for p in pts if p["feature"] == f and p["class"] == c]) for c in E.CLASSES}
        top = max([v.max() for v in vals.values() if len(v)] + [1.0])
        low = min([v.min() for v in vals.values() if len(v)] + [0.0])
        log = top > 20
        rng = np.random.default_rng(42 + k)
        r = prof[f]
        for x, c in enumerate(E.CLASSES):
            v = vals[c]
            ax.scatter(x + rng.uniform(-0.3, 0.3, size=len(v)), v, s=5, color=CLASS_COLOR[c], alpha=0.22, linewidths=0,
                       zorder=2)
            q1, q2, q3 = R.num(r["q1_" + c]), R.num(r["median_" + c]), R.num(r["q3_" + c])
            ax.add_patch(Rectangle((x - 0.36, q1), 0.72, q3 - q1, facecolor="none", edgecolor=INK, linewidth=0.9, zorder=4))
            ax.plot([x - 0.36, x + 0.36], [q2, q2], color=INK, linewidth=1.8, zorder=5, solid_capstyle="butt")
            ss = sessions[c]
            for m in med:
                if m["feature"] == f and m["class"] == c and m["median"] != "":
                    xs = x + (ss.index(m["session"]) - (len(ss) - 1) / 2.0) * (0.56 / max(len(ss) - 1, 1))
                    ax.scatter([xs], [float(m["median"])], s=26, marker="o" if c == "human" else "D",
                               facecolor=CLASS_COLOR[c], edgecolor="#ffffff", linewidths=0.8, zorder=6)
        if log:
            ax.set_yscale("symlog", linthresh=1.0, linscale=0.6)
            ax.set_ylim(min(low, 0) - 0.15, top * 1.6)
            P2.sym_ticks(ax, top)
        else:
            pad = (top - low) * 0.07 or 0.05
            ax.set_ylim(low - pad, top + pad)
        ax.set_xlim(-0.6, 1.6)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Human", "AI"])
        ax.tick_params(axis="x", length=0)
        ax.yaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)
        P1.clean_axes(ax, keep=("left",))
        ax.set_title(TITLE_2L[f], loc="left", pad=15, linespacing=1.12)
        ax.text(0.0, 1.035, "AUC %.2f, higher in %s" % (float(r["auc"]), "human" if r["higher_in"] == "human" else "AI"),
                transform=ax.transAxes, ha="left", va="bottom", color=MUTED)
    handles = [Line2D([0], [0], linestyle="none", marker="o", markersize=3, color=MUTED, alpha=0.5, label="One training window"),
               Line2D([0], [0], linestyle="none", marker="o", markersize=5.5, markerfacecolor=CLASS_COLOR["human"],
                      markeredgecolor="#ffffff", label="Median of one human session"),
               Line2D([0], [0], linestyle="none", marker="D", markersize=5, markerfacecolor=CLASS_COLOR["ai"],
                      markeredgecolor="#ffffff", label="Median of one AI session"),
               Patch(facecolor="none", edgecolor=INK, linewidth=0.9, label="Class median and interquartile range")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.052), ncol=2, frameon=False, handlelength=1.4,
               columnspacing=1.6, labelspacing=0.4, handletextpad=0.5, borderaxespad=0.0)
    fig.text(0.012, 0.014, "Session markers, left to right: %s (human); %s (AI)."
             % (" ".join(sessions["human"]), " ".join(sessions["ai"])), ha="left", va="bottom", color=MUTED)
    save(fig, "EDA10_command_features_by_class")


# ------------------------------------------------------------------------------------------ EDA11
def fig_h1_by_stage():
    rows = R.read_run3("R12_h1_by_stage_group.csv")
    cell = {(r["feature"], r["stage_group"], r["class"]): r for r in rows}
    ncol = 2
    height, top_in, block, plot_h = 8.2, 0.5, 2.36, 1.38
    fig = plt.figure(figsize=(W, height))
    off = {"human": -0.17, "ai": 0.17}
    xs = [0.0, 1.0, 2.2]
    tick = {"1-4": "Discovery", "5": "Execution", "7": "Lateral\nmovement\nand collection"}
    for k, f in enumerate(R.H1_COLUMNS):
        i, j = divmod(k, ncol)
        ax = fig.add_axes([0.085 + j * 0.5, (height - top_in - i * block - plot_h) / height, 0.40, plot_h / height])
        top = max(float(cell[(f, g, c)]["q3"]) for g in BY_STAGE for c in E.CLASSES)
        log = top > 20
        for x, g in zip(xs, BY_STAGE):
            for c in E.CLASSES:
                r = cell[(f, g, c)]
                q1, q2, q3 = float(r["q1"]), float(r["median"]), float(r["q3"])
                ax.plot([x + off[c], x + off[c]], [q1, q3], color=CLASS_COLOR[c], linewidth=3.2, alpha=0.45, zorder=3,
                        solid_capstyle="butt")
                ax.scatter([x + off[c]], [q2], s=44, marker="o" if c == "human" else "D", facecolor=CLASS_COLOR[c],
                           edgecolor="#ffffff", linewidths=0.9, zorder=5)
            a = cell[(f, g, "human")]
            ax.text(x, 1.02, "AUC %.2f" % float(a["same_stage_auc_in_all_rows_direction"]),
                    transform=ax.get_xaxis_transform(), ha="center", va="bottom", color=MUTED)
        if log:
            ax.set_yscale("symlog", linthresh=1.0, linscale=0.6)
            ax.set_ylim(-0.15, top * 1.9)
            P2.sym_ticks(ax, top * 1.9)
        else:
            ax.set_ylim(-0.06 * max(top, 1.0), max(top, 1.0) * 1.12)
        ax.set_xlim(-0.55, 2.95)
        ax.set_xticks(xs)
        ax.set_xticklabels([tick[g] for g in BY_STAGE], linespacing=1.1)
        ax.tick_params(axis="x", length=0)
        ax.yaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)
        P1.clean_axes(ax, keep=("left",))
        ax.set_title(R.LABEL[f], loc="left", pad=17)
    handles = [Line2D([0], [0], linestyle="none", marker="o", markersize=6.5, markerfacecolor=CLASS_COLOR["human"],
                      markeredgecolor="#ffffff", label="Human: median"),
               Line2D([0], [0], linestyle="none", marker="D", markersize=6, markerfacecolor=CLASS_COLOR["ai"],
                      markeredgecolor="#ffffff", label="AI: median"),
               Line2D([0], [0], color=MUTED, linewidth=3.2, alpha=0.45, label="Interquartile range")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.105), ncol=3, frameon=False, handlelength=1.4,
               columnspacing=1.6, handletextpad=0.5, borderaxespad=0.0)
    f0 = R.H1_COLUMNS[0]
    fig.text(0.012, 0.079, "AUC above each pair: the single-feature AUC within the stage group.", ha="left", va="bottom",
             color=MUTED)
    fig.text(0.012, 0.055, "Training windows that hold a command, with sessions in parentheses:", ha="left", va="bottom",
             color=MUTED)
    for y, c, lead in ((0.031, "human", "Human"), (0.007, "ai", "AI")):
        parts = ["%s %s (%s)" % (R.STAGE_NAME[g].lower(), cell[(f0, g, c)]["defined_windows"], cell[(f0, g, c)]["sessions"])
                 for g in BY_STAGE]
        fig.text(0.012, y, "%s: %s." % (lead, ", ".join(parts)), ha="left", va="bottom", color=MUTED)
    save(fig, "EDA11_command_features_by_stage_group")


# ------------------------------------------------------------------------------------------ EDA12
def fig_auc_by_stage():
    rows = R.read_run3("R13_main_top20_by_stage_group.csv")
    counts = {(r["class"], r["stage_group"]): r for r in R.read_run3("R13_stage_group_training_windows.csv")}
    n = len(rows)
    fig = plt.figure(figsize=(W, 6.1))
    left, width, gap = 0.40, 0.18, 0.02
    title = {"1-4": "Discovery", "5": "Execution", "7": "Lateral\nmovement and\ncollection"}
    for k, g in enumerate(BY_STAGE):
        ax = fig.add_axes([left + k * (width + gap), 0.185, width, 0.635])
        key = GROUP_KEY[g]
        for i, r in enumerate(rows):
            a_all, a_st = float(r["auc_all"]), R.num(r[key + "_auc_dir"])
            if a_st is None:
                ax.scatter([a_all], [i], s=30, color=SHADE_ALL, zorder=4, linewidths=0)
                continue
            ax.plot([a_all, a_st], [i, i], color="#b9cfe9", linewidth=1.6, zorder=3, solid_capstyle="round")
            ax.scatter([a_all], [i], s=30, color=SHADE_ALL, zorder=4, linewidths=0)
            hollow = r[key + "_indicative"] == "yes"
            ax.scatter([a_st], [i], s=30, facecolor="#ffffff" if hollow else SHADE_STAGE, edgecolor=SHADE_STAGE,
                       linewidths=1.2 if hollow else 0, zorder=5)
        ax.axvline(0.5, color=MUTED, linewidth=0.7, zorder=2)
        ax.set_xlim(0.33, 1.035)
        ax.set_xticks([0.4, 0.6, 0.8, 1.0])
        ax.set_ylim(n - 0.4, -0.6)
        ax.set_yticks(range(n))
        ax.set_yticklabels(["%s  %s" % (r["main_top20_rank"], R.short_label(r["feature"])) for r in rows] if k == 0 else [])
        ax.tick_params(axis="y", length=0)
        ax.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
        ax.yaxis.grid(True, color="#ededed", linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)
        P1.clean_axes(ax, keep=("bottom",))
        h, a = counts[("human", g)], counts[("ai", g)]
        ax.set_title("%s\nhuman %s (%s)\nAI %s (%s)" % (title[g], h["training_windows"], h["sessions"],
                                                        a["training_windows"], a["sessions"]),
                     loc="left", pad=5, linespacing=1.15)
        if k == 1:
            ax.set_xlabel("Single-feature AUC")
    handles = [Line2D([0], [0], linestyle="none", marker="o", markersize=6, color=SHADE_ALL, label="All training windows"),
               Line2D([0], [0], linestyle="none", marker="o", markersize=6, color=SHADE_STAGE, label="Within the stage group")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.073), ncol=3, frameon=False, handlelength=1.0,
               columnspacing=1.4, handletextpad=0.4, borderaxespad=0.0)
    fig.text(0.012, 0.04, "Panel titles: training windows of each class, with sessions in parentheses.",
             ha="left", va="bottom", color=MUTED)
    fig.text(0.012, 0.012, "The AUC keeps the direction it has over all training windows; under 0.5 the direction reverses.",
             ha="left", va="bottom", color=MUTED)
    save(fig, "EDA12_auc_within_stage_groups")


def pass1_redraws():
    """EDA03 to EDA05: the Pass 1 functions, unchanged, with checked inputs, the paper's stage-group
    names and run 3's output folder."""
    P1.save = save
    E.read_table = INP.table
    E.STAGE_GROUP_LABEL = dict(R.STAGE_NAME_2L)
    P1.GRID_AXES = [0.118, 0.275, 0.600, 0.635]            # a little narrower, so the stage names fit beside the grid
    P1.SIDE_AXES = [0.745, 0.275, 0.245, 0.635]
    P1.fig_e3()
    P1.fig_e4()
    P1.fig_e6()


def captions():
    ov = {r["item"]: r for r in R.read_run3("R2_overview.csv")}
    n_all, n_h, n_a = (ov["kept_windows_30s"][k] for k in ("all", "human", "ai"))
    t_all, t_h, t_a = (ov["training_windows_30s"][k] for k in ("all", "human", "ai"))
    kept = "n = %s kept 30-second windows (%s human, %s AI) from 9 sessions" % (P1.fmt(n_all), n_h, n_a)
    train = "n = %s training windows (%s human, %s AI)" % (t_all, t_h, t_a)
    r12 = {(r["feature"], r["stage_group"], r["class"]): r for r in R.read_run3("R12_h1_by_stage_group.csv")}
    aucs = [float(r["same_stage_auc_in_all_rows_direction"]) for r in r12.values()]
    pairs = sorted({(f, g) for (f, g, _c) in r12})
    assert all(r["same_stage_higher_in"] == "ai" for r in r12.values())
    med = lambda f, g, c: float(r12[(f, g, c)]["median"])
    ai_higher = [p for p in pairs if med(p[0], p[1], "ai") > med(p[0], p[1], "human")]
    assert all(med(f, g, "ai") == 0.0 == med(f, g, "human") for (f, g) in pairs if (f, g) not in ai_higher)
    top = [r for r in R.read_run3("R10_auc_main_configuration.csv") if r["main_top20_rank"] != ""]
    best = min(top, key=lambda r: int(r["main_top20_rank"]))
    cnt = {(r["class"], r["stage_group"]): r for r in R.read_run3("R13_stage_group_training_windows.csv")}
    stage_n = "; ".join("%s (human %s, AI %s)" % (R.STAGE_NAME[g].lower(), cnt[("human", g)]["training_windows"],
                                                  cnt[("ai", g)]["training_windows"]) for g in BY_STAGE)
    lines = [
        "# Figure captions for the exploratory data analysis",
        "",
        "Each figure is drawn from the tables in `tables/`. Counts of windows come from all kept windows. Feature values "
        "come from the training portion of the data. Sessions are labeled as in the session table; human operators first.",
        "",
        "**EDA01. Example rows of the feature table.** One 30-second training window of each session, with nine of the "
        "60 feature columns. For each session it is the first training window that holds at least two commands.",
        "",
        "**EDA02. Statistical summary of the dataset.** Top: overview of the dataset, the columns of the feature table, "
        "and the kept windows of each session. Bottom: kept windows by class and stage group, with the share of the "
        "class's windows. %s." % kept,
        "",
        "**EDA03. Activity by elapsed working time.** One row per session and one column per 5-minute bin of elapsed "
        "working time, with the logins used laid end to end. Cell: kept windows in the bin. Right: kept windows per "
        "session, with logged minutes. %s." % kept,
        "",
        "**EDA04. Kept windows by stage group.** Left: kept windows of each session, split by stage group. Right: the "
        "stage-group share of each class. %s." % kept,
        "",
        "**EDA05. Stage timeline of each session.** Same grid as the activity figure. Cell color: the stage group worked "
        "in most of the bin's kept windows. Ticks mark the stages the operator had accepted. %s." % kept,
        "",
        "**EDA06. What a window holds, by class.** Share of each class's training windows that hold no command, only "
        "commands that started no program, or commands that started programs. %s." % train,
        "",
        "**EDA07. Programs started, by stage group.** Left: the 15 programs started in the most training windows, split "
        "by stage group. Right: for each class, the share of its training windows in the stage group in which the "
        "program started. A window counts once however often the program ran in it. %s." % train,
        "",
        "**EDA08. Correlation of the 20 strongest features.** Spearman's rho, multiplied by 100, among the 20 features of "
        "the main configuration with the highest single-feature AUC, on the windows where both features are defined. "
        "%s." % train,
        "",
        "**EDA09. Single-feature AUC of the 20 strongest features.** How well each feature of the main configuration, "
        "taken alone, separates the two classes, by tier. Bar color: the class in which the feature is higher. Whisker: "
        "the range when each session in turn is left out. The highest is %s (%.2f); no feature reaches the screening "
        "line at %.2f. %s." % (R.short_label(best["feature"]).lower(), float(best["auc"]), SCREEN, train),
        "",
        "**EDA10. Command telemetry features by class.** Command length, flags, pipes, chaining and redirects: one point "
        "per training window, the class median and interquartile range, and one marker per session median. A log axis "
        "is used for the two length features. %s; a feature is plotted on the windows that hold a command." % train,
        "",
        "**EDA11. Command telemetry features within each stage group.** Class median and interquartile range of the "
        "same six features within discovery, execution, and lateral movement and collection, with the single-feature "
        "AUC within the stage group. All %d values are between %.2f and %.2f, each in the direction of higher values "
        "in the AI windows. The AI median is the higher one in %d of the %d pairs; in the others both medians are "
        "zero. Account manipulation is not drawn: the AI operator has no training window "
        "there." % (len(pairs), min(aucs), max(aucs), len(ai_higher), len(pairs)),
        "",
        "**EDA12. Single-feature AUC over all training windows and within each stage group.** The 20 strongest features "
        "of the main configuration. The value within a stage group keeps the direction the feature has over all "
        "training windows, so a value under 0.5 is a reversal. Training windows: %s." % stage_n,
        "",
    ]
    with open(os.path.join(R.FIGURES, "captions_run3.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    fig_data_example()
    fig_dataset_summary()
    pass1_redraws()
    fig_window_activity()
    fig_programs()
    fig_correlation()
    fig_auc()
    fig_h1_by_class()
    fig_h1_by_stage()
    fig_auc_by_stage()
    captions()
    E.write_json(os.path.join(R.OUT, "run3_figures_log.json"),
                 {"run": "EDA run 3", "run3_version": R.RUN3_VERSION, "figures": sorted(SAVED),
                  "pass_tables_opened": INP.opened,
                  "run3_tables_read": sorted(n for n in os.listdir(R.TABLES) if n.endswith(".csv")),
                  "note": "Figures are drawn from tables only. No file under data/ is opened by this script."})
    print("figures:", len(SAVED), "drawn")
    return 0


if __name__ == "__main__":
    sys.exit(main())
