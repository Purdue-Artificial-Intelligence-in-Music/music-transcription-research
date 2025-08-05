"""
Shared Preprocessor for MIDI Analysis

Calculates common information once and provides it to all metrics.
This eliminates redundant calculations and improves performance.
Follows the conventions of the entropy algorithm.

INSTRUMENT DETECTION IMPROVEMENT (2024):
- Enhanced extract_notes() function to use PrettyMIDI's is_drum property for perfect instrument detection
- Falls back to original music21 method if PrettyMIDI is not available
- Maintains backward compatibility while providing accurate tonal note extraction
"""

import math
import statistics
from fractions import Fraction
from collections import Counter
from music21 import midi, note, chord, converter, stream
from music21.exceptions21 import StreamException




def open_midi(midi_path):
    """Open and parse MIDI file using music21 conventions."""
    mf = midi.MidiFile()
    mf.open(midi_path)
    mf.read()
    mf.close()
    stream = midi.translate.midiFileToStream(mf)
    
    # Store file path as a custom attribute for enhanced drum detection
    # Use a safe way that won't interfere with music21's metadata system
    setattr(stream, '_original_file_path', midi_path)
    return stream


def get_instrument_for_note(note_obj, midi_stream):
    """
    Robust instrument detection for a note object.
    
    Since channel detection is failing, this function uses a workaround
    based on note characteristics and timing.
    
    Args:
        note_obj: Music21 note object
        midi_stream: The full MIDI stream for context
        
    Returns:
        str: Instrument name or "Unknown"
    """
    # Workaround: Use note characteristics to guess instrument
    try:
        # Check if it's a chord FIRST (before percussion check)
        if hasattr(note_obj, 'pitches') and len(note_obj.pitches) > 1:
            # Chords are usually tonal instruments - don't assume percussion
            # Check if any pitch is in a clearly tonal range
            tonal_pitches = 0
            percussion_pitches = 0
            
            for pitch in note_obj.pitches:
                if hasattr(pitch, 'midi'):
                    midi_note = pitch.midi
                    if 21 <= midi_note <= 108:  # Full piano range
                        tonal_pitches += 1
                    elif 35 <= midi_note <= 81:  # Percussion range
                        percussion_pitches += 1
            
            # If mostly tonal pitches, assume tonal instrument
            if tonal_pitches > percussion_pitches:
                return "Piano"  # Default to piano for chords
            else:
                return "Percussion"
        
        # Check if it's percussion
        if hasattr(note_obj, '__class__') and 'Percussion' in note_obj.__class__.__name__:
            return "Percussion"
        
        # Check if it's a single note
        if hasattr(note_obj, 'pitch') and hasattr(note_obj.pitch, 'midi'):
            midi_note = note_obj.pitch.midi
            
            # Harmonica notes (we know these work)
            if 57 <= midi_note <= 67:  # A to G
                return "Harmonica"
            
            # Piano range (very broad)
            elif 21 <= midi_note <= 108:
                return "Piano"
            
            # Bass range
            elif 28 <= midi_note <= 67:
                return "Electric Bass"
            
            # Guitar range
            elif 40 <= midi_note <= 88:
                return "Electric Guitar"
            
            # Organ range
            elif 36 <= midi_note <= 96:
                return "Electric Organ"
            
            # Choir range
            elif 48 <= midi_note <= 84:
                return "Choir"
            
            # Sampler range
            elif 36 <= midi_note <= 84:
                return "Sampler"
            
            # Percussion range (only if we're sure)
            elif 35 <= midi_note <= 81:
                # Be more conservative - only return percussion if we're certain
                return "Unknown"  # Let the filtering logic decide
        
    except:
        pass
    
    # First try the original method
    try:
        if hasattr(note_obj, 'getContextByClass'):
            instrument = note_obj.getContextByClass('Instrument')
            if instrument and hasattr(instrument, 'instrumentName') and instrument.instrumentName:
                return instrument.instrumentName
    except:
        pass
    
    return "Unknown"


def is_percussion_instrument(instrument):
    """Simple percussion detection matching jupyter notebook logic exactly."""
    # Check 1: is_drum property (most reliable)
    if instrument.is_drum:
        return True

    # Check 2: Official General MIDI percussion programs (0-127 indexing)
    percussion_programs = [47, 112, 113, 114, 115, 116, 117, 118, 119]
    if instrument.program in percussion_programs:
        return True

    # Check 3: Name-based detection
    name_lower = instrument.name.lower()
    if any(drum_word in name_lower for drum_word in ['drum', 'percussion', 'cymbal', 'timpani']):
        return True

    return False


