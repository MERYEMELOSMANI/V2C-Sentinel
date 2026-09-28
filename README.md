# V2C-Sentinel

V2C-Sentinel is a replay-based research prototype for studying two alert levels in CAN masquerade detection:

- **Level 1:** an immediate local warning from logistic regression.
- **Level 2:** a random-forest confirmation, admitted through a token-bucket request budget and delayed by a recorded 5G trace.

The research question is: **How do immediate local warnings and budget-limited cloud confirmations differ in timeliness, false-alert burden, and communication demand?**

## Evidence boundary

Both classifiers run on the development computer. The project replays communication delay from CICV5G; it does not deploy a cloud service or control a physical vehicle. The current evaluation contains one attack episode and one normal recording in each of the development and test splits. Results are therefore a reproducible case study, not a population-level performance estimate.

## Canonical workflow

Run commands from the repository root:

```powershell
python run_pipeline.py
python run_two_level_experiment.py
python validate_project.py
python generate_two_level_figures.py
```

The first command trains the models and creates `results/tables/all_predictions.csv`. The second command creates the paper's numerical evidence in `results/final_two_level/`. The validator checks saved artifact structure and causal invariants. Figure generation reads only the canonical two-level summary.

## Canonical files

| Purpose | File or directory |
|---|---|
| Recording-level train/dev/test split | `data/metadata/split_plan.csv` |
| Model training and predictions | `run_pipeline.py` |
| Paper experiment | `run_two_level_experiment.py` |
| Result validation | `validate_project.py` |
| Paper figures | `generate_two_level_figures.py` |
| Saved models | `models/` |
| Paper result source of truth | `results/final_two_level/` |
| Evaluation definition | `paper/evaluation_protocol.md` |
| Current manuscript | `paper/V2C_Sentinel_IEEE_17_Page_Journal_Draft.docx` |
| A0 poster | `poster/output/` |

## Data and features

ROAD signal-extraction recordings provide CAN identifiers, decoded signals, timestamps, and labels. Model inputs contain `ID` and columns beginning with `Signal_`; missing signal values are filled with `-1`. `Label` and `Time` are excluded from the features. The standardizer and both classifiers are fitted on the training recordings only. The local threshold is the 95th percentile of scores from the normal development recording.

The CICV5G urban-road n78 trace supplies recorded communication delays. It is applied by simulation time and is not synchronized with the ROAD recordings.

## Result directories

- `results/final_two_level/` contains the only results cited by the current paper.
- `results/final/` is reserved for a clean rerun of the supplementary unified-policy experiment.
- `results/cloud_confirmation/` is reserved for the supplementary cloud-confirmation experiment.
- `legacy/` and `results/legacy_mixed_outputs/` contain historical material and must not be cited as current evidence.

## Validation

`test_correctness.py` exercises the earlier unified simulator's deadline, fallback, episode, grouping, and budget logic. `validate_project.py` checks the canonical two-level artifacts. The two checks serve different purposes and should both pass before a release.

## Installation

The minimal Conda environment is defined in `environment.yml`:

```powershell
conda env create -f environment.yml
conda activate v2c-sentinel
```

Raw datasets and large generated predictions are intentionally excluded from Git. A reproducible release must provide dataset acquisition instructions, exact package versions, and file hashes.
