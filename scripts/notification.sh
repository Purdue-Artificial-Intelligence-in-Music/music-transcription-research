#!/bin/bash
#SBATCH -p gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00

# Send final notification

curl -s -X POST -H "Content-Type: application/json" -d "{
\"content\": \"<@746026689397653534> **All jobs have finished running**\",
\"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\",
\"allowed_mentions\": {
    \"users\": [\"746026689397653534\"]
}
}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux >/dev/null
