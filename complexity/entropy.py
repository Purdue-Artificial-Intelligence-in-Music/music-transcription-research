import math
import os
import statistics
import argparse
from fractions import Fraction
from music21 import midi, note, chord, converter
from music21.exceptions21 import StreamException
from .shared_preprocessor import (
    preprocess_midi, open_midi, extract_notes, extract_notes_melody, extract_ioi,
    calculate_entropy_optimized, calculate_pitch_interval_entropy_optimized,
    segment_analysis, analyze_tonal_certainty, analyze_pitch_class_entropy,
    analyze_melodic_interval_entropy, analyze_ioi_entropy
)


# Note: open_midi, extract_notes, extract_notes_melody, and extract_ioi functions
# are now imported from shared_preprocessor to avoid code duplication


def ioi_entropy(eo):
    """Calculate IOI entropy using optimized counting."""
    entropy_contributions = calculate_entropy_optimized(eo)
    return entropy_contributions


def pitch_entropy(en):
    """Calculate pitch entropy using optimized counting."""
    entropy_contributions = calculate_entropy_optimized(en)
    return entropy_contributions


def pitch_interval_entropy(en):
    """Calculate pitch interval entropy using optimized processing."""
    entropy_contributions = calculate_pitch_interval_entropy_optimized(en)
    return entropy_contributions


