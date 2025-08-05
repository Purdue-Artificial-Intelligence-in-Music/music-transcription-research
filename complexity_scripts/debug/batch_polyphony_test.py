#!/usr/bin/env python3
"""
Batch Polyphony Test Script
Test event-based vs adaptive resolution on 30 files
"""

import pretty_midi
import numpy as np
import os
import sys
from pathlib import Path

def is_percussion_instrument(instrument):
    """Advanced percussion detection"""
    if instrument.is_drum:
        return True
    percussion_programs = [47, 112, 113, 114, 115, 116, 117, 118, 119]
    if instrument.program in percussion_programs:
        return True
    name_lower = instrument.name.lower()
    if any(drum_word in name_lower for drum_word in ['drum', 'percussion', 'cymbal', 'timpani']):
        return True
    return False

def calculate_adaptive_time_resolution(all_notes):
    """Calculate adaptive time resolution"""
    if not all_notes:
        return 0.01
    
    durations = []
    for note in all_notes:
        duration = note.end - note.start
        if duration > 0:
            durations.append(duration)
    
    if not durations:
        return 0.01
    
    shortest_duration = min(durations)
    adaptive_resolution = shortest_duration / 4
    adaptive_resolution = max(0.001, min(0.1, adaptive_resolution))
    
    return adaptive_resolution, shortest_duration

def calculate_polyphony_metrics(polyphony_series):
    """Calculate basic polyphony metrics"""
    if not polyphony_series:
        return 0, 0, 0, 0
    
    max_polyphony = max(polyphony_series)
    avg_polyphony = np.mean(polyphony_series)
    std_polyphony = np.std(polyphony_series)
    
    polyphonic_moments = sum(1 for p in polyphony_series if p > 1)
    polyphony_density = polyphonic_moments / len(polyphony_series) if polyphony_series else 0
    
    return max_polyphony, avg_polyphony, std_polyphony, polyphony_density

def calculate_polyphony_adaptive_resolution(midi_data):
    """Calculate polyphony using adaptive resolution"""
    all_notes = []
    for instrument in midi_data.instruments:
        if not is_percussion_instrument(instrument):
            all_notes.extend(instrument.notes)
    
    if not all_notes:
        return 0, 0, 0, 0
    
    adaptive_resolution, shortest_duration = calculate_adaptive_time_resolution(all_notes)
    
    start_times = [note.start for note in all_notes]
    end_times = [note.end for note in all_notes]
    min_time = min(start_times)
    max_time = max(end_times)
    
    time_points = np.arange(min_time, max_time + adaptive_resolution, adaptive_resolution)
    
    polyphony_series = []
    for time in time_points:
        active_notes = 0
        for note in all_notes:
            if note.start <= time < note.end:
                active_notes += 1
        polyphony_series.append(active_notes)
    
    return calculate_polyphony_metrics(polyphony_series)

def calculate_polyphony_event_based(midi_data):
    """Calculate polyphony using CORRECTED event-based approach with time-weighted calculations"""
    all_notes = []
    for instrument in midi_data.instruments:
        if not is_percussion_instrument(instrument):
            all_notes.extend(instrument.notes)
    
    if not all_notes:
        return 0, 0, 0, 0
    
    # Get all unique time points (note starts and ends)
    time_points = set()
    for note in all_notes:
        time_points.add(note.start)
        time_points.add(note.end)
    time_points = sorted(list(time_points))
    
    # Calculate polyphony at each time point
    polyphony_series = []
    for time_point in time_points:
        active_notes = 0
        for note in all_notes:
            if note.start <= time_point < note.end:
                active_notes += 1
        polyphony_series.append(active_notes)
    
    # Calculate time-weighted average (this is the key fix!)
    time_intervals = []
    for i in range(len(time_points) - 1):
        interval = time_points[i + 1] - time_points[i]
        time_intervals.append(interval)
    
    # Calculate weighted average based on time intervals
    weighted_sum = 0
    total_time = 0
    
    for i in range(len(polyphony_series) - 1):
        polyphony = polyphony_series[i]
        interval = time_intervals[i]
        weighted_sum += polyphony * interval
        total_time += interval
    
    avg_polyphony = weighted_sum / total_time if total_time > 0 else 0
    
    # Calculate other metrics
    max_polyphony = max(polyphony_series)
    
    # Calculate weighted standard deviation
    variance_sum = 0
    for i in range(len(polyphony_series) - 1):
        polyphony = polyphony_series[i]
        interval = time_intervals[i]
        variance_sum += ((polyphony - avg_polyphony) ** 2) * interval
    
    std_polyphony = np.sqrt(variance_sum / total_time) if total_time > 0 else 0
    
    # Calculate density (time-weighted)
    polyphonic_time = 0
    for i in range(len(polyphony_series) - 1):
        polyphony = polyphony_series[i]
        interval = time_intervals[i]
        if polyphony > 1:
            polyphonic_time += interval
    
    polyphony_density = polyphonic_time / total_time if total_time > 0 else 0
    
    return max_polyphony, avg_polyphony, std_polyphony, polyphony_density

