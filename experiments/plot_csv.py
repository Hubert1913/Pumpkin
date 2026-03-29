import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import glob
import matplotlib.ticker as mticker

parser = argparse.ArgumentParser()
parser.add_argument("input_dir", type=str, help="Path to directory containing input .csv files")
parser.add_argument("output_dir", type=str, help="Path to directory for output figures")
parser.add_argument("--print_latex", type=bool, default=False, help="If latex table of statistics should dbe printed")
args = parser.parse_args()

files = glob.glob(fr"{args.input_dir}\data_*.csv")

files_raw = glob.glob(fr"{args.input_dir}\raw_data_*.csv")

dfs = [pd.read_csv(f) for f in files]
dfs_raw = [pd.read_csv(f) for f in files_raw]

df_all = pd.concat(dfs)

df_combined = (
    df_all
    .groupby(["type", "metric", "bin", "bin_center"])["density"]
    .sum()
    .reset_index()
)

df_combined_raw = (
    pd.concat(dfs_raw)
    .groupby(["type", "metric", "value"])["density"]
    .sum()
    .reset_index()
)

df_combined["density"] /= len(files)
df_combined_raw["density"] /= len(files)

bin_width = 1 / 100

metrics_names = [
    "size", "activity", "lbd", "num_variables",
    "decision_levels_span", "search_space_size",
    "constraints_count", "constraints_count_recursive"
]

plot_types = ["unweighted", "conflict", "proof", "useful_proof"]

for metric in metrics_names:
    df_m = df_combined[df_combined.metric == metric]
    plt.figure(figsize=(20, 5))
    for i, plot_type in enumerate(plot_types, 1):
        plt.subplot(1, 4, i)
        df_t = df_m[df_m.type == plot_type]

        plt.bar(df_t.bin_center, df_t.density, width=bin_width, color="skyblue", edgecolor="black", linewidth=0.5)
        plt.title(plot_type)
        plt.xlim(0, 1)
        plt.grid(axis='y', alpha=0.3)
        plt.ylabel("Density")

    plt.suptitle(f"Distribution of {metric}", size=16)
    plt.tight_layout()
    plt.savefig(f'{args.output_dir}/hist_{metric}.png')

