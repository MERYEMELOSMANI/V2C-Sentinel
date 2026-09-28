"""
V2C-Sentinel Results Interpretation
====================================
Step 7: Answers the five key questions from the experiment results.
Run this AFTER run_unified_experiment.py completes.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys

RESULTS_DIR = Path("results/final")

def main():
    if not (RESULTS_DIR / "summary.csv").exists():
        print("ERROR: results/final/summary.csv not found. Run run_unified_experiment.py first.")
        sys.exit(1)

    summary = pd.read_csv(RESULTS_DIR / "summary.csv")
    runs = pd.read_csv(RESULTS_DIR / "all_runs.csv")
    with open(RESULTS_DIR / "config.json") as f:
        config = json.load(f)

    print("=" * 70)
    print("V2C-Sentinel Results Interpretation")
    print("=" * 70)

    # Primary deadline for discussion
    DL = 0.150

    output_lines = []
    def p(text=""):
        print(text)
        output_lines.append(text)

    # ========================================================================
    # QUESTION 1: Does cloud assistance improve anything over local-only?
    # ========================================================================
    p("\n## Q1: Does cloud assistance improve anything over local-only?")
    p("-" * 60)

    for split in ['dev', 'test']:
        data = summary[(summary['split'] == split) & (summary['deadline_s'] == DL)]

        local_only = data[data['policy'] == 'local_only']
        cloud_unlimited = data[data['policy'] == 'cloud_unlimited']

        if local_only.empty or cloud_unlimited.empty:
            p(f"  [{split}] Data not available")
            continue

        lo = local_only.iloc[0]
        cu = cloud_unlimited.iloc[0]

        p(f"  [{split.upper()}]")
        p(f"    Local-only:      timely={lo['timely_detections']:.1f}, "
          f"FA/hr={lo['false_alerts_per_hr']:.1f}, "
          f"delay={lo['mean_detection_delay_s']*1000:.1f}ms")
        p(f"    Cloud-unlimited: timely={cu['timely_detections']:.1f}, "
          f"FA/hr={cu['false_alerts_per_hr']:.1f}, "
          f"delay={cu['mean_detection_delay_s']*1000:.1f}ms, "
          f"requests={cu['actual_request_rate_pct']:.1f}%")

        if cu['false_alerts_per_hr'] < lo['false_alerts_per_hr']:
            reduction = (1 - cu['false_alerts_per_hr'] / lo['false_alerts_per_hr']) * 100
            p(f"    → Cloud reduces false alerts by {reduction:.0f}%")
        if cu['timely_detections'] > lo['timely_detections']:
            p(f"    → Cloud improves timely detection")
        elif cu['timely_detections'] == lo['timely_detections']:
            p(f"    → Cloud provides same timely detection")

    # ========================================================================
    # QUESTION 2: Could the stronger detector simply run locally?
    # ========================================================================
    p("\n## Q2: Could the stronger detector simply run locally?")
    p("-" * 60)

    for split in ['dev', 'test']:
        data = summary[(summary['split'] == split) & (summary['deadline_s'] == DL)]
        strong_local = data[data['policy'] == 'strong_local']

        if strong_local.empty:
            p(f"  [{split}] Data not available")
            continue

        sl = strong_local.iloc[0]
        p(f"  [{split.upper()}]")
        p(f"    Strong-local (RF): timely={sl['timely_detections']:.1f}, "
          f"FA/hr={sl['false_alerts_per_hr']:.1f}, "
          f"delay={sl['mean_detection_delay_s']*1000:.1f}ms, "
          f"requests=0%")
        p(f"    → If vehicle hardware can run RF locally, cloud offloading is unnecessary")
        p(f"    → This baseline establishes the UPPER BOUND for local detection")

    # ========================================================================
    # QUESTION 3: At comparable request budgets, does combined beat periodic/random?
    # ========================================================================
    p("\n## Q3: At comparable budgets, does combined beat periodic or random?")
    p("-" * 60)

    for split in ['dev', 'test']:
        p(f"  [{split.upper()}]")
        data = summary[(summary['split'] == split) & (summary['deadline_s'] == DL)]

        budgets = sorted(data['budget_req_per_sec'].dropna().unique())

        for budget in budgets:
            p(f"    Budget = {budget:.0f} req/s:")
            bdata = data[data['budget_req_per_sec'] == budget]

            for policy in ['periodic', 'random', 'suspicion', 'combined']:
                pdata = bdata[bdata['policy'] == policy]
                if pdata.empty:
                    continue
                row = pdata.iloc[0]
                p(f"      {policy:12s}: timely={row['timely_detections']:.2f}, "
                  f"FA/hr={row['false_alerts_per_hr']:.1f}, "
                  f"actual_rate={row['actual_request_rate_pct']:.2f}%, "
                  f"delay={row['mean_detection_delay_s']*1000:.1f}ms")

    # ========================================================================
    # QUESTION 4: Do improvements persist across recordings and conditions?
    # ========================================================================
    p("\n## Q4: Do improvements persist across recordings and network conditions?")
    p("-" * 60)

    for split in ['dev', 'test']:
        p(f"  [{split.upper()}]")
        rec_data = runs[(runs['split'] == split) & (runs['deadline_s'] == DL)]
        recordings = rec_data['recording_id'].unique()

        for rec_id in recordings:
            p(f"    Recording: {rec_id}")
            rdata = rec_data[rec_data['recording_id'] == rec_id]

            for policy in ['local_only', 'strong_local', 'cloud_unlimited', 'combined']:
                pdata = rdata[rdata['policy'] == policy]
                if pdata.empty:
                    continue
                mean_timely = pdata['timely_detections'].mean()
                mean_fa = pdata['false_alerts_per_hr'].mean()
                n_runs = len(pdata)
                p(f"      {policy:15s}: timely={mean_timely:.2f}, "
                  f"FA/hr={mean_fa:.1f} (n={n_runs})")

    # ========================================================================
    # QUESTION 5: What is the cost in false alerts, delay, and communication?
    # ========================================================================
    p("\n## Q5: What is the cost in false alerts, delay, and communication?")
    p("-" * 60)

    for split in ['dev', 'test']:
        p(f"  [{split.upper()}]")
        data = summary[(summary['split'] == split) & (summary['deadline_s'] == DL)]

        for policy in ['local_only', 'strong_local', 'cloud_unlimited',
                       'periodic', 'random', 'suspicion', 'combined']:
            pdata = data[data['policy'] == policy]
            if pdata.empty:
                continue

            for _, row in pdata.iterrows():
                budget_str = f"budget={row['budget_req_per_sec']:.0f}" if not pd.isna(row['budget_req_per_sec']) else "no budget"
                p(f"    {policy:15s} ({budget_str}): "
                  f"FA/hr={row['false_alerts_per_hr']:.1f}, "
                  f"delay={row['mean_detection_delay_s']*1000:.1f}ms, "
                  f"late={row['late_reply_pct']:.1f}%, "
                  f"req_rate={row['actual_request_rate_pct']:.2f}%")

    # ========================================================================
    # HONEST ASSESSMENT
    # ========================================================================
    p("\n## Honest Assessment")
    p("-" * 60)

    # Check if combined actually wins
    dev_data = summary[(summary['split'] == 'dev') & (summary['deadline_s'] == DL)]
    combined_wins = 0
    combined_losses = 0

    budgets = sorted(dev_data['budget_req_per_sec'].dropna().unique())
    for budget in budgets:
        bdata = dev_data[dev_data['budget_req_per_sec'] == budget]
        combined = bdata[bdata['policy'] == 'combined']
        if combined.empty:
            continue
        c = combined.iloc[0]

        for other in ['periodic', 'random']:
            odata = bdata[bdata['policy'] == other]
            if odata.empty:
                continue
            o = odata.iloc[0]

            # Combined wins if: better timely OR same timely but fewer false alerts
            if c['timely_detections'] > o['timely_detections']:
                combined_wins += 1
            elif (c['timely_detections'] == o['timely_detections'] and
                  c['false_alerts_per_hr'] < o['false_alerts_per_hr']):
                combined_wins += 1
            elif c['timely_detections'] < o['timely_detections']:
                combined_losses += 1

    p(f"  Combined vs periodic/random: {combined_wins} wins, {combined_losses} losses")
    if combined_losses > combined_wins:
        p("  *** Combined selection does NOT consistently outperform simpler policies ***")
        p("  *** This negative result should be reported as-is ***")
    elif combined_wins > combined_losses:
        p("  Combined selection shows advantage at some budgets")
    else:
        p("  Results are mixed; no clear winner")

    # Save
    report_text = "\n".join(output_lines)
    with open(RESULTS_DIR / "interpretation.txt", 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"\nSaved to {RESULTS_DIR / 'interpretation.txt'}")


if __name__ == '__main__':
    main()