def process_single_file(file_path):
    """Process a single MIDI file and return results"""
    try:
        midi_data = pretty_midi.PrettyMIDI(file_path)
        
        # Calculate using both approaches
        max_adaptive, avg_adaptive, std_adaptive, density_adaptive = calculate_polyphony_adaptive_resolution(midi_data)
        max_event, avg_event, std_event, density_event = calculate_polyphony_event_based(midi_data)
        
        # Check if results are similar
        max_diff = abs(max_adaptive - max_event)
        avg_diff = abs(avg_adaptive - avg_event)
        std_diff = abs(std_adaptive - std_event)
        density_diff = abs(density_adaptive - density_event)
        
        similar = (max_diff <= 1 and avg_diff < 0.1 and std_diff < 0.1 and density_diff < 0.05)
        
        return {
            'file': os.path.basename(file_path),
            'max_adaptive': max_adaptive,
            'avg_adaptive': avg_adaptive,
            'std_adaptive': std_adaptive,
            'density_adaptive': density_adaptive,
            'max_event': max_event,
            'avg_event': avg_event,
            'std_event': std_event,
            'density_event': density_event,
            'similar': similar,
            'max_diff': max_diff,
            'avg_diff': avg_diff,
            'std_diff': std_diff,
            'density_diff': density_diff
        }
        
    except Exception as e:
        return {
            'file': os.path.basename(file_path),
            'error': str(e),
            'similar': False
        }

def main():
    """Main function to process multiple files"""
    
    # Get list of files to process - specifically Track00001-Track00030
    base_path = "/scratch/gilbreth/shang33/AIM/datasets/slakh2100"
    train_path = f"{base_path}/train"
    test_path = f"{base_path}/test"
    
    # Get list of available files - specifically Track00001-Track00030
    files_to_process = []
    
    # Generate Track00001-Track00030
    for i in range(1, 31):
        track_name = f"Track{i:05d}"  # Track00001, Track00002, etc.
        
        # Check train directory first
        train_file = f"{train_path}/{track_name}/{track_name}.mid"
        if os.path.exists(train_file):
            files_to_process.append(train_file)
        else:
            # Check test directory
            test_file = f"{test_path}/{track_name}/{track_name}.mid"
            if os.path.exists(test_file):
                files_to_process.append(test_file)
    
    print(f"🎵 BATCH POLYPHONY TEST")
    print(f"📁 Processing {len(files_to_process)} files (Track00001-Track00030)")
    print("="*60)
    
    results = []
    similar_count = 0
    different_count = 0
    error_count = 0
    
    for i, file_path in enumerate(files_to_process, 1):
        print(f"Processing {i}/{len(files_to_process)}: {os.path.basename(file_path)}")
        
        result = process_single_file(file_path)
        results.append(result)
        
        if 'error' in result:
            error_count += 1
            print(f"  ❌ Error: {result['error']}")
        elif result['similar']:
            similar_count += 1
            print(f"  ✅ Similar results")
        else:
            different_count += 1
            print(f"  ⚠️  Different results")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 SUMMARY RESULTS")
    print("="*60)
    print(f"📁 Total files processed: {len(results)}")
    print(f"✅ Similar results: {similar_count}")
    print(f"⚠️  Different results: {different_count}")
    print(f"❌ Errors: {error_count}")
    
    # Show detailed results for different files
    if different_count > 0:
        print(f"\n📋 DETAILED RESULTS FOR DIFFERENT FILES:")
        for result in results:
            if not result.get('similar', True) and 'error' not in result:
                print(f"\n📁 {result['file']}:")
                print(f"   Max: {result['max_adaptive']} (adaptive) vs {result['max_event']} (event)")
                print(f"   Avg: {result['avg_adaptive']:.3f} (adaptive) vs {result['avg_event']:.3f} (event)")
                print(f"   Std: {result['std_adaptive']:.3f} (adaptive) vs {result['std_event']:.3f} (event)")
                print(f"   Density: {result['density_adaptive']:.3f} (adaptive) vs {result['density_event']:.3f} (event)")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main() 