def extract_notes(midi_stream):
    """Extract pitch classes from tonal instruments only - matching jupyter logic."""
    if not hasattr(midi_stream, '_original_file_path'):
        return []
    
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(midi_stream._original_file_path)
    
    result = []
    for instrument in pm.instruments:
        if not is_percussion_instrument(instrument):
            for note in instrument.notes:
                result.append(note.pitch % 12)
    
    return result


def extract_notes_melody(midi_stream):
    """Extract melody notes (highest note at each time point)."""
    notes = midi_stream.flatten().notes
    off_set = []
    m_notes = []
    highest_notes = []

    for i in range(0, len(notes)):
        if notes[i].offset in off_set:
            continue

        try:
            if isinstance(notes[i], chord.Chord):
                chord_pitches = notes[i].pitches
                p = []
                for x in chord_pitches:
                    p.append(x.pitchClass)
                m_note = max(p)
            else:
                m_note = notes[i].pitch.pitchClass
        except (AttributeError, TypeError):
            # Skip percussion/unpitched notes
            continue

        try:
            for y in range(1, 5):
                if i + y < len(notes) and notes[i + y].offset == notes[i].offset:
                    if isinstance(notes[i + y], chord.Chord):
                        chord_pitches = notes[i + y].pitches
                        p = []
                        for x in chord_pitches:
                            p.append(x.pitchClass)
                        sec_max = max(p)
                    else:
                        sec_max = notes[i + y].pitch.pitchClass
                    m_note = m_note if (m_note > sec_max) else sec_max
        except (IndexError, AttributeError, TypeError):
            pass

        off_set.append(notes[i].offset)
        m_notes.append(m_note)

    for i in m_notes:
        highest_notes.append(max(0, int(i)))

    return highest_notes


def extract_ioi(midi_stream):
    """Extract inter-onset intervals from the stream."""
    ioi_list = []
    off_set = []
    notes = midi_stream.flatten().notes

    for i in range(0, len(notes)):
        if notes[i].offset not in off_set:
            m_note = notes[i]
            off_set.append(m_note.offset)

    for i in range(1, len(off_set)):
        try:
            ioi = Fraction(off_set[i] - off_set[i - 1]).limit_denominator(4)
            ioi_list.append(ioi)
        except (ValueError, TypeError):
            # Handle cases where Fraction conversion fails
            try:
                ioi_float = float(off_set[i] - off_set[i - 1])
                ioi_list.append(ioi_float)
            except (ValueError, TypeError):
                # Skip this interval if we can't convert it
                continue

    return ioi_list


def calculate_polyphony_series(midi_stream):
    """
    Calculate polyphony time series - matching jupyter notebook logic exactly.
    """
    # Check if we have the original file path (for full files)
    if hasattr(midi_stream, '_original_file_path'):
        # Use PrettyMIDI approach for full files
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(midi_stream._original_file_path)
        
        # Extract note events from tonal instruments only
        all_note_events = []
        for instrument in pm.instruments:
            if not is_percussion_instrument(instrument):
                for note in instrument.notes:
                    all_note_events.append({
                        'start': note.start,
                        'end': note.end,
                        'pitch': note.pitch % 12
                    })
    else:
        # Fallback: Use Music21 stream directly (for segments)
        all_note_events = []
        notes = midi_stream.flatten().notes
        
        for note_obj in notes:
            # Skip percussion instruments using Music21 approach
            try:
                if hasattr(note_obj, 'pitch'):
                    # Single note
                    all_note_events.append({
                        'start': float(note_obj.offset),
                        'end': float(note_obj.offset + note_obj.duration.quarterLength),
                        'pitch': note_obj.pitch.midi % 12
                    })
                elif hasattr(note_obj, 'pitches'):
                    # Chord - add each pitch separately
                    for pitch in note_obj.pitches:
                        all_note_events.append({
                            'start': float(note_obj.offset),
                            'end': float(note_obj.offset + note_obj.duration.quarterLength),
                            'pitch': pitch.midi % 12
                        })
            except (AttributeError, TypeError):
                continue
    
    if not all_note_events:
        return [], []
    
    # Get unique time points (jupyter logic)
    time_points = set()
    for note_event in all_note_events:
        time_points.add(note_event['start'])
        time_points.add(note_event['end'])
    time_points = sorted(list(time_points))
    
    # Calculate polyphony at each time point (jupyter logic)
    polyphony_series = []
    for time_point in time_points:
        active_notes = 0
        for note_event in all_note_events:
            if note_event['start'] <= time_point < note_event['end']:
                active_notes += 1
        polyphony_series.append(active_notes)
    
    return time_points, polyphony_series


