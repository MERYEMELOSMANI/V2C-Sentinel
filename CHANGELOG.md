# Changelog

## 2026-09-28
- Declared `run_pipeline.py` and `run_two_level_experiment.py` as the canonical paper workflow.
- Corrected the frozen protocol so its threshold, budgets, deadlines, and output paths match the two-level experiment.
- Moved superseded scripts and result tables under `legacy/` without deleting them.
- Added a canonical artifact validator and made console tests portable on Windows.
- Reduced the Conda environment to packages required by the canonical workflow.

## 2026-09-27
- **Project reset**: Moved all preliminary code, notebooks, and results into `archive/preliminary_invalid_for_research_conclusions/`.
- **Reason**: The preliminary scripts contained a massive label leakage (the Random Forest detector had access to the `Label` column directly via automatic numeric column selection). The scope of the project was also insufficiently defined. 
- **Next Steps**: Rebuild the experiment pipeline following strict evaluation protocol (train/dev/test separation, fixed local thresholds on dev, and explicitly named input features without leakage).
