#!/usr/bin/env python3

from mido import MidiFile

def analyze_midi_file(midi_path):
    mid = MidiFile(midi_path)
    print(f"File: {midi_path}")
    print(f"Tracks: {len(mid.tracks)}")
    print(f"Ticks per beat: {mid.ticks_per_beat}")
    print(f"Length (seconds): {mid.length}")
    
    note_on = 0
    note_off = 0
    other = 0
    notes_seen = set()
    
    for i, track in enumerate(mid.tracks):
        print(f"\nTrack {i}: {len(track)} messages")
        for msg in track:
            if msg.type == 'note_on':
                note_on += 1
                if msg.velocity > 0:
                    notes_seen.add(msg.note)
            elif msg.type == 'note_off':
                note_off += 1
            else:
                other += 1
                if msg.type == 'set_tempo':
                    print(f"  Tempo: {msg.tempo}")
    
    print(f"\nSummary:")
    print(f"Note On: {note_on}")
    print(f"Note Off: {note_off}")
    print(f"Other: {other}")
    print(f"Unique notes: {len(notes_seen)}")
    print(f"Note range: {min(notes_seen) if notes_seen else 'N/A'} - {max(notes_seen) if notes_seen else 'N/A'}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analyze_midi_file(sys.argv[1])
    else:
        analyze_midi_file('/depot/yunglu/data/transcription/BiMMuDa/1954/3/1954_03_full.mid') 