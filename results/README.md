# Result provenance

| Directory | Status | Use |
|---|---|---|
| `final_two_level/` | Canonical | Numerical source for the current paper and poster |
| `tables/all_predictions.csv` | Canonical generated input | Per-message predictions consumed by the two-level replay |
| `benchmarks/` | Context only | Development-machine latency and model-size measurements |
| `final/` | Reserved | Output of a future clean unified-policy rerun |
| `cloud_confirmation/` | Reserved | Output of the supplementary confirmation-policy experiment |
| `legacy_mixed_outputs/` | Invalid for citation | Mixed historical files retained only for traceability |

Historical tables formerly stored beside `all_predictions.csv` were moved to `../legacy/results/` so that obsolete and current evidence are not confused.
