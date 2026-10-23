#!/usr/bin/env python3
"""Plot the weighted mean net worth gap between families with children whose
reference person has a bachelor's degree or more and those whose reference
person has a high-school education or less, SCF 1989-2025.

Reads data/processed/scfp_selected.csv (built by get_data.py) and writes:
    results/mean_networth_by_education.csv
    figures/mean_networth_by_education.png
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed" / "scfp_selected.csv"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

# EDCL: 1 no high-school diploma, 2 high-school diploma/GED,
#       3 some college/associate degree (excluded), 4 bachelor's degree or more.
GROUPS = {4: "Bachelor's or more", 1: "High school or less", 2: "High school or less"}
COLLEGE, HS = "Bachelor's or more", "High school or less"

# Light-mode palette and chart ink (validated with the dataviz palette checker).
COLORS = {COLLEGE: "#2a78d6", HS: "#eb6834"}
INK, INK_2, MUTED, GRID, AXIS, SURFACE = (
    "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb")


def weighted_mean(x, w):
    return np.sum(x * w) / np.sum(w)


# The lab later switches to medians: replace this with a weighted median.
STATISTIC = weighted_mean


def summarize(df):
    """Statistic per year and group, computed within each of the five
    implicates and then averaged across them (the Fed's convention)."""
    df = df[df["kids"] > 0].copy()
    df["group"] = df["edcl"].map(GROUPS)
    df = df.dropna(subset=["group"])
    df["implicate"] = df["y1"] - 10 * df["yy1"]

    per_imp = (df.groupby(["year", "group", "implicate"])
                 .apply(lambda g: STATISTIC(g["networth"].to_numpy(), g["wgt"].to_numpy()),
                        include_groups=False)
                 .rename("value").reset_index())
    stat = per_imp.groupby(["year", "group"])["value"].mean().unstack("group")
    n = df.groupby(["year", "group"])["yy1"].nunique().unstack("group")

    out = pd.DataFrame({
        "mean_networth_bachelors_plus": stat[COLLEGE],
        "mean_networth_hs_or_less": stat[HS],
        "gap_dollars": stat[COLLEGE] - stat[HS],
        "ratio": stat[COLLEGE] / stat[HS],
        "n_households_bachelors_plus": n[COLLEGE],
        "n_households_hs_or_less": n[HS],
    })
    return out.reset_index()


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelcolor=INK_2, length=0, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def plot(res):
    """Academic-journal styling based on the POLISCI 158 Section 03 lab example.

    A single monochrome panel, distinct line/marker styles, labeled axes,
    a numbered caption and source note beneath the figure.
    """
    fig = plt.figure(figsize=(8.6, 6.25), facecolor="white")
    ax = fig.add_axes([0.105, 0.315, 0.845, 0.60])
    years = res["year"].to_numpy()
    ba = res["mean_networth_bachelors_plus"].to_numpy() / 1000
    hs = res["mean_networth_hs_or_less"].to_numpy() / 1000

    ax.plot(years, ba, color="#222222", linestyle="-", linewidth=1.4,
            marker="o", markersize=4.8, markerfacecolor="white",
            markeredgecolor="#222222", markeredgewidth=1.1,
            label="BA or more")
    ax.plot(years, hs, color="#555555", linestyle="--", linewidth=1.3,
            marker="s", markersize=4.5, markerfacecolor="white",
            markeredgecolor="#555555", markeredgewidth=1.0,
            label="HS or less")

    ax.set_xlim(1988, 2026)
    ax.set_ylim(0, 2400)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=8)
    ax.set_yticks(np.arange(0, 2401, 400))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.tick_params(axis="both", labelsize=8, direction="out",
                   width=0.65, length=3.0, colors="#222222")
    ax.set_ylabel("Mean net worth (thousands of 2025 dollars)", fontsize=9)
    ax.set_xlabel("Survey year", fontsize=9)
    for spine in ax.spines.values():
        spine.set_color("#222222")
        spine.set_linewidth(0.7)
    ax.grid(False)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.02),
              frameon=False, ncol=2, fontsize=9,
              handlelength=2.6, columnspacing=2.5)

    caption = (
        "Figure 1. Mean net worth of families with children, by education of reference person, "
        "1989–2025."
    )
    note = (
        "Note: Families with a child of the reference person living at home. Values in September-2025 "
        "dollars, adjusted with the CPI-U-RS.\n"
        "Source: Federal Reserve Board, Survey of Consumer Finances, 1989–2025 summary extract public data.\n"
        "Weighted means across five implicates; BA = bachelor's degree or more; HS = high school or less; "
        "some college excluded."
    )
    fig.text(0.105, 0.235, caption, ha="left", va="top",
             fontsize=9.2, color="#111111", fontfamily="serif")
    fig.text(0.105, 0.188, note, ha="left", va="top",
             fontsize=7.8, color="#333333", linespacing=1.45)

    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / "mean_networth_by_education.png"
    fig.savefig(path, dpi=220, facecolor="white")
    print(f"wrote {path.relative_to(ROOT)}")
    submission_path = ROOT / "figure.png"
    fig.savefig(submission_path, dpi=220, facecolor="white")
    print(f"wrote {submission_path.relative_to(ROOT)}")
    plt.close(fig)


def main():
    if not DATA.exists():
        sys.exit(f"{DATA.relative_to(ROOT)} not found; run get_data.py first.")
    res = summarize(pd.read_csv(DATA))
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / "mean_networth_by_education.csv"
    res.to_csv(path, index=False, float_format="%.2f")
    print(f"wrote {path.relative_to(ROOT)}")
    print(res.to_string(index=False))
    plot(res)


if __name__ == "__main__":
    main()
