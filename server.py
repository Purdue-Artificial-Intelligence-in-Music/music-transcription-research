#!/opt/homebrew/bin/python3
"""
Name: server.py
Purpose: Sync research files to an RCAC cluster (Gilbreth or Anvil) and
         optionally submit the main SLURM job.

Usage:
  python server.py                       # sync to Gilbreth + submit main.sh
  python server.py --no-submit           # sync to Gilbreth only
  python server.py --cluster anvil       # sync to Anvil (deploy only)
  python server.py --cluster both        # sync to both clusters
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import subprocess
import argparse
from paramiko import SSHClient, AutoAddPolicy

# Per-cluster connection + path settings. The transcription pipeline (main.sh
# and the per-model conda logic) is tuned for and validated on Gilbreth, so
# main.sh is auto-submitted only there. Anvil is wired up for deployment and
# for running CPU/GPU dataset builds and independent jobs; porting main.sh to
# Anvil is the next step once its build path is validated.
CLUSTERS = {
    "gilbreth": {
        "hostname": "gilbreth.rcac.purdue.edu",
        "username": "ochaturv",
        "remote_dir": "/scratch/gilbreth/ochaturv/research",
        "auto_submit_main": True,
    },
    "anvil": {
        "hostname": "anvil.rcac.purdue.edu",
        "username": "x-ochaturvedi",
        "remote_dir": "/anvil/scratch/x-ochaturvedi/research",
        "auto_submit_main": False,
    },
}

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

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


def connect(cfg):
    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(cfg["hostname"], username=cfg["username"])
    return client


def sync_files(client, cfg):
    remote_dir = cfg["remote_dir"]
    execute_cmd(client, f"rm -rf {remote_dir}")
    execute_cmd(client, f"mkdir -p {remote_dir}")

    cmd = ["rsync", "-avz", "--progress"]
    for exc in RSYNC_EXCLUDES:
        cmd += ["--exclude", exc]
    cmd += [f"{LOCAL_DIR}/", f"{cfg['username']}@{cfg['hostname']}:{remote_dir}/"]

    print(f"\nSyncing {LOCAL_DIR}/ -> {cfg['hostname']}:{remote_dir}/")
    subprocess.run(cmd, check=True)
    print("Sync complete.")


def deploy(name, submit):
    cfg = CLUSTERS[name]
    print(f"\n========== {name.upper()} ==========")
    client = connect(cfg)
    sync_files(client, cfg)

    if submit and cfg["auto_submit_main"]:
        execute_cmd(client, f"cd {cfg['remote_dir']} && sbatch scripts/main.sh")
    elif submit and not cfg["auto_submit_main"]:
        print(
            f"[note] {name} is deploy-only; main.sh is not auto-submitted here. "
            "Submit dataset/transcription jobs explicitly with the appropriate "
            "-A/-p flags for this cluster."
        )

    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync research files to RCAC clusters.")
    parser.add_argument(
        "--cluster",
        choices=["gilbreth", "anvil", "both"],
        default="gilbreth",
        help="Which cluster(s) to deploy to (default: gilbreth)",
    )
    parser.add_argument(
        "--no-submit",
        action="store_true",
        help="Sync files only, do not submit the main SLURM job",
    )
    args = parser.parse_args()

    targets = ["gilbreth", "anvil"] if args.cluster == "both" else [args.cluster]
    for name in targets:
        deploy(name, submit=not args.no_submit)


if __name__ == "__main__":
    main()
