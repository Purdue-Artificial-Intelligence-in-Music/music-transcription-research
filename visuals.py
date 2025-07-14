import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# Set style for better-looking plots
plt.style.use("seaborn-v0_8")
sns.set_palette("Set2")

# Load the data
print("Loading music results data...")
df = pd.read_pickle("./data/dataframe.pkl")
print(f"Loaded {len(df)} records")
print(f"Models: {df['model_name'].unique()}")
print(f"Data shape: {df.shape}")

# Create figure directory if it doesn't exist
import os

if not os.path.exists("figures"):
    os.makedirs("figures")

# Define consistent colors for models
models = df["model_name"].unique()
model_colors = dict(zip(models, sns.color_palette("Set2", len(models))))
print(f"Model colors: {model_colors}")

# ============================================================================
# IMAGE 1: CORE PERFORMANCE ANALYSIS
# ============================================================================
plt.figure(figsize=(16, 12))

# 1. Audio file length vs performance (colored by model)
plt.subplot(2, 3, 1)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.scatter(
        model_data["duration_seconds"],
        model_data["f_measure"],
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

    # Add trend line for each model
    if len(model_data) > 1:
        z = np.polyfit(model_data["duration_seconds"], model_data["f_measure"], 1)
        p = np.poly1d(z)
        plt.plot(
            model_data["duration_seconds"],
            p(model_data["duration_seconds"]),
            color=model_colors[model],
            linestyle="--",
            alpha=0.8,
            linewidth=2,
        )

plt.xlabel("Duration (seconds)", fontsize=12)
plt.ylabel("F-measure", fontsize=12)
plt.title("Audio File Length vs Performance", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 2. Precision vs Recall (colored by model)
plt.subplot(2, 3, 2)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.scatter(
        model_data["precision"],
        model_data["recall"],
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Precision", fontsize=12)
plt.ylabel("Recall", fontsize=12)
plt.title("Precision vs Recall by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)
# Add diagonal line for perfect precision-recall balance
max_val = max(df["precision"].max(), df["recall"].max())
plt.plot([0, max_val], [0, max_val], "k--", alpha=0.5, linewidth=1)

# 3. F-measure vs Overlap (colored by model)
plt.subplot(2, 3, 3)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.scatter(
        model_data["f_measure"],
        model_data["average_overlap_ratio"],
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

    # Add trend line for each model
    if len(model_data) > 1:
        z = np.polyfit(model_data["f_measure"], model_data["average_overlap_ratio"], 1)
        p = np.poly1d(z)
        plt.plot(
            model_data["f_measure"],
            p(model_data["f_measure"]),
            color=model_colors[model],
            linestyle="--",
            alpha=0.8,
            linewidth=2,
        )

plt.xlabel("F-measure", fontsize=12)
plt.ylabel("Average Overlap Ratio", fontsize=12)
plt.title("F-measure vs Overlap Ratio by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 4. Model Performance Comparison (Box plots)
plt.subplot(2, 3, 4)
df.boxplot(column="f_measure", by="model_name", ax=plt.gca())
plt.title("F-measure Distribution by Model", fontsize=14, fontweight="bold")
plt.xlabel("Model", fontsize=12)
plt.ylabel("F-measure", fontsize=12)
plt.xticks(rotation=45)
plt.suptitle("")  # Remove default title

# 5. Runtime vs Performance (colored by model)
plt.subplot(2, 3, 5)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.scatter(
        model_data["runtime"],
        model_data["f_measure"],
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Runtime (seconds)", fontsize=12)
plt.ylabel("F-measure", fontsize=12)
plt.title("Runtime vs Performance by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 6. Overall Performance Metrics Comparison
plt.subplot(2, 3, 6)
metrics = ["precision", "recall", "f_measure"]
x_pos = np.arange(len(metrics))
width = 0.25

for i, model in enumerate(models):
    model_data = df[df["model_name"] == model]
    means = [model_data[metric].mean() for metric in metrics]
    stds = [model_data[metric].std() for metric in metrics]

    plt.bar(
        x_pos + i * width,
        means,
        width,
        yerr=stds,
        capsize=5,
        alpha=0.8,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Metrics", fontsize=12)
plt.ylabel("Average Score", fontsize=12)
plt.title("Performance Metrics by Model", fontsize=14, fontweight="bold")
plt.xticks(x_pos + width, metrics)
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("figures/01_core_performance_analysis.png", dpi=300, bbox_inches="tight")
plt.show()

# ============================================================================
# IMAGE 2: ONSET vs OFFSET DETAILED ANALYSIS
# ============================================================================
plt.figure(figsize=(16, 12))

# 1. Onset vs Offset F-measure (colored by model)
plt.subplot(2, 3, 1)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.scatter(
        model_data["onset_f_measure"],
        model_data["offset_f_measure"],
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Onset F-measure", fontsize=12)
plt.ylabel("Offset F-measure", fontsize=12)
plt.title("Onset vs Offset F-measure by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)
# Add diagonal line
max_val = max(df["onset_f_measure"].max(), df["offset_f_measure"].max())
plt.plot(
    [0, max_val], [0, max_val], "k--", alpha=0.5, linewidth=1, label="Perfect Agreement"
)

# 2. Onset vs Offset Precision (colored by model)
plt.subplot(2, 3, 2)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.scatter(
        model_data["onset_precision"],
        model_data["offset_precision"],
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Onset Precision", fontsize=12)
plt.ylabel("Offset Precision", fontsize=12)
plt.title("Onset vs Offset Precision by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 3. Onset vs Offset Recall (colored by model)
plt.subplot(2, 3, 3)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.scatter(
        model_data["onset_recall"],
        model_data["offset_recall"],
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Onset Recall", fontsize=12)
plt.ylabel("Offset Recall", fontsize=12)
plt.title("Onset vs Offset Recall by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 4. Onset/Offset Performance Comparison
plt.subplot(2, 3, 4)
onset_metrics = ["onset_precision", "onset_recall", "onset_f_measure"]
offset_metrics = ["offset_precision", "offset_recall", "offset_f_measure"]
x_pos = np.arange(len(onset_metrics))
width = 0.35

for i, model in enumerate(models):
    model_data = df[df["model_name"] == model]
    onset_means = [model_data[metric].mean() for metric in onset_metrics]
    offset_means = [model_data[metric].mean() for metric in offset_metrics]

    plt.bar(
        x_pos - width / 2,
        onset_means,
        width,
        alpha=0.8,
        label=f"{model} Onset",
        color=model_colors[model],
    )
    plt.bar(
        x_pos + width / 2,
        offset_means,
        width,
        alpha=0.6,
        label=f"{model} Offset",
        color=model_colors[model],
        hatch="///",
    )

plt.xlabel("Metrics", fontsize=12)
plt.ylabel("Average Score", fontsize=12)
plt.title("Onset vs Offset Performance by Model", fontsize=14, fontweight="bold")
plt.xticks(x_pos, ["Precision", "Recall", "F-measure"])
plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
plt.grid(True, alpha=0.3)

# 5. Correlation heatmap for onset/offset metrics by model
plt.subplot(2, 3, 5)
onset_offset_cols = [
    "onset_precision",
    "onset_recall",
    "onset_f_measure",
    "offset_precision",
    "offset_recall",
    "offset_f_measure",
]
corr_matrix = df[onset_offset_cols].corr()
sns.heatmap(
    corr_matrix,
    annot=True,
    cmap="coolwarm",
    center=0,
    square=True,
    fmt=".3f",
    cbar_kws={"label": "Correlation"},
)
plt.title("Onset/Offset Correlation Matrix", fontsize=14, fontweight="bold")
plt.xticks(rotation=45)
plt.yticks(rotation=45)

# 6. Onset-Offset Performance Difference
plt.subplot(2, 3, 6)
df["onset_offset_diff"] = df["onset_f_measure"] - df["offset_f_measure"]
for model in models:
    model_data = df[df["model_name"] == model]
    plt.hist(
        model_data["onset_offset_diff"],
        alpha=0.7,
        bins=30,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Onset F-measure - Offset F-measure", fontsize=12)
plt.ylabel("Frequency", fontsize=12)
plt.title("Onset vs Offset Performance Difference", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)
plt.axvline(x=0, color="red", linestyle="--", alpha=0.8, label="Equal Performance")

plt.tight_layout()
plt.savefig("figures/02_onset_offset_analysis.png", dpi=300, bbox_inches="tight")
plt.show()

# ============================================================================
# IMAGE 3: ADVANCED PERFORMANCE PATTERNS
# ============================================================================
plt.figure(figsize=(16, 12))

# 1. Performance vs Duration (binned analysis)
plt.subplot(2, 3, 1)
df["duration_bin"] = pd.cut(
    df["duration_seconds"],
    bins=5,
    labels=["Very Short", "Short", "Medium", "Long", "Very Long"],
)
for model in models:
    model_data = df[df["model_name"] == model]
    duration_performance = model_data.groupby("duration_bin")["f_measure"].mean()
    plt.plot(
        duration_performance.index,
        duration_performance.values,
        marker="o",
        linewidth=2,
        markersize=8,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Duration Category", fontsize=12)
plt.ylabel("Average F-measure", fontsize=12)
plt.title("Performance vs Duration Category by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)

# 2. Runtime Efficiency Analysis
plt.subplot(2, 3, 2)
for model in models:
    model_data = df[df["model_name"] == model]
    # Calculate efficiency as F-measure per second
    efficiency = model_data["f_measure"] / (model_data["runtime"] / 60)  # per minute
    plt.scatter(
        model_data["runtime"],
        efficiency,
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Runtime (seconds)", fontsize=12)
plt.ylabel("Efficiency (F-measure/minute)", fontsize=12)
plt.title("Runtime Efficiency by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 3. Precision-Recall Trade-off Analysis
plt.subplot(2, 3, 3)
for model in models:
    model_data = df[df["model_name"] == model]
    # Calculate precision-recall difference
    pr_diff = model_data["precision"] - model_data["recall"]
    plt.scatter(
        model_data["f_measure"],
        pr_diff,
        alpha=0.6,
        s=40,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("F-measure", fontsize=12)
plt.ylabel("Precision - Recall", fontsize=12)
plt.title("Precision-Recall Balance by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)
plt.axhline(y=0, color="red", linestyle="--", alpha=0.8, label="Perfect Balance")

# 4. Performance Consistency Analysis
plt.subplot(2, 3, 4)
model_stats = []
for model in models:
    model_data = df[df["model_name"] == model]
    mean_perf = model_data["f_measure"].mean()
    std_perf = model_data["f_measure"].std()
    model_stats.append({"Model": model, "Mean": mean_perf, "Std": std_perf})

model_stats_df = pd.DataFrame(model_stats)
plt.scatter(model_stats_df["Mean"], model_stats_df["Std"], s=100, alpha=0.8)
for i, row in model_stats_df.iterrows():
    plt.annotate(
        row["Model"],
        (row["Mean"], row["Std"]),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=10,
    )

plt.xlabel("Mean F-measure", fontsize=12)
plt.ylabel("F-measure Standard Deviation", fontsize=12)
plt.title("Performance Consistency Analysis", fontsize=14, fontweight="bold")
plt.grid(True, alpha=0.3)

# 5. Overlap Ratio Analysis
plt.subplot(2, 3, 5)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.hist(
        model_data["average_overlap_ratio"],
        alpha=0.7,
        bins=30,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Average Overlap Ratio", fontsize=12)
plt.ylabel("Frequency", fontsize=12)
plt.title("Overlap Ratio Distribution by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 6. Overall Model Performance Radar Chart (if 3 models)
plt.subplot(2, 3, 6)
if len(models) <= 5:  # Only create radar chart if we have reasonable number of models
    categories = [
        "Precision",
        "Recall",
        "F-measure",
        "Onset F-measure",
        "Offset F-measure",
    ]

    # Number of variables
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Complete the circle

    ax = plt.subplot(2, 3, 6, projection="polar")

    for model in models:
        model_data = df[df["model_name"] == model]
        values = [
            model_data["precision"].mean(),
            model_data["recall"].mean(),
            model_data["f_measure"].mean(),
            model_data["onset_f_measure"].mean(),
            model_data["offset_f_measure"].mean(),
        ]
        values += values[:1]  # Complete the circle

        ax.plot(
            angles, values, "o-", linewidth=2, label=model, color=model_colors[model]
        )
        ax.fill(angles, values, alpha=0.25, color=model_colors[model])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 1)
    ax.set_title("Model Performance Radar Chart", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.0))
else:
    # If too many models, show a different visualization
    plt.text(
        0.5,
        0.5,
        "Too many models for radar chart\nShowing alternative visualization",
        ha="center",
        va="center",
        transform=plt.gca().transAxes,
        fontsize=12,
    )
    plt.axis("off")

plt.tight_layout()
plt.savefig(
    "figures/03_advanced_performance_patterns.png", dpi=300, bbox_inches="tight"
)
plt.show()

# ============================================================================
# IMAGE 4: STATISTICAL SUMMARY AND CORRELATIONS
# ============================================================================
plt.figure(figsize=(16, 10))

# 1. Model Performance Summary Table (as a visualization)
plt.subplot(2, 2, 1)
summary_data = []
for model in models:
    model_data = df[df["model_name"] == model]
    summary_data.append(
        {
            "Model": model,
            "Count": len(model_data),
            "Mean F-measure": f"{model_data['f_measure'].mean():.3f}",
            "Std F-measure": f"{model_data['f_measure'].std():.3f}",
            "Mean Runtime": f"{model_data['runtime'].mean():.1f}s",
            "Mean Precision": f"{model_data['precision'].mean():.3f}",
            "Mean Recall": f"{model_data['recall'].mean():.3f}",
        }
    )

summary_df = pd.DataFrame(summary_data)
plt.table(
    cellText=summary_df.values,
    colLabels=summary_df.columns,
    cellLoc="center",
    loc="center",
)
plt.axis("off")
plt.title("Model Performance Summary", fontsize=14, fontweight="bold")

# 2. Correlation Matrix for Key Metrics
plt.subplot(2, 2, 2)
key_metrics = [
    "duration_seconds",
    "precision",
    "recall",
    "f_measure",
    "average_overlap_ratio",
    "onset_f_measure",
    "offset_f_measure",
    "runtime",
]
corr_matrix = df[key_metrics].corr()
sns.heatmap(
    corr_matrix,
    annot=True,
    cmap="coolwarm",
    center=0,
    square=True,
    fmt=".3f",
    cbar_kws={"label": "Correlation"},
)
plt.title("Key Metrics Correlation Matrix", fontsize=14, fontweight="bold")
plt.xticks(rotation=45)
plt.yticks(rotation=45)

# 3. Performance Distribution Comparison
plt.subplot(2, 2, 3)
for model in models:
    model_data = df[df["model_name"] == model]
    plt.hist(
        model_data["f_measure"],
        alpha=0.7,
        bins=30,
        label=f"{model} (n={len(model_data)})",
        color=model_colors[model],
        density=True,
    )

plt.xlabel("F-measure", fontsize=12)
plt.ylabel("Density", fontsize=12)
plt.title("F-measure Distribution by Model", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)

# 4. Model Ranking Visualization
plt.subplot(2, 2, 4)
ranking_metrics = [
    "f_measure",
    "precision",
    "recall",
    "onset_f_measure",
    "offset_f_measure",
]
model_rankings = {}

for metric in ranking_metrics:
    model_means = [
        (model, df[df["model_name"] == model][metric].mean()) for model in models
    ]
    model_means.sort(key=lambda x: x[1], reverse=True)

    for rank, (model, score) in enumerate(model_means):
        if model not in model_rankings:
            model_rankings[model] = []
        model_rankings[model].append(rank + 1)

# Plot ranking
x_pos = np.arange(len(ranking_metrics))
width = 0.25

for i, model in enumerate(models):
    plt.bar(
        x_pos + i * width,
        model_rankings[model],
        width,
        alpha=0.8,
        label=model,
        color=model_colors[model],
    )

plt.xlabel("Metrics", fontsize=12)
plt.ylabel("Rank (1=Best)", fontsize=12)
plt.title("Model Ranking Across Metrics", fontsize=14, fontweight="bold")
plt.xticks(x_pos + width, ranking_metrics, rotation=45)
plt.legend()
plt.grid(True, alpha=0.3)
plt.gca().invert_yaxis()  # Lower rank number = better

plt.tight_layout()
plt.savefig("figures/04_statistical_summary.png", dpi=300, bbox_inches="tight")
plt.show()


# ============================================================================
# COMPREHENSIVE ANALYSIS WITH DETAILED STATISTICS
# ============================================================================
print("\n" + "=" * 80)
print("COMPREHENSIVE MODEL ANALYSIS")
print("=" * 80)
print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Total Dataset: {len(df)} files across {len(models)} models")
print(f"Models Analyzed: {list(models)}")
print(f"Datasets: {sorted(df['dataset_name'].unique())}")

print("\n" + "-" * 60)
print("DETAILED MODEL PERFORMANCE SUMMARY")
print("-" * 60)

for model in models:
    model_data = df[df["model_name"] == model]
    print(f"\n{model.upper()}:")
    print(f"  Files processed: {len(model_data)}")
    print(
        f"  Mean F-measure: {model_data['f_measure'].mean():.4f} ± {model_data['f_measure'].std():.4f}"
    )
    print(
        f"  Mean Precision: {model_data['precision'].mean():.4f} ± {model_data['precision'].std():.4f}"
    )
    print(
        f"  Mean Recall: {model_data['recall'].mean():.4f} ± {model_data['recall'].std():.4f}"
    )
    print(
        f"  Mean Runtime: {model_data['runtime'].mean():.2f} ± {model_data['runtime'].std():.2f} seconds"
    )
    print(f"  Median Runtime: {model_data['runtime'].median():.2f} seconds")
    print(
        f"  Mean Duration: {model_data['duration_seconds'].mean():.1f} ± {model_data['duration_seconds'].std():.1f} seconds"
    )
    print(
        f"  Onset Precision: {model_data['onset_precision'].mean():.4f} ± {model_data['onset_precision'].std():.4f}"
    )
    print(
        f"  Onset Recall: {model_data['onset_recall'].mean():.4f} ± {model_data['onset_recall'].std():.4f}"
    )
    print(
        f"  Onset F-measure: {model_data['onset_f_measure'].mean():.4f} ± {model_data['onset_f_measure'].std():.4f}"
    )
    print(
        f"  Offset Precision: {model_data['offset_precision'].mean():.4f} ± {model_data['offset_precision'].std():.4f}"
    )
    print(
        f"  Offset Recall: {model_data['offset_recall'].mean():.4f} ± {model_data['offset_recall'].std():.4f}"
    )
    print(
        f"  Offset F-measure: {model_data['offset_f_measure'].mean():.4f} ± {model_data['offset_f_measure'].std():.4f}"
    )
    print(
        f"  Average Overlap Ratio: {model_data['average_overlap_ratio'].mean():.4f} ± {model_data['average_overlap_ratio'].std():.4f}"
    )
    print(
        f"  No-Offset Precision: {model_data['precision_no_offset'].mean():.4f} ± {model_data['precision_no_offset'].std():.4f}"
    )
    print(
        f"  No-Offset Recall: {model_data['recall_no_offset'].mean():.4f} ± {model_data['recall_no_offset'].std():.4f}"
    )
    print(
        f"  No-Offset F-measure: {model_data['f_measure_no_offset'].mean():.4f} ± {model_data['f_measure_no_offset'].std():.4f}"
    )
    print(
        f"  Performance Range (F-measure): {model_data['f_measure'].min():.4f} to {model_data['f_measure'].max():.4f}"
    )
    print(
        f"  Efficiency (F-measure/runtime): {(model_data['f_measure'] / model_data['runtime']).mean():.6f}"
    )

print("\n" + "-" * 60)
print("OVERALL CORRELATIONS (All Models Combined)")
print("-" * 60)
print(f"Duration vs F-measure: {df['duration_seconds'].corr(df['f_measure']):.4f}")
print(f"Duration vs Precision: {df['duration_seconds'].corr(df['precision']):.4f}")
print(f"Duration vs Recall: {df['duration_seconds'].corr(df['recall']):.4f}")
print(f"Duration vs Runtime: {df['duration_seconds'].corr(df['runtime']):.4f}")
print(f"Precision vs Recall: {df['precision'].corr(df['recall']):.4f}")
print(
    f"F-measure vs Overlap Ratio: {df['f_measure'].corr(df['average_overlap_ratio']):.4f}"
)
print(
    f"F-measure vs No-Offset F-measure: {df['f_measure'].corr(df['f_measure_no_offset']):.4f}"
)
print(
    f"Onset vs Offset Precision: {df['onset_precision'].corr(df['offset_precision']):.4f}"
)
print(f"Onset vs Offset Recall: {df['onset_recall'].corr(df['offset_recall']):.4f}")
print(
    f"Onset vs Offset F-measure: {df['onset_f_measure'].corr(df['offset_f_measure']):.4f}"
)
print(f"Runtime vs F-measure: {df['runtime'].corr(df['f_measure']):.4f}")
print(f"Runtime vs Precision: {df['runtime'].corr(df['precision']):.4f}")
print(f"Runtime vs Recall: {df['runtime'].corr(df['recall']):.4f}")
print(
    f"Overlap Ratio vs Precision: {df['average_overlap_ratio'].corr(df['precision']):.4f}"
)
print(f"Overlap Ratio vs Recall: {df['average_overlap_ratio'].corr(df['recall']):.4f}")

print("\n" + "-" * 60)
print("MODEL-SPECIFIC CORRELATIONS")
print("-" * 60)

for model in models:
    model_data = df[df["model_name"] == model]
    print(f"\n{model.upper()} Correlations:")
    print(
        f"  Duration vs F-measure: {model_data['duration_seconds'].corr(model_data['f_measure']):.4f}"
    )
    print(
        f"  Precision vs Recall: {model_data['precision'].corr(model_data['recall']):.4f}"
    )
    print(
        f"  F-measure vs Overlap: {model_data['f_measure'].corr(model_data['average_overlap_ratio']):.4f}"
    )
    print(
        f"  Onset vs Offset F-measure: {model_data['onset_f_measure'].corr(model_data['offset_f_measure']):.4f}"
    )
    print(
        f"  Runtime vs F-measure: {model_data['runtime'].corr(model_data['f_measure']):.4f}"
    )
    print(
        f"  Runtime vs Duration: {model_data['runtime'].corr(model_data['duration_seconds']):.4f}"
    )

print("\n" + "-" * 60)
print("DATASET PERFORMANCE BREAKDOWN")
print("-" * 60)

for dataset in sorted(df["dataset_name"].unique()):
    dataset_data = df[df["dataset_name"] == dataset]
    print(f"\n{dataset}:")
    print(f"  Total files: {len(dataset_data)}")
    print(
        f"  Mean F-measure: {dataset_data['f_measure'].mean():.4f} ± {dataset_data['f_measure'].std():.4f}"
    )
    print(
        f"  Mean Duration: {dataset_data['duration_seconds'].mean():.1f} ± {dataset_data['duration_seconds'].std():.1f} seconds"
    )
    print(
        f"  Mean Runtime: {dataset_data['runtime'].mean():.2f} ± {dataset_data['runtime'].std():.2f} seconds"
    )

    # Model breakdown within dataset
    for model in models:
        model_dataset_data = dataset_data[dataset_data["model_name"] == model]
        if len(model_dataset_data) > 0:
            print(
                f"    {model}: {len(model_dataset_data)} files, F-measure: {model_dataset_data['f_measure'].mean():.4f}"
            )

print("\n" + "-" * 60)
print("PERFORMANCE RANKINGS")
print("-" * 60)

metrics_for_ranking = [
    "f_measure",
    "precision",
    "recall",
    "onset_f_measure",
    "offset_f_measure",
    "average_overlap_ratio",
]

for metric in metrics_for_ranking:
    print(f"\n{metric.upper().replace('_', ' ')} Rankings:")
    model_scores = [
        (model, df[df["model_name"] == model][metric].mean()) for model in models
    ]
    model_scores.sort(key=lambda x: x[1], reverse=True)

    for rank, (model, score) in enumerate(model_scores, 1):
        print(f"  {rank}. {model}: {score:.4f}")

print("\n" + "-" * 60)
print("EFFICIENCY ANALYSIS")
print("-" * 60)

efficiency_metrics = []
for model in models:
    model_data = df[df["model_name"] == model]
    efficiency = (model_data["f_measure"] / model_data["runtime"]).mean()
    efficiency_per_minute = efficiency * 60
    efficiency_metrics.append((model, efficiency, efficiency_per_minute))

# Sort by efficiency
efficiency_metrics.sort(key=lambda x: x[1], reverse=True)

print("Runtime Efficiency Rankings (F-measure per second):")
for rank, (model, eff_sec, eff_min) in enumerate(efficiency_metrics, 1):
    print(
        f"  {rank}. {model}: {eff_sec:.6f} F-measure/sec ({eff_min:.4f} F-measure/min)"
    )

print("\n" + "-" * 60)
print("STATISTICAL SIGNIFICANCE TESTS")
print("-" * 60)

# Perform ANOVA test for F-measure differences between models
from scipy import stats

f_measure_groups = [
    df[df["model_name"] == model]["f_measure"].values for model in models
]
f_stat, p_value = stats.f_oneway(*f_measure_groups)
print(f"ANOVA F-statistic for F-measure differences: {f_stat:.4f}")
print(f"ANOVA p-value: {p_value:.6f}")
print(f"Significant difference between models: {'Yes' if p_value < 0.05 else 'No'}")

# Pairwise comparisons
print("\nPairwise t-tests between models (F-measure):")
for i, model1 in enumerate(models):
    for j, model2 in enumerate(models):
        if i < j:  # Avoid duplicate comparisons
            data1 = df[df["model_name"] == model1]["f_measure"]
            data2 = df[df["model_name"] == model2]["f_measure"]
            t_stat, p_val = stats.ttest_ind(data1, data2)
            print(f"  {model1} vs {model2}: t={t_stat:.4f}, p={p_val:.6f}")

print("\n" + "-" * 60)
print("COMPLETE CORRELATION MATRIX")
print("-" * 60)

all_numeric_cols = [
    "duration_seconds",
    "precision",
    "recall",
    "f_measure",
    "average_overlap_ratio",
    "precision_no_offset",
    "recall_no_offset",
    "f_measure_no_offset",
    "average_overlap_ratio_no_offset",
    "onset_precision",
    "onset_recall",
    "onset_f_measure",
    "offset_precision",
    "offset_recall",
    "offset_f_measure",
    "runtime",
]

corr_matrix = df[all_numeric_cols].corr()
print("\nCorrelation Matrix (only values > 0.3 or < -0.3):")
for i, col1 in enumerate(all_numeric_cols):
    for j, col2 in enumerate(all_numeric_cols):
        if i < j:  # Avoid duplicate pairs
            corr_val = corr_matrix.loc[col1, col2]
            if abs(corr_val) > 0.3:
                print(f"  {col1} vs {col2}: {corr_val:.4f}")

print("\n" + "-" * 60)
print("FIGURES SAVED")
print("-" * 60)
print("1. figures/01_core_performance_analysis.png - Main performance comparisons")
print("2. figures/02_onset_offset_analysis.png - Onset/offset detailed analysis")
print("3. figures/03_advanced_performance_patterns.png - Advanced pattern analysis")
print("4. figures/04_statistical_summary.png - Statistical summary and rankings")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE!")
print("=" * 80)
