"""
V2C-Sentinel Two-Level Alert Experiment
================================================
This script implements the final, focused two-level alert system:
- Level 1: Immediate local warning (fast but noisy)
- Level 2: Cloud-confirmed alert (slower but cleaner)

We sweep over different budgets to see how the two-level system behaves.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import heapq
import time
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "version": "2.0.0",
    "timestamp": None,
    "local_proc_time_s": 0.005,
    "cloud_proc_time_s": 0.010,
    "deadlines_s": [0.150, 0.300],
    "request_budgets_per_sec": [1.0, 5.0, 10.0, 50.0, "unlimited"],
    "false_alert_grouping_window_s": 1.0,
    "episode_gap_tolerance_s": 0.5,
    "network_traces": [
        {
            "name": "urban_n78",
            "path": "data/raw/cicv5g/data/Urban road/2-n78/Urban road_n78.csv",
        }
    ]
}

RESULTS_DIR = Path("results/final_two_level")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

class TraceProvider:
    def __init__(self, trace_df):
        self.times = (trace_df['pub_time(ms)'] - trace_df['pub_time(ms)'].iloc[0]).values / 1000.0
        self.delays = trace_df['delay(ms)'].values / 1000.0
        self.max_time = self.times[-1]

    def get_delay_at(self, sim_time):
        wrapped_time = sim_time % self.max_time
        idx = np.searchsorted(self.times, wrapped_time)
        if idx >= len(self.delays):
            idx = len(self.delays) - 1
        return max(self.delays[idx], 0.001)

class TokenBucket:
    def __init__(self, rate_per_sec):
        self.rate = rate_per_sec
        self.burst = max(2.0, rate_per_sec * 0.1)
        self.tokens = self.burst
        self.last_time = 0.0

    def try_consume(self, current_time):
        elapsed = current_time - self.last_time
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_time = current_time
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

class UnlimitedBucket:
    def try_consume(self, current_time):
        return True

def extract_episodes(df_recording, gap_tolerance=0.5):
    is_attack = df_recording['true_label'] == 1
    attack_times = df_recording[is_attack]['timestamp'].values
    if len(attack_times) == 0:
        return []
    episodes = []
    onset = attack_times[0]
    last_t = attack_times[0]
    for t in attack_times[1:]:
        if t - last_t > gap_tolerance:
            episodes.append({'onset': onset, 'end': last_t})
            onset = t
        last_t = t
    episodes.append({'onset': onset, 'end': last_t})
    return episodes

def group_alerts(warning_times, threshold=1.0):
    if len(warning_times) == 0:
        return 0
    times = sorted(warning_times)
    alerts = 1
    last_alert = times[0]
    for t in times[1:]:
        if t - last_alert > threshold:
            alerts += 1
            last_alert = t
    return alerts

def simulate_two_level(df_recording, delay_provider, bucket):
    warnings = []
    request_log = []
    pending_replies = []
    seq = 0

    for row in df_recording.itertuples():
        idx = row.Index
        obs_time = row.timestamp
        local_done_time = obs_time + CONFIG['local_proc_time_s']

        while pending_replies and pending_replies[0][0] <= local_done_time:
            _, _, reply = heapq.heappop(pending_replies)
            if reply['pred'] == 1:
                warnings.append({
                    'time': reply['return_time'],
                    'source': 'level2_cloud',
                    'window_idx': reply['window_idx']
                })

        if row.local_pred == 1:
            warnings.append({
                'time': local_done_time,
                'source': 'level1_local',
                'window_idx': idx
            })

            if bucket.try_consume(local_done_time):
                actual_delay = delay_provider.get_delay_at(local_done_time)
                cloud_return_time = local_done_time + actual_delay + CONFIG['cloud_proc_time_s']

                reply = {
                    'return_time': cloud_return_time,
                    'pred': row.cloud_pred,
                    'window_idx': idx
                }
                heapq.heappush(pending_replies, (cloud_return_time, seq, reply))
                seq += 1

                request_log.append({
                    'sent': local_done_time,
                    'returned': cloud_return_time,
                    'rtt': actual_delay
                })

    for _, _, reply in sorted(pending_replies):
        if reply['pred'] == 1:
            warnings.append({
                'time': reply['return_time'],
                'source': 'level2_cloud',
                'window_idx': reply['window_idx']
            })

    return pd.DataFrame(warnings) if warnings else pd.DataFrame(columns=['time', 'source', 'window_idx']), pd.DataFrame(request_log) if request_log else pd.DataFrame(columns=['sent', 'returned', 'rtt'])

def evaluate_run(recording, warnings_df, episodes, deadline):
    metrics = {}
    metrics['n_messages'] = len(recording)
    metrics['attack_episodes'] = len(episodes)

    rec_duration = recording['timestamp'].max() - recording['timestamp'].min()
    attack_duration = sum(ep['end'] - ep['onset'] for ep in episodes)
    normal_duration_hr = max((rec_duration - attack_duration) / 3600.0, 0.001)

    for level in ['level1_local', 'level2_cloud']:
        if warnings_df.empty:
            level_warnings = pd.DataFrame(columns=['time', 'source', 'window_idx'])
        else:
            level_warnings = warnings_df[warnings_df['source'] == level]

        timely = 0
        delays = []

        for ep in episodes:
            ep_mask = (recording['timestamp'] >= ep['onset']) & (recording['timestamp'] <= ep['end'])
            ep_indices = recording[ep_mask].index

            if level_warnings.empty:
                delays.append(float('nan'))
                continue

            ep_warns = level_warnings[level_warnings['window_idx'].isin(ep_indices)]
            valid_warns = ep_warns[recording.loc[ep_warns['window_idx'], 'true_label'].values == 1]

            if valid_warns.empty:
                delays.append(float('nan'))
                continue

            delay = valid_warns['time'].min() - ep['onset']
            delays.append(delay)
            if delay <= deadline:
                timely += 1

        metrics[f'{level}_timely'] = timely
        metrics[f'{level}_delay'] = np.nanmean(delays) if delays and not all(np.isnan(d) for d in delays) else float('nan')

        if not level_warnings.empty:
            warn_labels = recording.loc[level_warnings['window_idx'], 'true_label'].values
            is_false = warn_labels == 0
            false_times = level_warnings[is_false]['time'].values
            grouped_false = group_alerts(false_times, CONFIG['false_alert_grouping_window_s'])
        else:
            grouped_false = 0

        metrics[f'{level}_false_per_hr'] = grouped_false / normal_duration_hr

    return metrics

def main():
    CONFIG['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    print("Loading data...")
    preds = pd.read_csv("results/tables/all_predictions.csv")
    dev_preds = preds[preds['split'] == 'dev']
    test_preds = preds[preds['split'] == 'test']

    trace_cfg = CONFIG['network_traces'][0]
    try:
        trace_df = pd.read_excel(trace_cfg['path'], engine='openpyxl')
    except Exception:
        trace_df = pd.read_csv(trace_cfg['path'], engine='python', encoding='latin1')
    if 'pub_time(ms)' not in trace_df.columns:
        for col in trace_df.columns:
            if 'pub_time' in col.lower():
                trace_df = trace_df.rename(columns={col: 'pub_time(ms)'})
            if 'delay' in col.lower() and 'ms' in col.lower():
                trace_df = trace_df.rename(columns={col: 'delay(ms)'})

    trace_df['pub_time(ms)'] = pd.to_numeric(trace_df['pub_time(ms)'], errors='coerce')
    trace_df['delay(ms)'] = pd.to_numeric(trace_df['delay(ms)'], errors='coerce')
    trace_df = trace_df.dropna(subset=['pub_time(ms)', 'delay(ms)'])
    provider = TraceProvider(trace_df)

    recordings = {}
    for split_name, split_df in [('dev', dev_preds), ('test', test_preds)]:
        for rec_id, group in split_df.groupby('recording_id'):
            rec_df = group.sort_values('timestamp').reset_index(drop=True)
            episodes = extract_episodes(rec_df, CONFIG['episode_gap_tolerance_s'])
            recordings[f"{split_name}/{rec_id}"] = {
                'split': split_name,
                'recording_id': rec_id,
                'df': rec_df,
                'episodes': episodes
            }

    all_rows = []
    jobs = []
    for deadline in CONFIG['deadlines_s']:
        for budget in CONFIG['request_budgets_per_sec']:
            jobs.append({'budget': budget, 'deadline': deadline})

    print(f"Running {len(jobs)} jobs * {len(recordings)} recordings...")

    for i, job in enumerate(jobs):
        b_val = job['budget']
        d_val = job['deadline']

        for rec_key, rec_data in recordings.items():
            df_rec = rec_data['df']
            eps = rec_data['episodes']

            if b_val == "unlimited":
                bucket = UnlimitedBucket()
            else:
                bucket = TokenBucket(b_val)

            warnings, reqs = simulate_two_level(df_rec, provider, bucket)
            metrics = evaluate_run(df_rec, warnings, eps, d_val)

            row = {
                'split': rec_data['split'],
                'recording_id': rec_data['recording_id'],
                'budget': b_val,
                'deadline_s': d_val,
                'total_requests': len(reqs),
            }
            row.update(metrics)
            all_rows.append(row)

    runs_df = pd.DataFrame(all_rows)
    runs_df.to_csv(RESULTS_DIR / "all_runs.csv", index=False)

    # ========================================================================
    # CORRECTED SUMMARY — proper aggregation
    # ========================================================================
    # Split attack recordings from normal recordings so that:
    #   - detection rate  = timely detections / total attack episodes  (attack recs only)
    #   - false-alert rate = mean FA/hr across normal recordings       (normal recs only)
    #   - detection delay  = mean delay across attack recordings only
    # ========================================================================

    summary_rows = []
    for (split, budget, deadline), grp in runs_df.groupby(['split', 'budget', 'deadline_s']):
        attack_recs = grp[grp['attack_episodes'] > 0]
        normal_recs = grp[grp['attack_episodes'] == 0]

        total_episodes = attack_recs['attack_episodes'].sum()

        row = {
            'split': split,
            'budget': budget,
            'deadline_s': deadline,
            'attack_episodes': int(total_episodes),
            'n_attack_recordings': len(attack_recs),
            'n_normal_recordings': len(normal_recs),
        }

        for level in ['level1_local', 'level2_cloud']:
            # Detection rate — only from attack recordings
            timely_sum = attack_recs[f'{level}_timely'].sum()
            row[f'{level}_detect_rate'] = timely_sum / total_episodes if total_episodes > 0 else 0.0
            row[f'{level}_timely'] = int(timely_sum)

            # Detection delay — mean across attack recordings (NaN-safe)
            delays = attack_recs[f'{level}_delay'].dropna()
            row[f'{level}_delay'] = delays.mean() if len(delays) > 0 else float('nan')

            # False-alert rate — mean across normal recordings
            if len(normal_recs) > 0:
                row[f'{level}_false_per_hr'] = normal_recs[f'{level}_false_per_hr'].mean()
            else:
                # Fallback: use all recordings if no pure-normal ones exist
                row[f'{level}_false_per_hr'] = grp[f'{level}_false_per_hr'].mean()

        row['total_requests'] = int(grp['total_requests'].sum())
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(RESULTS_DIR / "summary.csv", index=False)

    # ========================================================================
    # Print key results
    # ========================================================================
    print("\nKEY RESULTS (Dev Split, 150ms deadline)")
    dev_150 = summary[(summary['split'] == 'dev') & (summary['deadline_s'] == 0.150)].copy()
    display_cols = [
        'budget', 'attack_episodes',
        'level1_local_detect_rate', 'level1_local_delay',
        'level1_local_false_per_hr',
        'level2_cloud_detect_rate', 'level2_cloud_delay',
        'level2_cloud_false_per_hr',
        'total_requests'
    ]
    print(dev_150[display_cols].to_string(index=False))

if __name__ == "__main__":
    main()
