#!/opt/homebrew/bin/python3
"""
Name: server.py
Purpose: Sync research files to Gilbreth and optionally submit the main SLURM job.

Usage:
  python server.py              # sync files + submit sbatch job
  python server.py --no-submit  # sync files only
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import subprocess
import argparse
from paramiko import SSHClient, AutoAddPolicy

# For Gilbreth
hostname = "gilbreth.rcac.purdue.edu"
username = "ochaturv"

# For Anvil
# hostname = "anvil.rcac.purdue.edu"
# username = "x-ochaturvedi"

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
REMOTE_DIR = f"/scratch/gilbreth/{username}/research"
# REMOTE_DIR = f"/anvil/scratch/{username}/research"

RSYNC_EXCLUDES = [
    ".git/",
    "__pycache__/",
    "*.pyc",
    ".DS_Store",
    "data/",
    "poster/",
    "archive/",
    "results.pdf",
    "results.tex",
    "server.py",
]


def execute_cmd(client, cmd):
    """Execute a remote SSH command and print output."""
    print(f"\nExecuting: {cmd}")
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8").strip()
    err = stderr.read().decode("utf-8").strip()
    if out:
        print(f"STDOUT: {out}")
    if err:
        print(f"STDERR: {err}")
    exit_code = stdout.channel.recv_exit_status()
    print(f"Return Code: {exit_code}")
    return out


def sync_files(client):
    execute_cmd(client, f"rm -rf {REMOTE_DIR}")
    execute_cmd(client, f"mkdir -p {REMOTE_DIR}")

    cmd = ["rsync", "-avz", "--progress"]
    for exc in RSYNC_EXCLUDES:
        cmd += ["--exclude", exc]
    cmd += [f"{LOCAL_DIR}/", f"{username}@{hostname}:{REMOTE_DIR}/"]

    print(f"\nSyncing {LOCAL_DIR}/ → {REMOTE_DIR}/")
    subprocess.run(cmd, check=True)
    print("Sync complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync research files to Gilbreth.")
    parser.add_argument(
        "--no-submit", action="store_true", help="Sync files only, do not submit SLURM job"
    )
    args = parser.parse_args()

    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(hostname, username=username)

    sync_files(client)

    if not args.no_submit:
        execute_cmd(client, f"cd {REMOTE_DIR} && sbatch scripts/main.sh")

    client.close()


if __name__ == "__main__":
    main()
