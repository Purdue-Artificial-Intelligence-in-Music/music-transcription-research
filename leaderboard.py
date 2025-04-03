#!/opt/homebrew/bin/python3
"""
Name: leaderboard.py
Purpose: To process the details of each team's submission from the competition and update the leaderboard
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"


import csv
import json
import statistics
from pathlib import Path

JSON_FILE = "../teams.json"
SCOREBOARD_CSV = Path("transcription/leaderboard/leaderboard.csv")
DETAILS_JSON_DIR = Path("transcription/leaderboard/data")
DETAILS_JSON_DIR.mkdir(parents=True, exist_ok=True)


def parse_details(details_path):
    scores = {
        "Team Name": None,
        "Runtime": None,
        "Performance Score": None,
    }
    stat_totals = {}

    with open(details_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("Team Name:"):
                scores["Team Name"] = line.split(":", 1)[1].strip()
            elif line.startswith("Average runtime per file:"):
                scores["Runtime"] = float(line.split(":", 1)[1].split()[0])
            elif line.startswith("Average F-measure per file:"):
                scores["Performance Score"] = float(line.split(":", 1)[1].strip())
            elif any(
                stat in line
                for stat in [
                    "Precision",
                    "Recall",
                    "F-measure",
                    "Average_Overlap_Ratio",
                    "Onset_Precision",
                    "Onset_Recall",
                    "Onset_F-measure",
                    "Offset_Precision",
                    "Offset_Recall",
                    "Offset_F-measure",
                    "Precision_no_offset",
                    "Recall_no_offset",
                    "F-measure_no_offset",
                    "Average_Overlap_Ratio_no_offset",
                ]
            ):
                try:
                    key, val = line.split(":")
                    stat_totals.setdefault(key.strip(), []).append(float(val.strip()))
                except ValueError:
                    continue

    # Average each stat
    for key, values in stat_totals.items():
        scores[key] = round(statistics.mean(values), 6)

    return scores


def load_scoreboard():
    if not SCOREBOARD_CSV.exists():
        return []
    with open(SCOREBOARD_CSV, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_scoreboard(scoreboard):
    with open(SCOREBOARD_CSV, "w", newline="") as f:
        fieldnames = [
            "Team Name",
            "Team Members",
            "Submission Date",
            "Runtime",
            "Performance Score",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in scoreboard:
            writer.writerow(row)


def main():
    with open(JSON_FILE) as f:
        submissions = json.load(f)

    scoreboard = load_scoreboard()

    for sub in submissions:
        submission_date, _, team_name, team_members, _, _, _, _, _, _ = sub
        team_dir = Path(team_name)
        print(f"Processing {team_name}...")
        details_file = Path("..") / team_dir / "competition_output/details.txt"

        if not details_file.exists():
            print(f"[SKIP] {team_name}: details.txt not found")
            continue

        try:
            scores = parse_details(details_file)
            scores["Team Members"] = team_members
            scores["Submission Date"] = submission_date

            new_score = float(scores["Performance Score"])

            # Avoid exact duplicates (same team, same score)
            is_duplicate = any(
                row["Team Name"] == team_name
                and float(row["Performance Score"]) == new_score
                for row in scoreboard
            )

            if not is_duplicate:
                scoreboard.append(
                    {
                        "Team Name": scores["Team Name"],
                        "Team Members": team_members,
                        "Submission Date": submission_date,
                        "Runtime": scores["Runtime"],
                        "Performance Score": new_score,
                    }
                )

                # Save or update JSON entry for this team
                json_path = DETAILS_JSON_DIR / f"{team_name}.json"
                if json_path.exists():
                    with open(json_path) as jf:
                        existing_data = json.load(jf)
                else:
                    existing_data = []

                already_in_json = any(
                    float(entry.get("Performance Score", -1)) == new_score
                    for entry in existing_data
                )

                if not already_in_json:
                    existing_data.append(scores)
                    with open(json_path, "w") as jf:
                        json.dump(existing_data, jf, indent=4)

                print(f"[ADDED] {team_name} with score {new_score}")
            else:
                print(f"[SKIP] {team_name} with score {new_score} - already recorded")
        except Exception as e:
            print(f"[ERROR] {team_name}: {e}")

    write_scoreboard(scoreboard)


if __name__ == "__main__":
    main()
