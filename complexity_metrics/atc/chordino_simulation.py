"""
Chordino Simulation - Python implementation attempting to mimic the original Chordino algorithm
"""

import numpy as np
from collections import defaultdict
import tempfile
import os
import shutil
from mido import MidiFile

# Note names for conversion
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Chord dictionary (simplified version of Chordino's chord profiles)
CHORD_DICTIONARY = {
    # Major chords
    'C': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    'C#': [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
    'D': [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    'D#': [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
    'E': [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    'F': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
    'F#': [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],
    'G': [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    'G#': [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
    'A': [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
    'A#': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    'B': [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1],
    
    # Minor chords
    'Cm': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    'C#m': [0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    'Dm': [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0],
    'D#m': [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
    'Em': [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
    'Fm': [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
    'F#m': [0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    'Gm': [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0],
    'G#m': [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
    'Am': [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
    'A#m': [0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    'Bm': [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    
    # Dominant 7th chords
    'C7': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    'C#7': [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1],
    'D7': [1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    'D#7': [0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
    'E7': [0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    'F7': [1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
    'F#7': [0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0],
    'G7': [0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1],
    'G#7': [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0],
    'A7': [0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0],
    'A#7': [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0],
    'B7': [0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1],
    
    # Minor 7th chords
    'Cm7': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
    'C#m7': [0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    'Dm7': [1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0],
    'D#m7': [0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
    'Em7': [0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1],
    'Fm7': [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0],
    'F#m7': [0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0],
    'Gm7': [0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0],
    'G#m7': [0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1],
    'Am7': [1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0],
    'A#m7': [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0],
    'Bm7': [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1],
    
    # Diminished chords
    'Cdim': [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
    'C#dim': [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    'Ddim': [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0],
    'D#dim': [0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
    'Edim': [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    'Fdim': [0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1],
    'F#dim': [1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    'Gdim': [0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0],
    'G#dim': [0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    'Adim': [1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
    'A#dim': [0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
    'Bdim': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1],
}

def chroma_to_chord(chroma_vector, audible_threshold=0.07, max_tones=4):
    """
    Convert a chroma vector to the most likely chord using 4-tone selection.
    
    Based on Maršík et al. (2014) paper:
    - Selects 4 tones with highest presence per segment
    - Uses 0.07 threshold for audible tones (as recommended in the paper)
    - Matches against chord dictionary for chord detection
    """
    if np.sum(chroma_vector) == 0:
        return 'N'
    
    # Apply audible threshold (0.07 as recommended in the paper)
    audible_tones = chroma_vector >= audible_threshold
    
    if np.sum(audible_tones) == 0:
        return 'N'
    
    # Select top 4 tones with highest presence (as per paper)
    tone_indices = np.argsort(chroma_vector)[::-1]  # Sort by intensity, descending
    selected_tones = tone_indices[:max_tones]
    
    # Create binary vector for selected tones
    selected_chroma = np.zeros(12)
    for idx in selected_tones:
        if chroma_vector[idx] >= audible_threshold:
            selected_chroma[idx] = 1.0
    
    # Normalize selected chroma vector
    if np.sum(selected_chroma) > 0:
        selected_chroma_norm = selected_chroma / np.sum(selected_chroma)
    else:
        return 'N'
    
    best_chord = 'N'
    best_score = 0
    
    # Match against chord dictionary
    for chord_name, chord_profile in CHORD_DICTIONARY.items():
        # Calculate correlation between selected chroma and chord profile
        correlation = np.corrcoef(selected_chroma_norm, chord_profile)[0, 1]
        
        if not np.isnan(correlation) and correlation > best_score:
            best_score = correlation
            best_chord = chord_name
    
    # Only return chord if correlation is above threshold
    if best_score > 0.3:
        return best_chord
    else:
        return 'N'

def midi_to_chordino_labels_chordino_simulation(midi_path, output_path):
    """
    Generate chordino labels using a simulation of the original Chordino algorithm.
    This includes temporal smoothing and chord dictionary matching.
    """
    # Quick polyphony check for early termination
    mid = MidiFile(midi_path)
    max_polyphony = 0
    current_polyphony = 0
    
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                current_polyphony += 1
                max_polyphony = max(max_polyphony, current_polyphony)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                current_polyphony = max(0, current_polyphony - 1)
    
    # If max polyphony < 2, return empty file (no chords)
    if max_polyphony < 2:
        with open(output_path, 'w') as f:
            f.write("0.000: N\n")
        return
    
    # Re-load MIDI file for processing
    mid = MidiFile(midi_path)
    time = 0
    chords = []
    notes_on = set()
    ticks_per_beat = mid.ticks_per_beat
    tempo = 500000  # default MIDI tempo
    
    # Find tempo if present
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
    
    def ticks_to_seconds(ticks):
        return ticks * tempo / 1e6 / ticks_per_beat
    
    # Process MIDI events
    current_ticks = 0
    notes_on = {}  # {note: velocity}
    
    for track in mid.tracks:
        for msg in track:
            current_ticks += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                notes_on[msg.note] = msg.velocity
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in notes_on:
                    del notes_on[msg.note]
            
            # Convert current time to seconds
            current_time_seconds = ticks_to_seconds(current_ticks)
            
            # Create chroma vector from current notes
            chroma_vector = np.zeros(12)
            for note, velocity in notes_on.items():
                pitch_class = note % 12
                intensity = velocity / 127.0
                chroma_vector[pitch_class] += intensity
            
            # Detect chord using chord dictionary matching
            chord_label = chroma_to_chord(chroma_vector)
            chords.append((current_time_seconds, chord_label))
    
    # Apply temporal smoothing (simulate Chordino's HMM smoothing)
    smoothed_chords = apply_temporal_smoothing(chords)
    
    # Write to output in harmony-analyser format: timestamp: chord_label
    with open(output_path, "w") as f:
        for timestamp, chord in smoothed_chords:
            f.write(f"{timestamp:.3f}: {chord}\n")

def apply_temporal_smoothing(chords, window_size=0.1):
    """
    Apply temporal smoothing to chord labels, simulating Chordino's HMM approach.
    """
    if not chords:
        return []
    
    smoothed = []
    current_chord = chords[0][1]
    current_start = chords[0][0]
    
    for timestamp, chord in chords:
        # If chord changes and enough time has passed, add the previous chord
        if chord != current_chord and (timestamp - current_start) >= window_size:
            smoothed.append((current_start, current_chord))
            current_chord = chord
            current_start = timestamp
        elif chord != current_chord:
            # Chord changed but not enough time passed - keep previous chord
            continue
    
    # Add the last chord
    if chords:
        smoothed.append((current_start, current_chord))
    
    return smoothed

def test_chordino_simulation():
    """Test the chordino simulation with a sample file."""
    midi_file = '/depot/yunglu/data/transcription/nesmdb/013_AlterEgo_09_10LevelClearUnused.mid'
    track_id = '013_AlterEgo_09_10LevelClearUnused'
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_chordino = os.path.join(temp_dir, f'{track_id}-chordino-labels.txt')
        
        midi_to_chordino_labels_chordino_simulation(midi_file, temp_chordino)
        
        print('=== CHORDINO SIMULATION CHORD LABELS (first 50 lines) ===')
        with open(temp_chordino, 'r') as f:
            for i, line in enumerate(f):
                if i < 50:
                    print(line.strip())

if __name__ == "__main__":
    test_chordino_simulation() 