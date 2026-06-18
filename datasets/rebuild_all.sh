#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH -J rebuild_datasets
#SBATCH -o rebuild_datasets.out

cd "$SLURM_SUBMIT_DIR"

echo "Cleaning up existing datasets..."
rm -rf maestro-v3.0.0         && rm -f maestro-v3.0.0.txt
rm -rf slakh2100               && rm -f slakh2100.txt
rm -rf msmd_data               && rm -f msmd_data.txt
rm -rf xmidi_dataset           && rm -f xmidi_dataset.txt
rm -rf POP909                  && rm -f POP909.txt
rm -rf gigamidi                && rm -f gigamidi.txt
rm -rf nesmdb                  && rm -f nesmdb.txt
rm -rf BiMMuDa                 && rm -f BiMMuDa.txt
rm -rf aam_dataset             && rm -f aam_dataset.txt
rm -rf traditional_flute       && rm -f traditional_flute.txt
echo "Cleanup complete."

echo "Submitting dataset build jobs..."
sbatch datasets/maestro.sh
sbatch datasets/slakh.sh
sbatch datasets/msmd.sh
sbatch datasets/xmidi.sh
sbatch datasets/pop909.sh
sbatch datasets/gigamidi.sh
sbatch datasets/nesmdb.sh
sbatch datasets/bimmuda.sh
sbatch datasets/aam.sh
sbatch datasets/traditional_flute.sh
echo "All dataset jobs submitted."
