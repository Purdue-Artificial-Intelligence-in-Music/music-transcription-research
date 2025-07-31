#!/bin/bash

# LOCAL COMPLEXITY ANALYSIS RUNNER
# For testing and development purposes

echo "=================================================="
echo "Local Complexity Analysis Runner"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "midi_datasets.json" ]; then
    echo "Error: midi_datasets.json not found. Please run from the project root directory."
    echo "Generate it first: python scripts/generate_midi_config.py YOUR_USERNAME"
    exit 1
fi

# Create output directory
COMPLEXITY_OUTPUT_DIR="./complexity_results"
mkdir -p "$COMPLEXITY_OUTPUT_DIR"

echo "Output directory: $COMPLEXITY_OUTPUT_DIR"

# Check if specific dataset is provided
if [ $# -eq 1 ]; then
    DATASET_NAME="$1"
    echo "Analyzing specific dataset: $DATASET_NAME"
    python scripts/complexity_analysis.py --dataset "$DATASET_NAME" --output-dir "$COMPLEXITY_OUTPUT_DIR" --max-files 10 --num-workers 4
else
    echo "Analyzing all datasets (limited to 10 files per dataset for testing)"
    python scripts/complexity_analysis.py --output-dir "$COMPLEXITY_OUTPUT_DIR" --max-files 10 --num-workers 4
fi

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo "=================================================="
    echo "Complexity analysis completed successfully!"
    echo "Generated files:"
    ls -la "$COMPLEXITY_OUTPUT_DIR"
    
    # Optionally integrate with existing results
    if [ -f "data/dataframe.csv" ] || [ -f "data/dataframe.pkl" ]; then
        echo ""
        echo "Integrating with existing transcription results..."
        python scripts/integrate_complexity.py --complexity-dir "$COMPLEXITY_OUTPUT_DIR"
    else
        echo ""
        echo "No existing transcription results found. Run the main pipeline first to integrate results."
    fi
else
    echo "=================================================="
    echo "Complexity analysis failed!"
    exit 1
fi

echo "=================================================="
echo "Local Complexity Analysis Complete"
echo "==================================================" 