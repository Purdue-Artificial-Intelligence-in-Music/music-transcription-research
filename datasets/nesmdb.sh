#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-80gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --mem=240G
#SBATCH --time=01:30:00

source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"
load_modules

# Build into the cluster's dataset directory so the generated .txt file list
# points at the canonical location referenced by datasets.json.
mkdir -p "$DATA_ROOT"
cd "$DATA_ROOT"

# Start clean so re-runs don't merge with a previous build
rm -rf nesmdb nesmdb.txt nesmdb-midi.tar.gz

# Download the NES-MDB MIDI transcriptions. We render these with FluidSynth (the
# same controlled pipeline used for every other dataset) rather than the NES VGM
# synthesizer, so all datasets share identical acoustic conditions.
pip install gdown -q
gdown 1w2uo1Cmio4gz6nGUhZOtzF54kPkoKyo7 --output nesmdb-midi.tar.gz
mkdir -p nesmdb
tar -xzf nesmdb-midi.tar.gz -C nesmdb

# Normalize extensions to .mid (keep directory structure so each .wav sits next
# to its reference .mid, as the scoring step expects)
find nesmdb -type f -iname "*.midi" | while read -r file; do
    mv "$file" "${file%.midi}.mid"
done

# Create a Singularity container for FluidSynth (unique name per job so
# concurrent dataset builds don't delete each other's container)
FS_CONTAINER="fluidsynth_${SLURM_JOB_ID:-$$}.sif"
FS_DEFINITION="fluidsynth_${SLURM_JOB_ID:-$$}.def"
cat <<EOF >$FS_DEFINITION
BootStrap: docker
From: ubuntu:22.04

%post
    apt-get update && apt-get install -y \
        fluidsynth \
        wget \
        ffmpeg \
        unzip \
        curl \
        ca-certificates

    # Download the FluidR3 GM soundfont (GitHub mirror; the S3 source 403s on Anvil)
    mkdir -p /usr/share/sounds/sf2
    wget -O /usr/share/sounds/sf2/FluidR3_GM.sf2 "https://raw.githubusercontent.com/urish/cinto/master/media/FluidR3%20GM.sf2"

%environment
    export SOUND_FONT=/usr/share/sounds/sf2/FluidR3_GM.sf2

%runscript
    exec fluidsynth -ni "\$SOUND_FONT" "\$@"
EOF
singularity build --force "$FS_CONTAINER" "$FS_DEFINITION" >/dev/null
SF_PATH="/usr/share/sounds/sf2/FluidR3_GM.sf2"

# Function to convert a single MIDI file
convert_midi() {
    local midi_path="$1"
    local out="${midi_path%.mid}.wav"
    local tmp="${out%.wav}_tmp.wav"

    echo "Processing: $midi_path"

    # Convert MIDI to WAV using FluidSynth
    if singularity exec "$FS_CONTAINER" fluidsynth -ni "$SF_PATH" "$midi_path" -F "$tmp" -r 44100 2>/dev/null; then
        # Convert to mono 44.1kHz with ffmpeg
        if ffmpeg -loglevel error -y -i "$tmp" -ac 1 -ar 44100 "$out" 2>/dev/null; then
            rm "$tmp"
            echo "Converted: $out"
        else
            rm -f "$tmp"
            echo "FFmpeg failed on: $midi_path"
        fi
    else
        echo "FluidSynth failed on: $midi_path"
    fi
}

# Export the function and variables for parallel
export -f convert_midi
export FS_CONTAINER
export SF_PATH

# Run conversion in parallel (using all available CPU cores)
find nesmdb -type f -name "*.mid" | parallel -j 32 convert_midi {}

# Clean up
rm -f "$FS_DEFINITION" "$FS_CONTAINER" nesmdb-midi.tar.gz

# Generate a sorted list of all input files
find "$(realpath nesmdb)" -type f -name "*.wav" | sort >nesmdb.txt

# Print the number of .MID files and then .WAV files
echo "Number of .MID files: $(find nesmdb -type f -name "*.mid" | wc -l)"
echo "Number of .WAV files: $(find nesmdb -type f -name "*.wav" | wc -l)"

# Real-time completion notification
notify "**[$CLUSTER] Dataset build complete:** \`NESMDB\` — \`$(wc -l < nesmdb.txt 2>/dev/null || echo 0)\` files"