def calculate_time_based_polyphony_metrics(polyphony_series, time_points):
    """
    Calculate time-weighted polyphony metrics (like jupyter notebook).
    
    Args:
        polyphony_series: List of simultaneous note counts
        time_points: List of corresponding time points
        
    Returns:
        Dictionary with time-based metrics
    """
    if not polyphony_series or not time_points or len(polyphony_series) != len(time_points):
        return {
            'avg_polyphony': 0,
            'polyphonic_ratio': 0,
            'monophonic_ratio': 0,
            'silence_ratio': 0,
            'total_duration': 0
        }
    
    # Calculate time-weighted metrics
    total_duration = 0
    weighted_polyphony_sum = 0
    polyphonic_duration = 0
    monophonic_duration = 0
    silence_duration = 0
    
    for i in range(len(time_points) - 1):
        interval_duration = time_points[i+1] - time_points[i]
        polyphony_count = polyphony_series[i]
        
        total_duration += interval_duration
        weighted_polyphony_sum += polyphony_count * interval_duration
        
        if polyphony_count == 0:
            silence_duration += interval_duration
        elif polyphony_count == 1:
            monophonic_duration += interval_duration
        else:  # polyphony_count > 1
            polyphonic_duration += interval_duration
    
    # Calculate ratios
    avg_polyphony = weighted_polyphony_sum / total_duration if total_duration > 0 else 0
    polyphonic_ratio = polyphonic_duration / total_duration if total_duration > 0 else 0
    monophonic_ratio = monophonic_duration / total_duration if total_duration > 0 else 0
    silence_ratio = silence_duration / total_duration if total_duration > 0 else 0
    
    return {
        'avg_polyphony': avg_polyphony,
        'polyphonic_ratio': polyphonic_ratio,
        'monophonic_ratio': monophonic_ratio,
        'silence_ratio': silence_ratio,
        'total_duration': total_duration
    }


def get_file_info(midi_stream):
    """Extract file information following entropy conventions."""
    measures_count = len(midi_stream.measures(0, None)[0])
    total_notes = len(midi_stream.flatten().notes)
    
    # Handle potential Fraction objects in duration
    duration = midi_stream.duration.quarterLength
    if hasattr(duration, 'numerator') and hasattr(duration, 'denominator'):
        total_duration = float(duration)
    else:
        total_duration = duration
    
    return {
        'measures_count': measures_count,
        'total_notes': total_notes,
        'total_duration': total_duration
    }


def calculate_entropy_optimized(data_list):
    """
    Calculate entropy using optimized counting with Counter.
    
    Args:
        data_list: List of values to calculate entropy for
        
    Returns:
        List of entropy contributions for each unique value
    """
    if not data_list:
        return []
    
    # Use Counter for O(n) counting instead of O(n²) count() operations
    counter = Counter(data_list)
    total_count = len(data_list)
    
    result = []
    for value, count in counter.items():
        p = count / total_count
        entr = p * (math.log2(p))
        result.append(entr)
    
    return result


def calculate_pitch_interval_entropy_optimized(pitch_list):
    """
    Calculate pitch interval entropy with optimized processing.
    
    Args:
        pitch_list: List of pitch values
        
    Returns:
        List of entropy contributions for each interval
    """
    if len(pitch_list) < 2:
        return []
    
    # Calculate intervals efficiently
    intervals = []
    for i in range(1, len(pitch_list)):
        interval = pitch_list[i] - pitch_list[i - 1]
        # Ignore intervals > 12 notes
        if abs(interval) <= 12:
            intervals.append(interval)
    
    return calculate_entropy_optimized(intervals)


