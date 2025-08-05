#!/usr/bin/env python3
"""
Entropy Analysis Module
Calculates tonal certainty, pitch class entropy, melodic interval entropy, and IOI entropy.
"""

import math
import os
import statistics
from fractions import Fraction
from collections import Counter
from music21 import converter, note, chord

def extract_pitch_classes_mathematical(midi_stream):
    """Extract pitch classes from MIDI stream using Music21."""
    result = []
    for current_note in midi_stream.flatten().notes:
        try:
            if isinstance(current_note, note.Note):
                result.append(max(0.0, current_note.pitch.pitchClass))
            elif isinstance(current_note, chord.Chord):
                for pitch in current_note.pitches:
                    result.append(max(0.0, pitch.pitchClass))
        except (AttributeError, TypeError):
            # Skip percussion/unpitched notes that don't have pitchClass
            continue
    return result

def extract_melody_notes_mathematical(midi_stream):
    """Extract melody notes (highest note at each time point)."""
    notes = midi_stream.flatten().notes
    off_set = []
    m_notes = []
    highest_notes = []

    for i in range(0, len(notes)):
        if notes[i].offset in off_set:
            continue

        try:
            if isinstance(notes[i], chord.Chord):
                chord_pitches = notes[i].pitches
                p = []
                for x in chord_pitches:
                    p.append(x.pitchClass)
                m_note = max(p)
            else:
                m_note = notes[i].pitch.pitchClass
        except (AttributeError, TypeError):
            # Skip percussion/unpitched notes
            continue

        try:
            for y in range(1, 5):
                if i + y < len(notes) and notes[i + y].offset == notes[i].offset:
                    if isinstance(notes[i + y], chord.Chord):
                        chord_pitches = notes[i + y].pitches
                        p = []
                        for x in chord_pitches:
                            p.append(x.pitchClass)
                        sec_max = max(p)
                    else:
                        sec_max = notes[i + y].pitch.pitchClass
                    m_note = m_note if (m_note > sec_max) else sec_max
        except (IndexError, AttributeError, TypeError):
            pass

        off_set.append(notes[i].offset)
        m_notes.append(m_note)

    for i in m_notes:
        highest_notes.append(max(0, int(i)))

    return highest_notes

def extract_ioi_mathematical(midi_stream):
    """Extract inter-onset intervals from MIDI stream."""
    ioi_list = []
    off_set = []
    notes = midi_stream.flatten().notes

    for i in range(0, len(notes)):
        if notes[i].offset not in off_set:
            m_note = notes[i]
            off_set.append(m_note.offset)

    for i in range(1, len(off_set)):
        try:
            ioi = Fraction(off_set[i] - off_set[i - 1]).limit_denominator(4)
            ioi_list.append(ioi)
        except (ValueError, TypeError):
            # Handle cases where Fraction conversion fails
            try:
                ioi_float = float(off_set[i] - off_set[i - 1])
                ioi_list.append(ioi_float)
            except (ValueError, TypeError):
                # Skip this interval if we can't convert it
                continue

    return ioi_list

def calculate_entropy_mathematical(data_list):
    """Calculate entropy using standard information theory."""
    if not data_list:
        return []
    
    # Use Counter for O(n) counting
    counter = Counter(data_list)
    total_count = len(data_list)
    
    result = []
    for value, count in counter.items():
        p = count / total_count
        entr = p * (math.log2(p))
        result.append(entr)
    
    return result

def calculate_pitch_interval_entropy_mathematical(pitch_list):
    """Calculate pitch interval entropy with filtering for intervals <= 12 semitones."""
    if len(pitch_list) < 2:
        return []
    
    # Calculate intervals efficiently
    intervals = []
    for i in range(1, len(pitch_list)):
        interval = pitch_list[i] - pitch_list[i - 1]
        # Ignore intervals > 12 notes (original mechanism)
        if abs(interval) <= 12:
            intervals.append(interval)
    
    return calculate_entropy_mathematical(intervals)

