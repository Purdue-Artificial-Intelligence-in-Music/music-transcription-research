#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --time=01:00:00

# UPLOAD.SH

echo "--------------------------------------------------"
echo "Uploading results for model: $1"
model_name="$1"

dataset_name=${2// /_}
echo "Uploading dataset: $dataset_name"

MAIN_FOLDER_ID="11zBLIit-Cg7Tu5KHJXZBvaUauFr5Dtbc"
RESEARCH_DIR="/anvil/scratch/x-ochaturvedi/research"
MODEL_DIR="$RESEARCH_DIR/$model_name"
OUTPUT_DIR="$MODEL_DIR/research_output_${dataset_name}"

source /etc/profile.d/modules.sh
module purge
module load conda

conda activate /anvil/scratch/x-ochaturvedi/.conda/envs/upload-env

# Attach details file if present
DETAILS_FILE="$MODEL_DIR/details_${dataset_name}.txt"
if [[ -f "$DETAILS_FILE" ]]; then
    echo "Copying details file into output directory"
    cp "$DETAILS_FILE" "$OUTPUT_DIR/"
else
    echo "Warning: No details_${dataset_name}.txt file found"
fi

# Check if output dir exists
if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "Error: Output directory $OUTPUT_DIR does not exist!"
    exit 1
fi

# Perform upload
echo "→ Uploading $OUTPUT_DIR to Google Drive"
python "$RESEARCH_DIR/upload.py" \
    --main-folder="$MAIN_FOLDER_ID" \
    --model-name="$model_name" \
    --dataset-name="$dataset_name" \
    --local-directory="$OUTPUT_DIR"

conda deactivate
conda clean --all --yes -q

echo "Upload complete for $model_name / $dataset_name"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Finished uploading results for $model_name / $dataset_name\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
