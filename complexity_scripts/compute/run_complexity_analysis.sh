#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-80gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --job-name=complexity_analysis
#SBATCH --output=complexity_analysis_%j.out
#SBATCH --error=complexity_analysis_%j.err

# COMPLEXITY ANALYSIS - MAIN JOB SCRIPT

module purge

start_time=$(date +%s.%N)

echo "=========================================="
echo "Starting Complexity Analysis Pipeline"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "=========================================="

# Set working directory
cd /home/$USER/AIM/music-transcription-research/complexity_scripts/compute

# Create logs directory
mkdir -p logs

# Create output directory
COMPLEXITY_OUTPUT_DIR="./complexity_results"
mkdir -p "$COMPLEXITY_OUTPUT_DIR"

echo "=========================================="
echo "Environment setup complete"
echo "Output directory: $COMPLEXITY_OUTPUT_DIR"
echo "=========================================="

# Run complexity analysis
echo "Starting complexity analysis..."

# Check if specific dataset is provided as argument
if [ $# -eq 1 ]; then
    DATASET_NAME="$1"
    echo "Analyzing specific dataset: $DATASET_NAME"
    python3 complexity_analysis.py --dataset "$DATASET_NAME" --output-dir "$COMPLEXITY_OUTPUT_DIR" --num-workers 64
else
    echo "Analyzing all datasets"
    python3 complexity_analysis.py --output-dir "$COMPLEXITY_OUTPUT_DIR" --num-workers 64
fi

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "Complexity analysis completed successfully!"
    
    # List output files
    echo "Generated files:"
    ls -la "$COMPLEXITY_OUTPUT_DIR"
    
    # Calculate runtime
    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    runtime_formatted=$(printf '%02d:%02d:%02d' $(($runtime/3600)) $(($runtime%3600/60)) $(($runtime%60)))
    
    echo "Total Runtime: ${runtime_formatted}"
    echo "=========================================="
    
    
else
    echo "=========================================="
    echo "Complexity analysis failed!"
    echo "=========================================="
    
fi 

# Organize log files at the end
echo "=========================================="
echo "Organizing log files..."
echo "=========================================="

# Create logs directory in the main project location
mkdir -p ../../logs/

# Move log files to organized location
if [ -f "complexity_analysis_$SLURM_JOB_ID.out" ]; then
    mv "complexity_analysis_$SLURM_JOB_ID.out" "../../logs/"
    echo "Moved output log to ../../logs/complexity_analysis_$SLURM_JOB_ID.out"
fi

if [ -f "complexity_analysis_$SLURM_JOB_ID.err" ]; then
    mv "complexity_analysis_$SLURM_JOB_ID.err" "../../logs/"
    echo "Moved error log to ../../logs/complexity_analysis_$SLURM_JOB_ID.err"
fi

echo "Log organization complete!"
echo "==========================================" 