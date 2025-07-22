#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00

# UPLOAD.SH

start_time=$(date +%s.%N)

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
module load conda

conda activate /anvil/projects/x-cis240580/.conda/envs/upload-env

DETAILS_FILE="$MODEL_DIR/details_${dataset_name}.txt"

# Analyze and append stats to details file
if [[ -f "$DETAILS_FILE" ]]; then
    num_wavs=$(grep -c '\.wav$' "$DETAILS_FILE")

    avg_fmeasure=$(awk '/^F-measure:/ {sum += $2; count++} END {if (count > 0) print sum / count; else print "0.0"}' "$DETAILS_FILE")

    avg_runtime=$(awk '/^Runtime:/ {sum += $2; count++} END {if (count > 0) print sum / count; else print "0.0"}' "$DETAILS_FILE")

    {
        echo ""
        echo "Number of files processed: $num_wavs"
        echo "Average F-measure: $avg_fmeasure"
        echo "Average Runtime (seconds): $avg_runtime"
    } >> "$DETAILS_FILE"
fi

# Attach details file if present
if [[ -f "$DETAILS_FILE" ]]; then
    echo "Copying details file into output directory"
    cp "$DETAILS_FILE" "$OUTPUT_DIR/"
else
    echo "Warning: No details_${dataset_name}.txt file found"
fi

# Move relevant SLURM output files into the output directory
echo "Looking for SLURM output files for dataset: $dataset_name"
shopt -s nullglob
slurm_files=("$MODEL_DIR/research_output/${dataset_name}_chunk"*"_slurm_output.txt")

if (( ${#slurm_files[@]} > 0 )); then
    echo "Found ${#slurm_files[@]} SLURM output file(s). Moving to output directory."
    mv "${slurm_files[@]}" "$OUTPUT_DIR/"
else
    echo "No SLURM output files found for dataset: $dataset_name"
fi

# Check if output dir exists
if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "Error: Output directory $OUTPUT_DIR does not exist!"
    exit 1
fi

# Perform upload
echo "--> Uploading $OUTPUT_DIR to Google Drive"
python "$RESEARCH_DIR/upload.py" \
    --main-folder="$MAIN_FOLDER_ID" \
    --model-name="$model_name" \
    --dataset-name="$dataset_name" \
    --local-directory="$OUTPUT_DIR"

conda deactivate
conda clean --all --yes -q

echo "--------------------------------------------------"
echo "Upload complete for $model_name / $dataset_name"

end_time=$(date +%s.%N)
overall_runtime=$(echo "scale=2; $end_time - $start_time" | bc)

hours=$(echo "$overall_runtime / 3600" | bc)
minutes=$(echo "($overall_runtime % 3600) / 60" | bc)
seconds=$(echo "$overall_runtime % 60" | bc | cut -d'.' -f1)

overall_runtime_formatted=$(printf '%02d:%02d:%02d' "$hours" "$minutes" "$seconds")
echo "Total runtime: $overall_runtime_formatted"

curl -s -X POST -H "Content-Type: application/json" -d "{
\"content\": \"Finished uploading results for **$model_name / $dataset_name**\\n.wav files: $num_wavs\\nAvg F-measure: $avg_fmeasure\\nTotal runtime: $overall_runtime_formatted\",
\"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null