for metric in metrics_names:
    df_m = df_combined_raw[df_combined_raw.metric == metric]
    plt.figure(figsize=(20, 5))

    if metric == "search_space_size":
        for i, plot_type in enumerate(plot_types, 1):
            plt.subplot(1, 4, i)
            df_t = df_m[df_m.type == plot_type]

            log_values = np.log10(df_t['value'])
            plt.bar(log_values, df_t['density'], width=np.diff(log_values).mean(), color="skyblue", edgecolor="black", linewidth=0.5)
            plt.title(plot_type)

            ax = plt.gca()
            ticks = range(-30, 1, 5)
            ax.set_xticks(ticks)
            ax.set_xticklabels([f'$10^{{{t}}}$' for t in ticks])

            plt.grid(axis='y', alpha=0.3)
            plt.ylabel("Frequency")

        plt.suptitle(f"Distribution raw values of {metric}", size=16)
        plt.tight_layout()
        plt.savefig(f'{args.output_dir}/raw_hist_{metric}.png')
    elif metric == "activity":
        for i, plot_type in enumerate(plot_types, 1):
            plt.subplot(1, 4, i)
            df_t = df_m[df_m.type == plot_type]

            log_values = np.log10(df_t['value'])
            plt.bar(log_values, df_t['density'], width=np.diff(log_values).mean(), color="skyblue", edgecolor="black", linewidth=0.5)
            plt.ylabel('Frequency')

            ax = plt.gca()
            ticks = range(-35, 22, 8)
            ax.set_xticks(ticks)
            ax.set_xticklabels([f'$10^{{{t}}}$' for t in ticks])

            plt.title(plot_type)
            plt.grid(axis='y', alpha=0.3)
        plt.suptitle(f"Distribution raw values of {metric}", size=16)
        plt.tight_layout()
        plt.savefig(f'{args.output_dir}/raw_hist_{metric}.png')
    elif metric == "lbd" or metric == "decision_levels_span":
        for i, plot_type in enumerate(plot_types, 1):
            plt.subplot(1, 4, i)
            df_t = df_m[df_m.type == plot_type]

            plt.bar(df_t['value'], df_t['density'], width=0.8, color="skyblue", edgecolor="black", linewidth=0.5)
            plt.ylabel('Frequency')
            ax = plt.gca()
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))

            plt.title(plot_type)
            plt.grid(axis='y', alpha=0.3)
        plt.suptitle(f"Distribution raw values of {metric}", size=16)
        plt.tight_layout()
        plt.savefig(f'{args.output_dir}/raw_hist_{metric}.png')
    elif metric == "constraints_count" or metric == "constraints_count_recursive":
        for i, plot_type in enumerate(plot_types, 1):
            plt.subplot(1, 4, i)
            df_t = df_m[df_m.type == plot_type]

            plt.bar(df_t['value'], df_t['density'], width=1, color="skyblue", edgecolor="black", linewidth=0.5)
            plt.ylabel('Frequency')
            plt.xscale('symlog', linthresh=80)

            plt.title(plot_type)
            plt.grid(axis='y', alpha=0.3)
        plt.suptitle(f"Distribution raw values of {metric}", size=16)
        plt.tight_layout()
        plt.savefig(f'{args.output_dir}/raw_hist_{metric}.png')
    else:
        for i, plot_type in enumerate(plot_types, 1):
            plt.subplot(1, 4, i)
            df_t = df_m[df_m.type == plot_type]

            plt.bar(df_t['value'], df_t['density'], width=1, color="skyblue", edgecolor="black", linewidth=0.5)
            plt.ylabel('Frequency')
            plt.xscale('symlog', linthresh=30)

            plt.title(plot_type)
            plt.grid(axis='y', alpha=0.3)
        plt.suptitle(f"Distribution raw values of {metric}", size=16)
        plt.tight_layout()
        plt.savefig(f'{args.output_dir}/raw_hist_{metric}.png')


# --------- 2. COMPUTE STATS FROM HISTOGRAMS ----------


def stats_from_histogram(bin_centers: np.ndarray, density: np.ndarray) -> dict:
    """
    Compute mean, std, and skewness from a normalised histogram (density * bin_width ≈ 1).

    Uses the trapezoid rule so the result is exact for any bin spacing.
    """
    x = bin_centers
    p = density

    dx = bin_centers[1] - bin_centers[0]
    m1 = np.dot(x, p) * dx
    m2 = np.dot(x ** 2, p) * dx
    m3 = np.dot(x ** 3, p) * dx

    variance = m2 - m1 ** 2
    std = np.sqrt(np.maximum(variance, 0.0))  # guard against tiny negatives from rounding

    # Pearson's skewness  (E[X³] - 3·μ·σ² - μ³) / σ³
    if std > 0:
        skewness = (m3 - 3 * m1 * variance - m1 ** 3) / std ** 3
    else:
        skewness = np.nan

    return {"mean": m1, "std": std, "skewness": skewness}


