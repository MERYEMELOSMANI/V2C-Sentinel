import pandas as pd
import numpy as np
import os
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from joblib import dump, load

def load_data(split_plan, split_name):
    files = split_plan[split_plan['split'] == split_name]
    df_list = []
    
    for _, row in files.iterrows():
        base = Path("data/raw/road/road/signal_extractions")
        folder = "ambient" if row['type'] == "normal" else "attacks"
        path = base / folder / row['file_name']
        
        df = pd.read_csv(path)
        
        # Explicit feature selection (no Label leakage)
        # ID and any Signal_ columns
        feature_cols = ['ID'] + [c for c in df.columns if c.startswith('Signal_')]
        
        features = df[feature_cols].copy()
        # Fill missing signal values with -1 to differentiate from actual 0 values
        features = features.fillna(-1)
        
        labels = df['Label'].apply(lambda x: 1 if str(x).strip() == '1' else 0) if 'Label' in df.columns else pd.Series([0]*len(df))
        
        df_list.append({
            'recording_id': row['recording_id'],
            'features': features,
            'labels': labels,
            'timestamp': df['Time'] if 'Time' in df.columns else df.index,
            'feature_cols': feature_cols
        })
    return df_list

def run_experiment():
    Path("results/tables").mkdir(parents=True, exist_ok=True)
    Path("models").mkdir(exist_ok=True)
    
    print("Loading datasets based on split_plan.csv...")
    split_plan = pd.read_csv("data/metadata/split_plan.csv")
    
    train_data = load_data(split_plan, 'train')
    dev_data = load_data(split_plan, 'dev')
    test_data = load_data(split_plan, 'test')
    
    # Check feature consistency across all loaded datasets
    train_feature_names = train_data[0]['feature_cols']
    if 'Label' in train_feature_names or 'Time' in train_feature_names:
        raise ValueError("LEAKAGE DETECTED: Label or Time found in training features.")
        
    print(f"Features used for training ({len(train_feature_names)} total): {train_feature_names[:3]}...")
    
    # Concatenate training features
    print("Building models on training data...")
    X_train_normal = pd.concat([d['features'] for d in train_data if 'normal' in d['recording_id']])
    X_train_all = pd.concat([d['features'] for d in train_data])
    y_train_all = pd.concat([d['labels'] for d in train_data])
    
    # Train Scaler
    scaler = StandardScaler()
    X_train_all_scaled = scaler.fit_transform(X_train_all)
    X_train_normal_scaled = scaler.transform(X_train_normal)
    
    # Train Local Detector (Lightweight Supervised)
    local_model = LogisticRegression(random_state=42, max_iter=1000)
    local_model.fit(X_train_all_scaled, y_train_all)
    
    # Train Cloud Detector (Random Forest)
    # Uses both normal and attack recordings from the train set
    cloud_model = RandomForestClassifier(n_estimators=50, max_depth=15, random_state=42, n_jobs=-1)
    cloud_model.fit(X_train_all_scaled, y_train_all)
    
    # Save models
    dump(scaler, "models/scaler.joblib")
    dump(local_model, "models/local_lr.joblib")
    dump(cloud_model, "models/cloud_rf.joblib")
    
    # Select threshold using DEV set for local detector
    print("Selecting local threshold on DEV set...")
    dev_normal = pd.concat([d['features'] for d in dev_data if 'normal' in d['recording_id']])
    dev_normal_scaled = scaler.transform(dev_normal)
    dev_scores = local_model.predict_proba(dev_normal_scaled)[:, 1]
    # Target: approx 5% false alarms on dev set
    fixed_local_threshold = np.percentile(dev_scores, 95)
    print(f"Fixed Local Threshold chosen: {fixed_local_threshold} (Target 5% FA on normal dev data)")
    
    # Evaluate on all splits and save results
    def process_split(data_list, split_name):
        res = []
        for d in data_list:
            rec_id = d['recording_id']
            X_scaled = scaler.transform(d['features'])
            y = d['labels']
            t = d['timestamp']
            
            local_scores = local_model.predict_proba(X_scaled)[:, 1]
            local_preds = (local_scores >= fixed_local_threshold).astype(int)
            
            cloud_scores = cloud_model.predict_proba(X_scaled)[:, 1] if len(cloud_model.classes_) > 1 else np.zeros(len(y))
            cloud_preds = cloud_model.predict(X_scaled)
            
            res.append(pd.DataFrame({
                'recording_id': rec_id,
                'timestamp': t,
                'event_id': range(len(y)), # simple index for merging
                'true_label': y,
                'local_score': local_scores,
                'local_pred': local_preds,
                'cloud_score': cloud_scores,
                'cloud_pred': cloud_preds,
                'split': split_name
            }))
        return pd.concat(res)
    
    print("Generating predictions...")
    all_preds = pd.concat([
        process_split(train_data, 'train'),
        process_split(dev_data, 'dev'),
        process_split(test_data, 'test')
    ])
    
    all_preds.to_csv("results/tables/all_predictions.csv", index=False)
    
    # Evaluate Development performance to check if cloud helps
    print("\n--- DEVELOPMENT PERFORMANCE ---")
    dev_preds = all_preds[all_preds['split'] == 'dev']
    local_correct = dev_preds['local_pred'] == dev_preds['true_label']
    cloud_correct = dev_preds['cloud_pred'] == dev_preds['true_label']
    
    print("Local Correct / Cloud Correct Cross-Tabulation:")
    print(pd.crosstab(local_correct.reset_index(drop=True), cloud_correct.reset_index(drop=True), rownames=['Local Correct'], colnames=['Cloud Correct']))
    
    print("\n--- PIPELINE FINISHED ---")

if __name__ == "__main__":
    run_experiment()
