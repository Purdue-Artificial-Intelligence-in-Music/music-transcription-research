#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=1-00:00:00

module load parallel
module load ffmpeg

OUTDIR="./slakh2100"

# Download the dataset
wget -O slakh2100_flac_redux.tar.gz "https://zenodo.org/record/4599666/files/slakh2100_flac_redux.tar.gz?download=1" >/dev/null

# Extract the dataset
mkdir -p "$OUTDIR"
tar -xzf slakh2100_flac_redux.tar.gz --strip-components=1 -C "$OUTDIR" >/dev/null

# Remove the 'omitted' folder
rm -rf "$OUTDIR/omitted"

cd "$OUTDIR"

# Define the processing function
process_track() {
    track_dir="$1"
    track_name=$(basename "$track_dir")

    # Rename all_src.mid
    if [[ -f "$track_dir/all_src.mid" ]]; then
        mv "$track_dir/all_src.mid" "$track_dir/${track_name}.mid"
    fi

    # Convert mix.flac to .wav
    if [[ -f "$track_dir/mix.flac" ]]; then
        ffmpeg -loglevel error -y -i "$track_dir/mix.flac" -ar 44100 -ac 1 "$track_dir/${track_name}.wav"
        rm "$track_dir/mix.flac"
    fi

    # Remove all other files
    find "$track_dir" -mindepth 1 ! -name "${track_name}.mid" ! -name "${track_name}.wav" -exec rm -rf {} +
}

export -f process_track

# Find all Track directories and process them in parallel
find train test validation -type d -name 'Track*' | parallel -j 32 process_track

cd ../

# Clean up
rm slakh2100_flac_redux.tar.gz

# Generate a sorted list of all input files
find "$(realpath ./slakh2100)" -type f -name "*.wav" | sort >slakh2100.txt