def analyze_tonal_certainty_corrected(midi_stream):
    """Analyze tonal certainty using Music21 key analysis."""
    try:
        # Filter out percussion and unpitched instruments for tonal analysis
        filtered_stream = midi_stream.flatten()
        
        # Remove percussion chords and unpitched notes
        notes_to_remove = []
        for note_obj in filtered_stream.notes:
            if is_percussion_or_unpitched(note_obj):
                notes_to_remove.append(note_obj)
        
        # Remove the identified notes
        for note_obj in notes_to_remove:
            filtered_stream.remove(note_obj)
        
        # Only analyze if we have enough pitched notes
        if len(filtered_stream.notes) > 0:
            return filtered_stream.analyze("key").tonalCertainty()
        else:
            return 0.0
            
    except Exception as e:
        print(f"Error in tonal certainty analysis: {e}")
        return 0.0

def is_percussion_or_unpitched(note_obj):
    """Check if note is percussion or unpitched."""
    try:
        # Check for PercussionChord objects - these are definitely percussion
        if hasattr(note_obj, '__class__') and 'Percussion' in note_obj.__class__.__name__:
            return True
        
        # Check for Unpitched objects - these are definitely unpitched
        if hasattr(note_obj, '__class__') and 'Unpitched' in note_obj.__class__.__name__:
            return True
        
        # Check for notes without pitch information
        if not hasattr(note_obj, 'pitch') or not hasattr(note_obj.pitch, 'pitchClass'):
            return True
        
        # For everything else, assume it's tonal
        return False
    except:
        return False

def analyze_pitch_class_entropy_mathematical(midi_stream):
    """Analyze pitch class entropy."""
    notes = extract_pitch_classes_mathematical(midi_stream)
    entropy_contributions = calculate_entropy_mathematical(notes)
    return 0 - sum(entropy_contributions)

def analyze_melodic_interval_entropy_mathematical(midi_stream):
    """Analyze melodic interval entropy."""
    melody_notes = extract_melody_notes_mathematical(midi_stream)
    entropy_contributions = calculate_pitch_interval_entropy_mathematical(melody_notes)
    return 0 - sum(entropy_contributions)

def analyze_ioi_entropy_mathematical(midi_stream):
    """Analyze inter-onset interval entropy."""
    ioi_list = extract_ioi_mathematical(midi_stream)
    entropy_contributions = calculate_entropy_mathematical(ioi_list)
    return 0 - sum(entropy_contributions)

def calculate_polyphony_mathematical(midi_stream):
    """Calculate polyphony using event-based approach."""
    # Get all notes with their start and end times
    all_notes = []
    for current_note in midi_stream.flatten().notes:
        try:
            if isinstance(current_note, note.Note):
                all_notes.append({
                    'start': current_note.offset,
                    'end': current_note.offset + current_note.duration.quarterLength,
                    'pitch': current_note.pitch.pitchClass
                })
            elif isinstance(current_note, chord.Chord):
                for pitch in current_note.pitches:
                    all_notes.append({
                        'start': current_note.offset,
                        'end': current_note.offset + current_note.duration.quarterLength,
                        'pitch': pitch.pitchClass
                    })
        except (AttributeError, TypeError):
            # Skip percussion/unpitched notes
            continue
    
    if not all_notes:
        return 0, 0, 0, 0
    
    # Get all unique time points (note starts and ends)
    time_points = set()
    for note_info in all_notes:
        time_points.add(note_info['start'])
        time_points.add(note_info['end'])
    
    time_points = sorted(list(time_points))
    
    # Calculate polyphony at each time point
    polyphony_series = []
    for time_point in time_points:
        active_notes = 0
        for note_info in all_notes:
            if note_info['start'] <= time_point < note_info['end']:
                active_notes += 1
        polyphony_series.append(active_notes)
    
    # Calculate metrics
    max_polyphony = max(polyphony_series)
    
    # Calculate time-weighted average
    time_intervals = []
    for i in range(len(time_points) - 1):
        interval = time_points[i + 1] - time_points[i]
        time_intervals.append(interval)
    
    # Calculate weighted average
    weighted_sum = 0
    total_time = 0
    
    for i in range(len(polyphony_series) - 1):
        polyphony = polyphony_series[i]
        interval = time_intervals[i]
        weighted_sum += polyphony * interval
        total_time += interval
    
    avg_polyphony = weighted_sum / total_time if total_time > 0 else 0
    
    # Calculate weighted standard deviation
    variance_sum = 0
    for i in range(len(polyphony_series) - 1):
        polyphony = polyphony_series[i]
        interval = time_intervals[i]
        variance_sum += ((polyphony - avg_polyphony) ** 2) * interval
    
    std_polyphony = math.sqrt(variance_sum / total_time) if total_time > 0 else 0
    
    # Calculate density (time-weighted)
    polyphonic_time = 0
    for i in range(len(polyphony_series) - 1):
        polyphony = polyphony_series[i]
        interval = time_intervals[i]
        if polyphony > 1:
            polyphonic_time += interval
    
    polyphony_density = polyphonic_time / total_time if total_time > 0 else 0
    
    return max_polyphony, avg_polyphony, std_polyphony, polyphony_density

