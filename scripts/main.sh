#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:30:00
#SBATCH -J main

echo "--------------------------------------------------"
echo "Running main.sh"

if ! ping -c 1 repo.anaconda.com &>/dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -d "No internet access. Cannot create Conda environment. Exiting." -H "Title: Error" -H "Priority: urgent" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

source /etc/profile.d/modules.sh
module --force purge
module load external
module load ffmpeg
module load conda

echo "--------------------------------------------------"
echo "Running cloning for all model repositories"

CONDA_ENV_PATH="$HOME/.conda/envs/cloning-env"
if [ -d "$CONDA_ENV_PATH" ] && [ ! -f "$CONDA_ENV_PATH/bin/activate" ]; then
    echo "Removing invalid conda environment at $CONDA_ENV_PATH"
    rm -rf "$CONDA_ENV_PATH"
fi

conda create -y -q --name cloning-env
source activate cloning-env
conda install -y -q pip
pip install -q requests gitpython
conda install -c conda-forge -y -q git-lfs
git lfs install

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
    echo "Removing conda environment 'cloning-env'"
    conda env remove -y -q --name cloning-env
fi
conda clean --all --yes -q

rm -rf /scratch/gilbreth/ochaturv/.conda/envs/

echo "--------------------------------------------------"
echo "Creating Slurm jobs for each model"

MAX_ALLOWED=$((50000 - count + 1))
echo "Max allowed: $MAX_ALLOWED"

SLEEP_INTERVAL=300 # Time in seconds between checks (e.g., 5 minutes)

# Function to count jobs in cluster
count_jobs() {
    squeue -A standby | wc -l
}

while true; do
    COUNT=$(count_jobs)
    echo "$(date): Current jobs = $COUNT"

    if [ "$COUNT" -lt "$MAX_ALLOWED" ]; then
        echo "Job count is within limit. Running job generation..."
        python run.py
        break
    else
        echo "Too many jobs. Sleeping for $SLEEP_INTERVAL seconds..."
        sleep $SLEEP_INTERVAL
    fi
done

echo "--------------------------------------------------"
echo "Script execution completed!"

# curl -s -X POST -H "Content-Type: application/json" -d '{"content": "Main script for paper has been executed!", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
# curl -s -d "Main script for paper has been executed!" -H "Title: Main script execution" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt >/dev/null
