#!/usr/bin/env python3
"""
Complete Complexity Analysis
Analyzes entropy, polyphony, and ATC metrics across all datasets.
"""

import os
import json
import argparse
import pandas as pd
from pathlib import Path
import sys
import time
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict

# Add the complexity_metrics module to the path
sys.path.append("../../../music-transcription-research")

from complexity_metrics.entropy import main as entropy_analysis
from complexity_metrics.polyphony import main as polyphony_analysis
from complexity_metrics.atc_wrapper import calculate_atc_metrics

from complexity_scripts.compute.dataset_manager import get_dataset_manager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_dataset_files(dataset_name: str, limit: int = None) -> List[str]:
    """Get MIDI files from a dataset."""
    try:
        manager = get_dataset_manager()
        file_paths = manager.find_files(dataset_name, limit=limit)
        return [str(path) for path in file_paths]
    except Exception as e:
        logger.error(f"Error getting files for dataset {dataset_name}: {e}")
        return []


def analyze_complexity_for_file(midi_file_path, dataset_name):
    """Analyze complexity metrics for a single MIDI file."""
    start_time = time.time()
    filename = os.path.basename(midi_file_path)
    
    try:
        print(f"Processing: {filename}", file=sys.stderr)
        # Run entropy analysis
        entropy_results = entropy_analysis(midi_file_path)
        
        # Run ATC analysis
        atc_results = calculate_atc_metrics(midi_file_path)
        
        # Run polyphony analysis
        polyphony_results = polyphony_analysis(midi_file_path)
        
        processing_time = time.time() - start_time
        
        # Combine results
        results = {
            'midi_filename': os.path.basename(midi_file_path),
            'dataset_name': dataset_name,
            'file_path': midi_file_path,
            'processing_time': processing_time,
            'timestamp': pd.Timestamp.now()
        }
        
        # Add entropy metrics
        if entropy_results:
            results.update(entropy_results)
        
        # Add polyphony metrics
        if polyphony_results:
            results.update(polyphony_results)
        
        # Add ATC metrics
        if atc_results and not atc_results.get('error'):
            results['atc_score'] = atc_results.get('atc_score', 0)
            results['atc_processing_time'] = atc_results.get('processing_time', 0)
            if 'harmonic_complexity' in atc_results:
                for key, value in atc_results['harmonic_complexity'].items():
                    results[f'atc_{key}'] = value
        else:
            results['atc_score'] = 0
            results['atc_processing_time'] = 0
            if atc_results and atc_results.get('error'):
                results['atc_error'] = atc_results['error']
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing {midi_file_path}: {str(e)}")
        return {
            'midi_filename': os.path.basename(midi_file_path),
            'dataset_name': dataset_name,
            'file_path': midi_file_path,
            'processing_time': time.time() - start_time,
            'error': str(e)
        }


