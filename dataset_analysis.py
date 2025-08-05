#!/opt/homebrew/bin/python3
"""
Name: dataset_analysis.py
Purpose: Analyze MIDI files in datasets for use in music transcription survey papers.
"""

import json
import os
import statistics
import mido
import pandas as pd
import argparse
import concurrent.futures
from collections import Counter
from tqdm import tqdm
from pathlib import Path


def get_midi_files(dataset_path):
    """Find all MIDI files in a dataset directory using pathlib."""
    path = Path(dataset_path)
    if not path.exists():
        return []

    patterns = ["*.mid", "*.midi", "*.MID", "*.MIDI"]
    midi_files = []
    for pattern in patterns:
        midi_files.extend(path.rglob(pattern))
    return [str(f) for f in sorted(midi_files)]


def analyze_midi_file(midi_path):
    """Extract musical statistics from a single MIDI file."""
    try:
        mid = mido.MidiFile(midi_path)
        instruments = set()
        channels_used = set()
        pitches = []
        velocities = []
        tempo_changes = []
        time_signatures = set()
        key_signatures = set()
        control_changes = set()

        note_count = 0
        current_programs = {}

        for track in mid.tracks:
            for msg in track:
                msg_type = msg.type

                if msg_type == "program_change":
                    current_programs[msg.channel] = msg.program
                    instruments.add(msg.program)
                elif msg_type == "note_on" and msg.velocity > 0:
                    note_count += 1
                    channels_used.add(msg.channel)
                    pitches.append(msg.note)
                    velocities.append(msg.velocity)
                    if msg.channel not in current_programs:
                        current_programs[msg.channel] = 0
                    instruments.add(current_programs[msg.channel])
                elif msg_type == "set_tempo":
                    tempo_changes.append(mido.tempo2bpm(msg.tempo))
                elif msg_type == "time_signature":
                    time_signatures.add(f"{msg.numerator}/{msg.denominator}")
                elif msg_type == "key_signature":
                    key_signatures.add(msg.key)
                elif msg_type == "control_change":
                    control_changes.add(msg.control)

        has_dynamics = bool(control_changes & {7, 11})
        has_pedal = 64 in control_changes
        has_modulation = 1 in control_changes

        pitch_range = max(pitches) - min(pitches) if pitches else 0
        avg_velocity = statistics.mean(velocities) if velocities else 0
        note_density = note_count / mid.length if mid.length > 0 else 0
        avg_tempo = statistics.mean(tempo_changes) if tempo_changes else None

        return {
            "filename": os.path.basename(midi_path),
            "length_seconds": mid.length,
            "num_tracks": len(mid.tracks),
            "ticks_per_beat": mid.ticks_per_beat,
            "note_count": note_count,
            "unique_instruments": len(instruments),
            "channels_used": len(channels_used),
            "is_piano_only": len(instruments) == 1 and 0 in instruments,
            "is_monophonic": len(channels_used) == 1,
            "pitch_range": pitch_range,
            "avg_velocity": avg_velocity,
            "avg_tempo": avg_tempo,
            "note_density": note_density,
            "has_dynamics": has_dynamics,
            "has_pedal": has_pedal,
            "has_modulation": has_modulation,
            "instruments": sorted(list(instruments)),
        }

    except Exception as e:
        return {"filename": os.path.basename(midi_path), "error": str(e)}


def analyze_dataset(dataset_info, output_dir, max_workers=8):
    dataset_name, dataset_path = dataset_info[0], dataset_info[1]
    print(f"\nAnalyzing dataset: {dataset_name}")

    if not os.path.exists(dataset_path):
        result = {
            "dataset_name": dataset_name,
            "status": "Path not found",
            "file_count": 0,
        }
        return result

    midi_files = get_midi_files(dataset_path)
    if not midi_files:
        result = {
            "dataset_name": dataset_name,
            "status": "No MIDI files found",
            "file_count": 0,
        }
        return result

    print(f"Found {len(midi_files)} MIDI files in {dataset_name}")
    all_analyses = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_midi_file, f): f for f in midi_files}
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc=f"{dataset_name}",
        ):
            result = future.result()
            all_analyses.append(result)

    valid_analyses = [a for a in all_analyses if "error" not in a]
    print(f"Completed: {len(valid_analyses)}/{len(midi_files)} successful files")

    if not valid_analyses:
        return {
            "dataset_name": dataset_name,
            "status": "All files failed",
            "file_count": len(midi_files),
        }

    dataset_stats = calculate_dataset_stats(
        dataset_name, valid_analyses, len(midi_files)
    )

    # Save detailed per-dataset JSON
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(
        output_dir, f"{dataset_name.replace(' ', '_')}_detailed.json"
    )
    with open(json_path, "w") as f:
        json.dump(dataset_stats, f, indent=2)
    print(f"Saved detailed stats to {json_path}")

    return dataset_stats


