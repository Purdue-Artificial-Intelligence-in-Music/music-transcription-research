import os
import sys
import subprocess
import tempfile
import shutil
import mido
from mido import MidiFile
import numpy as np
from pychord import Chord, find_chords_from_notes
from functools import lru_cache
import time

# Note names for conversion
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def normalize_extreme_key_signatures(midi_path):
    """
    Handle extreme key signatures (8+ sharps) by transposing notes.
    If key has more than 8 sharps, transpose all pitched notes down by the excess.
    """
    try:
        # Create a temporary file for the normalized version
        import tempfile
        import shutil
        temp_fd, temp_path = tempfile.mkstemp(suffix='.mid')
        os.close(temp_fd)
        
        # Try to load MIDI file - if it fails due to key signature, we need to fix it
        try:
            midi = MidiFile(midi_path)
            extreme_key_found = False
            max_sharps = 0
            
            # Check for extreme key signatures
            for track in midi.tracks:
                for msg in track:
                    if msg.type == 'key_signature':
                        # Count sharps/flats (positive = sharps, negative = flats)
                        key_sharps = msg.key
                        if abs(key_sharps) > 8:
                            extreme_key_found = True
                            max_sharps = max(max_sharps, abs(key_sharps))
            
            if not extreme_key_found:
                return midi_path
                
        except Exception as e:
            # If loading fails (likely due to extreme key signature), we need to fix the raw MIDI data
            if "Could not decode key" in str(e):
                print(f"Fixing extreme key signature in raw MIDI data: {e}")
                return fix_extreme_key_signature_raw(midi_path, temp_path)
            else:
                raise e
        
        # Calculate transposition amount (bring down to max 7 sharps/flats)
        transpose_steps = max_sharps - 7
        
        # Create a normalized MIDI file
        normalized_midi = MidiFile(ticks_per_beat=midi.ticks_per_beat)
        
        for track in midi.tracks:
            new_track = mido.MidiTrack()
            
            for msg in track:
                new_msg = msg.copy()
                
                # Transpose note events
                if msg.type in ['note_on', 'note_off']:
                    if hasattr(msg, 'note'):
                        # Transpose the note down
                        new_msg.note = max(0, min(127, msg.note - transpose_steps))
                
                # Skip extreme key signature events entirely
                elif msg.type == 'key_signature' and abs(msg.key) > 8:
                    # Skip this message - don't include extreme key signatures
                    continue
                
                new_track.append(new_msg)
            
            normalized_midi.tracks.append(new_track)
        
        # Save normalized MIDI
        normalized_midi.save(temp_path)
        
        print(f"Normalized extreme key signature: {max_sharps} sharps -> {max_sharps - transpose_steps} sharps")
        return temp_path
            
    except Exception as e:
        print(f"Warning: Could not normalize key signature for {midi_path}: {e}")
        # Return original file if normalization fails
        return midi_path

def fix_extreme_key_signature_raw(midi_path, output_path):
    """
    Fix extreme key signatures by directly editing the raw MIDI bytes.
    This is a fallback when mido can't even load the file.
    """
    try:
        # Read raw MIDI bytes
        with open(midi_path, 'rb') as f:
            midi_data = bytearray(f.read())
        
        # Find and fix key signature events in the raw MIDI data
        # Key signature meta event: FF 59 02 sf mi
        # where sf = number of sharps/flats, mi = major/minor mode
        i = 0
        while i < len(midi_data) - 4:
            # Look for key signature meta event (FF 59 02)
            if (midi_data[i] == 0xFF and 
                i + 3 < len(midi_data) and 
                midi_data[i + 1] == 0x59 and 
                midi_data[i + 2] == 0x02):
                
                # Extract key signature value (signed byte)
                key_byte = midi_data[i + 3]
                if key_byte > 127:
                    key_value = key_byte - 256  # Convert to signed
                else:
                    key_value = key_byte
                
                # If extreme key signature, normalize it
                if abs(key_value) > 8:
                    if key_value > 0:
                        # Too many sharps, reduce to 7
                        new_key_value = 7
                    else:
                        # Too many flats, reduce to 7
                        new_key_value = -7
                    
                    # Convert back to unsigned byte
                    if new_key_value < 0:
                        midi_data[i + 3] = new_key_value + 256
                    else:
                        midi_data[i + 3] = new_key_value
                    
                    print(f"Fixed key signature: {key_value} -> {new_key_value}")
            
            i += 1
        
        # Write fixed MIDI data
        with open(output_path, 'wb') as f:
            f.write(midi_data)
        
        return output_path
        
    except Exception as e:
        print(f"Warning: Could not fix raw MIDI data: {e}")
        # Copy original file as fallback
        import shutil
        shutil.copy2(midi_path, output_path)
        return output_path

