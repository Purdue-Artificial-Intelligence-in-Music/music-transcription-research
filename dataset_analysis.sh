#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=32
#SBATCH --time=04:00:00

module load conda

rm -rf /scratch/gilbreth/ochaturv/.conda/envs/analysis
conda create -y -q --prefix /scratch/gilbreth/ochaturv/.conda/envs/analysis python=3.10 pip mido tqdm pandas > /dev/null
source activate /scratch/gilbreth/ochaturv/.conda/envs/analysis

python dataset_analysis.py datasets.json --generate-tex

conda deactivate
