# Changelog

## 2026-09-27
- **Project reset**: Moved all preliminary code, notebooks, and results into `archive/preliminary_invalid_for_research_conclusions/`.
- **Reason**: The preliminary scripts contained a massive label leakage (the Random Forest detector had access to the `Label` column directly via automatic numeric column selection). The scope of the project was also insufficiently defined. 
- **Next Steps**: Rebuild the experiment pipeline following strict evaluation protocol (train/dev/test separation, fixed local thresholds on dev, and explicitly named input features without leakage).
