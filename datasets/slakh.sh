#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-80gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --mem=240G
#SBATCH --time=02:30:00

source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"
load_modules

# Build into the cluster's dataset directory so the generated .txt file list
# points at the canonical location referenced by datasets.json.
mkdir -p "$DATA_ROOT"
cd "$DATA_ROOT"

# Start clean so re-runs don't merge with a previous build
rm -rf slakh2100 slakh2100.txt slakh2100_flac_redux.tar.gz

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

    # FluidSynth can exit 0 yet render silence, leaving a ~200-byte (empty) WAV
    # that downstream models can't transcribe. Verify the output is non-trivial
    # and retry once if it isn't.
    local attempt sz
    for attempt in 1 2; do
        if singularity exec "$FS_CONTAINER" fluidsynth -ni "$SF_PATH" "$midi_path" -F "$tmp" -r 44100 2>/dev/null \
            && ffmpeg -loglevel error -y -i "$tmp" -ac 1 -ar 44100 "$out" 2>/dev/null; then
            rm -f "$tmp"
            sz=$(stat -c%s "$out" 2>/dev/null || stat -f%z "$out" 2>/dev/null)
            if [[ -n "$sz" && "$sz" -ge 2048 ]]; then
                echo "Converted: $out"
                return
            fi
            echo "Empty WAV (${sz}B) for $midi_path (attempt $attempt)"
        else
            rm -f "$tmp"
            echo "FluidSynth/ffmpeg failed on: $midi_path (attempt $attempt)"
        fi
    done
    echo "WARN: could not synthesize a non-empty WAV for $midi_path"
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

# Real-time completion notification
notify "**[$CLUSTER] Dataset build complete:** \`Slakh 2100 Redux\` — \`$(wc -l < slakh2100.txt 2>/dev/null || echo 0)\` files"
