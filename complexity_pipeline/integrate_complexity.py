#!/opt/homebrew/bin/python3
"""
Name: integrate_complexity.py
Purpose: Integrate complexity analysis results with existing transcription results
"""

import os
import pandas as pd
import argparse
from pathlib import Path


def load_existing_dataframe():
    """Load the existing transcription results dataframe."""
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    csv_file = os.path.join(data_dir, 'dataframe.csv')
    pkl_file = os.path.join(data_dir, 'dataframe.pkl')
    
    if os.path.exists(csv_file):
        return pd.read_csv(csv_file)
    elif os.path.exists(pkl_file):
        return pd.read_pickle(pkl_file)
    else:
        print("No existing dataframe found!")
        return None


def load_complexity_results(complexity_dir):
    """Load complexity analysis results."""
    all_complexity = []
    
    if not os.path.exists(complexity_dir):
        print(f"Complexity results directory not found: {complexity_dir}")
        return None
    
    # Look for individual dataset files and combined file
    for file in os.listdir(complexity_dir):
        if file.endswith('_complexity.csv'):
            file_path = os.path.join(complexity_dir, file)
            df = pd.read_csv(file_path)
            all_complexity.append(df)
    
    # Also check for combined file
    combined_file = os.path.join(complexity_dir, 'all_complexity_results.csv')
    if os.path.exists(combined_file):
        return pd.read_csv(combined_file)
    
    # Combine individual files if no combined file exists
    if all_complexity:
        return pd.concat(all_complexity, ignore_index=True)
    
    return None


def match_files_by_name(transcription_df, complexity_df):
    """
    Match transcription and complexity results by filename.
    Handles different naming conventions between .wav and .mid files.
    """
    # Create a mapping from transcription filenames to complexity filenames
    transcription_files = set(transcription_df['midi_filename'].str.replace('.wav', ''))
    complexity_files = set(complexity_df['midi_filename'].str.replace('.mid', '').str.replace('.midi', ''))
    
    # Find common base names
    common_files = transcription_files.intersection(complexity_files)
    
    print(f"Found {len(common_files)} matching files between transcription and complexity results")
    
    # Create a mapping for easier lookup
    file_mapping = {}
    for base_name in common_files:
        # Find transcription row
        trans_row = transcription_df[transcription_df['midi_filename'].str.replace('.wav', '') == base_name]
        # Find complexity row
        comp_row = complexity_df[complexity_df['midi_filename'].str.replace('.mid', '').str.replace('.midi', '') == base_name]
        
        if not trans_row.empty and not comp_row.empty:
            file_mapping[base_name] = {
                'transcription_idx': trans_row.index[0],
                'complexity_idx': comp_row.index[0]
            }
    
    return file_mapping


def integrate_results(transcription_df, complexity_df):
    """Integrate complexity metrics into the transcription dataframe."""
    # Create a copy to avoid modifying the original
    integrated_df = transcription_df.copy()
    
    # Get file mappings
    file_mapping = match_files_by_name(transcription_df, complexity_df)
    
    # Add complexity columns (initialize with NaN)
    complexity_columns = [
        'max_polyphony', 'avg_polyphony', 'polyphony_density', 'polyphony_std',
        'k_piece', 'Hpc_piece', 'max_Hpi_piece', 'max_Hioi_piece',
        'mean_k_measures', 'mean_Hpc_measures', 'mean_max_Hpi_measures', 'mean_max_Hioi_measures'
    ]
    
    for col in complexity_columns:
        if col in complexity_df.columns:
            integrated_df[col] = float('nan')
    
    # Fill in complexity values for matching files
    matched_count = 0
    for base_name, mapping in file_mapping.items():
        trans_idx = mapping['transcription_idx']
        comp_idx = mapping['complexity_idx']
        
        # Copy complexity metrics to transcription row
        for col in complexity_columns:
            if col in complexity_df.columns:
                integrated_df.at[trans_idx, col] = complexity_df.at[comp_idx, col]
        
        matched_count += 1
    
    print(f"Successfully integrated complexity metrics for {matched_count} files")
    
    return integrated_df


def main():
    parser = argparse.ArgumentParser(description='Integrate complexity analysis with transcription results')
    parser.add_argument('--complexity-dir', type=str, default='./complexity_results',
                       help='Directory containing complexity analysis results')
    parser.add_argument('--output-dir', type=str, default='./data',
                       help='Output directory for integrated results')
    
    args = parser.parse_args()
    
    print("Loading existing transcription results...")
    transcription_df = load_existing_dataframe()
    
    if transcription_df is None:
        print("No transcription results found. Please run the main pipeline first.")
        return
    
    print(f"Loaded transcription results: {len(transcription_df)} rows")
    
    print("Loading complexity analysis results...")
    complexity_df = load_complexity_results(args.complexity_dir)
    
    if complexity_df is None:
        print("No complexity results found. Please run complexity analysis first.")
        return
    
    print(f"Loaded complexity results: {len(complexity_df)} rows")
    
    print("Integrating results...")
    integrated_df = integrate_results(transcription_df, complexity_df)
    
    # Save integrated results
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Save as CSV
    csv_output = os.path.join(args.output_dir, 'integrated_results.csv')
    integrated_df.to_csv(csv_output, index=False)
    
    # Save as pickle
    pkl_output = os.path.join(args.output_dir, 'integrated_results.pkl')
    integrated_df.to_pickle(pkl_output)
    
    print(f"Saved integrated results to:")
    print(f"  CSV: {csv_output}")
    print(f"  Pickle: {pkl_output}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("INTEGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"Original transcription rows: {len(transcription_df)}")
    print(f"Complexity analysis rows: {len(complexity_df)}")
    print(f"Integrated rows: {len(integrated_df)}")
    
    # Count how many rows have complexity data
    complexity_cols = [col for col in integrated_df.columns if col in [
        'max_polyphony', 'avg_polyphony', 'polyphony_density', 'polyphony_std',
        'k_piece', 'Hpc_piece', 'max_Hpi_piece', 'max_Hioi_piece'
    ]]
    
    if complexity_cols:
        rows_with_complexity = integrated_df[complexity_cols[0]].notna().sum()
        print(f"Rows with complexity data: {rows_with_complexity}")
        
        # Show some statistics for complexity metrics
        print(f"\nComplexity Metrics Summary:")
        for col in complexity_cols:
            if col in integrated_df.columns:
                valid_data = integrated_df[col].dropna()
                if len(valid_data) > 0:
                    print(f"  {col}: mean={valid_data.mean():.4f}, std={valid_data.std():.4f}")


if __name__ == "__main__":
    main() 