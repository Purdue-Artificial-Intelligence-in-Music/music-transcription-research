#!/bin/bash
#SBATCH -A yunglu-k
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=02:30:00

module load parallel
module load ffmpeg

# Download the dataset
wget -O slakh2100_flac_redux.tar.gz "https://zenodo.org/record/4599666/files/slakh2100_flac_redux.tar.gz?download=1" >/dev/null

# Extract the dataset
mkdir -p "slakh2100"
tar -xzf slakh2100_flac_redux.tar.gz --strip-components=1 -C "slakh2100" >/dev/null

# Remove the 'omitted' folder
rm -rf "slakh2100/omitted"

# Delete all non-MIDI essential files
find slakh2100 -type f ! -name "*.mid" -delete
find slakh2100 -type f -name "*.mid" ! -name "all_src.mid" -delete
find slakh2100 -type d -empty -delete

# Rename all_src.mid files to the parent directory name
find slakh2100 -type f -name "all_src.mid" | while read -r midi_file; do
    parent_dir=$(dirname "$midi_file")
    new_name="${parent_dir##*/}.mid"
    mv "$midi_file" "$parent_dir/$new_name"
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
find slakh2100 -type f -name "*.mid" | sort | parallel --jobs 32 convert_midi {}

# Clean up
rm -f slakh2100_flac_redux.tar.gz "$FS_DEFINITION" "$FS_CONTAINER"

# Generate a sorted list of all input files
find "$(realpath ./slakh2100)" -type f -name "*.wav" | sort >slakh2100.txt

# Print the number of .MID files and then .WAV files
echo "Number of .MID files: $(find slakh2100 -type f -name "*.mid" | wc -l)"
echo "Number of .WAV files: $(find slakh2100 -type f -name "*.wav" | wc -l)"
