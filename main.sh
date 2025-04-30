#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:30:00
#SBATCH -J main

export MODULEPATH=${MODULEPATH:-""}
export ROOTSAFE=${ROOTSAFE:-""}
set -euo pipefail
trap 'echo "Script terminated unexpectedly."; exit 1' ERR

echo "--------------------------------------------------"
echo "Starting main.sh"

# ------------------------------
# Internet Check
# ------------------------------
if ! ping -c 1 repo.anaconda.com &>/dev/null; then
    MSG="No internet access. Cannot create Conda environment. Exiting."
    echo "$MSG"
    curl -d "$MSG" -H "Title: Error" -H "Priority: urgent" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

# ------------------------------
# Environment Setup
# ------------------------------
echo "Loading modules and setting up Conda..."
source /etc/profile.d/modules.sh
module --force purge
module load external ffmpeg conda

CONDA_ENV_NAME="cloning-env"
eval "$(conda shell.bash hook)"
if conda env list | grep -q "$CONDA_ENV_NAME"; then
    conda remove -y --name "$CONDA_ENV_NAME" --all
fi

conda create -y -q --name "$CONDA_ENV_NAME"
conda activate "$CONDA_ENV_NAME"
conda install -y -q pip
pip install -q requests gitpython
conda install -c conda-forge -y -q git-lfs
git lfs install

# ------------------------------
# Run Cloning Script
# ------------------------------
echo "--------------------------------------------------"
echo "Running Python cloning script..."
python cloning.py

# ------------------------------
# Git LFS Pull per Team
# ------------------------------
echo "--------------------------------------------------"
echo "Parsing team data and running git lfs pull..."

mapfile -t TEAM_LINES < <(jq -c '.values[1:][]' models.json)
TEAM_COUNT=${#TEAM_LINES[@]}

for line in "${TEAM_LINES[@]}"; do
    TEAM_NAME=$(echo "$line" | jq -r '.[0]')
    TEAM_DIR="$TEAM_NAME"

    if [ -d "$TEAM_DIR" ]; then
        echo "Pulling LFS for $TEAM_DIR"
        cd "$TEAM_DIR"
        git lfs pull || echo "LFS pull failed for $TEAM_DIR"
        cd ..
    else
        echo "Directory $TEAM_DIR does not exist."
    fi
done

# ------------------------------
# Build MuseScore Singularity Container
# ------------------------------
echo "--------------------------------------------------"
echo "Building MuseScore Singularity container..."

MUSESCORE_SIF="musescore.sif"
MUSESCORE_DEF="musescore.def"

if [ ! -f "$MUSESCORE_SIF" ]; then
    cat <<EOF >"$MUSESCORE_DEF"
BootStrap: docker
From: ubuntu:22.04

%post
    apt update && apt install -y musescore ffmpeg curl imagemagick
    echo "MuseScore and ImageMagick Installed"

%runscript
    export QT_QPA_PLATFORM=offscreen
    exec /usr/bin/mscore "\$@"
EOF

    singularity build --force "$MUSESCORE_SIF" "$MUSESCORE_DEF" &>/dev/null
    rm "$MUSESCORE_DEF"
else
    echo "Singularity container already exists."
fi

# ------------------------------
# Cleanup Conda Environment
# ------------------------------
conda deactivate
conda env remove -y -q --name "$CONDA_ENV_NAME"
conda clean --all --yes -q

# ------------------------------
# Job Submission Control
# ------------------------------
echo "--------------------------------------------------"
echo "Creating Slurm jobs for each team"

MAX_ALLOWED=$((50000 - TEAM_COUNT + 1))
SLEEP_INTERVAL=300

count_jobs() {
    squeue -A standby | wc -l
}

while true; do
    CURRENT_JOBS=$(count_jobs)
    echo "$(date): Current jobs = $CURRENT_JOBS"

    if [ "$CURRENT_JOBS" -lt "$MAX_ALLOWED" ]; then
        echo "Job count is within limit. Running job generation..."
        python run.py
        break
    else
        echo "Too many jobs. Sleeping for $SLEEP_INTERVAL seconds..."
        sleep "$SLEEP_INTERVAL"
    fi
done

# ------------------------------
# Final Notification
# ------------------------------
echo "--------------------------------------------------"
echo "Script execution completed!"

curl -s -X POST -H "Content-Type: application/json" -d '{"content": "Main script for paper has been executed!"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Main script for paper has been executed!" -H "Title: Main script execution" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
