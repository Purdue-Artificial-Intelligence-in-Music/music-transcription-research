import math
import os
import statistics
import argparse
from fractions import Fraction
from music21 import midi, note, chord, converter
from music21.exceptions21 import StreamException
from .shared_preprocessor import (
    preprocess_midi, open_midi, extract_notes, 
    extract_notes_melody, extract_ioi, calculate_polyphony_series
)


def calculate_polyphony_metrics(polyphony_series):
    """
    Calculate polyphony metrics using statistical measures.
    
    These metrics are based on established research that treats polyphony
    as a property affecting transcription difficulty.
    
    Args:
        polyphony_series: List of simultaneous note counts
        
    Returns:
        Dictionary with polyphony metrics
    """
    if not polyphony_series:
        return {
            'max_polyphony': 0,
            'avg_polyphony': 0,
            'polyphony_density': 0,
            'polyphony_std': 0
        }
    
    # Metrics used in AMT research papers
    max_polyphony = max(polyphony_series)
    avg_polyphony = statistics.mean(polyphony_series)
    
    # Polyphony density: percentage of time with >1 simultaneous notes
    polyphonic_moments = sum(1 for p in polyphony_series if p > 1)
    polyphony_density = polyphonic_moments / len(polyphony_series) if polyphony_series else 0
    
    # Standard deviation for variation measure
    polyphony_std = statistics.stdev(polyphony_series) if len(polyphony_series) > 1 else 0
    
    return {
        'global_max_polyphony': max_polyphony,
        'global_avg_polyphony': avg_polyphony,
        'global_polyphony_density': polyphony_density,
        'global_polyphony_variation': polyphony_std
    }


