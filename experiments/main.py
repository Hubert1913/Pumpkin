import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
# from scipy.stats import skew, kurtosis
from collections import defaultdict
import re


def find_nogood_ids_from_processed_proof(processed_proof_path):
    nogood_ids = set()
    pattern = re.compile(r"n\s(\d+)\s")

    print(f"Reading nogood IDs from processed proof from: {processed_proof_path}")

    try:
        with open(processed_proof_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line[0] != 'n':
                    continue
                match = pattern.search(line)
                nogood_ids.add(int(match.group(1)))
    except FileNotFoundError:
        print(f"Warning: {processed_proof_path} not found.")

    print(f"Found {len(nogood_ids)} nogood IDs in the processed proof file")
    return nogood_ids


def parse_full_proof_file(full_proof_path: str, used_nogoods_ids: set) -> (dict, dict):
    pattern_inferences = re.compile(r"^i\s(\d+)\s.*?nogood(\d+)-(\d+)$")

    inference_id_map = {}
    prop_id_to_my_nogood_id_map = {}
    used_count_in_proof = defaultdict(int)
    nogood_inferences_in_proof = defaultdict(int)

    print(f"Processing the full proof file at {full_proof_path}")

    try:
        with open(full_proof_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line[0] == 'n':
                    parts = line.split()
                    nogood_id = int(parts[1])
                    if nogood_id not in used_nogoods_ids:
                        continue
                    idx = parts.index('0')
                    used_inference_ids = list(map(int, parts[idx + 1:]))
                    for inf_id in used_inference_ids:
                        if inf_id in inference_id_map:
                            prop_id = inference_id_map[inf_id]
                            used_count_in_proof[prop_id] += 1
                            nogood_inferences_in_proof[prop_id_to_my_nogood_id_map[prop_id]] += 1
                elif line[0] == 'i':
                    match = pattern_inferences.search(line)
                    if match:
                        inference_proof_id = int(match.group(1))
                        my_nogood_id = int(match.group(2))
                        my_propagation_id = int(match.group(3))
                        inference_id_map[inference_proof_id] = my_propagation_id
                        prop_id_to_my_nogood_id_map[my_propagation_id] = my_nogood_id
                        # nogood_inferences_in_proof[my_nogood_id] += 1

    except FileNotFoundError:
        print(f"Warning: {full_proof_path} not found.")

    print(f"Found {len(inference_id_map)} relevant inference IDs in the full proof file")
    return used_count_in_proof, nogood_inferences_in_proof


def analyze_nogood_events(file_path, full_proof_path, processed_proof_path, ver_num):
    used_nogood_ids = find_nogood_ids_from_processed_proof(processed_proof_path)
    used_count_in_proof, nogood_inferences_in_proof = parse_full_proof_file(full_proof_path, used_nogood_ids)

    # Metric names in order as specified
    metrics_names = [
        "size", "activity", "lbd", "num_variables",
        "decision_levels_span", "search_space_size"
    ]

    data = []
    abs_data = []
    conflict_weights = []
    proof_weights = []
    useful_proof_weights = []

    nogood_data = {}
    nogood_abs = {}

    all_prop_ids = set()

    prop_in_confl_count = defaultdict(int)
    prop_id_to_nogood_id_map = {}

    print(f"Reading and parsing: {file_path}...")

    try:
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split()

                if not parts:
                    continue

                if parts[0] == "PropInConfl":
                    try:
                        prop_id = int(parts[1])
                        prop_in_confl_count[prop_id] += 1
                    except (ValueError, IndexError):
                        continue

                elif parts[0] == "NogoodProp":
                    try:
                        # Format: NogoodProp ID_1 ID_2 V B V B V B V B V B V B
                        prop_id = int(parts[1])
                        nogood_id = int(parts[2])
                        v_vals = [float(parts[i]) for i in range(3, 15, 2)]
                        abs_vals = [float(parts[i]) for i in range(4, 15, 2)]

                        nogood_data[prop_id] = v_vals
                        nogood_abs[prop_id] = abs_vals

                        all_prop_ids.add(prop_id)
                        prop_id_to_nogood_id_map[prop_id] = nogood_id
                    except (ValueError, IndexError):
                        continue
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return

    print("Finished reading. Processing and plotting...")

    average_times_used_in_proof = sum(used_count_in_proof.values()) / len(used_count_in_proof)
    average_inferences_from_nogood_in_proof = sum(nogood_inferences_in_proof.values()) / len(nogood_inferences_in_proof)

    print(f"Inferences in proof were used on average {average_times_used_in_proof} times")
    print(f"Each nogood produced on average {average_inferences_from_nogood_in_proof} inferences in proof")

    for prop_id in all_prop_ids:
        data.append(nogood_data[prop_id])
        abs_data.append(nogood_abs[prop_id])
        conflict_weights.append(prop_in_confl_count.get(prop_id, 0))
        proof_weight = used_count_in_proof.get(prop_id, 0)
        proof_weights.append(proof_weight)
        useful_proof_weights.append(
            proof_weight
            if nogood_inferences_in_proof[prop_id_to_nogood_id_map[prop_id]] > average_inferences_from_nogood_in_proof
            else 0
        )

    # for prop_id, count in prop_in_confl_count.items():
    #     if prop_id in nogood_data:
    #         data.append(nogood_data[prop_id])
    #         abs_data.append(nogood_abs[prop_id])
    #         weights.append(count)
    #         proof_weights.append(used_count_in_proof.get(prop_id, 0))
    #         # useful_flags.append(prop_id in useful_prop_ids)

    # Create DataFrames for analysis
    df_metrics = pd.DataFrame(data, columns=metrics_names)
    df_abs = pd.DataFrame(abs_data, columns=metrics_names)

    df_metrics["conflict_weights"] = conflict_weights
    df_abs["conflict_weights"] = conflict_weights

    df_metrics["proof_weights"] = proof_weights
    df_abs["proof_weights"] = proof_weights

    df_metrics["useful_proof_weights"] = useful_proof_weights
    df_abs["useful_proof_weights"] = useful_proof_weights

    # --- 1. Plots for unweighted data ---
    plt.figure(figsize=(15, 10))
    for i, col in enumerate(metrics_names, 1):
        plt.subplot(2, 3, i)
        sns.histplot(
            df_metrics,
            x=col,
            # weights=df_metrics["weight"],
            bins=50,
            color="skyblue",
            stat="density",
            alpha=0.5,
            # label="all",
        )
        plt.xlim(0, 1)  # force x-axis to exactly [0, 1]
        plt.title(f'{col}')
        plt.grid(axis='y', alpha=0.3)

    plt.suptitle("Distribution of metrics, unweighted", size=16)
    plt.tight_layout()
    plt.savefig(f'unweighted_{ver_num}.png')

    plt.figure(figsize=(15, 10))
    for i, col in enumerate(metrics_names, 1):
        plt.subplot(2, 3, i)
        sns.histplot(
            df_abs,
            x=col,
            # weights=df_metrics["weight"],
            bins=50,
            color="skyblue",
            stat="density",
            alpha=0.5,
            # label="all",
        )
        plt.title(f'{col}')
        plt.grid(axis='y', alpha=0.3)

    plt.suptitle("Distribution of raw values, unweighted", size=16)
    plt.tight_layout()
    plt.savefig(f'unweighted_raw_{ver_num}.png')

    # --- 2. Plots for weighted according to conflict analysis usage ---
    plt.figure(figsize=(15, 10))
    for i, col in enumerate(metrics_names, 1):
        plt.subplot(2, 3, i)
        sns.histplot(
            df_metrics,
            x=col,
            weights=df_metrics["conflict_weights"],
            bins=50,
            color="skyblue",
            stat="density",
            alpha=0.5,
            # label="all",
        )
        plt.xlim(0, 1)  # force x-axis to exactly [0, 1]
        plt.title(f'{col}')
        plt.grid(axis='y', alpha=0.3)

    plt.suptitle("Distribution of metrics, weighted on usage in conflict analysis", size=16)
    plt.tight_layout()
    plt.savefig(f'confl_{ver_num}.png')

    plt.figure(figsize=(15, 10))
    for i, col in enumerate(metrics_names, 1):
        plt.subplot(2, 3, i)
        sns.histplot(
            df_abs,
            x=col,
            weights=df_abs["conflict_weights"],
            bins=50,
            color="skyblue",
            stat="density",
            alpha=0.5,
            # label="all",
        )
        plt.title(f'{col}')
        plt.grid(axis='y', alpha=0.3)

    plt.suptitle("Distribution of raw values, weighted on usage in conflict analysis", size=16)
    plt.tight_layout()
    plt.savefig(f'confl_raw_{ver_num}.png')

    # --- 3. Plots for weighted according to proof usage ---
    plt.figure(figsize=(15, 10))
    for i, col in enumerate(metrics_names, 1):
        plt.subplot(2, 3, i)
        sns.histplot(
            df_metrics,
            x=col,
            weights=df_metrics["proof_weights"],
            bins=50,
            color="skyblue",
            stat="density",
            alpha=0.9,
            label="all",
        )
        # Useful propagations
        sns.histplot(
            df_metrics,
            x=col,
            weights=df_metrics["useful_proof_weights"],
            bins=50,
            color="red",
            stat="density",
            alpha=0.4,
            label="above average",
        )
        plt.xlim(0, 1)  # force x-axis to exactly [0, 1]
        plt.title(f'{col}')
        plt.grid(axis='y', alpha=0.3)

        if i == 1:
            plt.legend()

    plt.suptitle("Distribution of metrics, weighted on usage in proof", size=16)
    plt.tight_layout()
    plt.savefig(f'proof_{ver_num}.png')
    # print("\nDistribution plots saved as 'metrics_distribution.png'.")

    plt.figure(figsize=(15, 10))
    for i, col in enumerate(metrics_names, 1):
        plt.subplot(2, 3, i)
        sns.histplot(
            df_abs,
            x=col,
            weights=df_abs["proof_weights"],
            bins=50,
            color="skyblue",
            stat="density",
            alpha=0.9,
            label="all"
        )
        sns.histplot(
            df_abs,
            x=col,
            weights=df_abs["useful_proof_weights"],
            bins=50,
            color="red",
            stat="density",
            alpha=0.4,
            label="above average"
        )
        plt.title(f'{col}')
        plt.grid(axis='y', alpha=0.3)

        if i == 1:
            plt.legend()

    plt.suptitle("Distribution of raw values, weighted on usage in proof", size=16)
    plt.tight_layout()
    plt.savefig(f'proof_raw_{ver_num}.png')

    # --- 2. Boolean Percentage Analysis ---
    # plt.figure(figsize=(12, 6))
    # bool_perc = df_bools.mean() * 100
    #
    # ax = sns.barplot(x=bool_perc.index, y=bool_perc.values, palette='viridis')
    # plt.title('Percentage of propagations where nogood is from the \'better\' half of all nogoods')
    # plt.ylabel('Frequency')
    # plt.xlabel('Metric Name')
    # plt.xticks(rotation=30)
    # plt.ylim(0, 105)
    #
    # # Add percentage labels on top of the bars
    # for p in ax.patches:
    #     ax.annotate(f'{p.get_height():.1f}%',
    #                 (p.get_x() + p.get_width() / 2., p.get_height()),
    #                 ha='center', va='center', xytext=(0, 9),
    #                 textcoords='offset points')
    #
    # plt.tight_layout()
    # plt.savefig('boolean_percentages_3.png')
    # print("Graph saved: 'boolean_percentages_2.png'")

    # --- 3. Statistical Analysis ---
    # stats = df_metrics.describe().T
    # stats['skewness'] = df_metrics.apply(skew)
    # stats['kurtosis'] = df_metrics.apply(kurtosis)
    #
    # print("\n" + "=" * 50)
    # print("KEY STATISTICAL INSIGHTS")
    # print("=" * 50)
    #
    # # Sorting by Kurtosis to find the most 'peaky' distributions
    # print("\nMetrics ranked by Peakiness (Kurtosis):")
    # print(stats['kurtosis'].sort_values(ascending=False))
    #
    # print("\nMetrics ranked by skewness:")
    # print(stats['skewness'].sort_values(ascending=False))
    #
    # # print("\nBoolean 'True' Frequency per Metric:")
    # # for metric, perc in bool_perc.items():
    # #     print(f"{metric:20}: {perc:.2f}%")
    #
    # print("\nSummary Statistics Table:")
    # print(stats[['mean', 'std', 'min', '50%', 'max']])


# To run the script:
# analyze_nogood_events("your_data_file.txt")


if __name__ == "__main__":
    analyze_nogood_events("out7_proof.txt", "proof7_full.drcp", "proof7_full_proc.drcp", 1)



