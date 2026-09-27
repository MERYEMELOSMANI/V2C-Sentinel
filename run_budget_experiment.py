import pandas as pd
import numpy as np
from pathlib import Path
from collections import deque
import random
import heapq
import time

RESULTS = Path("results/tables")
LOCAL_PROC_TIME = 0.005
CLOUD_PROC_TIME = 0.010
POLICY_TIMEOUT = 0.150 

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

def simulate_policy(df_recording, delay_provider, policy_type, score_thresh, periodic_int, random_prob, seed=0, offset=0.0):
    warnings, requests, pending_replies, past_delays = [], [], [], deque(maxlen=5)
    
    # Fix periodic offsets: Anchor to recording start plus offset
    next_periodic_time = df_recording['timestamp'].iloc[0] + offset
    random.seed(seed)
    
    for row in df_recording.itertuples():
        idx, obs_time = row.Index, row.timestamp
        local_done_time = obs_time + LOCAL_PROC_TIME
        
        while pending_replies and pending_replies[0][0] <= local_done_time:
            _, _, reply = heapq.heappop(pending_replies)
            past_delays.append(reply['rtt'])
            if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
                warnings.append({'time': reply['return_time'], 'source': 'cloud_timely', 'window_idx': reply['window_idx']})
        
        is_suspicious = row.local_score >= score_thresh
        
        is_periodic = False
        if obs_time >= next_periodic_time:
            is_periodic = True
            # Advance to next grid point strictly
            while next_periodic_time <= obs_time:
                next_periodic_time += periodic_int
                
        wants_request = False
        if policy_type == "periodic": wants_request = is_periodic
        elif policy_type == "random": wants_request = random.random() < random_prob
        elif policy_type == "suspicion": wants_request = is_suspicious
        elif policy_type == "combined": wants_request = is_suspicious or is_periodic
            
        if wants_request:
            actual_delay = delay_provider.get_delay_at(local_done_time)
            cloud_return_time = local_done_time + actual_delay + CLOUD_PROC_TIME
            deadline = local_done_time + POLICY_TIMEOUT
            
            reply = {'return_time': cloud_return_time, 'rtt': actual_delay, 'deadline': deadline, 'pred': row.cloud_pred, 'window_idx': idx}
            heapq.heappush(pending_replies, (cloud_return_time, len(requests), reply))
            
            if row.local_pred == 1 and cloud_return_time > deadline:
                warnings.append({'time': deadline, 'source': 'local_fallback', 'window_idx': idx})
                
            requests.append({'sent': local_done_time, 'returned': cloud_return_time})
        else:
            if row.local_pred == 1: warnings.append({'time': local_done_time, 'source': 'local_immediate', 'window_idx': idx})
                
    for _, _, reply in sorted(pending_replies):
        if reply['pred'] == 1 and reply['return_time'] <= reply['deadline']:
            warnings.append({'time': reply['return_time'], 'source': 'cloud_timely', 'window_idx': reply['window_idx']})
            
    return pd.DataFrame(warnings), pd.DataFrame(requests)

def evaluate_run(recording, warnings, episodes):
    timely = eventual = 0
    if warnings.empty:
        return timely, eventual
    origins = recording.loc[warnings['window_idx']]
    labels = origins['true_label'].to_numpy()
    times = origins['timestamp'].to_numpy()
    arrivals = warnings['time'].to_numpy()
    for episode in episodes:
        valid = (labels == 1) & (times >= episode['onset']) & (times <= episode['end'])
        eventual += int(valid.any())
        timely += int((valid & ((arrivals - episode['onset']) <= POLICY_TIMEOUT)).any())
    return timely, eventual


def main():
    print('Loading development predictions and network trace...', flush=True)
    preds = pd.read_csv(RESULTS / 'all_predictions.csv')
    dev = preds[preds['split'] == 'dev']
    provider = TraceProvider(pd.read_excel(
        'data/raw/cicv5g/data/Urban road/2-n78/Urban road_n78.csv', engine='openpyxl'))
    recordings = {key: frame.sort_values('timestamp').reset_index(drop=True)
                  for key, frame in dev.groupby('recording_id')}
    budgets = [0.01, 0.05, 0.10]
    total = len(budgets) * len(recordings) * 31
    completed = 0
    started = time.perf_counter()
    rows = []
    for budget in budgets:
        interval = 1.0 / (budget * 1000)
        threshold = np.percentile(dev['local_score'], 100 - budget * 100)
        combined_interval = 1.0 / ((budget / 2) * 1000)
        combined_threshold = np.percentile(dev['local_score'], 100 - budget / 2 * 100)
        jobs = [('periodic', threshold, interval, 0, float(offset))
                for offset in np.linspace(0, interval * 0.9, 10)]
        jobs += [('random', threshold, interval, seed, 0.0) for seed in range(10)]
        jobs += [('suspicion', threshold, interval, 0, 0.0)]
        jobs += [('combined', combined_threshold, combined_interval, 0, float(offset))
                 for offset in np.linspace(0, combined_interval * 0.9, 10)]
        for rec_id, recording in recordings.items():
            episodes = extract_episodes(recording)
            for policy, score, period, seed, offset in jobs:
                print(f'[{completed + 1}/{total}] {rec_id} | {policy} | budget {budget:.0%}', flush=True)
                warnings, requests = simulate_policy(recording, provider, policy, score,
                                                     period, budget, seed=seed, offset=offset)
                timely, eventual = evaluate_run(recording, warnings, episodes)
                rows.append(dict(budget=budget, policy=policy, recording=rec_id,
                                 seed=seed, offset=offset, requests=len(requests),
                                 timely_detections=timely, eventual_detections=eventual))
                del warnings, requests
                completed += 1
                elapsed = time.perf_counter() - started
                remaining = elapsed / completed * (total - completed)
                print(f'  Completed {completed}/{total}; elapsed {elapsed:.0f}s; estimated remaining {remaining:.0f}s', flush=True)
    runs = pd.DataFrame(rows)
    summary = runs.groupby(['budget', 'policy', 'recording'])[
        ['requests', 'timely_detections', 'eventual_detections']].mean().reset_index()
    summary['budget_%'] = summary['budget'] * 100
    agg = summary.groupby(['budget_%', 'policy'])[
        ['requests', 'timely_detections', 'eventual_detections']].sum().reset_index()
    agg['request_rate_%'] = agg['requests'] / len(dev) * 100
    agg = agg[['budget_%', 'policy', 'requests', 'request_rate_%',
               'timely_detections', 'eventual_detections']]
    RESULTS.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RESULTS / 'budget_controlled_runs.csv', index=False)
    agg.to_csv(RESULTS / 'budget_controlled_sweep.csv', index=False)
    print(agg.to_string(index=False), flush=True)
    print('Finished. Saved individual runs and summary in results/tables.', flush=True)


if __name__ == '__main__':
    main()
