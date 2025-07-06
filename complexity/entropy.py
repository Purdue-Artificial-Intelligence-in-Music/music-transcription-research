import lzma
import math
import os
import sys
import csv
import statistics
from fractions import Fraction
from music21 import midi, note, chord, pitch, abcFormat, stream, converter, key
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

