# Debug Tools

This folder contains debugging and comparison scripts for validating complexity metrics.

## Files

### `entropy_debug.py`
**Purpose**: Debug and compare entropy measures between different implementations

**Usage**:
```bash
# Debug single file
python3 entropy_debug.py --file /path/to/file.mid

# Debug batch of files
python3 entropy_debug.py --dataset slakh2100 --limit 10
```

**Output**: 
- Console output with detailed entropy measures
- CSV file with batch results (`entropy_debug_<dataset>.csv`)

### `polyphony_comparison.py`
**Purpose**: Compare polyphony calculations across different time resolutions

**Methods compared**:
1. **Event-based**: Original implementation (most accurate)
2. **Fine resolution**: Uniform 0.01s sampling
3. **Adaptive resolution**: Based on shortest note duration

**Usage**:
```bash
# Compare single file
python3 polyphony_comparison.py --file /path/to/file.mid

# Compare batch of files
python3 polyphony_comparison.py --dataset slakh2100 --limit 10
```

**Output**:
- Console output comparing all three methods
- CSV file with comparison results (`polyphony_comparison_<dataset>.csv`)

### `batch_polyphony_test.py`
**Purpose**: Batch testing for polyphony validation

**Usage**:
```bash
python3 batch_polyphony_test.py
```

## Validation Results

These scripts help validate that:
- Entropy calculations match baseline results
- Polyphony calculations are mathematically correct
- Different time resolution methods produce consistent results
- All implementations are working correctly

## Output Files

- `entropy_debug_*.csv`: Entropy debugging results
- `polyphony_comparison_*.csv`: Polyphony comparison results
- Console output with detailed analysis 