# Pre-computed chord patterns for fast lookup
CHORD_PATTERNS = {
    # Major triads
    (0, 4, 7): 'C', (1, 5, 8): 'C#', (2, 6, 9): 'D', (3, 7, 10): 'D#',
    (4, 8, 11): 'E', (5, 9, 0): 'F', (6, 10, 1): 'F#', (7, 11, 2): 'G',
    (8, 0, 3): 'G#', (9, 1, 4): 'A', (10, 2, 5): 'A#', (11, 3, 6): 'B',
    
    # Minor triads
    (0, 3, 7): 'Cm', (1, 4, 8): 'C#m', (2, 5, 9): 'Dm', (3, 6, 10): 'D#m',
    (4, 7, 11): 'Em', (5, 8, 0): 'Fm', (6, 9, 1): 'F#m', (7, 10, 2): 'Gm',
    (8, 11, 3): 'G#m', (9, 0, 4): 'Am', (10, 1, 5): 'A#m', (11, 2, 6): 'Bm',
    
    # Dominant 7th
    (0, 4, 7, 10): 'C7', (1, 5, 8, 11): 'C#7', (2, 6, 9, 0): 'D7',
    (3, 7, 10, 1): 'D#7', (4, 8, 11, 2): 'E7', (5, 9, 0, 3): 'F7',
    (6, 10, 1, 4): 'F#7', (7, 11, 2, 5): 'G7', (8, 0, 3, 6): 'G#7',
    (9, 1, 4, 7): 'A7', (10, 2, 5, 8): 'A#7', (11, 3, 6, 9): 'B7',
    
    # Minor 7th
    (0, 3, 7, 10): 'Cm7', (1, 4, 8, 11): 'C#m7', (2, 5, 9, 0): 'Dm7',
    (3, 6, 10, 1): 'D#m7', (4, 7, 11, 2): 'Em7', (5, 8, 0, 3): 'Fm7',
    (6, 9, 1, 4): 'F#m7', (7, 10, 2, 5): 'Gm7', (8, 11, 3, 6): 'G#m7',
    (9, 0, 4, 7): 'Am7', (10, 1, 5, 8): 'A#m7', (11, 2, 6, 9): 'Bm7',
    
    # Major 7th
    (0, 4, 7, 11): 'Cmaj7', (1, 5, 8, 0): 'C#maj7', (2, 6, 9, 1): 'Dmaj7',
    (3, 7, 10, 2): 'D#maj7', (4, 8, 11, 3): 'Emaj7', (5, 9, 0, 4): 'Fmaj7',
    (6, 10, 1, 5): 'F#maj7', (7, 11, 2, 6): 'Gmaj7', (8, 0, 3, 7): 'G#maj7',
    (9, 1, 4, 8): 'Amaj7', (10, 2, 5, 9): 'A#maj7', (11, 3, 6, 10): 'Bmaj7',
    
    # Power chords (5ths)
    (0, 7): 'C5', (1, 8): 'C#5', (2, 9): 'D5', (3, 10): 'D#5',
    (4, 11): 'E5', (5, 0): 'F5', (6, 1): 'F#5', (7, 2): 'G5',
    (8, 3): 'G#5', (9, 4): 'A5', (10, 5): 'A#5', (11, 6): 'B5',
}

@lru_cache(maxsize=1000)
def fast_chord_detection(notes_tuple):
    """
    Fast chord detection using pre-computed patterns.
    This is much faster than pychord's find_chords_from_notes().
    """
    if len(notes_tuple) < 2:
        return 'N'
    
    # Convert to sorted tuple for lookup
    notes_sorted = tuple(sorted(notes_tuple))
    
    # Check pre-computed patterns first
    if notes_sorted in CHORD_PATTERNS:
        return CHORD_PATTERNS[notes_sorted]
    
    # For 3+ notes, try to find root and determine chord type
    if len(notes_sorted) >= 3:
        # Find intervals from root
        root = notes_sorted[0]
        intervals = [(note - root) % 12 for note in notes_sorted[1:]]
        
        # Major triad: root, major 3rd (4), perfect 5th (7)
        if intervals[:2] == [4, 7]:
            return NOTE_NAMES[root]
        
        # Minor triad: root, minor 3rd (3), perfect 5th (7)
        if intervals[:2] == [3, 7]:
            return f"{NOTE_NAMES[root]}m"
        
        # Diminished triad: root, minor 3rd (3), diminished 5th (6)
        if intervals[:2] == [3, 6]:
            return f"{NOTE_NAMES[root]}dim"
        
        # Augmented triad: root, major 3rd (4), augmented 5th (8)
        if intervals[:2] == [4, 8]:
            return f"{NOTE_NAMES[root]}aug"
    
    # For 2 notes, check if it's a power chord
    if len(notes_sorted) == 2:
        interval = (notes_sorted[1] - notes_sorted[0]) % 12
        if interval == 7:  # Perfect 5th
            return f"{NOTE_NAMES[notes_sorted[0]]}5"
    
    # Fallback: return root note
    return NOTE_NAMES[notes_sorted[0]]

