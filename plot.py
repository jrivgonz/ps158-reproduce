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
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(8, 7.5), sharex=True, height_ratios=[2, 1],
        facecolor=SURFACE, layout="constrained")
    years = res["year"]

    series = ((COLLEGE, "mean_networth_bachelors_plus"), (HS, "mean_networth_hs_or_less"))
    for group, col in series:
        top.plot(years, res[col] / 1000, color=COLORS[group], linewidth=2, marker="o",
                 markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5, label=group)
    # Latest values as end labels, nudged apart when the two lines end close together.
    ends = {g: res[c].iloc[-1] / 1000 for g, c in series}
    hi, lo = sorted(ends, key=ends.get, reverse=True)
    for group, nudge in ((hi, 7), (lo, -7)):
        top.annotate(f"${ends[group]:,.0f}k", (years.iloc[-1], ends[group]),
                     xytext=(8, nudge), textcoords="offset points", va="center",
                     fontsize=9, color=INK_2)
    style(top)
    top.set_ylim(bottom=0)
    top.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}k")
    top.set_title("Mean net worth, families with children (thousands of constant dollars)",
                  loc="left", fontsize=10, color=INK_2)
    top.legend(frameon=False, loc="upper left", fontsize=9, labelcolor=INK_2)

    bottom.plot(years, res["ratio"], color=INK_2, linewidth=2, marker="o",
                markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5)
    bottom.annotate(f"{res['ratio'].iloc[-1]:.1f}x", (years.iloc[-1], res["ratio"].iloc[-1]),
                    xytext=(8, 0), textcoords="offset points", va="center",
                    fontsize=9, color=INK_2)
    style(bottom)
    bottom.set_ylim(bottom=0)
    bottom.yaxis.set_major_formatter(lambda v, _: f"{v:g}x")
    bottom.set_title("Ratio: bachelor's or more ÷ high school or less",
                     loc="left", fontsize=10, color=INK_2)
    bottom.set_xticks(years)
    bottom.set_xlim(years.min() - 1, years.max() + 4)

    fig.suptitle("Wealth gap by the education of the family's reference person, "
                 f"{years.min()}–{years.max()}", x=0.01, ha="left",
                 fontsize=12, color=INK, fontweight="bold")
    fig.text(0.01, -0.02,
             "Source: Federal Reserve Survey of Consumer Finances, summary extract. "
             "Families with KIDS > 0; education is EDCL of the reference person;\n"
             "some college excluded. Weighted by WGT, averaged over the five implicates. "
             "Dollars as published in the extract release used.",
             fontsize=8, color=MUTED, ha="left", va="top")

    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / "mean_networth_by_education.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    print(f"wrote {path.relative_to(ROOT)}")


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
