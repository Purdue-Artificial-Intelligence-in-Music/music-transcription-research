#!/opt/homebrew/bin/python3
"""
Name: run.py
Purpose: Submit SLURM jobs for each model in the AMT research paper
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import json
import subprocess
import os
from typing import Optional

MODELS_FILE = "models.json"
RUN_SCRIPT = "run.sh"
CLEANUP_SCRIPT = "cleanup.sh"


def extract_slurm_id(output: str) -> str:
    """Extract SLURM job ID from sbatch output."""
    return next((word for word in output.split() if word.isdigit()), "")


def submit_slurm_job(
    script_name: str, team_dir: str = "", dependency: Optional[str] = None
) -> str:
    """Submit a SLURM job and return the job ID."""
    sbatch_cmd = ["sbatch"]

    job_name = team_dir if team_dir else script_name
    output_file = (
        f"{team_dir}/research_output/slurm_output.txt"
        if team_dir
        else f"slurm_output-{script_name}.txt"
    )

    sbatch_cmd.extend(["-J", job_name, "-o", output_file])
    if dependency:
        sbatch_cmd.append(f"--dependency=afterany:{dependency}")

    sbatch_cmd.extend([script_name])
    if team_dir:
        sbatch_cmd.append(team_dir)

    print(f"\nSubmitting {script_name} for team: {team_dir or '[global]'}")
    if dependency:
        print(f"  Dependency: afterany:{dependency}")

    try:
        result = subprocess.run(
            sbatch_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        slurm_output = result.stdout.decode("utf-8").strip()
        print(f"  SLURM Output: {slurm_output}")

        slurm_id = extract_slurm_id(slurm_output)
        if slurm_id:
            print(f"  SLURM Job ID: {slurm_id}")
        else:
            print("  Warning: Failed to extract job ID from SLURM output.")

        return slurm_id

    except subprocess.CalledProcessError as e:
        print(f"  Error submitting job: {e.stderr.decode('utf-8')}")
        return dependency or ""  # Allow pipeline to continue


def main():
    print("Starting SLURM Job Submission Process\n")

    if not os.path.exists(MODELS_FILE):
        print(f"Error: {MODELS_FILE} not found.")
        return

    try:
        with open(MODELS_FILE, "r") as f:
            data = json.load(f)
            teams = data.get("values", [])[1:]  # Skip header
    except Exception as e:
        print(f"Error loading {MODELS_FILE}: {e}")
        return

    if not teams:
        print("No teams found in the JSON file.")
        return

    print(f"Found {len(teams)} teams in {MODELS_FILE}.")
    print(f"Current working directory: {os.getcwd()}")

    last_job_id = None

    for team in teams:
        team_dir = team[0]
        print(f"\nProcessing team: {team_dir}")
        last_job_id = submit_slurm_job(RUN_SCRIPT, team_dir, last_job_id)

    # Submit final cleanup job after all team jobs complete
    submit_slurm_job(CLEANUP_SCRIPT, dependency=last_job_id)

    print("\nSLURM Job Submission Process Completed!")


if __name__ == "__main__":
    main()
