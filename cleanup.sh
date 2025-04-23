#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00

echo "--------------------------------------------------"
echo "Running cleanup for teams"

mapfile -t lines < <(jq -c '.[]' teams.json)
for line in "${lines[@]}"; do
    TEAM_NAME=$(echo "$line" | jq -r '.[2]')
    rm -rf "$TEAM_NAME"
    echo "Removed directory $TEAM_NAME"
done

rm -rf teams.json

echo "--------------------------------------------------"
echo "Script execution completed!"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Cleaned up all of the repositories\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Cleaned up all of the repositories" -H "Title: Cleanup script execution" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
