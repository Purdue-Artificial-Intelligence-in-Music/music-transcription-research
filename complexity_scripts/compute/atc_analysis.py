#!/usr/bin/env python3
"""
ATC Analysis Script
Analyzes ATC metrics using both audio spectral chordino method and MIDI pychord calculation method.
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
import tempfile
import shutil
import subprocess

# Add the complexity_metrics module to the path
sys.path.append("/home/shang33/AIM/music-transcription-research")

from complexity_metrics.atc_wrapper import calculate_atc_metrics
from complexity_metrics.atc.single_midi_atc import midi_to_chordino_labels_harmony_format
from complexity_metrics.atc.chordino_simulation import midi_to_chordino_labels_chordino_simulation
from complexity_metrics.atc.midi_to_chroma import midi_to_chroma

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


def run_atc_analysis_with_chordino_simulation(midi_file_path):
    """
    Run ATC analysis using chordino simulation approach.
    """
    start_time = time.time()
    
    # Extract track ID from filename
    track_id = os.path.splitext(os.path.basename(midi_file_path))[0]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_chroma = os.path.join(temp_dir, f"{track_id}-chromas.txt")
        temp_chordino = os.path.join(temp_dir, f"{track_id}-chordino-labels.txt")
        temp_midi = os.path.join(temp_dir, f"{track_id}.mid")
        
        # Copy MIDI file to temp directory
        shutil.copy2(midi_file_path, temp_midi)
        
        # Generate chroma features
        midi_to_chroma(midi_file_path, temp_chroma, 10.0)
        
        # Generate chordino labels using chordino simulation
        midi_to_chordino_labels_chordino_simulation(midi_file_path, temp_chordino)
        
        # Run harmony analysis
        jar_path = '/home/shang33/AIM/music-transcription-research/complexity_metrics/atc/harmony-analyser/target/ha-script-1.2-beta.jar'
        cmd = [
            "java", "-Djava.awt.headless=true", "-jar",
            jar_path,
            "-a", "chord_analyser:average_chord_complexity_distance",
            "-s", ".mid",
            "-t", "0.001"
        ]
        
        # Change to temp directory and run
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                return {
                    'atc_score': 0.0,
                    'accd_score': 0.0,
                    'acc_score': 0.0,
                    'rccd_score': 0.0,
                    'processing_time': time.time() - start_time,
                    'error': f"Harmony analysis failed: {result.stderr}"
                }
            
            # Check if output was generated
            expected_output = os.path.join(temp_dir, f"{track_id}-average-cc-distance.txt")
            if os.path.exists(expected_output):
                # Parse ATC score
                atc_score = None
                rccd_score = None
                accd_score = None
                acc_score = None
                
                with open(expected_output, 'r') as f:
                    for line in f:
                        if 'Average Chord Complexity Distance' in line:
                            parts = line.strip().split(':')
                            if len(parts) == 2:
                                accd_score = float(parts[1].strip())
                        elif 'Relative Chord Complexity Distance' in line:
                            parts = line.strip().split(':')
                            if len(parts) == 2:
                                rccd_score = float(parts[1].strip())
                        elif 'Average Chord Complexity' in line:
                            parts = line.strip().split(':')
                            if len(parts) == 2:
                                acc_score = float(parts[1].strip())
                
                # Use RCCD as ATC score
                final_score = rccd_score if rccd_score is not None else accd_score
                
                if final_score is not None:
                    return {
                        'atc_score': final_score,
                        'accd_score': accd_score,
                        'acc_score': acc_score,
                        'rccd_score': rccd_score,
                        'processing_time': time.time() - start_time,
                        'error': None
                    }
            
            return {
                'atc_score': 0.0,
                'accd_score': 0.0,
                'acc_score': 0.0,
                'rccd_score': 0.0,
                'processing_time': time.time() - start_time,
                'error': 'Harmony analysis did not generate expected output'
            }
            
        finally:
            os.chdir(old_cwd)


def analyze_atc_for_file(midi_file_path, dataset_name):
    """Analyze ATC metrics for a single MIDI file using both methods."""
    start_time = time.time()
    filename = os.path.basename(midi_file_path)
    
    try:
        print(f"Processing: {filename}", file=sys.stderr)
        
        # Method 1: PYCHORD approach (current implementation)
        print(f"  Running PYCHORD method...", file=sys.stderr)
        pychord_results = calculate_atc_metrics(midi_file_path)
        
        # Method 2: CHORDINO SIMULATION approach
        print(f"  Running CHORDINO SIMULATION method...", file=sys.stderr)
        chordino_results = run_atc_analysis_with_chordino_simulation(midi_file_path)
        
        processing_time = time.time() - start_time
        
        # Combine results
        results = {
            'midi_filename': os.path.basename(midi_file_path),
            'dataset_name': dataset_name,
            'file_path': midi_file_path,
            'total_processing_time': processing_time,
            'timestamp': pd.Timestamp.now()
        }
        
        # Add PYCHORD method results
        if pychord_results and not pychord_results.get('error'):
            results['pychord_atc_score'] = pychord_results.get('atc_score', 0)
            results['pychord_processing_time'] = pychord_results.get('processing_time', 0)
            if 'analysis_details' in pychord_results:
                results['pychord_accd_score'] = pychord_results['analysis_details'].get('accd_score', 0)
                results['pychord_rccd_score'] = pychord_results['analysis_details'].get('rccd_score', 0)
                results['pychord_acc_score'] = pychord_results['analysis_details'].get('acc_score', 0)
        else:
            results['pychord_atc_score'] = 0
            results['pychord_processing_time'] = 0
            results['pychord_accd_score'] = 0
            results['pychord_rccd_score'] = 0
            results['pychord_acc_score'] = 0
            if pychord_results and pychord_results.get('error'):
                results['pychord_error'] = pychord_results['error']
        
        # Add CHORDINO SIMULATION method results
        if chordino_results and not chordino_results.get('error'):
            results['chordino_atc_score'] = chordino_results.get('atc_score', 0)
            results['chordino_processing_time'] = chordino_results.get('processing_time', 0)
            results['chordino_accd_score'] = chordino_results.get('accd_score', 0)
            results['chordino_rccd_score'] = chordino_results.get('rccd_score', 0)
            results['chordino_acc_score'] = chordino_results.get('acc_score', 0)
        else:
            results['chordino_atc_score'] = 0
            results['chordino_processing_time'] = 0
            results['chordino_accd_score'] = 0
            results['chordino_rccd_score'] = 0
            results['chordino_acc_score'] = 0
            if chordino_results and chordino_results.get('error'):
                results['chordino_error'] = chordino_results['error']
        
        # Calculate differences
        results['atc_score_difference'] = abs(results['pychord_atc_score'] - results['chordino_atc_score'])
        results['rccd_score_difference'] = abs(results['pychord_rccd_score'] - results['chordino_rccd_score'])
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing {midi_file_path}: {str(e)}")
        return {
            'midi_filename': os.path.basename(midi_file_path),
            'dataset_name': dataset_name,
            'file_path': midi_file_path,
            'total_processing_time': time.time() - start_time,
            'error': str(e),
            'pychord_atc_score': 0,
            'pychord_processing_time': 0,
            'pychord_accd_score': 0,
            'pychord_rccd_score': 0,
            'pychord_acc_score': 0,
            'chordino_atc_score': 0,
            'chordino_processing_time': 0,
            'chordino_accd_score': 0,
            'chordino_rccd_score': 0,
            'chordino_acc_score': 0,
            'atc_score_difference': 0,
            'rccd_score_difference': 0
        }


def process_batch_parallel(midi_files: List[str], dataset_name: str, num_workers: int = 32) -> List[Dict]:
    """Process multiple MIDI files in parallel."""
    print(f"Starting parallel processing of {len(midi_files)} files from {dataset_name} with {num_workers} workers", file=sys.stderr)
    logger.info(f"Starting parallel processing of {len(midi_files)} files from {dataset_name} with {num_workers} workers")
    
    start_time = time.time()
    results = []
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        future_to_file = {executor.submit(analyze_atc_for_file, midi_file, dataset_name): midi_file 
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
                    'total_processing_time': 0,
                    'pychord_atc_score': 0,
                    'pychord_processing_time': 0,
                    'pychord_accd_score': 0,
                    'pychord_rccd_score': 0,
                    'pychord_acc_score': 0,
                    'chordino_atc_score': 0,
                    'chordino_processing_time': 0,
                    'chordino_accd_score': 0,
                    'chordino_rccd_score': 0,
                    'chordino_acc_score': 0,
                    'atc_score_difference': 0,
                    'rccd_score_difference': 0
                })
    
    total_time = time.time() - start_time
    completion_msg = f"Completed processing {len(midi_files)} files in {total_time:.2f}s ({len(midi_files)/total_time:.2f} files/sec)"
    print(completion_msg, file=sys.stderr)
    logger.info(completion_msg)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Analyze ATC metrics using both methods')
    parser.add_argument('--dataset', type=str, help='Specific dataset to analyze')
    parser.add_argument('--output-dir', type=str, default='./atc_results', 
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
    
    # Get SLURM job ID if available
    job_id = os.environ.get('SLURM_JOB_ID', 'Unknown')
    
    for dataset_name in available_datasets:
        # Skip if specific dataset requested and this isn't it
        if args.dataset and dataset_name != args.dataset:
            continue
        
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Analyzing ATC for dataset: {dataset_name}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing ATC for dataset: {dataset_name}")
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
        dataset_start_time = time.time()
        dataset_results = process_batch_parallel(midi_files, dataset_name, args.num_workers)
        
        # Save dataset results
        if dataset_results:
            df = pd.DataFrame(dataset_results)
            output_file = os.path.join(args.output_dir, f"{dataset_name}_atc_analysis.csv")
            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(dataset_results)} results to {output_file}")
            
            all_results.extend(dataset_results)
            
            # Calculate dataset statistics
            dataset_time = time.time() - dataset_start_time
            dataset_time_formatted = f"{int(dataset_time//3600):02d}:{int((dataset_time%3600)//60):02d}:{int(dataset_time%60):02d}"
            
            if 'pychord_atc_score' in df.columns:
                pychord_avg = df['pychord_atc_score'].mean()
                chordino_avg = df['chordino_atc_score'].mean()
                diff_avg = df['atc_score_difference'].mean()
                
                
                print(f"Dataset {dataset_name} completed in {dataset_time_formatted}", file=sys.stderr)
                print(f"Average PYCHORD ATC Score: {pychord_avg:.3f}", file=sys.stderr)
                print(f"Average CHORDINO ATC Score: {chordino_avg:.3f}", file=sys.stderr)
                print(f"Average ATC Score Difference: {diff_avg:.3f}", file=sys.stderr)
    
    # Save combined results
    if all_results:
        combined_df = pd.DataFrame(all_results)
        combined_file = os.path.join(args.output_dir, "all_atc_analysis_results.csv")
        
        # Check if file exists and append instead of overwrite
        if os.path.exists(combined_file):
            existing_df = pd.read_csv(combined_file)
            combined_df = pd.concat([existing_df, combined_df], ignore_index=True)
            logger.info(f"Appended {len(all_results)} new results to existing file")
        else:
            logger.info(f"Created new combined results file")
            
        combined_df.to_csv(combined_file, index=False)
        logger.info(f"Saved combined results to {combined_file}")
        
        # Print summary statistics
        summary_msg = f"\n{'='*60}\nATC ANALYSIS SUMMARY\n{'='*60}\nTotal files analyzed: {len(all_results)}"
        print(summary_msg, file=sys.stderr)
        logger.info(f"\n{'='*60}")
        logger.info("ATC ANALYSIS SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total files analyzed: {len(all_results)}")
        
        if 'pychord_atc_score' in combined_df.columns:
            pychord_avg = combined_df['pychord_atc_score'].mean()
            chordino_avg = combined_df['chordino_atc_score'].mean()
            diff_avg = combined_df['atc_score_difference'].mean()
            
            print(f"Average PYCHORD ATC Score: {pychord_avg:.3f}", file=sys.stderr)
            print(f"Average CHORDINO ATC Score: {chordino_avg:.3f}", file=sys.stderr)
            print(f"Average ATC Score Difference: {diff_avg:.3f}", file=sys.stderr)
            
            logger.info(f"Average PYCHORD ATC Score: {pychord_avg:.3f}")
            logger.info(f"Average CHORDINO ATC Score: {chordino_avg:.3f}")
            logger.info(f"Average ATC Score Difference: {diff_avg:.3f}")


if __name__ == "__main__":
    main() 