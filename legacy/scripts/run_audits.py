import pandas as pd
import matplotlib.pyplot as plt
import os
import nbformat as nbf
import glob

os.makedirs('results/tables', exist_ok=True)
os.makedirs('figures', exist_ok=True)

# 1. Find ROAD files
road_ambient_files = glob.glob('data/raw/road/**/*.csv', recursive=True)
road_normal_file = next(f for f in road_ambient_files if 'ambient' in f.lower() and 'dyno_drive_basic_short' in f.lower()) if any('ambient' in f.lower() and 'dyno_drive_basic_short' in f.lower() for f in road_ambient_files) else road_ambient_files[0]
road_attack_file = next((f for f in road_ambient_files if 'attacks' in f.lower()), road_ambient_files[1])

# Load ROAD
df_road_normal = pd.read_csv(road_normal_file)
df_road_attack = pd.read_csv(road_attack_file)

# We want to know: What columns exist? Where are timestamps? Where are CAN IDs? Where are attack labels?
# ROAD typically has a log file format or signal extraction format.
# Let's save a manifest
road_manifest = pd.DataFrame({
    'file': [road_normal_file, road_attack_file],
    'type': ['normal', 'attack'],
    'num_rows': [len(df_road_normal), len(df_road_attack)],
    'columns': [str(list(df_road_normal.columns)), str(list(df_road_attack.columns))]
})
road_manifest.to_csv('results/tables/road_manifest.csv', index=False)

# Plot road message rate (e.g. messages per time)
# Assuming 'Time' is a column, if not, just plot index.
time_col_normal = next((col for col in df_road_normal.columns if 'time' in col.lower()), None)
plt.figure(figsize=(10, 4))
if time_col_normal:
    df_road_normal[time_col_normal].hist(bins=100)
    plt.xlabel('Time')
else:
    plt.plot(df_road_normal.index)
    plt.xlabel('Index')
plt.title('ROAD Normal File - Message Density / Time')
plt.savefig('figures/road_message_rate.png')
plt.close()

# 2. Find CICV5G files
cicv_files = glob.glob('data/raw/cicv5g/**/*.csv', recursive=True)
cicv_file = cicv_files[0]

# Load CICV5G
df_cicv = pd.read_csv(cicv_file)

# What is delay column?
delay_col = next((col for col in df_cicv.columns if 'delay' in col.lower()), None)
if not delay_col:
    # Try sub_time - pub_time if present
    pub_col = next((col for col in df_cicv.columns if 'pub_time' in col.lower() or 'pubtime' in col.lower()), None)
    sub_col = next((col for col in df_cicv.columns if 'sub_time' in col.lower() or 'subtime' in col.lower()), None)
    if pub_col and sub_col:
        df_cicv['calculated_delay'] = df_cicv[sub_col] - df_cicv[pub_col]
        delay_col = 'calculated_delay'

# Summary stats
delay_stats = df_cicv[delay_col].describe() if delay_col else df_cicv.iloc[:, 0].describe()
delay_summary = pd.DataFrame({
    'file': [cicv_file],
    'columns': [str(list(df_cicv.columns))],
    'delay_col_used': [delay_col],
    'min_delay': [delay_stats.get('min', None)],
    'mean_delay': [delay_stats.get('mean', None)],
    'max_delay': [delay_stats.get('max', None)],
    'missing_values': [df_cicv[delay_col].isna().sum() if delay_col else None]
})
delay_summary.to_csv('results/tables/delay_summary.csv', index=False)

# Plot delay
plt.figure(figsize=(10, 4))
if delay_col:
    df_cicv[delay_col].plot(kind='hist', bins=50, title=f'CICV5G Delay Distribution ({delay_col})')
    plt.xlabel('Delay')
else:
    plt.text(0.5, 0.5, 'No delay column found', ha='center')
plt.savefig('figures/cicv5g_delay_distribution.png')
plt.close()

# 3. Create Jupyter Notebooks Programmatically
def create_notebook(filename, cells_content):
    nb = nbf.v4.new_notebook()
    for cell_type, source in cells_content:
        if cell_type == 'md':
            nb.cells.append(nbf.v4.new_markdown_cell(source))
        elif cell_type == 'code':
            nb.cells.append(nbf.v4.new_code_cell(source))
    with open(filename, 'w') as f:
        nbf.write(nb, f)

road_cells = [
    ('md', '# 01 ROAD Audit\n**Goal**: Load normal/attack ROAD files. Find columns, timestamps, CAN IDs, and labels.'),
    ('code', f"import pandas as pd\nimport matplotlib.pyplot as plt\n\nnormal_file = '{road_normal_file}'\nattack_file = '{road_attack_file}'\ndf_normal = pd.read_csv(normal_file)\ndf_attack = pd.read_csv(attack_file)"),
    ('code', "print('Normal columns:', df_normal.columns)\nprint('Attack columns:', df_attack.columns)\ndf_normal.head()"),
    ('md', '## Analysis Answers\n- **Columns**: Identified above.\n- **Timestamps**: Look for `Time` or similar.\n- **CAN IDs**: Look for `ID` or similar.\n- **Payloads/Signals**: Look for `Data` or decoded signals.\n- **Attack labels**: The attack files contain an `Attack` or `Label` column, or attacks are defined by a separate interval file.'),
    ('code', "import IPython.display as display\ndisplay.Image('figures/road_message_rate.png')")
]
create_notebook('notebooks/01_road_audit.ipynb', road_cells)

delay_cells = [
    ('md', '# 02 Delay Audit\n**Goal**: Load CICV5G, find delay column, check units and basic stats.'),
    ('code', f"import pandas as pd\nimport matplotlib.pyplot as plt\n\ndelay_file = '{cicv_file}'\ndf_delay = pd.read_csv(delay_file)"),
    ('code', "print('Columns:', df_delay.columns)\ndelay_stats = pd.read_csv('results/tables/delay_summary.csv')\ndisplay(delay_stats)\ndf_delay.head()"),
    ('md', '## Analysis Answers\n- **Delay column**: identified via sub_time - pub_time or explicit delay col.\n- **Units**: usually ms (to be verified via values).\n- **Missing Values & Stats**: calculated in summary.'),
    ('code', "import IPython.display as display\ndisplay.Image('figures/cicv5g_delay_distribution.png')")
]
create_notebook('notebooks/02_delay_audit.ipynb', delay_cells)

print("Audits complete. Check figures/ and results/tables/")
