# Evaluation Protocol — Frozen 2026-09-27, reconciled 2026-09-28

This document describes the **canonical two-level experiment** used by the current paper. The reconciliation on 2026-09-28 corrected stale paths and parameters that still described an earlier unified-policy experiment; it did not change the saved two-level results.

## Data splits

| Role | Normal recording | Attack recording | Purpose |
|---|---|---|---|
| Train | `ambient_dyno_drive_basic_long.csv` | `correlated_signal_attack_1_masquerade.csv` | Fit scaler and both classifiers |
| Development | `ambient_dyno_drive_radio_infotainment.csv` | `correlated_signal_attack_2_masquerade.csv` | Select the local threshold and interpret behavior |
| Test | `ambient_dyno_drive_winter.csv` | `correlated_signal_attack_3_masquerade.csv` | Final reported evaluation, subject to prior-use disclosure |

Whole recordings remain together. Frames are not randomly divided across splits.

### Prior-use disclosure

The test recordings were inspected during development of preliminary scripts now preserved under `archive/frozen_2026-09-27/` and `legacy/scripts/`. They were not used to fit either model or choose the local threshold, but they are not a pristine blind holdout. Development and test results are therefore reported separately.

### Source-recording independence

The three correlated-signal attack recordings come from the same vehicle and attack methodology. They are distinct recordings with different attack windows, not independent attack families or vehicles.

## Model and feature settings

| Item | Canonical value |
|---|---|
| Features | `ID` and columns beginning with `Signal_` |
| Missing signal value | `-1` |
| Excluded inputs | `Label`, `Time` |
| Scaling | `StandardScaler`, fitted on combined training frames |
| Level-1 model | `LogisticRegression(random_state=42, max_iter=1000)` |
| Level-2 model | `RandomForestClassifier(n_estimators=50, max_depth=15, random_state=42)` |
| Local positive threshold | 95th percentile of local scores on the normal development recording |

Both models are supervised. “Local” and “cloud” describe their roles in the replay; both are executed on the development computer.

## Two-level replay

A local positive creates an immediate Level-1 warning and becomes eligible for Level-2 confirmation. A token bucket admits or rejects the cloud request. Rejected candidates are skipped rather than queued. An admitted request receives the CICV5G delay selected by simulation time plus the assumed cloud-processing time. A positive forest result creates a Level-2 confirmation.

| Parameter | Values |
|---|---|
| Local processing time | 5 ms, assumed |
| Cloud processing time | 10 ms, assumed |
| Reporting deadlines | 150 ms and 300 ms |
| Request budgets | 1, 5, 10, 50 requests/s and unrestricted |
| Token-bucket burst | `max(2, 0.1 × rate)` |
| False-alert grouping window | 1.0 s |
| Episode gap tolerance | 0.5 s |

The reporting deadlines evaluate the same generated alert history; they are not independent experiment repetitions.

## Network trace

The replay uses the CICV5G urban-road n78 trace. Simulation time wraps over the trace duration, and the first sample at or after the wrapped request time supplies the communication delay. ROAD and CICV5G are not synchronized. Only one fixed trace phase is evaluated.

## Metrics

| Metric | Definition |
|---|---|
| Timely detection | Episode with at least one true-positive warning no later than the deadline after episode onset |
| Detection delay | Time from episode onset to its first true-positive warning |
| Eventual detection | Episode with a true-positive warning, including one after the deadline |
| Grouped false alerts/hour | False warnings on a separate normal recording, grouped by the fixed 1 s rule and divided by normal exposure |
| Request count | Admitted cloud requests over the normal and attack recording in a split |
| Actual requests/second | Request count divided by combined split exposure |

Warnings are associated with the true label of their originating message. A benign warning inside an attack interval cannot count as attack detection.

## Evidence boundary

Each evaluated split contains one attack episode. Development contributes 390.456 s of normal exposure and test contributes 47.731 s, for 438.187 s total. The study does not support population-level detection rates, a general zero-false-positive claim, or deployment and safety claims.

The 5 ms and 10 ms processing constants are assumptions. Development-machine benchmark measurements are contextual and do not establish embedded-vehicle performance.

## Reproducibility and source of truth

The canonical sequence is:

```powershell
python run_pipeline.py
python run_two_level_experiment.py
python validate_project.py
python generate_two_level_figures.py
```

The numerical source of truth is:

- `results/final_two_level/all_runs.csv`
- `results/final_two_level/summary.csv`
- `results/final_two_level/paper_table.csv`

Files under `legacy/` and `results/legacy_mixed_outputs/` are retained for traceability and must not be used as current paper evidence.
