#!/bin/bash
#SBATCH -A yunglu-k
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=1-00:00:00

# RUN.SH

echo "--------------------------------------------------"
echo "Grading model: $1"
echo "Processing dataset: $2"
echo "Searching in: $3"

source /etc/profile.d/modules.sh
module --force purge
module load external
module load ffmpeg
module load conda

conda clean --all --yes

# Check for internet access
if ! ping -c 1 repo.anaconda.com &>/dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -d "No internet access. Cannot create Conda environment. Exiting." -H "Title: Error" -H "Priority: urgent" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

echo "--------------------------------------------------"
echo "Deleting any existing conda environment"
conda env remove -p /scratch/gilbreth/ochaturv/.conda/envs/running-env-"$environment_name" -y
conda env remove -p /scratch/gilbreth/ochaturv/.conda/envs/scoring-env-"$environment_name" -y
rm -rf /scratch/gilbreth/ochaturv/.conda/envs/running-env-"$environment_name"
rm -rf /scratch/gilbreth/ochaturv/.conda/envs/scoring-env-"$environment_name"

echo "--------------------------------------------------"
echo "Creating conda environment"
cd /scratch/gilbreth/ochaturv/research || {
    echo "Failed to change directory to /scratch/gilbreth/ochaturv/research"
    exit 1
}
if [ ! -f "./$1/environment.yml" ]; then
    echo "Error: environment.yml file not found for model $1"
    exit 1
fi
conda env create -q -f "./$1/environment.yml" --prefix /scratch/gilbreth/ochaturv/.conda/envs/running-env-"$environment_name"
conda create -y -q --prefix /scratch/gilbreth/ochaturv/.conda/envs/scoring-env-"$environment_name"

echo "--------------------------------------------------"
echo "Activating conda environment"
if [ ! -d "/scratch/gilbreth/ochaturv/.conda/envs/running-env-"$environment_name"" ]; then
    echo "Environment failed to create. Skipping execution."
    exit 1
fi
if [ ! -d "/scratch/gilbreth/ochaturv/.conda/envs/scoring-env-"$environment_name"" ]; then
    echo "Environment failed to create. Skipping scoring."
    exit 1
fi
# conda activate /scratch/gilbreth/ochaturv/.conda/envs/running-env-"$environment_name"
conda activate /scratch/gilbreth/ochaturv/.conda/envs/scoring-env-"$environment_name"
pip install -q mir_eval pretty_midi numpy pyyaml
conda deactivate

echo "--------------------------------------------------"
echo "Running the model: $1"
MODEL_DIR="$1"
mkdir -p "./$1/research_output"
cd "$1"
shopt -s nullglob

# Temporary file to store per-file runtimes
runtimes_dir="./runtimes"
rm -rf "$runtimes_dir"
mkdir "$runtimes_dir"
export runtimes_dir

