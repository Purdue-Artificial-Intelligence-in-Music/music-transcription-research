#!/bin/bash
# Defaults target Gilbreth; run.py overrides -A/-p/--qos per cluster (gpu_flags).
#SBATCH -A yunglu
#SBATCH -p a100-80gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --mem=240G
#SBATCH --time=2-00:00:00

source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"

# Check for internet access for Conda environment creation
if ! curl --silent --head --fail https://repo.anaconda.com > /dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    notify "URGENT: NO INTERNET ACCESS FOR CONDA CREATION ($CLUSTER)" mention
    exit 1
fi

start_time=$(date +%s.%N)

echo "--------------------------------------------------"
echo "Grading model: $1"
model_name=${1// /_}
export model_name

echo "Processing dataset: $2"
dataset_name=${2// /_}
export dataset_name

echo "Searching in: $3"

echo "Audio type: $4"
audio_type=${4// /_}
export audio_type

# $5 is the chunk directory; this array task picks its own chunk file by index.
chunk_dir="$5"
chunk_file="$chunk_dir/chunk_$(printf '%03d' "${SLURM_ARRAY_TASK_ID:-0}").txt"
echo "Chunk dir: $chunk_dir"
echo "Chunk file: $chunk_file"
if [[ ! -f "$chunk_file" ]]; then
    echo "Chunk file $chunk_file not found, exiting."
    exit 1
fi
chunk_basename=$(basename "$chunk_file" .txt)
export chunk_basename

load_modules

export PIP_NO_CACHE_DIR=true

echo "--------------------------------------------------"
echo "Available GPUs:"
nvidia-smi -L 2>/dev/null || echo "nvidia-smi not found"
gpu_count=$(nvidia-smi -L | wc -l) # Determine number of GPUs
cpu_count=$SLURM_CPUS_ON_NODE # Determine number of CPU cores

echo "--------------------------------------------------"
echo "Transcribing dataset files with $1"
export MODEL_DIR="$1"
mkdir -p "./$1/research_output_$dataset_name"
cd "$1"
shopt -s nullglob

# Temporary folder to store per-file data
temp_dir="./temp_${dataset_name}_${chunk_basename}"
rm -rf "$temp_dir"
mkdir "$temp_dir"
export temp_dir

# Activate the Conda environment
conda activate "$CONDA_ROOT/envs/running-env-$model_name"
conda_lib_priority

# Function to process one audio file
transcribe_file() {
    echo "-------------------------"
    echo "Processing file: $1"
    local original_file="$1"

    local slot="$2"
    # echo "Using GPU: $CUDA_VISIBLE_DEVICES"
    echo "Using GPU: $((slot - 1))"

    local file="$original_file" # Default file to process
    local base_name=$(basename "$original_file" .$audio_type)

    local transcription_path="./research_output_${dataset_name}/${base_name}.mid"
    local runtime_file="$temp_dir/${base_name}.runtime"

    local temp_wav_created=0
    if [[ "$audio_type" != "wav" ]]; then
        local temp_wav="$temp_dir/${base_name}.wav"
        echo "Converting $original_file to temporary WAV file..."
        ffmpeg -loglevel error -y -i "$original_file" -ac 1 -ar 44100 "$temp_wav"
        file="$temp_wav"
        temp_wav_created=1
    fi

    # Pad very short audio with trailing silence so model CNNs don't crash on
    # inputs shorter than their receptive field (e.g. ReconVAT on sub-second NES
    # SFX: "Kernel size can't be greater than actual input size"). Trailing
    # silence adds no notes, so scoring against the reference is unaffected.
    local MIN_DUR=2
    local dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    if [[ -n "$dur" ]] && awk "BEGIN{exit !($dur < $MIN_DUR)}"; then
        local padded_wav="$temp_dir/${base_name}_padded.wav"
        echo "Padding short audio (${dur}s) to ${MIN_DUR}s: $base_name"
        if ffmpeg -loglevel error -y -i "$file" -af "apad=whole_dur=${MIN_DUR}" -ac 1 -ar 44100 "$padded_wav" 2>/dev/null; then
            [[ "$temp_wav_created" -eq 1 ]] && rm -f "$file"
            file="$padded_wav"
            temp_wav_created=1
        fi
    fi

    local start_time=$(date +%s.%N)

    CUDA_VISIBLE_DEVICES=$((slot - 1)) python3 main.py -i "$file" -o "$transcription_path"

    local end_time=$(date +%s.%N)

    # Delete temporary WAV file if created
    if [[ "$temp_wav_created" -eq 1 ]]; then
        rm -f "$file"
    fi

    # Runtime calculation
    local runtime=$(echo "$end_time - $start_time" | bc)
    echo "$runtime" >"$runtime_file"
    echo "Processed ${base_name}.$audio_type in $runtime seconds"
}
export -f transcribe_file
export PATH CONDA_PREFIX LD_LIBRARY_PATH

# Run jobs in parallel using GNU Parallel
cat "$chunk_file" | parallel -j "$gpu_count" transcribe_file {} {%}

# Deactivate the running-env Conda environment
conda deactivate

# Compute average runtime
total=0
count=0
for file in "$temp_dir"/*.runtime; do
    if [[ -f "$file" ]]; then
        value=$(cat "$file")
        # Remove any whitespace
        value=$(echo "$value" | tr -d '[:space:]')
        if [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            total=$(echo "$total + $value" | bc)
            ((count++))
        fi
    fi
done
if [[ $count -gt 0 ]]; then
    avg_runtime=$(echo "scale=4; $total / $count" | bc)
    echo "--------------------------------------------------"
    echo "Average runtime per file: $avg_runtime seconds"
else
    echo "No valid runtimes collected or no files processed."
fi

echo "--------------------------------------------------"
echo "Scoring all transcriptions from $1"

details_file="./details_${dataset_name}.txt"
export details_file
touch "$details_file"

if [ ! -s "$details_file" ]; then
    {
        echo "Model Name: $model_name"
        echo "Dataset Name: $2"
        echo ""
        echo ""
    } >"$details_file"
fi

# Activate the Conda environment
conda activate "$CONDA_ROOT/envs/scoring-env"
conda_lib_priority

# Function to score one transcribed file
score_transcription() {
    echo "-------------------------"
    echo "Scoring file: $1"
    local original_file="$1"
    local slot="$2"

    # Base name without extension, using the same $audio_type as before
    local base_name
    base_name=$(basename "$original_file" .$audio_type)

    # Paths used during transcription/scoring
    local reference_file
    reference_file=$(realpath "${original_file%.$audio_type}.mid")
    if [[ ! -f "$reference_file" ]]; then
        reference_file=$(realpath "${original_file%.$audio_type}.midi")
    fi

    local transcription_path="./research_output_${dataset_name}/${base_name}.mid"
    local temp_detail_file="$temp_dir/${base_name}.details"
    local fmeasure_file="$temp_dir/${base_name}.fmeasure"
    local runtime_file="$temp_dir/${base_name}.runtime"

    # Duration (use the original audio file)
    local duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$original_file")

    # Validate inputs
    if [[ ! -f "$reference_file" ]]; then
        echo "Reference MIDI not found for $original_file, skipping scoring."
        echo "MISSING_REF" > "$fmeasure_file"
        {
            printf '%s\n' "$(basename "$original_file")"
            printf 'Duration: %s seconds\n' "${duration:-UNKNOWN}"
            printf 'Reference: %s\n' "MISSING"
            printf 'Transcription: %s\n\n' "$transcription_path"
        } > "$temp_detail_file"
        return
    fi
    if [[ ! -f "$transcription_path" ]]; then
        echo "Transcription MIDI not found at $transcription_path, skipping scoring."
        echo "MISSING_TRANS" > "$fmeasure_file"
        {
            printf '%s\n' "$(basename "$original_file")"
            printf 'Duration: %s seconds\n' "${duration:-UNKNOWN}"
            printf 'Reference: %s\n' "$reference_file"
            printf 'Transcription: %s\n\n' "MISSING"
        } > "$temp_detail_file"
        return
    fi

    # Score the transcription
    local output=$(python ../scripts/scoring.py --reference "$reference_file" --transcription "$transcription_path")

    # Read runtime captured earlier by the transcribe step (if present)
    local runtime="UNKNOWN"
    if [[ -f "$runtime_file" ]]; then
        runtime=$(tr -d '[:space:]' < "$runtime_file")
    fi

    # Write per-file details
    {
        printf '%s\n' "$(basename "$original_file")"
        printf 'Duration: %s seconds\n' "${duration:-UNKNOWN}"
        printf '%s\n' "$output"
        printf 'Runtime: %s seconds\n\n' "$runtime"
    } > "$temp_detail_file"

    # Extract F-measure and store it
    local fmeasure=$(echo "$output" | grep -m1 "F-measure:" | awk '{print $2}')

    if [[ "$fmeasure" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "$fmeasure" > "$fmeasure_file"
    else
        echo "INVALID" > "$fmeasure_file"
        echo "Warning: Invalid F-measure detected for $original_file -> '$fmeasure'"
    fi
}
export -f score_transcription
export PATH CONDA_PREFIX LD_LIBRARY_PATH

cat "$chunk_file" | parallel -j "$cpu_count" score_transcription {} {%}

# Deactivate the scoring-env Conda environment
conda deactivate

echo "--------------------------------------------------"

# Merge per-file details into shared details.txt without overwriting
echo "Appending per-file details into $details_file"
for file in "$temp_dir"/*.details; do
    if [[ -f "$file" ]]; then
        cat "$file" >> "$details_file"
    fi
done

# Compute average F-measure
total=0
count=0
for file in "$temp_dir"/*.fmeasure; do
    if [[ -f "$file" ]]; then
        value=$(cat "$file")
        if [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            total=$(echo "$total + $value" | bc)
            ((count++))
        fi
    fi
done
if [[ $count -gt 0 ]]; then
    avg_fmeasure=$(echo "scale=4; $total / $count" | bc)
    echo "Average F-measure per file: $avg_fmeasure"
else
    echo "No valid F-measures collected."
fi

# Clean up
rm -rf "$temp_dir"
cd ..

echo "--------------------------------------------------"
echo "Script execution completed!"

end_time=$(date +%s.%N)
overall_runtime=$(echo "scale=2; $end_time - $start_time" | bc)

hours=$(echo "$overall_runtime / 3600" | bc)
minutes=$(echo "($overall_runtime % 3600) / 60" | bc)
seconds=$(echo "$overall_runtime % 60" | bc | cut -d'.' -f1)

overall_runtime_formatted=$(printf '%02d:%02d:%02d' "$hours" "$minutes" "$seconds")
echo "Total runtime: $overall_runtime_formatted"

notify "**[$CLUSTER] Model Evaluation Completed**\n**Model:** \`$1\`\n**Dataset:** \`$2\`\n**Chunk:** \`$chunk_basename\`\n**Average F-measure:** \`$avg_fmeasure\`\n**Total Runtime:** \`$overall_runtime_formatted\`"
