# Complexity Analysis Pipeline

This folder contains scripts for analyzing musical complexity metrics (entropy, polyphony, and ATC harmony analysis) from MIDI datasets.

## Scripts Overview

### 1. `complexity_analysis.py`
**Core analysis script** - Processes MIDI files to extract all complexity metrics
- **Usage**: `python complexity_analysis.py --dataset Slakh2100 --num-workers 30`
- **Output**: CSV files with entropy, polyphony, and ATC (harmony) metrics
- **Environment**: Any Python environment
- **New**: Includes ATC harmony analysis from teammate's implementation

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

## Complexity Metrics Included

### 1. **Entropy-based Metrics** (Information Theory)
- Tonal Certainty, Pitch Class Entropy, Melodic Interval Entropy, IOI Entropy
- Captures information-theoretic complexity and predictability

### 2. **Polyphony-based Metrics** (Voice Complexity)
- Global max/avg polyphony, segmentation analysis, time-based density calculations
- Captures harmonic complexity through simultaneous voice counting

### 3. **ATC Metrics** (Harmony Analysis) - **NEW**
- Automatic Transcription Complexity scores from harmony analysis
- Chord progression complexity, tonal complexity measures
- Integrated from teammate's [ATC implementation](https://github.com/praneethkukunuru/atc-test)

## ATC Integration Details

The ATC (Automatic Transcription Complexity) metric has been integrated as a Git submodule:

```bash
# ATC is located at:
complexity/atc/           # Submodule with teammate's implementation
complexity/atc_wrapper.py # Integration wrapper for our pipeline
```

**ATC Usage Examples:**
```python
# Standalone ATC analysis
from complexity.atc_wrapper import calculate_atc_metrics
atc_results = calculate_atc_metrics('path/to/midi_file.mid')

# Integrated with all metrics
from complexity.atc_wrapper import integrate_with_existing_metrics
all_metrics = integrate_with_existing_metrics('path/to/midi_file.mid')
```

## Dependencies

- `music21`, `pandas`, `numpy`, `matplotlib`, `seaborn`
- `pretty_midi`, `argparse`, `pathlib`, `logging`
- `concurrent.futures.ProcessPoolExecutor`
- **ATC submodule**: Harmony analysis tools (automatic via Git submodule)
