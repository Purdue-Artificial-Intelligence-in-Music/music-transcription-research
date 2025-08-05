#!/usr/bin/env python3
"""
Dataset Manager for Music Complexity Analysis

This module provides a unified interface for accessing MIDI datasets
across different storage locations.
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DatasetInfo:
    """Dataset information container."""
    name: str
    path: str
    instrument: str
    audio_type: str
    count: int
    
    @property
    def is_midi_dataset(self) -> bool:
        """Check if this dataset contains MIDI files."""
        return self.audio_type.lower() in ['mid', 'midi']


class DatasetManager:
    """
    Dataset manager for music complexity analysis.
    
    Features:
    - Configuration-driven dataset discovery
    - Caching for performance
    - Multiple storage location support
    - Error handling and logging
    - Parallel file discovery
    """
    
    def __init__(self, 
                 config_file: str = "midi_datasets.json",
                 cache_dir: Optional[str] = None,
                 enable_cache: bool = True):
        """
        Initialize the dataset manager.
        
        Args:
            config_file: Path to dataset configuration file
            cache_dir: Directory for caching files (optional)
            enable_cache: Whether to enable file caching
        """
        self.config_file = Path(config_file)
        self.enable_cache = enable_cache
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = f"/scratch/gilbreth/{os.getenv('USER', 'default')}/AIM/midi_cache"
        self.cache_dir = Path(cache_dir)
        
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load dataset configuration
        self.datasets = self._load_config()
        
        # Cache for file listings
        self._file_cache = {}
    
    def _load_config(self) -> List[DatasetInfo]:
        """Load dataset configuration from JSON file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Dataset config file not found: {self.config_file}")
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            
            datasets = []
            # Skip header row if present
            values = data.get('values', [])
            if values and isinstance(values[0], list) and values[0][0] == "Dataset Name":
                values = values[1:]
            
            for row in values:
                if len(row) >= 5:
                    name, path, instrument, audio_type, count = row[:5]
                    datasets.append(DatasetInfo(
                        name=name,
                        path=path,
                        instrument=instrument,
                        audio_type=audio_type,
                        count=int(count)
                    ))
            
            logger.info(f"Loaded {len(datasets)} datasets from config")
            return datasets
            
        except Exception as e:
            logger.error(f"Error loading dataset config: {e}")
            raise
    
    def get_datasets(self, midi_only: bool = True) -> List[DatasetInfo]:
        """
        Get list of available datasets.
        
        Args:
            midi_only: If True, return only MIDI datasets
            
        Returns:
            List of dataset information
        """
        if midi_only:
            return [ds for ds in self.datasets if ds.is_midi_dataset]
        return self.datasets
    
    def get_dataset(self, name: str) -> Optional[DatasetInfo]:
        """Get dataset information by name."""
        for dataset in self.datasets:
            if dataset.name.lower() == name.lower():
                return dataset
        return None
    
    def find_files(self, 
                   dataset_name: str, 
                   extensions: List[str] = None,
                   limit: Optional[int] = None,
                   use_cache: bool = True) -> List[Path]:
        """
        Find files in a dataset.
        
        Args:
            dataset_name: Name of the dataset
            extensions: File extensions to search for (default: ['.mid', '.midi'])
            limit: Maximum number of files to return
            use_cache: Whether to use cached results
            
        Returns:
            List of file paths
        """
        if extensions is None:
            extensions = ['.mid', '.midi']
        
        dataset = self.get_dataset(dataset_name)
        if not dataset:
            logger.error(f"Dataset '{dataset_name}' not found")
            return []
        
        # Check cache first
        cache_key = f"{dataset_name}_{','.join(extensions)}_{limit}"
        if use_cache and cache_key in self._file_cache:
            logger.debug(f"Using cached file list for {dataset_name}")
            return self._file_cache[cache_key]
        
        # Find files
        files = self._discover_files(dataset.path, extensions, limit)
        
        # Cache results
        if use_cache:
            self._file_cache[cache_key] = files
        
        logger.info(f"Found {len(files)} files in {dataset_name}")
        return files
    
    def _discover_files(self, 
                       dataset_path: str, 
                       extensions: List[str],
                       limit: Optional[int] = None) -> List[Path]:
        """Discover files in dataset directory."""
        files = []
        dataset_path = Path(dataset_path)
        
        if not dataset_path.exists():
            logger.warning(f"Dataset path does not exist: {dataset_path}")
            return files
        
        try:
            # Use os.walk for better performance on large directories
            for root, dirs, filenames in os.walk(dataset_path):
                for filename in filenames:
                    if any(filename.lower().endswith(ext.lower()) for ext in extensions):
                        files.append(Path(root) / filename)
                        
                        # Apply limit if specified
                        if limit and len(files) >= limit:
                            return files
            
        except Exception as e:
            logger.error(f"Error discovering files in {dataset_path}: {e}")
        
        return files
    
    def get_file_batch(self, 
                      dataset_name: str,
                      file_paths: List[Union[str, Path]],
                      use_cache: bool = True) -> Dict[str, Path]:
        """
        Get a batch of files, with optional caching.
        
        Args:
            dataset_name: Name of the dataset
            file_paths: List of file paths to retrieve
            use_cache: Whether to cache files locally
            
        Returns:
            Dictionary mapping original paths to accessible paths
        """
        results = {}
        
        if not self.enable_cache or not use_cache:
            # Direct access without caching
            for file_path in file_paths:
                path_obj = Path(file_path)
                if path_obj.exists():
                    results[str(file_path)] = path_obj
            return results
        
        # With caching
        dataset_cache = self.cache_dir / dataset_name
        dataset_cache.mkdir(exist_ok=True)
        
        for file_path in file_paths:
            original_path = Path(file_path)
            cached_path = dataset_cache / original_path.name
            
            # Check if already cached
            if cached_path.exists():
                results[str(file_path)] = cached_path
                continue
            
            # Copy to cache if original exists
            if original_path.exists():
                try:
                    shutil.copy2(original_path, cached_path)
                    results[str(file_path)] = cached_path
                    logger.debug(f"Cached file: {original_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to cache {original_path}: {e}")
                    results[str(file_path)] = original_path
            else:
                logger.warning(f"File not found: {original_path}")
        
        return results
    
    def get_dataset_stats(self) -> Dict[str, Dict]:
        """Get statistics for all datasets."""
        stats = {}
        
        for dataset in self.get_datasets():
            files = self.find_files(dataset.name)
            stats[dataset.name] = {
                'configured_count': dataset.count,
                'actual_count': len(files),
                'path': dataset.path,
                'instrument': dataset.instrument,
                'audio_type': dataset.audio_type
            }
        
        return stats
    
    def validate_datasets(self) -> Dict[str, bool]:
        """Validate that all configured datasets are accessible."""
        results = {}
        
        for dataset in self.datasets:
            path = Path(dataset.path)
            results[dataset.name] = path.exists() and path.is_dir()
            
            if not results[dataset.name]:
                logger.warning(f"Dataset path not accessible: {dataset.name} -> {path}")
        
        return results
    
    def clear_cache(self, dataset_name: Optional[str] = None):
        """
        Clear cached files.
        
        Args:
            dataset_name: Specific dataset to clear, or None for all
        """
        if not self.enable_cache:
            return
        
        if dataset_name:
            dataset_cache = self.cache_dir / dataset_name
            if dataset_cache.exists():
                shutil.rmtree(dataset_cache)
                logger.info(f"Cleared cache for {dataset_name}")
        else:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Cleared all cached files")
        
        # Clear memory cache
        self._file_cache.clear()


