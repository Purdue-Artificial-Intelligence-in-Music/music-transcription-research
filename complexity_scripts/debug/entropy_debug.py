#!/usr/bin/env python3
"""
Entropy Debugging Script
Compare entropy measures between different implementations
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from complexity_metrics.entropy import main as entropy_analysis
from complexity_pipeline.dataset_manager import get_dataset_manager

def debug_entropy_measures(file_path):
    """Debug entropy measures for a single file"""
    print(f"🔍 DEBUGGING ENTROPY MEASURES")
    print(f"📁 File: {os.path.basename(file_path)}")
    print("="*60)
    
    try:
        # Run entropy analysis
        results = entropy_analysis(file_path)
        
        if results:
            print(f"🎼 Tonal Certainty: {results.get('tonal_certainty_piece', 0):.4f}")
            print(f"🎵 Pitch Class Entropy: {results.get('pitch_class_entropy_piece', 0):.4f}")
            print(f"🎹 Melodic Interval Entropy: {results.get('melodic_interval_entropy_piece', 0):.4f}")
            print(f"⏱️  IOI Entropy: {results.get('ioi_entropy_piece', 0):.4f}")
            
            # Debug info
            print(f"")
            print(f"🔍 DEBUG INFO:")
            print(f"   All results: {results}")
        else:
            print("❌ No results returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def compare_entropy_batch(dataset_name="slakh2100", limit=5):
    """Compare entropy measures across multiple files"""
    print(f"🔍 BATCH ENTROPY COMPARISON")
    print(f"📊 Dataset: {dataset_name}")
    print(f"📁 Files: {limit}")
    print("="*60)
    
    try:
        # Get dataset files
        manager = get_dataset_manager()
        files = manager.find_files(dataset_name, limit=limit)
        
        results = []
        for i, file_path in enumerate(files, 1):
            print(f"Processing {i}/{len(files)}: {file_path.name}")
            
            try:
                result = entropy_analysis(str(file_path))
                if result:
                    result['filename'] = file_path.name
                    result['dataset'] = dataset_name
                    results.append(result)
            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}")
        
        # Create comparison DataFrame
        if results:
            df = pd.DataFrame(results)
            print(f"")
            print(f"📊 RESULTS SUMMARY:")
            print(f"   Files processed: {len(results)}")
            print(f"   Average tonal certainty: {df['tonal_certainty_piece'].mean():.4f}")
            print(f"   Average pitch class entropy: {df['pitch_class_entropy_piece'].mean():.4f}")
            print(f"   Average melodic interval entropy: {df['melodic_interval_entropy_piece'].mean():.4f}")
            print(f"   Average IOI entropy: {df['ioi_entropy_piece'].mean():.4f}")
            
            # Save results
            output_file = f"entropy_debug_{dataset_name}.csv"
            df.to_csv(output_file, index=False)
            print(f"💾 Results saved to: {output_file}")
            
            return df
        else:
            print("❌ No results generated")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Main debugging function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug entropy measures")
    parser.add_argument("--file", type=str, help="Single file to debug")
    parser.add_argument("--dataset", type=str, default="slakh2100", help="Dataset to analyze")
    parser.add_argument("--limit", type=int, default=5, help="Number of files to analyze")
    
    args = parser.parse_args()
    
    if args.file:
        # Debug single file
        debug_entropy_measures(args.file)
    else:
        # Debug batch
        compare_entropy_batch(args.dataset, args.limit)

if __name__ == "__main__":
    main() 