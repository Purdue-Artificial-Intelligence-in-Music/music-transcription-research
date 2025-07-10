# Instructions on downloading each dataset

## Maestro v3.0.0

```bash
# Download the zip file
wget https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0.zip

# Verify the file integrity using SHA-256
echo "6680fea5be2339ea15091a249fbd70e49551246ddbd5ca50f1b2352c08c95291  maestro-v3.0.0.zip" | sha256sum -c -

# Unzip the dataset
unzip maestro-v3.0.0.zip
```

## Slakh 2100

```bash
# Check if Singularity is installed
if ! command -v singularity &>/dev/null; then
    echo "Error: Singularity is not installed. Please contact your system administrator."
    exit 1
fi

MUSESCORE_CONTAINER="musescore_slakh.sif"
MUSESCORE_DEFINITION="musescore_slakh.def"
OUTDIR="./slakh2100"

# Create and build MuseScore container if needed
if [ ! -f "$MUSESCORE_CONTAINER" ]; then
    cat <<EOF >"$MUSESCORE_DEFINITION"
BootStrap: docker
From: ubuntu:22.04

%post
    apt update && apt install -y musescore ffmpeg
    echo "MuseScore and FFmpeg installed"

%runscript
    export QT_QPA_PLATFORM=offscreen
    exec /usr/bin/mscore "\$@"
EOF

    singularity build "$MUSESCORE_CONTAINER" "$MUSESCORE_DEFINITION"
    rm "$MUSESCORE_DEFINITION"
fi

# Download the dataset
wget -O slakh2100_flac_redux.tar.gz "https://zenodo.org/record/4599666/files/slakh2100_flac_redux.tar.gz?download=1" >/dev/null

# Extract the dataset
mkdir -p "$OUTDIR"
tar -xzf slakh2100_flac_redux.tar.gz --strip-components=1 -C "$OUTDIR" >/dev/null

# Remove the 'omitted' folder
rm -rf "$OUTDIR/omitted"

cd "$OUTDIR"

# Process each track in train and test
for split in train test validation; do
    for track_dir in ${split}/Track*/; do
        track_name=$(basename "$track_dir")

        # Rename all_src.mid
        if [[ -f "$track_dir/all_src.mid" ]]; then
            mv "$track_dir/all_src.mid" "$track_dir/${track_name}.mid"
        fi

        # Convert mix.flac to .wav
        if [[ -f "$track_dir/mix.flac" ]]; then
            ffmpeg -loglevel error -y -i "$track_dir/mix.flac" "$track_dir/${track_name}.wav"
            rm "$track_dir/mix.flac"
        fi

        # Remove all other files
        find "$track_dir" -mindepth 1 ! -name "${track_name}.mid" ! -name "${track_name}.wav" -exec rm -rf {} +
    done
done

rm "$MUSESCORE_CONTAINER"
```
