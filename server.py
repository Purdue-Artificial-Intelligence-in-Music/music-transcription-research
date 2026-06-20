#!/opt/homebrew/bin/python3
"""
Name: server.py
Purpose: Deploy the research pipeline to RCAC clusters (Gilbreth / Anvil) and
         optionally distribute the model x dataset workload across both.

Usage:
  python server.py                       # sync to Gilbreth + submit main.sh
  python server.py --no-submit           # sync to Gilbreth only
  python server.py --cluster anvil       # sync to Anvil only
  python server.py --cluster both        # sync to both clusters
  python server.py --distribute          # auto-split datasets across BOTH
                                         #   clusters by capacity, then launch
  python server.py --distribute --dry-run  # show the plan, don't deploy/launch
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import os
import json
import subprocess
import argparse
from paramiko import SSHClient, AutoAddPolicy

# Per-cluster settings.
#   data_root    : where datasets (and their <name>.txt lists) live on that cluster
#   max_gpus     : relative GPU capacity weight used to balance the workload
#                  (Gilbreth's yunglu allocation = 3 A100; Anvil has far more)
#   sbatch_flags : account/partition flags injected when launching main.sh there
CLUSTERS = {
    "gilbreth": {
        "hostname": "gilbreth.rcac.purdue.edu",
        "username": "ochaturv",
        "remote_dir": "/scratch/gilbreth/ochaturv/research",
        "data_root": "/depot/yunglu/data/transcription",
        "max_gpus": 3,
        "sbatch_flags": ["-A", "yunglu", "-p", "a100-80gb"],
        "auto_submit_main": True,
    },
    "anvil": {
        "hostname": "anvil.rcac.purdue.edu",
        "username": "x-ochaturvedi",
        "remote_dir": "/anvil/scratch/x-ochaturvedi/research",
        "data_root": "/anvil/scratch/x-ochaturvedi/transcription",
        "max_gpus": 8,
        "sbatch_flags": ["-A", "cis240587-gpu", "-p", "gpu"],
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


def execute_cmd(client, cmd, quiet=False):
    """Execute a remote SSH command; return stdout (stripped)."""
    if not quiet:
        print(f"\nExecuting: {cmd}")
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8").strip()
    err = stderr.read().decode("utf-8").strip()
    if not quiet:
        if out:
            print(f"STDOUT: {out}")
        if err:
            print(f"STDERR: {err}")
        print(f"Return Code: {stdout.channel.recv_exit_status()}")
    else:
        stdout.channel.recv_exit_status()
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


# --------------------------------------------------------------------------
# Single-cluster deploy (existing behavior)
# --------------------------------------------------------------------------
def deploy(name, submit):
    cfg = CLUSTERS[name]
    print(f"\n========== {name.upper()} ==========")
    client = connect(cfg)
    sync_files(client, cfg)

    if submit and cfg["auto_submit_main"]:
        flags = " ".join(cfg["sbatch_flags"])
        execute_cmd(client, f"cd {cfg['remote_dir']} && sbatch {flags} scripts/main.sh")
    elif submit and not cfg["auto_submit_main"]:
        print(
            f"[note] {name} is deploy-only here; use --distribute to launch work "
            "on it, or submit jobs manually with its -A/-p flags."
        )
    client.close()


# --------------------------------------------------------------------------
# Cross-cluster distribution
# --------------------------------------------------------------------------
def load_local_values(name):
    with open(os.path.join(LOCAL_DIR, name)) as f:
        return json.load(f)["values"]


def eligible_model_count(ds_name, ds_instrument, model_rows):
    """Number of models run.py would actually run on this dataset (same skip
    logic: training overlap, already-completed, piano/instrument mismatch)."""
    n = 0
    for row in model_rows:
        _, instrument, training, completed = row
        if ds_name in set(training or []):
            continue
        if ds_name in set(completed or []):
            continue
        if instrument == "Piano" and ds_instrument != "Piano":
            continue
        n += 1
    return n


def build_work_items(dataset_rows, model_rows):
    items = []
    for row in dataset_rows:
        name, loc, instrument, audio, count = row[:5]
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        em = eligible_model_count(name, instrument, model_rows)
        items.append(
            {
                "name": name,
                "instrument": instrument,
                "audio": audio,
                "count": count,
                "dir": os.path.basename(loc.rstrip("/")),
                "eligible_models": em,
                "work": count * em,
            }
        )
    return items


def available_dataset_dirs(client, data_root, dirs):
    """Return the set of dataset dirs that have a non-empty <dir>.txt list on
    this cluster (i.e. were actually built there)."""
    if not dirs:
        return set()
    checks = " ; ".join(f'[ -s "{data_root}/{d}.txt" ] && echo "{d}"' for d in dirs)
    out = execute_cmd(client, checks, quiet=True)
    return set(out.split())


def assign_datasets(items, availability, capacity):
    """Greedy longest-processing-time: place each dataset (largest work first)
    on the available cluster with the lowest projected load/capacity ratio."""
    assignments = {c: [] for c in capacity}
    load = {c: 0.0 for c in capacity}
    skipped = []
    for item in sorted(items, key=lambda x: x["work"], reverse=True):
        candidates = [
            c for c in capacity if item["dir"] in availability.get(c, set())
        ]
        if not candidates:
            skipped.append(item["name"])
            continue
        best = min(candidates, key=lambda c: (load[c] + item["work"]) / capacity[c])
        assignments[best].append(item)
        load[best] += item["work"]
    return assignments, load, skipped


def distribute(submit=True, dry_run=False):
    model_rows = load_local_values("models.json")[1:]
    dataset_header, *dataset_rows = load_local_values("datasets.json")
    items = build_work_items(dataset_rows, model_rows)
    dirs = [i["dir"] for i in items]

    print("Model x dataset workload (file_count x eligible_models):")
    for i in sorted(items, key=lambda x: x["work"], reverse=True):
        print(f"  {i['name']:<22} files={i['count']:>7} x models={i['eligible_models']} = {i['work']}")

    clients, availability, capacity = {}, {}, {}
    for name, cfg in CLUSTERS.items():
        clients[name] = connect(cfg)
        availability[name] = available_dataset_dirs(clients[name], cfg["data_root"], dirs)
        capacity[name] = cfg["max_gpus"]
        print(f"\n[{name}] built datasets: {sorted(availability[name]) or '(none)'}")

    assignments, load, skipped = assign_datasets(items, availability, capacity)

    print("\n================ DISTRIBUTION PLAN ================")
    for name, assigned in assignments.items():
        print(
            f"[{name}] cap={capacity[name]}  load={int(load[name])}  "
            f"datasets: {', '.join(i['name'] for i in assigned) or '(none)'}"
        )
    if skipped:
        print(f"[skipped] not built on any cluster: {', '.join(skipped)}")
    print("==================================================")

    if dry_run:
        print("\n[dry-run] no files deployed, no jobs submitted.")
        for c in clients.values():
            c.close()
        return

    for name, assigned in assignments.items():
        cfg = CLUSTERS[name]
        client = clients[name]
        if not assigned:
            print(f"\n[{name}] nothing assigned; skipping.")
            continue
        print(f"\n========== DEPLOY + LAUNCH: {name.upper()} ==========")
        sync_files(client, cfg)

        # Per-cluster datasets.json subset, with paths rewritten to this cluster.
        subset = {
            "values": [dataset_header]
            + [
                [
                    i["name"],
                    f"{cfg['data_root']}/{i['dir']}",
                    i["instrument"],
                    i["audio"],
                    str(i["count"]),
                ]
                for i in assigned
            ]
        }
        sftp = client.open_sftp()
        with sftp.open(f"{cfg['remote_dir']}/datasets.json", "w") as f:
            f.write(json.dumps(subset, indent=4))
        sftp.close()
        print(f"Wrote {len(assigned)}-dataset datasets.json for {name}")

        if submit:
            flags = " ".join(cfg["sbatch_flags"])
            execute_cmd(client, f"cd {cfg['remote_dir']} && sbatch {flags} scripts/main.sh")

    for c in clients.values():
        c.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy/distribute the research pipeline.")
    parser.add_argument(
        "--cluster",
        choices=["gilbreth", "anvil", "both"],
        default="gilbreth",
        help="Single-cluster deploy target (ignored with --distribute)",
    )
    parser.add_argument(
        "--distribute",
        action="store_true",
        help="Auto-split datasets across both clusters by capacity and launch",
    )
    parser.add_argument(
        "--no-submit",
        action="store_true",
        help="Sync files only, do not submit the main SLURM job",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --distribute: print the plan without deploying or submitting",
    )
    args = parser.parse_args()

    if args.distribute:
        distribute(submit=not args.no_submit, dry_run=args.dry_run)
    else:
        targets = ["gilbreth", "anvil"] if args.cluster == "both" else [args.cluster]
        for name in targets:
            deploy(name, submit=not args.no_submit)


if __name__ == "__main__":
    main()
