#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --time=01:30:00
#SBATCH -J main
#SBATCH -o 0_main_output.out

start_time=$(date +%s.%N)

echo "--------------------------------------------------"
echo "Running main.sh"

if ! ping -c 1 repo.anaconda.com &>/dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

source /etc/profile.d/modules.sh
module --force purge
module load ffmpeg
module load conda

rm -rf /anvil/projects/x-cis240580/.conda/

echo "--------------------------------------------------"
echo "Creating shared conda environments for scoring and Google Drive upload"

conda create -y -q --prefix /anvil/projects/x-cis240580/.conda/envs/scoring-env python=3.10 pip setuptools mir_eval pretty_midi numpy=1.23 pyyaml >/dev/null
conda create -y -q --prefix /anvil/projects/x-cis240580/.conda/envs/upload-env python=3.10 pip pydrive2 >/dev/null

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

CONDA_ENV_PATH="$HOME/.conda/envs/cloning-env"
if [ -d "$CONDA_ENV_PATH" ] && [ ! -f "$CONDA_ENV_PATH/bin/activate" ]; then
    echo "Removing invalid conda environment at $CONDA_ENV_PATH"
    rm -rf "$CONDA_ENV_PATH"
fi

conda create -y -q --name cloning-env python=3.13 pip >/dev/null
conda activate cloning-env
pip install -q requests gitpython >/dev/null
conda install -c conda-forge -y -q git-lfs >/dev/null
git lfs install >/dev/null

python cloning.py

echo "--------------------------------------------------"
echo "Paring the json file with all model data"
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

        # Perform git lfs pull
        git lfs pull

        # Return to the parent directory
        cd .. || {
            echo "Failed to return to parent directory"
            continue
        }
    else
        echo "Directory $MODEL_DIR does not exist."
    fi
done

conda deactivate
if conda env list | grep -q "cloning-env"; then
    conda env remove -y -q --name cloning-env >/dev/null
fi
conda clean --all --yes -q

rm -rf /anvil/projects/x-cis240580/.conda/envs/cloning-env

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
