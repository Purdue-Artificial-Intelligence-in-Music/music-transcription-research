#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-40gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --mem=240G
#SBATCH --time=04:00:00

rm -rf gigamidi
mkdir -p gigamidi

source /etc/profile.d/modules.sh
module load external
module load conda parallel ffmpeg
source "$(conda info --base)/etc/profile.d/conda.sh"

# Download and unzip the GigaMIDI dataset
# wget --header="Authorization: Bearer $HF_TOKEN" \
    #  --content-disposition \
    #  "https://huggingface.co/datasets/Metacreation/GigaMIDI/resolve/main/Final_GigaMIDI_V1.1_Final.zip"
# unzip -q Final_GigaMIDI_V1.1_Final.zip -d gigamidi

cat <<EOF > extract_gigamidi.py
import os
from datasets import load_dataset
from huggingface_hub import login

# Set custom cache directories (adjust to your quota-safe path!)
os.environ["HF_HOME"] = "/depot/yunglu/data/transcription"
os.environ["TRANSFORMERS_CACHE"] = "/depot/yunglu/data/transcription/transformers"
os.environ["HF_DATASETS_CACHE"] = "/depot/yunglu/data/transcription/datasets"
os.environ["HF_METRICS_CACHE"] = "/depot/yunglu/data/transcription/metrics"

# Replace with your token (keep this secret!)
HF_TOKEN = os.environ.get("HF_TOKEN", "")
login(token=HF_TOKEN)

# Output path
output_dir = "gigamidi"
os.makedirs(output_dir, exist_ok=True)

# Load dataset
print("Loading dataset...")
dataset = load_dataset("Metacreation/GigaMIDI", split="train")

# Extract and save each MIDI file
print("Saving MIDI files...")
for i, sample in enumerate(dataset):
    md5 = sample['md5']
    path = os.path.join(output_dir, f"{md5}.mid")
    with open(path, "wb") as f:
        f.write(sample["music"])
    if (i + 1) % 10000 == 0:
        print(f"Saved {i + 1} files")

print(f"All MIDI files saved to: {output_dir}")
EOF

# Conda creation
rm -rf /scratch/gilbreth/ochaturv/.conda/envs/gigamidi
conda create --prefix /scratch/gilbreth/ochaturv/.conda/envs/gigamidi python=3.10 -y -q > /dev/null
conda activate /scratch/gilbreth/ochaturv/.conda/envs/gigamidi
pip install datasets huggingface_hub -q > /dev/null

python extract_gigamidi.py
conda deactivate
rm -rf /scratch/gilbreth/ochaturv/.conda/envs/gigamidi
rm -f extract_gigamidi.py

# Print the number of MIDI files found
MIDI_COUNT=$(find gigamidi -type f \( -iname "*.mid" -o -iname "*.midi" \) | wc -l)
echo "Found $MIDI_COUNT MIDI files."

# Rename any .midi files to .mid
find gigamidi -type f -name "*.midi" | while read -r file; do
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

find gigamidi -type f -name "*.mid" | parallel --jobs 32 convert_midi {}

rm -f "$FS_DEFINITION" "$FS_CONTAINER"

# Generate a sorted list of all input files
find "$(realpath gigamidi)" -type f -name "*.wav" | sort >gigamidi.txt

echo "Number of .MID files: $(find gigamidi -type f -name "*.mid" | wc -l)"
echo "Number of .WAV files: $(find gigamidi -type f -name "*.wav" | wc -l)"
