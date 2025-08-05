#!/bin/bash
# MASTER SCRIPT - Submit complexity analysis for all datasets
# This script submits job arrays for large-scale deployment

echo "=========================================="
echo "Complexity Analysis - Large Scale Deployment"
echo "Submitting job arrays for all datasets"
echo "=========================================="

# Check if job array script exists
if [ ! -f "run_complexity_job_array.sh" ]; then
    echo "Error: run_complexity_job_array.sh not found!"
    exit 1
fi

# Change to compute directory
cd /home/$USER/AIM/music-transcription-research/complexity_scripts/compute

# Submit job array
echo "Submitting job array for all datasets..."
JOB_ID=$(sbatch run_complexity_job_array.sh | awk '{print $4}')

echo "=========================================="
echo "Job Array Submitted Successfully!"
echo "Job ID: $JOB_ID"
echo "Array Range: 0-7 (8 datasets)"
echo "=========================================="

# Show job status
echo "Job Status:"
squeue -j $JOB_ID

echo ""
echo "To monitor progress:"
echo "  squeue -j $JOB_ID"
echo "  tail -f logs/complexity_array_${JOB_ID}_*.out"
echo "  tail -f logs/complexity_array_${JOB_ID}_*.err"
echo ""
echo "To cancel all jobs:"
echo "  scancel $JOB_ID"
echo ""
echo "To cancel specific array task:"
echo "  scancel ${JOB_ID}_0  # Cancel task 0 (slakh2100)"
echo "  scancel ${JOB_ID}_1  # Cancel task 1 (maestro)"
echo "  etc..." 