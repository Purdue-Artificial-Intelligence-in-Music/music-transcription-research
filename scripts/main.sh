#!/bin/bash
# Defaults target Gilbreth. To run on Anvil, submit with overrides, e.g.:
#   sbatch -A cis240587-gpu -p gpu scripts/main.sh
#SBATCH -A yunglu
#SBATCH -p a100-80gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=240G
#SBATCH --time=2-00:00:00
#SBATCH -J main
#SBATCH -o 0_main_output.out

cd "$SLURM_SUBMIT_DIR"
source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"

# Check for internet access for Conda environment creation
if ! curl --silent --head --fail https://repo.anaconda.com > /dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    notify "URGENT: NO INTERNET ACCESS FOR CONDA CREATION ($CLUSTER)" mention
    exit 1
fi

start_time=$(date +%s.%N)

echo "--------------------------------------------------"
echo "Running main.sh on $CLUSTER"

load_modules

export JOBS="${SLURM_CPUS_PER_TASK:-${SLURM_CPUS_ON_NODE:-$(getconf _NPROCESSORS_ONLN)}}"
export PARALLEL="--will-cite"

task_time=$(date +%s.%N)
rm -rf "$CONDA_ROOT/"
echo "Cleaned conda directory in $(echo "$(date +%s.%N) - $task_time" | bc) seconds"

echo "--------------------------------------------------"
echo "Verifying dataset file counts match datasets.json"
task_time=$(date +%s.%N)

DATASET_JSON="$RESEARCH_DIR/datasets.json"
MISMATCHES=0

mapfile -t datasets < <(jq -r '.values[1:][] | @tsv' "$DATASET_JSON")

# Regenerate lists in parallel
printf '%s\n' "${datasets[@]}" | parallel -j "$JOBS" --colsep '\t' '
    name={1}; path={2}; ext={4};
    echo "Regenerating list for: {1}";
    find "$(realpath "$path")" -type f -name "*.${ext}" | sort > "${path}.txt"
'

# Check counts in parallel
MISMATCHES=$(
printf '%s\n' "${datasets[@]}" | parallel -j "$JOBS" --colsep '\t' '
    name={1}; path={2}; ext={4}; expected={5};
    list_file="${path}.txt";
    if [[ ! -f "$list_file" ]]; then
        echo "[ERROR] Missing list file: $list_file" >&2
        echo ERR
    else
        actual=$(wc -l < "$list_file" | tr -d " ");
        if [[ "$actual" -eq "$expected" ]]; then
            echo "[OK] {1} | Expected: $expected, Found: $actual"
            echo OK
        else
            echo "[MISMATCH] {1} | Expected: $expected, Found: $actual"
            echo ERR
        fi
    fi
' | grep -c ERR
)

if [[ "$MISMATCHES" -gt 0 ]]; then
    echo "[WARNING] $MISMATCHES mismatches found in dataset file counts."
else
    echo "[SUCCESS] All dataset counts match expected values."
fi
echo "Dataset verification completed in $(echo "$(date +%s.%N) - $task_time" | bc) seconds"

echo "--------------------------------------------------"
echo "Creating shared conda environments for scoring and Google Drive upload"
task_time=$(date +%s.%N)

export CONDA_PKGS_DIRS=$CONDA_ROOT/pkgs_scoring
mkdir -p "$CONDA_PKGS_DIRS"
mamba create -y -q --prefix $CONDA_ROOT/envs/scoring-env python=3.10 pip setuptools mir_eval pretty_midi numpy=1.23 pyyaml >/dev/null

# Raise pretty_midi's MAX_TICK so long files don't trip its sanity check
PM_FILE=$(ls $CONDA_ROOT/envs/scoring-env/lib/python3*/site-packages/pretty_midi/pretty_midi.py 2>/dev/null | head -1)
if [ -n "$PM_FILE" ] && [ -f "$PM_FILE" ]; then
    sed -i 's/^MAX_TICK = 1e7/MAX_TICK = 1e8/' "$PM_FILE"
    echo "Patched MAX_TICK in $PM_FILE"
else
    echo "[WARN] pretty_midi.py not found; MAX_TICK patch skipped"
fi

rm -rf "$CONDA_PKGS_DIRS"