# Convenience functions for backward compatibility
def get_dataset_manager(config_file: str = "midi_datasets.json", 
                       cache_dir: Optional[str] = None) -> DatasetManager:
    """Get a dataset manager instance."""
    # Look for config file relative to this script
    if not os.path.isabs(config_file):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, '..', config_file)
    
    return DatasetManager(config_file=config_file, cache_dir=cache_dir)


def find_midi_files(dataset_name: str, limit: Optional[int] = None) -> List[Path]:
    """Convenience function to find MIDI files in a dataset."""
    manager = get_dataset_manager()
    return manager.find_files(dataset_name, limit=limit)


if __name__ == "__main__":
    # Example usage and testing
    try:
        manager = get_dataset_manager()
        
        # Print dataset statistics
        print("Dataset Statistics:")
        stats = manager.get_dataset_stats()
        for name, info in stats.items():
            print(f"  {name}: {info['actual_count']}/{info['configured_count']} files")
        
        # Validate datasets
        print("\nDataset Validation:")
        validation = manager.validate_datasets()
        for name, valid in validation.items():
            status = "✅" if valid else "❌"
            print(f"  {status} {name}")
        
        # Example: Get files from a dataset
        if stats:
            first_dataset = list(stats.keys())[0]
            print(f"\nExample files from {first_dataset}:")
            files = manager.find_files(first_dataset, limit=3)
            for file_path in files:
                print(f"  {file_path}")
                
    except Exception as e:
        print(f"Error: {e}")