def notes_to_chord_label(notes):
    """
    Optimized chord detection using fast lookup patterns.
    This is much faster than the original pychord approach.
    """
    if not notes or len(notes) < 2:
        return 'N'
    
    # Convert note names to pitch classes
    pitch_classes = []
    for note in notes:
        if note in NOTE_NAMES:
            pitch_classes.append(NOTE_NAMES.index(note))
    
    if len(pitch_classes) < 2:
        return 'N'
    
    # Use fast chord detection
    return fast_chord_detection(tuple(pitch_classes))

def midi_to_chordino_labels_harmony_format(midi_path, output_path):
    """
    Generate chordino labels in harmony-analyser format: timestamp: chord_label
    
    Based on Maršík et al. (2014) paper:
    - Uses direct note analysis (simulating 4-tone selection)
    - Applies key signature normalization for extreme keys
    - Generates chord labels for harmony analyzer input
    - Optimized version with batch processing and caching
    """
    # Apply key signature normalization if needed
    normalized_midi_path = normalize_extreme_key_signatures(midi_path)
    
    mid = MidiFile(normalized_midi_path)
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

    # Process all tracks and collect events
    all_events = []
    for track in mid.tracks:
        track_time = 0
        for msg in track:
            track_time += msg.time
            if msg.type in ['note_on', 'note_off']:
                all_events.append((track_time, msg))
    
    # Sort events by time
    all_events.sort(key=lambda x: x[0])
    
    # Process events in chronological order
    current_time = 0
    notes_on = set()
    chord_cache = {}  # Cache for chord detection results
    last_chord = None
    
    for event_time, msg in all_events:
        current_time = event_time
        
        if msg.type == 'note_on' and msg.velocity > 0:
            notes_on.add(msg.note % 12)
        elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
            notes_on.discard(msg.note % 12)
        
        # Determine current chord
        # Note: This simulates the 4-tone selection from the paper
        # The harmony analyzer will further filter to 4 tones with highest presence
        if len(notes_on) >= 2:
            # Create cache key
            notes_key = tuple(sorted(notes_on))
            
            # Check cache first
            if notes_key in chord_cache:
                current_chord = chord_cache[notes_key]
            else:
                # Convert to note names and detect chord
                note_names = [NOTE_NAMES[n] for n in notes_key]
                current_chord = notes_to_chord_label(note_names)
                chord_cache[notes_key] = current_chord
        else:
            current_chord = "N"
        
        # Only append if chord changed
        if current_chord != last_chord:
            chords.append((ticks_to_seconds(current_time), current_chord))
            last_chord = current_chord
    
    # Remove consecutive duplicates more efficiently
    filtered = []
    prev_chord = None
    for timestamp, chord in chords:
        if chord != prev_chord:
            filtered.append((timestamp, chord))
            prev_chord = chord
    
    # Batch write to file
    with open(output_path, "w") as f:
        for timestamp, chord in filtered:
            f.write(f"{timestamp:.3f}: {chord}\n")