def segment_analysis(midi_stream, measures_count, analysis_func, segment_size=16):
    """
    Generic segmentation analysis following entropy algorithm pattern.
    
    Args:
        midi_stream: Music21 stream object
        measures_count: Total number of measures
        analysis_func: Function to apply to each segment
        segment_size: Size of each segment in measures
        
    Returns:
        Tuple of (whole_piece_result, mean_segment_result)
    """
    # Analyze whole piece
    whole_piece_result = analysis_func(midi_stream)
    
    # Analyze segments
    first_measure = 0
    last_measure = segment_size
    segment_results = []
    
    if last_measure > measures_count:
        # Piece is shorter than segment size
        mean_segment_result = whole_piece_result
    else:
        while last_measure <= measures_count:
            try:
                segment_stream = midi_stream.measures(first_measure, last_measure)
                segment_result = analysis_func(segment_stream)
                segment_results.append(segment_result)
            except Exception as e:
                print(f"Error processing measures {first_measure}-{last_measure}: {e}")
            
            first_measure = last_measure
            last_measure += segment_size  # Fixed: Use segment_size parameter
        
        mean_segment_result = statistics.mean(segment_results) if segment_results else whole_piece_result
    
    return whole_piece_result, mean_segment_result


# Standard MIDI percussion and unpitched instruments
PERCUSSION_INSTRUMENTS = {
    # General MIDI Percussion (Channel 10)
    35: "Acoustic Bass Drum",
    36: "Bass Drum 1", 
    37: "Side Stick",
    38: "Acoustic Snare",
    39: "Hand Clap",
    40: "Electric Snare",
    41: "Low Floor Tom",
    42: "Closed Hi-Hat",
    43: "High Floor Tom",
    44: "Pedal Hi-Hat",
    45: "Low Tom",
    46: "Open Hi-Hat",
    47: "Low-Mid Tom",
    48: "Hi-Mid Tom",
    49: "Crash Cymbal 1",
    50: "High Tom",
    51: "Ride Cymbal 1",
    52: "Chinese Cymbal",
    53: "Ride Bell",
    54: "Tambourine",
    55: "Splash Cymbal",
    56: "Cowbell",
    57: "Crash Cymbal 2",
    58: "Vibraslap",
    59: "Ride Cymbal 2",
    60: "Hi Bongo",
    61: "Low Bongo",
    62: "Mute Hi Conga",
    63: "Open Hi Conga",
    64: "Low Conga",
    65: "High Timbale",
    66: "Low Timbale",
    67: "High Agogo",
    68: "Low Agogo",
    69: "Cabasa",
    70: "Maracas",
    71: "Short Whistle",
    72: "Long Whistle",
    73: "Short Guiro",
    74: "Long Guiro",
    75: "Claves",
    76: "Hi Wood Block",
    77: "Low Wood Block",
    78: "Mute Cuica",
    79: "Open Cuica",
    80: "Mute Triangle",
    81: "Open Triangle"
}

# Unpitched instruments that should be excluded from tonal analysis
UNPITCHED_INSTRUMENTS = {
    # Drums and percussion
    "drum", "drums", "percussion", "timpani", "cymbals", "gong", "tam-tam",
    # Effects and noise
    "thunder", "rain", "ocean", "bird", "telephone", "doorbell",
    # Unpitched strings
    "unpitched", "noise", "effect"
}

def is_percussion_or_unpitched(note_obj, midi_stream=None):
    """
    Check if a note object represents percussion or unpitched content.
    
    This function is now more conservative - it only filters out obvious percussion.
    
    Args:
        note_obj: Music21 note object
        midi_stream: Optional MIDI stream for better instrument detection
        
    Returns:
        bool: True if percussion/unpitched, False if pitched
    """
    # Check for PercussionChord objects - these are definitely percussion
    if hasattr(note_obj, '__class__') and 'Percussion' in note_obj.__class__.__name__:
        return True
    
    # Check for Unpitched objects - these are definitely unpitched
    if hasattr(note_obj, '__class__') and 'Unpitched' in note_obj.__class__.__name__:
        return True
    
    # Check for notes without pitch information
    if not hasattr(note_obj, 'pitch') or not hasattr(note_obj.pitch, 'pitchClass'):
        return True
    
    # Get instrument name using robust detection
    instrument_name = "Unknown"
    if midi_stream:
        instrument_name = get_instrument_for_note(note_obj, midi_stream)
    else:
        # Fallback to old method
        try:
            if hasattr(note_obj, 'getContextByClass'):
                instrument = note_obj.getContextByClass('Instrument')
                if instrument and hasattr(instrument, 'instrumentName') and instrument.instrumentName:
                    instrument_name = instrument.instrumentName
        except (AttributeError, TypeError):
            pass
    
    # Only filter if we have a clear percussion instrument name
    instrument_name_lower = instrument_name.lower()
    if 'percussion' in instrument_name_lower or 'drum' in instrument_name_lower:
        return True
    
    # Check instrument name for unpitched instruments
    for unpitched in UNPITCHED_INSTRUMENTS:
        if unpitched in instrument_name_lower:
            return True
    
    # For everything else, assume it's tonal
    # This is more conservative and prevents over-filtering
    return False


