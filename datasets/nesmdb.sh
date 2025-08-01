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

# Download and unzip the NES-MDB datasets
pip install gdown -q

gdown 1lx03YN-giEPuNdQiiuKTSfZRu2Dt7Uf8 --output nesmdb-vgm.tar.gz
mkdir -p nesmdb-vgm
tar -xzf nesmdb-vgm.tar.gz -C nesmdb-vgm

gdown 1w2uo1Cmio4gz6nGUhZOtzF54kPkoKyo7 --output nesmdb-midi.tar.gz
mkdir -p nesmdb-midi
tar -xzf nesmdb-midi.tar.gz -C nesmdb-midi

# Count input files
num_vgm=$(find nesmdb-vgm -name '*.vgm' | wc -l)
num_midi=$(find nesmdb-midi -name '*.mid' | wc -l)
echo "Found $num_vgm .vgm files"
echo "Found $num_midi .mid files"

# Conda creation
rm -rf /home/ochaturv/.conda/envs/nesmdb
conda create -n nesmdb python=2.7 -y -q > /dev/null
source activate nesmdb
git clone https://github.com/chrisdonahue/nesmdb.git
cd nesmdb
git fetch origin pull/14/head:pr-14
git checkout pr-14
pip install .
cd ../
rm -rf nesmdb
pip install pretty_midi -q

# Create convertor script dynamically
cat <<EOF > nesmdb-convertor.py
import argparse
import cPickle as pickle
from nesmdb.convert import vgm_to_wav
from scipy.io.wavfile import write as write_wav

def convert_file(input_fp, output_fp):
    if input_fp.endswith('.vgm') and output_fp.endswith('.wav'):
        with open(input_fp, 'rb') as f:
            vgm_data = f.read()
        wav = vgm_to_wav(vgm_data)
        write_wav(output_fp, 44100, wav)
        print("Converted VGM to WAV: {}".format(output_fp))

    else:
        print("Unsupported conversion. Only supports:")
        print("  .vgm --> .wav")

def main():
    parser = argparse.ArgumentParser(description='Convert NES VGM to WAV.')
    parser.add_argument('-i', '--input', required=True, help='Input file (.vgm)')
    parser.add_argument('-o', '--output', required=True, help='Output file (.wav)')
    args = parser.parse_args()
    convert_file(args.input, args.output)

if __name__ == '__main__':
    main()
EOF

# Create the final dataset
mkdir -p nesmdb

# Convert VGM -> WAV
find nesmdb-vgm -name '*.vgm' | \
  parallel -j32 "python nesmdb-convertor.py -i {} -o nesmdb/{/.}.wav"

# Copy all MIDI files to nesmdb
find nesmdb-midi -name '*.mid' -exec cp {} nesmdb/ \;

# Clean up
conda deactivate
rm -f nesmdb-vgm.tar.gz nesmdb-midi.tar.gz nesmdb-convertor.py
rm -rf nesmdb-vgm nesmdb-midi /home/ochaturv/.conda/envs/nesmdb

# Check consistency
echo "Checking consistency of .wav and .mid files..."
wav_basenames=$(find nesmdb -name '*.wav' -exec basename {} .wav \; | sort)
mid_basenames=$(find nesmdb -name '*.mid' -exec basename {} .mid \; | sort)

missing_mids=$(comm -23 <(echo "$wav_basenames") <(echo "$mid_basenames"))
missing_wavs=$(comm -13 <(echo "$wav_basenames") <(echo "$mid_basenames"))

if [ -n "$missing_mids" ] || [ -n "$missing_wavs" ]; then
    echo "Mismatches detected:"
    if [ -n "$missing_mids" ]; then
        echo "Missing .mid for:"
        echo "$missing_mids"
    fi
    if [ -n "$missing_wavs" ]; then
        echo "Missing .wav for:"
        echo "$missing_wavs"
    fi
else
    echo "All .wav and .mid files are matched!"
fi

# Remove unmatched .wav files
echo "Removing extra .wav files without matching .mid..."
for base in $missing_mids; do
    wav_path="nesmdb/$base.wav"
    if [ -f "$wav_path" ]; then
        echo "Deleting $wav_path"
        rm -f "$wav_path"
    fi
done

# Final count
final_wavs=$(find nesmdb -name '*.wav' | wc -l)
final_mids=$(find nesmdb -name '*.mid' | wc -l)
echo "Final: $final_wavs .wav and $final_mids .mid files"

# Generate a sorted list of all .wav files
find "$(realpath "nesmdb")" -type f -name "*.wav" | sort > nesmdb.txt
