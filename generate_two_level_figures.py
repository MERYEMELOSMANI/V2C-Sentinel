"""
Generate final figures and tables for the Two-Level Alert System paper.
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
    dev = df[df['split'] == 'dev'].copy()

    # ================================================================
    # Figure 1: Two-panel bar chart — False Alerts & Detection Delay
    # ================================================================
    budget_labels = ['1', '5', '10', '50', 'unlim.']
    x = np.arange(len(budget_labels))
    w = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    # --- Panel A: False alerts per hour (150ms deadline) ---
    d150 = dev[dev['deadline_s'] == 0.15].sort_values('total_requests')
    l1_fa = d150['level1_local_false_per_hr'].values
    l2_fa = d150['level2_cloud_false_per_hr'].values

    bars1 = ax1.bar(x - w/2, l1_fa, w, label='Level 1: Local Warning', color='#e07b54', edgecolor='white')
    bars2 = ax1.bar(x + w/2, l2_fa, w, label='Level 2: Cloud Confirmed', color='#5b9bd5', edgecolor='white')
    ax1.set_xticks(x)
    ax1.set_xticklabels(budget_labels)
    ax1.set_xlabel('Cloud Request Budget (req/s)')
    ax1.set_ylabel('False Alerts per Hour')
    ax1.set_title('(a) False Alert Rate by Alert Level')
    ax1.legend(fontsize=8)
    ax1.set_yscale('symlog', linthresh=1)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))

    # Add value labels on bars
    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., h, f'{h:,.0f}',
                     ha='center', va='bottom', fontsize=7)
    for bar in bars2:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., max(h, 0.5), f'{h:,.0f}',
                 ha='center', va='bottom', fontsize=7)

    # --- Panel B: Detection delay ---
    l1_delay = d150['level1_local_delay'].values
    l2_delay = d150['level2_cloud_delay'].values

    ax2.bar(x - w/2, l1_delay * 1000, w, label='Level 1: Local Warning', color='#e07b54', edgecolor='white')
    ax2.bar(x + w/2, l2_delay * 1000, w, label='Level 2: Cloud Confirmed', color='#5b9bd5', edgecolor='white')
    ax2.axhline(150, color='red', linestyle='--', linewidth=1, label='150 ms deadline')
    ax2.set_xticks(x)
    ax2.set_xticklabels(budget_labels)
    ax2.set_xlabel('Cloud Request Budget (req/s)')
    ax2.set_ylabel('Detection Delay (ms)')
    ax2.set_title('(b) Detection Delay by Alert Level')
    ax2.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "two_level_system.png", dpi=300, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / "two_level_system.pdf", bbox_inches='tight')
    print("Saved figures/final/two_level_system.png/.pdf")

    # ================================================================
    # Figure 2: Budget vs Cloud Requests Used
    # ================================================================
    fig2, ax3 = plt.subplots(figsize=(6, 4))
    d150_budgeted = d150[d150['budget'] != 'unlimited'].copy()
    d150_budgeted['budget_f'] = d150_budgeted['budget'].astype(float)
    ax3.bar(d150_budgeted['budget_f'].astype(str), d150_budgeted['total_requests'],
            color='#5b9bd5', edgecolor='white')
    # Add unlimited as separate bar
    unlim = d150[d150['budget'] == 'unlimited']['total_requests'].values[0]
    all_labels = list(d150_budgeted['budget_f'].astype(str)) + ['unlim.']
    all_vals = list(d150_budgeted['total_requests']) + [unlim]
    ax3.clear()
    ax3.bar(all_labels, all_vals, color='#5b9bd5', edgecolor='white')
    for i, v in enumerate(all_vals):
        ax3.text(i, v + 200, f'{v:,.0f}', ha='center', fontsize=8)
    ax3.set_xlabel('Cloud Request Budget (req/s)')
    ax3.set_ylabel('Total Cloud Requests Sent')
    ax3.set_title('Cloud Requests Under Budget Constraints')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cloud_budget_usage.png", dpi=300, bbox_inches='tight')
    print("Saved figures/final/cloud_budget_usage.png")

    # ================================================================
    # Table: Paper-ready LaTeX-style summary
    # ================================================================
    table = d150[['budget', 'level1_local_timely', 'level1_local_delay',
                  'level1_local_false_per_hr', 'level2_cloud_timely',
                  'level2_cloud_delay', 'level2_cloud_false_per_hr',
                  'total_requests']].copy()
    table.columns = ['Budget', 'L1 Detect', 'L1 Delay(s)', 'L1 FA/hr',
                     'L2 Detect', 'L2 Delay(s)', 'L2 FA/hr', 'Requests']
    table['L1 Delay(s)'] = table['L1 Delay(s)'].map(lambda v: f'{v:.3f}')
    table['L2 Delay(s)'] = table['L2 Delay(s)'].map(lambda v: f'{v:.3f}')
    table['L1 FA/hr'] = table['L1 FA/hr'].map(lambda v: f'{v:,.0f}')
    table['L2 FA/hr'] = table['L2 FA/hr'].map(lambda v: f'{v:,.0f}')
    table['Requests'] = table['Requests'].map(lambda v: f'{v:,.0f}')
    table.to_csv(RESULTS_DIR / "paper_table.csv", index=False)
    print("\nPaper Table (dev, 150ms deadline):")
    print(table.to_string(index=False))

if __name__ == "__main__":
    main()
