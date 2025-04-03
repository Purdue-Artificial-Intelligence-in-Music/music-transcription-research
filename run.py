#!/opt/homebrew/bin/python3
"""
Name: run.py
Purpose: Submit SLURM jobs for each team's model in the AMT competition
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import json
import subprocess
import os


def extract_slurm_id(output: str) -> str:
    """Extracts SLURM job ID from sbatch output."""
    words = output.split()
    for word in words:
        if word.isdigit():
            return word
    return ""


def submit_slurm_job(script_name: str, team_dir: str, dependency: str = None) -> str:
    """Submits a SLURM job and returns the job ID, with detailed logging."""
    sbatch_cmd = ["sbatch"]
    if team_dir == "":
        sbatch_cmd.append(f"-J{script_name}")
        sbatch_cmd.append(f"-oslurm_output-{script_name}.txt")
        # sbatch_cmd.append(f"-eslurm_error.err")
    else:
        sbatch_cmd.append(f"-J{team_dir}")
        sbatch_cmd.append(f"-o{team_dir}/competition_output/slurm_output.txt")
        # sbatch_cmd.append(f"-e{team_dir}/competition_output/slurm_error.err")

    if dependency:
        sbatch_cmd.append(f"--dependency=afterany:{dependency}")

    sbatch_cmd.extend([script_name, team_dir])

    tab = "\t" if team_dir else ""

    if team_dir:
        print(f"{tab}Submitting {script_name} job for team: {team_dir}...")
    else:
        print(f"{tab}Submitting {script_name} job...")

    if dependency:
        print(f"{tab}Dependency: Job will run after SLURM Job ID {dependency}")

    try:
        result = subprocess.run(
            sbatch_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        slurm_output = result.stdout.decode("utf-8").strip()
        print(f"{tab}SLURM Output: {slurm_output}")

        slurm_id = extract_slurm_id(slurm_output)
        if slurm_id:
            print(f"{tab}SLURM Job ID: {slurm_id}\n")
        else:
            print(f"{tab}Failed to extract SLURM job ID from output: {slurm_output}\n")

        return slurm_id

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode("utf-8")
        print(
            f"{tab}Error submitting {script_name} job for team {team_dir}: {error_msg}"
        )
        return dependency  # Keep last known dependency so the pipeline continues


def main():
    print("Starting SLURM Job Submission Process")

    last_slurm_id = None

    # Load team data
    try:
        with open("teams.json", "r") as file:
            teams = json.load(file)
        print(f"\nLoaded team data: {len(teams)} teams found.")
    except Exception as e:
        print(f"Error loading teams.json: {e}")
        return

    print(f"Current working directory: {os.getcwd()}")

    for team in teams:
        team_dir = team[2]
        print(f"\nProcessing team: {team_dir}")

        last_slurm_id = submit_slurm_job("run.sh", team_dir, last_slurm_id)

    submit_slurm_job("cleanup.sh", "", last_slurm_id)

    print("\nSLURM Job Submission Process Completed!")


if __name__ == "__main__":
    main()
