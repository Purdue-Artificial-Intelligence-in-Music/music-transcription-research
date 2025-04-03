#!/opt/homebrew/bin/python3
"""
Name: scoring.py
Purpose: To compare 2 .mid files to score the transcribed output compared to the original sheet music
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import argparse
import mir_eval  # TODO: Need to update to the improved version of mir_eval.transcription
import pretty_midi
import numpy as np
import yaml


def extract_notes_with_offset(midi_file) -> list:
    # Load the MIDI file
    midi_data = pretty_midi.PrettyMIDI(midi_file)

    # Extract instrument, onset, offset, and pitch
    note_events = []
    for instrument in midi_data.instruments:

        if instrument.is_drum == True:
            continue

        for note in instrument.notes:
            onset = note.start
            offset = note.end
            pitch = note.pitch

            note_events.append(
                (get_instrument_family(instrument.program), onset, offset, pitch)
            )
    # Sort by onset time
    note_events.sort(key=lambda x: x[1])

    return note_events


def get_instrument_family(program_number: int) -> str:
    # Load the instrument data
    with open("instrument_families.yaml", "r") as file:
        instrument_data = yaml.safe_load(file)

    for family, instruments in instrument_data["instrument_families"].items():
        if isinstance(instruments, dict) and program_number in instruments:
            return family

    return "Unknown"


def prepare_data_for_mir_eval(note_events) -> tuple:
    intervals = []
    families = []
    pitches = []
    for family, onset, offset, pitch in note_events:
        intervals.append([onset, offset])
        families.append(family)
        pitches.append(pitch)
    # Convert to NumPy arrays
    intervals = np.array(intervals)
    families = np.array(families)
    pitches = np.array(pitches)

    return intervals, families, pitches


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Compare two MIDI files for transcription accuracy."
    )
    parser.add_argument(
        "--reference", required=True, help="Path to the reference MIDI file"
    )
    parser.add_argument(
        "--transcription", required=True, help="Path to the transcribed MIDI file"
    )
    parser.add_argument("--output", required=False, help="Path to save the F1 score")
    args = parser.parse_args()

    # Extract and prepare notes from reference and transcribed MIDI files
    reference_notes = extract_notes_with_offset(args.reference)
    estimated_notes = extract_notes_with_offset(args.transcription)

    # Prepare intervals and pitches for both reference and estimated notes
    ref_intervals, ref_instrument_families, ref_pitches = prepare_data_for_mir_eval(
        reference_notes
    )
    est_intervals, est_instrument_families, est_pitches = prepare_data_for_mir_eval(
        estimated_notes
    )

    # Compare the transcriptions
    scores = mir_eval.transcription.evaluate(
        ref_intervals,
        ref_pitches,
        est_intervals,
        est_pitches,
        ref_instruments=ref_instrument_families,
        est_instruments=est_instrument_families,
    )

    # Optionally, save the F1 score to a file if an output path is provided
    if args.output:
        with open(args.output, "w") as file:
            for key, value in scores.items():
                file.write(f"{key}: {value}\n")
    else:
        # Print the results
        for key, value in scores.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
