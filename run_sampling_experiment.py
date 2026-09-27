import pandas as pd
import numpy as np
from pathlib import Path
from collections import deque
import random

RESULTS = Path("results/tables")
LOCAL_PROC_TIME = 0.005
CLOUD_PROC_TIME = 0.010
POLICY_TIMEOUT = 0.150 
PERIODIC_INTERVAL = 0.100

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

def extract_episodes(df_recording, gap_tolerance=0.5):
    is_attack = df_recording['true_label'] == 1
    attack_times = df_recording[is_attack]['timestamp'].values
    if len(attack_times) == 0: return []
    episodes, onset, last_t = [], attack_times[0], attack_times[0]
    for t in attack_times[1:]:
        if t - last_t > gap_tolerance:
            episodes.append({'onset': onset, 'end': last_t})
            onset = t
        last_t = t
    episodes.append({'onset': onset, 'end': last_t})
    return episodes

def simulate_policy(df_recording, delay_provider, policy_type, score_threshold, seed=0, offset=0.0):
    warnings, requests, pending_replies, past_delays = [], [], [], deque(maxlen=5)
    last_periodic_time = -1.0 + offset
    random.seed(seed)
    
    for row in df_recording.itertuples():
        idx, obs_time = row.Index, row.timestamp
        local_done_time = obs_time + LOCAL_PROC_TIME
        
        while pending_replies and pending_replies[0]['return_time'] <= local_done_time:
            reply = pending_replies.pop(0)
            past_delays.append(reply['rtt'])
            if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
                warnings.append({'time': reply['return_time'], 'source': 'cloud_timely', 'window_idx': reply['window_idx']})
        
        est_delay = sum(past_delays)/len(past_delays) if past_delays else 0.050
        is_suspicious = row.local_score >= score_threshold
        delay_good = (est_delay + CLOUD_PROC_TIME) <= POLICY_TIMEOUT
        
        is_periodic = (local_done_time - last_periodic_time) >= PERIODIC_INTERVAL
        
        wants_request = False
        if policy_type == "periodic_sampling": wants_request = is_periodic
        elif policy_type == "random_sampling": wants_request = random.random() < 0.05
        elif policy_type == "suspicion_plus_periodic": wants_request = is_suspicious or is_periodic
            
        if wants_request:
            if is_periodic: last_periodic_time = local_done_time
            actual_delay = delay_provider.get_delay_at(local_done_time)
            cloud_return_time = local_done_time + actual_delay + CLOUD_PROC_TIME
            deadline = local_done_time + POLICY_TIMEOUT
            
            pending_replies.append({'return_time': cloud_return_time, 'rtt': actual_delay, 'deadline': deadline, 'pred': row.cloud_pred, 'window_idx': idx})
            pending_replies.sort(key=lambda x: x['return_time'])
            
            if row.local_pred == 1 and cloud_return_time > deadline:
                warnings.append({'time': deadline, 'source': 'local_fallback', 'window_idx': idx})
                
            requests.append({'sent': local_done_time, 'returned': cloud_return_time})
        else:
            if row.local_pred == 1: warnings.append({'time': local_done_time, 'source': 'local_immediate', 'window_idx': idx})
                
    for reply in pending_replies:
        if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
            warnings.append({'time': reply['return_time'], 'source': 'cloud_timely', 'window_idx': reply['window_idx']})
            
    return pd.DataFrame(warnings), pd.DataFrame(requests)

if __name__ == "__main__":
    preds = pd.read_csv(RESULTS / "all_predictions.csv")
    dev_preds = preds[preds['split'] == 'dev']
    SCORE_THRESHOLD = np.percentile(dev_preds['local_score'], 90)
    delay_df = pd.read_excel("data/raw/cicv5g/data/Urban road/2-n78/Urban road_n78.csv", engine='openpyxl')
    provider = TraceProvider(delay_df)
    
    results = []
    
    for rec_id, rec_df in dev_preds.groupby('recording_id'):
        rec_df = rec_df.sort_values('timestamp').reset_index(drop=True)
        episodes = extract_episodes(rec_df)
        
        # Periodic over 10 offsets (0 to 90ms)
        for offset in np.linspace(0, 0.09, 10):
            w, r = simulate_policy(rec_df, provider, "periodic_sampling", SCORE_THRESHOLD, offset=offset)
            results.append({'policy': 'periodic', 'rec': rec_id, 'requests': len(r), 'run': offset, 'warnings': w})
            
        # Random over 10 seeds
        for seed in range(10):
            w, r = simulate_policy(rec_df, provider, "random_sampling", SCORE_THRESHOLD, seed=seed)
            results.append({'policy': 'random', 'rec': rec_id, 'requests': len(r), 'run': seed, 'warnings': w})
            
        # Suspicion + Periodic over 10 offsets
        for offset in np.linspace(0, 0.09, 10):
            w, r = simulate_policy(rec_df, provider, "suspicion_plus_periodic", SCORE_THRESHOLD, offset=offset)
            results.append({'policy': 'suspicion+periodic', 'rec': rec_id, 'requests': len(r), 'run': offset, 'warnings': w})
            
    # Evaluate aggregate
    summary_rows = []
    for (policy, rec_id), group in pd.DataFrame(results).groupby(['policy', 'rec']):
        total_requests = group['requests'].mean()
        rec_df = dev_preds[dev_preds['recording_id'] == rec_id].sort_values('timestamp').reset_index(drop=True)
        episodes = extract_episodes(rec_df)
        
        avg_timely = 0
        avg_eventual = 0
        for w_df in group['warnings']:
            if len(w_df) == 0: continue
            for ep in episodes:
                ep_warns = w_df[w_df['window_idx'].isin(rec_df[(rec_df['timestamp'] >= ep['onset']) & (rec_df['timestamp'] <= ep['end'])].index)]
                valid_warns = ep_warns[rec_df.loc[ep_warns['window_idx'], 'true_label'].values == 1]
                if len(valid_warns) > 0:
                    avg_eventual += 1
                    if len(valid_warns[(valid_warns['time'] - ep['onset']) <= POLICY_TIMEOUT]) > 0:
                        avg_timely += 1
                        
        summary_rows.append({
            'policy': policy,
            'recording': rec_id,
            'requests': total_requests,
            'request_rate_%': (total_requests / len(rec_df)) * 100,
            'timely_detections': avg_timely / 10.0,
            'eventual_detections': avg_eventual / 10.0
        })

    agg = pd.DataFrame(summary_rows).groupby('policy').sum(numeric_only=True).reset_index()
    agg['request_rate_%'] = agg['requests'] / len(dev_preds) * 100
    print(agg[['policy', 'request_rate_%', 'timely_detections', 'eventual_detections']])
