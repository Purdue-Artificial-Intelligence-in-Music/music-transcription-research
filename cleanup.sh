#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00

echo "--------------------------------------------------"
echo "Running leaderboard update script"

source /etc/profile.d/modules.sh
module --force purge
module load external
module load ffmpeg
module load conda

echo "--------------------------------------------------"
echo "Cloning the website repository"

MAIN_REPO_URL="https://github.com/ai4musicians/ai4musicians.github.io.git"
MAIN_REPO_PAT="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"

if [[ -z "$MAIN_REPO_URL" || -z "$MAIN_REPO_PAT" ]]; then
    echo "MAIN_REPO_URL and MAIN_REPO_PAT must be set as environment variables."
    exit 1
fi

AUTH_REPO_URL="${MAIN_REPO_URL/https:\/\/github.com/https:\/\/$MAIN_REPO_PAT@github.com}"
REPO_NAME=$(basename "$MAIN_REPO_URL" .git)

rm -rf "$REPO_NAME"
git clone "$AUTH_REPO_URL"
cd "$REPO_NAME"

echo "--------------------------------------------------"
echo "Updating the leaderboard"

# Run the Python script from inside the repo
python3 ../leaderboard.py

echo "--------------------------------------------------"
echo "Pushing changes to the leaderboard"

git config user.email "ojaschaturvedi06@gmail.com"
git config user.name "Ojas Chaturvedi"

# Commit & push if there are changes
if [[ -n "$(git status --porcelain)" ]]; then
    git status
    git add transcription
    git commit -m "AMT models run - $(date -Iseconds)"
    git push
else
    echo "No changes to commit."
fi

cd ../
rm -rf "$REPO_NAME"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Updated the leaderboard\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Updated the leaderboard" -H "Title: Leaderboard Update" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt

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
echo "Scipt execution completed!"

curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"Cleaned up all of the repositories\", \"avatar_url\": \"https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png\"}" https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux
curl -d "Cleaned up all of the repositories" -H "Title: Cleanup script execution" -H "Priority: default" -H "Topic: gilbreth-notify-amt" ntfy.sh/gilbreth-notify-amt
