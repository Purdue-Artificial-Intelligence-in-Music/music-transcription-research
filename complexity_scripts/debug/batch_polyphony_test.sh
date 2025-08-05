#!/bin/bash
#SBATCH --job-name=polyphony_test
#SBATCH --output=polyphony_test_%j.out
#SBATCH --error=polyphony_test_%j.err
#SBATCH --time=00:30:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gres=gpu:1
#SBATCH --account=yunglu-k

# Set working directory
cd /home/shang33/AIM/music-transcription-research

# Run the batch test (using system Python)
echo "Starting batch polyphony test at $(date)"
python3 batch_polyphony_test.py > polyphony_test_results.txt 2>&1

# Send Discord notification
runtime=$(($SECONDS))
runtime_formatted=$(printf "%02d:%02d:%02d" $((runtime/3600)) $((runtime%3600/60)) $((runtime%60)))

echo "Batch polyphony test completed at $(date)"
echo "Results saved to: polyphony_test_results.txt" 