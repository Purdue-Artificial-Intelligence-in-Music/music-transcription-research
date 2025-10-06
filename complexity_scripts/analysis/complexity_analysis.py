#!/usr/bin/env python3
"""
Final Music Complexity Analysis Script
Clean, comprehensive analysis with proper correlation matrices and all visualizations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
from scipy.stats import spearmanr
import itertools

warnings.filterwarnings('ignore')

def setup_plotting():
    """Configure matplotlib for consistent plotting style."""
    plt.style.use('default')
    sns.set_palette("husl")
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['xtick.labelsize'] = 8
    plt.rcParams['ytick.labelsize'] = 8

def get_all_complexity_metrics():
    """Define and return all 18 complexity metrics."""
    return [
        'tonal_certainty_piece',
        'pitch_class_entropy_piece', 
        'melodic_interval_entropy_piece',
        'ioi_entropy_piece',
        'max_polyphony',
        'avg_polyphony',
        'std_polyphony', 
        'polyphony_density',
        'seg_max_poly',
        'seg_avg_poly', 
        'seg_poly_density',
        'seg_poly_std',
        'seg_mean_max_polyphony_measures',
        'seg_std_max_polyphony_measures',
        'seg_mean_avg_polyphony_measures',
        'seg_std_avg_polyphony_measures',
        'seg_mean_polyphony_density_measures',
        'seg_std_polyphony_density_measures'
    ]

def load_and_merge_data():
    """Load and merge data."""
    print("🎯 LOADING AND MERGING DATA")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Load complexity data
    complexity_file = project_root / "complexity_scripts/compute/raw_data/all_complexity_results.csv"
    complexity_df = pd.read_csv(complexity_file)
    print(f"✅ Loaded {len(complexity_df)} complexity records")
    
    # Load F-measure data
    fmeasure_file = project_root / "data/dataframe.csv"
    fmeasure_df = pd.read_csv(fmeasure_file)
    print(f"✅ Loaded {len(fmeasure_df)} F-measure records")
    
    # Exclude XMIDI dataset as requested
    complexity_df = complexity_df[complexity_df['dataset_name'] != 'xmidi'].copy()
    print(f"✅ Excluded XMIDI dataset, {len(complexity_df)} complexity records remaining")
    
    # Map dataset names for consistency
    dataset_mapping = {
        'MSMD': 'msmd',
        'BiMMuDa': 'bimmuda', 
        'POP909': 'pop909',
        'AAM': 'aam',
        'Slakh 2100 Redux': 'slakh2100',
        'Maestro': 'maestro',
        'NESMDB': 'nesmdb'
    }
    
    fmeasure_df['dataset_name'] = fmeasure_df['dataset_name'].map(dataset_mapping).fillna(fmeasure_df['dataset_name'])
    fmeasure_df['midi_filename'] = fmeasure_df['midi_filename'].str.replace('.wav', '.mid')
    
    # Merge datasets
    merged_df = pd.merge(fmeasure_df, complexity_df, on=['dataset_name', 'midi_filename'], how='inner')
    print(f"✅ Direct merge: {len(merged_df)} matches")
    
    if len(merged_df) == 0:
        print("❌ No matching records found!")
        return None
    
    # Clean data
    initial_count = len(merged_df)
    merged_df = merged_df[merged_df['max_polyphony'] > 0].copy()
    print(f"✅ After removing zero-polyphony: {initial_count} → {len(merged_df)} records")
    
    # Print final summary
    print(f"\n📊 Final Data Summary:")
    print(f"Datasets: {sorted(merged_df['dataset_name'].unique())}")
    print(f"Models: {sorted(merged_df['model_name'].unique())}")
    
    dataset_counts = merged_df['dataset_name'].value_counts()
    model_counts = merged_df['model_name'].value_counts()
    
    print(f"\n📈 Dataset breakdown:")
    for dataset, count in dataset_counts.items():
        print(f"  {dataset}: {count}")
    
    print(f"\n🤖 Model breakdown:")
    for model, count in model_counts.items():
        print(f"  {model}: {count}")
    
    return merged_df

def create_metrics_vs_models_correlation_matrix(df, output_dir):
    """Create the key correlation matrix: metrics (Y) vs model F-measures (X)."""
    print("\n📊 CREATING METRICS VS MODELS CORRELATION MATRIX")
    print("=" * 70)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    models = df['model_name'].unique()
    
    # Create output directory
    main_dir = output_dir / "correlation_matrices"
    main_dir.mkdir(exist_ok=True)
    
    # 1. All datasets combined
    print("Creating overall metrics vs models correlation matrix...")
    create_metrics_models_matrix(df, available_metrics, models, 
                                title="Complexity Metrics vs Model F-Measures\n(All Datasets Combined)",
                                filename=main_dir / "metrics_vs_models_all_datasets.png")
    
    # 2. Per dataset
    print("Creating dataset-specific metrics vs models correlation matrices...")
    datasets = df['dataset_name'].unique()
    for dataset in datasets:
        dataset_data = df[df['dataset_name'] == dataset]
        if len(dataset_data) >= 50:
            create_metrics_models_matrix(dataset_data, available_metrics, models,
                                        title=f"Complexity Metrics vs Model F-Measures\n{dataset.upper()} Dataset",
                                        filename=main_dir / f"metrics_vs_models_{dataset}.png")
            print(f"   ✅ {dataset}: {len(dataset_data)} samples")
        else:
            print(f"   ⚠️ {dataset}: Only {len(dataset_data)} samples - skipped")

def create_metrics_models_matrix(df, metrics, models, title, filename):
    """Create correlation matrix with metrics on Y-axis and models on X-axis."""
    # Calculate correlations between each metric and each model's F-measure
    correlation_matrix = pd.DataFrame(index=metrics, columns=models, dtype=float)
    
    for metric in metrics:
        for model in models:
            model_data = df[df['model_name'] == model]
            if len(model_data) >= 5:
                valid_data = model_data[[metric, 'f_measure']].dropna()
                if len(valid_data) >= 3:
                    corr, _ = spearmanr(valid_data[metric], valid_data['f_measure'])
                    correlation_matrix.loc[metric, model] = float(corr)
                else:
                    correlation_matrix.loc[metric, model] = np.nan
            else:
                correlation_matrix.loc[metric, model] = np.nan
    
    # Create visualization
    plt.figure(figsize=(16, 12))
    
    # Create heatmap
    sns.heatmap(correlation_matrix, 
                annot=True, 
                cmap='RdBu_r', 
                center=0, 
                square=False, 
                fmt='.3f',
                cbar_kws={'shrink': 0.8},
                linewidths=0.5)
    
    plt.title(title, fontsize=16, pad=20)
    plt.xlabel('Transcription Models', fontsize=12)
    plt.ylabel('Complexity Metrics', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return correlation_matrix

def create_metrics_correlation_matrix(df, output_dir):
    """Create correlation matrix between complexity metrics only."""
    print("\n📊 CREATING METRICS CORRELATION MATRIX")
    print("=" * 60)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    
    # Create output directory
    metrics_dir = output_dir / "metrics_correlations"
    metrics_dir.mkdir(exist_ok=True)
    
    # Overall metrics correlation matrix
    print("Creating overall metrics correlation matrix...")
    create_metrics_only_matrix(df, available_metrics,
                               title="Complexity Metrics Intercorrelations\n(All Datasets Combined)",
                               filename=metrics_dir / "metrics_correlation_matrix.png")
    
    # Dataset-specific metrics correlations
    print("Creating dataset-specific metrics correlations...")
    datasets = df['dataset_name'].unique()
    for dataset in datasets:
        dataset_data = df[df['dataset_name'] == dataset]
        if len(dataset_data) >= 50:
            create_metrics_only_matrix(dataset_data, available_metrics,
                                       title=f"Complexity Metrics Intercorrelations\n{dataset.upper()} Dataset",
                                       filename=metrics_dir / f"metrics_correlation_{dataset}.png")
            print(f"   ✅ {dataset}: {len(dataset_data)} samples")
        else:
            print(f"   ⚠️ {dataset}: Only {len(dataset_data)} samples - skipped")

def create_metrics_only_matrix(df, metrics, title, filename):
    """Create correlation matrix for metrics only."""
    correlation_data = df[metrics].corr(method='spearman')
    
    plt.figure(figsize=(16, 14))
    
    # Create mask for upper triangle
    mask = np.triu(np.ones_like(correlation_data, dtype=bool))
    
    # Create heatmap
    sns.heatmap(correlation_data, 
                mask=mask,
                annot=True, 
                cmap='RdBu_r', 
                center=0, 
                square=True, 
                fmt='.3f',
                cbar_kws={'shrink': 0.8},
                linewidths=0.5)
    
    plt.title(title, fontsize=16, pad=20)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return correlation_data

def create_distribution_plots(df, output_dir):
    """Create distribution plots for each complexity metric."""
    print("\n📊 CREATING DISTRIBUTION PLOTS")
    print("=" * 60)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    
    # Create output directory
    dist_dir = output_dir / "distribution_plots"
    dist_dir.mkdir(exist_ok=True)
    
    datasets = df['dataset_name'].unique()
    
    # Create distribution plots for each metric
    for metric in available_metrics:
        print(f"   Creating distribution plot for {metric}...")
        
        plt.figure(figsize=(15, 10))
        
        # Overall distribution (subplot 1)
        plt.subplot(2, 2, 1)
        plt.hist(df[metric].dropna(), bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        plt.title(f'{metric} - All Datasets Combined')
        plt.xlabel(metric)
        plt.ylabel('Frequency')
        
        # Per-dataset distributions (subplot 2)
        plt.subplot(2, 2, 2) 
        for dataset in datasets:
            dataset_data = df[df['dataset_name'] == dataset][metric].dropna()
            if len(dataset_data) > 0:
                plt.hist(dataset_data, bins=30, alpha=0.6, label=dataset)
        plt.title(f'{metric} - By Dataset')
        plt.xlabel(metric)
        plt.ylabel('Frequency')
        plt.legend()
        
        # Box plot by dataset (subplot 3)
        plt.subplot(2, 2, 3)
        box_data = [df[df['dataset_name'] == dataset][metric].dropna() for dataset in datasets]
        box_labels = [f"{dataset}\n(n={len(data)})" for dataset, data in zip(datasets, box_data)]
        plt.boxplot([data for data in box_data if len(data) > 0], 
                    labels=[label for data, label in zip(box_data, box_labels) if len(data) > 0])
        plt.title(f'{metric} - Box Plot by Dataset')
        plt.xticks(rotation=45)
        plt.ylabel(metric)
        
        # Box plot by model (subplot 4)
        plt.subplot(2, 2, 4)
        models = df['model_name'].unique()[:8]  # Limit to first 8 models for readability
        box_data_models = [df[df['model_name'] == model][metric].dropna() for model in models]
        box_labels_models = [f"{model[:10]}\n(n={len(data)})" for model, data in zip(models, box_data_models)]
        plt.boxplot([data for data in box_data_models if len(data) > 0],
                    labels=[label for data, label in zip(box_data_models, box_labels_models) if len(data) > 0])
        plt.title(f'{metric} - Box Plot by Model (Top 8)')
        plt.xticks(rotation=45, fontsize=8)
        plt.ylabel(metric)
        
        plt.tight_layout()
        safe_metric_name = metric.replace('/', '_').replace(' ', '_')
        plt.savefig(dist_dir / f"distribution_{safe_metric_name}.png", dpi=300, bbox_inches='tight')
        plt.close()

def create_scatter_plots(df, output_dir):
    """Create scatter plots of metrics vs F-measure."""
    print("\n📊 CREATING SCATTER PLOTS")
    print("=" * 60)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    
    # Create output directory
    scatter_dir = output_dir / "scatter_plots"
    scatter_dir.mkdir(exist_ok=True)
    
    datasets = df['dataset_name'].unique()
    
    # Create scatter plots for each metric vs F-measure
    for metric in available_metrics:
        print(f"   Creating scatter plot for {metric} vs F-measure...")
        
        plt.figure(figsize=(16, 12))
        
        # Overall scatter plot (subplot 1)
        plt.subplot(2, 3, 1)
        plt.scatter(df[metric], df['f_measure'], alpha=0.5, s=20)
        plt.xlabel(metric)
        plt.ylabel('F-measure')
        plt.title(f'{metric} vs F-measure\nAll Datasets')
        
        # Add correlation coefficient
        corr, p_val = spearmanr(df[metric].dropna(), df.loc[df[metric].notna(), 'f_measure'])
        plt.text(0.05, 0.95, f'ρ = {corr:.3f}\np = {p_val:.3f}', 
                transform=plt.gca().transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Dataset-specific scatter plots
        for i, dataset in enumerate(datasets[:5]):  # Limit to 5 datasets for layout
            plt.subplot(2, 3, i+2)
            dataset_data = df[df['dataset_name'] == dataset]
            
            if len(dataset_data) > 5:
                plt.scatter(dataset_data[metric], dataset_data['f_measure'], alpha=0.6, s=25)
                plt.xlabel(metric)
                plt.ylabel('F-measure')
                plt.title(f'{dataset.upper()}\n(n={len(dataset_data)})')
                
                # Add correlation coefficient
                if len(dataset_data) > 2:
                    corr, p_val = spearmanr(dataset_data[metric].dropna(), 
                                          dataset_data.loc[dataset_data[metric].notna(), 'f_measure'])
                    plt.text(0.05, 0.95, f'ρ = {corr:.3f}', 
                            transform=plt.gca().transAxes, verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        safe_metric_name = metric.replace('/', '_').replace(' ', '_')
        plt.savefig(scatter_dir / f"scatter_{safe_metric_name}_vs_fmeasure.png", dpi=300, bbox_inches='tight')
        plt.close()

def create_summary_statistics(df, output_dir):
    """Create comprehensive summary statistics."""
    print("\n📊 CREATING SUMMARY STATISTICS")
    print("=" * 60)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    
    # Create output directory
    stats_dir = output_dir / "statistical_calculations"
    stats_dir.mkdir(exist_ok=True)
    
    # Overall correlations
    correlations = []
    for metric in available_metrics:
        valid_data = df[[metric, 'f_measure']].dropna()
        if len(valid_data) > 10:
            corr, p_val = spearmanr(valid_data[metric], valid_data['f_measure'])
            correlations.append({
                'metric': metric,
                'correlation': corr,
                'p_value': p_val,
                'n_samples': len(valid_data)
            })
    
    overall_corr_df = pd.DataFrame(correlations).sort_values('correlation', key=abs, ascending=False)
    overall_corr_df.to_csv(stats_dir / "overall_correlations.csv", index=False)
    
    # Save merged dataset
    df.to_csv(stats_dir / "merged_complexity_fmeasure_data.csv", index=False)
    
    print(f"✅ Summary statistics saved to {stats_dir}")
    print(f"📊 Top 5 correlations with F-measure:")
    for _, row in overall_corr_df.head(5).iterrows():
        print(f"  {row['metric']}: ρ = {row['correlation']:.3f} (p = {row['p_value']:.3f})")

def main():
    """Main analysis function."""
    print("🎵 FINAL MUSIC COMPLEXITY ANALYSIS")
    print("=" * 80)
    
    # Setup
    setup_plotting()
    
    # Load and merge data
    merged_df = load_and_merge_data()
    if merged_df is None:
        return
    
    # Create output directory structure
    script_dir = Path(__file__).parent
    output_dir = script_dir / "plots"
    output_dir.mkdir(exist_ok=True)
    
    # Run all analyses
    create_metrics_vs_models_correlation_matrix(merged_df, output_dir)
    create_metrics_correlation_matrix(merged_df, output_dir)
    create_distribution_plots(merged_df, output_dir)
    create_scatter_plots(merged_df, output_dir)
    create_summary_statistics(merged_df, output_dir)
    
    print(f"\n🎉 FINAL ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📁 Results saved to: {output_dir}")
    print(f"📊 Total records analyzed: {len(merged_df)}")
    print(f"📈 Datasets: {len(merged_df['dataset_name'].unique())}")
    print(f"🤖 Models: {len(merged_df['model_name'].unique())}")
    print(f"📋 Complexity metrics: {len(get_all_complexity_metrics())}")

if __name__ == "__main__":
    main()
