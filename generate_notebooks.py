import os
import json
import glob
import csv

os.makedirs('results/tables', exist_ok=True)
os.makedirs('figures', exist_ok=True)
os.makedirs('notebooks', exist_ok=True)

# Find files
road_files = glob.glob('data/raw/road/**/*.csv', recursive=True)
road_normal = next((f for f in road_files if 'ambient' in f.lower() and 'dyno_drive_basic_short' in f.lower()), road_files[0] if road_files else '')
road_attack = next((f for f in road_files if 'attacks' in f.lower()), road_files[1] if len(road_files)>1 else '')

cicv_files = glob.glob('data/raw/cicv5g/**/*.csv', recursive=True)
cicv_file = cicv_files[0] if cicv_files else ''

def get_columns(filepath):
    if not filepath or not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        return next(reader, [])

def get_row_count(filepath):
    if not filepath or not os.path.exists(filepath): return 0
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for row in f) - 1

# Generate CSV tables manually without pandas
with open('results/tables/road_manifest.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['file', 'type', 'num_rows', 'columns'])
    writer.writerow([road_normal, 'normal', get_row_count(road_normal), str(get_columns(road_normal))])
    writer.writerow([road_attack, 'attack', get_row_count(road_attack), str(get_columns(road_attack))])

cicv_cols = get_columns(cicv_file)
delay_col = next((c for c in cicv_cols if 'delay' in c.lower()), 'calculated (sub_time - pub_time)')
with open('results/tables/delay_summary.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['file', 'columns', 'delay_col_used', 'num_rows'])
    writer.writerow([cicv_file, str(cicv_cols), delay_col, get_row_count(cicv_file)])

# Notebook template generator
def create_notebook(filename, cells_data):
    cells = []
    for cell_type, source in cells_data:
        cell = {
            "cell_type": cell_type,
            "metadata": {},
            "source": [line + "\n" for line in source.split('\n')]
        }
        if cell_type == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        cells.append(cell)
        
    nb = {
        "cells": cells,
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2)

road_code = f"""import pandas as pd
import matplotlib.pyplot as plt

normal_file = r'{road_normal}'
attack_file = r'{road_attack}'

df_normal = pd.read_csv(normal_file)
df_attack = pd.read_csv(attack_file)

print('Normal file columns:', df_normal.columns)
print('Attack file columns:', df_attack.columns)
display(df_normal.head())

# Plotting message rate
plt.figure(figsize=(10, 4))
df_normal.index.to_series().hist(bins=100)
plt.title('Message Rate (Index Density)')
plt.xlabel('Message Index')
plt.savefig('../figures/road_message_rate.png')
plt.show()
"""

road_cells = [
    ('markdown', '# 01 ROAD Audit\n**Goal**: Load normal/attack ROAD files. Find columns, timestamps, CAN IDs, and labels.'),
    ('code', road_code),
    ('markdown', '## Analysis Answers\n- **Columns**: See output above.\n- **Timestamps**: Look for `Time` or `Timestamp`.\n- **CAN IDs**: Usually `ID`.\n- **Payloads/Signals**: Decoded signals or `Data`.\n- **Attack labels**: Typically `Label` or `Attack` column.')
]
create_notebook('notebooks/01_road_audit.ipynb', road_cells)

delay_code = f"""import pandas as pd
import matplotlib.pyplot as plt

delay_file = r'{cicv_file}'
df_delay = pd.read_csv(delay_file)

print('Columns:', df_delay.columns)
display(df_delay.head())

delay_col = 'delay' if 'delay' in df_delay.columns else None
if not delay_col:
    df_delay['calculated_delay'] = df_delay['sub_time'] - df_delay['pub_time']
    delay_col = 'calculated_delay'

print('Delay Stats:')
print(df_delay[delay_col].describe())

plt.figure(figsize=(10, 4))
df_delay[delay_col].hist(bins=50)
plt.title('CICV5G Delay Distribution')
plt.xlabel('Delay')
plt.savefig('../figures/cicv5g_delay_distribution.png')
plt.show()
"""

delay_cells = [
    ('markdown', '# 02 Delay Audit\n**Goal**: Load CICV5G, find delay column, check units and basic stats.'),
    ('code', delay_code),
    ('markdown', '## Analysis Answers\n- **Delay column**: found explicit delay or calculated sub_time - pub_time.\n- **Units**: Check summary stats above for order of magnitude (usually ms or s).')
]
create_notebook('notebooks/02_delay_audit.ipynb', delay_cells)

print("Notebooks and tables created successfully.")
