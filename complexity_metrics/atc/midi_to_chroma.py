#!/usr/bin/env python3
"""
Convert MIDI file to chroma features for harmony-analyser.

This script converts a MIDI file to chroma features (12-dimensional vectors)
that can be used by the harmony-analyser for ATC analysis.
"""

import os
import sys
import numpy as np
from mido import MidiFile
import argparse

def midi_to_chroma(midi_path, output_path, frame_rate=10.0):
    """
    Convert MIDI file to chroma features.
    
    Args:
        midi_path: Path to MIDI file
        output_path: Path to output chroma file
        frame_rate: Number of chroma frames per second
    """
    mid = MidiFile(midi_path)
    
    # Find tempo
    tempo = 500000  # default MIDI tempo (microseconds per beat)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
    
    # Calculate total duration in seconds
    total_ticks = 0
    for track in mid.tracks:
        for msg in track:
            total_ticks += msg.time
    
    # Convert ticks to seconds
    ticks_per_beat = mid.ticks_per_beat
    total_duration = total_ticks * tempo / 1e6 / ticks_per_beat
    
    # Calculate number of frames
    num_frames = int(total_duration * frame_rate)
    
    # Initialize chroma matrix
    chroma_matrix = np.zeros((num_frames, 12))
    
    # Process MIDI events
    current_ticks = 0
    notes_on = {}  # {note: velocity}
    
    def ticks_to_seconds(ticks):
        return ticks * tempo / 1e6 / ticks_per_beat
    
    for track in mid.tracks:
        for msg in track:
            current_ticks += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                notes_on[msg.note] = msg.velocity
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in notes_on:
                    del notes_on[msg.note]
            
            # Convert current time to frame index
            current_time_seconds = ticks_to_seconds(current_ticks)
            frame_idx = int(current_time_seconds * frame_rate)
            if frame_idx >= num_frames:
                frame_idx = num_frames - 1
            
            # Update chroma for current frame
            for note, velocity in notes_on.items():
                pitch_class = note % 12
                # Normalize velocity to 0-1 range
                intensity = velocity / 127.0
                chroma_matrix[frame_idx, pitch_class] += intensity
    
    # Normalize chroma vectors
    for i in range(num_frames):
        norm = np.linalg.norm(chroma_matrix[i])
        if norm > 0:
            chroma_matrix[i] /= norm
    
    # Write chroma file in the format expected by harmony-analyser
    # Format: timestamp: chroma_values (with colon after timestamp)
    with open(output_path, 'w') as f:
        for i in range(num_frames):
            timestamp = i / frame_rate
            chroma_values = chroma_matrix[i]
            f.write(f"{timestamp:.3f}: {chroma_values[0]:.6f} {chroma_values[1]:.6f} {chroma_values[2]:.6f} {chroma_values[3]:.6f} {chroma_values[4]:.6f} {chroma_values[5]:.6f} {chroma_values[6]:.6f} {chroma_values[7]:.6f} {chroma_values[8]:.6f} {chroma_values[9]:.6f} {chroma_values[10]:.6f} {chroma_values[11]:.6f}\n")

def main():
    parser = argparse.ArgumentParser(description='Convert MIDI file to chroma features')
    parser.add_argument('midi_file', help='Input MIDI file')
    parser.add_argument('output_file', help='Output chroma file')
    parser.add_argument('--frame-rate', type=float, default=10.0, help='Frames per second (default: 10.0)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.midi_file):
        print(f"Error: MIDI file '{args.midi_file}' not found.")
        sys.exit(1)
    
    midi_to_chroma(args.midi_file, args.output_file, args.frame_rate)
    print(f"Converted {args.midi_file} to chroma features: {args.output_file}")

if __name__ == "__main__":
    main() 