def process_batch_parallel(midi_files: List[str], dataset_name: str, num_workers: int = 32) -> List[Dict]:
    """Process multiple MIDI files in parallel."""
    print(f"Starting parallel processing of {len(midi_files)} files from {dataset_name} with {num_workers} workers", file=sys.stderr)
    logger.info(f"Starting parallel processing of {len(midi_files)} files from {dataset_name} with {num_workers} workers")
    
    start_time = time.time()
    results = []
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        future_to_file = {executor.submit(analyze_complexity_for_file, midi_file, dataset_name): midi_file 
                         for midi_file in midi_files}
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_file):
            midi_file = future_to_file[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                completed += 1
                
                # Progress update every 5 files or at the end
                if completed % 5 == 0 or completed == len(midi_files):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = (len(midi_files) - completed) / rate if rate > 0 else 0
                    progress_msg = f"Progress: {completed}/{len(midi_files)} ({completed/len(midi_files)*100:.1f}%) Rate: {rate:.2f} files/sec, ETA: {remaining/60:.1f} minutes"
                    print(progress_msg, file=sys.stderr)
                    logger.info(progress_msg)
                
                # Individual file completion
                if completed % 1 == 0:
                    filename = os.path.basename(midi_file)
                    print(f"Completed: {filename} ({completed}/{len(midi_files)})", file=sys.stderr)
                
            except Exception as e:
                error_msg = f"Exception for {midi_file}: {e}"
                print(error_msg, file=sys.stderr)
                logger.error(error_msg)
                results.append({
                    'midi_filename': os.path.basename(midi_file),
                    'dataset_name': dataset_name,
                    'file_path': midi_file,
                    'error': str(e),
                    'processing_time': 0,
                    'atc_score': 0,
                    'atc_processing_time': 0
                })
    
    total_time = time.time() - start_time
    completion_msg = f"Completed processing {len(midi_files)} files in {total_time:.2f}s ({len(midi_files)/total_time:.2f} files/sec)"
    print(completion_msg, file=sys.stderr)
    logger.info(completion_msg)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Analyze music complexity metrics')
    parser.add_argument('--dataset', type=str, help='Specific dataset to analyze')
    parser.add_argument('--output-dir', type=str, default='./complexity_results', 
                       help='Output directory for results')
    parser.add_argument('--max-files', type=int, default=None, 
                       help='Maximum number of files to analyze per dataset')
    parser.add_argument('--num-workers', type=int, default=32,
                       help='Number of parallel workers (default: 32)')
    
    args = parser.parse_args()
    
    # Use dataset manager instead of config file
    from complexity_scripts.compute.dataset_manager import get_dataset_manager
    manager = get_dataset_manager()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    all_results = []
    
    # Get available datasets
    available_datasets = ['slakh2100', 'maestro', 'pop909', 'nesmdb', 'msmd', 'aam', 'bimmuda', 'traditional_flute', 'xmidi']
    
    for dataset_name in available_datasets:
        # Skip if specific dataset requested and this isn't it
        if args.dataset and dataset_name != args.dataset:
            continue
        
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Analyzing dataset: {dataset_name}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing dataset: {dataset_name}")
        logger.info(f"{'='*60}")
        
        # Find MIDI files using dataset manager
        midi_files = get_dataset_files(dataset_name, limit=args.max_files)
        
        if not midi_files:
            warning_msg = f"No MIDI files found in {dataset_name}"
            print(warning_msg, file=sys.stderr)
            logger.warning(warning_msg)
            continue
        
        found_msg = f"Found {len(midi_files)} MIDI files"
        print(found_msg, file=sys.stderr)
        logger.info(found_msg)
        
        # Process files in parallel
        dataset_results = process_batch_parallel(midi_files, dataset_name, args.num_workers)
        
        # Save dataset results
        if dataset_results:
            df = pd.DataFrame(dataset_results)
            output_file = os.path.join(args.output_dir, f"{dataset_name}_complexity.csv")
            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(dataset_results)} results to {output_file}")
            
            all_results.extend(dataset_results)
    
    # Save combined results
    if all_results:
        combined_df = pd.DataFrame(all_results)
        combined_file = os.path.join(args.output_dir, "all_complexity_results.csv")
        combined_df.to_csv(combined_file, index=False)
        logger.info(f"Saved combined results to {combined_file}")
        
        # Print summary statistics
        summary_msg = f"\n{'='*60}\nCOMPLEXITY ANALYSIS SUMMARY\n{'='*60}\nTotal files analyzed: {len(all_results)}"
        print(summary_msg, file=sys.stderr)
        logger.info(f"\n{'='*60}")
        logger.info("COMPLEXITY ANALYSIS SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total files analyzed: {len(all_results)}")
        
        if 'max_poly' in combined_df.columns:
            poly_msg = f"Average max polyphony: {combined_df['max_poly'].mean():.2f}\nMax polyphony range: {combined_df['max_poly'].min()} - {combined_df['max_poly'].max()}"
            print(poly_msg, file=sys.stderr)
            logger.info(f"Average max polyphony: {combined_df['max_poly'].mean():.2f}")
            logger.info(f"Max polyphony range: {combined_df['max_poly'].min()} - {combined_df['max_poly'].max()}")
        
        if 'tonal_certainty' in combined_df.columns:
            tonal_msg = f"Average tonal certainty: {combined_df['tonal_certainty'].mean():.4f}\nTonal certainty range: {combined_df['tonal_certainty'].min():.4f} - {combined_df['tonal_certainty'].max():.4f}"
            print(tonal_msg, file=sys.stderr)
            logger.info(f"Average tonal certainty: {combined_df['tonal_certainty'].mean():.4f}")
            logger.info(f"Tonal certainty range: {combined_df['tonal_certainty'].min():.4f} - {combined_df['tonal_certainty'].max():.4f}")


if __name__ == "__main__":
    main()
