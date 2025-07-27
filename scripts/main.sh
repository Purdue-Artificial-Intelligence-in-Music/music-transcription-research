#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:30:00
#SBATCH -J main
#SBATCH -o 0_main_output.out

start_time=$(date +%s.%N)

echo "--------------------------------------------------"
echo "Running main.sh"

if ! curl -s --head https://repo.anaconda.com | grep -q "^HTTP.* 200"; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

source /etc/profile.d/modules.sh
module load ffmpeg
module load conda
module load parallel

rm -rf /anvil/projects/x-cis240580/.conda/

echo "--------------------------------------------------"
echo "Verifying dataset .wav counts match datasets.json"

DATASET_JSON="/anvil/scratch/x-ochaturvedi/research/datasets.json"
MISMATCHES=0

mapfile -t datasets < <(jq -r '.values[1:][] | @tsv' "$DATASET_JSON")

for row in "${datasets[@]}"; do
    IFS=$'\t' read -r name path instrument audio_type expected_count <<< "$row"
    
    echo "Regenerating list for: $name"
    find "$(realpath "$path")" -type f -name "*.wav" | sort >"${path}.txt"
done

for row in "${datasets[@]}"; do
    IFS=$'\t' read -r name path instrument audio_type expected_count <<< "$row"
    
    list_file="${path}.txt"
    
    if [[ ! -f "$list_file" ]]; then
        echo "[ERROR] Missing list file: $list_file"
        ((MISMATCHES++))
        continue
    fi

    actual_count=$(wc -l < "$list_file" | tr -d ' ')
    
    if [[ "$actual_count" -eq "$expected_count" ]]; then
        echo "[OK] $name | Expected: $expected_count, Found: $actual_count"
    else
        echo "[MISMATCH] $name | Expected: $expected_count, Found: $actual_count"
        ((MISMATCHES++))
    fi
done

if [[ $MISMATCHES -gt 0 ]]; then
    echo "--------------------------------------------------"
    echo "[WARNING] $MISMATCHES mismatches found in dataset .wav counts."
else
    echo "--------------------------------------------------"
    echo "[SUCCESS] All dataset counts match expected values."
fi

echo "--------------------------------------------------"
echo "Creating shared conda environments for scoring and Google Drive upload"

export CONDA_PKGS_DIRS=/anvil/projects/x-cis240580/.conda/pkgs_scoring
mkdir -p "$CONDA_PKGS_DIRS"
conda create -y -q --prefix /anvil/projects/x-cis240580/.conda/envs/scoring-env python=3.10 pip setuptools mir_eval pretty_midi numpy=1.23 pyyaml >/dev/null
rm -rf "$CONDA_PKGS_DIRS"

export CONDA_PKGS_DIRS=/anvil/projects/x-cis240580/.conda/pkgs_upload
mkdir -p "$CONDA_PKGS_DIRS"
conda create -y -q --prefix /anvil/projects/x-cis240580/.conda/envs/upload-env python=3.10 pip pydrive2 >/dev/null
rm -rf "$CONDA_PKGS_DIRS"

if [ ! -d "/anvil/projects/x-cis240580/.conda/envs/scoring-env" ]; then
    echo "Scoring environment failed to create. Skipping scoring."
    exit 1
fi
if [ ! -d "/anvil/projects/x-cis240580/.conda/envs/upload-env" ]; then
    echo "Upload environment failed to create. Skipping upload."
    exit 1
fi

echo "--------------------------------------------------"
echo "Running cloning for all model repositories"

export CONDA_PKGS_DIRS=/anvil/projects/x-cis240580/.conda/pkgs_cloning
mkdir -p "$CONDA_PKGS_DIRS"
conda create -y -q --prefix /anvil/projects/x-cis240580/.conda/envs/cloning-env python=3.13 git-lfs pip requests gitpython >/dev/null
rm -rf "$CONDA_PKGS_DIRS"

conda activate /anvil/projects/x-cis240580/.conda/envs/cloning-env
pip install -q requests gitpython >/dev/null
conda install -c conda-forge -y -q git-lfs >/dev/null
git lfs install >/dev/null

python cloning.py

echo "--------------------------------------------------"
echo "Paring the json file with all model data"
echo ""
echo "Cloned models:"
count=0
mapfile -t lines < <(jq -c '.values[1:][]' models.json)
for line in "${lines[@]}"; do
    MODEL_NAME=$(echo "$line" | jq -r '.[0]')
    echo "$MODEL_NAME"
    count=$((count + 1))
done

for line in "${lines[@]}"; do
    MODEL_NAME=$(echo "$line" | jq -r '.[0]')
    MODEL_DIR="$MODEL_NAME"

    if [ -d "$MODEL_DIR" ]; then
        cd "$MODEL_DIR" || {
            echo "Failed to enter directory $MODEL_DIR"
            continue
        }

        git lfs pull

        cd .. || {
            echo "Failed to return to parent directory"
            continue
        }
    else
        echo "Directory $MODEL_DIR does not exist."
    fi