def calculate_polyphony_by_measures(midi_stream, measures_count, preprocessed_data=None):
    """
    Calculate polyphony metrics for 16-measure segments.
    
    Following the entropy algorithm's segmentation approach for
    consistent analysis across different complexity metrics.
    
    Args:
        midi_stream: Music21 stream object
        measures_count: Total number of measures in the piece
        preprocessed_data: Optional preprocessed data
        
    Returns:
        Dictionary with segment-based polyphony metrics
    """
    if preprocessed_data and 'polyphony_series' in preprocessed_data:
        polyphony_series = preprocessed_data['polyphony_series']
        time_points = preprocessed_data.get('time_points', [])
    else:
        time_points, polyphony_series = calculate_polyphony_series(midi_stream)
    
    if not polyphony_series:
        return {
            'max_polyphony_piece': 0,
            'mean_max_polyphony_measures': 0,
            'std_max_polyphony_measures': 0,
            'mean_avg_polyphony_measures': 0,
            'std_avg_polyphony_measures': 0,
            'mean_polyphony_density_measures': 0,
            'std_polyphony_density_measures': 0
        }
    
    # Adaptive segment size: use smaller segments for short pieces  
    if measures_count < 16:
        segment_size = max(4, measures_count // 2) if measures_count >= 8 else measures_count
        print(f"Short piece ({measures_count} measures): using {segment_size}-measure segments")
    else:
        segment_size = 16
    
    # Segment analysis following entropy algorithm pattern
    first_measure = 1
    last_measure = min(segment_size, measures_count)  # Handle short pieces
    max_polyphony_measures = []
    avg_polyphony_measures = []
    polyphony_density_measures = []
    
    while first_measure <= measures_count:
        try:
            # Extract segment
            segment_stream = midi_stream.measures(first_measure, last_measure)
            
            # Calculate polyphony for this segment
            segment_time_points, segment_polyphony = calculate_polyphony_series(segment_stream)
            
            if segment_polyphony:
                # Calculate metrics for this segment
                segment_metrics = calculate_polyphony_metrics(segment_polyphony)
                
                max_polyphony_measures.append(segment_metrics['global_max_polyphony'])
                avg_polyphony_measures.append(segment_metrics['global_avg_polyphony'])
                polyphony_density_measures.append(segment_metrics['global_polyphony_density'])
            
            # Move to next segment
            first_measure = last_measure + 1
            last_measure = min(first_measure + segment_size - 1, measures_count)
            
        except Exception as e:
            print(f"Error processing measures {first_measure}-{last_measure}: {e}")
            first_measure = last_measure + 1
            last_measure = min(first_measure + segment_size - 1, measures_count)
    
    # Calculate overall piece metrics using time-based calculation
    from complexity.shared_preprocessor import calculate_time_based_polyphony_metrics
    piece_time_metrics = calculate_time_based_polyphony_metrics(polyphony_series, time_points)
    
    # Also calculate event-based for max polyphony (this doesn't change with time weighting)
    piece_metrics = calculate_polyphony_metrics(polyphony_series)
    
    # Calculate segment statistics
    mean_max = statistics.mean(max_polyphony_measures) if max_polyphony_measures else 0
    std_max = statistics.stdev(max_polyphony_measures) if len(max_polyphony_measures) > 1 else 0
    
    mean_avg = statistics.mean(avg_polyphony_measures) if avg_polyphony_measures else 0
    std_avg = statistics.stdev(avg_polyphony_measures) if len(avg_polyphony_measures) > 1 else 0
    
    mean_density = statistics.mean(polyphony_density_measures) if polyphony_density_measures else 0
    std_density = statistics.stdev(polyphony_density_measures) if len(polyphony_density_measures) > 1 else 0
    
    # Debug info for short pieces
    if measures_count < 16:
        print(f"DEBUG: {len(max_polyphony_measures)} segments created, max_values: {max_polyphony_measures}")
    
    return {
        # Global piece metrics (time-weighted)
        'max_poly': piece_metrics['global_max_polyphony'],
        'avg_poly': piece_time_metrics['avg_polyphony'],
        'poly_density': piece_time_metrics['polyphonic_ratio'],
        'poly_std': piece_time_metrics.get('polyphony_std', 0),
        
        # Segment-based metrics (variation across sections)
        'seg_max_poly': mean_max,
        'seg_max_std': std_max,
        'seg_avg_poly': mean_avg,
        'seg_avg_std': std_avg,
        'seg_density': mean_density,
        'seg_density_std': std_density
    }


def main(midi_file_path):
    """
    Main function to analyze polyphony complexity of a MIDI file.
    
    Args:
        midi_file_path: Path to the MIDI file
        
    Returns:
        Dictionary with polyphony analysis results
    """
    if not midi_file_path or not os.path.exists(midi_file_path):
        print(f"Error: File {midi_file_path} not found.")
        return None
    
    try:
        # Preprocess MIDI file
        preprocessed_data = preprocess_midi(midi_file_path)
        if not preprocessed_data:
            print(f"Error: Could not preprocess {midi_file_path}")
            return None
        
        midi_stream = open_midi(midi_file_path)
        measures_count = preprocessed_data['file_info']['measures_count']
        
        # Calculate polyphony metrics using preprocessed data
        polyphony_results = calculate_polyphony_by_measures(
            midi_stream, measures_count, preprocessed_data
        )
        
        # Print results with clean naming
        print("POLYPHONY ANALYSIS RESULTS:")
        print(f"Max Polyphony: {polyphony_results['max_poly']:.1f}")
        print(f"Avg Polyphony: {polyphony_results['avg_poly']:.2f} (time-weighted)")
        print(f"Polyphonic Density: {polyphony_results['poly_density']:.3f}")
        print(f"Segment Analysis: max={polyphony_results['seg_max_poly']:.1f}±{polyphony_results['seg_max_std']:.1f}, avg={polyphony_results['seg_avg_poly']:.2f}±{polyphony_results['seg_avg_std']:.2f}")
        
        return polyphony_results
        
    except StreamException as e:
        print(f"StreamException: {e}")
        return None
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze polyphony complexity of MIDI files")
    parser.add_argument("-i", "--midi_file", type=str, required=True, help="Path to MIDI file")
    
    args = parser.parse_args()
    main(args.midi_file) 