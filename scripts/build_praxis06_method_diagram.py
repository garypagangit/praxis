from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def add_box(ax, xy, width, height, text, facecolor="#f8fafc", edgecolor="#334155"):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.035",
        linewidth=1.4,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=10,
        color="#0f172a",
        wrap=True,
    )


def add_arrow(ax, start, end, color="#334155"):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.5,
        color=color,
    )
    ax.add_patch(arrow)


def main() -> None:
    out_dir = Path("reports/tta_streaming_apt/paper_assets_20260509/figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    add_box(
        ax,
        (0.04, 0.58),
        0.18,
        0.22,
        "Held-out\nunlabeled\nstream",
        facecolor="#e0f2fe",
    )
    add_box(
        ax,
        (0.30, 0.72),
        0.20,
        0.18,
        "Frozen\nsupport-floor\nMLP",
        facecolor="#f1f5f9",
    )
    add_box(
        ax,
        (0.30, 0.38),
        0.20,
        0.18,
        "BN-adapted\ncandidate\nMLP",
        facecolor="#ecfdf5",
    )
    add_box(
        ax,
        (0.60, 0.56),
        0.20,
        0.24,
        "Selective gate\nuncertainty override\nRecon rescue\nDE guard",
        facecolor="#fff7ed",
    )
    add_box(
        ax,
        (0.86, 0.58),
        0.10,
        0.20,
        "Locked\nstage\nprediction",
        facecolor="#ede9fe",
    )

    add_arrow(ax, (0.22, 0.69), (0.30, 0.81))
    add_arrow(ax, (0.22, 0.66), (0.30, 0.47))
    add_arrow(ax, (0.50, 0.81), (0.60, 0.70))
    add_arrow(ax, (0.50, 0.47), (0.60, 0.62))
    add_arrow(ax, (0.80, 0.68), (0.86, 0.68))

    ax.text(
        0.40,
        0.29,
        "No test labels. Thresholds selected on validation, then replayed once on the locked test split.",
        ha="center",
        va="center",
        fontsize=9,
        color="#475569",
    )
    ax.text(
        0.70,
        0.47,
        "Goal: recover Reconnaissance while preserving Data Exfiltration.",
        ha="center",
        va="center",
        fontsize=9,
        color="#475569",
    )

    fig.suptitle(
        "Selective Test-Time Adaptation for Streaming APT Stage Detection",
        fontsize=14,
        fontweight="bold",
        color="#0f172a",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    png = out_dir / "figure1_method_diagram.png"
    svg = out_dir / "figure1_method_diagram.svg"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    print(png)
    print(svg)


if __name__ == "__main__":
    main()