def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply stats_from_histogram to every (type, metric) group.

    Parameters
    ----------
    df : DataFrame with columns [type, metric, bin, bin_center, density]

    Returns
    -------
    DataFrame with columns [type, metric, mean, std, skewness]
    """
    records = []
    for (t, m), group in df.groupby(["type", "metric"], sort=False):
        g = group.sort_values("bin")
        s = stats_from_histogram(g["bin_center"].to_numpy(), g["density"].to_numpy())
        records.append({"type": t, "metric": m, **s})

    return pd.DataFrame(records)


def to_latex(stats: pd.DataFrame, float_fmt: str = "{:.4f}") -> str:
    """
    Render a LaTeX booktabs table grouped by type.
    """
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Type & Metric & Mean & Std & Skewness \\",
        r"\midrule",
    ]

    for t in plot_types:
        group = stats[stats.type == t]
        first = True
        for m in metrics_names:
            row = group[group.metric == m].iloc[0]
            type_cell = t if first else ""
            first = False
            mean_s = float_fmt.format(row["mean"])
            std_s = float_fmt.format(row["std"])
            skew_s = float_fmt.format(row["skewness"])
            lines.append(f"{type_cell} & {row['metric']} & {mean_s} & {std_s} & {skew_s} \\\\")
        lines.append(r"\midrule")

    # Remove the last \midrule and replace with \bottomrule
    lines[-1] = r"\bottomrule"
    lines += [
        r"\end{tabular}",
        r"\caption{Summary statistics derived from histogram data.}",
        r"\label{tab:histogram_stats}",
        r"\end{table}",
    ]
    return "\n".join(lines)


stats = compute_stats(df_combined)

stats.to_csv(f'{args.output_dir}/stats.csv', index=False)
print(f"Stats saved to {args.output_dir}/stats.csv")
print(stats.to_string(index=False))

if args.print_latex:
    fmt = f"{{:.4f}}"
    print("\n--- LaTeX table ---\n")
    print(to_latex(stats, float_fmt=fmt))

# --------- 3. COMPUTE PERCENTAGE OF >= 0.5 ----------

ABOVE = {"activity", "search_space_size"}   # >= 0.5
BELOW = {"size", "lbd", "num_variables", "decision_levels_span", "constraints_count", "constraints_count_recursive"}  # <= 0.5


def pct_good_side(bin_centers: np.ndarray, density: np.ndarray, metric: str) -> float:
    """Integrate density over the 'good' side of 0.5 for the given metric."""
    dx = bin_centers[1] - bin_centers[0]
    if metric in ABOVE:
        mask = bin_centers >= 0.5
    else:
        mask = bin_centers <= 0.5
    return float(np.sum(density[mask]) * dx * 100)


def compute_pct(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (t, m), group in df.groupby(["type", "metric"], sort=False):
        g = group.sort_values("bin")
        pct = pct_good_side(g["bin_center"].to_numpy(), g["density"].to_numpy(), m)
        records.append({"type": t, "metric": m, "pct": pct})
    return pd.DataFrame(records)


def plot(df: pd.DataFrame, output_path: str) -> None:
    pct_df = compute_pct(df)

    types = plot_types
    metrics = metrics_names

    cmap = plt.get_cmap("tab10")
    colors = {m: cmap(i) for i, m in enumerate(metrics)}

    fig, axes = plt.subplots(1, len(types), figsize=(4 * len(types), 4.5),
                             sharey=True)
    if len(types) == 1:
        axes = [axes]

    x = np.arange(len(metrics))
    bar_width = 0.65

    for ax, t in zip(axes, types):
        subset = pct_df[pct_df["type"] == t].set_index("metric")
        heights = [subset.loc[m, "pct"] if m in subset.index else 0.0
                   for m in metrics]
        bars = ax.bar(x, heights, width=bar_width,
                      color=[colors[m] for m in metrics],
                      edgecolor="white", linewidth=0.6)

        for bar, h in zip(bars, heights):
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.8,
                    f"{h:.1f}%", ha="center", va="bottom",
                    fontsize=8, color="0.25")

        ax.set_title(t, fontsize=11, fontweight="bold", pad=8)
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, rotation=30, ha="right", fontsize=9)
        ax.set_xlim(-0.5, len(metrics) - 0.5)
        ax.set_ylim(0, 110)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%g%%"))
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5)

    axes[0].set_ylabel("% of propagations", fontsize=10)

    # Legend: metric name + direction hint
    # def legend_label(m):
    #     return f"{m}  (≥0.5)" if m in ABOVE else f"{m}  (≤0.5)"
    #
    # handles = [plt.Rectangle((0, 0), 1, 1, color=colors[m]) for m in metrics]
    # labels = [legend_label(m) for m in metrics]
    # fig.legend(handles, labels, title="Metric", loc="lower center",
    #            ncol=len(metrics), bbox_to_anchor=(0.5, -0.06),
    #            fontsize=9, title_fontsize=9, frameon=False)

    fig.suptitle("Percentage of propagations made by nogoods from the 'better' half, according to given metric",
                 fontsize=13, fontweight="bold", y=1.02)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved to {output_path}")


plot(df_combined, output_path=f"{args.output_dir}/percentages.png")
