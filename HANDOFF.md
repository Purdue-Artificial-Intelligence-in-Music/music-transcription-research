# AMT Pipeline — Handoff / Remaining Tasks

Status as of the latest run. The pipeline transcribes each dataset's audio with
each model, scores it (mir_eval F-measure), and uploads results to Google Drive.
Work is split across two clusters: **Gilbreth** (`yunglu`, 3× A100-80gb) and
**Anvil** (`cis240587-gpu`, many A100s). See `scripts/cluster_env.sh` for all
per-cluster settings.

## ✅ Done and verified (on Google Drive, full counts)

| Model | Datasets completed |
|---|---|
| Bytedance Piano transcription | MSMD, BiMMuDa, POP909 |
| Transkun | MSMD, BiMMuDa, POP909 |
| Madmom | Maestro, MSMD, BiMMuDa, POP909 |
| ReconVAT | Maestro, Slakh 2100 Redux, MSMD, BiMMuDa, POP909, NESMDB, AAM |

`models.json` "Completed Datasets" reflect this, so `run.py` skips them.
Verify Drive anytime with: `python scripts/list_drive.py --check`

Piano models (Bytedance/Transkun/Madmom) skip the Multiple-instrument datasets
(Slakh, NESMDB, AAM) and their own training set (Maestro for Bytedance/Transkun)
by design — that is not missing work.

## ⛔ Remaining models (all currently in models.json `disabled`, except MR-MT3/Jointist which are enabled but fail to clone)

### 1. MR-MT3 and Jointist — blocked on the GitHub token (quick fix, yours)
- Both clone-fail with: `batch response: Resource not accessible by personal access token`.
- The `keys.json` token pulls LFS fine for ReconVAT but **not** for `mr-mt3` and
  `Jointist`. The fine-grained PAT is missing those two repos.
- **Fix:** regenerate the PAT with `mr-mt3` + `Jointist` added (Contents: read),
  or use a classic token with full `repo` scope, and update `keys.json`
  (gitignored). Then they run as-is — both have a correct `-i/-o` main.py and
  buildable env.yml. They are Multiple-instrument, so run on all 7 datasets.

### 2. MT3 — dependency hell (deferred)
- `inference.py` needs `ddsp.spectral_ops`, `tensorflow`, and `t5.data` (via
  `contrib/`), so those can't be dropped. The env.yml pip stack (ddsp 3.3.4 +
  t5 0.9.3, py3.8) hits `Cannot install flax ... ResolutionImpossible` on the
  cluster.
- Already fixed: python 3.7→3.8 pin. Still unresolved: the flax/jax/tensorflow
  version conflict.
- **Approach:** iterative py3.8 env builds pinning a mutually-compatible
  jax/jaxlib/flax/tensorflow set, or containerize with a frozen lock-file
  (recommended for this old ecosystem). Staged repo + env live at
  `$MODEL_STAGE_DIR/MT3` on each cluster.

### 3. Omnizart — dependency hell (deferred)
- `omnizart` pip install fails on its own deps, so `omnizart download-checkpoints`
  never runs → staged repo only has the `chord` checkpoint, missing `music_piano`
  (which the Piano transcription needs; error was missing `configurations.yaml`).
- **Approach:** resolve omnizart's deps (py3.8) enough to run
  `omnizart download-checkpoints` into the staged repo, or containerize. See
  `scripts/stage_models.sh` (it attempts this and reports the failure).

### 4. CREPE Pitch Tracker — needs a fork (yours)
- Source repo `tgondil/crepe-amt` is not yours; the PAT can't access it.
- **Fix:** clone it (you have personal access), push to a repo under your own
  account, update the URL + token in `keys.json`, then re-enable. Its main.py
  interface still needs checking against the `-i <file> -o <file>.mid` contract.

### 5. Basic Pitch — needs a fork + main.py wrapper (yours)
- Source repo `KayshavBhardwaj/basic-pitch-test-1` — cloneable, but its `main.py`
  is Spotify's stock CLI: `-o` is an **output directory** and it writes
  `<name>_basic_pitch.mid`, which does NOT match the pipeline's
  `-i <file> -o <file>.mid` contract → produced 0 output.
- **Fix:** fork to your account, wrap main.py to accept a single input audio file
  and write to the exact output path given by `-o`, update `keys.json`, re-enable.

### 6. XMIDI dataset — parked
- 108,023 files; disabled in `datasets.json` under `"disabled"`. Re-enable by
  moving the row back to `"values"`. Given its size, run it on Anvil.

## How the pieces fit (for whoever continues)

- **Config:** `scripts/cluster_env.sh` is the single source of truth — detects
  the cluster and exports DATA_ROOT, CONDA_ROOT, MODEL_DATA_DIR, per-cluster
  SLURM account/partition/QOS, `load_modules`, `conda_lib_priority`, and
  `notify`. Every job script sources it.
- **Deploy/run:** `python server.py --cluster {gilbreth|anvil|both}` rsyncs the
  code and launches `main.sh`. `python server.py --distribute` splits datasets
  across both clusters by capacity (writes per-cluster `datasets.json` subsets).
  `--no-submit` deploys without launching.
- **Staging:** `scripts/stage_models.sh` pre-clones every model (code + LFS
  weights) into `$MODEL_STAGE_DIR` so `cloning.py` copies complete models
  instead of cloning each run. Run once per cluster after a token change.
- **models.json / datasets.json:** the pipeline reads only the `"values"` key;
  a `"disabled"` key preserves excluded rows. `run.py` skips a dataset already
  in a model's "Completed Datasets".
- **keys.json** (gitignored): per-model GitHub URL/user/token + optional
  pre-staged path. Must have a token with LFS access to every enabled repo.
- **Drive check:** `python scripts/list_drive.py [--check]`.

## Non-obvious fixes already in place (don't regress these)
- `conda_lib_priority` prepends the env's `nvidia/*/lib` then `$CONDA_PREFIX/lib`
  so PyTorch's bundled cuDNN wins and matplotlib's libstdc++ import works.
- Model checkpoints read `$MODEL_DATA_DIR` (not hardcoded Gilbreth paths).
- `upload.sh` only deletes output on a *successful* upload and only then posts
  "Finished uploading"; `upload.py` returns non-zero on failure. Failed uploads
  keep the output and can be retried without re-transcription.
- `run.sh` pads sub-2s audio with trailing silence (fixes CNN crashes on very
  short clips; silence doesn't affect scoring).
- Dataset synth scripts verify non-empty WAV output; `slakh.sh` re-saves
  unrenderable MIDIs through `mido` (fixes "Invalid length for KeySignature").
- Gilbreth `main.sh`/`run.sh` require an explicit GPU + `--mem`; support jobs
  (upload/notify) run on standby (Gilbreth) or the GPU account (Anvil).
