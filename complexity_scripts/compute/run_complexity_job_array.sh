#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-40gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --job-name=complexity_array
#SBATCH --output=complexity_array_%A_%a.out
#SBATCH --error=complexity_array_%A_%a.err
#SBATCH --array=0-7

# COMPLEXITY ANALYSIS - JOB ARRAY SCRIPT
# Runs complexity analysis on different datasets in parallel

module purge

start_time=$(date +%s.%N)

echo "=========================================="
echo "Starting Complexity Analysis Array Job"
echo "Job ID: $SLURM_JOB_ID"
echo "Array Job ID: $SLURM_ARRAY_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Node: $SLURM_NODELIST"
echo "=========================================="

# Set working directory
cd complexity_scripts/compute

# Create logs directory
mkdir -p logs

# Create output directory
COMPLEXITY_OUTPUT_DIR="./complexity_results"
mkdir -p "$COMPLEXITY_OUTPUT_DIR"

echo "=========================================="
echo "Environment setup complete"
echo "Output directory: $COMPLEXITY_OUTPUT_DIR"
echo "=========================================="

# Define datasets for array jobs
DATASETS=("nesmdb" "aam" "xmidi" "bimmuda" "msmd" "pop909" "maestro" "slakh")

# Get dataset for this array task
DATASET_NAME="${DATASETS[$SLURM_ARRAY_TASK_ID]}"
echo "Processing dataset: $DATASET_NAME"

# Run complexity analysis
echo "Starting complexity analysis for $DATASET_NAME..."

python3 complexity_analysis.py --dataset "$DATASET_NAME" --output-dir "$COMPLEXITY_OUTPUT_DIR" --num-workers 32

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "Complexity analysis for $DATASET_NAME completed successfully!"
    
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
    echo "Complexity analysis for $DATASET_NAME failed!"
    echo "=========================================="
    
fi 

# Organize log files at the end
echo "=========================================="
echo "Organizing log files..."
echo "=========================================="

# Create logs directory in the main project location
mkdir -p ../../logs/

# Move log files to organized location
if [ -f "complexity_array_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.out" ]; then
    mv "complexity_array_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.out" "../../logs/"
    echo "Moved output log to ../../logs/complexity_array_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.out"
fi

if [ -f "complexity_array_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.err" ]; then
    mv "complexity_array_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.err" "../../logs/"
    echo "Moved error log to ../../logs/complexity_array_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.err"
fi

echo "Log organization complete!"
echo "==========================================" 