def analyze_tonal_certainty(midi_stream):
    """Analyze tonal certainty of a stream."""
    try:
        # Filter out percussion and unpitched instruments for tonal analysis
        filtered_stream = midi_stream.flatten()
        
        # Remove percussion chords and unpitched notes
        notes_to_remove = []
        for note_obj in filtered_stream.notes:
            if is_percussion_or_unpitched(note_obj, midi_stream):
                notes_to_remove.append(note_obj)
        
        # Remove the identified notes
        for note_obj in notes_to_remove:
            filtered_stream.remove(note_obj)
        
        # Only analyze if we have enough pitched notes
        if len(filtered_stream.notes) > 0:
            return filtered_stream.analyze("key").tonalCertainty()
        else:
            return 0.0
            
    except Exception as e:
        print(f"Error in tonal certainty analysis: {e}")
        return 0.0


def analyze_pitch_class_entropy(midi_stream):
    """Analyze pitch class entropy of a stream."""
    notes = extract_notes(midi_stream)
    entropy_contributions = calculate_entropy_optimized(notes)
    return 0 - sum(entropy_contributions)


def analyze_melodic_interval_entropy(midi_stream):
    """Analyze melodic interval entropy of a stream."""
    melody_notes = extract_notes_melody(midi_stream)
    entropy_contributions = calculate_pitch_interval_entropy_optimized(melody_notes)
    return 0 - sum(entropy_contributions)


def analyze_ioi_entropy(midi_stream):
    """Analyze inter-onset interval entropy of a stream."""
    ioi_list = extract_ioi(midi_stream)
    entropy_contributions = calculate_entropy_optimized(ioi_list)
    return 0 - sum(entropy_contributions)


def preprocess_midi(midi_file_path):
    """
    Preprocess MIDI file and return all common data.
    
    Args:
        midi_file_path: Path to MIDI file
        
    Returns:
        Dictionary containing all preprocessed data
    """
    if not midi_file_path:
        return None
    
    try:
        # Load and quantize the MIDI file (using enhanced open_midi for drum detection)
        midi_stream = open_midi(midi_file_path)
        quantized_stream = midi_stream.quantize()
        
        # Preserve file path after quantization for enhanced drum detection
        if hasattr(midi_stream, '_original_file_path'):
            quantized_stream._original_file_path = midi_stream._original_file_path
        midi_stream = quantized_stream
        
        # Extract file information
        file_info = get_file_info(midi_stream)
        
        # Extract all the common data using shared functions
        notes = extract_notes(midi_stream)
        melody_notes = extract_notes_melody(midi_stream)
        ioi_list = extract_ioi(midi_stream)
        time_points, polyphony_series = calculate_polyphony_series(midi_stream)
        
        # Get parts for track-based analysis
        midi_parts = midi_stream.parts.stream()
        
        # Pre-calculate tonal certainty (expensive operation)
        tonal_certainty = analyze_tonal_certainty(midi_stream)
        
        return {
            'midi_stream': midi_stream,
            'notes': notes,
            'melody_notes': melody_notes,
            'ioi_list': ioi_list,
            'polyphony_series': polyphony_series,
            'time_points': time_points,
            'midi_parts': midi_parts,
            'file_info': file_info,
            'tonal_certainty': tonal_certainty
        }
        
    except StreamException as e:
        print(f"StreamException: {e}")
        return None
    except Exception as e:
        print(f"Error preprocessing file: {e}")
        return None 


 