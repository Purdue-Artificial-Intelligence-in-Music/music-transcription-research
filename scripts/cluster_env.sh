#!/bin/bash
# cluster_env.sh — single source of truth for cluster-specific settings.
# Source this near the top of any job script:
#
#     source "${SLURM_SUBMIT_DIR:-$(pwd)}/scripts/cluster_env.sh"
#     load_modules
#
# It exports paths, SLURM account/partition/QOS choices, a module loader, and a
# notify() helper used for real-time Discord updates. Detection is by filesystem
# sentinel (compute-node hostnames are not reliably cluster-tagged): /anvil
# exists only on Anvil and /depot/yunglu only on Gilbreth. Any exported value
# can be overridden by pre-setting it before sourcing.

# --- Discord webhook (shared) ---------------------------------------------
export WEBHOOK_URL="https://discord.com/api/webhooks/1355780352530055208/84HI6JSNN3cPHbux6fC2qXanozCSrza7-0nAGJgsC_dC2dWAqdnMR7d4wsmwQ4Ai4Iux"
export DISCORD_USER_ID="746026689397653534"
export DISCORD_AVATAR="https://droplr.com/wp-content/uploads/2020/10/Screenshot-on-2020-10-21-at-10_29_26.png"

if [ -d /anvil ]; then
    export CLUSTER="anvil"
    export DATA_ROOT="${DATA_ROOT:-/anvil/scratch/x-ochaturvedi/transcription}"
    export CONDA_ROOT="${CONDA_ROOT:-/anvil/scratch/x-ochaturvedi/.conda}"
    export RESEARCH_DIR="${RESEARCH_DIR:-/anvil/scratch/x-ochaturvedi/research}"
    # Writable root for model checkpoints/weights. Model wrappers read this
    # (e.g. "$MODEL_DATA_DIR/piano_transcription_inference_data/...pth") so they
    # never hardcode a cluster-specific path; missing checkpoints auto-download.
    export MODEL_DATA_DIR="${MODEL_DATA_DIR:-/anvil/scratch/x-ochaturvedi/model_data}"
    # Pre-staged model dirs (code + weights). cloning.py copies from here instead
    # of git-cloning, so models with git-LFS weights work even when the token
    # can't pull LFS. Stage a working model dir here per cluster to enable it.
    export MODEL_STAGE_DIR="${MODEL_STAGE_DIR:-/anvil/scratch/x-ochaturvedi/models}"

    # GPU jobs (transcription / dataset builds): the gpu partition (the cis*-gpu
    # accounts are associated only with it -- the `ai` partition rejects them).
    # Use a FRESH allocation (cis240580-gpu, FairShare 1.0, unused) rather than
    # cis240587-gpu (FairShare 0.57, heavily used) so jobs rank higher in the
    # heavily-contended gpu queue and actually get scheduled.
    export GPU_ACCOUNT="${GPU_ACCOUNT:-cis240580-gpu}"
    export GPU_PARTITION="${GPU_PARTITION:-gpu}"
    export GPU_QOS="${GPU_QOS:-}"
    # Anvil GPU nodes are SHARED: 512G RAM / 4 GPUs (~128G per GPU). Requesting a
    # Gilbreth-sized 240G for one GPU can't fit alongside other jobs on a node,
    # so the job never backfills and sits forever on (Priority). Right-size the
    # per-job memory to a single-GPU share so it schedules on the shared partition.
    export GPU_MEM="${GPU_MEM:-120G}"
    # Support jobs (upload / notify): the CPU allocation (cis220051) hit its
    # AssocGrpCPUMinutesLimit, so route these to the GPU account/partition,
    # which has surplus SU. (Uploads don't use the GPU, but Anvil has plenty.)
    export SUPPORT_ACCOUNT="${SUPPORT_ACCOUNT:-cis240580-gpu}"
    export SUPPORT_PARTITION="${SUPPORT_PARTITION:-gpu}"
    export SUPPORT_QOS="${SUPPORT_QOS:-}"
    export SUPPORT_GRES="${SUPPORT_GRES:-gpu:1}"

    load_modules() {
        # Anvil exposes conda/parallel/ffmpeg directly (no "external" module).
        module load conda parallel ffmpeg 2>/dev/null
        source "$(conda info --base)/etc/profile.d/conda.sh"
    }
