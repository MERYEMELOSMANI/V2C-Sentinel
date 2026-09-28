import os
import json

# 1. Update README.md
readme_content = """# V2C-Sentinel

This project studies deadline-aware cloud confirmation for CAN masquerade detection:
when should a vehicle trust the local detector, ask the cloud, or ignore a late cloud response?

## Data Used
- **MAIN SECURITY DATA**: ROAD dataset
- **MAIN DELAY DATA**: CICV5G dataset
- **OPTIONAL BACKUP**: SynCAN dataset
- **REFERENCE CODE**: CANShield

## First Coding Milestone
- Load one normal ROAD file and one attack ROAD file.
- Load one CICV5G delay file.
- Generate summary tables: `results/tables/road_manifest.csv`, `results/tables/delay_summary.csv`
- Generate simple plots: `figures/road_message_rate.png`, `figures/cicv5g_delay_distribution.png`
"""

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(readme_content)

def create_notebook(filename, cells_data):
    cells = []
    for cell_type, source in cells_data:
        cell = {
            "cell_type": cell_type,
            "metadata": {},
            "source": [line + "\n" for line in source.split('\n')[:-1]] + [source.split('\n')[-1]]
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

# 2. Notebook 01: ROAD audit
road_cells = [
    ("markdown", "# 01 ROAD Audit\nGoal:\n- Can I load one normal ROAD recording?\n- Can I load one attack ROAD recording?\n- What columns exist?\n- Where are timestamps?\n- Where are CAN IDs?\n- Where are payloads or signal values?\n- Where are attack labels or attack intervals?\n- Are timestamps sorted?\n- Are there missing values?\n- How many messages per CAN ID?"),
    ("code", "from pathlib import Path\nimport pandas as pd\nimport matplotlib.pyplot as plt\n\nRAW_ROAD = Path(\"../data/raw/road\")\nRESULTS = Path(\"../results/tables\")\nFIGURES = Path(\"../figures\")\n\nRESULTS.mkdir(parents=True, exist_ok=True)\nFIGURES.mkdir(parents=True, exist_ok=True)\n\nfiles = list(RAW_ROAD.rglob(\"*\"))\nfiles[:10], len(files)"),
    ("code", "# Change this after seeing your real file names\nfile_path = files[0]\n\nprint(file_path)\n\n# Try depending on file type\nif file_path.suffix == \".csv\":\n    df = pd.read_csv(file_path)\nelif file_path.suffix == \".parquet\":\n    df = pd.read_parquet(file_path)\nelse:\n    print(\"Unknown format:\", file_path.suffix)\n\ndf.head()"),
    ("code", "manifest = []\n\nfor f in RAW_ROAD.rglob(\"*\"):\n    if f.is_file():\n        manifest.append({\n            \"file_name\": f.name,\n            \"path\": str(f),\n            \"extension\": f.suffix,\n            \"size_mb\": round(f.stat().st_size / (1024 * 1024), 2)\n        })\n\nmanifest_df = pd.DataFrame(manifest)\nmanifest_df.to_csv(RESULTS / \"road_manifest.csv\", index=False)\nmanifest_df.head()")
]
create_notebook('notebooks/01_road_audit.ipynb', road_cells)

# 3. Notebook 02: CICV5G delay audit
delay_cells = [
    ("markdown", "# 02 Delay Audit\nGoal:\n- Can we load the delay dataset?\n- What columns exist?\n- Which column is send time?\n- Which column is receive time?\n- Which column is round-trip delay?\n- Is delay in ms or seconds?\n- Are there missing values?\n- What is min, mean, median, 95%, max delay?"),
    ("code", "from pathlib import Path\nimport pandas as pd\nimport matplotlib.pyplot as plt\n\nRAW_DELAY = Path(\"../data/raw/cicv5g\")\nRESULTS = Path(\"../results/tables\")\nFIGURES = Path(\"../figures\")\n\nRESULTS.mkdir(parents=True, exist_ok=True)\nFIGURES.mkdir(parents=True, exist_ok=True)\n\nfiles = list(RAW_DELAY.rglob(\"*\"))\nfiles[:10], len(files)"),
    ("code", "file_path = files[0]\nprint(file_path)\n\nif file_path.suffix == \".csv\":\n    delay_df = pd.read_csv(file_path)\nelif file_path.suffix == \".parquet\":\n    delay_df = pd.read_parquet(file_path)\nelse:\n    print(\"Unknown format:\", file_path.suffix)\n\ndelay_df.head()"),
    ("code", "delay_df.describe(include=\"all\").T.to_csv(RESULTS / \"delay_summary.csv\")\ndelay_df.describe(include=\"all\").T"),
    ("code", "delay_col = \"delay\"  # change this to the real column name\n\ndelay_df[delay_col].dropna().hist(bins=100)\nplt.xlabel(\"Delay\")\nplt.ylabel(\"Count\")\nplt.title(\"CICV5G delay distribution\")\nplt.savefig(FIGURES / \"cicv5g_delay_distribution.png\", dpi=200, bbox_inches=\"tight\")\nplt.show()")
]
create_notebook('notebooks/02_delay_audit.ipynb', delay_cells)

# 4. Create split_plan.csv
split_plan_content = """recording_id,file_name,type,split
normal_01,normal_drive_01.csv,normal,train
normal_02,normal_drive_02.csv,normal,dev
normal_03,normal_drive_03.csv,normal,test
attack_01,attack_masquerade_01.csv,attack,train
attack_02,attack_masquerade_02.csv,attack,dev
attack_03,attack_masquerade_03.csv,attack,test
"""
os.makedirs('data/metadata', exist_ok=True)
with open('data/metadata/split_plan.csv', 'w', encoding='utf-8') as f:
    f.write(split_plan_content)

print("Done.")
