import math
import os
import statistics
import argparse
from fractions import Fraction
from music21 import midi, note, chord, converter
from music21.exceptions21 import StreamException


def open_midi(midi_path):
    mf = midi.MidiFile()
    mf.open(midi_path)
    mf.read()
    mf.close()

    return midi.translate.midiFileToStream(mf)


def extract_notes(midi_stream):
    result = []
    for current_note in midi_stream.flatten().notes:
        if isinstance(current_note, note.Note):
            result.append(max(0.0, current_note.pitch.pitchClass))
        elif isinstance(current_note, chord.Chord):
            for pitch in current_note.pitches:
                result.append(max(0.0, pitch.pitchClass))
    return result


def extract_notes_melody(midi_stream):
    notes = midi_stream.flatten().notes
    off_set = []
    m_notes = []
    highest_notes = []

    for i in range(0, len(notes)):
        if notes[i].offset in off_set:
            continue

        if isinstance(notes[i], chord.Chord):
            chord_pitches = notes[i].pitches
            p = []
            for x in chord_pitches:
                p.append(x.ps)
            m_note = max(p)

        else:
            m_note = notes[i].pitch.ps

        try:
            for y in range(1, 5):
                if notes[i + y].offset == notes[i].offset:
                    if isinstance(notes[i + y], chord.Chord):
                        chord_pitches = notes[i + y].pitches
                        p = []
                        for x in chord_pitches:
                            p.append(x.ps)
                        sec_max = max(p)
                    else:
                        sec_max = notes[i + y].pitch.ps
                    m_note = m_note if (m_note > sec_max) else sec_max
        except IndexError:
            pass

        off_set.append(notes[i].offset)
        m_notes.append(m_note)

    for i in m_notes:
        highest_notes.append(max(0, int(i)))

    return highest_notes


def extract_ioi(midi_stream):
    ioi_list = []
    off_set = []
    notes = midi_stream.flatten().notes

    for i in range(0, len(notes)):
        if notes[i].offset not in off_set:
            m_note = notes[i]
            off_set.append(m_note.offset)

    for i in range(1, len(off_set)):
        ioi = Fraction(off_set[i] - off_set[i - 1]).limit_denominator(4)
        ioi_list.append(ioi)

    return ioi_list


def ioi_entropy(eo):
    result = []
    duration_list = []

    for i in eo:
        if i not in duration_list:
            duration_list.append(i)

    for i in duration_list:
        p = eo.count(i) / len(eo)
        entr = p * (math.log2(p))
        result.append(entr)

    return result


def pitch_entropy(en):
    result = []
    note_list = []

    for cn in en:
        if cn not in note_list:
            note_list.append(cn)

    for cn in note_list:
        p = en.count(cn) / len(en)
        entr = p * (math.log2(p))
        result.append(entr)

    return result


def pitch_interval_entropy(en):
    interval_list = []
    interval_seq = []
    result = []

    for i in range(1, len(en)):
        interval = en[i] - en[i - 1]
        # ignore intervals > 12 notes
        if abs(interval) <= 12:
            if interval not in interval_list:
                interval_list.append(interval)
            interval_seq.append(interval)

    for i in interval_list:
        p = interval_seq.count(i) / len(interval_seq)
        entr = p * (math.log2(p))
        result.append(entr)

    return result


def main(midi_file_path):
    """Analyze a single MIDI file and return complexity metrics"""

    if not os.path.exists(midi_file_path):
        print(f"Error: File {midi_file_path} does not exist")
        return None

    try:
        # Load and quantize the MIDI file
        midi_stream = converter.parse(midi_file_path).quantize()
        measures_count = len(midi_stream.measures(0, None)[0])

        print(f"Analyzing: {os.path.basename(midi_file_path)}")
        print(f"Number of measures: {measures_count}")
        print("=" * 50)

        # Get the tonal certainty for the whole piece
        k_piece = midi_stream.analyze("key").tonalCertainty()

        # Get the mean tonal certainty for every 16 measures
        first_measure = 0
        last_measure = 16
        k_list_measures = []

        if last_measure > measures_count:
            mean_k_measures = k_piece
        else:
            while last_measure <= measures_count:
                k_list_measures.append(
                    midi_stream.measures(first_measure, last_measure)
                    .analyze("key")
                    .tonalCertainty()
                )
                first_measure = last_measure
                last_measure += last_measure
            mean_k_measures = statistics.mean(k_list_measures)

        # Get the pitch class entropy for the whole piece
        # NOTE: This combines ALL notes from ALL tracks into one analysis
        Hpc_piece = 0 - sum(pitch_entropy(extract_notes(midi_stream)))

        # Get the mean pitch class entropy for every 16 measures
        # NOTE: This also combines all tracks when analyzing each segment
        first_measure = 0
        last_measure = 16
        Hpc_list_measures = []

        if last_measure > measures_count:
            mean_Hpc_measures = Hpc_piece
        else:
            while last_measure <= measures_count:
                Hpc_list_measures.append(
                    0
                    - sum(
                        pitch_entropy(
                            extract_notes(
                                midi_stream.measures(first_measure, last_measure)
                            )
                        )
                    )
                )
                first_measure = last_measure
                last_measure += last_measure
            mean_Hpc_measures = statistics.mean(Hpc_list_measures)

        # Analyze each part/track separately for melodic and rhythmic complexity
        # NOTE: This approach analyzes each MIDI track individually, then takes the maximum
        # This identifies the most complex individual voice rather than averaging all parts
        midi_parts = midi_stream.parts.stream()

        Hpi_list_piece = []
        Hioi_list_piece = []

        # Calculate entropy for each individual track/part
        for midi_part in midi_parts:
            Hpi_list_piece.append(
                0 - sum(pitch_interval_entropy(extract_notes_melody(midi_part)))
            )
            Hioi_list_piece.append(0 - sum(ioi_entropy(extract_ioi(midi_part))))

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
            first_measure = 0
            last_measure = 16

            Hpi_list_measures = []
            if last_measure > measures_count:
                mean_Hpi_measures = max_Hpi_piece
            else:
                while last_measure <= measures_count:
                    Hpi_list_measures.append(
                        0
                        - sum(
                            pitch_interval_entropy(
                                extract_notes_melody(
                                    midi_part.measures(first_measure, last_measure)
                                )
                            )
                        )
                    )
                    first_measure = last_measure
                    last_measure += last_measure
                mean_Hpi_measures = (
                    statistics.mean(Hpi_list_measures) if Hpi_list_measures else 0
                )

            first_measure = 0
            last_measure = 16

            Hioi_list_measures = []
            if last_measure > measures_count:
                mean_Hioi_measures = max_Hioi_piece
            else:
                while last_measure <= measures_count:
                    Hioi_list_measures.append(
                        0
                        - sum(
                            ioi_entropy(
                                extract_ioi(
                                    midi_part.measures(first_measure, last_measure)
                                )
                            )
                        )
                    )
                    first_measure = last_measure
                    last_measure += last_measure
                mean_Hioi_measures = (
                    statistics.mean(Hioi_list_measures) if Hioi_list_measures else 0
                )

            all_mean_Hpi_measures.append(mean_Hpi_measures)
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
