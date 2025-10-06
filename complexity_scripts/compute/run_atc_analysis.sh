#!/bin/bash
#SBATCH -A yunglu
#SBATCH -p a100-80gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=60:00:00
#SBATCH --job-name=atc_analysis
#SBATCH --output=atc_analysis_%j.out
#SBATCH --error=atc_analysis_%j.err

# ATC ANALYSIS - MAIN JOB SCRIPT
# Runs both audio spectral chordino method and MIDI pychord calculation method

module purge

start_time=$(date +%s.%N)

echo "=========================================="
echo "Starting ATC Analysis Pipeline"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "=========================================="

# Set working directory
cd complexity_scripts/compute

# Create logs directory
mkdir -p logs

# Create output directory
ATC_OUTPUT_DIR="./atc_results"
mkdir -p "$ATC_OUTPUT_DIR"

echo "=========================================="
echo "Environment setup complete"
echo "Output directory: $ATC_OUTPUT_DIR"
echo "=========================================="

# Run ATC analysis
echo "Starting ATC analysis..."

# Check command line arguments
if [ $# -eq 1 ]; then
    # Only dataset provided
    DATASET_NAME="$1"
    echo "Analyzing specific dataset: $DATASET_NAME"
    python3 atc_analysis.py --dataset "$DATASET_NAME" --output-dir "$ATC_OUTPUT_DIR" --num-workers 8
elif [ $# -eq 2 ]; then
    # Dataset and max-files provided
    DATASET_NAME="$1"
    MAX_FILES="$2"
    echo "Analyzing specific dataset: $DATASET_NAME with max-files: $MAX_FILES"
    python3 atc_analysis.py --dataset "$DATASET_NAME" --max-files "$MAX_FILES" --output-dir "$ATC_OUTPUT_DIR" --num-workers 8
elif [ $# -eq 3 ]; then
    # Dataset, max-files, and num-workers provided
    DATASET_NAME="$1"
    MAX_FILES="$2"
    NUM_WORKERS="$3"
    echo "Analyzing specific dataset: $DATASET_NAME with max-files: $MAX_FILES and num-workers: $NUM_WORKERS"
    python3 atc_analysis.py --dataset "$DATASET_NAME" --max-files "$MAX_FILES" --num-workers "$NUM_WORKERS" --output-dir "$ATC_OUTPUT_DIR"
else
    echo "Analyzing all datasets"
    python3 atc_analysis.py --output-dir "$ATC_OUTPUT_DIR" --num-workers 8
fi

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "ATC analysis completed successfully!"
    
    # List output files
    echo "Generated files:"
    ls -la "$ATC_OUTPUT_DIR"
    
    # Show sample results
    if [ -f "$ATC_OUTPUT_DIR/all_atc_analysis_results.csv" ]; then
        echo "=========================================="
        echo "Sample results (first 5 rows):"
        echo "=========================================="
        head -5 "$ATC_OUTPUT_DIR/all_atc_analysis_results.csv"
        
        # Show summary statistics
        echo "=========================================="
        echo "Summary Statistics:"
        echo "=========================================="
        
        # Count total files analyzed
        total_files=$(tail -n +2 "$ATC_OUTPUT_DIR/all_atc_analysis_results.csv" | wc -l)
        echo "Total files analyzed: $total_files"
        
        # Calculate average ATC scores if file exists and has data
        if [ $total_files -gt 0 ]; then
            # Calculate average PYCHORD ATC score
            pychord_avg=$(tail -n +2 "$ATC_OUTPUT_DIR/all_atc_analysis_results.csv" | cut -d',' -f6 | awk '{sum+=$1} END {print sum/NR}')
            echo "Average PYCHORD ATC Score: $pychord_avg"
            
            # Calculate average CHORDINO ATC score
            chordino_avg=$(tail -n +2 "$ATC_OUTPUT_DIR/all_atc_analysis_results.csv" | cut -d',' -f11 | awk '{sum+=$1} END {print sum/NR}')
            echo "Average CHORDINO ATC Score: $chordino_avg"
            
            # Calculate average difference
            diff_avg=$(tail -n +2 "$ATC_OUTPUT_DIR/all_atc_analysis_results.csv" | cut -d',' -f16 | awk '{sum+=$1} END {print sum/NR}')
            echo "Average ATC Score Difference: $diff_avg"
        fi
    fi
    
    # Calculate runtime
    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    runtime_int=${runtime%.*}
    runtime_formatted=$(printf '%02d:%02d:%02d' $(($runtime_int/3600)) $(($runtime_int%3600/60)) $(($runtime_int%60)))
    
    echo "Total Runtime: ${runtime_formatted}"
    echo "=========================================="
    
    
else
    echo "=========================================="
    echo "ATC analysis failed!"
    echo "=========================================="
    
fi 

# Organize log files at the end
echo "=========================================="
echo "Organizing log files..."
echo "=========================================="

# Create logs directory in the main project location
mkdir -p ../../logs/

# Move log files to organized location
if [ -f "atc_analysis_$SLURM_JOB_ID.out" ]; then
    mv "atc_analysis_$SLURM_JOB_ID.out" "../../logs/"
    echo "Moved output log to ../../logs/atc_analysis_$SLURM_JOB_ID.out"
fi

if [ -f "atc_analysis_$SLURM_JOB_ID.err" ]; then
    mv "atc_analysis_$SLURM_JOB_ID.err" "../../logs/"
    echo "Moved error log to ../../logs/atc_analysis_$SLURM_JOB_ID.err"
fi

echo "Log organization complete!"
echo "==========================================" 