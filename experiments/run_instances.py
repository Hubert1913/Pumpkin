import argparse
import os
import subprocess
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SOLVER_EXE = r".\target\release\pumpkin-solver.exe"
# PROCESSOR_EXE = r".\target\release\pumpkin-proof-processor.exe"
MAIN_SCRIPT = r".\experiments\main.py"
TIMEOUT_MS = 5400000
MAX_WORKERS = 5

SEPARATOR = "=" * 10
SAT_SEPARATOR = "-" * 10
UNSAT_MARKER = "UNSATISFIABLE"

print_lock = threading.Lock()
skipped_count = 0
skipped_lock = threading.Lock()


def log(instance: str, message: str) -> None:
    with print_lock:
        print(f"[{instance}] {message}")


def run_instance(fzn_path: Path, output_dir: str, out_csv_dir: str, sat: bool) -> None:
    instance = fzn_path.stem

    proof_full = rf"{output_dir}\{instance}_proof_full.drcp"
    # proof_processed = rf"{output_dir}\{instance}_proof_full_processed.drcp"
    stats_path = rf"{output_dir}\{instance}_stats.txt"
    stdout_log = rf"{output_dir}\{instance}_sdout.log"

    # --- Step 1: Run the solver ---
    solver_cmd = [
        SOLVER_EXE,
        "-s", str(fzn_path),
        "-t", str(TIMEOUT_MS),
        "--proof-path", proof_full,
        "--proof-type", "full",
        "--stats-path", stats_path,
    ]

    log(instance, f"Starting solver: {' '.join(solver_cmd)}")

    try:
        result = subprocess.run(
            solver_cmd,
            capture_output=True,
            text=True,
        )
        stdout_output = result.stdout

        with open(stdout_log, "w", encoding="utf-8") as f:
            f.write(stdout_output)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)

        log(instance, f"Solver finished (exit code {result.returncode}). Output saved to {stdout_log}")

    except FileNotFoundError:
        log(instance, f"ERROR: Solver executable not found at '{SOLVER_EXE}'")
        return
    except Exception as e:
        log(instance, f"ERROR during solver execution: {e}")
        return

    # --- Step 2: Check output for separator sequences ---
    should_process = SEPARATOR in stdout_output  # or DASH_SEPARATOR in stdout_output
    if sat:
        if SAT_SEPARATOR in stdout_output:
            sat_type = "sat"
            should_process = True
        elif UNSAT_MARKER in stdout_output:
            sat_type = "unsat"
            should_process = True

    if not should_process:
        log(instance, "No separator found in solver output. Skipping the instance.")
        return

    # --- Step 2b: Parse solveTime and skip if below threshold ---
    solve_time = None
    for line in stdout_output.splitlines():
        line = line.strip()
        if line.startswith("%%%mzn-stat: solveTime="):
            try:
                solve_time = float(line.split("=", 1)[1])
            except ValueError:
                log(instance, f"WARNING: Could not parse solveTime from line: {line!r}")

    if solve_time is None:
        log(instance, "WARNING: No solveTime stat found in solver output. Skipping proof processing.")
        return

    log(instance, f"solveTime = {solve_time}")

    if solve_time < 20.0:
        log(instance, f"solveTime {solve_time} is below 20. Skipping proof processing.")
        global skipped_count
        with skipped_lock:
            skipped_count += 1
        return

    # log(instance, "Separator found in solver output. Running proof processor...")
    #
    # # --- Step 3: Run proof processor ---
    # processor_cmd = [
    #     PROCESSOR_EXE,
    #     str(fzn_path),
    #     proof_full,
    #     proof_processed,
    # ]
    #
    # log(instance, f"Running proof processor: {' '.join(processor_cmd)}")
    #
    # try:
    #     proc_result = subprocess.run(
    #         processor_cmd,
    #         capture_output=True,
    #         text=True,
    #     )
    #     log(instance, f"Proof processor finished (exit code {proc_result.returncode})")
    #     if proc_result.stderr:
    #         log(instance, f"Processor stderr: {proc_result.stderr.strip()}")
    #
    # except FileNotFoundError:
    #     log(instance, f"ERROR: Proof processor executable not found at '{PROCESSOR_EXE}'")
    #     return
    # except Exception as e:
    #     log(instance, f"ERROR during proof processing: {e}")
    #     return

    # --- Step 4: Run main.py ---
    if not sat:
        main_cmd = ["python", MAIN_SCRIPT, instance, output_dir, out_csv_dir]
    else:
        out_csv_dir_sat = out_csv_dir + sat_type + out_csv_dir[-1]
        os.makedirs(out_csv_dir_sat, exist_ok=True)

        main_cmd = ["python", MAIN_SCRIPT, instance, output_dir, out_csv_dir_sat, "--sat", "true"]

    log(instance, f"Running main.py: {' '.join(main_cmd)}")

    try:
        main_result = subprocess.run(
            main_cmd,
            capture_output=True,
            text=True,
        )
        log(instance, f"main.py finished (exit code {main_result.returncode})")
        if main_result.stdout:
            log(instance, f"main.py stdout: {main_result.stdout.strip()}")
        if main_result.stderr:
            log(instance, f"main.py stderr: {main_result.stderr.strip()}")

    except Exception as e:
        log(instance, f"ERROR running main.py: {e}")
        return

    log(instance, "All steps completed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("flatzinc_dir", type=str, help="Path to directory containing input .fzn files")
    parser.add_argument("output_dir", type=str, help="Path to directory for solver output files")
    parser.add_argument("out_csv_dir", type=str, help="Path to directory for output .csv files")
    parser.add_argument("--sat", type=bool, default=False, help="If we are looking for SAT separators in stdout")
    args = parser.parse_args()

    flatzinc_path = Path(args.flatzinc_dir)

    if not flatzinc_path.exists():
        print(f"ERROR: FlatZinc directory not found: {flatzinc_path.resolve()}")
        return

    fzn_files = sorted(flatzinc_path.glob("*.fzn"))

    if not fzn_files:
        print(f"No .fzn files found in {flatzinc_path.resolve()}")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.out_csv_dir, exist_ok=True)

    print(f"Found {len(fzn_files)} .fzn file(s). Running with {MAX_WORKERS} workers.\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_instance, f, args.output_dir, args.out_csv_dir, args.sat): f for f in fzn_files}
        for future in as_completed(futures):
            fzn = futures[future]
            try:
                future.result()
            except Exception as e:
                with print_lock:
                    print(f"[{fzn.stem}] Unhandled exception: {e}")

    print("\nAll instances processed.")
    print(f"{skipped_count}/{len(fzn_files)} skipped due to solveTime.")


if __name__ == "__main__":
    main()
