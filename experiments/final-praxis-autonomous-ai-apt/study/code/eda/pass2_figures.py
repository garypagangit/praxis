"""EDA Pass 2, figures (handoff sections 6 and 9): E1, E2 (tier lines filled in), E5, E7 to E12.

Every figure is drawn from the CSV tables in reports/eda/tables/ and from nothing else
(handoff rule 8), so each plotted number can be traced. PNG at 300 dpi and SVG.

Style is the Pass 1 style (handoff section 9). The constants and helpers come from
`pass1_figures.py`, which is frozen and is imported, not edited: 6.2 in wide; human blue,
AI orange with a diagonal hatch; humans first; four stage-group colors, always labeled;
one blue ramp for magnitude; blue to red through gray for correlation; one hue in two
shades for two measures of one thing; no pie or donut chart and no second y-axis; text
9 pt in the file.

E1 shows text from two training windows. It is written twice: as it is, to be read by a
person before use (handoff section 10, check 4), and with every letter and digit masked,
which is the copy used to check the layout.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import pass2_common as C

E = C.E
np = C.np

import pass1_figures as P1                                       # frozen; style and helpers only

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

W = P1.WIDTH_IN
FS = P1.FS
INK, MUTED, GRID, NO_DATA = P1.INK, P1.MUTED, P1.GRID, P1.NO_DATA
CLASS_COLOR, CLASS_HATCH = P1.CLASS_COLOR, P1.CLASS_HATCH
STAGE_COLOR, STAGE_TEXT, RAMP = P1.STAGE_COLOR, P1.STAGE_TEXT, P1.RAMP
DIVERGE = LinearSegmentedColormap.from_list("blue_gray_red", ["#1c5cab", "#f0efec", "#c23b2e"])
SHADE_ALL, SHADE_STAGE = "#86b6ef", "#1c5cab"
GRAY3 = ["#e4e3df", "#a9a8a3", "#5a5a58"]
GRAY4 = ["#e9e8e4", "#c4c3bd", "#77766f", "#3b3b39"]
MONO = "DejaVu Sans Mono"
STAGE_SHORT = {"1-4": "1–4", "5": "5", "6": "6", "7": "7"}
GROUP_KEY = {"1-4": "s1_4", "5": "s5", "6": "s6", "7": "s7"}
TIER_LABEL = C.TIER_LABEL
WL = "w30"


def num(s):
    return None if s in ("", None) else float(s)


def pass1_rows(name):
    """A Pass 1 table, from the study folder, checked against Freeze 2 before it is read."""
    rel = "reports/eda/tables/" + name
    inp = C.Inputs2([rel])
    import csv
    with open(inp.path(rel), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def session_rows():
    rows = [r for r in pass1_rows("T1_dataset_summary_by_session.csv") if r["row_type"] == "session"]
    ypos, y, prev = {}, 0.0, None
    for r in rows:
        if prev is not None and r["class"] != prev:
            y += 0.55
        ypos[r["session"]] = y
        y += 1.0
        prev = r["class"]
    return rows, ypos


def t4():
    return E.read_table("T4_feature_profile_%s.csv" % WL)


def class_n():
    r = t4()[0]
    return {"human": int(r["n_human"]), "ai": int(r["n_ai"])}


def class_handles():
    return [Patch(facecolor=CLASS_COLOR[c], hatch=CLASS_HATCH[c], edgecolor="#ffffff", linewidth=0.0,
                  label=E.CLASS_LABEL[c]) for c in E.CLASSES]


def label_of(r):
    return r["feature"] + ("" if r["in_main_configuration"] == "yes" else " *")


# ------------------------------------------------------------------------------------------ E2
def fig_e2():
    rows, ypos = session_rows()
    ov = {r["item"]: r for r in E.read_table("E2_overview_pass2.csv")}
    tier = {t: sum(1 for r in t4() if r["tier"] == t) for t in C.TIERS}
    fig = plt.figure(figsize=(W, 3.25))
    ax_t = fig.add_axes([0.012, 0.05, 0.325, 0.86])
    ax_b = fig.add_axes([0.445, 0.145, 0.27, 0.765])
    ax_c = fig.add_axes([0.81, 0.145, 0.18, 0.765])
    ax_t.set_axis_off()
    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(0, 1)
    ax_t.add_patch(Rectangle((0, 0), 1, 1, facecolor="#f6f5f2", edgecolor="none", zorder=0))
    ax_t.text(0.04, 0.96, "Dataset overview", fontsize=FS + 0.5, fontweight="bold", va="top")
    lines = [
        ("Sessions", P1.fmt(ov["sessions"]["all"]), False),
        ("human / AI", "%s / %s" % (ov["sessions"]["human"], ov["sessions"]["ai"]), True),
        ("Logins used", P1.fmt(ov["logins_used"]["all"]), False),
        ("human / AI", "%s / %s" % (ov["logins_used"]["human"], ov["logins_used"]["ai"]), True),
        ("Raw records", P1.fmt(ov["raw_records"]["all"]), False),
        ("Classifier input", P1.fmt(ov["classifier_input_records"]["all"]), False),
        ("Kept windows", P1.fmt(ov["kept_windows_30s"]["all"]), False),
        ("human / AI", "%s / %s" % (ov["kept_windows_30s"]["human"], ov["kept_windows_30s"]["ai"]), True),
        ("Window length", "%s s" % ov["window_length_s"]["all"], False),
        ("Feature columns", ov["feature_columns_by_tier"]["all"], False),
        ("behavior / content", "%d / %d" % (tier["behavior"], tier["command_content"]), True),
        ("context / input", "%d / %d" % (tier["context"], tier["input_channel"]), True),
        ("Undefined in a window", ov["columns_with_undefined_values"]["all"], False),
    ]
    y, step = 0.862, 0.0655
    for label, value, sub in lines:
        ax_t.text(0.10 if sub else 0.04, y, label, va="center", color=MUTED if sub else INK)
        ax_t.text(0.96, y, value, va="center", ha="right", color=MUTED if sub else INK,
                  fontweight="normal" if sub else "bold")
        y -= step

    top = max(int(r["kept_30s"]) for r in rows)
    for r in rows:
        v = int(r["kept_30s"])
        P1.class_bar(ax_b, ypos[r["session"]], v, r["class"])
        ax_b.text(v + top * 0.025, ypos[r["session"]], P1.fmt(v), va="center", ha="left")
    ax_b.set_yticks([ypos[r["session"]] for r in rows])
    ax_b.set_yticklabels([r["session"] for r in rows])
    ax_b.set_ylim(max(ypos.values()) + 0.6, -0.6)
    ax_b.set_xlim(0, top * 1.22)
    ax_b.set_xticks([0, 100, 200])
    ax_b.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax_b.set_axisbelow(True)
    ax_b.tick_params(axis="y", length=0)
    P1.clean_axes(ax_b, keep=("bottom",))
    ax_b.set_xlabel("Kept 30 s windows")
    ax_b.set_title("Kept windows per session", loc="left", pad=6)
    for cls in E.CLASSES:
        ys = [ypos[r["session"]] for r in rows if r["class"] == cls]
        ax_b.text(top * 1.2, max(ys) - 0.5 if cls == "human" else min(ys) + 1.0, E.CLASS_LABEL[cls],
                  ha="right", va="center", color=INK, fontweight="bold")

    n = {c: int(ov["kept_windows_30s"][c]) for c in E.CLASSES}
    p = {c: ov["kept_windows_30s_pct"][c] for c in E.CLASSES}
    for i, c in enumerate(E.CLASSES):
        ax_c.bar(i, n[c], width=0.62, color=CLASS_COLOR[c], hatch=CLASS_HATCH[c], edgecolor="#ffffff",
                 linewidth=0.0, zorder=3)
        ax_c.text(i, n[c] + max(n.values()) * 0.02, "%s\n%s%%" % (P1.fmt(n[c]), p[c]), ha="center", va="bottom",
                  linespacing=1.15)
    ax_c.set_xticks([0, 1])
    ax_c.set_xticklabels([E.CLASS_LABEL[c] for c in E.CLASSES])
    ax_c.set_xlim(-0.55, 1.55)
    ax_c.set_ylim(0, max(n.values()) * 1.27)
    ax_c.set_yticks([0, 200, 400, 600])
    ax_c.yaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax_c.set_axisbelow(True)
    ax_c.tick_params(axis="x", length=0)
    P1.clean_axes(ax_c, keep=("bottom",))
    ax_c.set_title("Class distribution", loc="left", pad=6)
    P1.save(fig, "E2_dataset_summary_pass2")


# ------------------------------------------------------------------------------------------ E1
def mask(s):
    return re.sub(r"[0-9]", "0", re.sub(r"[A-Za-z]", "x", s))


def wrap_name(name):
    if len(name) <= 13 or "_" not in name:
        return name
    cuts = [i for i, ch in enumerate(name) if ch == "_"]
    i = min(cuts, key=lambda k: abs(k - len(name) / 2.0))
    return name[:i + 1] + "\n" + name[i + 1:]


def fig_e1(masked):
    lines = E.read_table("E1_data_example.csv")
    summ = {r["class"]: r for r in E.read_table("E1_window_summary.csv")}
    feats = E.read_table("E1_feature_rows.csv")
    show = mask if masked else (lambda s: s)
    n_lines = max([sum(1 for l in lines if l["class"] == c) for c in E.CLASSES] + [1])
    row_h, head_h, table_h = 0.335, 0.62, 1.12
    height = head_h + n_lines * row_h + table_h + 0.12
    fig = plt.figure(figsize=(W, height))
    top = 1.0 - 0.06 / height
    for k, cls in enumerate(E.CLASSES):
        x0 = 0.012 + k * 0.496
        ax = fig.add_axes([x0, (table_h + 0.06) / height, 0.48, (head_h + n_lines * row_h) / height])
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(head_h + n_lines * row_h, 0)                 # inches from the top
        ax.add_patch(Rectangle((0, 0), 1, head_h + n_lines * row_h, facecolor="#f6f5f2", edgecolor="none", zorder=0))
        ax.add_patch(Rectangle((0, 0), 0.012, head_h + n_lines * row_h, facecolor=CLASS_COLOR[cls],
                               hatch=CLASS_HATCH[cls], edgecolor="#ffffff", linewidth=0.0, zorder=1))
        s = summ[cls]
        if not s["session"]:
            ax.text(0.04, 0.2, "%s: no window passed the rule" % E.CLASS_LABEL[cls], va="center")
            continue
        ax.text(0.04, 0.17, "%s operator, %s" % (E.CLASS_LABEL[cls], s["session"]), fontweight="bold", va="center")
        ax.text(0.04, 0.41, "One 30 s training window, stages 1–4, holding\n%s input, %s output, %s program-start records"
                % (s["input_records"], s["output_records"], s["program_starts"]),
                va="center", color=MUTED, linespacing=1.2)
        y = head_h
        for l in [l for l in lines if l["class"] == cls]:
            what = l["kind"]
            ax.text(0.04, y + 0.085, "%s s   %s, %s   %s" % (l["t_in_window_s"], l["source"], what, l["detail"]),
                    va="center", color=MUTED)
            ax.text(0.04, y + 0.235, show(l["text"]), va="center", family=MONO, fontsize=FS - 0.4)
            y += row_h
    # the two feature rows, six columns
    ax = fig.add_axes([0.012, 0.03 / height, 0.976, (table_h - 0.02) / height])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    col0, cw = 0.135, (1.0 - 0.135) / max(len(feats), 1)
    ax.text(0.0, 0.93, "Feature rows built from the two windows (six of 60 columns)", va="center", fontweight="bold")
    for j, f in enumerate(feats):
        xc = col0 + (j + 0.5) * cw
        ax.text(xc, 0.66, wrap_name(f["feature"]), ha="center", va="center", linespacing=1.1)
    ax.plot([0, 1], [0.47, 0.47], color=MUTED, linewidth=0.6)
    for i, cls in enumerate(E.CLASSES):
        yy = 0.33 - i * 0.22
        ax.text(0.0, yy, "%s %s" % (E.CLASS_LABEL[cls], summ[cls]["session"]), va="center")
        for j, f in enumerate(feats):
            v = f[cls]
            ax.text(col0 + (j + 0.5) * cw, yy, show(v) if v != "undefined" else v, ha="center", va="center",
                    color=MUTED if v == "undefined" else INK, family=MONO if v != "undefined" else None,
                    fontsize=FS - 0.4 if v != "undefined" else FS)
    P1.save(fig, "E1_data_example_masked" if masked else "E1_data_example")


# ------------------------------------------------------------------------------------------ E5
def fig_e5():
    rows = E.read_table("E5_machines_by_class.csv")
    names = []
    for r in rows:
        if r["machine"] not in names:
            names.append(r["machine"])
    get = {(r["machine"], r["class"]): r for r in rows}
    fig = plt.figure(figsize=(W, 3.0))
    ax = fig.add_axes([0.235, 0.215, 0.39, 0.685])
    ax2 = fig.add_axes([0.705, 0.215, 0.265, 0.685])
    off = {"human": -0.2, "ai": 0.2}
    top = max(float(r["share_pct"]) for r in rows)
    for i, m in enumerate(names):
        for cls in E.CLASSES:
            r = get[(m, cls)]
            v = float(r["share_pct"])
            ax.barh(i + off[cls], v, height=0.36, color=CLASS_COLOR[cls], hatch=CLASS_HATCH[cls], edgecolor="#ffffff",
                    linewidth=0.0, zorder=3)
            ax.text(v + top * 0.02, i + off[cls], "%.0f%%" % v if v >= 9.95 else "%.1f%%" % v, va="center", ha="left")
            k = int(r["sessions_addressing"])
            ax2.barh(i + off[cls], k, height=0.36, color=CLASS_COLOR[cls], hatch=CLASS_HATCH[cls], edgecolor="#ffffff",
                     linewidth=0.0, zorder=3)
            ax2.text(k + 0.12, i + off[cls], "%d of %s" % (k, r["sessions_in_class"]), va="center", ha="left")
    for a in (ax, ax2):
        a.set_ylim(len(names) - 0.45, -0.55)
        a.tick_params(axis="y", length=0)
        a.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
        a.set_axisbelow(True)
        P1.clean_axes(a, keep=("bottom",))
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(["%s (%s)\n%s" % (m, get[(m, "human")]["role"], get[(m, "human")]["address"]) for m in names],
                       linespacing=1.15)
    ax.set_xlim(0, top * 1.22)
    ax.set_xlabel("Share of the class's commands (%)")
    ax.set_title("Commands that name the machine", loc="left", pad=6)
    ax2.set_yticks([])
    ax2.set_xlim(0, 6.9)
    ax2.set_xticks([0, 1, 2, 3, 4, 5])
    ax2.set_xlabel("Sessions")
    ax2.set_title("Sessions that addressed it", loc="left", pad=6)
    fig.legend(handles=class_handles(), loc="lower left", bbox_to_anchor=(0.012, 0.012), ncol=2, frameon=False,
               handlelength=1.3, handleheight=1.0, columnspacing=1.6, handletextpad=0.5, borderaxespad=0.0)
    P1.save(fig, "E5_machines_named")


# ------------------------------------------------------------------------------------------ E7
def stacked(ax, table, key, order, labels, colors):
    for i, cls in enumerate(E.CLASSES):
        left = 0.0
        for k, name in enumerate(order):
            r = next(x for x in table if x["class"] == cls and x[key] == name)
            v = float(r["share_pct"])
            ax.barh(i, v, left=left, height=0.62, color=colors[k], edgecolor="#ffffff", linewidth=0.9, zorder=3)
            if v >= 7.5:
                ax.text(left + v / 2.0, i, "%.0f%%" % v, ha="center", va="center", zorder=4,
                        color="#ffffff" if k >= len(order) - 1 - (len(order) == 4) else INK)
            elif v > 0:
                ax.text(left + v / 2.0, i - 0.36, "%.0f%%" % v, ha="center", va="bottom", zorder=4, color=INK)
            left += v
    ax.set_xlim(0, 100)
    ax.set_ylim(1.5, -0.5)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="y", length=0)
    P1.clean_axes(ax, keep=("bottom",))
    return [Patch(facecolor=colors[k], edgecolor="none", label=labels[k]) for k in range(len(order))]


def fig_e7():
    act = E.read_table("E7_window_activity_by_class.csv")
    ent = E.read_table("E7_entry_style_by_class.csv")
    nw = {c: next(r["class_windows"] for r in act if r["class"] == c) for c in E.CLASSES}
    nc = {c: next(r["class_commands"] for r in ent if r["class"] == c) for c in E.CLASSES}
    fig = plt.figure(figsize=(W, 2.6))
    ax = fig.add_axes([0.125, 0.5, 0.345, 0.375])
    ax2 = fig.add_axes([0.635, 0.5, 0.345, 0.375])
    h1 = stacked(ax, act, "window_type", ["quiet", "no_program", "programs"],
                 ["No command", "Only commands that started no program", "Commands that started programs"], GRAY3)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["%s\nn = %s" % (E.CLASS_LABEL[c], P1.fmt(nw[c])) for c in E.CLASSES], linespacing=1.15)
    ax.set_xlabel("Share of the class's training windows (%)")
    ax.set_title("What a window holds", loc="left", pad=6)
    ax.legend(handles=h1, loc="upper left", bbox_to_anchor=(-0.37, -0.5), frameon=False, handlelength=1.2,
              handleheight=1.0, labelspacing=0.45, handletextpad=0.5, borderaxespad=0.0)
    h2 = stacked(ax2, ent, "entry_style", ["typed", "paste", "recall", "line"],
                 ["Typed", "Pasted", "Recalled from history", "Written as a whole line"], GRAY4)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["%s\nn = %s" % (E.CLASS_LABEL[c], P1.fmt(nc[c])) for c in E.CLASSES], linespacing=1.15)
    ax2.set_xlabel("Share of the class's commands (%)")
    ax2.set_title("Command entry (diagnostic)", loc="left", pad=6)
    ax2.legend(handles=h2, loc="upper left", bbox_to_anchor=(-0.37, -0.5), frameon=False, ncol=2, handlelength=1.2,
               handleheight=1.0, labelspacing=0.45, columnspacing=1.2, handletextpad=0.5, borderaxespad=0.0)
    P1.save(fig, "E7_activity_and_entry")


# ------------------------------------------------------------------------------------------ E8
def fig_e8():
    top = E.read_table("E8_top_programs.csv")
    heat = {(r["program"], r["class"], r["stage_group"]): r for r in E.read_table("E8_program_stage_heatmap.csv")}
    n = len(top)
    fig = plt.figure(figsize=(W, 4.75))
    ax = fig.add_axes([0.268, 0.185, 0.285, 0.675])
    hx = fig.add_axes([0.612, 0.185, 0.376, 0.675])
    most = max(int(r["training_windows"]) for r in top)
    for i, r in enumerate(top):
        left = 0
        for g in E.STAGE_GROUPS:
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
            for k, g in enumerate(E.STAGE_GROUPS):
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
    hx.set_xticklabels([STAGE_SHORT[g] for _ in E.CLASSES for g in E.STAGE_GROUPS])
    hx.set_yticks([])
    hx.tick_params(axis="x", length=0)
    P1.clean_axes(hx, keep=())
    for cls in E.CLASSES:
        hx.text(x0[cls] + 2.0, -0.95, E.CLASS_LABEL[cls], ha="center", va="center", fontweight="bold")
    hx.set_xlabel("Stage group")
    hx.set_title("Share of the class's windows\nin the stage group (%)", loc="left", pad=17, linespacing=1.15)
    handles = [Patch(facecolor=STAGE_COLOR[g], edgecolor="none", label=E.STAGE_GROUP_LABEL[g]) for g in E.STAGE_GROUPS]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.058), ncol=4, frameon=False,
               handlelength=1.2, handleheight=1.0, columnspacing=1.2, handletextpad=0.5, borderaxespad=0.0)
    h2 = [Patch(facecolor="none", edgecolor=INK, linewidth=1.1, label="Run by one class only"),
          Patch(facecolor=NO_DATA, edgecolor="none", label="The class has no training window in the stage group")]
    fig.legend(handles=h2, loc="lower left", bbox_to_anchor=(0.012, 0.012), ncol=2, frameon=False,
               handlelength=1.4, handleheight=1.0, columnspacing=1.2, handletextpad=0.5, borderaxespad=0.0)
    P1.save(fig, "E8_programs_started")


# ------------------------------------------------------------------------------------------ E9
def fig_e9():
    pairs = E.read_table("E9_spearman_top20.csv")
    name = {}
    for p in pairs:
        name[int(p["rank_a"])] = p["feature_a"]
        name[int(p["rank_b"])] = p["feature_b"]
    main = {r["feature"]: r["in_main_configuration"] for r in t4()}
    n = max(name)
    fig = plt.figure(figsize=(W, 6.25))
    cell = 0.925 / (n - 1)
    ax = fig.add_axes([0.055, 0.06, 0.925, cell * (n - 1) * W / 6.25])
    for p in pairs:
        a, b = int(p["rank_a"]), int(p["rank_b"])              # a > b: row a, column b
        rho = num(p["spearman_rho"])
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
    ax.set_xlabel("Feature (rank by single-feature AUC, after merging near-duplicates)")
    # key in the empty upper triangle: rank and feature
    x_key = 0.618
    fig.text(x_key, 0.972, "Rank and feature", fontweight="bold", va="center")
    for i in range(1, n + 1):
        fig.text(x_key + 0.028, 0.972 - i * 0.0238, str(i), ha="right", va="center", color=MUTED)
        fig.text(x_key + 0.043, 0.972 - i * 0.0238, name[i] + ("" if main[name[i]] == "yes" else " *"), va="center")
    fig.text(x_key, 0.972 - (n + 1.15) * 0.0238, "* not in the main configuration", va="center", color=MUTED)
    cax = fig.add_axes([0.27, 0.925, 0.29, 0.016])
    for k in range(100):                               # drawn as patches: no embedded image in the SVG
        cax.add_patch(Rectangle((-100 + 2 * k, 0), 2.05, 1, facecolor=DIVERGE((k + 0.5) / 100.0), edgecolor="none"))
    cax.set_xlim(-100, 100)
    cax.set_ylim(0, 1)
    cax.set_yticks([])
    cax.set_xticks([-100, -50, 0, 50, 100])
    cax.set_xticklabels(["−100", "−50", "0", "50", "100"])
    cax.tick_params(length=2)
    for side in ("left", "right", "top", "bottom"):
        cax.spines[side].set_visible(False)
    fig.text(0.27, 0.958, "Spearman ρ × 100", va="center")
    P1.save(fig, "E9_spearman_top20")


# ------------------------------------------------------------------------------------------ E10
def auc_axis(ax, feats, xlim=(0.36, 1.115)):
    for i, r in enumerate(feats):
        auc = num(r["auc"])
        if auc is None:
            ax.text(0.515, i, "no AI value", va="center", ha="left", color=MUTED,
                    bbox=dict(facecolor="#ffffff", edgecolor="none", pad=0.8), zorder=6)
            continue
        cls = r["higher_in"]
        ax.barh(i, auc - 0.5, left=0.5, height=0.64, color=CLASS_COLOR[cls], hatch=CLASS_HATCH[cls],
                edgecolor="#ffffff", linewidth=0.0, zorder=3)
        lo, hi = num(r["auc_drop_min"]), num(r["auc_drop_max"])
        ax.plot([lo, hi], [i, i], color=INK, linewidth=0.9, zorder=4, solid_capstyle="butt")
        for x in (lo, hi):
            ax.plot([x, x], [i - 0.2, i + 0.2], color=INK, linewidth=0.9, zorder=4, solid_capstyle="butt")
        ax.text(xlim[1], i, "%.2f" % auc, va="center", ha="right")
    ax.axvline(0.5, color=MUTED, linewidth=0.7, zorder=2)
    ax.axvline(C.FLAG, color=INK, linewidth=0.8, linestyle=(0, (4, 2)), zorder=2)
    ax.set_xlim(*xlim)
    ax.set_ylim(len(feats) - 0.45, -0.55)
    ax.set_yticks(range(len(feats)))
    ax.set_yticklabels([label_of(r) for r in feats])
    ax.tick_params(axis="y", length=0)
    ax.set_xticks([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    P1.clean_axes(ax, keep=("bottom",))


def auc_legend(fig, y=0.012):
    handles = [Patch(facecolor=CLASS_COLOR["human"], edgecolor="#ffffff", linewidth=0.0, label="Higher in human windows"),
               Patch(facecolor=CLASS_COLOR["ai"], hatch=CLASS_HATCH["ai"], edgecolor="#ffffff", linewidth=0.0,
                     label="Higher in AI windows"),
               Line2D([0], [0], color=INK, linewidth=0.9, marker="|", markersize=6, label="Range with one session left out"),
               Line2D([0], [0], color=INK, linewidth=0.8, linestyle=(0, (4, 2)), label="0.95 flag")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, y), ncol=2, frameon=False, handlelength=1.6,
               handleheight=1.0, columnspacing=1.6, labelspacing=0.4, handletextpad=0.5, borderaxespad=0.0)
    fig.text(0.988, y + 0.004, "* not in the main configuration", ha="right", va="bottom", color=MUTED)


def by_tier(rows):
    out = []
    for t in C.TIERS:
        fs = sorted([r for r in rows if r["tier"] == t], key=lambda r: int(r["rank"]))
        if fs:
            out.append((t, fs))
    return out


def fig_e10_top20():
    rows = [r for r in t4() if r["top20_rank"] != ""]
    groups = by_tier(rows)
    row_h, gap, bottom_in, top_in = 0.185, 0.36, 0.86, 0.3
    height = bottom_in + top_in + sum(len(fs) for _, fs in groups) * row_h + (len(groups) - 1) * gap
    fig = plt.figure(figsize=(W, height))
    y = height - top_in
    for k, (t, fs) in enumerate(groups):
        h = len(fs) * row_h
        ax = fig.add_axes([0.305, (y - h) / height, 0.68, h / height])
        auc_axis(ax, fs)
        ax.set_title("%s (%d of the top %d)" % (TIER_LABEL[t], len(fs), len(rows)), loc="left", pad=4)
        if k < len(groups) - 1:
            ax.set_xticklabels([])
            ax.tick_params(axis="x", length=0)
        else:
            ax.set_xlabel("Single-feature AUC on training windows")
        y -= h + gap
    auc_legend(fig)
    P1.save(fig, "E10_auc_top20")


def fig_e10_full():
    groups = dict(by_tier(t4()))
    cols = [["behavior", "context"], ["command_content", "input_channel"]]
    row_h, gap, bottom_in, top_in = 0.172, 0.66, 0.86, 0.3
    height = bottom_in + top_in + max(sum(len(groups[t]) for t in c) for c in cols) * row_h + gap
    fig = plt.figure(figsize=(W, height))
    for j, c in enumerate(cols):
        y = height - top_in
        for k, t in enumerate(c):
            fs = groups[t]
            h = len(fs) * row_h
            ax = fig.add_axes([0.268 + j * 0.495, (y - h) / height, 0.222, h / height])
            auc_axis(ax, fs, xlim=(0.36, 1.25))
            ax.set_xticks([0.4, 0.6, 0.8, 1.0])
            ax.set_title("%s (%d)" % (TIER_LABEL[t], len(fs)), loc="right", pad=4)
            if k == len(c) - 1:
                ax.set_xlabel("Single-feature AUC")
            y -= h + gap
    auc_legend(fig)
    P1.save(fig, "E10_auc_all_features")


# ------------------------------------------------------------------------------------------ E11
def sym_ticks(ax, top):
    ticks = [0, 1, 10, 100, 1000, 10000, 100000, 1000000, 10000000]
    ticks = [t for t in ticks if t <= max(top, 1) * 1.001] or [0, 1]
    if len(ticks) > 5:
        ticks = [ticks[0]] + ticks[2::2] if len(ticks) % 2 else ticks[::2]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_minor_locator(NullLocator())

    def lab(v, _):
        if v >= 1000000:
            return "%gM" % (v / 1000000.0)
        if v >= 1000:
            return "%gk" % (v / 1000.0)
        return "%g" % v
    ax.yaxis.set_major_formatter(FuncFormatter(lab))


def fig_e11():
    pts = E.read_table("E11_points.csv")
    med = E.read_table("E11_session_medians.csv")
    prof = {r["feature"]: r for r in t4()}
    feats = []
    for r in med:
        if r["feature"] not in feats:
            feats.append(r["feature"])
    sessions = {c: [] for c in E.CLASSES}
    for r in med:
        if r["session"] not in sessions[r["class"]]:
            sessions[r["class"]].append(r["session"])
    ncol, nrow = 3, 4
    height, top_in, block, plot_h = 8.4, 0.52, 1.88, 1.2
    fig = plt.figure(figsize=(W, height))
    for k, f in enumerate(feats):
        i, j = divmod(k, ncol)
        ax = fig.add_axes([0.072 + j * 0.318, (height - top_in - i * block - plot_h) / height, 0.245, plot_h / height])
        vals = {c: np.array([float(p["value"]) for p in pts if p["feature"] == f and p["class"] == c]) for c in E.CLASSES}
        top = max([v.max() for v in vals.values() if len(v)] + [1.0])
        low = min([v.min() for v in vals.values() if len(v)] + [0.0])
        log = top > 20
        rng = np.random.default_rng(42 + k)
        for x, c in enumerate(E.CLASSES):
            v = vals[c]
            ax.scatter(x + rng.uniform(-0.3, 0.3, size=len(v)), v, s=5, color=CLASS_COLOR[c], alpha=0.22, linewidths=0,
                       zorder=2)                      # vector points: no embedded image in the SVG
            r = prof[f]
            q1, q2, q3 = num(r["q1_" + c]), num(r["median_" + c]), num(r["q3_" + c])
            if q2 is not None:
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
            sym_ticks(ax, top)
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
        r = prof[f]
        ax.set_title(label_of(r), loc="left", pad=15)
        ax.text(0.0, 1.035, "AUC %.2f, higher in %s" % (float(r["auc"]), "human" if r["higher_in"] == "human" else "AI"),
                transform=ax.transAxes, ha="left", va="bottom", color=MUTED)
    handles = [Line2D([0], [0], linestyle="none", marker="o", markersize=3, color=MUTED, alpha=0.5, label="One training window"),
               Line2D([0], [0], linestyle="none", marker="o", markersize=5.5, markerfacecolor=CLASS_COLOR["human"],
                      markeredgecolor="#ffffff", label="Median of one human session"),
               Line2D([0], [0], linestyle="none", marker="D", markersize=5, markerfacecolor=CLASS_COLOR["ai"],
                      markeredgecolor="#ffffff", label="Median of one AI session"),
               Patch(facecolor="none", edgecolor=INK, linewidth=0.9, label="Class median and interquartile range")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.047), ncol=2, frameon=False, handlelength=1.4,
               columnspacing=1.6, labelspacing=0.4, handletextpad=0.5, borderaxespad=0.0)
    fig.text(0.012, 0.027, "Session markers, left to right: %s (human); %s (AI)."
             % (" ".join(sessions["human"]), " ".join(sessions["ai"])), ha="left", va="bottom", color=MUTED)
    fig.text(0.012, 0.007, "* not in the main configuration", ha="left", va="bottom", color=MUTED)
    P1.save(fig, "E11_top12_distributions")


# ------------------------------------------------------------------------------------------ E12
def fig_e12():
    rows = E.read_table("T7_top20_by_stage_%s.csv" % WL)
    counts = {(r["class"], r["stage_group"]): r for r in E.read_table("T7_stage_group_training_windows_%s.csv" % WL)}
    groups = [g for g in E.STAGE_GROUPS if counts[("human", g)]["at_least_10_in_both_classes"] == "yes"]
    n = len(rows)
    fig = plt.figure(figsize=(W, 5.75))
    left, width, gap = 0.292, 0.212, 0.026
    for k, g in enumerate(groups):
        ax = fig.add_axes([left + k * (width + gap), 0.165, width, 0.715])
        key = GROUP_KEY[g]
        for i, r in enumerate(rows):
            a_all, a_st = num(r["auc_all"]), num(r[key + "_auc_dir"])
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
        ax.set_yticklabels(["%s  %s" % (r["top20_rank"], label_of(r)) for r in rows] if k == 0 else [])
        ax.tick_params(axis="y", length=0)
        ax.xaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
        ax.yaxis.grid(True, color="#ededed", linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)
        P1.clean_axes(ax, keep=("bottom",))
        h, a = counts[("human", g)], counts[("ai", g)]
        ax.set_title("%s\nhuman %s (%s)\nAI %s (%s)"
                     % (E.STAGE_GROUP_LABEL[g], h["training_windows"], h["sessions"],
                        a["training_windows"], a["sessions"]), loc="left", pad=5, linespacing=1.15)
        if k == 1:
            ax.set_xlabel("Single-feature AUC, in the direction it has over all training windows")
    handles = [Line2D([0], [0], linestyle="none", marker="o", markersize=6, color=SHADE_ALL, label="All training windows"),
               Line2D([0], [0], linestyle="none", marker="o", markersize=6, color=SHADE_STAGE, label="Within the stage group")]
    if any(r[GROUP_KEY[g] + "_indicative"] == "yes" for r in rows for g in groups):
        handles.append(Line2D([0], [0], linestyle="none", marker="o", markersize=6, markerfacecolor="#ffffff",
                              markeredgecolor=SHADE_STAGE, markeredgewidth=1.2, label="Fewer than 10 windows in a class"))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.047), ncol=3, frameon=False, handlelength=1.0,
               columnspacing=1.4, handletextpad=0.4, borderaxespad=0.0)
    fig.text(0.012, 0.012, "Panel titles: training windows (sessions) of each class.   * not in the main configuration",
             ha="left", va="bottom", color=MUTED)
    P1.save(fig, "E12_all_windows_against_same_stage")


# ------------------------------------------------------------------------------------------ captions
def captions():
    n = class_n()
    prof = t4()
    flagged = [r for r in prof if r["flag"] == "yes"]
    top = [r for r in prof if r["top20_rank"] != ""]
    e1 = {r["class"]: r for r in E.read_table("E1_window_summary.csv")}
    e8 = E.read_table("E8_top_programs.csv")
    ent = {(r["class"], r["entry_style"]): r for r in E.read_table("E7_entry_style_by_class.csv")}
    counts = {(r["class"], r["stage_group"]): r for r in E.read_table("T7_stage_group_training_windows_%s.csv" % WL)}
    groups = [g for g in E.STAGE_GROUPS if counts[("human", g)]["at_least_10_in_both_classes"] == "yes"]
    nn = "n = %s training windows (%s human, %s AI)" % (P1.fmt(n["human"] + n["ai"]), n["human"], n["ai"])
    tier = {t: sum(1 for r in prof if r["tier"] == t) for t in C.TIERS}
    lines = [
        "# EDA Pass 2: figure captions",
        "",
        "Drawn from the tables in `reports/eda/tables/`. Feature values and command text come from the rows marked "
        "`train` in the frozen split file only: %s. Pass 2 was run after the models were scored, as a report "
        "(handoff 12a). Sessions are labeled as in Table 4-1; humans first. An asterisk marks a column that is not "
        "in the main configuration." % nn,
        "",
        "**E1. Data example.** Cleaned recorder and audit records from one training window of stages 1 to 4 for each "
        "class (%s, human; %s, AI), with the placeholders the cleaning leaves, and the six highest-ranked feature "
        "columns of the two windows. Times are seconds from the start of the window. **To be read by a person for "
        "credentials before use.** `E1_data_example_masked` is the same figure with every letter and digit masked."
        % (e1["human"]["session"] or "none", e1["ai"]["session"] or "none"),
        "",
        "**E2. Statistical summary of the dataset.** As in Pass 1, with the feature columns filled in: %d columns "
        "(behavior %d, command content %d, context %d, input channel %d); %s are undefined in at least one kept "
        "window. All kept windows, not training rows."
        % (len(prof), tier["behavior"], tier["command_content"], tier["context"], tier["input_channel"],
           next(r["all"] for r in E.read_table("E2_overview_pass2.csv") if r["item"] == "columns_with_undefined_values")),
        "",
        "**E5. Lab machines named in commands.** Left: share of each class's training commands that name the machine "
        "by host name or address. Right: sessions that addressed it. Commands: %s human, %s AI."
        % (ent[("human", "typed")]["class_commands"], ent[("ai", "typed")]["class_commands"]),
        "",
        "**E7. Window activity and command entry.** Left: share of each class's training windows that hold no "
        "command, only commands that started no program (a line typed into a waiting program, or a shell built-in), "
        "or commands that started programs. Right: how the commands of those windows reached the shell; this panel "
        "is input-channel data and is diagnostic. %s; commands: %s human, %s AI."
        % (nn, ent[("human", "typed")]["class_commands"], ent[("ai", "typed")]["class_commands"]),
        "",
        "**E8. Programs started.** Left: the %d programs started in the most training windows, split by stage "
        "group. Right: for each class, the share of its training windows in the stage group in which the program "
        "started; a row is outlined where only one class ran the program; gray: the class has no training window in "
        "the stage group. A window counts once however often the program ran in it. %s."
        % (len(e8), nn),
        "",
        "**E9. Spearman correlation of the top 20 features.** Lower triangle, ρ × 100, on the rows where both "
        "features are defined. Features are ranked by single-feature AUC after near-duplicates (|ρ| > %.2f) are "
        "merged. %s." % (C.DUP_RHO, nn),
        "",
        "**E10. Single-feature AUC.** AUC of each feature alone on the rows where it is defined, by tier. Bar color: "
        "the class in which the feature is higher. Whisker: the range when each session in turn is left out, in the "
        "same direction. Dashed line: the 0.95 shortcut flag. `E10_auc_top20`: the top 20 after merging. "
        "`E10_auc_all_features`: all %d columns; four input-channel columns have no AI value. Flagged: %s. %s."
        % (len(prof), ", ".join("`%s` (%.3f)" % (r["feature"], float(r["auc"])) for r in flagged) or "none", nn),
        "",
        "**E11. Distributions of the 12 strongest features.** For each class: one point per training window, the "
        "class median and interquartile range, and one marker per session median. A log axis is used where the "
        "values pass 20. %s; a feature is plotted on the rows where it is defined." % nn,
        "",
        "**E12. AUC over all training windows against AUC within the same stage group.** Top %d features. The "
        "same-stage value is kept in the direction the feature has over all training windows, so a value under 0.5 "
        "is a reversal. Stage groups with at least %d training windows in both classes: %s. Stage 6 has no AI "
        "training window." % (len(top), C.MIN_WINDOWS,
                              "; ".join("%s (human %s, AI %s)" % (E.STAGE_GROUP_LABEL[g], counts[("human", g)]["training_windows"],
                                                                  counts[("ai", g)]["training_windows"]) for g in groups)),
        "",
    ]
    with open(os.path.join(E.FIGURES, "captions_pass2.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


PASS2_FIGURES = ("E1_", "E2_dataset_summary_pass2", "E5_", "E7_", "E8_", "E9_", "E10_", "E11_", "E12_", "captions_pass2")


def main():
    os.makedirs(E.FIGURES, exist_ok=True)
    fig_e1(False)
    fig_e1(True)
    fig_e2()
    fig_e5()
    fig_e7()
    fig_e8()
    fig_e9()
    fig_e10_top20()
    fig_e10_full()
    fig_e11()
    fig_e12()
    captions()
    names = sorted(n for n in os.listdir(E.FIGURES) if n.startswith(PASS2_FIGURES))
    log = {"pass": "EDA Pass 2 (figures)", "eda_version": E.EDA_VERSION, "pass2_version": C.PASS2_VERSION,
           "drawn_from": "reports/eda/tables/ only",
           "libraries": {"matplotlib": matplotlib.__version__, "numpy": np.__version__},
           "figures": {n: E.sha256_file(os.path.join(E.FIGURES, n)) for n in names}}
    E.write_json(os.path.join(E.OUT, "pass2_figures_log.json"), log)
    print("COMPLETE: Pass 2 figures", len(names), "files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