def calculate_dataset_stats(dataset_name, analyses, total_files):
    durations = [a["length_seconds"] for a in analyses if a["length_seconds"]]
    note_counts = [a["note_count"] for a in analyses]
    instrument_counts = [a["unique_instruments"] for a in analyses]
    pitch_ranges = [a["pitch_range"] for a in analyses if a["pitch_range"] > 0]
    velocities = [a["avg_velocity"] for a in analyses if a["avg_velocity"] > 0]
    note_densities = [a["note_density"] for a in analyses if a["note_density"] > 0]
    tempos = [a["avg_tempo"] for a in analyses if a["avg_tempo"]]

    piano_only = sum(a["is_piano_only"] for a in analyses)
    monophonic = sum(a["is_monophonic"] for a in analyses)
    has_dynamics = sum(a["has_dynamics"] for a in analyses)
    has_pedal = sum(a["has_pedal"] for a in analyses)
    has_modulation = sum(a["has_modulation"] for a in analyses)

    all_instruments = [inst for a in analyses for inst in a["instruments"]]
    instrument_freq = Counter(all_instruments)

    return {
        "dataset_name": dataset_name,
        "file_count": total_files,
        "total_duration_hours": sum(durations) / 3600 if durations else 0,
        "avg_duration": statistics.mean(durations) if durations else 0,
        "total_notes": sum(note_counts),
        "avg_notes_per_file": statistics.mean(note_counts),
        "avg_note_density": statistics.mean(note_densities) if note_densities else 0,
        "avg_pitch_range": statistics.mean(pitch_ranges) if pitch_ranges else 0,
        "avg_velocity": statistics.mean(velocities) if velocities else 0,
        "avg_tempo_bpm": statistics.mean(tempos) if tempos else None,
        "tempo_range": f"{min(tempos):.1f}-{max(tempos):.1f}" if tempos else None,
        "unique_instruments_total": len(instrument_freq),
        "avg_instruments_per_file": statistics.mean(instrument_counts),
        "piano_only_pct": piano_only / len(analyses) * 100,
        "monophonic_pct": monophonic / len(analyses) * 100,
        "dynamics_pct": has_dynamics / len(analyses) * 100,
        "pedal_pct": has_pedal / len(analyses) * 100,
        "modulation_pct": has_modulation / len(analyses) * 100,
        "top_instruments": dict(instrument_freq.most_common(5)),
    }


def generate_final_report(all_results, output_dir, generate_tex=False):
    df = pd.DataFrame(all_results)
    df = df[
        [
            "dataset_name",
            "file_count",
            "total_duration_hours",
            "avg_duration",
            "total_notes",
            "avg_notes_per_file",
            "avg_note_density",
            "avg_pitch_range",
            "avg_velocity",
            "avg_tempo_bpm",
            "tempo_range",
            "unique_instruments_total",
            "avg_instruments_per_file",
            "piano_only_pct",
            "monophonic_pct",
            "dynamics_pct",
            "pedal_pct",
            "modulation_pct",
        ]
    ]
    csv_path = os.path.join(output_dir, "dataset_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"Summary saved to {csv_path}")

    if generate_tex:
        tex_path = os.path.join(output_dir, "dataset_summary.tex")
        with open(tex_path, "w") as f:
            f.write("\\begin{tabular}{lrrrrr}\n")
            f.write("\\toprule\n")
            f.write(
                "Dataset & Files & Duration (h) & Notes & Instruments & Piano-Only (\%) \\\n"
            )
            f.write("\\midrule\n")
            for row in df.itertuples():
                f.write(
                    f"{row.dataset_name} & {row.file_count} & {row.total_duration_hours:.1f} & {row.total_notes} & {row.unique_instruments_total} & {row.piano_only_pct:.1f} \\\n"
                )
            f.write("\\bottomrule\n")
            f.write("\\end{tabular}\n")
        print(f"LaTeX table saved to {tex_path}")


def main():
    parser = argparse.ArgumentParser(description="MIDI dataset analyzer")
    parser.add_argument("config", help="Path to JSON config file")
    parser.add_argument("--output-dir", default=".", help="Directory to save results")
    parser.add_argument(
        "--file-workers",
        type=int,
        default=None,
        help="Parallel workers per dataset (default: all cores)",
    )
    parser.add_argument(
        "--generate-tex", action="store_true", help="Generate LaTeX table of results"
    )
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)
    file_workers = args.file_workers or os.cpu_count()

    dataset_infos = config["values"][1:]  # Skip header
    all_results = []

    for dataset_info in dataset_infos:
        result = analyze_dataset(dataset_info, args.output_dir, file_workers)
        if "file_count" in result and result["file_count"] > 0:
            all_results.append(result)

    generate_final_report(all_results, args.output_dir, generate_tex=args.generate_tex)


if __name__ == "__main__":
    main()
