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
import math

CHUNK_SIZE = 1500
MODELS_FILE = "models.json"
DATASETS_FILE = "datasets.json"
RUN_SCRIPT = "run.sh"
UPLOAD_SCRIPT = "upload.sh"
NOTIFICATION_SCRIPT = "notification.sh"


def extract_slurm_id(output: str) -> str:
    """Extract SLURM job ID from sbatch output."""
    return next((word for word in output.split() if word.isdigit()), "")


def submit_job(command):
    """Run sbatch command and return job ID if successful."""
    try:
        result = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = result.stdout.decode().strip()
        return extract_slurm_id(output)
    except subprocess.CalledProcessError as e:
        print(f"\tFailed to submit job: {e.stderr.decode().strip()}")
        return None


def main():
    print("Starting SLURM Job Submission Process")

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

    total_jobs_submitted = 0
    all_upload_ids = []

    # Sort models by reverse alphabetical order
    model_data.sort(key=lambda x: x[0], reverse=True)

    for dataset_row in dataset_data:
        dataset_name, dataset_path, dataset_instrument, audio_type, _ = dataset_row
        print(f"\nProcessing dataset: {dataset_name}")

        list_file_path = f"{dataset_path}.txt"
        if not os.path.isfile(list_file_path):
            print(f"\t- Missing file list: {list_file_path}, skipping dataset.")
            continue

        with open(list_file_path, "r") as f:
            all_files = [line.strip() for line in f if line.strip()]

        total_files = len(all_files)
        num_chunks = math.ceil(total_files / CHUNK_SIZE)
        print(f"\t- Total files: {total_files}, Chunks: {num_chunks}")

        chunk_dir = f"chunks/{dataset_name}"
        os.makedirs(chunk_dir, exist_ok=True)

        for model_row in model_data:
            model_name, instrument_type, training_datasets, completed_datasets = (
                model_row
            )
            print(f"\tProcessing model: {model_name}")

            training_datasets = set(
                training_datasets if isinstance(training_datasets, list) else []
            )
            completed_datasets = set(
                completed_datasets if isinstance(completed_datasets, list) else []
            )

            if dataset_name in training_datasets:
                print(f"\t\t- Skipping: {dataset_name} used for training {model_name}.")
                continue

            if dataset_name in completed_datasets:
                print(
                    f"\t\t- Skipping: {dataset_name} already completed for {model_name}."
                )
                continue

            if instrument_type == "Piano" and dataset_instrument != "Piano":
                print(f"\t\t- Skipping: model and dataset instrument mismatch.")
                continue

            chunk_job_ids = []

            for i in range(num_chunks):
                chunk_files = all_files[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
                chunk_path = os.path.abspath(f"{chunk_dir}/chunk_{i:03d}.txt")

                with open(chunk_path, "w") as chunk_file:
                    chunk_file.write("\n".join(chunk_files) + "\n")

                job_name = f"{model_name}_{dataset_name}_chunk{i:03d}"
                output_file = f"{model_name}/research_output/{dataset_name}_chunk{i:03d}_slurm_output.txt"

                sbatch_cmd = [
                    "sbatch",
                    "-J",
                    job_name,
                    "-o",
                    output_file,
                    RUN_SCRIPT,
                    model_name,
                    dataset_name,
                    dataset_path,
                    audio_type,
                    chunk_path,
                ]

                job_id = submit_job(sbatch_cmd)
                if job_id:
                    chunk_job_ids.append(job_id)
                    total_jobs_submitted += 1
                    print(
                        f"\t\t- Submitted chunk {i + 1}/{num_chunks} as job ID: {job_id}"
                    )
                else:
                    print(f"\t\t- Failed to submit chunk {i + 1}/{num_chunks}")

            if chunk_job_ids:
                dependency_str = ":".join(chunk_job_ids)
                upload_job_name = f"Upload-{model_name}-{dataset_name}"
                upload_cmd = [
                    "sbatch",
                    "-J",
                    upload_job_name,
                    "--dependency=afterany:" + dependency_str,
                    UPLOAD_SCRIPT,
                    model_name,
                    dataset_name,
                ]

                upload_job_id = submit_job(upload_cmd)
                if upload_job_id:
                    print(f"\t\t- Upload job submitted (Job ID: {upload_job_id})")
                    total_jobs_submitted += 1
                    all_upload_ids.append(upload_job_id)
                else:
                    print(f"\t\t- Failed to submit upload job.")

    # Submit final notification job
    if all_upload_ids:
        dependency_str = ":".join(all_upload_ids)
        notify_cmd = [
            "sbatch",
            "-J",
            "Notify",
            "--dependency=afterany:" + dependency_str,
            NOTIFICATION_SCRIPT,
        ]

        notification_job_id = submit_job(notify_cmd)
        if notification_job_id:
            print(f"\nNotification job submitted! Job ID: {notification_job_id}")
            total_jobs_submitted += 1
        else:
            print("\nFailed to submit notification job.")
    else:
        print("\nNo upload jobs submitted, so skipping notification job.")

    print("\nSLURM Job Submission Complete.")
    print(f"Total jobs submitted: {total_jobs_submitted}")

    with open("jobs_submitted.txt", "w") as f:
        f.write(str(total_jobs_submitted))


if __name__ == "__main__":
    main()
