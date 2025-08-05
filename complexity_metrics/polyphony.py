#!/usr/bin/env python3
"""
Improved Polyphony Implementation
Based on learnings from mathematical analysis
"""

import pretty_midi
import numpy as np
import statistics
import os

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

def calculate_polyphony_metrics(polyphony_series):
    """Calculate basic polyphony metrics (for backward compatibility)"""
    if not polyphony_series:
        return {
            'global_max_polyphony': 0,
            'global_avg_polyphony': 0,
            'global_polyphony_density': 0,
            'global_polyphony_variation': 0
        }
    
    max_polyphony = max(polyphony_series)
    avg_polyphony = np.mean(polyphony_series)
    std_polyphony = np.std(polyphony_series)
    
    polyphonic_moments = sum(1 for p in polyphony_series if p > 1)
    polyphony_density = polyphonic_moments / len(polyphony_series) if polyphony_series else 0
    
    return {
        'global_max_polyphony': max_polyphony,
        'global_avg_polyphony': avg_polyphony,
        'global_polyphony_density': polyphony_density,
        'global_polyphony_variation': std_polyphony
    }

def calculate_polyphony_by_measures_improved(midi_stream, measures_count, preprocessed_data=None):
    """
    Calculate polyphony metrics for 16-measure segments using improved approach.
    
    Args:
        midi_stream: Music21 stream object
        measures_count: Total number of measures in the piece
        preprocessed_data: Optional preprocessed data
        
    Returns:
        Dictionary with segment-based polyphony metrics
    """
    # Use event-based polyphony calculation for better accuracy
    if hasattr(midi_stream, '_original_file_path'):
        midi_data = pretty_midi.PrettyMIDI(midi_stream._original_file_path)
        max_poly, avg_poly, std_poly, density_poly = calculate_polyphony_event_based(midi_data)
        
        # For segmentation, we'll use a simplified approach since we can't easily
        # segment PrettyMIDI data by measures. We'll use time-based segmentation.
        total_duration = midi_data.get_end_time()
        estimated_measures = int(total_duration / 2)  # Rough estimate
        
        # Adaptive segment size
        if estimated_measures < 16:
            segment_size = max(4, estimated_measures // 2) if estimated_measures >= 8 else estimated_measures
        else:
            segment_size = 16
        
        # Time-based segmentation (8 segments)
        num_segments = 8
        segment_duration = total_duration / num_segments
        
        segment_metrics = []
        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            
            # Extract polyphony for this time segment
            segment_notes = []
            for instrument in midi_data.instruments:
                if not is_percussion_instrument(instrument):
                    for note in instrument.notes:
                        if start_time <= note.start < end_time or start_time <= note.end < end_time:
                            segment_notes.append(note)
            
            if segment_notes:
                # Calculate polyphony for this segment
                segment_time_points = set()
                for note in segment_notes:
                    segment_time_points.add(max(start_time, note.start))
                    segment_time_points.add(min(end_time, note.end))
                segment_time_points = sorted(list(segment_time_points))
                
                if len(segment_time_points) > 1:
                    # Calculate segment polyphony
                    segment_polyphony = []
                    for time_point in segment_time_points:
                        active_notes = 0
                        for note in segment_notes:
                            if note.start <= time_point < note.end:
                                active_notes += 1
                        segment_polyphony.append(active_notes)
                    
                    if segment_polyphony:
                        segment_max = max(segment_polyphony)
                        segment_avg = np.mean(segment_polyphony)
                        segment_std = np.std(segment_polyphony)
                        segment_density = sum(1 for p in segment_polyphony if p > 1) / len(segment_polyphony)
                        
                        segment_metrics.append({
                            'max': segment_max,
                            'avg': segment_avg,
                            'std': segment_std,
                            'density': segment_density
                        })
        
        # Calculate segment statistics
        if segment_metrics:
            max_means = [s['max'] for s in segment_metrics]
            avg_means = [s['avg'] for s in segment_metrics]
            density_means = [s['density'] for s in segment_metrics]
            
            mean_max = np.mean(max_means)
            std_max = np.std(max_means) if len(max_means) > 1 else 0
            mean_avg = np.mean(avg_means)
            std_avg = np.std(avg_means) if len(avg_means) > 1 else 0
            mean_density = np.mean(density_means)
            std_density = np.std(density_means) if len(density_means) > 1 else 0
        else:
            mean_max = std_max = mean_avg = std_avg = mean_density = std_density = 0
        
        return {
            # Global piece metrics (time-weighted)
            'max_poly': max_poly,
            'avg_poly': avg_poly,
            'poly_density': density_poly,
            'poly_std': std_poly,
            
            # Segment-based metrics (variation across sections)
            'mean_max_polyphony_measures': mean_max,
            'std_max_polyphony_measures': std_max,
            'mean_avg_polyphony_measures': mean_avg,
            'std_avg_polyphony_measures': std_avg,
            'mean_polyphony_density_measures': mean_density,
            'std_polyphony_density_measures': std_density
        }
    else:
        # Fallback to original implementation for segments
        return {
            'max_poly': 0,
            'avg_poly': 0,
            'poly_density': 0,
            'poly_std': 0,
            'mean_max_polyphony_measures': 0,
            'std_max_polyphony_measures': 0,
            'mean_avg_polyphony_measures': 0,
            'std_avg_polyphony_measures': 0,
            'mean_polyphony_density_measures': 0,
            'std_polyphony_density_measures': 0
        }

def main(midi_file_path):
    """Analyze a single MIDI file with improved polyphony calculation"""
    
    if not os.path.exists(midi_file_path):
        print(f"Error: File {midi_file_path} does not exist")
        return None
    
    try:
        # Load MIDI file
        midi_data = pretty_midi.PrettyMIDI(midi_file_path)
        
        # Calculate polyphony using improved event-based approach
        max_poly, avg_poly, std_poly, density_poly = calculate_polyphony_event_based(midi_data)
        
        # Get file info
        total_duration = midi_data.get_end_time()
        estimated_measures = int(total_duration / 2)
        
        print(f"🎵 IMPROVED POLYPHONY ANALYSIS")
        print(f"📁 File: {os.path.basename(midi_file_path)}")
        print(f"⏱️  Duration: {total_duration:.2f} seconds")
        print(f"📊 Estimated measures: {estimated_measures}")
        print("="*50)
        
        print(f"🎹 Max polyphony: {max_poly}")
        print(f"📊 Average polyphony: {avg_poly:.3f}")
        print(f"📈 Standard deviation: {std_poly:.3f}")
        print(f"🎯 Polyphony density: {density_poly:.3f}")
        
        # Calculate segmentation metrics
        from music21 import converter
        midi_stream = converter.parse(midi_file_path)
        midi_stream._original_file_path = midi_file_path
        
        segment_results = calculate_polyphony_by_measures_improved(midi_stream, estimated_measures)
        
        print(f"\n📊 SEGMENTATION RESULTS:")
        print(f"   Mean max polyphony across segments: {segment_results['mean_max_polyphony_measures']:.3f}")
        print(f"   Std dev of max polyphony: {segment_results['std_max_polyphony_measures']:.3f}")
        print(f"   Mean avg polyphony across segments: {segment_results['mean_avg_polyphony_measures']:.3f}")
        print(f"   Std dev of avg polyphony: {segment_results['std_avg_polyphony_measures']:.3f}")
        print(f"   Mean polyphony density: {segment_results['mean_polyphony_density_measures']:.3f}")
        print(f"   Std dev of polyphony density: {segment_results['std_polyphony_density_measures']:.3f}")
        
        return {
            'max_polyphony': max_poly,
            'avg_polyphony': avg_poly,
            'std_polyphony': std_poly,
            'polyphony_density': density_poly,
            'segmentation_results': segment_results
        }
        
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("Usage: python polyphony_improved.py <midi_file>") 