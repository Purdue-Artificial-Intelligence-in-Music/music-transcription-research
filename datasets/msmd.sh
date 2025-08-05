#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=03:00:00

module load ffmpeg
module load parallel

ZENODO_URL="https://zenodo.org/record/2597505/files/msmd_aug_v1-1_no-audio.zip?download=1"
ZIP_FILE="msmd_aug_v1-1_no-audio.zip"
TARGET_DIR="msmd_data"
EXPECTED_SHA256="c3b4f3d2f04fd8709394c93494ddc99eb0b2e2f8d1db5f5465e63cd1ed255cf0"

rm -rf "$TARGET_DIR"

# Download and unzip the MSMD dataset
wget --no-verbose -O "$ZIP_FILE" "$ZENODO_URL"
TEMP_DIR=$(mktemp -d)
UNZIP_DISABLE_ZIPBOMB_DETECTION=TRUE unzip -q "$ZIP_FILE" -d "$TEMP_DIR"

mkdir -p "$TARGET_DIR"
mv "$TEMP_DIR"/msmd_aug_v1-1_no-audio/* "$TARGET_DIR"/

rm -rf "$TEMP_DIR"

# Download and extract the "success" entries of the all_pieces.yaml file
YAML_FILE="all_pieces.yaml"
wget -O "$YAML_FILE" https://raw.githubusercontent.com/CPJKU/msmd/refs/heads/master/msmd/splits/all_pieces.yaml
SUCCESS_LIST=$(mktemp)
awk '
  /^success:/ {flag=1; next}
  /^failed:|^problem:/ {flag=0}
  flag && /^- / {print substr($0, 3)}
' "$YAML_FILE" | tr -d '\r' > "$SUCCESS_LIST"

echo "Success list count: $(wc -l < "$SUCCESS_LIST")"

# Remove any directories that are not in the success list
find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -type d | while read -r dir; do
    base=$(basename "$dir" | tr -d '\r' | sed 's:/*$::')
    if ! grep -Fxq "$base" "$SUCCESS_LIST"; then
        rm -rf "$dir"
    fi
done

# Remove the Da capo problematic pieces explicitly (12 total)
DA_CAPO_DIRS=(
    "BachJS__BWV817__bach-french-suite-6-polonaise"
    "Traditional__traditioner_af_swenska_folk_dansar.1.16__traditioner_af_swenska_folk_dansar.1.16"
    "Traditional__traditioner_af_swenska_folk_dansar.1.18__traditioner_af_swenska_folk_dansar.1.18"
    "Traditional__traditioner_af_swenska_folk_dansar.1.9__traditioner_af_swenska_folk_dansar.1.9"
    "Traditional__traditioner_af_swenska_folk_dansar.3.1__traditioner_af_swenska_folk_dansar.3.1"
    "Traditional__traditioner_af_swenska_folk_dansar.3.5__traditioner_af_swenska_folk_dansar.3.5"
    "FischerJKF__Fischer_EratoAllemande__Fischer_EratoAllemande"
    "MozartWA__KV331__KV331_2_1_menuetto"
    "SchubertF__D935__SchubertF-D935-2-Impromptu"
    "Traditional__traditioner_af_swenska_folk_dansar.1.11__traditioner_af_swenska_folk_dansar.1.11"
    "Traditional__traditioner_af_swenska_folk_dansar.1.33__traditioner_af_swenska_folk_dansar.1.33"
    "Traditional__traditioner_af_swenska_folk_dansar.2.30__traditioner_af_swenska_folk_dansar.2.30"
)
for bad_dir in "${DA_CAPO_DIRS[@]}"; do
    rm -rf "$TARGET_DIR/$bad_dir"
done

# Delete all non-MIDI files and empty directories
find "$TARGET_DIR" -type f ! \( -iname "*.mid" -o -iname "*.midi" \) -delete
find "$TARGET_DIR" -type d \( -name "scores" -o -name "performances" \) -exec rm -rf {} +
find "$TARGET_DIR" -type f \( -iname "*.ly" -o -iname "*.norm.ly" -o -iname "*.yml" \) -delete

# Rename .midi files to .mid
find "$TARGET_DIR" -type f -iname "*.midi" | while read -r midi_file; do
    mv "$midi_file" "${midi_file%.midi}.mid"
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
find "$TARGET_DIR" -type f -iname "*.mid" | parallel -j 32 convert_midi {}

# Clean up
rm -f "$FS_DEFINITION" "$FS_CONTAINER" "$ZIP_FILE" "$YAML_FILE" "$SUCCESS_LIST"

# Generate a sorted list of all input files
find "$(realpath "$TARGET_DIR")" -type f -name "*.wav" | sort >msmd_data.txt