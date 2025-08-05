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

ZENODO_URLS=(
    "https://zenodo.org/records/5794629/files/0001-1000-midis.zip?download=1",
    "https://zenodo.org/records/5794629/files/1001-2000-midis.zip?download=1",
    "https://zenodo.org/records/5794629/files/2001-3000-midis.zip?download=1"
)
TARGET_DIR="aam_dataset"

# Create target directory
rm -rf aam_dataset
mkdir -p aam_dataset

# Download and extract each ZIP
for url in "${ZENODO_URLS[@]}"; do
    zip_name=$(basename "$url" | cut -d'?' -f1)
    echo "Downloading: $zip_name"
    wget --no-verbose -O "$zip_name" "$url"

    echo "Unzipping: $zip_name"
    unzip -q "$zip_name" -d aam_dataset

    rm -f "$zip_name"
done

# Print number of MIDI files before merging
echo "Total MIDI files before merging: $(find "$TARGET_DIR" -name '*.mid' | wc -l)"

# Create conda environment for Python dependencies
conda create -n aam python=3.10 -y -q > /dev/null
source activate aam
pip install miditoolkit pretty_midi -q

# Write Python script for merging MIDI files
cat <<EOF > midi_combiner.py
import os
import glob
import copy
import argparse
import miditoolkit
import pretty_midi


def merge_midi_files(midi_dir: str, prefix: str):
    midi_paths = sorted(glob.glob(os.path.join(midi_dir, f"{prefix}_*.mid")))
    if not midi_paths:
        print(
            f"[ERROR] No MIDI files found for prefix '{prefix}' in directory: {midi_dir}"
        )
        return

    base_midi = None
    for path in midi_paths:
        try:
            base_midi = miditoolkit.MidiFile(path)
            break
        except:
            continue

    if base_midi is None:
        print(f"[ERROR] No valid base MIDI file for prefix: {prefix}")
        return

    merged_midi = miditoolkit.MidiFile()
    merged_midi.ticks_per_beat = base_midi.ticks_per_beat
    merged_midi.tempo_changes = base_midi.tempo_changes
    merged_midi.time_signature_changes = base_midi.time_signature_changes
    merged_midi.key_signature_changes = [
        ks for ks in base_midi.key_signature_changes if -7 <= ks.key_number <= 7
    ]

    instrument_count = 0
    program_to_channel = {}
    next_channel = 0
    drum_channel = 9
    assigned_channels = set()

    all_notes = []
    all_control_changes = []
    original_total_notes = 0

    print(f"[INFO] Merging instruments for prefix '{prefix}':")
    for path in midi_paths:
        try:
            midi = miditoolkit.MidiFile(path)
        except:
            print(f"[WARN] Failed to read MIDI: {path}")
            continue

        for inst in midi.instruments:
            # print(
            #     f"[DEBUG] Instrument: is_drum={inst.is_drum}\tname={inst.name}\tprogram={inst.program}"
            # )

            if len(inst.notes) == 0:
                continue

            original_total_notes += len(inst.notes)

            inst_copy = copy.deepcopy(inst)
            inst_copy.name = inst_copy.name or os.path.basename(path).replace(
                ".mid", ""
            )

            if inst_copy.is_drum:
                inst_copy.channel = drum_channel
            else:
                prog = inst_copy.program
                if prog in program_to_channel:
                    inst_copy.channel = program_to_channel[prog]
                else:
                    while (
                        next_channel in assigned_channels
                        or next_channel == drum_channel
                    ):
                        next_channel += 1
                        if next_channel >= 16:
                            raise RuntimeError(
                                f"Exceeded available MIDI channels even with program reuse for prefix '{prefix}'"
                            )
                    program_to_channel[prog] = next_channel
                    inst_copy.channel = next_channel
                    assigned_channels.add(next_channel)

            print(
                f"[DEBUG] Assigned channel {inst_copy.channel} to instrument {inst_copy.name} (program={inst_copy.program})"
            )
            print(
                f"[NOTE] {inst_copy.name}:\t{len(inst_copy.notes)} notes,\tmin_pitch={min(n.pitch for n in inst_copy.notes)},\tmax_pitch={max(n.pitch for n in inst_copy.notes)}"
            )
            print(
                f"[CTRL] {inst_copy.name}:\t{len(inst_copy.control_changes)} control changes"
            )

            all_notes.extend(inst_copy.notes)
            all_control_changes.extend(inst_copy.control_changes)
            merged_midi.instruments.append(inst_copy)
            instrument_count += 1

    if instrument_count > 0:
        output_path = os.path.join(midi_dir, f"{prefix}.mid")
        merged_midi.dump(output_path)
        print(f"[SUCCESS] Merged {instrument_count} instruments for prefix '{prefix}'")
        print(f"[OUTPUT] Combined MIDI written to: {output_path}")

        # Validation
        merged_pm = pretty_midi.PrettyMIDI(output_path)
        merged_notes = sum(len(i.notes) for i in merged_pm.instruments)
        merged_duration = merged_pm.get_end_time()
        original_duration = 0.0
        for path in midi_paths:
            try:
                pm = pretty_midi.PrettyMIDI(path)
                for inst in pm.instruments:
                    all_notes.extend(inst.notes)
                original_duration = max(original_duration, pm.get_end_time())
            except Exception as e:
                print(f"[WARN] Failed to parse {path} with PrettyMIDI: {e}")

        print(f"[VERIFY] Original total notes:\t{original_total_notes}")
        print(f"[VERIFY] Merged total notes:\t{merged_notes}")
        print(f"[VERIFY] Original duration:\t{original_duration:.2f}s")
        print(f"[VERIFY] Merged duration:\t{merged_duration:.2f}s")

    for path in midi_paths:
        os.remove(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--midi_dir", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    merge_midi_files(args.midi_dir, args.prefix)
EOF

# Merge MIDI files for prefixes 0001 to 3000 using GNU parallel
PREFIXES=$(seq -f "%04g" 1 3000)
export PYTHONPATH=$PWD
parallel -j 32 python3 midi_combiner.py --midi_dir "$TARGET_DIR" --prefix {} ::: $PREFIXES
conda deactivate

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
find aam_dataset -type f -name "*.mid" | parallel --jobs 32 convert_midi {}

# Clean up
rm -f "$FS_DEFINITION" "$FS_CONTAINER" midi_combiner.py
rm -rf /home/ochaturv/.conda/envs/aam

# Generate a sorted list of all input files
find "$(realpath "aam_dataset")" -type f -name "*.wav" | sort >aam_dataset.txt

# Print the number of .MID files and then .WAV files
echo "Number of .MID files: $(find aam_dataset -type f -name "*.mid" | wc -l)"
echo "Number of .WAV files: $(find aam_dataset -type f -name "*.wav" | wc -l)"
