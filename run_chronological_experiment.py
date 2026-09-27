import pandas as pd
import numpy as np
from pathlib import Path
from collections import deque
import random
import time

RESULTS = Path("results/tables")
RESULTS.mkdir(parents=True, exist_ok=True)

# Hardware/Network constants
LOCAL_PROC_TIME = 0.005 # 5ms local execution
CLOUD_PROC_TIME = 0.010 # 10ms cloud inference
POLICY_TIMEOUT = 0.150 
PERIODIC_INTERVAL = 0.100 # sample every 100ms
RANDOM_PROBABILITY = 0.05 # 5% chance per message

class TraceProvider:
    def __init__(self, trace_df):
        self.times = (trace_df['pub_time(ms)'] - trace_df['pub_time(ms)'].iloc[0]).values / 1000.0
        self.delays = (trace_df['delay(ms)'].values / 1000.0)
        self.max_time = self.times[-1]

    def get_delay_at(self, sim_time):
        wrapped_time = sim_time % self.max_time
        idx = np.searchsorted(self.times, wrapped_time)
        if idx >= len(self.delays):
            idx = len(self.delays) - 1
        return self.delays[idx]

def simulate_chronological_replay(df_recording, delay_provider, policy_type, score_threshold):
    warnings = []
    late_diagnostic = []
    requests = []
    
    pending_replies = []
    past_delays = deque(maxlen=5)
    
    last_periodic_time = -1.0
    random.seed(42) # fixed seed for reproducibility
    
    for row in df_recording.itertuples():
        idx = row.Index
        obs_time = row.timestamp
        local_done_time = obs_time + LOCAL_PROC_TIME
        
        # Process returned cloud replies
        while pending_replies and pending_replies[0]['return_time'] <= local_done_time:
            reply = pending_replies.pop(0)
            past_delays.append(reply['rtt']) # update est_delay with actual returned RTT
            
            if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
                warnings.append({'time': reply['return_time'], 'source': 'cloud_timely', 'window_idx': reply['window_idx']})
            elif reply['pred'] == 1 and reply['return_time'] > reply['deadline']:
                late_diagnostic.append({'time': reply['return_time'], 'source': 'cloud_late', 'window_idx': reply['window_idx']})
        
        est_delay = sum(past_delays)/len(past_delays) if past_delays else 0.050
        
        # Policy logic
        wants_request = False
        is_suspicious = row.local_score >= score_threshold
        delay_good = (est_delay + CLOUD_PROC_TIME) <= POLICY_TIMEOUT
        
        # Exact-delay ideal benchmark
        ideal_delay = delay_provider.get_delay_at(local_done_time)
        ideal_delay_good = (ideal_delay + CLOUD_PROC_TIME) <= POLICY_TIMEOUT
        
        # Periodic logic
        time_since_last = local_done_time - last_periodic_time
        is_periodic = time_since_last >= PERIODIC_INTERVAL
        
        if policy_type == "local_only":
            wants_request = False
        elif policy_type == "cloud_always_ideal":
            wants_request = ideal_delay_good
        elif policy_type == "cloud_always_est":
            wants_request = delay_good
        elif policy_type == "suspicion_only":
            wants_request = is_suspicious
        elif policy_type == "delay_only":
            wants_request = delay_good
        elif policy_type == "proposed_ideal":
            wants_request = is_suspicious and ideal_delay_good
        elif policy_type == "proposed_est":
            wants_request = is_suspicious and delay_good
        elif policy_type == "periodic_sampling":
            wants_request = is_periodic
        elif policy_type == "random_sampling":
            wants_request = random.random() < RANDOM_PROBABILITY
        elif policy_type == "suspicion_plus_periodic":
            wants_request = is_suspicious or is_periodic
            
        if wants_request:
            if is_periodic:
                last_periodic_time = local_done_time
                
            actual_delay = delay_provider.get_delay_at(local_done_time)
            cloud_return_time = local_done_time + actual_delay + CLOUD_PROC_TIME
            deadline_time = local_done_time + POLICY_TIMEOUT
            
            pending_replies.append({
                'return_time': cloud_return_time, 
                'rtt': actual_delay,
                'deadline': deadline_time,
                'pred': row.cloud_pred,
                'window_idx': idx
            })
            pending_replies.sort(key=lambda x: x['return_time'])
            
            # Local fallback is evaluated immediately AT the deadline if the cloud isn't back
            # We can just schedule a local fallback warning if local_pred == 1
            if row.local_pred == 1:
                # We add this to warnings as a scheduled fallback. If cloud arrives and says 0, it doesn't matter, 
                # we already deferred the decision to the deadline.
                # Wait, if cloud arrives BEFORE deadline and says 0, does it suppress the local fallback?
                # YES. If cloud replies in time, its answer replaces the local decision.
                # Since we don't have a robust event queue, we can just say: if cloud says 0 and is timely, it suppresses.
                # If cloud is late, we MUST output local_fallback at the deadline.
                if cloud_return_time > deadline_time:
                    warnings.append({'time': deadline_time, 'source': 'local_fallback', 'window_idx': idx})
                elif cloud_return_time <= deadline_time and row.cloud_pred == 0:
                    # Cloud suppressed it in time. Do nothing.
                    pass
                
            requests.append({'sent': local_done_time, 'returned': cloud_return_time, 'late': cloud_return_time > deadline_time})
        else:
            # Local immediate
            if row.local_pred == 1:
                warnings.append({'time': local_done_time, 'source': 'local_immediate', 'window_idx': idx})
                
    # Flush remaining
    for reply in pending_replies:
        if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
            warnings.append({'time': reply['return_time'], 'source': 'cloud_timely', 'window_idx': reply['window_idx']})
        elif reply['pred'] == 1 and reply['return_time'] > reply['deadline']:
            late_diagnostic.append({'time': reply['return_time'], 'source': 'cloud_late', 'window_idx': reply['window_idx']})
            
    return pd.DataFrame(warnings), pd.DataFrame(requests), pd.DataFrame(late_diagnostic)

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
    if len(warning_times) == 0: return 0
    times = sorted(warning_times)
    alerts = 1
    last_alert = times[0]
    for t in times[1:]:
        if t - last_alert > threshold:
            alerts += 1
            last_alert = t
    return alerts

