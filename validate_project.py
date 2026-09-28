"""Validate the saved artifacts used by the V2C-Sentinel paper.

This check is intentionally fast: it does not retrain models or rerun the
294 MB prediction pipeline. It verifies the canonical files, experiment grid,
split manifest, and causal invariants that must hold in the saved results.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "final_two_level"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def number(value: str) -> float:
    return float(value.replace(",", ""))


def close(a: float, b: float, tolerance: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    required = [
        ROOT / "data" / "metadata" / "split_plan.csv",
        ROOT / "models" / "scaler.joblib",
        ROOT / "models" / "local_lr.joblib",
        ROOT / "models" / "cloud_rf.joblib",
        ROOT / "results" / "tables" / "all_predictions.csv",
        RESULTS / "all_runs.csv",
        RESULTS / "config.json",
        RESULTS / "summary.csv",
        RESULTS / "paper_table.csv",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    require(not missing, f"Missing canonical artifacts: {', '.join(missing)}")

    split_rows = read_csv(required[0])
    require(len(split_rows) == 6, "Split plan must contain exactly six recordings")
    for split in ("train", "dev", "test"):
        rows = [row for row in split_rows if row["split"] == split]
        require(len(rows) == 2, f"{split} must contain one normal and one attack recording")
        require({row["type"] for row in rows} == {"normal", "attack"},
                f"{split} recording types are invalid")

    with (RESULTS / "config.json").open(encoding="utf-8-sig") as handle:
        config = json.load(handle)
    require(config["deadlines_s"] == [0.15, 0.30], "Saved deadline configuration is invalid")
    require(config["request_budgets_per_sec"] == [1.0, 5.0, 10.0, 50.0, "unlimited"],
            "Saved request-budget configuration is invalid")
    require(close(float(config["local_proc_time_s"]), 0.005), "Saved local processing time is invalid")
    require(close(float(config["cloud_proc_time_s"]), 0.010), "Saved cloud processing time is invalid")

    runs = read_csv(RESULTS / "all_runs.csv")
    summary = read_csv(RESULTS / "summary.csv")
    paper = read_csv(RESULTS / "paper_table.csv")
    require(len(runs) == 40, "all_runs.csv must contain 40 recording-level runs")
    require(len(summary) == 20, "summary.csv must contain the 2 x 5 x 2 experiment grid")
    require(len(paper) == 10, "paper_table.csv must contain ten 150 ms result rows")

    expected_splits = {"dev", "test"}
    expected_budgets = {"1.0", "5.0", "10.0", "50.0", "unlimited"}
    expected_deadlines = {0.15, 0.30}
    require({row["split"] for row in summary} == expected_splits, "Unexpected split in summary")
    require({row["budget"] for row in summary} == expected_budgets, "Unexpected budget grid")
    require({number(row["deadline_s"]) for row in summary} == expected_deadlines,
            "Unexpected deadline grid")

    for split in expected_splits:
        split_rows = [row for row in summary if row["split"] == split]
        for field in (
            "level1_local_detect_rate",
            "level1_local_delay",
            "level1_local_false_per_hr",
        ):
            values = {round(number(row[field]), 12) for row in split_rows}
            require(len(values) == 1, f"Local metric {field} changes with budget/deadline in {split}")

        for row in split_rows:
            require(number(row["attack_episodes"]) == 1, f"{split} must report one attack episode")
            require(number(row["level1_local_detect_rate"]) == 1.0,
                    f"Level 1 must detect the saved {split} episode")
            require(number(row["level2_cloud_false_per_hr"]) >= 0.0,
                    "False-alert rates cannot be negative")
            require(number(row["total_requests"]) >= 0.0, "Request totals cannot be negative")

    summary_150 = {
        (row["split"], row["budget"]): row
        for row in summary
        if close(number(row["deadline_s"]), 0.15)
    }
    for row in paper:
        key = (row["Split"], row["Budget"])
        require(key in summary_150, f"Paper row {key} has no canonical summary row")
        source = summary_150[key]
        require(int(row["Requests"].replace(",", "")) == int(number(source["total_requests"])),
                f"Request total mismatch for {key}")
        require(close(number(row["L1 Delay(s)"]), number(source["level1_local_delay"]), 1e-3),
                f"Level-1 delay mismatch for {key}")
        require(close(number(row["L2 Delay(s)"]), number(source["level2_cloud_delay"]), 1e-3),
                f"Level-2 delay mismatch for {key}")

    print("PASS: canonical files are present")
    print("PASS: recording-level split manifest is valid")
    print("PASS: saved configuration matches the canonical experiment")
    print("PASS: saved experiment grid is complete")
    print("PASS: local-path invariants hold")
    print("PASS: paper table matches the canonical 150 ms summary")


if __name__ == "__main__":
    main()
