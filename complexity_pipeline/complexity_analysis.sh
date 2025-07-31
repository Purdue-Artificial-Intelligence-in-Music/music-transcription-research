#!/bin/bash
#SBATCH -A yunglu-k
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=30
#SBATCH --time=12:00:00
#SBATCH -J complexity_analysis
#SBATCH -o logs/complexity_analysis_%j.out
#SBATCH -e logs/complexity_analysis_%j.err

# COMPLEXITY ANALYSIS SLURM SCRIPT

start_time=$(date +%s.%N)

echo "--------------------------------------------------"
echo "Starting Complexity Analysis Pipeline"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "--------------------------------------------------"

# Load modules
source /etc/profile.d/modules.sh
module use /opt/spack/cpu/Core
module use /opt/spack/gpu/Core
module load conda
module load parallel
module load gcc

# Set up conda environment for complexity analysis
export CONDA_PKGS_DIRS=/scratch/gilbreth/$USER/.conda/pkgs_complexity
mkdir -p "$CONDA_PKGS_DIRS"

# Create complexity analysis environment
conda create -y -q --prefix /scratch/gilbreth/$USER/.conda/envs/complexity-env \
    python=3.10 pip setuptools music21 pandas numpy matplotlib seaborn >/dev/null

# Activate environment
source /scratch/gilbreth/$USER/.conda/envs/complexity-env/bin/activate

# Install additional dependencies if needed
pip install --quiet pretty_midi

# Change to project directory
cd /home/$USER/AIM/music-transcription-research

# Create output directory
COMPLEXITY_OUTPUT_DIR="./complexity_results"
mkdir -p "$COMPLEXITY_OUTPUT_DIR"

echo "--------------------------------------------------"
echo "Environment setup complete"
echo "Output directory: $COMPLEXITY_OUTPUT_DIR"
echo "--------------------------------------------------"

# Run complexity analysis
echo "Starting complexity analysis..."

# Check if specific dataset is provided as argument
if [ $# -eq 1 ]; then
    DATASET_NAME="$1"
    echo "Analyzing specific dataset: $DATASET_NAME"
    python scripts/complexity_analysis.py --dataset "$DATASET_NAME" --output-dir "$COMPLEXITY_OUTPUT_DIR" --num-workers 30
else
    echo "Analyzing all datasets"
    python scripts/complexity_analysis.py --output-dir "$COMPLEXITY_OUTPUT_DIR" --num-workers 30
fi

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo "--------------------------------------------------"
    echo "Complexity analysis completed successfully!"
    
    # List output files
    echo "Generated files:"
    ls -la "$COMPLEXITY_OUTPUT_DIR"
    
    # Calculate runtime
    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    echo "Total runtime: ${runtime} seconds"
    
    # Send notification (optional)
    if command -v curl &> /dev/null; then
        curl -s -X POST -H "Content-Type: application/json" \
            -d "{\"content\": \"Complexity analysis completed successfully! Runtime: ${runtime}s\"}" \
            https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    fi
else
    echo "--------------------------------------------------"
    echo "Complexity analysis failed!"
    
    # Send error notification
    if command -v curl &> /dev/null; then
        curl -s -X POST -H "Content-Type: application/json" \
            -d "{\"content\": \"Complexity analysis failed! Check logs for details.\"}" \
            https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
    fi
fi

echo "--------------------------------------------------"
echo "Complexity Analysis Pipeline Complete"
echo "--------------------------------------------------" 