if __name__ == "__main__":
    preds = pd.read_csv(RESULTS / "all_predictions.csv")
    dev_preds = preds[preds['split'] == 'dev']
    SCORE_THRESHOLD = np.percentile(dev_preds['local_score'], 90)
    
    delay_df = pd.read_excel("data/raw/cicv5g/data/Urban road/2-n78/Urban road_n78.csv", engine='openpyxl')
    provider = TraceProvider(delay_df)
    
    policies = [
        "local_only", "cloud_always_est", "suspicion_only", 
        "proposed_est", "periodic_sampling", "random_sampling", "suspicion_plus_periodic"
    ]
    
    summary_rows = []
    
    for policy in policies:
        for rec_id, rec_df in dev_preds.groupby('recording_id'):
            rec_df = rec_df.sort_values('timestamp').reset_index(drop=True)
            recording_duration = rec_df['timestamp'].max() - rec_df['timestamp'].min()
            
            # calculate normal driving time (excluding attack episodes)
            episodes = extract_episodes(rec_df)
            attack_duration = sum((ep['end'] - ep['onset']) for ep in episodes)
            normal_duration_hr = (recording_duration - attack_duration) / 3600.0
            if normal_duration_hr <= 0: normal_duration_hr = 0.001
            
            warnings_df, reqs_df, late_df = simulate_chronological_replay(rec_df, provider, policy, SCORE_THRESHOLD)
            
            # False alerts evaluation
            false_warnings = 0
            grouped_false_alerts = 0
            if len(warnings_df) > 0:
                warn_labels = rec_df.loc[warnings_df['window_idx'], 'true_label'].values
                is_false = (warn_labels == 0)
                false_warnings = is_false.sum()
                false_warning_times = warnings_df[is_false]['time'].values
                grouped_false_alerts = group_alerts(false_warning_times, threshold=1.0)
                
            false_alerts_per_hr = grouped_false_alerts / normal_duration_hr
            
            timely_detections = 0
            missed = 0
            
            for ep in episodes:
                if len(warnings_df) > 0:
                    ep_warnings = warnings_df[warnings_df['window_idx'].isin(
                        rec_df[(rec_df['timestamp'] >= ep['onset']) & (rec_df['timestamp'] <= ep['end'])].index
                    )]
                    # Require an attack-labelled originating message (true_label == 1) for a true detection
                    valid_ep_warnings = ep_warnings[rec_df.loc[ep_warnings['window_idx'], 'true_label'].values == 1]
                    
                    timely_ep_warnings = valid_ep_warnings[(valid_ep_warnings['time'] - ep['onset']) <= POLICY_TIMEOUT]
                    
                    if len(timely_ep_warnings) > 0:
                        timely_detections += 1
                    else:
                        missed += 1
                else:
                    missed += 1
                    
            summary_rows.append({
                'policy': policy,
                'requests': len(reqs_df),
                'request_rate_%': (len(reqs_df) / len(rec_df)) * 100,
                'msg_false_warns': false_warnings,
                'grouped_false_alerts': grouped_false_alerts,
                'false_alerts_per_hr': false_alerts_per_hr,
                'attack_episodes': len(episodes),
                'timely_detections': timely_detections,
                'missed': missed
            })

    summary_df = pd.DataFrame(summary_rows)
    agg = summary_df.groupby('policy').sum(numeric_only=True).reset_index()
    agg['request_rate_%'] = agg['requests'] / len(dev_preds) * 100
    total_normal_hr = sum(
        ( (g['timestamp'].max() - g['timestamp'].min()) - sum((e['end']-e['onset']) for e in extract_episodes(g)) ) / 3600.0 
        for _, g in dev_preds.groupby('recording_id')
    )
    agg['false_alerts_per_hr'] = agg['grouped_false_alerts'] / total_normal_hr
    
    print("\n--- NEW POLICY EXPERIMENT RESULTS (DEV) ---")
    print(agg[['policy', 'request_rate_%', 'grouped_false_alerts', 'false_alerts_per_hr', 'timely_detections', 'missed']])
    agg.to_csv(RESULTS / "dev_policy_sweep.csv", index=False)