export CONDA_PKGS_DIRS=$CONDA_ROOT/pkgs_upload
mkdir -p "$CONDA_PKGS_DIRS"
mamba create -y -q --prefix $CONDA_ROOT/envs/upload-env python=3.10 pip pydrive2 >/dev/null
rm -rf "$CONDA_PKGS_DIRS"

if [ ! -d "$CONDA_ROOT/envs/scoring-env" ]; then
    echo "Scoring environment failed to create. Skipping scoring."
    exit 1
fi
if [ ! -d "$CONDA_ROOT/envs/upload-env" ]; then
    echo "Upload environment failed to create. Skipping upload."
    exit 1
fi
echo "Shared conda environments created in $(echo "$(date +%s.%N) - $task_time" | bc) seconds"

echo "--------------------------------------------------"
echo "Running cloning for all model repositories"
task_time=$(date +%s.%N)

export CONDA_PKGS_DIRS=$CONDA_ROOT/pkgs_cloning
mkdir -p "$CONDA_PKGS_DIRS"
mamba create -y -q --prefix $CONDA_ROOT/envs/cloning-env python=3.12 git-lfs pip requests gitpython >/dev/null
rm -rf "$CONDA_PKGS_DIRS"

conda activate $CONDA_ROOT/envs/cloning-env
pip install -q requests gitpython >/dev/null
conda install -c conda-forge -y -q git-lfs >/dev/null
git lfs install >/dev/null

python scripts/cloning.py
echo "Cloning completed in $(echo "$(date +%s.%N) - $task_time" | bc) seconds"

echo "--------------------------------------------------"
echo "Parsing the json file with all model data"
echo ""
task_time=$(date +%s.%N)

mapfile -t MODEL_NAMES < <(jq -r '.values[1:][] | select(length>0) | .[0]' models.json | tr -d '\r' | sed "s/^'//;s/'$//")

BASE_DIR="$(pwd)"
export BASE_DIR

echo "Extracted model names from JSON:"
printf "'%s'\n" "${MODEL_NAMES[@]}"
echo ""

# Run git lfs pull in parallel for each directory
printf '%s\0' "${MODEL_NAMES[@]}" \
| parallel -0 -j "$JOBS" '
    cd "$BASE_DIR" || exit 1
    dir={}
    if [[ -d "$dir" ]]; then
        echo "[START] git lfs pull in: $dir"
        if git -C "$dir" lfs pull; then
            echo "[DONE ] $dir"
        else
            echo "[ERROR] git lfs pull failed in: $dir" >&2
        fi
    else
        echo "[MISSING] Directory \"$dir\" does not exist." >&2
        echo "[DEBUG] Looking for: $(printf %q "$dir")" >&2
    fi
'
echo ""

echo "Model parsing completed in $(echo "$(date +%s.%N) - $task_time" | bc) seconds"

conda deactivate
rm -rf $CONDA_ROOT/envs/cloning-env

echo "--------------------------------------------------"
echo "Making model conda environments"
task_time=$(date +%s.%N)

