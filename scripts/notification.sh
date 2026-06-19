#!/bin/bash
# This job only fires a Discord webhook. run.py submits it with cluster-
# appropriate account/partition/QOS (Gilbreth: preemptible standby + forced GPU;
# Anvil: CPU shared partition) via support_flags(). Resources below are defaults.
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH -J Notify
#SBATCH -o 0_notify_output.out

source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"

# Send final notification
notify "**[$CLUSTER] All jobs have finished running**" mention