def run_harmony_analyser(midi_path):
    """
    Run the harmony analyser on a MIDI file.
    
    Based on the paper "Improving Music Classification Using Harmonic Complexity" (Maršík et al., 2014):
    - Uses NNLS Chroma and Chordino plugins for feature extraction
    - Selects 4 tones with highest presence per segment to represent chords
    - Calculates Average Transition Complexity (ATC) between consecutive chords
    - Uses 0.07 threshold for audible tones (as recommended in the paper)
    """
    import tempfile
    import shutil
    from midi_to_chroma import midi_to_chroma
    from chordino_simulation import midi_to_chordino_labels_chordino_simulation
    
    # Create temporary directory and copy MIDI file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy MIDI file to temp directory
        temp_midi = os.path.join(temp_dir, os.path.basename(midi_path))
        shutil.copy2(midi_path, temp_midi)
        
        # Generate required files for harmony analyzer
        track_id = os.path.splitext(os.path.basename(midi_path))[0]
        temp_chroma = os.path.join(temp_dir, f"{track_id}-chromas.txt")
        temp_chordino = os.path.join(temp_dir, f"{track_id}-chordino-labels.txt")
        
        # Generate chroma features
        midi_to_chroma(midi_path, temp_chroma, 10.0)
        
        # Generate chordino labels using PYCHORD approach (harmony format)
        midi_to_chordino_labels_harmony_format(midi_path, temp_chordino)
        
        # Change to temp directory
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Use absolute path to JAR file
            atc_dir = os.path.dirname(os.path.abspath(__file__))
            JAR_PATH = os.path.join(atc_dir, "harmony-analyser", "target", "ha-script-1.2-beta.jar")
            # Make sure the JAR path is absolute
            JAR_PATH = os.path.abspath(JAR_PATH)
            PLUGIN_KEY = "chord_analyser:average_chord_complexity_distance"
            cmd = [
                "java", "-Djava.awt.headless=true", "-jar", JAR_PATH,
                "-a", PLUGIN_KEY,
                "-s", ".mid",
                "-t", "0.07"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"Error running harmony-analyser for {midi_path}: {result.stderr}")
                return None
            
            # Check if output was generated
            expected_output = os.path.join(temp_dir, f"{track_id}-average-cc-distance.txt")
            if os.path.exists(expected_output):
                # Read the ATC score from the output file before temp directory is cleaned up
                try:
                    with open(expected_output, 'r') as f:
                        content = f.read()
                        # Parse all ATC metrics from the content
                        # Based on Maršík et al. (2014) paper:
                        # - ACCD: Average Chord Complexity Distance (often 7.0 = max complexity)
                        # - ACC: Average Chord Complexity (often -1.0 = normalization factor)
                        # - RCCD: Relative Chord Complexity Distance (the actual ATC metric we use)
                        accd_value = 0.0
                        acc_value = 0.0
                        rccd_value = 0.0
                        
                        for line in content.split('\n'):
                            if 'Average Chord Complexity Distance (ACCD):' in line:
                                accd_value = float(line.split(':')[1].strip()) if line.split(':')[1].strip() != 'NaN' else 0.0
                            elif 'Average Chord Complexity (ACC):' in line:
                                acc_value = float(line.split(':')[1].strip()) if line.split(':')[1].strip() != 'NaN' else 0.0
                            elif 'Relative Chord Complexity Distance (RCCD):' in line:
                                rccd_value = float(line.split(':')[1].strip()) if line.split(':')[1].strip() != 'NaN' else 0.0
                        
                        # Return RCCD as the main ATC score (Average Transition Complexity)
                        # RCCD represents the harmonic complexity as defined in the paper
                        # Note: RCCD is not constrained to 0-1 range and can exceed 1 for complex music
                        return {
                            'atc_score': rccd_value,  # Primary metric: Average Transition Complexity
                            'accd_score': accd_value,  # System parameter (often 7.0)
                            'acc_score': acc_value,    # Normalization factor (often -1.0)
                            'rccd_score': rccd_value   # Same as atc_score for consistency
                        }
                except Exception as e:
                    print(f"Error reading output file: {e}")
                    return None
            else:
                print(f"No output file generated: {expected_output}")
                return None
                
        finally:
            # Restore original working directory
            os.chdir(old_cwd)

