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
DATASETS_FILE = "datasets.json"
RUN_SCRIPT = "run.sh"
CLEANUP_SCRIPT = "cleanup.sh"


def extract_slurm_id(output: str) -> str:
    """Extract SLURM job ID from sbatch output."""
    return next((word for word in output.split() if word.isdigit()), "")


def submit_slurm_job(
    script_name: str, model_dir: str = "", dependency: Optional[str] = None
) -> str:
    """Submit a SLURM job and return the job ID."""
    sbatch_cmd = ["sbatch"]

    job_name = model_dir if model_dir else script_name
    output_file = (
        f"{model_dir}/research_output/slurm_output.txt"
        if model_dir
        else f"slurm_output-{script_name}.out"
    )

    sbatch_cmd.extend(["-J", job_name, "-o", output_file])
    if dependency:
        sbatch_cmd.append(f"--dependency=afterany:{dependency}")

    sbatch_cmd.extend([script_name])
    if model_dir:
        sbatch_cmd.append(model_dir)

    print(f"\nSubmitting {script_name} for model: {model_dir or '[global]'}")
    if dependency:
        print(f"  Dependency: {dependency}")

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
    if not os.path.exists(DATASETS_FILE):
        print(f"Error: {DATASETS_FILE} not found.")
        return

    try:
        with open(MODELS_FILE, "r") as f:
            model_data = json.load(f).get("values", [])[1:]
    except Exception as e:
        print(f"Error loading {MODELS_FILE}: {e}")
        return

    try:
        with open(DATASETS_FILE, "r") as f:
            dataset_data = json.load(f).get("values", [])[1:]
    except Exception as e:
        print(f"Error loading {DATASETS_FILE}: {e}")
        return

    if not model_data:
        print("No models found.")
        return
    if not dataset_data:
        print("No datasets found.")
        return

    print(f"Found {len(model_data)} models and {len(dataset_data)} datasets.")
    print(f"Current working directory: {os.getcwd()}")

    previous_job_id = None
    total_jobs_submitted = 0

    for model_row in model_data:
        model_name = model_row[0]
        print(f"\nProcessing model: {model_name}")

        for dataset_row in dataset_data:
            dataset_name, dataset_path, _, audio_type, midi_extension = dataset_row
            print(f"  - Dataset: {dataset_name}")

            sbatch_cmd = [
                "sbatch",
                "-J",
                f"{model_name}_{dataset_name}",
                "-o",
                f"{model_name}/research_output/{dataset_name}_slurm_output.txt",
            ]

            # Add dependency on previous job if it exists
            if previous_job_id:
                sbatch_cmd.append(f"--dependency=afterany:{previous_job_id}")
                print(f"    Dependency on job: {previous_job_id}")

            sbatch_cmd.extend(
                [
                    RUN_SCRIPT,
                    model_name,
                    dataset_name,
                    dataset_path,
                    audio_type,
                    midi_extension,
                ]
            )

            try:
                result = subprocess.run(
                    sbatch_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                output = result.stdout.decode().strip()
                job_id = extract_slurm_id(output)

                if job_id:
                    print(f"    Submitted SLURM job ID: {job_id}")
                    previous_job_id = job_id  # Use this job as dependency for next job
                    total_jobs_submitted += 1
                else:
                    print(
                        f"    Warning: Failed to extract job ID, continuing without dependency"
                    )

            except subprocess.CalledProcessError as e:
                print(f"    Failed to submit job: {e.stderr.decode().strip()}")

    # Submit cleanup job dependent on the last successful job
    if previous_job_id:
        print(f"\nSubmitting cleanup job dependent on final job: {previous_job_id}")
        cleanup_job_id = submit_slurm_job(CLEANUP_SCRIPT, dependency=previous_job_id)
        if cleanup_job_id:
            print(f"Cleanup job submitted with ID: {cleanup_job_id}")

    print(f"\nSLURM Job Submission Process Completed!")
    print(f"Total jobs submitted: {total_jobs_submitted}")


if __name__ == "__main__":
    main()
