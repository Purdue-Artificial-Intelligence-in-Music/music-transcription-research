#!/bin/bash
# Uploading to Google Drive is network/CPU-bound, not GPU work. run.py submits
# this with cluster-appropriate account/partition/QOS (Gilbreth: preemptible
# standby + a forced GPU; Anvil: the CPU shared partition). nodes/cpus/mem/time
# below are defaults; -A/-p/--qos/--gres come from run.py's support_flags().
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00

# UPLOAD.SH

source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"
load_modules

start_time=$(date +%s.%N)

echo "--------------------------------------------------"
echo "Uploading results for model: $1"
model_name="$1"

dataset_name=${2// /_}
echo "Uploading dataset: $dataset_name"

MAIN_FOLDER_ID="1aP9Nc49RfXheSiV5vmp-AFr5WBuUxDlE"
MODEL_DIR="$RESEARCH_DIR/$model_name"
OUTPUT_DIR="$MODEL_DIR/research_output_${dataset_name}"

conda activate "$CONDA_ROOT/envs/upload-env"
conda_lib_priority

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

# Copy (don't move) the SLURM output files into the output directory so they get
# uploaded to Drive but ALSO remain under research_output/ for cluster-side
# debugging. Moving them deleted the transcription logs when OUTPUT_DIR was
# removed below, making model failures impossible to diagnose.
echo "Looking for SLURM output files for dataset: $dataset_name"
shopt -s nullglob
slurm_files=("$MODEL_DIR/research_output/${2}_chunk"*"_slurm_output.txt")

if (( ${#slurm_files[@]} > 0 )); then
    echo "Found ${#slurm_files[@]} SLURM output file(s). Copying to output directory."
    cp "${slurm_files[@]}" "$OUTPUT_DIR/"
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
python "$RESEARCH_DIR/scripts/upload.py" \
    --main-folder="$MAIN_FOLDER_ID" \
    --model-name="$model_name" \
    --dataset-name="$dataset_name" \
    --local-directory="$OUTPUT_DIR"
upload_rc=$?

conda deactivate
conda clean --all --yes -q

echo "--------------------------------------------------"
# Only delete the transcription output if the upload actually succeeded.
# Deleting on failure (e.g. Drive folder not shared with the service account)
# permanently loses the .mid results and forces a full re-run.
if [[ "$upload_rc" -eq 0 ]]; then
    echo "Upload succeeded for $model_name / $dataset_name; removing output dir"
    rm -rf "$OUTPUT_DIR"
else
    echo "[ERROR] Upload FAILED (rc=$upload_rc) for $model_name / $dataset_name"
    echo "Keeping $OUTPUT_DIR so the upload can be retried (no re-transcription needed)."
    notify "[$CLUSTER] **Upload FAILED** for \`$model_name / $dataset_name\` (rc=$upload_rc). Output kept for retry." mention
fi

end_time=$(date +%s.%N)
overall_runtime=$(echo "scale=2; $end_time - $start_time" | bc)

hours=$(echo "$overall_runtime / 3600" | bc)
minutes=$(echo "($overall_runtime % 3600) / 60" | bc)
seconds=$(echo "$overall_runtime % 60" | bc | cut -d'.' -f1)

overall_runtime_formatted=$(printf '%02d:%02d:%02d' "$hours" "$minutes" "$seconds")
echo "Total runtime: $overall_runtime_formatted"

# Only announce success if the upload actually succeeded (otherwise the
# "Upload FAILED ... kept for retry" message above already fired).
if [[ "$upload_rc" -eq 0 ]]; then
    notify "[$CLUSTER] Finished uploading results for **$model_name / $dataset_name**\\n.wav files: $num_wavs\\nAvg F-measure: $avg_fmeasure\\nTotal runtime: $overall_runtime_formatted" mention
fi