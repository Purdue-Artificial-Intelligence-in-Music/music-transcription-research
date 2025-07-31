# Complexity Analysis Pipeline

This folder contains scripts for analyzing musical complexity metrics (entropy and polyphony) from MIDI datasets.

## Scripts Overview

### 1. `complexity_analysis.py`
**Core analysis script** - Processes MIDI files to extract complexity metrics
- **Usage**: `python complexity_analysis.py --dataset Slakh2100 --num-workers 30`
- **Output**: CSV files with entropy and polyphony metrics
- **Environment**: Any Python environment

### 2. `complexity_analysis.sh`
**Cluster execution script** - Runs complexity analysis on HPC cluster
- **Usage**: `sbatch complexity_analysis.sh`
- **Features**: SLURM job submission, conda environment setup, Discord notifications
- **Resources**: 30 CPUs, 12 hours, yunglu-k cluster

### 3. `generate_midi_config.py`
**Configuration generator** - Creates `midi_datasets.json` with user-specific paths
- **Usage**: `python generate_midi_config.py`
- **Purpose**: Sets up dataset paths for your scratch directory
- **Output**: `midi_datasets.json` (gitignored)

### 4. `integrate_complexity.py`
**Data integration script** - Merges complexity results with AMT performance data
- **Usage**: `python integrate_complexity.py`
- **Purpose**: Enables correlation analysis between complexity and transcription accuracy
- **Output**: Combined CSV for research analysis

### 5. `run_complexity_local.sh`
**Local testing script** - Quick validation and debugging
- **Usage**: `./run_complexity_local.sh`
- **Purpose**: Test pipeline locally before cluster submission
- **Features**: Limited files, 4 workers, immediate feedback

## Quick Start

1. **Setup**: `python generate_midi_config.py`
2. **Test**: `./run_complexity_local.sh`
3. **Cluster**: `sbatch complexity_analysis.sh`
4. **Integrate**: `python integrate_complexity.py`

## Dependencies

- `music21`, `pandas`, `numpy`, `matplotlib`, `seaborn`
- `pretty_midi`, `argparse`, `pathlib`, `logging`
- `concurrent.futures.ProcessPoolExecutor`
