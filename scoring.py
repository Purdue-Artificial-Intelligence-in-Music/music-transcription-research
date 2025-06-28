#!/opt/homebrew/bin/python3
"""
Name: scoring.py
Purpose: To compare 2 .mid files to score the transcribed output compared to the original sheet music
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"

import pretty_midi
import os
import argparse
import mir_eval


def midi_to_txt(midi_file, txt_file):
    """
    Converts a MIDI file to a three-column .txt file: start_time, end_time, frequency.
    """
    midi_data = pretty_midi.PrettyMIDI(midi_file)
    notes_data = []
    for instrument in midi_data.instruments:
        for note in instrument.notes:
            start_time = note.start
            end_time = note.end
            pitch_freq = pretty_midi.note_number_to_hz(note.pitch)
            notes_data.append((start_time, end_time, pitch_freq))
    notes_data.sort(key=lambda x: x[0])
    with open(txt_file, "w") as f:
        for note in notes_data:
            f.write(f"{note[0]}\t{note[1]}\t{note[2]}\n")


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

    reference_midi = args.reference
    transcription_midi = args.transcription
    reference_txt = "reference.txt"
    transcription_txt = "transcription.txt"

    # Convert both MIDI files to .txt
    midi_to_txt(reference_midi, reference_txt)
    midi_to_txt(transcription_midi, transcription_txt)

    # Load the valued intervals from the .txt files
    ref_intervals, ref_pitches = mir_eval.io.load_valued_intervals(reference_txt)
    est_intervals, est_pitches = mir_eval.io.load_valued_intervals(transcription_txt)

    # Evaluate the transcription
    scores = mir_eval.transcription.evaluate(
        ref_intervals, ref_pitches, est_intervals, est_pitches
    )
    for key, value in scores.items():
        print(f"{key}: {value:.6f}")

    # Delete the intermediate .txt files
    os.remove(reference_txt)
    os.remove(transcription_txt)


if __name__ == "__main__":
    main()
