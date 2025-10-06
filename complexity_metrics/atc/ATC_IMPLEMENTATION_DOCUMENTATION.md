# ATC (Audio-to-Chord) Implementation Documentation

## Overview

This implementation is based on the paper **"Improving Music Classification Using Harmonic Complexity"** by Maršík et al. (2014). The ATC analysis calculates harmonic complexity metrics that can predict AMT (Automatic Music Transcription) accuracy.

## Paper Reference

**Title**: Improving Music Classification Using Harmonic Complexity  
**Authors**: Ladislav Maršík, Jaroslav Pokorný, Martin Ilčík  
**Conference**: ITAT 2014  
**DOI**: https://www.researchgate.net/publication/321906241

## Key Concepts from the Paper

### 1. Harmonic Complexity Definition

The paper defines **Average Transition Complexity (ATC)** as:

```
ATC(M) = (∑(i=0 to l-1) t_i) / (l-1)
```

Where:
- `t_i` = transition complexity between successive chords
- `l` = length of chord sequence
- ATC represents the average complexity of chord transitions in a musical piece

### 2. Chord Detection Process

Based on the paper, the chord detection process involves:

1. **Feature Extraction**: Uses NNLS Chroma and Chordino plugins
2. **4-Tone Selection**: Selects 4 tones with highest presence per segment
3. **Audible Threshold**: Uses 0.07 threshold for audible tones (recommended in paper)
4. **Chord Matching**: Matches against chord dictionary for chord detection

### 3. Implementation Architecture

Our implementation provides two approaches:

#### **PYCHORD Method** (`run_harmony_analyser`)
- Uses `midi_to_chordino_labels_harmony_format()` for chord detection
- Direct note analysis approach
- Applies key signature normalization for extreme keys
- Generates chord labels in harmony-analyser format

#### **CHORDINO Method** (`run_chordino_atc_analysis`)
- Uses `midi_to_chordino_labels_chordino_simulation()` for chord detection
- Chroma vector analysis with 4-tone selection
- Implements the exact algorithm described in the paper
- Uses 0.07 audible threshold and 4-tone maximum

## Metrics Explanation

### Primary Metric: RCCD (Relative Chord Complexity Distance)

**RCCD** is the main ATC score that represents harmonic complexity:
- **Range**: Not constrained to 0-1 (can exceed 1 for complex music)
- **Meaning**: Higher values indicate more complex harmonic transitions
- **Usage**: Primary metric for AMT accuracy prediction

### Secondary Metrics: ACCD and ACC

**ACCD (Average Chord Complexity Distance)**:
- Often constant at 7.0 (maximum complexity in the system)
- Represents system parameter rather than variable metric

**ACC (Average Chord Complexity)**:
- Often constant at -1.0 (normalization factor)
- Used internally by harmony analyzer

## File Structure

```
complexity_metrics/atc/
├── single_midi_atc.py              # Main ATC analysis functions
├── chordino_simulation.py          # CHORDINO simulation implementation
├── midi_to_chroma.py               # Chroma feature extraction
├── harmony-analyser/               # Java harmony analyzer
│   └── target/ha-script-1.2-beta.jar
└── ATC_IMPLEMENTATION_DOCUMENTATION.md
```

## Usage

### Basic ATC Analysis

```python
from single_midi_atc import run_harmony_analyser, run_chordino_atc_analysis

# PYCHORD method
pychord_result = run_harmony_analyser('path/to/file.mid')
print(f"PYCHORD ATC Score: {pychord_result['atc_score']}")

# CHORDINO method  
chordino_result = run_chordino_atc_analysis('path/to/file.mid')
print(f"CHORDINO ATC Score: {chordino_result['atc_score']}")
```

### Expected Output

```python
{
    'atc_score': 1.9325154,    # Primary metric (RCCD)
    'accd_score': 7.0,         # System parameter
    'acc_score': -1.0,         # Normalization factor
    'rccd_score': 1.9325154    # Same as atc_score
}
```

## Algorithm Validation

The paper shows that ATC values:
- **Improve music classification by up to 4%**
- **Show up to 10% improvement for Jazz music**
- **Are particularly effective for complex harmonic movements**

## Key Implementation Details

### 1. 4-Tone Selection
```python
# Select top 4 tones with highest presence (as per paper)
tone_indices = np.argsort(chroma_vector)[::-1]  # Sort by intensity, descending
selected_tones = tone_indices[:max_tones]
```

### 2. Audible Threshold
```python
# Apply audible threshold (0.07 as recommended in the paper)
audible_tones = chroma_vector >= audible_threshold
```

### 3. Key Signature Normalization
- Handles extreme key signatures (>8 sharps/flats)
- Transposes notes to bring keys within normal range
- Prevents parsing errors in harmony analyzer

## Performance Characteristics

### Expected ATC Score Ranges
- **Simple music** (POP909): 0.15 - 0.75
- **Complex music** (Maestro): 1.5 - 2.0+
- **Monophonic music**: 0.0 (early termination)

### Processing Times
- **PYCHORD method**: ~20-40 seconds per file
- **CHORDINO method**: ~20-40 seconds per file
- **Failed files**: ~1-2 seconds (early termination)

## Troubleshooting

### Common Issues

1. **ACCD/ACC always 7.0/-1.0**: This is expected behavior (system parameters)
2. **RCCD > 1.0**: Normal for complex music (not constrained to 0-1 range)
3. **ATC = 0.0**: Indicates monophonic music or chord detection failure
4. **Key signature errors**: Handled by normalization in `normalize_extreme_key_signatures()`

### Debugging

Use the debug script to test ATC analysis:
```bash
python3 complexity_scripts/debug/debug_atc_analysis.py --dataset pop909 --max-files 5
```

## Future Improvements

1. **Threshold Optimization**: Test different audible thresholds for better chord detection
2. **Chord Dictionary Expansion**: Add more chord types for better matching
3. **Temporal Smoothing**: Improve HMM-based smoothing for chord transitions
4. **Performance Optimization**: Further optimize chord detection algorithms

## References

1. Maršík, L., Pokorný, J., & Ilčík, M. (2014). Improving Music Classification Using Harmonic Complexity. ITAT 2014.
2. Mauch, M., & Levy, M. (2011). Structural Change on Multiple Time Scales as a Correlate of Musical Complexity. ISMIR 2011.
3. Krumhansl, C. L. (1990). Cognitive Foundations of Musical Pitch. Oxford University Press.

