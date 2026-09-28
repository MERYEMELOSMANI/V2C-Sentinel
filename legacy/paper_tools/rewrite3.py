import sys

with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_two_level_experiment.py", "r", encoding="utf-8") as f:
    content = f.read()

old_load = """    trace_cfg = CONFIG['network_traces'][0]
    trace_df = pd.read_csv(trace_cfg['path'], engine='python', encoding='latin1')
    if 'pub_time(ms)' not in trace_df.columns:
        for col in trace_df.columns:
            if 'pub_time' in col.lower():
                trace_df = trace_df.rename(columns={col: 'pub_time(ms)'})
            if 'delay' in col.lower():
                trace_df = trace_df.rename(columns={col: 'delay(ms)'})"""

new_load = """    trace_cfg = CONFIG['network_traces'][0]
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
    trace_df = trace_df.dropna(subset=['pub_time(ms)', 'delay(ms)'])"""

content = content.replace(old_load, new_load)

with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_two_level_experiment.py", "w", encoding="utf-8") as f:
    f.write(content)
