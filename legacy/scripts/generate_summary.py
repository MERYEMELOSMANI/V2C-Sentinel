import pandas as pd
from pathlib import Path

RESULTS_DIR = Path("results/final")

runs_df = pd.read_csv(RESULTS_DIR / "all_runs.csv")

agg_cols = [
    'timely_detections', 'eventual_detections', 'missed_episodes',
    'mean_detection_delay_s', 'raw_false_warnings', 'grouped_false_alerts',
    'false_alerts_per_hr', 'total_requests', 'actual_request_rate_pct',
    'actual_req_per_sec', 'late_replies', 'late_reply_pct'
]

summary = runs_df.groupby(
    ['split', 'policy', 'budget_req_per_sec', 'deadline_s'], dropna=False
).agg(
    n_runs=('seed', 'count'),
    **{col: (col, 'mean') for col in agg_cols}
).reset_index()

summary.to_csv(RESULTS_DIR / "summary.csv", index=False)
print("Saved summary.csv")

# Print the key results like the main script does
display_cols = [
    'policy', 'budget_req_per_sec',
    'timely_detections', 'mean_detection_delay_s',
    'false_alerts_per_hr', 'actual_req_per_sec', 'late_reply_pct'
]
dev_summary = summary[(summary['split'] == 'dev') & (summary['deadline_s'] == 0.150)].copy()

dev_summary['budget_req_per_sec'] = dev_summary['budget_req_per_sec'].fillna(0)
dev_summary.sort_values(['budget_req_per_sec', 'policy'], inplace=True)
dev_summary['budget_req_per_sec'] = dev_summary['budget_req_per_sec'].replace(0, 'N/A')
dev_summary['actual_req_per_sec'] = dev_summary['actual_req_per_sec'].round(1)
dev_summary['false_alerts_per_hr'] = dev_summary['false_alerts_per_hr'].round(1)
dev_summary['mean_detection_delay_s'] = dev_summary['mean_detection_delay_s'].round(3)
dev_summary['late_reply_pct'] = dev_summary['late_reply_pct'].round(1)

print("\n" + "=" * 70)
print("KEY RESULTS (dev split, 150ms deadline)")
print("=" * 70)
print(dev_summary[display_cols].to_string(index=False))
