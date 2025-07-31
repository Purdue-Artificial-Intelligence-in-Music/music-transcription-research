#!/usr/bin/env python3
"""
Complete Complexity Analysis using ALL datasets
Uses datasets stored in /scratch/gilbreth/YOUR_USERNAME/AIM/datasets/
All MIDI files only (no WAV conversion)
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

# Add the complexity module to the path
sys.path.append(".")

from complexity.entropy import main as entropy_analysis
from complexity.polyphony import main as polyphony_analysis

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_datasets_config():
    """Load dataset configuration from midi_datasets.json."""
    datasets_file = os.path.join(os.path.dirname(__file__), '..', 'midi_datasets.json')
    with open(datasets_file, 'r') as f:
        data = json.load(f)
    
    # Skip header row
    datasets = []
    for row in data['values'][1:]:
        dataset_name, dataset_path, instrument, audio_type, count = row
        datasets.append({
            'name': dataset_name,
            'path': dataset_path,
            'instrument': instrument,
            'audio_type': audio_type,
            'count': int(count)
        })
    
    return datasets


def find_midi_files(dataset_path):
    """Find all MIDI files in a dataset directory."""
    midi_files = []
    if os.path.exists(dataset_path):
        for root, dirs, files in os.walk(dataset_path):
            for file in files:
                if file.lower().endswith('.mid') or file.lower().endswith('.midi'):
                    midi_files.append(os.path.join(root, file))
    return midi_files


def analyze_complexity_for_file(midi_file_path, dataset_name):
    """Analyze complexity metrics for a single MIDI file."""
    start_time = time.time()
    
    try:
        # Run entropy analysis
        entropy_results = entropy_analysis(midi_file_path)
        
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


def process_batch_parallel(midi_files: List[str], dataset_name: str, num_workers: int = 16) -> List[Dict]:
    """Process multiple MIDI files in parallel using ProcessPoolExecutor."""
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
                
                # Progress update every 10 files or at the end
                if completed % 10 == 0 or completed == len(midi_files):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = (len(midi_files) - completed) / rate if rate > 0 else 0
                    logger.info(f"Progress: {completed}/{len(midi_files)} ({completed/len(midi_files)*100:.1f}%) "
                              f"Rate: {rate:.2f} files/sec, ETA: {remaining/60:.1f} minutes")
                
            except Exception as e:
                logger.error(f"Exception for {midi_file}: {e}")
                results.append({
                    'midi_filename': os.path.basename(midi_file),
                    'dataset_name': dataset_name,
                    'file_path': midi_file,
                    'error': str(e),
                    'processing_time': 0
                })
    
    total_time = time.time() - start_time
    logger.info(f"Completed processing {len(midi_files)} files in {total_time:.2f}s "
               f"({len(midi_files)/total_time:.2f} files/sec)")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Analyze music complexity metrics')
    parser.add_argument('--dataset', type=str, help='Specific dataset to analyze')
    parser.add_argument('--output-dir', type=str, default='./complexity_results', 
                       help='Output directory for results')
    parser.add_argument('--max-files', type=int, default=None, 
                       help='Maximum number of files to analyze per dataset')
    parser.add_argument('--num-workers', type=int, default=16,
                       help='Number of parallel workers (default: 16)')
    
    args = parser.parse_args()
    
    # Load dataset configuration
    datasets = load_datasets_config()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    all_results = []
    
    for dataset in datasets:
        dataset_name = dataset['name']
        dataset_path = dataset['path']
        
        # Skip if specific dataset requested and this isn't it
        if args.dataset and dataset_name != args.dataset:
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing dataset: {dataset_name}")
        logger.info(f"Path: {dataset_path}")
        logger.info(f"{'='*60}")
        
        # Find MIDI files
        midi_files = find_midi_files(dataset_path)
        
        if not midi_files:
            logger.warning(f"No MIDI files found in {dataset_path}")
            continue
        
        logger.info(f"Found {len(midi_files)} MIDI files")
        
        # Limit files if requested
        if args.max_files:
            midi_files = midi_files[:args.max_files]
            logger.info(f"Analyzing first {len(midi_files)} files")
        
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
        logger.info(f"\n{'='*60}")
        logger.info("COMPLEXITY ANALYSIS SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total files analyzed: {len(all_results)}")
        
        if 'max_polyphony' in combined_df.columns:
            logger.info(f"Average max polyphony: {combined_df['max_polyphony'].mean():.2f}")
            logger.info(f"Max polyphony range: {combined_df['max_polyphony'].min()} - {combined_df['max_polyphony'].max()}")
        
        if 'tonal_certainty_piece' in combined_df.columns:
            logger.info(f"Average tonal certainty: {combined_df['tonal_certainty_piece'].mean():.4f}")
            logger.info(f"Tonal certainty range: {combined_df['tonal_certainty_piece'].min():.4f} - {combined_df['tonal_certainty_piece'].max():.4f}")


if __name__ == "__main__":
    main()