def main(midi_file_path):
    """Analyze a single MIDI file and return complexity metrics"""

    if not os.path.exists(midi_file_path):
        print(f"Error: File {midi_file_path} does not exist")
        return None

    try:
        # Use preprocessor to load MIDI file and extract common data
        preprocessed_data = preprocess_midi(midi_file_path)
        if not preprocessed_data:
            print(f"Error: Could not preprocess file {midi_file_path}")
            return None
        
        midi_stream = preprocessed_data['midi_stream']
        measures_count = preprocessed_data['file_info']['measures_count']
        tonal_certainty = preprocessed_data['tonal_certainty']

        print(f"Analyzing: {os.path.basename(midi_file_path)}")
        print(f"Number of measures: {measures_count}")
        print("=" * 50)

        # Get the tonal certainty for the whole piece (pre-calculated)
        k_piece = tonal_certainty

        # Get the mean tonal certainty for every 16 measures
        k_piece_seg, mean_k_measures = segment_analysis(
            midi_stream, measures_count, analyze_tonal_certainty, 16
        )

        # Get the pitch class entropy for the whole piece
        # NOTE: This combines ALL notes from ALL tracks into one analysis
        Hpc_piece = analyze_pitch_class_entropy(midi_stream)

        # Get the mean pitch class entropy for every 16 measures
        # NOTE: This also combines all tracks when analyzing each segment
        Hpc_piece_seg, mean_Hpc_measures = segment_analysis(
            midi_stream, measures_count, analyze_pitch_class_entropy, 16
        )

        # Analyze each part/track separately for melodic and rhythmic complexity
        # NOTE: This approach analyzes each MIDI track individually, then takes the maximum
        # This identifies the most complex individual voice rather than averaging all parts
        midi_parts = preprocessed_data['midi_parts']

        Hpi_list_piece = []
        Hioi_list_piece = []

        # Calculate entropy for each individual track/part
        for midi_part in midi_parts:
            Hpi_list_piece.append(analyze_melodic_interval_entropy(midi_part))
            Hioi_list_piece.append(analyze_ioi_entropy(midi_part))

        # Take the maximum complexity across all tracks
        # This represents the most melodically/rhythmically complex individual part
        max_Hpi_piece = max(Hpi_list_piece) if Hpi_list_piece else 0
        max_Hioi_piece = max(Hioi_list_piece) if Hioi_list_piece else 0

        # Calculate mean entropy measures across parts for 16-measure segments
        # NOTE: Like above, this analyzes each track separately then takes the maximum
        # This gives you the complexity of the most complex part in each time segment
        all_mean_Hpi_measures = []
        all_mean_Hioi_measures = []

        for midi_part in midi_parts:
            # Analyze melodic interval entropy for segments
            Hpi_piece_seg, mean_Hpi_measures = segment_analysis(
                midi_part, measures_count, analyze_melodic_interval_entropy, 16
            )
            all_mean_Hpi_measures.append(mean_Hpi_measures)

            # Analyze IOI entropy for segments
            Hioi_piece_seg, mean_Hioi_measures = segment_analysis(
                midi_part, measures_count, analyze_ioi_entropy, 16
            )
            all_mean_Hioi_measures.append(mean_Hioi_measures)

        # Again, take the maximum complexity across all tracks for the segmented analysis
        max_mean_Hpi_measures = (
            max(all_mean_Hpi_measures) if all_mean_Hpi_measures else 0
        )
        max_mean_Hioi_measures = (
            max(all_mean_Hioi_measures) if all_mean_Hioi_measures else 0
        )

        # Print results
        print("COMPLEXITY ANALYSIS RESULTS:")
        print("-" * 30)
        # Range 0-1: Higher = more traditionally tonal, Lower = more chromatic/atonal
        print(f"Tonal Certainty (whole piece): {k_piece:.4f}")
        print(f"Mean Tonal Certainty (16-measure segments): {mean_k_measures:.4f}")

        # Range ~0-3.58: Higher = more varied note selection, Lower = more repetitive
        # NOTE: Combines all tracks - reflects overall harmonic complexity
        print(f"Pitch Class Entropy (whole piece): {Hpc_piece:.4f}")
        print(
            f"Mean Pitch Class Entropy (16-measure segments): {mean_Hpc_measures:.4f}"
        )

        # Range varies: Higher = more unpredictable melodic jumps, Lower = more stepwise
        # NOTE: Shows the MOST complex individual track, not average of all tracks
        print(f"Max Melodic Interval Entropy (whole piece): {max_Hpi_piece:.4f}")
        print(
            f"Max Mean Melodic Interval Entropy (16-measure segments): {max_mean_Hpi_measures:.4f}"
        )

        # Range varies: Higher = more rhythmic variety, Lower = more regular timing
        # NOTE: Shows the MOST rhythmically complex individual track, not average
        print(f"Max IOI Entropy (whole piece): {max_Hioi_piece:.4f}")
        print(
            f"Max Mean IOI Entropy (16-measure segments): {max_mean_Hioi_measures:.4f}"
        )

        # Quick interpretation guide
        print("\n" + "=" * 50)
        print("INTERPRETATION GUIDE:")
        print(
            f"- Tonal Certainty: {'High' if k_piece > 0.7 else 'Medium' if k_piece > 0.4 else 'Low'} - {'Traditional harmony' if k_piece > 0.7 else 'Some chromaticism' if k_piece > 0.4 else 'Atonal/chromatic'}"
        )
        print(
            f"- Pitch Complexity: {'High' if Hpc_piece > 2.5 else 'Medium' if Hpc_piece > 1.5 else 'Low'} - {'Varied note selection' if Hpc_piece > 2.5 else 'Moderate variety' if Hpc_piece > 1.5 else 'Repetitive notes'}"
        )
        print(
            f"- Melodic Complexity: {'High' if max_Hpi_piece > 2.0 else 'Medium' if max_Hpi_piece > 1.0 else 'Low'} - {'Unpredictable jumps' if max_Hpi_piece > 2.0 else 'Mixed intervals' if max_Hpi_piece > 1.0 else 'Mostly stepwise'}"
        )
        print(
            f"- Rhythmic Complexity: {'High' if max_Hioi_piece > 1.0 else 'Medium' if max_Hioi_piece > 0.5 else 'Low'} - {'Complex rhythms' if max_Hioi_piece > 1.0 else 'Some variation' if max_Hioi_piece > 0.5 else 'Regular timing'}"
        )
        print(
            "\nNOTE: Melodic and Rhythmic values show the most complex individual track, while Pitch Class Entropy combines all tracks together."
        )

        return {
            "tonal_certainty_piece": k_piece,
            "mean_tonal_certainty_measures": mean_k_measures,
            "pitch_class_entropy_piece": Hpc_piece,
            "mean_pitch_class_entropy_measures": mean_Hpc_measures,
            "max_melodic_interval_entropy_piece": max_Hpi_piece,
            "max_mean_melodic_interval_entropy_measures": max_mean_Hpi_measures,
            "max_ioi_entropy_piece": max_Hioi_piece,
            "max_mean_ioi_entropy_measures": max_mean_Hioi_measures,
        }

    except StreamException as e:
        print(f"StreamException: {e}")
        return None
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return None





# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze MIDI files for entropy complexity metrics"
    )
    parser.add_argument(
        "-i",
        "--midi_file",
        type=str,
        help="Path to the MIDI file to analyze",
    )
    args = parser.parse_args()

    main(args.midi_file)
