#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00

module load ffmpeg
module load parallel

# Clone the BiMMuDa repository and keep relevant files
git clone --depth=1 https://github.com/madelinehamilton/BiMMuDa.git BiMMuDa
find BiMMuDa -mindepth 1 -maxdepth 1 ! -name "bimmuda_dataset" -exec rm -rf {} +
if [ -d BiMMuDa/bimmuda_dataset ]; then
    mv BiMMuDa/bimmuda_dataset/* BiMMuDa/
    rmdir BiMMuDa/bimmuda_dataset
fi

# Remove songs with no main melody
NO_MELODY_DIRS=(
    "1992/2"
    "1992/3"
    "1993/2"
    "1997/5"
    "2017/4"
)
for bad_dir in "${NO_MELODY_DIRS[@]}"; do
    rm -rf "BiMMuDa/$bad_dir"
done

# Delete all non-MIDI essential files
find BiMMuDa -type f -name "*.mid" ! -name "*_full.mid" -delete
find BiMMuDa -type f -name "*.mscz" -delete
find BiMMuDa -type f -name "*.txt" -delete

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
find BiMMuDa -type f -name "*.mid" | parallel --jobs 32 convert_midi {}

# Clean up
rm -f "$FS_DEFINITION" "$FS_CONTAINER"

# Generate a sorted list of all input files
find "$(realpath "BiMMuDa")" -type f -name "*.wav" | sort >BiMMuDa.txt

# Print the number of .MID files and then .WAV files
echo "Number of .MID files: $(find BiMMuDa -type f -name "*.mid" | wc -l)"
echo "Number of .WAV files: $(find BiMMuDa -type f -name "*.wav" | wc -l)"