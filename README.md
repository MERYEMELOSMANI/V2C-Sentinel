# V2C-Sentinel: Deadline-Aware Cloud Assistance for CAN Masquerade Detection

## Research Question
**Can selectively requesting a second detector improve timely CAN masquerade detection under limited communication and false-alarm budgets, compared with local-only and simpler request policies?**

## Experiment Scope
- **Local Detector:** Isolation Forest
- **Cloud Detector:** Random Forest
- Both models execute on the available computer. Vehicle–cloud communication is represented through replay.
- Outputs are warnings and logs. Physical vehicle control is outside the study.

## Project Structure
- `data/`: Raw and processed dataset files.
- `src/`: Experiment pipeline modules.
- `notebooks/`: Evaluation notebooks.
- `results/`: Final output tables and figures.
- `archive/`: Old preliminary results and pilots.
