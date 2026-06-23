#!/bin/bash
# stage_models.sh — pre-stage every model repo (code + git-LFS weights) into the
# cluster's $MODEL_STAGE_DIR so the pipeline's cloning.py copies a complete model
# instead of cloning it every run. Also downloads Omnizart's model checkpoints.
#
# Run once per cluster (login node is fine; it's I/O-bound):
#     bash scripts/stage_models.sh
#
# Reads model name / URL / user / token from keys.json.

set -uo pipefail

RESEARCH_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
source "$RESEARCH_DIR/scripts/cluster_env.sh"
load_modules
git lfs install >/dev/null 2>&1 || true

mkdir -p "$MODEL_STAGE_DIR"
echo "[stage] Staging models into $MODEL_STAGE_DIR on $CLUSTER"

# Clone + LFS-pull each model that has a GitHub URL in keys.json.
while IFS=$'\t' read -r name url user token; do
    [ -z "${url:-}" ] && continue
    dest="$MODEL_STAGE_DIR/$name"
    link="${url#https://}"
    echo "[stage] === $name ==="
    rm -rf "$dest"
    if git clone "https://${user}:${token}@${link}" "$dest" >/dev/null 2>&1; then
        ( cd "$dest" && git lfs pull >/dev/null 2>&1 )
        # Strip the token from the staged remote so copied dirs carry no creds.
        ( cd "$dest" && git remote set-url origin "$url" >/dev/null 2>&1 )
        echo "[stage]   ok  ($(du -sh "$dest" 2>/dev/null | cut -f1))"
    else
        echo "[stage]   CLONE FAILED for $name"
    fi
done < <(jq -r '.values[1:][] | select(.[1] != "") | [.[0], .[1], .[2], .[3]] | @tsv' "$RESEARCH_DIR/keys.json")

# Omnizart needs its pretrained checkpoints fetched into the repo. Build a temp
# env OUTSIDE $CONDA_ROOT (so the pipeline's conda cleanup can't wipe it), install
# omnizart editable from the staged repo so download-checkpoints lands in it.
OMNI="$MODEL_STAGE_DIR/Omnizart"
if [ -d "$OMNI" ]; then
    echo "[stage] === Omnizart download-checkpoints ==="
    STAGE_ENV="$MODEL_STAGE_DIR/.stage_omnizart_env"
    rm -rf "$STAGE_ENV"
    if mamba create -y -q --prefix "$STAGE_ENV" python=3.8 pip >/dev/null 2>&1; then
        conda activate "$STAGE_ENV"
        if pip install -q -e "$OMNI" >/dev/null 2>&1; then
            ( cd "$OMNI" && omnizart download-checkpoints >/dev/null 2>&1 \
                && echo "[stage]   checkpoints downloaded" \
                || echo "[stage]   download-checkpoints FAILED" )
        else
            echo "[stage]   omnizart pip install FAILED (resolve deps, then re-run)"
        fi
        conda deactivate
    fi
    rm -rf "$STAGE_ENV"
fi

echo "[stage] DONE on $CLUSTER"
echo "[stage] Staged models:"
ls -1 "$MODEL_STAGE_DIR" 2>/dev/null | grep -v '^\.' | sed 's/^/  /'
