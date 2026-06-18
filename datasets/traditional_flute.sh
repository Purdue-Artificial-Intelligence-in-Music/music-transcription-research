#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-40gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --mem=240G
#SBATCH --time=01:30:00

rm -rf traditional_flute

source /etc/profile.d/modules.sh
module load external
module load parallel ffmpeg

KAGGLE_URL="https://www.kaggle.com/api/v1/datasets/download/jbraga/traditional-flute-dataset"
ZIP_FILE="traditional_flute.zip"

# Download the Traditional Flute dataset (requires ~/.kaggle/kaggle.json)
wget -q --auth-no-challenge -O "$ZIP_FILE" "$KAGGLE_URL"
unzip -q "$ZIP_FILE" -d traditional_flute
rm -f "$ZIP_FILE"

# Flatten: move all MIDI files from nested score/ directories to traditional_flute/
find traditional_flute -type f \( -name "*.midi" -o -name "*.mid" \) -exec mv {} traditional_flute/ \;
find traditional_flute -mindepth 1 -type d -exec rm -rf {} +

# Rename .midi to .mid
find traditional_flute -type f -name "*.midi" | while read -r file; do
    mv "$file" "${file%.midi}.mid"
done

echo "Found $(find traditional_flute -type f -name "*.mid" | wc -l) MIDI files."

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

    if singularity exec "$FS_CONTAINER" fluidsynth -ni "$SF_PATH" "$midi_path" -F "$tmp" -r 44100 2>/dev/null; then
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

export -f convert_midi
export FS_CONTAINER
export SF_PATH

find traditional_flute -type f -name "*.mid" | parallel --jobs 32 convert_midi {}

rm -f "$FS_DEFINITION" "$FS_CONTAINER"

# Generate a sorted list of all input files
find "$(realpath traditional_flute)" -type f -name "*.wav" | sort >traditional_flute.txt

echo "Number of .MID files: $(find traditional_flute -type f -name "*.mid" | wc -l)"
echo "Number of .WAV files: $(find traditional_flute -type f -name "*.wav" | wc -l)"