done

conda deactivate
rm -rf /anvil/projects/x-cis240580/.conda/envs/cloning-env

echo "--------------------------------------------------"
echo "Making model conda environments"

make_env() {
    local line="$1"
    MODEL_NAME_RAW=$(echo "$line" | jq -r '.[0]')
    MODEL_NAME=${MODEL_NAME_RAW// /_}
    ENV_NAME="running-env-${MODEL_NAME}"
    ENV_PATH="/anvil/projects/x-cis240580/.conda/envs/$ENV_NAME"
    PKGS_PATH="/anvil/projects/x-cis240580/.conda/pkgs_${ENV_NAME}"
    MODEL_DIR="$MODEL_NAME_RAW"

    # Set custom package directory
    export CONDA_PKGS_DIRS="$PKGS_PATH"
    mkdir -p "$CONDA_PKGS_DIRS"

    # Remove old environment if it exists
    if [ -d "$ENV_PATH" ]; then
        conda env remove -y --prefix "$ENV_PATH" >/dev/null
        rm -rf "$ENV_PATH"
    fi

    # Check if environment.yml exists
    if [ ! -f "./$MODEL_DIR/environment.yml" ]; then
        echo "[SKIP] Missing environment.yml for $MODEL_DIR"
        return
    fi

    echo "[INFO] Creating conda env for $MODEL_NAME_RAW..."
    conda env create -q -f "./$MODEL_DIR/environment.yml" --prefix "$ENV_PATH" >/dev/null || {
        echo "[ERROR] Failed to create environment for $MODEL_NAME_RAW"
        return
    }

    PYTHON_VERSION=$(grep -E '^ *- *python[=>< ]' "./$MODEL_DIR/environment.yml" | sed -E 's/.*python[^0-9]*([0-9]+\.[0-9]+).*/\1/' | head -n 1)
    if [ -z "$PYTHON_VERSION" ]; then
        echo "[ERROR] Could not determine Python version for $MODEL_NAME_RAW"
        return
    fi

    echo "[INFO] Installing TensorFlow in $ENV_NAME (Python $PYTHON_VERSION)..."
    "$ENV_PATH/bin/pip" install --quiet tensorflow

    PY_CMD="$ENV_PATH/bin/python"
    PY_VER=$($PY_CMD -c 'import sys; print(sys.version.split()[0])')
    TF_VER=$($PY_CMD -c "import os; os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'; import tensorflow as tf; print(tf.__version__)" 2>/dev/null)

    echo "[RESULT] $MODEL_NAME_RAW | Python: ${PY_VER:-unknown} | TensorFlow: ${TF_VER:-failed to import}"

    conda clean --packages --tarballs --yes >/dev/null
    rm -rf "$PKGS_PATH"
}

export -f make_env
export CONDA_PKGS_DIRS
export PATH

# Use parallel to create conda environments in parallel
printf "%s\n" "${lines[@]}" | parallel -j 8 make_env

conda info --envs

echo "--------------------------------------------------"
# (Optional) Enable for Gilbreth usage

# MAX_ALLOWED=$((50000 - count + 1))
# SLEEP_INTERVAL=300 # Time in seconds between checks (e.g., 5 minutes)

# # Function to count jobs in cluster
# count_jobs() {
#     squeue -A standby | wc -l
# }

# while true; do
#     COUNT=$(count_jobs)
#     echo "$(date): Current jobs = $COUNT"

#     if [ "$COUNT" -lt "$MAX_ALLOWED" ]; then
#         echo "Job count is within limit. Running job generation..."
#         # python run.py
#         break
#     else
#         echo "Too many jobs. Sleeping for $SLEEP_INTERVAL seconds..."
#         sleep $SLEEP_INTERVAL
#     fi
# done

python run.py

job_count="UNKNOWN"
if [ -f "jobs_submitted.txt" ]; then
    job_count=$(cat jobs_submitted.txt)
fi
rm -f jobs_submitted.txt

echo "--------------------------------------------------"
echo "Script execution completed!"

end_time=$(date +%s.%N)
overall_runtime=$(echo "scale=2; $end_time - $start_time" | bc)

hours=$(echo "$overall_runtime / 3600" | bc)
minutes=$(echo "($overall_runtime % 3600) / 60" | bc)
seconds=$(echo "$overall_runtime % 60" | bc | cut -d'.' -f1)

overall_runtime_formatted=$(printf '%02d:%02d:%02d' "$hours" "$minutes" "$seconds")
echo "Total runtime: $overall_runtime_formatted"

curl -s -X POST -H "Content-Type: application/json" -d '{"content": "Main script for paper has been executed!\nTotal runtime: '"$overall_runtime_formatted"'\n**Jobs submitted**: '"$job_count"'", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