def run_chordino_atc_analysis(midi_path):
    """
    Run CHORDINO simulation with harmony analyzer to get ATC score.
    
    This implements the CHORDINO-based approach from the paper:
    - Uses CHORDINO simulation for chord detection
    - Follows the same 4-tone selection and 0.07 threshold as the paper
    - Returns Average Transition Complexity (ATC) as RCCD metric
    """
    import tempfile
    import shutil
    from midi_to_chroma import midi_to_chroma
    from chordino_simulation import midi_to_chordino_labels_chordino_simulation
    
    # Create temporary directory and copy MIDI file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy MIDI file to temp directory
        temp_midi = os.path.join(temp_dir, os.path.basename(midi_path))
        shutil.copy2(midi_path, temp_midi)
        
        # Generate required files for harmony analyzer
        track_id = os.path.splitext(os.path.basename(midi_path))[0]
        temp_chroma = os.path.join(temp_dir, f"{track_id}-chromas.txt")
        temp_chordino = os.path.join(temp_dir, f"{track_id}-chordino-labels.txt")
        
        # Generate chroma features
        midi_to_chroma(midi_path, temp_chroma, 10.0)
        
        # Generate chordino labels using chordino simulation
        midi_to_chordino_labels_chordino_simulation(midi_path, temp_chordino)
        
        # Change to temp directory
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Use absolute path to JAR file
            atc_dir = os.path.dirname(os.path.abspath(__file__))
            JAR_PATH = os.path.join(atc_dir, "harmony-analyser", "target", "ha-script-1.2-beta.jar")
            # Make sure the JAR path is absolute
            JAR_PATH = os.path.abspath(JAR_PATH)
            PLUGIN_KEY = "chord_analyser:average_chord_complexity_distance"
            cmd = [
                "java", "-Djava.awt.headless=true", "-jar", JAR_PATH,
                "-a", PLUGIN_KEY,
                "-s", ".mid",
                "-t", "0.07"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"Error running harmony-analyser for {midi_path}: {result.stderr}")
                return None
            
            # Check if output was generated
            expected_output = os.path.join(temp_dir, f"{track_id}-average-cc-distance.txt")
            if os.path.exists(expected_output):
                # Read the ATC score from the output file before temp directory is cleaned up
                try:
                    with open(expected_output, 'r') as f:
                        content = f.read()
                        # Parse all ATC metrics from the content
                        # Based on Maršík et al. (2014) paper:
                        # - ACCD: Average Chord Complexity Distance (often 7.0 = max complexity)
                        # - ACC: Average Chord Complexity (often -1.0 = normalization factor)
                        # - RCCD: Relative Chord Complexity Distance (the actual ATC metric we use)
                        accd_value = 0.0
                        acc_value = 0.0
                        rccd_value = 0.0
                        
                        for line in content.split('\n'):
                            if 'Average Chord Complexity Distance (ACCD):' in line:
                                accd_value = float(line.split(':')[1].strip()) if line.split(':')[1].strip() != 'NaN' else 0.0
                            elif 'Average Chord Complexity (ACC):' in line:
                                acc_value = float(line.split(':')[1].strip()) if line.split(':')[1].strip() != 'NaN' else 0.0
                            elif 'Relative Chord Complexity Distance (RCCD):' in line:
                                rccd_value = float(line.split(':')[1].strip()) if line.split(':')[1].strip() != 'NaN' else 0.0
                        
                        # Return RCCD as the main ATC score (Average Transition Complexity)
                        # RCCD represents the harmonic complexity as defined in the paper
                        # Note: RCCD is not constrained to 0-1 range and can exceed 1 for complex music
                        return {
                            'atc_score': rccd_value,  # Primary metric: Average Transition Complexity
                            'accd_score': accd_value,  # System parameter (often 7.0)
                            'acc_score': acc_value,    # Normalization factor (often -1.0)
                            'rccd_score': rccd_value   # Same as atc_score for consistency
                        }
                except Exception as e:
                    print(f"Error reading output file: {e}")
                    return None
            else:
                print(f"No output file generated: {expected_output}")
                return None
                
        finally:
            # Restore original working directory
            os.chdir(old_cwd)

def parse_atc_score(output_file):
    """Parse ATC score from harmony analyser output."""
    try:
        with open(output_file, 'r') as f:
            for line in f:
                if 'Average Chord Complexity Distance' in line:
                    parts = line.strip().split(':')
                    if len(parts) == 2:
                        return float(parts[1].strip())
    except Exception as e:
        print(f"Error reading/parsing {output_file}: {e}")
    return None

def main():
    """Main function for standalone testing."""
    if len(sys.argv) < 2:
        print("Usage: python single_midi_atc.py <midi_file>")
        sys.exit(1)
    
    midi_file = sys.argv[1]
    # Use current directory for output to avoid permission issues
    base_name = os.path.splitext(os.path.basename(midi_file))[0]
    chordino_path = f"{base_name}-chordino-labels.txt"
    
    print(f"Generating optimized chord labels for {midi_file}...")
    start_time = time.time()
    midi_to_chordino_labels_harmony_format(midi_file, chordino_path)
    end_time = time.time()
    
    print(f"Optimized chord generation completed in {end_time - start_time:.2f} seconds")
    print(f"Output saved to: {chordino_path}")

if __name__ == "__main__":
    main() 