def main(midi_file_path):
    """Analyze a single MIDI file for entropy metrics."""
    
    if not os.path.exists(midi_file_path):
        print(f"Error: File {midi_file_path} does not exist")
        return None
    
    try:
        # Load MIDI file using Music21
        midi_stream = converter.parse(midi_file_path)
        
        print(f"🎵 ENTROPY ANALYSIS")
        print(f"📁 File: {os.path.basename(midi_file_path)}")
        print("="*50)
        
        # Analyze entropy metrics
        k_piece = analyze_tonal_certainty_corrected(midi_stream)
        Hpc_piece = analyze_pitch_class_entropy_mathematical(midi_stream)
        Hpi_piece = analyze_melodic_interval_entropy_mathematical(midi_stream)
        Hioi_piece = analyze_ioi_entropy_mathematical(midi_stream)
        
        # Calculate polyphony
        max_poly, avg_poly, std_poly, density_poly = calculate_polyphony_mathematical(midi_stream)
        
        # Print results
        print(f"🎼 Tonal Certainty: {k_piece:.4f}")
        print(f"")
        print(f"🎵 Pitch Class Entropy: {Hpc_piece:.4f}")
        print(f"")
        print(f"🎹 Melodic Interval Entropy: {Hpi_piece:.4f}")
        print(f"")
        print(f"⏱️  IOI Entropy: {Hioi_piece:.4f}")
        print(f"")
        print(f"🎹 Max Polyphony: {max_poly}")
        print(f"📊 Average Polyphony: {avg_poly:.3f}")
        print(f"📈 Standard Deviation: {std_poly:.3f}")
        print(f"🎯 Polyphony Density: {density_poly:.3f}")
        
        # Debug info
        pitch_classes = extract_pitch_classes_mathematical(midi_stream)
        print(f"")
        print(f"🔍 DEBUG INFO:")
        print(f"   Total pitch classes: {len(pitch_classes)}")
        print(f"   Unique pitch classes: {len(set(pitch_classes))}")
        print(f"   Pitch class distribution: {dict(Counter(pitch_classes))}")
        
        return {
            'tonal_certainty_piece': k_piece,
            'pitch_class_entropy_piece': Hpc_piece,
            'melodic_interval_entropy_piece': Hpi_piece,
            'ioi_entropy_piece': Hioi_piece,
            'max_polyphony': max_poly,
            'avg_polyphony': avg_poly,
            'std_polyphony': std_poly,
            'polyphony_density': density_poly,
        }
        
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("Usage: python entropy_corrected_final.py <midi_file>") 