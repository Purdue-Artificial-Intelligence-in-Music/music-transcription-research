#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=03:59:00

# RUN.SH

echo "--------------------------------------------------"
echo "Grading model: $1"

source /etc/profile.d/modules.sh
module --force purge
module load external
module load ffmpeg
module load conda

# Check for internet access
if ! ping -c 1 repo.anaconda.com &>/dev/null; then
    echo "No internet access. Cannot create Conda environment. Exiting."
    curl -d "No internet access. Cannot create Conda environment. Exiting." -H "Title: Error" -H "Priority: urgent" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
    curl -s -X POST -H "Content-Type: application/json" -d '{"content": "URGENT: NO INTERNET ACCESS FOR CONDA CREATION", "avatar_url": "https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"}' https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    exit 1
fi

CONDA_ENV_PATH="$HOME/.conda/envs/running-env"
if [ -d "$CONDA_ENV_PATH" ] && [ ! -f "$CONDA_ENV_PATH/bin/activate" ]; then
    rm -rf "$CONDA_ENV_PATH"
fi

echo "--------------------------------------------------"
echo "Creating conda environment"
conda env create -q -f "./$1/environment.yml" --name running-env
source activate running-env

echo "--------------------------------------------------"
echo "Running the model: $1"
mkdir -p "./$1/competition_output"
cd "$1"
shopt -s nullglob

# Store runtimes in an array
declare -a runtimes

# Loop through each .mp3 file and time the execution
for file in ../evaluation_mp3/*.mp3; do
    base_name=$(basename "$file" .mp3)
    start_time=$(date +%s.%N)

    python3 main.py -i "$file" -o "competition_output/${base_name}.mid"

    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    runtimes+=("$runtime")

    echo "Processed ${base_name}.mp3 in $runtime seconds"
done

# Compute the average runtime
total=0
for time in "${runtimes[@]}"; do
    total=$(echo "$total + $time" | bc)
done

num_files=${#runtimes[@]}
if [ "$num_files" -gt 0 ]; then
    avg_runtime=$(echo "scale=4; $total / $num_files" | bc)
    echo "--------------------------------------------------"
    echo "Average runtime per file: $avg_runtime seconds"
    printf 'Average runtime per file: %s seconds\n\n' "$avg_runtime" >>"./details.txt"
else
    echo "No files processed."
    echo "No files processed." >>"./details.txt"
fi

cd ..

conda deactivate
if conda env list | grep -q "running-env"; then
    echo "Removing conda environment 'running-env'"
    conda env remove -y -q --name running-env
fi
conda clean --all --yes -q

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Finished running model: $1\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Finished running model: $1" -H "Title: Finished running model" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt

# SCORING.SH

CONDA_ENV_PATH="$HOME/.conda/envs/scoring-env"
if [ -d "$CONDA_ENV_PATH" ] && [ ! -f "$CONDA_ENV_PATH/bin/activate" ]; then
    rm -rf "$CONDA_ENV_PATH"
fi

echo "--------------------------------------------------"
echo "Creating conda environment"
conda create -y -q --name scoring-env
source activate scoring-env
pip install -q mir_eval pretty_midi numpy pyyaml

echo "--------------------------------------------------"
echo "Scoring the output files"

TEAM_DIR="$1"
OUTPUT_DIR="$TEAM_DIR/competition_output"

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Error: Output directory $OUTPUT_DIR does not exist!"
    exit 1
fi

# Store scores in an array
declare -a scores

# Loop through each .mid file and extract the F-measure score
for file in ./evaluation_mid/*.mid; do
    output=$(python3 ./scoring.py --reference $file --transcription "$OUTPUT_DIR"/$(basename "$file"))
    printf '%s\n' "$(basename "$file")" >>"./$1/details.txt"
    printf '%s\n\n' "$output" >>"./$1/details.txt"

    # Extract the F-measure score using grep and awk
    fmeasure=$(echo "$output" | grep -m1 "F-measure:" | awk '{print $2}')

    # Ensure the extracted value is numeric
    if [[ "$fmeasure" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        scores+=("$fmeasure")
    else
        echo "Warning: Invalid F-measure detected: '$fmeasure' in $file" >>"./$1/details.txt"
    fi
done

# Compute the average score
total=0
valid_scores=0

for score in "${scores[@]}"; do
    if [[ "$score" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        total=$(echo "$total + $score" | bc)
        ((valid_scores++))
    fi
done

# Only compute the average if we have valid scores
if [ "$valid_scores" -gt 0 ]; then
    avg_score=$(echo "scale=4; $total / $valid_scores" | bc)
    echo "--------------------------------------------------"
    echo "Average F-measure per file: $avg_score"
    printf 'Average F-measure per file: %s\n' "$avg_score" >>"./$1/details.txt"
else
    echo "No valid F-measure scores found! Check the MIDI output." >>"./$1/details.txt"
fi

conda deactivate
if conda env list | grep -q "scoring-env"; then
    echo "Removing conda environment 'scoring-env'"
    conda env remove -y -q --name scoring-env
fi
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
TEAM_DIR="$1"
OUTPUT_DIR="$TEAM_DIR/competition_output"

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

CONDA_ENV_PATH="$HOME/.conda/envs/upload-env"
if [ -d "$CONDA_ENV_PATH" ] && [ ! -f "$CONDA_ENV_PATH/bin/activate" ]; then
    echo "Removing invalid conda environment at $CONDA_ENV_PATH"
    rm -rf "$CONDA_ENV_PATH"
fi

echo "--------------------------------------------------"
echo "Creating conda environment"
conda create -y -q --name upload-env
source activate upload-env
pip install -q pydrive2

echo "--------------------------------------------------"
echo "Uploading the output files"
echo "Participants, please let us know if you notice any issues with the autnomous grading system. For questions or concerns, please reach out to us via this email: ochaturv@purdue.edu."
echo "--------------------------------------------------"
echo "Script execution completed!"

TEAM_DIR="$1"
OUTPUT_DIR="$TEAM_DIR/competition_output"
GDRIVE_PARENT_FOLDER_ID="1i1xahjfreIqTozgF4dieFYPo3ezrDzQP"

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Error: Output directory $OUTPUT_DIR does not exist!"
    exit 1
fi

mv "$1/details.txt" "$OUTPUT_DIR"/details.txt

MP3_DIR="evaluation_mp3"
if [ -d "$MP3_DIR" ]; then
    for file in "$MP3_DIR"/*; do
        [ -f "$file" ] && cp "$file" "$OUTPUT_DIR"/
    done
fi

python ./upload.py --main-folder="$GDRIVE_PARENT_FOLDER_ID" --team-name="$TEAM_DIR" --local-directory="$OUTPUT_DIR"

conda deactivate
if conda env list | grep -q "upload-env"; then
    echo "Removing conda environment 'upload-env'"
    conda env remove -y -q --name upload-env
fi
conda clean --all --yes -q

echo "--------------------------------------------------"
echo "Script execution completed!"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Finished script for model: $1\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Finished script for model: $1" -H "Title: Finished script for model" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
