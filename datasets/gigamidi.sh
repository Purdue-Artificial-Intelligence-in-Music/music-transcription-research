#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=04:00:00

rm -rf gigamidi
mkdir -p gigamidi

module load ffmpeg
module load parallel
module load conda

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
HF_TOKEN = "$HF_TOKEN"
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
rm -rf /home/ochaturv/.conda/envs/gigamidi
conda create -n gigamidi python=3.10 -y -q > /dev/null
source activate gigamidi
pip install datasets huggingface_hub -q > /dev/null

python extract_gigamidi.py

# Print the number of MIDI files found
MIDI_COUNT=$(find gigamidi -type f \( -iname "*.mid" -o -iname "*.midi" \) | wc -l)
echo "Found $MIDI_COUNT MIDI files with .mid or .midi extension."

# Find any files with the same name
echo "Checking for duplicate filenames..."
DUPLICATES=$(find gigamidi -type f -name "*.mid" -or -name "*.midi" | \
    xargs -n1 basename | sort | uniq -d)

if [ -z "$DUPLICATES" ]; then
    echo "No duplicate filenames found."
else
    echo "Duplicate filenames found:"
    echo "$DUPLICATES"
fi
