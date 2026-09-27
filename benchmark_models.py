import pandas as pd
import numpy as np
import time
from joblib import load
from pathlib import Path
import sys

def benchmark_models():
    print("Loading models and data...")
    try:
        scaler = load("models/scaler.joblib")
        local_model = load("models/local_iforest.joblib")
        cloud_model = load("models/cloud_rf.joblib")
    except Exception as e:
        print(f"Error loading models: {e}")
        return

    split_plan = pd.read_csv("data/metadata/split_plan.csv")
    dev_files = split_plan[split_plan['split'] == 'dev']
    
    # Just load one normal and one attack to benchmark
    base = Path("data/raw/road/road/signal_extractions")
    dfs = []
    for _, row in dev_files.iterrows():
        folder = "ambient" if row['type'] == "normal" else "attacks"
        df = pd.read_csv(base / folder / row['file_name'])
        feature_cols = ['ID'] + [c for c in df.columns if c.startswith('Signal_')]
        features = df[feature_cols].fillna(-1)
        dfs.append(features)
        
    X_raw = pd.concat(dfs).reset_index(drop=True)
    print(f"Total samples for benchmark: {len(X_raw)}")
    
    start = time.perf_counter()
    X_scaled = scaler.transform(X_raw)
    scale_time = time.perf_counter() - start
    
    # 1. Benchmark Local Model (Isolation Forest)
    start = time.perf_counter()
    # Batch predict
    if hasattr(local_model, 'score_samples'):
        _ = local_model.score_samples(X_scaled)
    else:
        _ = local_model.predict_proba(X_scaled)
    local_batch_time = time.perf_counter() - start
    
    # 2. Benchmark Cloud Model (Random Forest) locally
    start = time.perf_counter()
    # Batch predict
    _ = cloud_model.predict_proba(X_scaled)
    cloud_batch_time = time.perf_counter() - start
    
    # Print results
    print("\n--- DEVELOPMENT MACHINE BENCHMARK ---")
    print("Note: These are times on the development machine, not on a constrained CAN gateway.")
    print(f"Number of messages: {len(X_raw)}")
    print(f"Scaling time: {scale_time:.4f} sec ({scale_time/len(X_raw)*1e6:.2f} us/msg)")
    print(f"Local Model (Isolation Forest / DT) batch inference: {local_batch_time:.4f} sec ({local_batch_time/len(X_raw)*1e6:.2f} us/msg)")
    print(f"Cloud Model (Random Forest) batch inference: {cloud_batch_time:.4f} sec ({cloud_batch_time/len(X_raw)*1e6:.2f} us/msg)")
    
    # Single message inference (to simulate per-message latency)
    print("\nSimulating single-message inference (first 1000 messages)...")
    single_X = X_scaled[:1000]
    
    start = time.perf_counter()
    for i in range(1000):
        if hasattr(local_model, 'score_samples'):
            _ = local_model.score_samples(single_X[i:i+1])
        else:
            _ = local_model.predict_proba(single_X[i:i+1])
    local_single_time = (time.perf_counter() - start) / 1000.0
    
    start = time.perf_counter()
    for i in range(1000):
        _ = cloud_model.predict_proba(single_X[i:i+1])
    cloud_single_time = (time.perf_counter() - start) / 1000.0
    
    print(f"Local Model single-message latency: {local_single_time*1e6:.2f} us")
    print(f"Cloud Model single-message latency: {cloud_single_time*1e6:.2f} us")
    
if __name__ == "__main__":
    benchmark_models()
