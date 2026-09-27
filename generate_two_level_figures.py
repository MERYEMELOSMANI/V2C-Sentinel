"""
Generate final figures and tables for the Two-Level Alert System paper.

Uses the CORRECTED summary.csv with proper detection rates.
Shows dev and test splits separately to reveal attack-dependent latency.
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

RESULTS_DIR = Path("results/final_two_level")
FIGURES_DIR = Path("figures/final")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

def main():
    df = pd.read_csv(RESULTS_DIR / "summary.csv")

    # ================================================================
    # Figure 1: Three-panel figure
    #   (a) False Alert Rate — dev split (same for test, so one panel)
    #   (b) Detection Delay — Dev attack
    #   (c) Detection Delay — Test attack
    # ================================================================
    budget_labels = ['1', '5', '10', '50', 'unlim.']
    x = np.arange(len(budget_labels))
    w = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    ax_fa, ax_dev, ax_test = axes

    # Use 150ms deadline throughout
    dev150 = df[(df['split'] == 'dev') & (df['deadline_s'] == 0.15)].sort_values('total_requests')
    test150 = df[(df['split'] == 'test') & (df['deadline_s'] == 0.15)].sort_values('total_requests')

    # --- Panel A: False alerts per hour (dev, representative) ---
    l1_fa = dev150['level1_local_false_per_hr'].values
    l2_fa = dev150['level2_cloud_false_per_hr'].values

    bars1 = ax_fa.bar(x - w/2, l1_fa, w, label='Level 1: Local', color='#e07b54', edgecolor='white')
    bars2 = ax_fa.bar(x + w/2, l2_fa, w, label='Level 2: Cloud', color='#5b9bd5', edgecolor='white')
    ax_fa.set_xticks(x)
    ax_fa.set_xticklabels(budget_labels)
    ax_fa.set_xlabel('Cloud Request Budget (req/s)')
    ax_fa.set_ylabel('False Alerts per Hour')
    ax_fa.set_title('(a) False Alert Rate\n(Normal Recordings)')
    ax_fa.legend(fontsize=8)
    ax_fa.set_yscale('symlog', linthresh=1)
    ax_fa.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))

    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax_fa.text(bar.get_x() + bar.get_width()/2., h, f'{h:,.0f}',
                       ha='center', va='bottom', fontsize=7)
    for bar in bars2:
        h = bar.get_height()
        ax_fa.text(bar.get_x() + bar.get_width()/2., max(h, 0.5), f'{h:,.0f}',
                   ha='center', va='bottom', fontsize=7)

    # --- Panel B: Detection Delay — Dev attack ---
    l1_dev = dev150['level1_local_delay'].values * 1000
    l2_dev = dev150['level2_cloud_delay'].values * 1000

    ax_dev.bar(x - w/2, l1_dev, w, label='Level 1: Local', color='#e07b54', edgecolor='white')
    b2_dev = ax_dev.bar(x + w/2, l2_dev, w, label='Level 2: Cloud', color='#5b9bd5', edgecolor='white')
    ax_dev.axhline(150, color='red', linestyle='--', linewidth=1, label='150 ms deadline')
    ax_dev.set_xticks(x)
    ax_dev.set_xticklabels(budget_labels)
    ax_dev.set_xlabel('Cloud Request Budget (req/s)')
    ax_dev.set_ylabel('Detection Delay (ms)')
    ax_dev.set_title('(b) Detection Delay\n(Dev Attack Recording)')
    ax_dev.legend(fontsize=7, loc='upper right')

    # Add value labels on cloud bars
    for bar in b2_dev:
        h = bar.get_height()
        if h > 0:
            label = f'{h:,.0f}' if h >= 10 else f'{h:.1f}'
            ax_dev.text(bar.get_x() + bar.get_width()/2., h, label,
                        ha='center', va='bottom', fontsize=7)

    # --- Panel C: Detection Delay — Test attack ---
    l1_test = test150['level1_local_delay'].values * 1000
    l2_test = test150['level2_cloud_delay'].values * 1000

    ax_test.bar(x - w/2, l1_test, w, label='Level 1: Local', color='#e07b54', edgecolor='white')
    b2_test = ax_test.bar(x + w/2, l2_test, w, label='Level 2: Cloud', color='#5b9bd5', edgecolor='white')
    ax_test.axhline(150, color='red', linestyle='--', linewidth=1, label='150 ms deadline')
    ax_test.set_xticks(x)
    ax_test.set_xticklabels(budget_labels)
    ax_test.set_xlabel('Cloud Request Budget (req/s)')
    ax_test.set_ylabel('Detection Delay (ms)')
    ax_test.set_title('(c) Detection Delay\n(Test Attack Recording)')
    ax_test.legend(fontsize=7, loc='upper right')

    for bar in b2_test:
        h = bar.get_height()
        if h > 0:
            label = f'{h:,.0f}' if h >= 10 else f'{h:.1f}'
            ax_test.text(bar.get_x() + bar.get_width()/2., h, label,
                        ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "two_level_system.png", dpi=300, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / "two_level_system.pdf", bbox_inches='tight')
    print("Saved figures/final/two_level_system.png/.pdf")

    # ================================================================
    # Figure 2: Budget vs Cloud Requests Used (dev + test side by side)
    # ================================================================
    fig2, (ax_bdev, ax_btest) = plt.subplots(1, 2, figsize=(11, 4))

    for ax_b, split_df, title in [(ax_bdev, dev150, 'Dev Split'), (ax_btest, test150, 'Test Split')]:
        budgeted = split_df[split_df['budget'] != 'unlimited'].copy()
        budgeted['budget_f'] = budgeted['budget'].astype(float)
        unlim = split_df[split_df['budget'] == 'unlimited']['total_requests'].values[0]
        all_labels = list(budgeted['budget_f'].astype(str)) + ['unlim.']
        all_vals = list(budgeted['total_requests']) + [unlim]
        ax_b.bar(all_labels, all_vals, color='#5b9bd5', edgecolor='white')
        for i, v in enumerate(all_vals):
            ax_b.text(i, v + max(all_vals)*0.02, f'{v:,.0f}', ha='center', fontsize=8)
        ax_b.set_xlabel('Cloud Request Budget (req/s)')
        ax_b.set_ylabel('Total Cloud Requests Sent')
        ax_b.set_title(f'Cloud Requests — {title}')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig2.text(0.5, 0.02, 
              "Note: Raw request counts differ across splits because recording durations differ; budget is expressed in requests per second.", 
              ha='center', fontsize=9, style='italic', color='gray')
    plt.savefig(FIGURES_DIR / "cloud_budget_usage.png", dpi=300, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / "cloud_budget_usage.pdf", bbox_inches='tight')
    print("Saved figures/final/cloud_budget_usage.png/.pdf")

    # ================================================================
    # Table: Corrected paper-ready summary (both splits)
    # ================================================================
    d150 = df[df['deadline_s'] == 0.15].sort_values(['split', 'total_requests'])
    table = d150[['split', 'budget', 'attack_episodes',
                  'level1_local_detect_rate', 'level1_local_delay',
                  'level1_local_false_per_hr',
                  'level2_cloud_detect_rate', 'level2_cloud_delay',
                  'level2_cloud_false_per_hr',
                  'total_requests']].copy()
    table.columns = ['Split', 'Budget', 'Attacks',
                     'L1 DetRate', 'L1 Delay(s)', 'L1 FA/hr',
                     'L2 DetRate', 'L2 Delay(s)', 'L2 FA/hr',
                     'Requests']
    table['L1 DetRate'] = table['L1 DetRate'].map(lambda v: f'{v:.0%}')
    table['L2 DetRate'] = table['L2 DetRate'].map(lambda v: f'{v:.0%}')
    table['L1 Delay(s)'] = table['L1 Delay(s)'].map(lambda v: f'{v:.3f}')
    table['L2 Delay(s)'] = table['L2 Delay(s)'].map(lambda v: f'{v:.3f}')
    table['L1 FA/hr'] = table['L1 FA/hr'].map(lambda v: f'{v:,.0f}')
    table['L2 FA/hr'] = table['L2 FA/hr'].map(lambda v: f'{v:,.0f}')
    table['Requests'] = table['Requests'].map(lambda v: f'{v:,.0f}')
    table.to_csv(RESULTS_DIR / "paper_table.csv", index=False)
    print("\nCorrected Paper Table (150ms deadline, both splits):")
    print(table.to_string(index=False))

if __name__ == "__main__":
    main()
