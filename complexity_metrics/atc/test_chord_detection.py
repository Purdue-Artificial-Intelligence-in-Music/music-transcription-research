#!/usr/bin/env python3

from mido import MidiFile

def test_chord_detection(midi_path):
    mid = MidiFile(midi_path)
    notes_on = set()
    chord_events = []
    
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on':
                if msg.velocity > 0:
                    notes_on.add(msg.note % 12)
                else:
                    notes_on.discard(msg.note % 12)
                
                if len(notes_on) >= 2:
                    chord_events.append(sorted(notes_on.copy()))
    
    print(f"Total chord events: {len(chord_events)}")
    if chord_events:
        print(f"Sample chord events: {chord_events[:10]}")
    else:
        print("No chord events found!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_chord_detection(sys.argv[1])
    else:
        test_chord_detection('/depot/yunglu/data/transcription/BiMMuDa/1954/3/1954_03_full.mid') 