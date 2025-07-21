#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=2-00:00:00

# RUN.SH

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
module load ffmpeg
module load conda
module load parallel
module load gcc/11.2.0

export PIP_NO_CACHE_DIR=true

export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# Check for internet access
if ! curl -s --head https://repo.anaconda.com | grep -q "^HTTP.* 200"; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

echo "--------------------------------------------------"
echo "Running the model: $1"
MODEL_DIR="$1"
mkdir -p "./$1/research_output_$dataset_name"
cd "$1"
shopt -s nullglob

curl -s -X POST -H "Content-Type: application/json" -d "{
  \"content\": \"**Job Started**\n**Model:** \`$1\`\n**Dataset:** \`$dataset_name\`\n**Chunk:** \`$chunk_basename\`\",
  \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
}" \
    -H "Content-Type: application/json" \
    "https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux" >/dev/null

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

# Temporary file to store per-file runtimes
temp_dir="./temp_${dataset_name}_${chunk_basename}"
rm -rf "$temp_dir"
mkdir "$temp_dir"
export temp_dir

# Function to process one audio file
process_file() {
    source "$(conda info --base)/etc/profile.d/conda.sh"

    echo "Processing file: $1"
    local original_file="$1"
    local file="$original_file" # Default file to process
    local base_name=$(basename "$original_file" .$audio_type)

    local reference_file=$(realpath "${original_file%.$audio_type}.mid")
    local transcription_path=".$MODEL_DIR/research_output_${dataset_name}/${base_name}.mid"
    local runtime_file="$temp_dir/${base_name}.runtime"
    local fmeasure_file="$temp_dir/${base_name}.fmeasure"

    local temp_wav_created=0
    if [[ "$audio_type" != "wav" ]]; then
        local temp_wav="$temp_dir/${base_name}.wav"
        echo "Converting $original_file to temporary WAV file..."
        ffmpeg -loglevel error -y -i "$original_file" "$temp_wav"
        file="$temp_wav"
        temp_wav_created=1
    fi

    local duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")

    conda activate /anvil/projects/x-cis240580/.conda/envs/running-env-"$model_name"

    local start_time=$(date +%s.%N)

    python3 main.py -i "$file" -o "$transcription_path"

    local end_time=$(date +%s.%N)

    conda deactivate

    # Delete temporary WAV file if created
    if [[ "$temp_wav_created" -eq 1 ]]; then
        rm -f "$file"
    fi

    # Runtime calculation
    local runtime=$(echo "$end_time - $start_time" | bc)
    echo "$runtime" >"$runtime_file"
    echo "Processed ${base_name}.$audio_type in $runtime seconds"

    # Scoring
    if [[ ! -f "$reference_file" ]]; then
        reference_file=$(realpath "${original_file%.$audio_type}.midi")
    fi
    if [[ ! -f "$reference_file" ]]; then
        echo "Reference MIDI not found for $original_file, skipping scoring."
        echo "MISSING_REF" >"$fmeasure_file"
        return
    fi

    if [[ ! -f "$transcription_path" ]]; then
        echo "Transcription MIDI not found at $transcription_path, skipping scoring."
        echo "MISSING_TRANS" >"$fmeasure_file"
        return
    fi

    conda activate /anvil/projects/x-cis240580/.conda/envs/scoring-env

    local output=$(python3 ../scoring.py --reference "$reference_file" --transcription "$transcription_path")

    {
        printf '%s\n' "$(basename "$original_file")"
        printf 'Duration: %s seconds\n' "$duration"
        printf '%s\n' "$output"
        printf 'Runtime: %f seconds\n\n' "$runtime"
    } >>"$details_file"

    # Extract F-measure and store it
    local fmeasure=$(echo "$output" | grep -m1 "F-measure:" | awk '{print $2}')

    if [[ "$fmeasure" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "$fmeasure" >"$fmeasure_file"
    else
        echo "INVALID" >"$fmeasure_file"
        echo "Warning: Invalid F-measure detected: '$fmeasure' for $original_file"
    fi

    conda deactivate
}
export -f process_file

# Determine number of parallel jobs
gpu_count=$(nvidia-smi -L | wc -l)

# Run jobs in parallel using GNU Parallel
cat "$chunk_file" | parallel -j "$gpu_count" process_file

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

# Clean up
rm -rf "$temp_dir"
cd ..

curl -s -X POST -H "Content-Type: application/json" -d "{
  \"content\": \"**Model Evaluation Complete**\n**Model:** \`$1\`\n**Dataset:** \`$2\`\n**Chunk:** \`$chunk_basename\`\n**Average F-measure:** \`$avg_fmeasure\`\",
    \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
}" \
    -H "Content-Type: application/json" \
    "https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux" >/dev/null

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
  \"content\": \"**Job Completed**\n**Model:** \`$1\`\n**Dataset:** \`$2\`\n**Chunk:** \`$chunk_basename\`\n**Total Runtime:** \`$overall_runtime_formatted\`\",
    \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
}" \
    -H "Content-Type: application/json" \
    "https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux" >/dev/null