elif [ -d /depot/yunglu ]; then
    export CLUSTER="gilbreth"
    export DATA_ROOT="${DATA_ROOT:-/depot/yunglu/data/transcription}"
    export CONDA_ROOT="${CONDA_ROOT:-/scratch/gilbreth/ochaturv/.conda}"
    export RESEARCH_DIR="${RESEARCH_DIR:-/scratch/gilbreth/ochaturv/research}"
    # Writable root for model checkpoints/weights. Points at the existing
    # /scratch/gilbreth/ochaturv/<model>_data location so current checkpoints
    # are reused (no re-download); model wrappers read $MODEL_DATA_DIR.
    export MODEL_DATA_DIR="${MODEL_DATA_DIR:-/scratch/gilbreth/ochaturv}"
    # Pre-staged model dirs (code + weights); cloning.py copies from here rather
    # than git-cloning, so git-LFS weights work without a working LFS token.
    export MODEL_STAGE_DIR="${MODEL_STAGE_DIR:-/scratch/gilbreth/ochaturv/models}"

    # GPU jobs: yunglu's only runnable partition is a100-80gb (3 GPUs, normal QOS).
    export GPU_ACCOUNT="${GPU_ACCOUNT:-yunglu}"
    export GPU_PARTITION="${GPU_PARTITION:-a100-80gb}"
    export GPU_QOS="${GPU_QOS:-normal}"
    # Gilbreth a100-80gb nodes are effectively dedicated, so a large per-job
    # memory request schedules fine.
    export GPU_MEM="${GPU_MEM:-240G}"
    # Support jobs: no CPU partition exists on Gilbreth, so a GPU must be
    # requested even for CPU work. Use the preemptible standby QOS so these
    # never consume one of the 3 normal-QOS GPUs.
    export SUPPORT_ACCOUNT="${SUPPORT_ACCOUNT:-yunglu}"
    export SUPPORT_PARTITION="${SUPPORT_PARTITION:-a100-80gb}"
    export SUPPORT_QOS="${SUPPORT_QOS:-standby}"
    export SUPPORT_GRES="${SUPPORT_GRES:-gpu:1}"

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
    export RESEARCH_DIR="${RESEARCH_DIR:-$(pwd)}"
    export GPU_ACCOUNT="" GPU_PARTITION="" GPU_QOS=""
    export SUPPORT_ACCOUNT="" SUPPORT_PARTITION="" SUPPORT_QOS="" SUPPORT_GRES=""
    load_modules() { :; }
fi

# Keep ALL package caches, conda envs, and tool caches OFF $HOME. Cluster home
# quotas are tiny (Anvil: 25 GB) while scratch is huge; conda/mamba, pip,
# huggingface, torch, numba and matplotlib all default to writing under $HOME,
# which silently fills the home quota and then breaks env creation with
# "Disk quota exceeded" (e.g. mamba writing ~/.conda/environments.txt). Point
# every cache/registry at scratch (derived from the cluster's CONDA_ROOT).
if [ -n "$CONDA_ROOT" ]; then
    export CONDA_PKGS_DIRS="$CONDA_ROOT/pkgs"
    # NB: do NOT set CONDA_ENVS_DIRS -- it aliases conda's `envs_dirs`, which
    # collides with a pre-existing `envs_path` alias and raises MultipleKeysError,
    # breaking every conda call. The pipeline creates envs with an explicit
    # --prefix under $CONDA_ROOT/envs anyway, so envs already land on scratch.
    _CACHE_ROOT="$(dirname "$CONDA_ROOT")/.cache"
    export PIP_CACHE_DIR="$_CACHE_ROOT/pip"
    export XDG_CACHE_HOME="$_CACHE_ROOT/xdg"
    export HF_HOME="$_CACHE_ROOT/huggingface"
    export TORCH_HOME="$_CACHE_ROOT/torch"
    export NUMBA_CACHE_DIR="$_CACHE_ROOT/numba"
    export MPLCONFIGDIR="$_CACHE_ROOT/matplotlib"
    mkdir -p "$CONDA_PKGS_DIRS" "$PIP_CACHE_DIR" "$XDG_CACHE_HOME" \
        "$HF_HOME" "$TORCH_HOME" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR" 2>/dev/null || true
fi

# notify "<message>"        -> plain Discord message
# notify "<message>" mention -> message that also pings DISCORD_USER_ID
notify() {
    local msg="$1"
    local mention="$2"
    local payload
    if [ "$mention" = "mention" ]; then
        msg="<@${DISCORD_USER_ID}> ${msg}"
        payload="{\"content\": \"${msg}\", \"avatar_url\": \"${DISCORD_AVATAR}\", \"allowed_mentions\": {\"users\": [\"${DISCORD_USER_ID}\"]}}"
    else
        payload="{\"content\": \"${msg}\", \"avatar_url\": \"${DISCORD_AVATAR}\"}"
    fi
    curl -s -X POST -H "Content-Type: application/json" -d "${payload}" "${WEBHOOK_URL}" >/dev/null 2>&1 || true
}

# Call right AFTER `conda activate <env>` so the activated env's own shared
# libraries (libstdc++, etc.) take precedence over older module-provided ones.
# Without this, a cluster module's stale libstdc++ shadows the env's newer one
# and compiled extensions fail to import (e.g. matplotlib: "CXXABI_1.3.15 not
# found"), which silently makes every model produce no output.
conda_lib_priority() {
    [ -z "$CONDA_PREFIX" ] && return
    # PyTorch (pip) bundles its own CUDA libs (cuDNN, cuBLAS, NCCL, ...) under
    # site-packages/nvidia/*/lib. Put those FIRST so a conda-installed cuDNN in
    # $CONDA_PREFIX/lib can't shadow the version PyTorch was built against
    # (otherwise: "cuDNN version incompatibility ... conflicting cuDNN in
    # LD_LIBRARY_PATH"). $CONDA_PREFIX/lib still precedes system/module dirs so
    # the env's newer libstdc++ wins (fixes the matplotlib CXXABI import error).
    local nvlibs
    nvlibs=$(ls -d "$CONDA_PREFIX"/lib/python3*/site-packages/nvidia/*/lib 2>/dev/null | paste -sd: -)
    export LD_LIBRARY_PATH="${nvlibs:+$nvlibs:}$CONDA_PREFIX/lib:${LD_LIBRARY_PATH}"
}

export -f load_modules notify conda_lib_priority 2>/dev/null || true

echo "[cluster_env] CLUSTER=$CLUSTER DATA_ROOT=$DATA_ROOT GPU=$GPU_ACCOUNT/$GPU_PARTITION SUPPORT=$SUPPORT_ACCOUNT/$SUPPORT_PARTITION"
