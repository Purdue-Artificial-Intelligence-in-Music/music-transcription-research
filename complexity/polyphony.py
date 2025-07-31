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
        'max_polyphony': max_polyphony,
        'avg_polyphony': avg_polyphony,
        'polyphony_density': polyphony_density,
        'polyphony_std': polyphony_std
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
    else:
        polyphony_series = calculate_polyphony_series(midi_stream)
    
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
    
    # Segment analysis following entropy algorithm pattern
    first_measure = 1
    last_measure = min(16, measures_count)  # Handle short pieces
    max_polyphony_measures = []
    avg_polyphony_measures = []
    polyphony_density_measures = []
    
    while first_measure <= measures_count:
        try:
            # Extract segment
            segment_stream = midi_stream.measures(first_measure, last_measure)
            
            # Calculate polyphony for this segment
            segment_polyphony = calculate_polyphony_series(segment_stream)
            
            if segment_polyphony:
                # Calculate metrics for this segment
                segment_metrics = calculate_polyphony_metrics(segment_polyphony)
                
                max_polyphony_measures.append(segment_metrics['max_polyphony'])
                avg_polyphony_measures.append(segment_metrics['avg_polyphony'])
                polyphony_density_measures.append(segment_metrics['polyphony_density'])
            
            # Move to next segment
            first_measure = last_measure + 1
            last_measure = min(first_measure + 15, measures_count)  # 16-measure segments
            
        except Exception as e:
            print(f"Error processing measures {first_measure}-{last_measure}: {e}")
            first_measure = last_measure + 1
            last_measure = min(first_measure + 15, measures_count)
    
    # Calculate overall piece metrics
    piece_metrics = calculate_polyphony_metrics(polyphony_series)
    
    # Calculate segment statistics
    mean_max = statistics.mean(max_polyphony_measures) if max_polyphony_measures else 0
    std_max = statistics.stdev(max_polyphony_measures) if len(max_polyphony_measures) > 1 else 0
    
    mean_avg = statistics.mean(avg_polyphony_measures) if avg_polyphony_measures else 0
    std_avg = statistics.stdev(avg_polyphony_measures) if len(avg_polyphony_measures) > 1 else 0
    
    mean_density = statistics.mean(polyphony_density_measures) if polyphony_density_measures else 0
    std_density = statistics.stdev(polyphony_density_measures) if len(polyphony_density_measures) > 1 else 0
    
    return {
        'max_polyphony_piece': piece_metrics['max_polyphony'],
        'mean_max_polyphony_measures': mean_max,
        'std_max_polyphony_measures': std_max,
        'mean_avg_polyphony_measures': mean_avg,
        'std_avg_polyphony_measures': std_avg,
        'mean_polyphony_density_measures': mean_density,
        'std_polyphony_density_measures': std_density
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
        
        # Calculate polyphony metrics
        polyphony_results = calculate_polyphony_by_measures(
            midi_stream, measures_count, preprocessed_data
        )
        
        # Print results
        print("POLYPHONY ANALYSIS RESULTS:")
        print(f"Maximum Polyphony: {polyphony_results['max_polyphony_piece']:.1f}")
        print(f"Average Polyphony: {polyphony_results['mean_avg_polyphony_measures']:.2f} ± {polyphony_results['std_avg_polyphony_measures']:.2f}")
        print(f"Polyphony Density: {polyphony_results['mean_polyphony_density_measures']:.3f} ± {polyphony_results['std_polyphony_density_measures']:.3f}")
        print(f"Max Polyphony (segments): {polyphony_results['mean_max_polyphony_measures']:.1f} ± {polyphony_results['std_max_polyphony_measures']:.1f}")
        
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