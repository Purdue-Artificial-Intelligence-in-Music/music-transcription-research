import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Fix: Use Seaborn to set the style to avoid the FileNotFoundError
sns.set_style("whitegrid")
sns.set_context("talk") 
PURDUE_GOLD = "#CEB888"
PURDUE_BLACK = "#000000"

def generate_poster_visuals():
    # Load data
    try:
        df = pd.read_pickle("../data/dataframe.pkl")
    except FileNotFoundError:
        print("Error: ../data/dataframe.pkl not found.")
        return

    # 1. Clean Model Names for better layout
    name_map = {
        "Bytedance_Piano_transcription": "Bytedance",
        "CREPE_Pitch_Tracker": "CREPE",
        "Basic_Pitch": "Basic Pitch",
    }
    df['model_name'] = df['model_name'].replace(name_map)
    
    # 2. Setup Instrument Categories
    df["inst_cat"] = df["reference_midi_instruments"].apply(lambda x: "Single" if x == 1 else "Multiple")
    inst_order = ["Single", "Multiple"]

    if not os.path.exists("figures"):
        os.makedirs("figures")

    # --- FIGURE 1: Horizontal F-Measure (The Leaderboard) ---
    plt.figure(figsize=(10, 6))
    order = df.groupby("model_name")["f_measure"].mean().sort_values(ascending=False).index
    sns.boxplot(data=df, y="model_name", x="f_measure", color=PURDUE_GOLD, order=order, width=0.6, fliersize=1)
    plt.title("Overall Performance (F-measure)")
    plt.ylabel("")
    plt.xlabel("Accuracy Score")
    plt.tight_layout()
    plt.savefig("figures/f_measure_boxplot.png", dpi=300)

    # --- FIGURE 2: Single vs Multiple (The Polyphony Penalty) ---
    plt.figure(figsize=(10, 6))
    sns.pointplot(data=df, x="inst_cat", y="f_measure", hue="model_name", 
                  order=inst_order, dodge=0.4, markers="D", capsize=.1, errorbar=None)
    plt.title("Polyphony Penalty: Single vs. Multiple")
    plt.ylabel("F-measure")
    plt.xlabel("Instrument Configuration")
    plt.legend(title="Model", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='x-small')
    plt.tight_layout()
    plt.savefig("figures/polyphony_penalty.png", dpi=300)

    # --- FIGURE 3: Onset vs Offset (The Error Insight) ---
    metrics = df.groupby("model_name")[["onset_f_measure", "offset_f_measure"]].mean().reset_index()
    metrics_melted = metrics.melt(id_vars="model_name", var_name="Type", value_name="Score")
    metrics_melted["Type"] = metrics_melted["Type"].replace({"onset_f_measure": "Onset (Start)", "offset_f_measure": "Offset (End)"})

    plt.figure(figsize=(12, 6))
    sns.barplot(data=metrics_melted, x="model_name", y="Score", hue="Type", palette=[PURDUE_GOLD, PURDUE_BLACK])
    plt.title("Note Detection: Onset vs. Offset Accuracy")
    plt.xticks(rotation=30, ha='right')
    plt.ylabel("Mean F-measure")
    plt.xlabel("")
    plt.legend(title="Detection Type")
    plt.tight_layout()
    plt.savefig("figures/onset_offset_comparison.png", dpi=300)

    # 4. Generate data for Typst table
    summary = df.groupby("model_name")["f_measure"].agg(["mean", "std"]).sort_values("mean", ascending=False)
    print("\n=== COPY THIS DATA INTO YOUR TYPST TABLE ===")
    for model, row in summary.iterrows():
        print(f"[{model}], [{row['mean']:.3f}], [{row['std']:.3f}],")
    
    # To get the Onset F-measure means:
    print("\n=== ONSET F-MEASURE MEANS ===")
    onset_summary = df.groupby("model_name")["onset_f_measure"].mean().reindex(summary.index)
    for model, val in onset_summary.items():
        print(f"[{model} Onset Mean: {val:.3f}]")

    # To get Runtime means:
    print("\n=== RUNTIME MEANS ===")
    runtime_summary = df.groupby("model_name")["runtime"].mean().reindex(summary.index)
    for model, val in runtime_summary.items():
        print(f"[{model} Runtime Mean: {val:.1f}s]")

if __name__ == "__main__":
    generate_poster_visuals()