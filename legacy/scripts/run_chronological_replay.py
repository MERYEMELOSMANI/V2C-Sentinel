import pandas as pd
import numpy as np
from pathlib import Path
from collections import deque

RESULTS = Path("results/tables")

# Load Test Predictions
preds = pd.read_csv(RESULTS / "all_predictions.csv")
# For the chronological pilot, let's use the 'dev' split to tune/evaluate
dev_preds = preds[preds['split'] == 'dev'].copy()

# Load Real Delay Trace sequentially
delay_df = pd.read_excel("data/raw/cicv5g/data/Urban road/2-n78/Urban road_n78.csv", engine='openpyxl')
delay_col = next(c for c in delay_df.columns if 'delay(ms)' in c or 'delay' in c.lower())
delay_trace_seconds = (delay_df[delay_col].dropna().astype(float) / 1000.0).to_numpy()

class TraceProvider:
    def __init__(self, delays):
        self.delays = delays
        self.idx = 0
        self.length = len(delays)
    def get_next_delay(self):
        d = self.delays[self.idx]
        self.idx = (self.idx + 1) % self.length
        return d

# Hardware/Network constants
LOCAL_PROC_TIME = 0.005 # 5ms local execution
CLOUD_PROC_TIME = 0.010 # 10ms cloud inference
MAX_PENDING = 1

# Policy Parameters
POLICY_TIMEOUT = 0.150 # Policy won't request if it thinks delay > 150ms
SCORE_THRESHOLD = np.percentile(dev_preds['local_score'], 90) # fixed threshold

def simulate_chronological_replay(df_recording, delay_provider, policy_type="proposed"):
    # Output structure: list of warnings [timestamp, source, window_idx]
    warnings = []
    # Log of requests [sent_time, return_time, used_for_warning]
    requests = []
    
    pending_replies = [] # list of dicts: {'return_time': float, 'pred': int, 'window_idx': int}
    
    # Connection estimator (last N delays)
    past_delays = deque(maxlen=5)
    
    for row in df_recording.itertuples():
        idx = row.Index
        obs_time = row.timestamp
        local_done_time = obs_time + LOCAL_PROC_TIME
        
        # 1. Process any replies that arrived BEFORE or EXACTLY WHEN local processing finished
        # We need to process replies as time marches forward.
        while pending_replies and pending_replies[0]['return_time'] <= local_done_time:
            reply = pending_replies.pop(0)
            if reply['pred'] == 1:
                warnings.append({'time': reply['return_time'], 'source': 'cloud', 'window_idx': reply['window_idx']})
        
        # 2. Local detector evaluation
        if row.local_pred == 1:
            warnings.append({'time': local_done_time, 'source': 'local', 'window_idx': idx})
            
        # 3. Policy decision to request cloud
        # Estimate delay
        est_delay = sum(past_delays)/len(past_delays) if past_delays else 0.050
        
        wants_request = False
        if policy_type == "local_only":
            wants_request = False
        elif policy_type == "cloud_always":
            wants_request = True
        elif policy_type == "suspicion_only":
            wants_request = row.local_score >= SCORE_THRESHOLD
        elif policy_type == "delay_only":
            wants_request = est_delay <= POLICY_TIMEOUT
        elif policy_type == "proposed":
            wants_request = (row.local_score >= SCORE_THRESHOLD) and (est_delay <= POLICY_TIMEOUT)
            
        if wants_request and len(pending_replies) < MAX_PENDING:
            net_delay_one_way = delay_provider.get_next_delay() / 2.0 
            rtt = delay_provider.get_next_delay()
            
            past_delays.append(rtt)
            cloud_return_time = local_done_time + rtt + CLOUD_PROC_TIME
            
            pending_replies.append({
                'return_time': cloud_return_time, 
                'pred': row.cloud_pred,
                'window_idx': idx
            })
            # sort by return time just in case
            pending_replies.sort(key=lambda x: x['return_time'])
            
            requests.append({'sent': local_done_time, 'returned': cloud_return_time})
            
    # Flush remaining replies
    for reply in pending_replies:
        if reply['pred'] == 1:
            warnings.append({'time': reply['return_time'], 'source': 'cloud', 'window_idx': reply['window_idx']})
            
    return pd.DataFrame(warnings), pd.DataFrame(requests)

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

if __name__ == "__main__":
    print("Running chronological simulations on DEV recordings...")
    
    summary_rows = []
    
    for policy in ["local_only", "cloud_always", "suspicion_only", "delay_only", "proposed"]:
        provider = TraceProvider(delay_trace_seconds)
        
        for rec_id, rec_df in dev_preds.groupby('recording_id'):
            # Pre-sort and reset index ONCE per recording so internal iterrows matches .loc lookups
            rec_df = rec_df.sort_values('timestamp').reset_index(drop=True)
            
            warnings_df, reqs_df = simulate_chronological_replay(rec_df, provider, policy)
            episodes = extract_episodes(rec_df)
        
            # False alerts evaluation
            # Any warning whose time does not fall into an attack episode is a false alert
            # Actually, simpler: if the window_idx associated with the warning has true_label==0, it's a false alert.
            if len(warnings_df) > 0:
                warn_labels = rec_df.loc[warnings_df['window_idx'], 'true_label'].values
                false_alerts = (warn_labels == 0).sum()
            else:
                false_alerts = 0
                
            # Timely detection per episode
            timely_detections_50ms = 0
            timely_detections_150ms = 0
            missed = 0
            
            for ep in episodes:
                # find first warning inside this episode (or shortly after)
                # A warning is valid for this episode if it originates from a window inside the episode
                if len(warnings_df) > 0:
                    ep_warnings = warnings_df[warnings_df['window_idx'].isin(rec_df[(rec_df['timestamp'] >= ep['onset']) & (rec_df['timestamp'] <= ep['end'])].index)]
                    if len(ep_warnings) > 0:
                        first_warn_time = ep_warnings['time'].min()
                        delay = first_warn_time - ep['onset']
                        if delay <= 0.050:
                            timely_detections_50ms += 1
                        if delay <= 0.150:
                            timely_detections_150ms += 1
                    else:
                        missed += 1
                else:
                    missed += 1
                    
            summary_rows.append({
                'policy': policy,
                'recording': rec_id,
                'requests': len(reqs_df),
                'request_rate_%': (len(reqs_df) / len(rec_df)) * 100,
                'false_alerts': false_alerts,
                'attack_episodes': len(episodes),
                'timely_50ms': timely_detections_50ms,
                'timely_150ms': timely_detections_150ms,
                'missed': missed
            })

    summary_df = pd.DataFrame(summary_rows)
    # Aggregate by policy
    agg = summary_df.groupby('policy').sum(numeric_only=True).reset_index()
    agg['request_rate_%'] = agg['requests'] / len(dev_preds) * 100
    
    print("\n--- CHRONOLOGICAL EPISODE RESULTS (DEV) ---")
    print(agg[['policy', 'request_rate_%', 'false_alerts', 'attack_episodes', 'timely_50ms', 'timely_150ms', 'missed']])
    agg.to_csv(RESULTS / "chronological_replay_dev.csv", index=False)
