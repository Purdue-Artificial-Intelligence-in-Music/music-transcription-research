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

gdown 1i2HdWsxPEjBUtsMclioqC7nmN9aCDwRc --output nesmdb-exprsco.tar.gz
mkdir -p nesmdb-exprsco
tar -xzf nesmdb-exprsco.tar.gz -C nesmdb-exprsco

# Count input files
num_vgm=$(find nesmdb-vgm -name '*.vgm' | wc -l)
num_exprsco=$(find nesmdb-exprsco -name '*.exprsco.pkl' | wc -l)
echo "Found $num_vgm .vgm files"
echo "Found $num_exprsco .exprsco.pkl files"

# Conda creation
rm -rf /home/x-ochaturvedi/.conda/envs/nesmdb
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
from nesmdb.score.midi import exprsco_to_midi
from scipy.io.wavfile import write as write_wav

def convert_file(input_fp, output_fp):
    if input_fp.endswith('.vgm') and output_fp.endswith('.wav'):
        with open(input_fp, 'rb') as f:
            vgm_data = f.read()
        wav = vgm_to_wav(vgm_data)
        write_wav(output_fp, 44100, wav)
        print("Converted VGM to WAV: {}".format(output_fp))

    elif input_fp.endswith('.exprsco.pkl') and output_fp.endswith('.mid'):
        with open(input_fp, 'rb') as f:
            exprsco = pickle.load(f)
        midi_bytes = exprsco_to_midi(exprsco)
        with open(output_fp, 'wb') as f:
            f.write(midi_bytes)
        print("Converted exprsco to MIDI: {}".format(output_fp))

    else:
        print("Unsupported conversion. Only supports:")
        print("  .vgm --> .wav")
        print("  .exprsco.pkl --> .mid")

def main():
    parser = argparse.ArgumentParser(description='Convert NES VGM to WAV or exprsco.pkl to MIDI.')
    parser.add_argument('-i', '--input', required=True, help='Input file (.vgm or .exprsco.pkl)')
    parser.add_argument('-o', '--output', required=True, help='Output file (.wav or .mid)')
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

# Convert EXPRSCO -> MIDI (strip .pkl to avoid .exprsco.mid)
find nesmdb-exprsco -name '*.exprsco.pkl' | \
  parallel -j32 'f={}; base=$(basename "$f"); base=${base%.exprsco.pkl}; python nesmdb-convertor.py -i "$f" -o nesmdb/"$base".mid'

# Clean up
conda deactivate
rm -f nesmdb-vgm.tar.gz nesmdb-exprsco.tar.gz nesmdb-convertor.py
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
