#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00

rm -rf traditional_flute

module load ffmpeg
module load parallel

KAGGLE_URL="https://www.kaggle.com/api/v1/datasets/download/jbraga/traditional-flute-dataset"
ZIP_FILE="traditional_flute.zip"

# Download and unzip the Traditional Flute dataset, keeping only the MIDI files
wget -q -O "$ZIP_FILE" "$KAGGLE_URL"
unzip -q "$ZIP_FILE" -d traditional_flute
find traditional_flute/traditional-flute-dataset/score -type f -name "*.midi" -exec mv {} traditional_flute/ \;
rm -rf traditional_flute/traditional-flute-dataset
rm -f traditional_flute/traditional-flute-dataset.zip

# Rename all .midi files to .mid
find traditional_flute -type f -name "*.midi" | while read -r file; do
    mv "$file" "${file%.midi}.mid"
done

# Print the number of MIDI files found
MIDI_COUNT=$(find traditional_flute -type f -name "*.mid" | wc -l)
echo "Found $MIDI_COUNT MIDI files."