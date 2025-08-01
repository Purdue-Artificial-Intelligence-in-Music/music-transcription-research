#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00

module load external
module load conda
module load ffmpeg
module load parallel

# Ensure gdown is installed
if ! command -v gdown &>/dev/null; then
    pip install gdown
fi

# Download and unzip the XMIDI dataset from Google Drive
gdown 1qDkSH31x7jN8X-2RyzB9wuxGji4QxYyA --output xmidi_dataset.zip
unzip xmidi_dataset.zip -d xmidi_dataset

# Rename all .midi files to .mid
echo "Renaming .midi files to .mid..."
find xmidi_dataset -type f -name "*.midi" | while read -r file; do
    mv "$file" "${file%.midi}.mid"
done

FS_CONTAINER="fluidsynth.sif"
FS_DEFINITION="fluidsynth.def"

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

    # Download the FluidR3 GM soundfont
    mkdir -p /usr/share/sounds/sf2
    wget -O /tmp/FluidR3_GM.zip https://keymusician01.s3.amazonaws.com/FluidR3_GM.zip
    unzip -o /tmp/FluidR3_GM.zip -d /usr/share/sounds/sf2

%environment
    export SOUND_FONT=/usr/share/sounds/sf2/FluidR3_GM.sf2

%runscript
    exec fluidsynth -ni "\$SOUND_FONT" "\$@"
EOF

# Build Singularity container
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
find ./xmidi_dataset -type f -name "*.mid" | parallel -j 32 convert_midi {}

# Clean up
rm "$FS_DEFINITION" "$FS_CONTAINER"

# Generate a sorted list of all input files
find "$(realpath ./xmidi_dataset)" -type f -name "*.wav" | sort >xmidi_dataset.txt
