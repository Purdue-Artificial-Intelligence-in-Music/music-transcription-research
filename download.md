# Instructions on downloading each dataset

## Slakh 2100

```bash
OUTDIR="./slakh2100"

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
```
