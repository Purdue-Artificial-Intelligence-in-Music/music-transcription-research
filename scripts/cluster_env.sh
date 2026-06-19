#!/bin/bash
# cluster_env.sh — detect the RCAC cluster and export shared paths plus a
# module-loading function. Source this near the top of a job script:
#
#     source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"
#     load_modules
#
# Detection is by filesystem sentinel rather than hostname, since compute-node
# hostnames are not reliably cluster-tagged: /anvil exists only on Anvil and
# /depot/yunglu only on Gilbreth. DATA_ROOT/CONDA_ROOT can be pre-set by the
# caller to override the defaults.

if [ -d /anvil ]; then
    export CLUSTER="anvil"
    export DATA_ROOT="${DATA_ROOT:-/anvil/scratch/x-ochaturvedi/transcription}"
    export CONDA_ROOT="${CONDA_ROOT:-/anvil/scratch/x-ochaturvedi/.conda}"
    load_modules() {
        # Anvil exposes conda/parallel/ffmpeg directly (no "external" module).
        module load conda parallel ffmpeg 2>/dev/null
        source "$(conda info --base)/etc/profile.d/conda.sh"
    }
elif [ -d /depot/yunglu ]; then
    export CLUSTER="gilbreth"
    export DATA_ROOT="${DATA_ROOT:-/depot/yunglu/data/transcription}"
    export CONDA_ROOT="${CONDA_ROOT:-/scratch/gilbreth/ochaturv/.conda}"
    load_modules() {
        # Gilbreth R9: conda/parallel live under the "external" module tree.
        source /etc/profile.d/modules.sh
        module load external
        module load conda parallel ffmpeg gcc
        source "$(conda info --base)/etc/profile.d/conda.sh"
    }
else
    export CLUSTER="unknown"
    export DATA_ROOT="${DATA_ROOT:-$(pwd)}"
    export CONDA_ROOT="${CONDA_ROOT:-$HOME/.conda}"
    load_modules() { :; }
fi

echo "[cluster_env] CLUSTER=$CLUSTER DATA_ROOT=$DATA_ROOT CONDA_ROOT=$CONDA_ROOT"
