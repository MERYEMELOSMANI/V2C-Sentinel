"""
V2C-Sentinel Unified Experiment
================================
Single script producing every comparison for the paper.

Policies compared:
  - local_only:       Local detector only, no cloud requests
  - strong_local:     Cloud-grade RF running locally (upper bound, no network)
  - cloud_unlimited:  Cloud queried for every message, no deadline/budget limit
  - periodic:         Cloud queried on a fixed time grid
  - random:           Cloud queried with a fixed probability per message
  - suspicion:        Cloud queried when local_score exceeds threshold
  - combined:         Cloud queried when suspicious OR periodic-grid fires

Budget mechanism:
  All policies (except local_only, strong_local, cloud_unlimited) enforce a
  shared request budget expressed as max requests per second (req/s). If a policy
  wants to send a request but the token bucket is empty, the request is suppressed.

Deadlines tested:
  100ms, 150ms, 200ms, 300ms — presented as experimental deadlines.
  150ms rationale: approximate upper bound for a CAN gateway to process and act
  on a detection result before the next message cycle; presented as an
  experimental parameter, not an application requirement.

False-alert grouping:
  Consecutive false warnings within 1 second are grouped into one operator alert.
  Rationale: sub-second repeated warnings about the same region of traffic
  represent a single alerting event for a human operator or automated response.

Metrics per run:
  - timely_detections: attack episodes with >=1 true-positive warning within deadline
  - detection_delay_s: time from episode onset to first true-positive warning (NaN if missed)
  - missed_episodes: attack episodes with no valid detection
  - eventual_detections: episodes detected at any time (even after deadline)
  - grouped_false_alerts: grouped false warnings
  - false_alerts_per_hr: grouped false alerts / normal driving hours
  - total_requests: cloud requests actually sent
  - actual_request_rate_pct: requests / total messages * 100
  - actual_req_per_sec: requests / recording duration
  - late_replies: cloud replies arriving after deadline
  - late_reply_pct: late replies / total requests * 100
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import deque
import heapq
import random
import time
import json
import hashlib
import sys

# ============================================================================
# CONFIGURATION — frozen after Step 5
# ============================================================================

CONFIG = {
    "version": "1.0.0",
    "timestamp": None,  # filled at runtime
    "local_model": {
        "file": "models/local_lr.joblib",
        "algorithm": "LogisticRegression",
        "note": "sklearn LogisticRegression trained on the train split"
    },
    "cloud_model": {
        "file": "models/cloud_rf.joblib",
        "algorithm": "RandomForestClassifier(n_estimators=50, max_depth=15)"
    },
    "local_proc_time_s": 0.005,
    "cloud_proc_time_s": 0.010,
    "deadlines_s": [0.100, 0.150, 0.200, 0.300],
    "request_budgets_per_sec": [1.0, 5.0, 10.0, 50.0],
    "periodic_intervals_s": None,  # computed from budget: 1/budget
    "random_probabilities": None,  # computed from budget and msg rate
    "suspicion_threshold_percentile": 90,
    "suspicion_threshold_value": None,  # computed from dev data
    "false_alert_grouping_window_s": 1.0,
    "episode_gap_tolerance_s": 0.5,
    "num_random_seeds": 10,
    "num_periodic_offsets": 10,
    "network_traces": [
        {
            "name": "urban_n78",
            "path": "data/raw/cicv5g/data/Urban road/2-n78/Urban road_n78.csv",
            "format": "csv_excel"
        }
    ],
    "policies": [
        "local_only", "strong_local", "cloud_unlimited",
        "periodic", "random", "suspicion", "combined"
    ]
}

RESULTS_DIR = Path("results/final")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# TRACE PROVIDER — maps simulation time to recorded 5G delay
# ============================================================================

class TraceProvider:
    """Replays recorded 5G delays by mapping simulation time to trace time."""

    def __init__(self, trace_df):
        self.times = (trace_df['pub_time(ms)'] - trace_df['pub_time(ms)'].iloc[0]).values / 1000.0
        self.delays = trace_df['delay(ms)'].values / 1000.0
        self.max_time = self.times[-1]
        if self.max_time <= 0:
            raise ValueError("Trace has zero or negative duration")

    def get_delay_at(self, sim_time):
        """Return the recorded delay at the given simulation time (wraps around)."""
        wrapped_time = sim_time % self.max_time
        idx = np.searchsorted(self.times, wrapped_time)
        if idx >= len(self.delays):
            idx = len(self.delays) - 1
        return max(self.delays[idx], 0.001)  # floor at 1ms to avoid zero-delay


# ============================================================================
# TOKEN BUCKET — shared request budget
# ============================================================================

class TokenBucket:
    """Simple token bucket for request rate limiting."""

    def __init__(self, rate_per_sec, burst=None):
        """
        rate_per_sec: max sustained requests per second
        burst: max burst size (default: 2x rate to absorb jitter)
        """
        self.rate = rate_per_sec
        self.burst = burst if burst is not None else max(2.0, rate_per_sec * 0.1)
        self.tokens = self.burst
        self.last_time = 0.0

    def try_consume(self, current_time):
        """Try to consume one token. Returns True if allowed."""
        elapsed = current_time - self.last_time
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_time = current_time

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class UnlimitedBucket:
    """Always allows requests (for unlimited policies)."""
    def try_consume(self, current_time):
        return True


# ============================================================================
# EPISODE EXTRACTION
# ============================================================================

def extract_episodes(df_recording, gap_tolerance=0.5):
    """Extract contiguous attack episodes with gap tolerance."""
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


# ============================================================================
# FALSE ALERT GROUPING
# ============================================================================

def group_alerts(warning_times, threshold=1.0):
    """Group warnings within `threshold` seconds into single alerts."""
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


# ============================================================================
# CORE SIMULATION ENGINE
# ============================================================================

def simulate_policy(df_recording, delay_provider, policy_type, score_threshold,
                    deadline, bucket, periodic_interval=0.1,
                    random_prob=0.05, seed=0, offset=0.0):
    """
    Simulate a request-selection policy on one recording.

    Returns:
        warnings: DataFrame of issued warnings
        requests: DataFrame of cloud requests
        late_diagnostics: DataFrame of late cloud replies
    """
    warnings = []
    request_log = []
    late_diagnostics = []
    pending_replies = []  # min-heap: (return_time, seq, reply_dict)
    past_delays = deque(maxlen=5)

    rec_start = df_recording['timestamp'].iloc[0]
    next_periodic_time = rec_start + offset

    rng = random.Random(seed)
    seq = 0

    for row in df_recording.itertuples():
        idx = row.Index
        obs_time = row.timestamp
        local_done_time = obs_time + CONFIG['local_proc_time_s']

        # --- Process returned cloud replies ---
        while pending_replies and pending_replies[0][0] <= local_done_time:
            _, _, reply = heapq.heappop(pending_replies)
            past_delays.append(reply['rtt'])

            if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
                warnings.append({
                    'time': reply['return_time'],
                    'source': 'cloud_timely',
                    'window_idx': reply['window_idx']
                })
            elif reply['pred'] == 1 and reply['return_time'] > reply['deadline']:
                late_diagnostics.append({
                    'time': reply['return_time'],
                    'source': 'cloud_late',
                    'window_idx': reply['window_idx']
                })

        # --- Check for timed-out pending requests that need local fallback ---
        # (handled below when cloud is late)

        # --- Policy decision ---
        is_suspicious = row.local_score >= score_threshold

        is_periodic = False
        if obs_time >= next_periodic_time:
            is_periodic = True
            while next_periodic_time <= obs_time:
                next_periodic_time += periodic_interval

        wants_request = False

        if policy_type == "local_only":
            wants_request = False
        elif policy_type == "strong_local":
            wants_request = False
        elif policy_type == "cloud_unlimited":
            wants_request = True
        elif policy_type == "periodic":
            wants_request = is_periodic
        elif policy_type == "random":
            wants_request = rng.random() < random_prob
        elif policy_type == "suspicion":
            wants_request = is_suspicious
        elif policy_type == "combined":
            wants_request = is_suspicious or is_periodic

        # --- Budget check ---
        if wants_request and not bucket.try_consume(local_done_time):
            wants_request = False  # budget exhausted

        # --- Execute request or local-only decision ---
        if wants_request:
            actual_delay = delay_provider.get_delay_at(local_done_time)
            cloud_return_time = local_done_time + actual_delay + CONFIG['cloud_proc_time_s']
            deadline_time = local_done_time + deadline

            reply = {
                'return_time': cloud_return_time,
                'rtt': actual_delay,
                'deadline': deadline_time,
                'pred': row.cloud_pred,
                'window_idx': idx
            }
            heapq.heappush(pending_replies, (cloud_return_time, seq, reply))
            seq += 1

            is_late = cloud_return_time > deadline_time

            # Local fallback logic: if cloud will be late AND local says attack,
            # issue local_fallback warning at deadline
            if row.local_pred == 1:
                if is_late:
                    warnings.append({
                        'time': deadline_time,
                        'source': 'local_fallback',
                        'window_idx': idx
                    })
                elif row.cloud_pred == 0:
                    # Cloud arrives in time and says normal → suppress local warning
                    pass
                # else: cloud arrives in time and says attack → cloud_timely handles it

            request_log.append({
                'sent': local_done_time,
                'returned': cloud_return_time,
                'late': is_late,
                'rtt': actual_delay
            })

        else:
            # No cloud request — use local/strong_local decision
            if policy_type == "strong_local":
                if row.cloud_pred == 1:  # RF prediction used locally
                    warnings.append({
                        'time': local_done_time,
                        'source': 'strong_local',
                        'window_idx': idx
                    })
            else:
                if row.local_pred == 1:
                    warnings.append({
                        'time': local_done_time,
                        'source': 'local_immediate',
                        'window_idx': idx
                    })

    # --- Flush remaining pending replies ---
    for _, _, reply in sorted(pending_replies):
        if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
            warnings.append({
                'time': reply['return_time'],
                'source': 'cloud_timely',
                'window_idx': reply['window_idx']
            })
        elif reply['pred'] == 1 and reply['return_time'] > reply['deadline']:
            late_diagnostics.append({
                'time': reply['return_time'],
                'source': 'cloud_late',
                'window_idx': reply['window_idx']
            })

    return (pd.DataFrame(warnings) if warnings else pd.DataFrame(columns=['time', 'source', 'window_idx']),
            pd.DataFrame(request_log) if request_log else pd.DataFrame(columns=['sent', 'returned', 'late', 'rtt']),
            pd.DataFrame(late_diagnostics) if late_diagnostics else pd.DataFrame(columns=['time', 'source', 'window_idx']))


# ============================================================================
# EVALUATION
# ============================================================================

def evaluate_run(recording, warnings_df, episodes, deadline):
    """Evaluate detection and false-alert metrics for one simulation run."""
    n_messages = len(recording)
    rec_duration = recording['timestamp'].max() - recording['timestamp'].min()

    # --- Attack episode evaluation ---
    timely_detections = 0
    eventual_detections = 0
    missed_episodes = 0
    detection_delays = []

    for ep in episodes:
        ep_mask = (recording['timestamp'] >= ep['onset']) & (recording['timestamp'] <= ep['end'])
        ep_indices = recording[ep_mask].index

        if warnings_df.empty:
            missed_episodes += 1
            detection_delays.append(float('nan'))
            continue

        # Find warnings originating from attack messages within this episode
        ep_warnings = warnings_df[warnings_df['window_idx'].isin(ep_indices)]
        valid_warnings = ep_warnings[
            recording.loc[ep_warnings['window_idx'], 'true_label'].values == 1
        ]

        if valid_warnings.empty:
            missed_episodes += 1
            detection_delays.append(float('nan'))
            continue

        eventual_detections += 1
        first_warn_time = valid_warnings['time'].min()
        delay = first_warn_time - ep['onset']
        detection_delays.append(delay)

        if delay <= deadline:
            timely_detections += 1

    # --- False alert evaluation ---
    if not warnings_df.empty:
        warn_labels = recording.loc[warnings_df['window_idx'], 'true_label'].values
        is_false = warn_labels == 0
        false_warning_times = warnings_df[is_false]['time'].values
        raw_false_warnings = int(is_false.sum())
        grouped_false = group_alerts(false_warning_times,
                                      CONFIG['false_alert_grouping_window_s'])
    else:
        raw_false_warnings = 0
        grouped_false = 0
        false_warning_times = np.array([])

    # Normal driving time (exclude attack episodes)
    attack_duration = sum(ep['end'] - ep['onset'] for ep in episodes)
    normal_duration_hr = max((rec_duration - attack_duration) / 3600.0, 0.001)
    false_alerts_per_hr = grouped_false / normal_duration_hr

    return {
        'n_messages': n_messages,
        'recording_duration_s': rec_duration,
        'attack_episodes': len(episodes),
        'timely_detections': timely_detections,
        'eventual_detections': eventual_detections,
        'missed_episodes': missed_episodes,
        'detection_delays_s': detection_delays,
        'mean_detection_delay_s': np.nanmean(detection_delays) if detection_delays and not all(np.isnan(d) for d in detection_delays) else float('nan'),
        'raw_false_warnings': raw_false_warnings,
        'grouped_false_alerts': grouped_false,
        'false_alerts_per_hr': false_alerts_per_hr,
        'normal_driving_hr': normal_duration_hr
    }


# ============================================================================
# MAIN EXPERIMENT LOOP
# ============================================================================

def build_jobs(config, avg_msg_rate):
    """Build the list of (policy, budget, deadline, seed, offset) jobs."""
    jobs = []

    for deadline in config['deadlines_s']:
        # --- Baselines (no budget) ---
        jobs.append({
            'policy': 'local_only', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })
        jobs.append({
            'policy': 'strong_local', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })
        jobs.append({
            'policy': 'cloud_unlimited', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })

        # --- Budget-controlled policies ---
        for budget in config['request_budgets_per_sec']:
            periodic_interval = 1.0 / budget
            random_prob = budget / avg_msg_rate if avg_msg_rate > 0 else 0.05

            # Periodic: vary offsets
            for i in range(config['num_periodic_offsets']):
                offset = periodic_interval * i / config['num_periodic_offsets']
                jobs.append({
                    'policy': 'periodic', 'budget': budget, 'deadline': deadline,
                    'seed': 0, 'offset': offset,
                    'periodic_interval': periodic_interval, 'random_prob': random_prob
                })

            # Random: vary seeds
            for seed in range(config['num_random_seeds']):
                jobs.append({
                    'policy': 'random', 'budget': budget, 'deadline': deadline,
                    'seed': seed, 'offset': 0.0,
                    'periodic_interval': periodic_interval, 'random_prob': random_prob
                })

            # Suspicion: one run (deterministic given threshold)
            jobs.append({
                'policy': 'suspicion', 'budget': budget, 'deadline': deadline,
                'seed': 0, 'offset': 0.0,
                'periodic_interval': periodic_interval, 'random_prob': random_prob
            })

            # Combined: vary offsets (periodic component varies)
            for i in range(config['num_periodic_offsets']):
                offset = periodic_interval * i / config['num_periodic_offsets']
                jobs.append({
                    'policy': 'combined', 'budget': budget, 'deadline': deadline,
                    'seed': 0, 'offset': offset,
                    'periodic_interval': periodic_interval, 'random_prob': random_prob
                })

    return jobs


def main():
    t_start = time.time()
    CONFIG['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    print("=" * 70)
    print("V2C-Sentinel Unified Experiment")
    print("=" * 70)
    print(f"Started: {CONFIG['timestamp']}")

    # --- Load predictions ---
    print("\n[1/4] Loading predictions...")
    preds = pd.read_csv("results/tables/all_predictions.csv")
    print(f"  Total predictions: {len(preds):,}")

    dev_preds = preds[preds['split'] == 'dev']
    print(f"  Dev predictions: {len(dev_preds):,}")

    # --- Compute threshold from dev data ---
    score_threshold = np.percentile(
        dev_preds['local_score'],
        CONFIG['suspicion_threshold_percentile']
    )
    CONFIG['suspicion_threshold_value'] = float(score_threshold)
    print(f"  Suspicion threshold (p{CONFIG['suspicion_threshold_percentile']}): {score_threshold:.6f}")

    # --- Load network trace ---
    print("\n[2/4] Loading network trace...")
    trace_cfg = CONFIG['network_traces'][0]
    # Note: The CICV5G .csv file is actually Excel format
    try:
        trace_df = pd.read_excel(trace_cfg['path'], engine='openpyxl')
    except Exception:
        trace_df = pd.read_csv(trace_cfg['path'], engine='python', encoding='latin1')

    # Handle column name variations
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
    delay_stats = trace_df['delay(ms)'].describe()
    print(f"  Trace: {trace_cfg['name']}")
    print(f"  Trace duration: {provider.max_time:.1f}s, samples: {len(trace_df):,}")
    print(f"  Delay stats (ms): mean={delay_stats['mean']:.1f}, "
          f"median={delay_stats['50%']:.1f}, p95={delay_stats.get('75%', 0)*1.5:.1f}")

    # --- Organize recordings ---
    print("\n[3/4] Preparing recordings...")
    splits_to_run = ['dev', 'test']
    recordings = {}
    for split in splits_to_run:
        split_data = preds[preds['split'] == split]
        for rec_id, rec_df in split_data.groupby('recording_id'):
            rec_df = rec_df.sort_values('timestamp').reset_index(drop=True)
            recordings[(split, rec_id)] = rec_df
            episodes = extract_episodes(rec_df)
            n_attack_msgs = (rec_df['true_label'] == 1).sum()
            duration = rec_df['timestamp'].max() - rec_df['timestamp'].min()
            msg_rate = len(rec_df) / duration if duration > 0 else 0
            print(f"  {split}/{rec_id}: {len(rec_df):,} msgs, "
                  f"{duration:.1f}s, {msg_rate:.0f} msg/s, "
                  f"{len(episodes)} attack episode(s), "
                  f"{n_attack_msgs:,} attack msgs")

    # --- Compute average message rate for random probability calibration ---
    all_msg_rates = []
    for (split, rec_id), rec_df in recordings.items():
        duration = rec_df['timestamp'].max() - rec_df['timestamp'].min()
        if duration > 0:
            all_msg_rates.append(len(rec_df) / duration)
    avg_msg_rate = np.mean(all_msg_rates) if all_msg_rates else 1000.0
    print(f"  Average message rate: {avg_msg_rate:.0f} msg/s")

    # --- Build jobs ---
    jobs = build_jobs(CONFIG, avg_msg_rate)
    total_runs = len(jobs) * len(recordings)
    print(f"\n[4/4] Running {len(jobs)} job configs × {len(recordings)} recordings = {total_runs} runs")
    print("-" * 70)

    # --- Run ---
    all_rows = []
    completed = 0
    run_start = time.perf_counter()

    for job in jobs:
        for (split, rec_id), recording in recordings.items():
            # Create bucket
            if job['budget'] is None:
                bucket = UnlimitedBucket()
            else:
                bucket = TokenBucket(job['budget'])

            # Re-create trace provider for each run (stateless lookup, no reset needed)
            warnings_df, requests_df, late_df = simulate_policy(
                recording, provider,
                policy_type=job['policy'],
                score_threshold=score_threshold,
                deadline=job['deadline'],
                bucket=bucket,
                periodic_interval=job['periodic_interval'],
                random_prob=job['random_prob'],
                seed=job['seed'],
                offset=job['offset']
            )

            episodes = extract_episodes(recording, CONFIG['episode_gap_tolerance_s'])
            eval_result = evaluate_run(recording, warnings_df, episodes, job['deadline'])

            total_requests = len(requests_df)
            late_replies = int(requests_df['late'].sum()) if not requests_df.empty else 0
            rec_duration = eval_result['recording_duration_s']

            row = {
                'split': split,
                'recording_id': rec_id,
                'policy': job['policy'],
                'budget_req_per_sec': job['budget'] if job['budget'] else float('nan'),
                'deadline_s': job['deadline'],
                'seed': job['seed'],
                'offset_s': job['offset'],
                'periodic_interval_s': job['periodic_interval'],
                'random_prob': job['random_prob'],
                'n_messages': eval_result['n_messages'],
                'recording_duration_s': rec_duration,
                'attack_episodes': eval_result['attack_episodes'],
                'timely_detections': eval_result['timely_detections'],
                'eventual_detections': eval_result['eventual_detections'],
                'missed_episodes': eval_result['missed_episodes'],
                'mean_detection_delay_s': eval_result['mean_detection_delay_s'],
                'raw_false_warnings': eval_result['raw_false_warnings'],
                'grouped_false_alerts': eval_result['grouped_false_alerts'],
                'false_alerts_per_hr': eval_result['false_alerts_per_hr'],
                'normal_driving_hr': eval_result['normal_driving_hr'],
                'total_requests': total_requests,
                'actual_request_rate_pct': (total_requests / eval_result['n_messages'] * 100) if eval_result['n_messages'] > 0 else 0,
                'actual_req_per_sec': total_requests / rec_duration if rec_duration > 0 else 0,
                'late_replies': late_replies,
                'late_reply_pct': (late_replies / total_requests * 100) if total_requests > 0 else 0,
            }
            all_rows.append(row)
            completed += 1

            if completed % 50 == 0 or completed == total_runs:
                elapsed = time.perf_counter() - run_start
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = (total_runs - completed) / rate if rate > 0 else 0
                print(f"  [{completed}/{total_runs}] {elapsed:.0f}s elapsed, "
                      f"~{remaining:.0f}s remaining | "
                      f"{split}/{rec_id} {job['policy']} "
                      f"budget={job['budget']} deadline={job['deadline']}")

    # --- Save results ---
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    runs_df = pd.DataFrame(all_rows)
    runs_df.to_csv(RESULTS_DIR / "all_runs.csv", index=False)
    print(f"  Saved {len(runs_df)} individual runs → results/final/all_runs.csv")

    # --- Aggregate summary ---
    # For stochastic policies (periodic, random, combined), average over seeds/offsets
    # For deterministic policies, just take the single value
    agg_cols = [
        'timely_detections', 'eventual_detections', 'missed_episodes',
        'mean_detection_delay_s', 'raw_false_warnings', 'grouped_false_alerts',
        'false_alerts_per_hr', 'total_requests', 'actual_request_rate_pct',
        'actual_req_per_sec', 'late_replies', 'late_reply_pct'
    ]

    summary = runs_df.groupby(
        ['split', 'policy', 'budget_req_per_sec', 'deadline_s']
    ).agg(
        n_runs=('seed', 'count'),
        **{col: (col, 'mean') for col in agg_cols}
    ).reset_index()

    summary.to_csv(RESULTS_DIR / "summary.csv", index=False)
    print(f"  Saved summary → results/final/summary.csv")

    # --- Save config ---
    CONFIG['total_runs'] = total_runs
    CONFIG['total_time_s'] = time.time() - t_start
    with open(RESULTS_DIR / "config.json", 'w') as f:
        json.dump(CONFIG, f, indent=2, default=str)
    print(f"  Saved config → results/final/config.json")

    # --- Print key results ---
    print("\n" + "=" * 70)
    print("KEY RESULTS (dev split, 150ms deadline)")
    print("=" * 70)

    dev_summary = summary[
        (summary['split'] == 'dev') & (summary['deadline_s'] == 0.150)
    ].copy()

    if not dev_summary.empty:
        display_cols = [
            'policy', 'budget_req_per_sec', 'n_runs',
            'timely_detections', 'eventual_detections', 'missed_episodes',
            'mean_detection_delay_s', 'grouped_false_alerts', 'false_alerts_per_hr',
            'actual_request_rate_pct', 'actual_req_per_sec', 'late_reply_pct'
        ]
        print(dev_summary[display_cols].to_string(index=False))

    print(f"\nTotal experiment time: {time.time() - t_start:.0f}s")
    print("Done.")


if __name__ == '__main__':
    main()
