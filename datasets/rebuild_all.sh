#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-80gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH -J rebuild_datasets
#SBATCH -o rebuild_datasets.out

cd "$SLURM_SUBMIT_DIR"

# Each dataset script wipes and rebuilds its own directory inside $DATA_ROOT
# (see scripts/cluster_env.sh), so simply submitting them rebuilds from scratch.
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
