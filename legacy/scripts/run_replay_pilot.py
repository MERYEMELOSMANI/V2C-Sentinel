import pandas as pd
import numpy as np
from pathlib import Path
import json

RESULTS = Path("results/tables")
RESULTS.mkdir(parents=True, exist_ok=True)

local = pd.read_csv(RESULTS / "local_predictions.csv")
cloud = pd.read_csv(RESULTS / "cloud_predictions.csv")

print("Merging local and cloud predictions...")
df = local.merge(
    cloud[["recording_id", "timestamp", "event_id", "cloud_score", "cloud_pred"]],
    on=["recording_id", "timestamp", "event_id"],
    how="inner"
)

df["local_correct"] = df["local_pred"] == df["true_label"]
df["cloud_correct"] = df["cloud_pred"] == df["true_label"]

# Fake delay distribution
rng = np.random.default_rng(42)
df["cloud_delay"] = rng.lognormal(mean=np.log(0.08), sigma=0.6, size=len(df))

# Simple Request Policy
request_threshold = np.percentile(df["local_score"], 90) # use 90th percentile instead of a hardcoded 0.44
df["request_cloud"] = df["local_score"] >= request_threshold

# Deadline rule
deadline_seconds = 0.150
df["deadline"] = deadline_seconds
df["cloud_return_time"] = df["timestamp"] + df["cloud_delay"]
df["deadline_time"] = df["timestamp"] + df["deadline"]

df["cloud_on_time"] = df["cloud_return_time"] <= df["deadline_time"]
df["late_reply"] = df["request_cloud"] & (~df["cloud_on_time"])

df["final_pred"] = df["local_pred"]
use_cloud = df["request_cloud"] & df["cloud_on_time"]
df.loc[use_cloud, "final_pred"] = df.loc[use_cloud, "cloud_pred"]

# Measure corrections and harm
df["final_correct"] = df["final_pred"] == df["true_label"]

df["corrected_by_cloud"] = (
    df["request_cloud"]
    & df["cloud_on_time"]
    & (~df["local_correct"])
    & (df["cloud_correct"])
)

df["harmed_by_cloud"] = (
    df["request_cloud"]
    & df["cloud_on_time"]
    & (df["local_correct"])
    & (~df["cloud_correct"])
)

summary = {
    "total_windows": len(df),
    "cloud_requests": int(df["request_cloud"].sum()),
    "cloud_request_rate_%": df["request_cloud"].mean() * 100,
    "late_replies": int(df["late_reply"].sum()),
    "late_reply_rate_%": df["late_reply"].mean() * 100,
    "cloud_corrections_on_time": int(df["corrected_by_cloud"].sum()),
    "cloud_harms_on_time": int(df["harmed_by_cloud"].sum()),
    "local_accuracy_%": df["local_correct"].mean() * 100,
    "final_accuracy_%": df["final_correct"].mean() * 100,
}

summary_df = pd.DataFrame([summary])
summary_df.to_csv(RESULTS / "replay_summary.csv", index=False)

replay_results = df[[
    "recording_id", "event_id", "timestamp", "true_label", "local_score", "local_pred",
    "cloud_score", "cloud_pred", "request_cloud", "cloud_delay", "deadline", "cloud_on_time",
    "late_reply", "final_pred", "local_correct", "cloud_correct", "final_correct",
    "corrected_by_cloud", "harmed_by_cloud"
]]
replay_results.to_csv(RESULTS / "replay_results.csv", index=False)

# Test many deadlines
def run_replay(base_df, request_threshold, deadline_seconds):
    d = base_df.copy()
    d["request_cloud"] = d["local_score"] >= request_threshold
    d["deadline"] = deadline_seconds
    
    d["cloud_return_time"] = d["timestamp"] + d["cloud_delay"]
    d["deadline_time"] = d["timestamp"] + d["deadline"]
    d["cloud_on_time"] = d["cloud_return_time"] <= d["deadline_time"]
    d["late_reply"] = d["request_cloud"] & (~d["cloud_on_time"])
    
    d["final_pred"] = d["local_pred"]
    use_cloud = d["request_cloud"] & d["cloud_on_time"]
    d.loc[use_cloud, "final_pred"] = d.loc[use_cloud, "cloud_pred"]
    
    d["local_correct"] = d["local_pred"] == d["true_label"]
    d["cloud_correct"] = d["cloud_pred"] == d["true_label"]
    d["final_correct"] = d["final_pred"] == d["true_label"]
    
    d["corrected_by_cloud"] = (
        d["request_cloud"] & d["cloud_on_time"] & (~d["local_correct"]) & d["cloud_correct"]
    )
    d["harmed_by_cloud"] = (
        d["request_cloud"] & d["cloud_on_time"] & d["local_correct"] & (~d["cloud_correct"])
    )
    
    return {
        "request_threshold": request_threshold,
        "deadline_seconds": deadline_seconds,
        "total_windows": len(d),
        "cloud_requests": int(d["request_cloud"].sum()),
        "cloud_request_rate_%": d["request_cloud"].mean() * 100,
        "late_replies": int(d["late_reply"].sum()),
        "late_reply_rate_%": d["late_reply"].mean() * 100,
        "cloud_corrections_on_time": int(d["corrected_by_cloud"].sum()),
        "cloud_harms_on_time": int(d["harmed_by_cloud"].sum()),
        "local_accuracy_%": d["local_correct"].mean() * 100,
        "final_accuracy_%": d["final_correct"].mean() * 100,
        "attack_recall_local_%": (d.loc[d["true_label"] == 1, "local_pred"].eq(1).mean() * 100),
        "attack_recall_final_%": (d.loc[d["true_label"] == 1, "final_pred"].eq(1).mean() * 100),
        "false_alarm_local": int(((d["true_label"] == 0) & (d["local_pred"] == 1)).sum()),
        "false_alarm_final": int(((d["true_label"] == 0) & (d["final_pred"] == 1)).sum()),
    }

