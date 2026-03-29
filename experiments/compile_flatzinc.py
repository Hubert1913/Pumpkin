import argparse
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_WORKERS = 4


def build_jobs(instances_dir, flatzinc_dir):
    jobs = []
    for subfolder in instances_dir.iterdir():
        if not subfolder.is_dir():
            continue

        mzn_files = list(subfolder.glob("*.mzn"))
        if not mzn_files:
            print(f"[SKIP] No .mzn file found in {subfolder.name}")
            continue

        mzn_file = mzn_files[0]
        dzn_files = list(subfolder.glob("*.dzn"))

        if not dzn_files:
            print(f"[SKIP] No .dzn files found in {subfolder.name}")
            continue

        for dzn_file in dzn_files:
            output_name = f"{subfolder.name}_{dzn_file.stem}.fzn"
            output_path = flatzinc_dir / output_name
            jobs.append((subfolder.name, mzn_file, dzn_file, output_path))

    return jobs


def run_job(job, solver):
    subfolder_name, mzn_file, dzn_file, output_path = job
    cmd = [
        "minizinc", "-c",
        "--solver", solver,
        str(mzn_file),
        str(dzn_file),
        "--output-to-file", str(output_path),
    ]
    label = f"{subfolder_name}/{dzn_file.name}"
    print(f"[START] {label}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"[OK]    {label} -> {output_path.name}")
        else:
            print(f"[FAIL]  {label} (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().splitlines():
                    print(f"        {line}")
        return result.returncode == 0
    except FileNotFoundError:
        print(f"[ERROR] 'minizinc' not found. Is it installed and on your PATH?")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("instances_dir", type=str, help="Path to directory containing instances")
    parser.add_argument("flatzinc_dir", type=str, help="Path to directory for output .fzn files")
    parser.add_argument("solver_path", type=str, help="Path to solver .msc file")
    args = parser.parse_args()

    instances_dir = Path(args.instances_dir)
    flatzinc_dir = Path(args.flatzinc_dir)

    flatzinc_dir.mkdir(parents=True, exist_ok=True)

    jobs = build_jobs(instances_dir, flatzinc_dir)
    if not jobs:
        print("No jobs found. Check that your instances directory exists and is populated.")
        return

    print(f"Found {len(jobs)} job(s). Running with {MAX_WORKERS} parallel workers.\n")

    success, failure = 0, 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_job, job, args.solver_path): job for job in jobs}
        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                failure += 1

    print(f"\nDone. {success} succeeded, {failure} failed.")


if __name__ == "__main__":
    main()
