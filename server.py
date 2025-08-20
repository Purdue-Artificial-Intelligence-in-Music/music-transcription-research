#!/opt/homebrew/bin/python3
"""
Name: server.py
Purpose: Upload files to the Gilbreth/Anvil computing cluster server at Purdue University RCAC
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import os
from tqdm import tqdm

hostname = "gilbreth.rcac.purdue.edu"  # or "anvil.rcac.purdue.edu"
username = "ochaturv"  # or "x-ochaturvedi"


def execute_cmd(client, cmd):
    """Execute a remote command via SSH and return the output."""
    print(f"\nExecuting Command: {cmd}")
    _, stdout, stderr = client.exec_command(cmd)

    output = stdout.read().decode("utf-8").strip()
    error_output = stderr.read().decode("utf-8").strip()

    if output:
        print(f"STDOUT: {output}")
    if error_output:
        print(f"STDERR: {error_output}")

    exit_code = stdout.channel.recv_exit_status()
    print(f"Return Code: {exit_code}")

    return output


def main() -> None:
    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(hostname, username=username)

    scp = SCPClient(client.get_transport())

    remote_path = f"/scratch/gilbreth/{username}/research/"  # or f"/anvil/scratch/{username}/research/"

    # execute_cmd(client, f"rm -rf /scratch/gilbreth/{username}/.conda/")
    execute_cmd(client, f"rm -rf {remote_path}")
    execute_cmd(client, f"mkdir -p {remote_path}")
    print("")

    # Gather all files to upload
    files_to_upload = []

    # Gather files from the current directory
    for script in os.listdir():
        if (
            script.endswith(".sh")
            or script.endswith(".py")
            or script.endswith(".json")
            or script.endswith(".yaml")
        ) and script != "main.py":
            files_to_upload.append(script)

    # Gather files from the scripts directory
    for script in os.listdir("scripts"):
        if (
            script.endswith(".sh")
            or script.endswith(".py")
            or script.endswith(".json")
            or script.endswith(".yaml")
        ):
            files_to_upload.append(f"scripts/{script}")

    # Use tqdm to show progress
    for script in tqdm(files_to_upload, desc="Uploading files", unit="file"):
        scp.put(script, remote_path=remote_path)

    # Execute the job script
    execute_cmd(client, f"cd {remote_path} && sbatch main.sh")


if __name__ == "__main__":
    main()
