import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import warnings
import os

warnings.filterwarnings("ignore")

# ============================================================================
# CONFIGURATION
# ============================================================================
NAME_MAPPING = {"miros": "MIROS", "yptfmoem": "YourMT3-YPTF-MoE-M"}

STYLE_CONFIG = {
    "MIROS": {"marker": "o", "linestyle": "-", "color": "#1f77b4"},
    "YourMT3-YPTF-MoE-M": {"marker": "s", "linestyle": "--", "color": "#ff7f0e"},
}

# ============================================================================
# STYLE SETTINGS (Normal 10pt look)
# ============================================================================
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 10,  # Standard 10pt font
        "axes.labelsize": 11,  # Slightly larger for axis labels
        "axes.titlesize": 12,  # Titles
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "lines.linewidth": 1.5,
        "lines.markersize": 7,
    }
)

# ============================================================================
# LOAD AND FILTER DATA
# ============================================================================
print("Loading data...")
df = pd.read_pickle("./data/dataframe.pkl")

# Filter
df_clean = df[df["model_name"].isin(NAME_MAPPING.keys())].copy()
if df_clean.empty:
    raise ValueError(f"No data found for keys: {list(NAME_MAPPING.keys())}")

# Map Names
df_clean["Model"] = df_clean["model_name"].map(NAME_MAPPING)

# Categorize
df_clean["reference_midi_instruments"] = pd.to_numeric(
    df_clean["reference_midi_instruments"], errors="coerce"
)
df_clean["instrument_category"] = df_clean["reference_midi_instruments"].apply(
    lambda x: "Single" if x == 1 else "Multiple"
)

print(f"Successfully filtered to {len(df_clean)} records.")

# ============================================================================
# PLOTTING
# ============================================================================
if not os.path.exists("figures"):
    os.makedirs("figures")

CAT_ORDER = ["Single", "Multiple"]

# Create figure with standard convenient size
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# --- LEFT PLOT: Boxplot ---
sns.boxplot(
    data=df_clean,
    x="instrument_category",
    y="f_measure",
    hue="Model",
    order=CAT_ORDER,
    palette={name: config["color"] for name, config in STYLE_CONFIG.items()},
    ax=axes[0],
)
axes[0].set_title("F-measure by Model and Input Instrument Count")
axes[0].set_xlabel("Instrument Configuration")
axes[0].set_ylabel("F-measure")
axes[0].grid(True, axis="y", alpha=0.3)

# --- RIGHT PLOT: Pointplot ---
hue_order = sorted(df_clean["Model"].unique())
palette_list = [STYLE_CONFIG[m]["color"] for m in hue_order]
markers_list = [STYLE_CONFIG[m]["marker"] for m in hue_order]
linestyles_list = [STYLE_CONFIG[m]["linestyle"] for m in hue_order]

sns.pointplot(
    data=df_clean,
    x="instrument_category",
    y="f_measure",
    hue="Model",
    order=CAT_ORDER,
    hue_order=hue_order,
    palette=palette_list,
    markers=markers_list,
    linestyles=linestyles_list,
    dodge=True,
    capsize=0.1,
    errorbar="ci",
    ax=axes[1],
)
axes[1].set_title("Model Performance Across Instrument Configurations")
axes[1].set_xlabel("Instrument Configuration")
axes[1].set_ylabel("Mean F-measure")
axes[1].grid(True, axis="y", alpha=0.3)

plt.tight_layout()

outfile = "figures/instrumentation_analysis.png"
plt.savefig(outfile, dpi=300)
plt.close()

print(f"Success! Saved graph to {outfile}")
