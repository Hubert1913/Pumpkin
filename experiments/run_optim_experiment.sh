#!/bin/bash
#SBATCH --job-name=nogood-metrics-optim
#SBATCH --array=0-16
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=compute-p2
#SBATCH --time=02:30:00
#SBATCH --mem-per-cpu=4000M
#SBATCH --account=education-eemcs-msc-cs
#SBATCH --output=/scratch/hnowak/nogood-metrics/optim/slurm-logs/slurm_%A_%a.out
#SBATCH --error=/scratch/hnowak/nogood-metrics/optim/slurm-logs/slurm_%A_%a.err

# ── Modules ──────────────────────────────────────────────────────────────────
module load 2025
module load python
module load py-numpy
module load py-pandas

# ── Paths ────────────────────────────────────────────────────────────────────
FZN_DIR="/scratch/hnowak/nogood-metrics/optim/flatzinc"
SOLVER="/scratch/hnowak/nogood-metrics/optim/Pumpkin/target/release/pumpkin-solver"
SCRIPT_DIR="/scratch/hnowak/nogood-metrics/optim/Pumpkin/experiments"
OUT_DIR="/scratch/hnowak/nogood-metrics/optim/outputs"
CSV_DIR="/scratch/hnowak/nogood-metrics/optim/out_data"

# ── Setup ────────────────────────────────────────────────────────────────────
mkdir -p "$OUT_DIR" "$CSV_DIR"

# Build sorted array of .fzn files and pick the one for this task
mapfile -t FZN_FILES < <(find "$FZN_DIR" -maxdepth 1 -name "*.fzn" | sort)
FZN_PATH="${FZN_FILES[$SLURM_ARRAY_TASK_ID]}"

if [[ -z "$FZN_PATH" ]]; then
    echo "No .fzn file for task index $SLURM_ARRAY_TASK_ID — exiting."
    exit 1
fi

INSTANCE_NAME="$(basename "$FZN_PATH" .fzn)"

echo "=== Task $SLURM_ARRAY_TASK_ID | Instance: $INSTANCE_NAME ==="

# ── Step 1: Run the solver ────────────────────────────────────────────────────
PROOF_PATH="$OUT_DIR/${INSTANCE_NAME}_proof_full.drcp"
STATS_PATH="$OUT_DIR/${INSTANCE_NAME}_stats.txt"
STDOUT_LOG="$OUT_DIR/${INSTANCE_NAME}_stdout.log"
STDERR_LOG="$OUT_DIR/${INSTANCE_NAME}_stderr.log"

"$SOLVER" \
    -s "$FZN_PATH" \
    -t 7200000 \
    --proof-path "$PROOF_PATH" \
    --proof-type full \
    --stats-path "$STATS_PATH" \
    > "$STDOUT_LOG" \
    2> "$STDERR_LOG"

# ── Step 2: Check stdout conditions ──────────────────────────────────────────

# Condition 1: the "==========" separator must be present
if ! grep -qF "==========" "$STDOUT_LOG"; then
    echo "[$INSTANCE_NAME] SKIP — separator not found in stdout."
    exit 0
fi

# Condition 2: extract solveTime and check it is < 50
SOLVE_TIME_LINE=$(grep "^%%%mzn-stat: solveTime=" "$STDOUT_LOG" | tail -n1)
if [[ -z "$SOLVE_TIME_LINE" ]]; then
    echo "[$INSTANCE_NAME] SKIP — solveTime line not found in stdout."
    exit 0
fi

SOLVE_TIME=$(echo "$SOLVE_TIME_LINE" | sed 's/^%%%mzn-stat: solveTime=//')

# Use awk for float comparison (bash cannot compare floats natively)
PASSES=$(awk -v t="$SOLVE_TIME" 'BEGIN { print (t < 50) ? "1" : "0" }')
if [[ "$PASSES" != "1" ]]; then
    echo "[$INSTANCE_NAME] SKIP — solveTime=$SOLVE_TIME is not < 50."
    exit 0
fi

echo "[$INSTANCE_NAME] Conditions met (solveTime=$SOLVE_TIME) — running Python script."

# ── Step 3: Run the Python analysis script ────────────────────────────────────
PY_STDOUT="$OUT_DIR/${INSTANCE_NAME}_stdout_python.log"
PY_STDERR="$OUT_DIR/${INSTANCE_NAME}_stderr_python.log"

echo "Before:"
which python

source ~/venvs/nogood-metrics-venv/bin/activate

echo "After:"
which python

# Verify deps are installed — if not, install them once on the login node:
#   module load python/3.11 && pip install --user pandas numpy file_read_backwards
# python3 -c "import file_read_backwards, pandas, numpy" || {
#     echo "[$INSTANCE_NAME] ERROR — missing Python dependencies. Install them on the login node first."
#     exit 1
# }

cd "$SCRIPT_DIR"

python main.py \
    "$INSTANCE_NAME" \
    "$OUT_DIR" \
    "$CSV_DIR" \
    > "$PY_STDOUT" \
    2> "$PY_STDERR"

PY_EXIT=$?
if [[ $PY_EXIT -ne 0 ]]; then
    echo "[$INSTANCE_NAME] WARNING — Python script exited with code $PY_EXIT. See $PY_STDERR."
else
    echo "[$INSTANCE_NAME] Done."
fi