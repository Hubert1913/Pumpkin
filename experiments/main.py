import pandas as pd
import numpy as np
from collections import defaultdict
import re
import argparse
from file_read_backwards import FileReadBackwards
import itertools


# def find_nogood_ids_from_processed_proof(processed_proof_path):
#     nogood_ids = set()
#     pattern = re.compile(r"n\s(\d+)\s")
#
#     print(f"Reading nogood IDs from processed proof from: {processed_proof_path}")
#
#     try:
#         with open(processed_proof_path, "r", encoding="utf-8", errors="ignore") as f:
#             for line in f:
#                 if line[0] != 'n':
#                     continue
#                 match = pattern.search(line)
#                 nogood_ids.add(int(match.group(1)))
#     except FileNotFoundError:
#         print(f"Warning: {processed_proof_path} not found.")
#
#     print(f"Found {len(nogood_ids)} nogood IDs in the processed proof file")
#     return nogood_ids


def parse_full_proof_file(full_proof_path: str) -> (dict, dict):
    print("Starting to read the full proof file backwards")
    used_nogoods_ids = set()

    used_proof_steps = set()
    seen_last_nogood = False
    inference_c_pattern = re.compile(r" c:(\d+) ")
    skip_count = 0
    with FileReadBackwards(full_proof_path) as frb:
        for line in frb:
            line = line.strip()

            if line[0] == 'n':
                parts = line.split()
                proof_step_id = int(parts[1])
                if seen_last_nogood and proof_step_id not in used_proof_steps:
                    skip_count += 1
                    continue

                if proof_step_id % 10 == 0:
                    used_proof_steps = set(filter(lambda x: x <= proof_step_id, used_proof_steps))

                if not seen_last_nogood:
                    seen_last_nogood = True

                used_nogoods_ids.add(int(parts[1]))
                seen_zero = False
                for p in parts:
                    if p == '0':
                        seen_zero = True
                    elif seen_zero:
                        used_proof_steps.add(int(p))
            if line[0] == 'i':
                parts = line.split()
                if int(parts[1]) not in used_proof_steps:
                    continue
                match = inference_c_pattern.search(line)
                if match:
                    step_id = int(match.group(1))
                    used_proof_steps.add(step_id)

    print(f"With self-trimming we found {len(used_nogoods_ids)} used_nogoods_ids")
    print(f"We skipped {skip_count} nogoods")

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


