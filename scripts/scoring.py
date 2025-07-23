#!/opt/homebrew/bin/python3
"""
Name: scoring.py
Purpose: To compare 2 .mid files to score the transcribed output compared to the original sheet music
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import pretty_midi
import numpy as np
import argparse
import mir_eval


def extract_intervals_and_pitches(midi_file):
    """
    Extracts start_time, end_time, and pitch frequency for each note in a MIDI file.
    Returns NumPy arrays suitable for mir_eval.
    """
    midi_data = pretty_midi.PrettyMIDI(midi_file)
    intervals = []
    pitches = []

    for instrument in midi_data.instruments:
        for note in instrument.notes:
            intervals.append([note.start, note.end])
            pitches.append(pretty_midi.note_number_to_hz(note.pitch))

    if not intervals:
        return np.empty((0, 2)), np.array([])

    # Sort by start time
    intervals, pitches = zip(*sorted(zip(intervals, pitches), key=lambda x: x[0][0]))

    return np.array(intervals), np.array(pitches)


def count_instruments(midi_file):
    """
    Counts the number of instruments in a MIDI file.
    """
    midi_data = pretty_midi.PrettyMIDI(midi_file)
    return len(midi_data.instruments)


def main():
    parser = argparse.ArgumentParser(
        description="Score a transcription against a reference MIDI file."
    )
    parser.add_argument(
        "--reference", required=True, help="Path to the reference MIDI file"
    )
    parser.add_argument(
        "--transcription", required=True, help="Path to the transcription MIDI file"
    )
    args = parser.parse_args()

    ref_intervals, ref_pitches = extract_intervals_and_pitches(args.reference)
    est_intervals, est_pitches = extract_intervals_and_pitches(args.transcription)

    # Evaluate the transcription
    scores = mir_eval.transcription.evaluate(
        ref_intervals, ref_pitches, est_intervals, est_pitches
    )

    # Count the number of instruments in both MIDI files
    ref_instruments = count_instruments(args.reference)
    est_instruments = count_instruments(args.transcription)

    print(f"Reference MIDI Instruments: {ref_instruments}")
    print(f"Transcription MIDI Instruments: {est_instruments}")

    for key, value in scores.items():
        print(f"{key}: {value:.6f}")


if __name__ == "__main__":
    main()