# Function to process one .mp3 file
process_file() {
    source "$(conda info --base)/etc/profile.d/conda.sh"

    echo "Processing file: $1"
    local file="$1"
    local base_name
    base_name=$(basename "$file" .wav)

    # Paths
    local reference_file=$(realpath "${file%.wav}.midi")
    local transcription_path=".$MODEL_DIR/research_output_$dataset_name/${base_name}.midi"
    local runtime_file="$temp_dir/${base_name}.runtime"
    local fmeasure_file="$temp_dir/${base_name}.fmeasure"

    echo "Reference file: $reference_file"
    echo "Transcription path: $transcription_path"
    echo "Runtime file: $runtime_file"
    echo "F-measure file: $fmeasure_file"
    echo "Temp directory: $temp_dir"

    conda activate /scratch/gilbreth/ochaturv/.conda/envs/running-env-"$environment_name"

    local start_time
    start_time=$(date +%s.%N)

    python3 main.py -i "$file" -o "$transcription_path"

    local end_time
    end_time=$(date +%s.%N)

    conda deactivate

    # Runtime calculation
    local runtime
    runtime=$(echo "$end_time - $start_time" | bc)
    echo "$runtime" >"$runtime_file"
    echo "Processed ${base_name}.wav in $runtime seconds"

    # Scoring
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

    conda activate /scratch/gilbreth/ochaturv/.conda/envs/scoring-env-"$environment_name"

    local output
    output=$(python3 ../scoring.py --reference "$reference_file" --transcription "$transcription_path")

    {
        printf '%s\n' "$(basename "$file")"
        printf '%s\n' "$output"
        printf 'Runtime: %f seconds\n\n' "$runtime"
    } >>"./details_$dataset_name.txt"

    # Extract F-measure and store it
    local fmeasure
    fmeasure=$(echo "$output" | grep -m1 "F-measure:" | awk '{print $2}')

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
find "$3" -type f -name '*.wav' | parallel -j "$cores" process_file

# Compute average runtime using a loop
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
    printf 'Average runtime per file: %s seconds\n\n' "$avg_runtime" >>"./$MODEL_DIR/details.txt"
else
    echo "No valid runtimes collected or no files processed."
fi

    fi
done
else
fi


conda deactivate
conda clean --all --yes -q

# CONVERSION.SH

if ! command -v singularity &>/dev/null; then
    echo "Error: Singularity is not installed. Please contact your system administrator."
    exit 1
fi

MUSESCORE_CONTAINER="musescore.sif"
MUSESCORE_DEFINITION="musescore.def"

# Create the Singularity definition file dynamically
cat <<EOF >$MUSESCORE_DEFINITION
BootStrap: docker
From: ubuntu:22.04

%post
    apt update && apt install -y musescore ffmpeg curl imagemagick
    echo "MuseScore and ImageMagick Installed"

%runscript
    export QT_QPA_PLATFORM=offscreen
    exec /usr/bin/mscore "\$@"
EOF

# Build the Singularity container (force overwrite if it exists)
singularity build --force "$MUSESCORE_CONTAINER" "$MUSESCORE_DEFINITION" >/dev/null 2>&1

export XDG_RUNTIME_DIR=/tmp/runtime-ochaturv

echo "--------------------------------------------------"
echo "Converting the output files"
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Error: Output directory $OUTPUT_DIR does not exist!"
    exit 1
fi

# Convert each .mid file using MuseScore inside Singularity (headless mode)
for file in "$OUTPUT_DIR"/*.mid; do
    # Generate PDF using MuseScore
    singularity exec "$MUSESCORE_CONTAINER" env QT_QPA_PLATFORM=offscreen mscore -o "$OUTPUT_DIR/$(basename "$file" .mid).pdf" "$file"

    # Fix the ICC profile issue using ImageMagick's mogrify
    singularity exec "$MUSESCORE_CONTAINER" mogrify -strip "$OUTPUT_DIR/$(basename "$file" .mid).pdf"
done

rm -f "$MUSESCORE_CONTAINER" "$MUSESCORE_DEFINITION"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Finished scoring model: $1\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Finished scoring model: $1" -H "Title: Finished scoring model" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt

# UPLOAD.SH

echo "--------------------------------------------------"
echo "Deleting any existing conda environment"
conda env remove -p /scratch/gilbreth/ochaturv/.conda/envs/upload-env -y

echo "--------------------------------------------------"
echo "Creating conda environment"
conda create -y -q --prefix /scratch/gilbreth/ochaturv/.conda/envs/upload-env

echo "--------------------------------------------------"
echo "Activating conda environment"
if [ ! -d "/scratch/gilbreth/ochaturv/.conda/envs/upload-env" ]; then
    echo "Environment failed to create. Skipping upload."
    exit 1
fi
conda activate /scratch/gilbreth/ochaturv/.conda/envs/upload-env
pip install -q pydrive2

echo "--------------------------------------------------"
echo "Uploading the output files"

mv "$1/details.txt" "$OUTPUT_DIR"/details.txt

python ./upload.py --main-folder="11zBLIit-Cg7Tu5KHJXZBvaUauFr5Dtbc" --model-name="$MODEL_DIR" --dataset-name="$2" --local-directory="$OUTPUT_DIR"

conda deactivate
conda clean --all --yes -q

echo "--------------------------------------------------"
echo "Script execution completed!"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Finished script for model: $1\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Finished script for model: $1" -H "Title: Finished script for model" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