def analyze_nogood_events(instance_name: str, input_dir_path: str, output_dir_path: str):
    file_path = f"{input_dir_path}/{instance_name}_stats.txt"
    full_proof_path = f"{input_dir_path}/{instance_name}_proof_full.drcp"
    # processed_proof_path = f"experiments/outputs/{instance_name}_proof_full_processed.drcp"

    csv_data_path = f"{output_dir_path}/data_{instance_name}.csv"
    csv_raw_data_path = f"{output_dir_path}/raw_data_{instance_name}.csv"
    correlation_csv_path = f"{output_dir_path}/corr_{instance_name}.csv"

    # used_nogood_ids = find_nogood_ids_from_processed_proof(processed_proof_path)
    used_count_in_proof, nogood_inferences_in_proof = parse_full_proof_file(full_proof_path)
    # used_count_in_proof, nogood_inferences_in_proof = parse_full_proof_file(full_proof_path, used_nogood_ids)

    # Metric names in order as specified
    metrics_names = [
        "size", "activity", "lbd", "num_variables",
        "decision_levels_span", "search_space_size",
        "constraints_count"
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
                        # Format: NogoodProp ID_1 ID_2 V B V B V B V B V B V B V B
                        prop_id = int(parts[1])
                        nogood_id = int(parts[2])
                        v_vals = [float(parts[i]) for i in range(3, 17, 2)]
                        abs_vals = [float(parts[i]) for i in range(4, 17, 2)]

                        nogood_data[prop_id] = v_vals
                        nogood_abs[prop_id] = abs_vals

                        all_prop_ids.add(prop_id)
                        prop_id_to_nogood_id_map[prop_id] = nogood_id
                    except (ValueError, IndexError):
                        continue
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return

    print("Finished reading. Processing and saving to csv...")

    rows_for_csv = []
    bins = np.linspace(0, 1, 101)
    bin_centers = (bins[:-1] + bins[1:]) / 2

    bins_log = np.logspace(-35, 20, 101)
    bin_centers_log = np.sqrt(bins_log[:-1] * bins_log[1:])

    bins_log_search_space_size = np.logspace(-30, 0, 101)
    bin_centers_log_search_space_size = np.sqrt(bins_log_search_space_size[:-1] * bins_log_search_space_size[1:])

    raw_rows_for_csv = []

    average_inferences_from_nogood_in_proof = sum(nogood_inferences_in_proof.values()) / len(nogood_inferences_in_proof)

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
    for col in metrics_names:
        density, _ = np.histogram(
            df_metrics[col],
            bins=bins,
            density=True
        )

        for i, d in enumerate(density):
            rows_for_csv.append({
                "type": "unweighted",
                "metric": col,
                "bin": i,
                "bin_center": bin_centers[i],
                "density": d
            })

    for col in metrics_names:
        total_weight = df_abs[col].size
        if col == "search_space_size":
            clipped = df_abs[col].clip(lower=bins_log_search_space_size[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log_search_space_size,
                density=False
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "unweighted",
                    "metric": col,
                    "value": bin_centers_log_search_space_size[i],
                    "density": d / total_weight
                })
        elif col == "activity":
            clipped = df_abs[col].clip(lower=bins_log[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log,
                density=False
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "unweighted",
                    "metric": col,
                    "value": bin_centers_log[i],
                    "density": d / total_weight
                })
        else:
            counts = df_abs[col].value_counts()
            for value, count in counts.items():
                raw_rows_for_csv.append({
                    "type": "unweighted",
                    "metric": col,
                    "value": value,
                    "density": count / total_weight
                })

    # --- 2. Plots for weighted according to conflict analysis usage ---
    for col in metrics_names:
        density, _ = np.histogram(
            df_metrics[col],
            bins=bins,
            density=True,
            weights=df_metrics["conflict_weights"]
        )

        for i, d in enumerate(density):
            rows_for_csv.append({
                "type": "conflict",
                "metric": col,
                "bin": i,
                "bin_center": bin_centers[i],
                "density": d
            })

    for col in metrics_names:
        total_weight = df_abs["conflict_weights"].sum()
        if col == "search_space_size":
            clipped = df_abs[col].clip(lower=bins_log_search_space_size[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log_search_space_size,
                density=False,
                weights=df_abs["conflict_weights"]
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "conflict",
                    "metric": col,
                    "value": bin_centers_log_search_space_size[i],
                    "density": d / total_weight
                })
        elif col == "activity":
            clipped = df_abs[col].clip(lower=bins_log[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log,
                density=False,
                weights=df_abs["conflict_weights"]
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "conflict",
                    "metric": col,
                    "value": bin_centers_log[i],
                    "density": d / total_weight
                })
        else:
            weighted_counts = df_abs.groupby(col)["conflict_weights"].sum()
            for value, weight_sum in weighted_counts.items():
                raw_rows_for_csv.append({
                    "type": "conflict",
                    "metric": col,
                    "value": value,
                    "density": weight_sum / total_weight
                })

    # --- 3. Plots for weighted according to proof usage ---
    for col in metrics_names:
        density, _ = np.histogram(
            df_metrics[col],
            bins=bins,
            density=True,
            weights=df_metrics["proof_weights"]
        )

        for i, d in enumerate(density):
            rows_for_csv.append({
                "type": "proof",
                "metric": col,
                "bin": i,
                "bin_center": bin_centers[i],
                "density": d
            })

    for col in metrics_names:
        total_weight = df_abs["proof_weights"].sum()
        if col == "search_space_size":
            clipped = df_abs[col].clip(lower=bins_log_search_space_size[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log_search_space_size,
                density=False,
                weights=df_abs["proof_weights"]
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "proof",
                    "metric": col,
                    "value": bin_centers_log_search_space_size[i],
                    "density": d / total_weight
                })
        elif col == "activity":
            clipped = df_abs[col].clip(lower=bins_log[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log,
                density=False,
                weights=df_abs["proof_weights"]
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "proof",
                    "metric": col,
                    "value": bin_centers_log[i],
                    "density": d / total_weight
                })
        else:
            weighted_counts = df_abs.groupby(col)["proof_weights"].sum()
            for value, weight_sum in weighted_counts.items():
                raw_rows_for_csv.append({
                    "type": "proof",
                    "metric": col,
                    "value": value,
                    "density": weight_sum / total_weight
                })

    for col in metrics_names:
        density, _ = np.histogram(
            df_metrics[col],
            bins=bins,
            density=True,
            weights=df_metrics["useful_proof_weights"]
        )

        for i, d in enumerate(density):
            rows_for_csv.append({
                "type": "useful_proof",
                "metric": col,
                "bin": i,
                "bin_center": bin_centers[i],
                "density": d
            })

    for col in metrics_names:
        total_weight = df_abs["useful_proof_weights"].sum()
        if col == "search_space_size":
            clipped = df_abs[col].clip(lower=bins_log_search_space_size[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log_search_space_size,
                density=False,
                weights=df_abs["useful_proof_weights"]
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "useful_proof",
                    "metric": col,
                    "value": bin_centers_log_search_space_size[i],
                    "density": d / total_weight
                })
        elif col == "activity":
            clipped = df_abs[col].clip(lower=bins_log[0])
            density, _ = np.histogram(
                clipped,
                bins=bins_log,
                density=False,
                weights=df_abs["useful_proof_weights"]
            )

            for i, d in enumerate(density):
                raw_rows_for_csv.append({
                    "type": "useful_proof",
                    "metric": col,
                    "value": bin_centers_log[i],
                    "density": d / total_weight
                })
        else:
            weighted_counts = df_abs.groupby(col)["useful_proof_weights"].sum()
            for value, weight_sum in weighted_counts.items():
                raw_rows_for_csv.append({
                    "type": "useful_proof",
                    "metric": col,
                    "value": value,
                    "density": weight_sum / total_weight
                })

    df_csv = pd.DataFrame(rows_for_csv)
    df_csv.to_csv(csv_data_path, index=False)

    df_csv_raw = pd.DataFrame(raw_rows_for_csv)
    df_csv_raw.to_csv(csv_raw_data_path, index=False)

    # --- 0. Boolean Percentage Analysis ---
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

    # --- 4. Correlation calculation ---
    print("Calculating correlations...")
    # All 6 value columns
    VALUE_COLS = metrics_names

    # The 2 columns to transform with  1 - x  before correlating
    INVERT_COLS = ["activity", "search_space_size"]

    # The 3 weight columns
    WEIGHT_COLS = ["conflict_weights", "proof_weights", "useful_proof_weights"]

    # Apply 1-x transform
    df = df_metrics.copy()
    for col in INVERT_COLS:
        df[col] = 1 - df[col]

    corr_csv_rows = []
    pairs = list(itertools.combinations(VALUE_COLS, 2))

    for col_a, col_b in pairs:
        x = df[col_a].values.astype(float)
        y = df[col_b].values.astype(float)

        # Unweighted correlation
        mask = ~(np.isnan(x) | np.isnan(y))
        r_unweighted = np.corrcoef(x[mask], y[mask])[0, 1]
        corr_csv_rows.append({"col_a": col_a, "col_b": col_b,
                     "weight": "unweighted", "correlation": r_unweighted})

        # Weighted correlations
        for wcol in WEIGHT_COLS:
            w = df[wcol].values.astype(float)
            valid = ~(np.isnan(x) | np.isnan(y) | np.isnan(w)) & (w > 0)
            r_w = weighted_corr(x[valid], y[valid], w[valid])
            corr_csv_rows.append({"col_a": col_a, "col_b": col_b,
                         "weight": wcol, "correlation": r_w})

    corr_result_df = pd.DataFrame(corr_csv_rows)
    corr_result_df.to_csv(correlation_csv_path, index=False)


def weighted_corr(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    """Weighted Pearson correlation between x and y using weights w."""
    w = w / w.sum()                          # normalise weights to sum to 1
    mx = np.sum(w * x)
    my = np.sum(w * y)
    cov  = np.sum(w * (x - mx) * (y - my))
    stdx = np.sqrt(np.sum(w * (x - mx) ** 2))
    stdy = np.sqrt(np.sum(w * (y - my) ** 2))
    if stdx == 0 or stdy == 0:
        return np.nan
    return cov / (stdx * stdy)


parser = argparse.ArgumentParser()
parser.add_argument("instance_name", type=str, help="Name of the instance to analyze")
parser.add_argument("input_dir_path", type=str, help="Path to directory containing input .drc and .txt files")
parser.add_argument("output_dir_path", type=str, help="Path to directory where the resulting.csv files should be stored")
args = parser.parse_args()
analyze_nogood_events(args.instance_name, args.input_dir_path, args.output_dir_path)
