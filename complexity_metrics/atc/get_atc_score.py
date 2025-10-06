#!/usr/bin/env python3
"""
ATC Score Calculator
Calculates ATC (Automatic Transcription Complexity) score using the harmony-analyser Java tool.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import time

def calculate_atc_score(midi_file_path):
    """
    Calculate ATC score for a MIDI file using the harmony-analyser Java tool.
    
    Args:
        midi_file_path: Path to MIDI file
        
    Returns:
        ATC score as float
    """
    try:
        # Check if harmony-analyser JAR exists
        jar_path = os.path.join('harmony-analyser', 'target', 'ha-script-1.2-beta.jar')
        if not os.path.exists(jar_path):
            print(f"Error: Harmony analyser JAR not found at {jar_path}")
            return 0.0
        
        # Convert MIDI to chordino labels first
        base_name = os.path.splitext(os.path.basename(midi_file_path))[0]
        chordino_path = f"{base_name}-chordino-labels.txt"
        
        # Import the function from single_midi_atc.py
        from single_midi_atc import midi_to_chordino_labels_harmony_format
        midi_to_chordino_labels_harmony_format(midi_file_path, chordino_path)
        
        if not os.path.exists(chordino_path):
            print(f"Error: Could not generate chordino labels for {midi_file_path}")
            return 0.0
        
        # Run harmony-analyser on the chordino labels
        cmd = ['java', '-jar', jar_path, '-a', 'chord_analyser:average_chord_complexity_distance', chordino_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the ATC score from output
        output = result.stdout.strip()
        try:
            atc_score = float(output)
            return atc_score
        except ValueError:
            print(f"Error: Could not parse ATC score from output: {output}")
            return 0.0
            
    except subprocess.CalledProcessError as e:
        print(f"Error running harmony-analyser: {e.stderr}")
        return 0.0
    except Exception as e:
        print(f"Error calculating ATC score: {e}")
        return 0.0
    finally:
        # Clean up temporary chordino file
        if 'chordino_path' in locals() and os.path.exists(chordino_path):
            try:
                os.remove(chordino_path)
            except:
                pass

def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python get_atc_score.py <midi_file>")
        sys.exit(1)
    
    midi_file = sys.argv[1]
    
    if not os.path.exists(midi_file):
        print(f"Error: MIDI file not found: {midi_file}")
        sys.exit(1)
    
    print(f"Calculating ATC score for: {midi_file}")
    atc_score = calculate_atc_score(midi_file)
    print(f"ATC Score for '{os.path.basename(midi_file)}': {atc_score}")

if __name__ == "__main__":
    main()
