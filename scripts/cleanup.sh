#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH -J cleanup
#SBATCH -o cleanup_output.txt

set -euo pipefail
trap 'echo "Cleanup script terminated unexpectedly."; exit 1' ERR

echo "--------------------------------------------------"
echo "Starting cleanup for all model directories"

MODELS_FILE="models.json"

if [ ! -f "$MODELS_FILE" ]; then
    echo "Error: $MODELS_FILE not found. Nothing to clean."
    exit 0
fi

# Read only model rows (skip header)
mapfile -t lines < <(jq -c '.values[1:][]' "$MODELS_FILE")

for line in "${lines[@]}"; do
    MODEL_NAME=$(echo "$line" | jq -r '.[0]')

    if [ -n "$MODEL_NAME" ] && [ -d "$MODEL_NAME" ]; then
        rm -rf "$MODEL_NAME"
        echo "Removed directory: $MODEL_NAME"
    else
        echo "Directory not found or invalid name: '$MODEL_NAME'"
    fi
done

echo "--------------------------------------------------"
echo "Cleanup script execution completed successfully!"
# curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Cleaned up all of the repositories\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
# curl -s -d "Cleaned up all of the repositories" -H "Title: Cleanup script execution" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt >/dev/null
