# Music Complexity Analysis

## Overview
This project implements mathematically correct music complexity metrics including:
- **Entropy Analysis**: Pitch class, melodic interval, and IOI entropy
- **Polyphony Analysis**: Maximum, average, and density metrics
- **ATC Analysis**: Automatic Transcription Complexity (harmony analysis)

## Key Files

### Core Implementation
- `complexity/entropy.py` - Mathematically correct entropy calculations
- `complexity/polyphony.py` - Time-weighted polyphony analysis
- `complexity/shared_preprocessor.py` - Common preprocessing functions
- `complexity/atc_wrapper.py` - ATC (harmony) analysis wrapper

### Analysis Scripts
- `complexity_pipeline/run_complexity_analysis.sh` - Main job script for cluster execution
- `complexity_pipeline/complexity_analysis.py` - Core analysis pipeline
- `batch_polyphony_test.py` - Batch testing for polyphony validation

### Usage

#### Run Full Analysis (All Datasets)
```bash
sbatch complexity_pipeline/run_complexity_analysis.sh
```

#### Run Analysis for Specific Dataset
```bash
sbatch complexity_pipeline/run_complexity_analysis.sh slakh2100
```

#### Test Individual File
```bash
python3 complexity/entropy.py /path/to/file.mid
python3 complexity/polyphony.py /path/to/file.mid
```

## Results
- Output files are saved to `complexity_results/`
- Logs are saved to `logs/`
- Results include all complexity metrics in CSV format

## Validation
All implementations have been validated against baseline results and show perfect matches for:
- Pitch class entropy
- Melodic interval entropy  
- IOI entropy
- Max polyphony
- Tonal certainty

## Mathematical Correctness
- Uses time-weighted calculations for polyphony
- Preserves original entropy mechanisms exactly
- Event-based sampling for precision
- Advanced percussion detection 