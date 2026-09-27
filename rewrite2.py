import sys

with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_two_level_experiment.py", "r", encoding="utf-8") as f:
    content = f.read()

old_load = """    print("Loading data...")
    dev_preds = pd.read_csv("data/processed/dev_predictions.csv")
    test_preds = pd.read_csv("data/processed/test_predictions.csv")
    preds = pd.concat([dev_preds, test_preds], ignore_index=True)
    
    trace_cfg = CONFIG['network_traces'][0]
    trace_df = pd.read_csv(trace_cfg['path'])"""

new_load = """    print("Loading data...")
    preds = pd.read_csv("results/tables/all_predictions.csv")
    dev_preds = preds[preds['split'] == 'dev']
    test_preds = preds[preds['split'] == 'test']
    
    trace_cfg = CONFIG['network_traces'][0]
    trace_df = pd.read_csv(trace_cfg['path'], engine='python', encoding='latin1')
    if 'pub_time(ms)' not in trace_df.columns:
        for col in trace_df.columns:
            if 'pub_time' in col.lower():
                trace_df = trace_df.rename(columns={col: 'pub_time(ms)'})
            if 'delay' in col.lower():
                trace_df = trace_df.rename(columns={col: 'delay(ms)'})"""

content = content.replace(old_load, new_load)

with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_two_level_experiment.py", "w", encoding="utf-8") as f:
    f.write(content)