make_env() {
    local MODEL_NAME_RAW="$1"
    MODEL_NAME=${MODEL_NAME_RAW// /_}
    ENV_NAME="running-env-${MODEL_NAME}"
    ENV_PATH="$CONDA_ROOT/envs/$ENV_NAME"
    PKGS_PATH="$CONDA_ROOT/pkgs_${ENV_NAME}_$$"
    MODEL_DIR="$MODEL_NAME_RAW"

    echo "[INFO] PKGS_PATH: $PKGS_PATH"
    echo "[INFO] Creating conda env for $MODEL_NAME_RAW..."

    # Isolate PKGS path
    CONDA_PKGS_DIRS="$PKGS_PATH"
    export CONDA_PKGS_DIRS
    mkdir -p "$CONDA_PKGS_DIRS"

    # Remove existing environment if it exists
    if [ -d "$ENV_PATH" ]; then
        conda env remove -y --prefix "$ENV_PATH" >/dev/null
        rm -rf "$ENV_PATH"
    fi

    # Check if environment.yml exists
    if [ ! -f "./$MODEL_DIR/environment.yml" ]; then
        echo "[SKIP] Missing environment.yml for $MODEL_DIR"
        rm -rf "$PKGS_PATH"
        return
    fi

    # Retry logic for mamba create
    MAX_ATTEMPTS=3
    for ((i=1; i<=MAX_ATTEMPTS; i++)); do
        if mamba env create -y -q -f "./$MODEL_DIR/environment.yml" --prefix "$ENV_PATH" >/dev/null 2>"$ENV_PATH-create.log"; then
            break
        elif [[ $i -lt $MAX_ATTEMPTS ]]; then
            echo "[WARN] Env creation failed for $MODEL_NAME_RAW — retrying ($i/$MAX_ATTEMPTS)..."
            sleep $((RANDOM % 10 + 5))
        else
            echo "[ERROR] Failed to create environment for $MODEL_NAME_RAW after $MAX_ATTEMPTS attempts"
            cat "$ENV_PATH-create.log"
            rm -rf "$PKGS_PATH"
            return
        fi
    done

    PYTHON_CMD="$ENV_PATH/bin/python"

    PY_VER=$($PYTHON_CMD -c 'import sys; print(sys.version.split()[0])')

    REQUIRES_TF=$(grep -i 'tensorflow' "./$MODEL_DIR/environment.yml" || true)
    REQUIRES_PT=$(grep -Ei 'torch|pytorch' "./$MODEL_DIR/environment.yml" || true)

    # GPU detection
    if command -v nvidia-smi &>/dev/null && nvidia-smi -L | grep -q "GPU"; then
        echo "[INFO] GPU detected on node via nvidia-smi."
    else
        echo "[WARN] No GPU detected by nvidia-smi — GPU libraries may not be usable."
    fi

    # Framework detection and reporting
    if $PYTHON_CMD -c "import torch" 2>/dev/null; then
        PT_VER=$($PYTHON_CMD -c "import torch; print(torch.__version__)" 2>/dev/null || echo "unknown")
        CUDA_AVAIL=$($PYTHON_CMD -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "unknown")
        echo "[RESULT] $MODEL_NAME_RAW | Python: $PY_VER | PyTorch: $PT_VER | CUDA: $CUDA_AVAIL"
    elif $PYTHON_CMD -c "import tensorflow as tf" 2>/dev/null; then
        TF_VER=$($PYTHON_CMD -c "import tensorflow as tf; print(tf.__version__)" 2>/dev/null || echo "unknown")
        GPU_DEVICES=$($PYTHON_CMD -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))" 2>/dev/null || echo "unknown")
        echo "[RESULT] $MODEL_NAME_RAW | Python: $PY_VER | TensorFlow: $TF_VER | GPUs: $GPU_DEVICES"
    else
        echo "[RESULT] $MODEL_NAME_RAW | Python: $PY_VER | No TF/PT detected | CUDA libraries installed"
    fi

    conda clean --packages --tarballs --yes >/dev/null
    rm -rf "$PKGS_PATH"
}

export -f make_env
export PATH

# Use parallel to create conda environments in parallel
printf '%s\n' "${MODEL_NAMES[@]}" | parallel -j "$JOBS" make_env

echo "Model environments created in $(echo "$(date +%s.%N) - $task_time" | bc) seconds"

# conda deactivate
conda info --envs

echo "--------------------------------------------------"
task_time=$(date +%s.%N)

python scripts/run.py

job_count="UNKNOWN"
if [ -f "jobs_submitted.txt" ]; then
    job_count=$(cat jobs_submitted.txt)
fi
rm -f jobs_submitted.txt

echo "Job generation completed in $(echo "$(date +%s.%N) - $task_time" | bc) seconds"

echo "--------------------------------------------------"
echo "Script execution completed!"

end_time=$(date +%s.%N)
overall_runtime=$(echo "scale=2; $end_time - $start_time" | bc)

hours=$(echo "$overall_runtime / 3600" | bc)
minutes=$(echo "($overall_runtime % 3600) / 60" | bc)
seconds=$(echo "$overall_runtime % 60" | bc | cut -d'.' -f1)

overall_runtime_formatted=$(printf '%02d:%02d:%02d' "$hours" "$minutes" "$seconds")
echo "Total runtime: $overall_runtime_formatted"

notify "**[$CLUSTER] main.sh completed**\nTotal runtime: $overall_runtime_formatted\n**Jobs submitted**: $job_count"
