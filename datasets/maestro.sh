#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00

module load ffmpeg
module load parallel

# Download the zip file
wget --progress=bar:force -O maestro-v3.0.0.zip https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip

# Verify the file integrity using SHA-256
echo "70470ee253295c8d2c71e6d9d4a815189e35c89624b76d22fce5a019d5dde12c maestro-v3.0.0.zip" | sha256sum -c -

# Unzip the dataset
unzip maestro-v3.0.0.zip

# Rename all .midi files to .mid
find maestro-v3.0.0 -type f -name "*.midi" | while read -r file; do
    mv "$file" "${file%.midi}.mid"
done

# Create a Singularity container for FluidSynth
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
find maestro-v3.0.0 -type f -name "*.mid" | parallel --jobs 32 convert_midi {}

# Clean up
rm -f maestro-v3.0.0.zip "$FS_DEFINITION" "$FS_CONTAINER"

# Generate a sorted list of all input files
find "$(realpath ./maestro-v3.0.0)" -type f -name "*.wav" | sort >maestro-v3.0.0.txt

# Print the number of .MID files and then .WAV files
echo "Number of .MID files: $(find maestro-v3.0.0 -type f -name "*.mid" | wc -l)"
echo "Number of .WAV files: $(find maestro-v3.0.0 -type f -name "*.wav" | wc -l)"
