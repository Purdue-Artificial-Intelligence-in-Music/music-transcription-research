import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Modern "Clean" Styling
sns.set_style("white") # Remove all background grids
sns.set_context("poster", font_scale=0.8)
PURDUE_GOLD = "#CEB888"
PURDUE_BLACK = "#000000"

def generate_modern_slopechart():
    df = pd.read_pickle("../data/dataframe.pkl")
    
    # 1. Clean Names
    name_map = {"Bytedance_Piano_transcription": "Bytedance", "CREPE_Pitch_Tracker": "CREPE", "Basic_Pitch": "Basic Pitch"}
    df['model_name'] = df['model_name'].replace(name_map)
    
    # 2. Prep Data
    df["inst_cat"] = df["reference_midi_instruments"].apply(lambda x: "Single" if x == 1 else "Multiple")
    slope_data = df.groupby(['model_name', 'inst_cat'])['f_measure'].mean().reset_index()

    plt.figure(figsize=(10, 8))
    
    # Use a specific color palette - highlighting Transkun in Purdue Gold
    models = slope_data['model_name'].unique()
    colors = {m: "darkgray" for m in models}
    colors['Transkun'] = PURDUE_GOLD # Highlight the top performer
    colors['MT3'] = PURDUE_BLACK   # Highlight the standard transformer
    
    # Create the Slopechart
    for model in models:
        data = slope_data[slope_data['model_name'] == model]
        if len(data) == 2:
            # Sort to ensure Single is left, Multiple is right
            data = data.sort_values('inst_cat', ascending=False) 
            plt.plot(data['inst_cat'], data['f_measure'], marker='o', 
                     linewidth=4, markersize=12, color=colors[model], alpha=0.8, label=model)
            
            # Label the lines directly on the plot for a modern look
            plt.text(1.02, data[data['inst_cat']=='Multiple']['f_measure'].values[0], 
                     model, fontsize=14, color=colors[model], weight='bold')

    # Styling
    plt.title("The Polyphony Penalty", fontsize=28, pad=30, weight='bold')
    plt.ylabel("Accuracy (F-measure)", fontsize=20)
    plt.xlabel("")
    plt.ylim(-0.05, 1.05)
    plt.xticks([0, 1], ["Single Instrument", "Multiple Instruments"], fontsize=22)
    
    # Remove chart borders (spines) for a modern feel
    sns.despine(left=False, bottom=True, trim=True)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("figures/modern_polyphony_slope.png", dpi=300)

if __name__ == "__main__":
    generate_modern_slopechart()