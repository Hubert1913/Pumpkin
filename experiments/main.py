import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import skew, kurtosis


def analyze_nogood_events(file_path):
    # Metric names in order as specified
    metrics_names = [
        "size", "activity", "lbd", "num_variables",
        "decision_levels_span", "search_space_size"
    ]

    data = []
    bool_data = []

    print(f"Reading and parsing: {file_path}...")

    try:
        with open(file_path, 'r', encoding="utf-8-sig") as f:
            for line in f:
                parts = line.strip().split()
                # Only process lines starting with "NogoodProp"
                if not parts or parts[0] != "NogoodProp":
                    continue

                try:
                    # Format: NogoodProp ID V B V B V B V B V B V B
                    # V values are at indices: 2, 4, 6, 8, 10, 12
                    v_vals = [float(parts[i]) for i in range(2, 14, 2)]
                    # B values are at indices: 3, 5, 7, 9, 11, 13
                    b_vals = [parts[i].lower() == 'true' for i in range(3, 14, 2)]

                    data.append(v_vals)
                    bool_data.append(b_vals)
                except (ValueError, IndexError):
                    continue
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return

    if not data:
        print("No valid 'NogoodProp' lines found in the file.")
        return

    # Create DataFrames for analysis
    df_metrics = pd.DataFrame(data, columns=metrics_names)
    df_bools = pd.DataFrame(bool_data, columns=metrics_names)

    # --- 1. Metric Distribution Analysis (Log Scale) ---
    # plt.figure(figsize=(18, 10))
    # for i, col in enumerate(metrics_names, 1):
    #     plt.subplot(2, 3, i)
    #
    #     # We use log_scale=True. We handle 0 values by replacing them with
    #     # a very small epsilon to avoid math errors in log transform.
    #     clean_series = df_metrics[col].replace(0, 1e-9)
    #
    #     sns.histplot(clean_series, kde=True, color='skyblue', bins=30, log_scale=True)
    #     plt.title(f'Log-Scale Distribution: {col}')
    #     plt.xlabel(f'{col} (log scale)')
    #     plt.grid(True, which="both", ls="-", alpha=0.1)
    #
    # plt.tight_layout()
    # plt.savefig('metrics_distribution_log.png')
    # print("Graph saved: 'metrics_distribution_log.png'")

    # 1.5. Visualizing Distributions
    plt.figure(figsize=(15, 10))
    for i, col in enumerate(metrics_names, 1):
        plt.subplot(2, 3, i)
        sns.histplot(df_metrics[col], kde=True, color='skyblue', bins=50, kde_kws={'clip': (0, 1)})
        plt.xlim(0, 1) # force x-axis to exactly [0, 1]
        plt.title(f'Distribution of {col}')
        plt.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('metrics_distribution_2.png')
    # print("\nDistribution plots saved as 'metrics_distribution.png'.")

    # --- 2. Boolean Percentage Analysis ---
    plt.figure(figsize=(12, 6))
    bool_perc = df_bools.mean() * 100

    ax = sns.barplot(x=bool_perc.index, y=bool_perc.values, palette='viridis')
    plt.title('Percentage of propagations where nogood is from the \'better\' half of all nogoods')
    plt.ylabel('Frequency')
    plt.xlabel('Metric Name')
    plt.xticks(rotation=30)
    plt.ylim(0, 105)

    # Add percentage labels on top of the bars
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.1f}%',
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 9),
                    textcoords='offset points')

    plt.tight_layout()
    plt.savefig('boolean_percentages.png')
    print("Graph saved: 'boolean_percentages_2.png'")

    # --- 3. Statistical Analysis ---
    stats = df_metrics.describe().T
    stats['skewness'] = df_metrics.apply(skew)
    stats['kurtosis'] = df_metrics.apply(kurtosis)

    print("\n" + "=" * 50)
    print("KEY STATISTICAL INSIGHTS")
    print("=" * 50)

    # Sorting by Kurtosis to find the most 'peaky' distributions
    print("\nMetrics ranked by Peakiness (Kurtosis):")
    print(stats['kurtosis'].sort_values(ascending=False))

    print("\nMetrics ranked by skewness:")
    print(stats['skewness'].sort_values(ascending=False))

    print("\nBoolean 'True' Frequency per Metric:")
    for metric, perc in bool_perc.items():
        print(f"{metric:20}: {perc:.2f}%")

    print("\nSummary Statistics Table:")
    print(stats[['mean', 'std', 'min', '50%', 'max']])


# To run the script:
# analyze_nogood_events("your_data_file.txt")


if __name__ == "__main__":
    analyze_nogood_events("out2.txt")