print("Running parameter sweep...")
base_df = df.copy()
deadlines = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
# Calculate thresholds based on percentiles to ensure we get some requests
thresholds = [np.percentile(df["local_score"], p) for p in [50, 75, 85, 90, 95, 99]]

rows = []
for threshold in thresholds:
    for deadline in deadlines:
        rows.append(run_replay(base_df, threshold, deadline))

sweep_df = pd.DataFrame(rows)
sweep_df.to_csv(RESULTS / "deadline_sweep.csv", index=False)
print("Saved replay_summary.csv and deadline_sweep.csv!")

# Update Notebook 05
notebook_cells = [
    ("markdown", "# 05 Deadline-Aware Replay\nFor each window, policy decides: keep local OR ask cloud. Cloud answer returns after a sampled delay."),
    ("code", "import pandas as pd\nimport numpy as np\nfrom pathlib import Path\n\nRESULTS = Path('../results/tables')\nRESULTS.mkdir(parents=True, exist_ok=True)\n\nlocal = pd.read_csv(RESULTS / 'local_predictions.csv')\ncloud = pd.read_csv(RESULTS / 'cloud_predictions.csv')\n\nprint(local.shape)\nprint(cloud.shape)\nprint(local.head())\nprint(cloud.head())"),
    ("code", "print('TRUE LABELS')\nprint(local['true_label'].value_counts())\n\nprint('LOCAL PREDS')\nprint(local['local_pred'].value_counts())\n\nprint('CLOUD PREDS')\nprint(cloud['cloud_pred'].value_counts())"),
    ("code", "df = local.merge(\n    cloud[['recording_id', 'timestamp', 'event_id', 'cloud_score', 'cloud_pred']],\n    on=['recording_id', 'timestamp', 'event_id'],\n    how='inner'\n)\nprint(df.shape)\n\ndf['local_correct'] = df['local_pred'] == df['true_label']\ndf['cloud_correct'] = df['cloud_pred'] == df['true_label']\npd.crosstab(df['local_correct'], df['cloud_correct'])"),
    ("code", "rng = np.random.default_rng(42)\ndf['cloud_delay'] = rng.lognormal(mean=np.log(0.08), sigma=0.6, size=len(df))\ndf['cloud_delay'].describe()"),
    ("code", "deadline_seconds = 0.150\ndf['deadline'] = deadline_seconds\nrequest_threshold = np.percentile(df['local_score'], 90)\ndf['request_cloud'] = df['local_score'] >= request_threshold\ndf['request_cloud'].value_counts(normalize=True) * 100"),
    ("code", "df['cloud_return_time'] = df['timestamp'] + df['cloud_delay']\ndf['deadline_time'] = df['timestamp'] + df['deadline']\n\ndf['cloud_on_time'] = df['cloud_return_time'] <= df['deadline_time']\ndf['late_reply'] = df['request_cloud'] & (~df['cloud_on_time'])\n\ndf['final_pred'] = df['local_pred']\nuse_cloud = df['request_cloud'] & df['cloud_on_time']\ndf.loc[use_cloud, 'final_pred'] = df.loc[use_cloud, 'cloud_pred']"),
    ("code", "df['final_correct'] = df['final_pred'] == df['true_label']\n\ndf['corrected_by_cloud'] = (df['request_cloud'] & df['cloud_on_time'] & (~df['local_correct']) & df['cloud_correct'])\ndf['harmed_by_cloud'] = (df['request_cloud'] & df['cloud_on_time'] & df['local_correct'] & (~df['cloud_correct']))\n\nsummary = {\n    'total_windows': len(df),\n    'cloud_requests': int(df['request_cloud'].sum()),\n    'cloud_request_rate_%': df['request_cloud'].mean() * 100,\n    'late_replies': int(df['late_reply'].sum()),\n    'late_reply_rate_%': df['late_reply'].mean() * 100,\n    'cloud_corrections_on_time': int(df['corrected_by_cloud'].sum()),\n    'cloud_harms_on_time': int(df['harmed_by_cloud'].sum()),\n    'local_accuracy_%': df['local_correct'].mean() * 100,\n    'final_accuracy_%': df['final_correct'].mean() * 100,\n}\npd.DataFrame([summary]).to_csv(RESULTS / 'replay_summary.csv', index=False)\nsummary"),
]

cells = []
for cell_type, source in notebook_cells:
    cell = {"cell_type": cell_type, "metadata": {}, "source": [line + "\\n" for line in source.split('\\n')[:-1]] + [source.split('\\n')[-1]]}
    if cell_type == "code":
        cell["outputs"] = []
        cell["execution_count"] = None
    cells.append(cell)

with open('notebooks/05_replay_policy_pilot.ipynb', 'w') as f:
    json.dump({"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 4}, f, indent=2)

print("Notebook 05 generated.")
