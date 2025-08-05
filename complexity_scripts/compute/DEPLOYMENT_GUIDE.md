# Large-Scale Complexity Analysis Deployment Guide

## Overview

This guide provides instructions for deploying complexity analysis across all datasets using optimized job arrays with maximum CPU utilization.

## Architecture

### Job Array Structure
- **8 parallel jobs** (one per dataset)
- **32 CPUs per job** (maximum utilization)
- **4-hour time limit** per dataset (standby partition)
- **Automatic fallback** to original dataset paths

### Datasets
1. `slakh2100` - 1,710 files
2. `maestro` - 1,276 files  
3. `pop909` - 909 files
4. `nesmdb` - 5,278 files
5. `msmd` - 467 files
6. `aam` - 3,000 files
7. `bimmuda` - 375 files
8. `xmidi` - 108,023 files

## Quick Start

### 1. Deploy All Datasets
```bash
cd /home/$USER/AIM/music-transcription-research/complexity_scripts/compute
./submit_all_datasets.sh
```

### 2. Deploy Single Dataset
```bash
sbatch run_complexity_job_array.sh
# Then manually specify dataset in the script
```

### 3. Monitor Progress
```bash
# Check job status
squeue -j <JOB_ID>

# Monitor logs
tail -f logs/complexity_array_<JOB_ID>_*.out
tail -f logs/complexity_array_<JOB_ID>_*.err

# Performance monitoring
python3 monitor_performance.py --duration 3600
```

## Resource Optimization

### CPU Utilization
- **32 CPUs per job** (vs. 8 for model training)
- **ProcessPoolExecutor** for parallel file processing
- **Optimized for I/O intensive** complexity analysis

### Memory Management
- **Streaming processing** to avoid memory overflow
- **Batch processing** with configurable limits
- **Automatic cleanup** of temporary files

### Dataset Access
- **Primary**: `/depot/yunglu/data/transcription/`
- **Fallback**: `/scratch/gilbreth/shang33/AIM/datasets/`
- **Automatic path resolution** in dataset manager

## Performance Monitoring

### Real-time Monitoring
```bash
# Start performance monitoring
python3 monitor_performance.py --duration 7200 --log-file performance.log

# Monitor specific metrics
watch -n 5 'tail -n 1 performance.log'
```

### Expected Performance
- **CPU Usage**: 80-95% (32 cores)
- **Memory**: 2-4GB per job
- **Processing Speed**: 0.5-2 files/second
- **Total Runtime**: 4-12 hours per dataset

## Job Management

### Submit Jobs
```bash
# Submit all datasets
./submit_all_datasets.sh

# Submit single dataset (modify script)
sbatch run_complexity_job_array.sh
```

### Monitor Jobs
```bash
# List all jobs
squeue -u $USER

# Check specific job
squeue -j <JOB_ID>

# View job details
scontrol show job <JOB_ID>
```

### Cancel Jobs
```bash
# Cancel all array jobs
scancel <JOB_ID>

# Cancel specific array task
scancel <JOB_ID>_0  # Cancel slakh2100
scancel <JOB_ID>_1  # Cancel maestro
```

## Output Structure

### Results Directory
```
complexity_results/
├── slakh2100_complexity.csv
├── maestro_complexity.csv
├── pop909_complexity.csv
├── nesmdb_complexity.csv
├── msmd_complexity.csv
├── aam_complexity.csv
├── bimmuda_complexity.csv
├── xmidi_complexity.csv
└── all_complexity_results.csv
```

### Log Files
```
logs/
├── complexity_array_<JOB_ID>_0.out  # slakh2100
├── complexity_array_<JOB_ID>_0.err
├── complexity_array_<JOB_ID>_1.out  # maestro
├── complexity_array_<JOB_ID>_1.err
└── ...
```

## Discord Notifications

### Job Start
```
🎵 **Complexity Analysis Started**
Job ID: 12345678
Array Task: 0
Dataset: slakh2100
Node: gilbreth001
```

### Job Completion
```
✅ **Complexity Analysis Completed**
Job ID: 12345678
Array Task: 0
Dataset: slakh2100
Runtime: 06:23:45
```

### Job Failure
```
❌ **Complexity Analysis Failed**
Job ID: 12345678
Array Task: 0
Dataset: slakh2100
```

## Troubleshooting

### Common Issues

1. **Dataset Not Found**
   - Check fallback paths in dataset manager
   - Verify dataset names in configuration

2. **Memory Issues**
   - Reduce `--num-workers` if needed
   - Monitor with `monitor_performance.py`

3. **Job Timeout**
   - Increase `--time` in SLURM script
   - Use `--max-files` to limit processing

4. **Permission Errors**
   - Check file permissions on datasets
   - Verify output directory access

### Debug Commands
```bash
# Test dataset access
python3 -c "from dataset_manager import get_dataset_manager; dm = get_dataset_manager(); print(dm.find_files('slakh2100', limit=1))"

# Test single file processing
python3 complexity_analysis.py --dataset slakh2100 --max-files 1

# Check system resources
htop
nvidia-smi
```

## Expected Timeline

### Small Datasets (1-2 hours)
- `msmd` (467 files)
- `bimmuda` (375 files)
- `pop909` (909 files)

### Medium Datasets (4-6 hours)
- `aam` (3,000 files)
- `maestro` (1,276 files)
- `slakh2100` (1,710 files)
- `nesmdb` (5,278 files)

### Large Datasets (8-12 hours)
- `xmidi` (108,023 files)

### Total Expected Runtime
- **All datasets**: 4-8 hours
- **Parallel execution**: 8 jobs simultaneously
- **Optimal completion**: 4-6 hours

## Post-Processing

### Combine Results
```bash
# All results are automatically combined
ls -la complexity_results/all_complexity_results.csv
```

### Analysis Scripts
```bash
# Move to analysis folder for correlation studies
cd ../analysis/
python3 correlate_complexity_accuracy.py
```

## Security Notes

- **Dataset paths** are automatically resolved
- **Fallback mechanisms** ensure data access
- **Log files** contain no sensitive information
- **Discord notifications** use webhook URLs 