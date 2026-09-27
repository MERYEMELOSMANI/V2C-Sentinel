# Evaluation Protocol — FROZEN 2026-09-27

This document defines the evaluation setup. After this point, no settings
may be tuned to improve final results.

## Data Splits

| Role | Normal Recording | Attack Recording | Purpose |
|---|---|---|---|
| **Train** | ambient_dyno_drive_basic_long.csv | correlated_signal_attack_1_masquerade.csv | Model training only |
| **Dev** | ambient_dyno_drive_radio_infotainment.csv | correlated_signal_attack_2_masquerade.csv | Threshold selection, policy tuning |
| **Test** | ambient_dyno_drive_winter.csv | correlated_signal_attack_3_masquerade.csv | Final evaluation (see disclosure below) |

### Prior-use disclosure
The test recordings (normal_03, attack_03) were previously inspected during
development of `run_final_test.py` and `run_chronological_replay.py`. Results
from those prior scripts are archived in `archive/frozen_2026-09-27/`. No
model training or threshold selection used test data. The unified experiment
uses a completely rewritten simulation engine, but the test recordings are
not fully untouched. We disclose this and report dev results alongside test.

### Source-recording independence
All three correlated_signal_attack recordings (1, 2, 3) are from the same
vehicle and attack methodology (ROAD dataset). They differ in timing and
injection parameters but share the same CAN bus setup. We do not claim they
are fully independent attack scenarios; we claim they are distinct recordings
with different attack windows.

## Settings Chosen on Dev Data

| Parameter | Value | How chosen |
|---|---|---|
| Suspicion threshold | 90th percentile of dev `local_score` | Fixed before test evaluation |
| False-alert grouping window | 1.0 second | Defined a priori (sub-second warnings = same alerting event) |
| Episode gap tolerance | 0.5 seconds | From ROAD dataset attack structure |
| Local processing time | 5 ms | Assumed (not measured on target hardware) |
| Cloud processing time | 10 ms | Assumed (not measured on target hardware) |

## Network Traces

| Trace | Source | Alignment |
|---|---|---|
| Urban road n78 | CICV5G dataset, Tongji University | Mapped by simulation time (wraps around trace). No synchronized recording exists between CICV5G and ROAD — the delay trace is applied via time-based lookup, not temporal alignment. |

## Experimental Parameters

| Parameter | Values |
|---|---|
| Deadlines | 100 ms, 150 ms, 200 ms, 300 ms |
| Request budgets | 1, 5, 10, 50 req/s |
| Random seeds | 0–9 (10 seeds per random policy configuration) |
| Periodic offsets | 10 evenly spaced within one interval |
| Policies | local_only, strong_local, cloud_unlimited, periodic, random, suspicion, combined |

### Deadline justification
150 ms is used as the primary reporting deadline. It is presented as an
**experimental parameter**, not an application-specific safety requirement.
Rationale: it approximates the time for a CAN gateway to receive a message,
forward it for analysis, wait for a remote response, and act on the result
before the next relevant message cycle. Additional deadlines (100, 200, 300 ms)
are tested to show sensitivity.

## Processing Time Assumptions vs. Measurements

The `local_proc_time` (5 ms) and `cloud_proc_time` (10 ms) are **assumed
constants**, not measured on target automotive hardware. The benchmark script
(`benchmark_models.py`) measures actual inference latency on the development
machine, which will be reported separately. Development-machine timings do
not establish performance on a constrained vehicle gateway.

## Metrics

| Metric | Definition |
|---|---|
| Timely detection | Attack episode with ≥1 true-positive warning within deadline of onset |
| Detection delay | Time from episode onset to first true-positive warning |
| Missed episode | Attack episode with no true-positive warning at any time |
| Eventual detection | Episode detected at any time (including after deadline) |
| Grouped false alerts/hr | False warnings grouped within 1s, divided by normal driving hours |
| Request rate | Actual cloud requests / total messages × 100% |
| Requests/sec | Actual cloud requests / recording duration |
| Late replies | Cloud replies arriving after the deadline |

## Reproducibility

- All random seeds are fixed and recorded per run
- Configuration saved as `results/final/config.json`
- Individual run results saved as `results/final/all_runs.csv`
- Aggregated results saved as `results/final/summary.csv`
