import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
RAW_ROAD = Path("data/raw/road")
RAW_DELAY = Path("data/raw/cicv5g")
RESULTS = Path("results/tables")
FIGURES = Path("figures")

RESULTS.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

# ----------------- ROAD AUDIT -----------------
road_files = list(RAW_ROAD.rglob("*.csv"))

manifest = []
for f in road_files:
    if f.is_file():
        manifest.append({
            "file_name": f.name,
            "path": str(f),
            "extension": f.suffix,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2)
        })
manifest_df = pd.DataFrame(manifest)
manifest_df.to_csv(RESULTS / "road_manifest.csv", index=False)

if len(road_files) > 0:
    normal_file = next((f for f in road_files if 'ambient' in str(f)), road_files[0])
    df_road = pd.read_csv(normal_file)
    
    plt.figure(figsize=(10, 4))
    if 'Time' in df_road.columns:
        df_road['Time'].hist(bins=100)
        plt.xlabel("Time")
    else:
        df_road.index.to_series().hist(bins=100)
        plt.xlabel("Message Index")
    plt.ylabel("Count")
    plt.title("ROAD Message Density")
    plt.savefig(FIGURES / "road_message_rate.png", dpi=200, bbox_inches="tight")
    plt.close()

# ----------------- DELAY AUDIT -----------------
delay_files = list(RAW_DELAY.rglob("*.csv"))

if len(delay_files) > 0:
    delay_file = delay_files[0]
    delay_df = pd.read_csv(delay_file, encoding='latin1', on_bad_lines='skip', engine='python')
    
    delay_df.describe(include="all").T.to_csv(RESULTS / "delay_summary.csv")
    
    # Identify delay col
    delay_col = next((c for c in delay_df.columns if 'delay' in c.lower()), None)
    if not delay_col:
        if 'sub_time' in delay_df.columns and 'pub_time' in delay_df.columns:
            # Check if they are numeric
            delay_df['sub_time'] = pd.to_numeric(delay_df['sub_time'], errors='coerce')
            delay_df['pub_time'] = pd.to_numeric(delay_df['pub_time'], errors='coerce')
            delay_df['delay'] = delay_df['sub_time'] - delay_df['pub_time']
            delay_col = 'delay'
            
    if delay_col:
        delay_df[delay_col] = pd.to_numeric(delay_df[delay_col], errors='coerce')
        plt.figure(figsize=(10, 4))
        delay_df[delay_col].dropna().hist(bins=100)
        plt.xlabel("Delay")
        plt.ylabel("Count")
        plt.title("CICV5G delay distribution")
        plt.savefig(FIGURES / "cicv5g_delay_distribution.png", dpi=200, bbox_inches="tight")
        plt.close()

print("Execution complete!")
