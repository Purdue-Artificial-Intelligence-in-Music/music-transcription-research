#!/usr/bin/env python3
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

# Smaller chunks -> shorter per-job runtime -> the jobs backfill into gaps on a
# heavily-contended, fully-reserved partition (Anvil's gpu queue had ~1670
# pending jobs and every free GPU was PLANNED for higher-priority jobs). A
# 250-file chunk runs in a few hours instead of most of a day.
CHUNK_SIZE = 250
MODELS_FILE = "models.json"
DATASETS_FILE = "datasets.json"
RUN_SCRIPT = "scripts/run.sh"
UPLOAD_SCRIPT = "scripts/upload.sh"
NOTIFICATION_SCRIPT = "scripts/notification.sh"

# Optional cap on how many array tasks (chunks) a single model/dataset array may
# run at once. None = let the SLURM allocation throttle naturally. On the normal
# QOS yunglu only has 3 GPUs, so the allocation caps real concurrency anyway;
# this just keeps the scheduler view tidy if set.
ARRAY_THROTTLE = None


def gpu_flags():
    """SLURM account/partition/QOS for GPU jobs, from cluster_env.sh exports."""
    flags = []
    if os.environ.get("GPU_ACCOUNT"):
        flags += ["-A", os.environ["GPU_ACCOUNT"]]
    if os.environ.get("GPU_PARTITION"):
        flags += ["-p", os.environ["GPU_PARTITION"]]
    if os.environ.get("GPU_QOS"):
        flags += ["--qos", os.environ["GPU_QOS"]]
    # Per-cluster memory (run.sh hardcodes 240G, which is too large for Anvil's
    # shared GPU nodes; cluster_env.sh sets GPU_MEM to a schedulable size).
    if os.environ.get("GPU_MEM"):
        flags += ["--mem", os.environ["GPU_MEM"]]
    return flags


def support_flags():
    """SLURM flags for support jobs (upload/notify). On Gilbreth this is the
    preemptible standby QOS with a forced GPU; on Anvil it's a CPU partition."""
    flags = []
    if os.environ.get("SUPPORT_ACCOUNT"):
        flags += ["-A", os.environ["SUPPORT_ACCOUNT"]]
    if os.environ.get("SUPPORT_PARTITION"):
        flags += ["-p", os.environ["SUPPORT_PARTITION"]]
    if os.environ.get("SUPPORT_QOS"):
        flags += ["--qos", os.environ["SUPPORT_QOS"]]
    if os.environ.get("SUPPORT_GRES"):
        flags += [f"--gres={os.environ['SUPPORT_GRES']}"]
    return flags


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

        if num_chunks == 0:
            print(f"\t- No files to process for {dataset_name}, skipping.")
            continue

        # Chunk contents depend only on the dataset's file list, so write them
        # once here and reuse the same chunk directory for every model.
        chunk_dir = os.path.abspath(f"chunks/{dataset_name}")
        os.makedirs(chunk_dir, exist_ok=True)
        for i in range(num_chunks):
            chunk_files = all_files[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
            with open(f"{chunk_dir}/chunk_{i:03d}.txt", "w") as chunk_file:
                chunk_file.write("\n".join(chunk_files) + "\n")

        # SLURM array spec: one task per chunk (0-indexed), optionally throttled.
        array_spec = f"0-{num_chunks - 1}"
        if ARRAY_THROTTLE:
            array_spec += f"%{ARRAY_THROTTLE}"

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

            # sbatch -o won't create missing parent directories.
            os.makedirs(f"{model_name}/research_output", exist_ok=True)

            # Submit all chunks as a single SLURM array job. run.sh selects its
            # chunk from $SLURM_ARRAY_TASK_ID inside the shared chunk directory.
            job_name = f"{model_name}_{dataset_name}"
            output_file = (
                f"{model_name}/research_output/{dataset_name}_chunk%a_slurm_output.txt"
            )

            sbatch_cmd = [
                "sbatch",
                *gpu_flags(),
                "-J",
                job_name,
                "-o",
                output_file,
                f"--array={array_spec}",
                RUN_SCRIPT,
                model_name,
                dataset_name,
                dataset_path,
                audio_type,
                chunk_dir,
            ]

            array_job_id = submit_job(sbatch_cmd)
            if not array_job_id:
                print(f"\t\t- Failed to submit array job for {model_name}.")
                continue

            total_jobs_submitted += 1
            print(
                f"\t\t- Submitted array job {array_job_id} ({num_chunks} chunk task(s))"
            )

            # Upload waits for every task in the array to finish (afterany).
            upload_job_name = f"Upload-{model_name}-{dataset_name}"
            upload_cmd = [
                "sbatch",
                *support_flags(),
                "-J",
                upload_job_name,
                "--dependency=afterany:" + array_job_id,
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
            *support_flags(),
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
