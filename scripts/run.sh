#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=32
#SBATCH --time=2-00:00:00

# RUN.SH

start_time=$(date +%s.%N)

echo "--------------------------------------------------"
echo "Grading model: $1"
echo "Processing dataset: $2"
echo "Searching in: $3"
echo "Audio type: $4"
echo ""
echo "Running on: $(hostname)"
echo ""

model_name=${1// /_}
dataset_name=${2// /_}
export dataset_name

audio_type=${4// /_}
export audio_type

environment_name="${model_name}_${dataset_name}"
export environment_name
echo "Environment name: $environment_name"

source /etc/profile.d/modules.sh
module --force purge
module load ffmpeg
module load conda
module load parallel
module load gcc/11.2.0

export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

conda clean --all --yes

# Check for internet access
if ! ping -c 1 repo.anaconda.com &>/dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

echo "--------------------------------------------------"
echo "Deleting any existing conda environment"
conda env remove -q -p /anvil/scratch/x-ochaturvedi/.conda/envs/running-env-"$environment_name" -y
conda env remove -q -p /anvil/scratch/x-ochaturvedi/.conda/envs/scoring-env-"$environment_name" -y
rm -rf /anvil/scratch/x-ochaturvedi/.conda/envs/running-env-"$environment_name"
rm -rf /anvil/scratch/x-ochaturvedi/.conda/envs/scoring-env-"$environment_name"

echo "--------------------------------------------------"
echo "Creating conda environment"
cd /anvil/scratch/x-ochaturvedi/research || {
    echo "Failed to change directory to /anvil/scratch/x-ochaturvedi/research"
    exit 1
}
if [ ! -f "./$1/environment.yml" ]; then
    echo "Error: environment.yml file not found for model $1"
    exit 1
fi
conda env create -q -f "./$1/environment.yml" --prefix /anvil/scratch/x-ochaturvedi/.conda/envs/running-env-"$environment_name"
conda create -y -q --prefix /anvil/scratch/x-ochaturvedi/.conda/envs/scoring-env-"$environment_name" python=3.10 pip setuptools mir_eval pretty_midi numpy=1.23 pyyaml

echo "--------------------------------------------------"
echo "Activating conda environment"
if [ ! -d "/anvil/scratch/x-ochaturvedi/.conda/envs/running-env-"$environment_name"" ]; then
    echo "Environment failed to create. Skipping execution."
    exit 1
fi
if [ ! -d "/anvil/scratch/x-ochaturvedi/.conda/envs/scoring-env-"$environment_name"" ]; then
    echo "Environment failed to create. Skipping scoring."
    exit 1
fi

echo "--------------------------------------------------"
echo "Running the model: $1"
MODEL_DIR="$1"
mkdir -p "./$1/research_output_$dataset_name"
cd "$1"
shopt -s nullglob

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Started running model $1 for dataset $dataset_name\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null

touch "./details_$dataset_name.txt"
{
    echo "Model Name: $model_name"
    echo "Dataset Name: $2"
    echo ""
    echo ""
} >"./details_$dataset_name.txt"

# Temporary file to store per-file runtimes
temp_dir="./temp_$dataset_name"
rm -rf "$temp_dir"
mkdir "$temp_dir"
export temp_dir

# Function to process one .mp3 file
process_file() {
    source "$(conda info --base)/etc/profile.d/conda.sh"

    echo "Processing file: $1"
    local file="$1"
    local base_name=$(basename "$file" .$audio_type)

    local reference_file=$(realpath "${file%.$audio_type}.mid")
    local transcription_path=".$MODEL_DIR/research_output_$dataset_name/${base_name}.mid"
    local runtime_file="$temp_dir/${base_name}.runtime"
    local fmeasure_file="$temp_dir/${base_name}.fmeasure"

    local duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")

    conda activate /anvil/scratch/x-ochaturvedi/.conda/envs/running-env-"$environment_name"

    local start_time=$(date +%s.%N)

    python3 main.py -i "$file" -o "$transcription_path"

    local end_time=$(date +%s.%N)

    conda deactivate

    # Runtime calculation
    local runtime=$(echo "$end_time - $start_time" | bc)
    echo "$runtime" >"$runtime_file"
    echo "Processed ${base_name}.$audio_type in $runtime seconds"

    # Scoring
    if [[ ! -f "$reference_file" ]]; then
        reference_file=$(realpath "${file%.$audio_type}.midi")
    fi
    if [[ ! -f "$reference_file" ]]; then
        echo "Reference MIDI not found for $file, skipping scoring."
        echo "MISSING_REF" >"$fmeasure_file"
        return
    fi

    if [[ ! -f "$transcription_path" ]]; then
        echo "Transcription MIDI not found at $transcription_path, skipping scoring."
        echo "MISSING_TRANS" >"$fmeasure_file"
        return
    fi

    conda activate /anvil/scratch/x-ochaturvedi/.conda/envs/scoring-env-"$environment_name"

    local output=$(python3 ../scoring.py --reference "$reference_file" --transcription "$transcription_path")

    {
        printf '%s\n' "$(basename "$file")"
        printf 'Duration: %s seconds\n' "$duration"
        printf '%s\n' "$output"
        printf 'Runtime: %f seconds\n\n' "$runtime"
    } >>"./details_$dataset_name.txt"

    # Extract F-measure and store it
    local fmeasure=$(echo "$output" | grep -m1 "F-measure:" | awk '{print $2}')

    if [[ "$fmeasure" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "$fmeasure" >"$fmeasure_file"
    else
        echo "INVALID" >"$fmeasure_file"
        echo "Warning: Invalid F-measure detected: '$fmeasure' for $file"
    fi

    conda deactivate
}

export -f process_file

# Determine number of parallel jobs
cores=4
if command -v nproc &>/dev/null; then
    cores=$(nproc)
elif [[ "$OSTYPE" == "darwin"* ]]; then
    cores=$(sysctl -n hw.ncpu)
fi

# Run jobs in parallel using GNU Parallel
find "$3" -type f -name "*.$audio_type" | parallel -j "$cores" process_file

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
    printf 'Average F-measure per file: %s\n' "$avg_fmeasure" >>"./details_$dataset_name.txt"
else
    echo "No valid F-measures collected."
    echo "No valid F-measures collected." >>"./details_$dataset_name.txt"
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
    printf 'Average runtime per file: %s seconds\n' "$avg_runtime" >>"./details_$dataset_name.txt"
else
    echo "No valid runtimes collected or no files processed."
    echo "No valid runtimes collected or no files processed." >>"./details_$dataset_name.txt"
fi

# Clean up
rm -rf "$temp_dir"
cd ..

conda deactivate
conda clean --all --yes -q
rm -rf /anvil/scratch/x-ochaturvedi/.conda/envs

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Finished running model $1 for dataset $dataset_name\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null

# UPLOAD.SH

echo "--------------------------------------------------"
echo "Deleting any existing conda environment"
conda env remove -p /anvil/scratch/x-ochaturvedi/.conda/envs/upload-env-"$environment_name" -y

echo "--------------------------------------------------"
echo "Creating conda environment"
conda create -y -q --prefix /anvil/scratch/x-ochaturvedi/.conda/envs/upload-env-"$environment_name" python=3.10 pip pydrive2

echo "--------------------------------------------------"
echo "Activating conda environment"
if [ ! -d "/anvil/scratch/x-ochaturvedi/.conda/envs/upload-env-"$environment_name"" ]; then
    echo "Environment failed to create. Skipping upload."
    exit 1
fi
conda activate /anvil/scratch/x-ochaturvedi/.conda/envs/upload-env-"$environment_name"

echo "--------------------------------------------------"
echo "Uploading the output files"

OUTPUT_DIR="$1/research_output_$dataset_name"
OUTPUT_DIR=$(realpath "$OUTPUT_DIR")
export OUTPUT_DIR
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Error: Output directory $OUTPUT_DIR does not exist!"
    exit 1
fi

mv "$1/details_$dataset_name.txt" "$OUTPUT_DIR"/details_$dataset_name.txt
mv "$1/research_output/${2}_slurm_output.txt" "$OUTPUT_DIR"/

python ./upload.py --main-folder="11zBLIit-Cg7Tu5KHJXZBvaUauFr5Dtbc" --model-name="$MODEL_DIR" --dataset-name="$2" --local-directory="$OUTPUT_DIR"

conda deactivate
conda clean --all --yes -q

rm -rf /anvil/scratch/x-ochaturvedi/.conda/envs

echo "--------------------------------------------------"
echo "Script execution completed!"

end_time=$(date +%s.%N)
overall_runtime=$(echo "scale=2; $end_time - $start_time" | bc)

hours=$(echo "$overall_runtime / 3600" | bc)
minutes=$(echo "($overall_runtime % 3600) / 60" | bc)
seconds=$(echo "$overall_runtime % 60" | bc | cut -d'.' -f1)

overall_runtime_formatted=$(printf '%02d:%02d:%02d' "$hours" "$minutes" "$seconds")
echo "Total runtime: $overall_runtime_formatted"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Finished script for model $1 and dataset $dataset_name. Total runtime: $overall_runtime_formatted\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
