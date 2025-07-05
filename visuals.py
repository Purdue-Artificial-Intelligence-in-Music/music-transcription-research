import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats
import warnings

warnings.filterwarnings("ignore")

# Set style for better-looking plots
plt.style.use("seaborn-v0_8")
sns.set_palette("Set2")

# Load the data
print("Loading music results data...")
df = pd.read_pickle("./results/dataframe.pkl")
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
# PRINT COMPREHENSIVE ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("COMPREHENSIVE MODEL ANALYSIS")
print("=" * 80)

print(f"\nTOTAL DATASET: {len(df)} files across {len(models)} models")
print(f"MODELS ANALYZED: {list(models)}")

print("\n" + "-" * 50)
print("MODEL PERFORMANCE SUMMARY")
print("-" * 50)

for model in models:
    model_data = df[df["model_name"] == model]
    print(f"\n{model.upper()}:")
    print(f"  Files processed: {len(model_data)}")
    print(
        f"  Mean F-measure: {model_data['f_measure'].mean():.3f} ± {model_data['f_measure'].std():.3f}"
    )
    print(
        f"  Mean Precision: {model_data['precision'].mean():.3f} ± {model_data['precision'].std():.3f}"
    )
    print(
        f"  Mean Recall: {model_data['recall'].mean():.3f} ± {model_data['recall'].std():.3f}"
    )
    print(
        f"  Mean Runtime: {model_data['runtime'].mean():.1f} ± {model_data['runtime'].std():.1f} seconds"
    )
    print(f"  Onset F-measure: {model_data['onset_f_measure'].mean():.3f}")
    print(f"  Offset F-measure: {model_data['offset_f_measure'].mean():.3f}")

print("\n" + "-" * 50)
print("KEY CORRELATIONS (Overall)")
print("-" * 50)
print(f"Duration vs F-measure: {df['duration_seconds'].corr(df['f_measure']):.3f}")
print(f"Precision vs Recall: {df['precision'].corr(df['recall']):.3f}")
print(f"F-measure vs Overlap: {df['f_measure'].corr(df['average_overlap_ratio']):.3f}")
print(
    f"Onset vs Offset F-measure: {df['onset_f_measure'].corr(df['offset_f_measure']):.3f}"
)
print(f"Runtime vs F-measure: {df['runtime'].corr(df['f_measure']):.3f}")

print("\n" + "-" * 50)
print("FIGURES SAVED")
print("-" * 50)
print("1. figures/01_core_performance_analysis.png - Main performance comparisons")
print("2. figures/02_onset_offset_analysis.png - Onset/offset detailed analysis")
print("3. figures/03_advanced_performance_patterns.png - Advanced pattern analysis")
print("4. figures/04_statistical_summary.png - Statistical summary and rankings")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE!")
print("=" * 80)
