#!/usr/bin/env python3
"""
Generate MIDI datasets configuration for any user
"""

import os
import json
import argparse

def generate_midi_config(username):
    """Generate midi_datasets.json for a specific user."""
    
    config = {
        "values": [
            ["Dataset Name", "Server Location", "Instrument", "Audio Type", "Count"],
            ["Slakh2100", f"/scratch/gilbreth/{username}/AIM/datasets/slakh2100", "Multiple", "mid", "1710"],
            ["Maestro", f"/scratch/gilbreth/{username}/AIM/datasets/maestro", "Piano", "mid", "1276"],
            ["XMIDI", f"/scratch/gilbreth/{username}/AIM/datasets/xmidi", "Multiple", "mid", "108023"],
            ["MSMD", f"/scratch/gilbreth/{username}/AIM/datasets/msmd", "Piano", "mid", "467"],
            ["BiMMuDa", f"/scratch/gilbreth/{username}/AIM/datasets/bimmuda", "Piano", "mid", "375"],
            ["POP909", f"/scratch/gilbreth/{username}/AIM/datasets/pop909", "Piano", "mid", "909"],
            ["NESMDB", f"/scratch/gilbreth/{username}/AIM/datasets/nesmdb", "Multiple", "mid", "5278"],
            ["AAM", f"/scratch/gilbreth/{username}/AIM/datasets/aam", "Multiple", "mid", "3000"]
        ]
    }
    
    return config

def main():
    parser = argparse.ArgumentParser(description="Generate MIDI datasets configuration")
    parser.add_argument("username", help="Your username")
    
    args = parser.parse_args()
    
    config = generate_midi_config(args.username)
    
    # Write to midi_datasets.json
    with open("midi_datasets.json", "w") as f:
        json.dump(config, f, indent=4)
    
    print(f"Generated midi_datasets.json for user: {args.username}")
    print("Configuration points to:")
    print(f"  /scratch/gilbreth/{args.username}/AIM/datasets/")
    print("\nNext steps:")
    print(f"1. Download datasets: YOUR_USERNAME={args.username} sbatch datasets/dl_all_datasets_midi.sh")
    print("2. Run complexity analysis: PYTHONPATH=. python scripts/complexity_analysis.py")

if __name__ == "__main__":
    main()
