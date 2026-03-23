"""
plot_correlations.py
--------------------
Combines multiple long-format correlation CSVs (produced by main.py),
takes the mean correlation per (col_a, col_b, weight) group, and produces
4 heatmap plots — one per weight type (unweighted + 3 weight columns).

Usage:
    python plot_correlations.py --inputs corr1.csv corr2.csv corr3.csv --output_dir ./plots
    python plot_correlations.py --inputs_glob "./results/corr_*.csv" --output_dir ./plots
"""

import glob
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm


# ── Configuration ─────────────────────────────────────────────────────────────

# Must match the column names used in compute_correlations.py
VALUE_COLS = [
    "size", "activity", "lbd", "num_variables",
    "decision_levels_span", "search_space_size"
]
WEIGHT_COLS = ["unweighted", "conflict_weights", "proof_weights", "useful_proof_weights"]   # must match the 'weight' values in your CSVs

PLOT_TITLES  = {
    "unweighted": "Unweighted",
    "conflict_weights": "Weighted by usage in conflict analysis",
    "proof_weights": "Weighted by usage in trimmed proof",
    "useful_proof_weights": "Weighted by usage in proof, from useful nogoods",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_and_combine(paths: list[str]) -> pd.DataFrame:
    dfs = [pd.read_csv(p) for p in paths]
    combined = pd.concat(dfs, ignore_index=True)
    return combined


def mean_corr_matrix(df: pd.DataFrame, weight: str) -> pd.DataFrame:
    """Return a symmetric n×n mean correlation matrix for one weight type."""
    sub = df[df["weight"] == weight].groupby(["col_a", "col_b"])["correlation"].mean().reset_index()

    # Build full symmetric matrix
    mat = pd.DataFrame(np.nan, index=VALUE_COLS, columns=VALUE_COLS)
    mat_arr = mat.to_numpy(copy=True)
    np.fill_diagonal(mat_arr, 1.0)
    mat = pd.DataFrame(mat_arr, index=VALUE_COLS, columns=VALUE_COLS)

    for _, row in sub.iterrows():
        a, b, r = row["col_a"], row["col_b"], row["correlation"]
        if a in mat.index and b in mat.columns:
            mat.loc[a, b] = r
            mat.loc[b, a] = r

    return mat


def plot_heatmap(ax: plt.Axes, matrix: pd.DataFrame, title: str) -> None:
    n = len(matrix)
    data = matrix.values.astype(float)

    # Diverging colormap centred at 0
    vmin, vmax = -1, 1
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    im = ax.imshow(data, cmap="RdBu_r", norm=norm, aspect="equal")

    # Colorbar
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson r", fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    # Axis labels
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(matrix.index, fontsize=9)

    # Annotate cells
    for i in range(n):
        for j in range(n):
            val = data[i, j]
            if not np.isnan(val):
                text_color = "white" if abs(val) > 0.6 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=8, color=text_color)

    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    paths = glob.glob(r"./out_data/corr_*.csv")
    out_dir = "./figures/"
    out_path = out_dir + "correlation_heatmaps.png"

    print(f"Loading {len(paths)} file(s)...")

    os.makedirs(out_dir, exist_ok=True)

    combined = load_and_combine(paths)
    # print(combined)

    # One figure with 4 subplots (2×2)
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle(f"Correlations between metrics",
                 fontsize=14, fontweight="bold", y=1.01)

    for ax, weight in zip(axes.flat, WEIGHT_COLS):
        mat = mean_corr_matrix(combined, weight)
        plot_heatmap(ax, mat, PLOT_TITLES[weight])

    plt.tight_layout()

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved plot → {out_path}")
    # plt.show()


if __name__ == "__main__":
    main()
