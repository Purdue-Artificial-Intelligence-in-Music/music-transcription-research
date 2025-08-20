#!/bin/bash
#SBATCH -A yunglu-k
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=2-00:00:00

# Check for internet access for Conda environment creation
if ! curl --silent --head --fail https://repo.anaconda.com > /dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
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

echo "Chunk file: $5"
chunk_file="$5"
chunk_basename=$(basename "$chunk_file" .txt)
export chunk_basename

source /etc/profile.d/modules.sh
module use /opt/spack/cpu/Core
module use /opt/spack/gpu/Core
module load ffmpeg
module load external
module load conda
module load parallel
module load gcc
source "$(conda info --base)/etc/profile.d/conda.sh"

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
conda activate /scratch/gilbreth/ochaturv/.conda/envs/running-env-"$model_name"

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

    # local duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")

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
conda activate /scratch/gilbreth/ochaturv/.conda/envs/scoring-env

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
    local output=$(python ../scoring.py --reference "$reference_file" --transcription "$transcription_path")

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

curl -s -X POST -H "Content-Type: application/json" -d "{
    \"content\": \"**Model Evaluation Completed**\n**Model:** \`$1\`\n**Dataset:** \`$2\`\n**Chunk:** \`$chunk_basename\`\n**Average F-measure:** \`$avg_fmeasure\`\n**Total Runtime:** \`$overall_runtime_formatted\`\",
    \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
}" \
    -H "Content-Type: application/json" \
    "https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux" >/dev/null
