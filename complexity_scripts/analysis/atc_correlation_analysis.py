#!/usr/bin/env python3
"""
ATC Correlation Analysis Script
Creates metrics vs models correlation matrix for ATC scores (POP909 dataset only)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
from scipy.stats import spearmanr

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

def load_and_merge_atc_data():
    """Load and merge ATC data with complexity and F-measure data for POP909."""
    print("🎯 LOADING AND MERGING ATC DATA (POP909)")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Load ATC data
    atc_file = project_root / "complexity_scripts/compute/atc_results/pop909_atc_analysis.csv"
    atc_df = pd.read_csv(atc_file)
    print(f"✅ Loaded {len(atc_df)} ATC records")
    
    # Load complexity data
    complexity_file = project_root / "complexity_scripts/compute/raw_data/all_complexity_results.csv"
    complexity_df = pd.read_csv(complexity_file)
    complexity_df = complexity_df[complexity_df['dataset_name'] == 'pop909'].copy()
    print(f"✅ Loaded {len(complexity_df)} POP909 complexity records")
    
    # Load F-measure data
    fmeasure_file = project_root / "data/dataframe.csv"
    fmeasure_df = pd.read_csv(fmeasure_file)
    fmeasure_df = fmeasure_df[fmeasure_df['dataset_name'] == 'POP909'].copy()
    fmeasure_df['midi_filename'] = fmeasure_df['midi_filename'].str.replace('.wav', '.mid')
    fmeasure_df['dataset_name'] = 'pop909'  # Standardize dataset name
    print(f"✅ Loaded {len(fmeasure_df)} POP909 F-measure records")
    
    # First merge ATC and complexity data (both have .mid files)
    atc_complexity_df = pd.merge(atc_df, complexity_df, on=['dataset_name', 'midi_filename'], how='inner')
    print(f"✅ Merged ATC + complexity: {len(atc_complexity_df)} records")
    
    # Now merge with F-measure data
    atc_merged_df = pd.merge(atc_complexity_df, fmeasure_df, on=['dataset_name', 'midi_filename'], how='inner')
    print(f"✅ Merged with F-measure data: {len(atc_merged_df)} records")
    
    if len(atc_merged_df) == 0:
        print("❌ No matching records found!")
        return None
    
    # Clean data
    initial_count = len(atc_merged_df)
    atc_merged_df = atc_merged_df[atc_merged_df['max_polyphony'] > 0].copy()
    print(f"✅ After removing zero-polyphony: {initial_count} → {len(atc_merged_df)} records")
    
    # Print final summary
    print(f"\n📊 Final ATC Data Summary:")
    print(f"Models: {sorted(atc_merged_df['model_name'].unique())}")
    
    model_counts = atc_merged_df['model_name'].value_counts()
    print(f"\n🤖 Model breakdown:")
    for model, count in model_counts.items():
        print(f"  {model}: {count}")
    
    # Check ATC score availability
    atc_metrics = ['pychord_atc_score', 'chordino_atc_score']
    print(f"\n📈 ATC Score Summary:")
    for metric in atc_metrics:
        valid_scores = atc_merged_df[metric].dropna()
        print(f"  {metric}: {len(valid_scores)} valid scores (range: {valid_scores.min():.3f} - {valid_scores.max():.3f})")
    
    return atc_merged_df

def create_atc_correlation_matrices(df, output_dir):
    """Create correlation matrices for ATC scores vs complexity metrics."""
    print("\n📊 CREATING ATC CORRELATION MATRICES")
    print("=" * 60)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    atc_metrics = ['pychord_atc_score', 'chordino_atc_score']
    
    # Create output directory
    atc_dir = output_dir / "atc_correlations"
    atc_dir.mkdir(exist_ok=True)
    
    # 1. Overall ATC correlation matrix (all models combined)
    print("Creating overall ATC correlation matrix...")
    create_atc_metrics_matrix(df, available_metrics, atc_metrics,
                              title="Complexity Metrics vs ATC Scores\n(POP909 Dataset - All Models Combined)",
                              filename=atc_dir / "atc_metrics_vs_scores_all_models.png")
    
    # 2. Per-model ATC correlation matrices
    print("Creating model-specific ATC correlation matrices...")
    models = df['model_name'].unique()
    for model in models:
        model_data = df[df['model_name'] == model]
        if len(model_data) >= 10:
            create_atc_metrics_matrix(model_data, available_metrics, atc_metrics,
                                      title=f"Complexity Metrics vs ATC Scores\n{model} Model (POP909)",
                                      filename=atc_dir / f"atc_metrics_vs_scores_{model.replace(' ', '_').replace('/', '_')}.png")
            print(f"   ✅ {model}: {len(model_data)} samples")
        else:
            print(f"   ⚠️ {model}: Only {len(model_data)} samples - skipped")

def create_atc_metrics_matrix(df, complexity_metrics, atc_metrics, title, filename):
    """Create correlation matrix with complexity metrics vs ATC scores."""
    # Calculate correlations between each complexity metric and each ATC score
    correlation_matrix = pd.DataFrame(index=complexity_metrics, columns=atc_metrics, dtype=float)
    
    for metric in complexity_metrics:
        for atc_metric in atc_metrics:
            valid_data = df[[metric, atc_metric]].dropna()
            if len(valid_data) >= 3:
                corr, _ = spearmanr(valid_data[metric], valid_data[atc_metric])
                correlation_matrix.loc[metric, atc_metric] = float(corr)
            else:
                correlation_matrix.loc[metric, atc_metric] = np.nan
    
    # Create visualization
    plt.figure(figsize=(12, 16))
    
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
    plt.xlabel('ATC Scores', fontsize=12)
    plt.ylabel('Complexity Metrics', fontsize=12)
    plt.xticks(rotation=0)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return correlation_matrix

def create_atc_vs_fmeasure_comparison(df, output_dir):
    """Create comparison between ATC scores and F-measure correlations."""
    print("\n📊 CREATING ATC vs F-MEASURE COMPARISON")
    print("=" * 60)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    atc_metrics = ['pychord_atc_score', 'chordino_atc_score']
    
    # Create output directory
    comparison_dir = output_dir / "atc_comparisons"
    comparison_dir.mkdir(exist_ok=True)
    
    # Calculate correlations for each metric
    correlations = []
    for metric in available_metrics:
        # F-measure correlation
        fmeasure_data = df[[metric, 'f_measure']].dropna()
        if len(fmeasure_data) >= 3:
            fmeasure_corr, _ = spearmanr(fmeasure_data[metric], fmeasure_data['f_measure'])
        else:
            fmeasure_corr = np.nan
        
        # ATC correlations
        atc_corrs = {}
        for atc_metric in atc_metrics:
            atc_data = df[[metric, atc_metric]].dropna()
            if len(atc_data) >= 3:
                atc_corr, _ = spearmanr(atc_data[metric], atc_data[atc_metric])
                atc_corrs[atc_metric] = atc_corr
            else:
                atc_corrs[atc_metric] = np.nan
        
        correlations.append({
            'metric': metric,
            'f_measure_correlation': fmeasure_corr,
            'pychord_atc_correlation': atc_corrs['pychord_atc_score'],
            'chordino_atc_correlation': atc_corrs['chordino_atc_score']
        })
    
    corr_df = pd.DataFrame(correlations)
    
    # Create comparison plot
    plt.figure(figsize=(14, 10))
    
    # Plot F-measure vs ATC correlations
    plt.subplot(2, 2, 1)
    plt.scatter(corr_df['f_measure_correlation'], corr_df['pychord_atc_correlation'], alpha=0.7, s=50)
    plt.xlabel('F-measure Correlation')
    plt.ylabel('Pychord ATC Correlation')
    plt.title('F-measure vs Pychord ATC Correlations')
    plt.plot([-1, 1], [-1, 1], 'r--', alpha=0.5)
    
    # Add correlation coefficient
    valid_data = corr_df[['f_measure_correlation', 'pychord_atc_correlation']].dropna()
    if len(valid_data) > 0:
        corr, _ = spearmanr(valid_data['f_measure_correlation'], valid_data['pychord_atc_correlation'])
        plt.text(0.05, 0.95, f'ρ = {corr:.3f}', transform=plt.gca().transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.subplot(2, 2, 2)
    plt.scatter(corr_df['f_measure_correlation'], corr_df['chordino_atc_correlation'], alpha=0.7, s=50)
    plt.xlabel('F-measure Correlation')
    plt.ylabel('Chordino ATC Correlation')
    plt.title('F-measure vs Chordino ATC Correlations')
    plt.plot([-1, 1], [-1, 1], 'r--', alpha=0.5)
    
    # Add correlation coefficient
    valid_data = corr_df[['f_measure_correlation', 'chordino_atc_correlation']].dropna()
    if len(valid_data) > 0:
        corr, _ = spearmanr(valid_data['f_measure_correlation'], valid_data['chordino_atc_correlation'])
        plt.text(0.05, 0.95, f'ρ = {corr:.3f}', transform=plt.gca().transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Top correlations comparison
    plt.subplot(2, 2, 3)
    top_metrics = corr_df.reindex(corr_df['f_measure_correlation'].abs().nlargest(10).index)['metric']
    f_measure_corrs = [corr_df[corr_df['metric'] == m]['f_measure_correlation'].iloc[0] for m in top_metrics]
    pychord_corrs = [corr_df[corr_df['metric'] == m]['pychord_atc_correlation'].iloc[0] for m in top_metrics]
    
    x = np.arange(len(top_metrics))
    width = 0.35
    
    plt.bar(x - width/2, f_measure_corrs, width, label='F-measure', alpha=0.8)
    plt.bar(x + width/2, pychord_corrs, width, label='Pychord ATC', alpha=0.8)
    
    plt.xlabel('Complexity Metrics')
    plt.ylabel('Correlation with F-measure/ATC')
    plt.title('Top 10 Metrics: F-measure vs Pychord ATC Correlations')
    plt.xticks(x, [m[:15] + '...' if len(m) > 15 else m for m in top_metrics], rotation=45, ha='right')
    plt.legend()
    
    plt.subplot(2, 2, 4)
    chordino_corrs = [corr_df[corr_df['metric'] == m]['chordino_atc_correlation'].iloc[0] for m in top_metrics]
    
    plt.bar(x - width/2, f_measure_corrs, width, label='F-measure', alpha=0.8)
    plt.bar(x + width/2, chordino_corrs, width, label='Chordino ATC', alpha=0.8)
    
    plt.xlabel('Complexity Metrics')
    plt.ylabel('Correlation with F-measure/ATC')
    plt.title('Top 10 Metrics: F-measure vs Chordino ATC Correlations')
    plt.xticks(x, [m[:15] + '...' if len(m) > 15 else m for m in top_metrics], rotation=45, ha='right')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(comparison_dir / "atc_vs_fmeasure_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save correlation data
    corr_df.to_csv(comparison_dir / "atc_correlation_comparison.csv", index=False)
    
    print(f"✅ ATC comparison analysis saved to {comparison_dir}")

def create_summary_statistics(df, output_dir):
    """Create summary statistics for ATC analysis."""
    print("\n📊 CREATING ATC SUMMARY STATISTICS")
    print("=" * 60)
    
    complexity_metrics = get_all_complexity_metrics()
    available_metrics = [m for m in complexity_metrics if m in df.columns]
    atc_metrics = ['pychord_atc_score', 'chordino_atc_score']
    
    # Create output directory
    stats_dir = output_dir / "atc_statistical_calculations"
    stats_dir.mkdir(exist_ok=True)
    
    # Calculate correlations for each metric
    correlations = []
    for metric in available_metrics:
        # F-measure correlation
        fmeasure_data = df[[metric, 'f_measure']].dropna()
        if len(fmeasure_data) >= 3:
            fmeasure_corr, fmeasure_p = spearmanr(fmeasure_data[metric], fmeasure_data['f_measure'])
        else:
            fmeasure_corr, fmeasure_p = np.nan, np.nan
        
        # ATC correlations
        atc_corrs = {}
        for atc_metric in atc_metrics:
            atc_data = df[[metric, atc_metric]].dropna()
            if len(atc_data) >= 3:
                atc_corr, atc_p = spearmanr(atc_data[metric], atc_data[atc_metric])
                atc_corrs[atc_metric] = atc_corr
                atc_corrs[f'{atc_metric}_p'] = atc_p
            else:
                atc_corrs[atc_metric] = np.nan
                atc_corrs[f'{atc_metric}_p'] = np.nan
        
        correlations.append({
            'metric': metric,
            'f_measure_correlation': fmeasure_corr,
            'f_measure_p_value': fmeasure_p,
            'pychord_atc_correlation': atc_corrs['pychord_atc_score'],
            'pychord_atc_p_value': atc_corrs['pychord_atc_score_p'],
            'chordino_atc_correlation': atc_corrs['chordino_atc_score'],
            'chordino_atc_p_value': atc_corrs['chordino_atc_score_p']
        })
    
    corr_df = pd.DataFrame(correlations).sort_values('f_measure_correlation', key=abs, ascending=False)
    corr_df.to_csv(stats_dir / "atc_correlations_summary.csv", index=False)
    
    # Save merged dataset
    df.to_csv(stats_dir / "atc_merged_data.csv", index=False)
    
    print(f"✅ ATC summary statistics saved to {stats_dir}")
    print(f"📊 Top 5 F-measure correlations:")
    for _, row in corr_df.head(5).iterrows():
        print(f"  {row['metric']}: ρ = {row['f_measure_correlation']:.3f} (p = {row['f_measure_p_value']:.3f})")
    
    print(f"📊 Top 5 Pychord ATC correlations:")
    pychord_sorted = corr_df.sort_values('pychord_atc_correlation', key=abs, ascending=False)
    for _, row in pychord_sorted.head(5).iterrows():
        print(f"  {row['metric']}: ρ = {row['pychord_atc_correlation']:.3f} (p = {row['pychord_atc_p_value']:.3f})")

def main():
    """Main ATC analysis function."""
    print("🎵 ATC CORRELATION ANALYSIS (POP909)")
    print("=" * 80)
    
    # Setup
    setup_plotting()
    
    # Load and merge ATC data
    atc_df = load_and_merge_atc_data()
    if atc_df is None:
        return
    
    # Create output directory structure
    script_dir = Path(__file__).parent
    output_dir = script_dir / "plots"
    output_dir.mkdir(exist_ok=True)
    
    # Run ATC analyses
    create_atc_correlation_matrices(atc_df, output_dir)
    create_atc_vs_fmeasure_comparison(atc_df, output_dir)
    create_summary_statistics(atc_df, output_dir)
    
    print(f"\n🎉 ATC ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📁 Results saved to: {output_dir}")
    print(f"📊 Total records analyzed: {len(atc_df)}")
    print(f"🤖 Models: {len(atc_df['model_name'].unique())}")
    print(f"📋 Complexity metrics: {len(get_all_complexity_metrics())}")

if __name__ == "__main__":
    main()
