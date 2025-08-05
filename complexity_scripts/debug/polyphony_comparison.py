#!/usr/bin/env python3
"""
Polyphony Comparison Script
Compare polyphony metrics across different time resolutions
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from complexity_metrics.polyphony import main as polyphony_analysis
from complexity_pipeline.dataset_manager import get_dataset_manager

def calculate_polyphony_fine_resolution(midi_data):
    """Calculate polyphony using fine time resolution (0.01s)"""
    # Get all notes with their start and end times
    all_notes = []
    for current_note in midi_data.flatten().notes:
        try:
            if hasattr(current_note, 'pitch'):
                all_notes.append({
                    'start': current_note.offset,
                    'end': current_note.offset + current_note.duration.quarterLength,
                    'pitch': current_note.pitch.pitchClass
                })
            elif hasattr(current_note, 'pitches'):
                for pitch in current_note.pitches:
                    all_notes.append({
                        'start': current_note.offset,
                        'end': current_note.offset + current_note.duration.quarterLength,
                        'pitch': pitch.pitchClass
                    })
        except (AttributeError, TypeError):
            continue
    
    if not all_notes:
        return 0, 0, 0, 0
    
    # Use fine time resolution (0.01s)
    time_resolution = 0.01
    total_duration = max(note['end'] for note in all_notes)
    time_points = np.arange(0, total_duration, time_resolution)
    
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
    avg_polyphony = np.mean(polyphony_series)
    std_polyphony = np.std(polyphony_series)
    polyphony_density = sum(1 for p in polyphony_series if p > 1) / len(polyphony_series)
    
    return max_polyphony, avg_polyphony, std_polyphony, polyphony_density

def calculate_polyphony_adaptive_resolution(midi_data):
    """Calculate polyphony using adaptive time resolution"""
    # Get all notes with their start and end times
    all_notes = []
    for current_note in midi_data.flatten().notes:
        try:
            if hasattr(current_note, 'pitch'):
                all_notes.append({
                    'start': current_note.offset,
                    'end': current_note.offset + current_note.duration.quarterLength,
                    'pitch': current_note.pitch.pitchClass
                })
            elif hasattr(current_note, 'pitches'):
                for pitch in current_note.pitches:
                    all_notes.append({
                        'start': current_note.offset,
                        'end': current_note.offset + current_note.duration.quarterLength,
                        'pitch': pitch.pitchClass
                    })
        except (AttributeError, TypeError):
            continue
    
    if not all_notes:
        return 0, 0, 0, 0
    
    # Calculate adaptive resolution based on shortest note duration
    durations = [note['end'] - note['start'] for note in all_notes]
    shortest_duration = min(durations) if durations else 0.1
    adaptive_resolution = shortest_duration / 4
    
    total_duration = max(note['end'] for note in all_notes)
    time_points = np.arange(0, total_duration, adaptive_resolution)
    
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
    avg_polyphony = np.mean(polyphony_series)
    std_polyphony = np.std(polyphony_series)
    polyphony_density = sum(1 for p in polyphony_series if p > 1) / len(polyphony_series)
    
    return max_polyphony, avg_polyphony, std_polyphony, polyphony_density

def compare_polyphony_methods(file_path):
    """Compare polyphony calculations using different methods"""
    print(f"🔍 POLYPHONY COMPARISON")
    print(f"📁 File: {os.path.basename(file_path)}")
    print("="*60)
    
    try:
        from music21 import converter
        midi_data = converter.parse(file_path)
        
        # Method 1: Event-based (original implementation)
        print(f"🎹 METHOD 1: Event-based (Original)")
        try:
            results_event = polyphony_analysis(file_path)
            if results_event:
                print(f"   Max: {results_event.get('max_polyphony', 0)}")
                print(f"   Avg: {results_event.get('avg_polyphony', 0):.3f}")
                print(f"   Std: {results_event.get('std_polyphony', 0):.3f}")
                print(f"   Density: {results_event.get('polyphony_density', 0):.3f}")
            else:
                print("   ❌ No results")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print(f"")
        
        # Method 2: Fine resolution (0.01s)
        print(f"🎹 METHOD 2: Fine Resolution (0.01s)")
        try:
            max_fine, avg_fine, std_fine, density_fine = calculate_polyphony_fine_resolution(midi_data)
            print(f"   Max: {max_fine}")
            print(f"   Avg: {avg_fine:.3f}")
            print(f"   Std: {std_fine:.3f}")
            print(f"   Density: {density_fine:.3f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print(f"")
        
        # Method 3: Adaptive resolution
        print(f"🎹 METHOD 3: Adaptive Resolution")
        try:
            max_adaptive, avg_adaptive, std_adaptive, density_adaptive = calculate_polyphony_adaptive_resolution(midi_data)
            print(f"   Max: {max_adaptive}")
            print(f"   Avg: {avg_adaptive:.3f}")
            print(f"   Std: {std_adaptive:.3f}")
            print(f"   Density: {density_adaptive:.3f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return {
            'event_based': results_event,
            'fine_resolution': (max_fine, avg_fine, std_fine, density_fine),
            'adaptive_resolution': (max_adaptive, avg_adaptive, std_adaptive, density_adaptive)
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def compare_polyphony_batch(dataset_name="slakh2100", limit=5):
    """Compare polyphony methods across multiple files"""
    print(f"🔍 BATCH POLYPHONY COMPARISON")
    print(f"📊 Dataset: {dataset_name}")
    print(f"📁 Files: {limit}")
    print("="*60)
    
    try:
        # Get dataset files
        manager = get_dataset_manager()
        files = manager.find_files(dataset_name, limit=limit)
        
        results = []
        for i, file_path in enumerate(files, 1):
            print(f"Processing {i}/{len(files)}: {file_path.name}")
            
            try:
                comparison = compare_polyphony_methods(str(file_path))
                if comparison:
                    result = {
                        'filename': file_path.name,
                        'dataset': dataset_name
                    }
                    
                    # Add event-based results
                    if comparison['event_based']:
                        result.update({
                            'event_max': comparison['event_based'].get('max_polyphony', 0),
                            'event_avg': comparison['event_based'].get('avg_polyphony', 0),
                            'event_std': comparison['event_based'].get('std_polyphony', 0),
                            'event_density': comparison['event_based'].get('polyphony_density', 0)
                        })
                    
                    # Add fine resolution results
                    if comparison['fine_resolution']:
                        max_f, avg_f, std_f, density_f = comparison['fine_resolution']
                        result.update({
                            'fine_max': max_f,
                            'fine_avg': avg_f,
                            'fine_std': std_f,
                            'fine_density': density_f
                        })
                    
                    # Add adaptive resolution results
                    if comparison['adaptive_resolution']:
                        max_a, avg_a, std_a, density_a = comparison['adaptive_resolution']
                        result.update({
                            'adaptive_max': max_a,
                            'adaptive_avg': avg_a,
                            'adaptive_std': std_a,
                            'adaptive_density': density_a
                        })
                    
                    results.append(result)
                    
            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}")
        
        # Create comparison DataFrame
        if results:
            df = pd.DataFrame(results)
            print(f"")
            print(f"📊 RESULTS SUMMARY:")
            print(f"   Files processed: {len(results)}")
            
            # Save results
            output_file = f"polyphony_comparison_{dataset_name}.csv"
            df.to_csv(output_file, index=False)
            print(f"💾 Results saved to: {output_file}")
            
            return df
        else:
            print("❌ No results generated")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Main comparison function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare polyphony methods")
    parser.add_argument("--file", type=str, help="Single file to compare")
    parser.add_argument("--dataset", type=str, default="slakh2100", help="Dataset to analyze")
    parser.add_argument("--limit", type=int, default=5, help="Number of files to analyze")
    
    args = parser.parse_args()
    
    if args.file:
        # Compare single file
        compare_polyphony_methods(args.file)
    else:
        # Compare batch
        compare_polyphony_batch(args.dataset, args.limit)

if __name__ == "__main__":
    main() 