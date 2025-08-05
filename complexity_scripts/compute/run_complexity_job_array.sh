#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --job-name=complexity_array
#SBATCH --partition=gilbreth-standby
#SBATCH --output=logs/complexity_array_%A_%a.out
#SBATCH --error=logs/complexity_array_%A_%a.err
#SBATCH --array=0-7

# COMPLEXITY ANALYSIS - JOB ARRAY SCRIPT
# Optimized for large-scale deployment with maximum CPU utilization

module purge

start_time=$(date +%s.%N)

# Define datasets for job array
DATASETS=("slakh2100" "maestro" "pop909" "nesmdb" "msmd" "aam" "bimmuda" "xmidi")
DATASET_NAME=${DATASETS[$SLURM_ARRAY_TASK_ID]}

echo "=========================================="
echo "Starting Complexity Analysis - Job Array"
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Dataset: $DATASET_NAME"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "=========================================="

# Send Discord notification for job start
# curl -s -X POST -H "Content-Type: application/json" -d "{
# \"content\": \"🎵 **Complexity Analysis Started**\nJob ID: $SLURM_JOB_ID\nArray Task: $SLURM_ARRAY_TASK_ID\nDataset: $DATASET_NAME\nNode: $SLURM_NODELIST\",
# \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
# }" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null

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

# Run complexity analysis with maximum CPU utilization
echo "Starting complexity analysis for dataset: $DATASET_NAME"

# Use all available CPUs for maximum performance
python3 complexity_analysis.py \
    --dataset "$DATASET_NAME" \
    --output-dir "$COMPLEXITY_OUTPUT_DIR" \
    --num-workers $SLURM_CPUS_PER_TASK

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "Complexity analysis completed successfully!"
    echo "Dataset: $DATASET_NAME"
    
    # List output files
    echo "Generated files:"
    ls -la "$COMPLEXITY_OUTPUT_DIR"/*"$DATASET_NAME"*
    
    # Calculate runtime
    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    runtime_formatted=$(printf '%02d:%02d:%02d' $(($runtime/3600)) $(($runtime%3600/60)) $(($runtime%60)))
    
    echo "Total Runtime: ${runtime_formatted}"
    echo "=========================================="
    
    # Send Discord notification for successful completion
    curl -s -X POST -H "Content-Type: application/json" -d "{
\"content\": \"✅ **Complexity Analysis Completed**\nJob ID: $SLURM_JOB_ID\nArray Task: $SLURM_ARRAY_TASK_ID\nDataset: $DATASET_NAME\nRuntime: ${runtime_formatted}\",
\"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
    
else
    echo "=========================================="
    echo "Complexity analysis failed!"
    echo "Dataset: $DATASET_NAME"
    echo "=========================================="
    
    # Send Discord notification for failure
    curl -s -X POST -H "Content-Type: application/json" -d "{
\"content\": \"❌ **Complexity Analysis Failed**\nJob ID: $SLURM_JOB_ID\nArray Task: $SLURM_ARRAY_TASK_ID\nDataset: $DATASET_NAME\",
\"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"
}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
fi 