"""
ATC (Automatic Transcription Complexity) Wrapper

This module provides an interface to the ATC harmony analysis tool
using the lacimarsik/harmony-analyser Java application for chord progression analysis.
"""

import os
import sys
import time
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)

# Path to the ATC submodule
ATC_DIR = os.path.join(os.path.dirname(__file__), 'atc')

def calculate_atc_metrics(midi_file_path, use_preprocessor_data=None):
    """
    Calculate ATC (Automatic Transcription Complexity) metrics for a MIDI file.
    
    Args:
        midi_file_path: Path to MIDI file
        use_preprocessor_data: Optional preprocessed data (for future use)
        
    Returns:
        Dictionary with ATC complexity metrics
    """
    start_time = time.time()
    
    if not os.path.exists(midi_file_path):
        return {
            'atc_score': 0.0,
            'processing_time': 0.0,
            'error': f'File not found: {midi_file_path}'
        }
    
    try:
        # Change to ATC directory for proper execution
        old_cwd = os.getcwd()
        os.chdir(ATC_DIR)
        
        try:
            # Check if harmony-analyser JAR exists
            jar_path = os.path.join('harmony-analyser', 'target', 'ha-script-1.2-beta.jar')
            if not os.path.exists(jar_path):
                return {
                    'atc_score': 0.0,
                    'processing_time': time.time() - start_time,
                    'error': f'Harmony analyser JAR not found at {jar_path}. The harmony analyzer needs to be built first.'
                }
            
            # Use get_atc_score.py script
            cmd = [sys.executable, 'get_atc_score.py', midi_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse ATC score from output
            output = result.stdout
            atc_score = None
            
            if 'ATC Score for' in output:
                # Extract score from output line like "ATC Score for 'file.mid': 4.123"
                for line in output.splitlines():
                    if 'ATC Score for' in line and ':' in line:
                        try:
                            score_str = line.split(':')[-1].strip()
                            atc_score = float(score_str)
                            break
                        except (ValueError, IndexError):
                            continue
            
            if atc_score is None:
                return {
                    'atc_score': 0.0,
                    'processing_time': time.time() - start_time,
                    'error': 'Could not parse ATC score from output'
                }
            
            return {
                'atc_score': atc_score,
                'processing_time': time.time() - start_time,
                'error': None,
                'method': 'java_harmony_analyser',
                'analysis_details': {
                    'harmony_analyser_version': '1.2-beta',
                    'analysis_type': 'chord_analyser:average_chord_complexity_distance'
                }
            }
            
        finally:
            # Always restore original directory
            os.chdir(old_cwd)
    
    except subprocess.CalledProcessError as e:
        error_msg = f"ATC tool execution failed: {e.stderr.strip() if e.stderr else str(e)}"
        return {
            'atc_score': 0.0,
            'processing_time': time.time() - start_time,
            'error': error_msg
        }
    except Exception as e:
        return {
            'atc_score': 0.0,
            'processing_time': time.time() - start_time,
            'error': f'Unexpected error: {str(e)}'
        }


def integrate_with_existing_metrics(midi_file_path):
    """
    Run all complexity metrics (entropy, polyphony, ATC) for a MIDI file.
    
    Args:
        midi_file_path: Path to MIDI file
        
    Returns:
        Dictionary with all complexity metrics
    """
    results = {
        'midi_filename': os.path.basename(midi_file_path),
        'file_path': midi_file_path
    }
    
    # Calculate ATC
    try:
        atc_results = calculate_atc_metrics(midi_file_path)
        results['atc'] = atc_results
    except Exception as e:
        results['atc'] = {'error': str(e), 'atc_score': 0.0}
    
    # Calculate Entropy
    try:
        sys.path.append(os.path.dirname(__file__))
        from entropy import main as entropy_main
        entropy_results = entropy_main(midi_file_path)
        results['entropy'] = entropy_results if entropy_results else {'error': 'Entropy analysis failed'}
    except Exception as e:
        results['entropy'] = {'error': str(e)}
    
    # Calculate Polyphony
    try:
        from polyphony import main as polyphony_main
        polyphony_results = polyphony_main(midi_file_path)
        results['polyphony'] = polyphony_results if polyphony_results else {'error': 'Polyphony analysis failed'}
    except Exception as e:
        results['polyphony'] = {'error': str(e)}
    
    return results


def main():
    """Command-line interface for ATC analysis."""
    if len(sys.argv) < 2:
        print("Usage: python atc_wrapper.py <midi_file>")
        print("Example: python atc_wrapper.py /path/to/file.mid")
        sys.exit(1)
    
    midi_file = sys.argv[1]
    
    print(f"=== ATC Analysis ===")
    print(f"File: {midi_file}")
    print()
    
    # Run ATC analysis
    results = calculate_atc_metrics(midi_file)
    
    if results.get('error'):
        print(f"Error: {results['error']}")
        sys.exit(1)
    
    print("Results:")
    print(f"  ATC Score: {results['atc_score']:.3f}")
    print(f"  Processing Time: {results['processing_time']:.3f}s")
    print(f"  Method: {results.get('method', 'Unknown')}")
    
    if 'analysis_details' in results:
        print("  Analysis Details:")
        for key, value in results['analysis_details'].items():
            print(f"    {key}: {value}")


if __name__ == "__main__":
    main()