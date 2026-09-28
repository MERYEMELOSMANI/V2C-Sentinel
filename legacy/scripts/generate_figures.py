"""
V2C-Sentinel Figure Generation
================================
Step 8: Generates the four paper figures from final experiment results.

Figures:
  1. Architecture diagram (system overview)
  2. Timely detection vs actual cloud-request rate
  3. Detection delay by policy
  4. False alerts per normal driving hour by policy
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import json

RESULTS_DIR = Path("results/final")
FIGURES_DIR = Path("figures/final")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Style settings
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.dpi': 300,
})

POLICY_COLORS = {
    'local_only': '#888888',
    'strong_local': '#2ca02c',
    'cloud_unlimited': '#1f77b4',
    'periodic': '#ff7f0e',
    'random': '#d62728',
    'suspicion': '#9467bd',
    'combined': '#e377c2',
}

POLICY_LABELS = {
    'local_only': 'Local Only (LR)',
    'strong_local': 'Strong Local (RF)',
    'cloud_unlimited': 'Cloud Unlimited',
    'periodic': 'Periodic',
    'random': 'Random',
    'suspicion': 'Suspicion',
    'combined': 'Combined',
}

POLICY_MARKERS = {
    'local_only': 's',
    'strong_local': 'D',
    'cloud_unlimited': '*',
    'periodic': 'o',
    'random': '^',
    'suspicion': 'v',
    'combined': 'P',
}


def load_data():
    summary = pd.read_csv(RESULTS_DIR / "summary.csv")
    runs = pd.read_csv(RESULTS_DIR / "all_runs.csv")
    with open(RESULTS_DIR / "config.json") as f:
        config = json.load(f)
    return summary, runs, config


# ============================================================================
# FIGURE 1: Architecture Diagram
# ============================================================================
def fig1_architecture():
    """System architecture showing message flow and which components are recorded vs simulated."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis('off')
    ax.set_title("V2C-Sentinel: System Architecture", fontsize=14, fontweight='bold', pad=15)

    # Boxes
    boxes = {
        'CAN Bus': (0.3, 2.0, 1.5, 1.0, '#E8F0FE'),
        'Local\nDetector\n(LR)': (2.5, 2.0, 1.3, 1.0, '#E8F8E8'),
        'Request\nSelection\nPolicy': (4.5, 2.0, 1.3, 1.0, '#FFF3E0'),
        'Cloud\nDetector\n(RF)': (6.8, 3.5, 1.3, 1.0, '#E8F0FE'),
        'Decision\nEngine': (6.8, 0.5, 1.3, 1.0, '#FCE4EC'),
        'Warning\nOutput': (8.8, 2.0, 1.0, 1.0, '#F3E5F5'),
    }

    for label, (x, y, w, h, color) in boxes.items():
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                                         facecolor=color, edgecolor='#333333', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center',
                fontsize=8, fontweight='bold')

    # Arrows
    arrow_style = dict(arrowstyle='->', color='#333333', lw=1.5)

    # CAN → Local
    ax.annotate('', xy=(2.5, 2.5), xytext=(1.8, 2.5), arrowprops=arrow_style)
    ax.text(2.15, 2.7, 'messages', fontsize=7, ha='center', color='#666')

    # Local → Policy
    ax.annotate('', xy=(4.5, 2.5), xytext=(3.8, 2.5), arrowprops=arrow_style)
    ax.text(4.15, 2.7, 'score', fontsize=7, ha='center', color='#666')

    # Policy → Cloud (selected msgs)
    ax.annotate('', xy=(6.8, 4.0), xytext=(5.8, 2.8),
                arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=2,
                              connectionstyle='arc3,rad=0.2'))
    ax.text(5.9, 3.6, 'selected\nmessages', fontsize=7, ha='center', color='#1f77b4')

    # Cloud → Decision
    ax.annotate('', xy=(7.45, 1.5), xytext=(7.45, 3.5),
                arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=2))
    ax.text(7.8, 2.5, 'reply\n(+delay)', fontsize=7, ha='center', color='#1f77b4')

    # Policy → Decision (local fallback)
    ax.annotate('', xy=(6.8, 1.0), xytext=(5.8, 2.2),
                arrowprops=dict(arrowstyle='->', color='#ff7f0e', lw=1.5,
                              connectionstyle='arc3,rad=-0.2', linestyle='dashed'))
    ax.text(5.8, 1.3, 'local\nfallback', fontsize=7, ha='center', color='#ff7f0e')

    # Decision → Warning
    ax.annotate('', xy=(8.8, 2.5), xytext=(8.1, 1.3),
                arrowprops=dict(arrowstyle='->', color='#333333', lw=1.5,
                              connectionstyle='arc3,rad=-0.2'))

    # Legend for recorded vs simulated
    recorded = mpatches.Patch(facecolor='#E8F0FE', edgecolor='#333', label='Recorded data (ROAD)')
    simulated = mpatches.Patch(facecolor='#FFF3E0', edgecolor='#333', label='Simulated component')
    network = mpatches.Patch(facecolor='white', edgecolor='#1f77b4', label='5G link (CICV5G delay)')
    ax.legend(handles=[recorded, simulated, network], loc='lower left',
              framealpha=0.9, fontsize=8)

    # 5G delay annotation
    ax.text(6.3, 4.7, '5G Network\n(recorded delays)', fontsize=8,
            ha='center', style='italic', color='#1f77b4',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                     edgecolor='#1f77b4', alpha=0.8))

    fig.savefig(FIGURES_DIR / "fig1_architecture.png")
    fig.savefig(FIGURES_DIR / "fig1_architecture.pdf")
    plt.close(fig)
    print("  Saved fig1_architecture")


# ============================================================================
# FIGURE 2: Timely Detection vs Request Rate
# ============================================================================
def fig2_detection_vs_request_rate(summary, deadline=0.150):
    """Timely detection fraction vs actual cloud-request rate for each policy."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

    for ax, split in zip(axes, ['dev', 'test']):
        data = summary[(summary['split'] == split) & (summary['deadline_s'] == deadline)]

        # Count total attack episodes per split
        total_eps = data['timely_detections'].max() + data['missed_episodes'].max()
        if total_eps == 0:
            total_eps = 1

        for policy in POLICY_LABELS:
            pdata = data[data['policy'] == policy]
            if pdata.empty:
                continue

            x = pdata['actual_request_rate_pct'].values
            y = (pdata['timely_detections'] / total_eps).values

            ax.scatter(x, y, c=POLICY_COLORS[policy],
                      marker=POLICY_MARKERS[policy], s=80,
                      label=POLICY_LABELS[policy], zorder=5, edgecolors='black', linewidths=0.5)

        ax.set_xlabel("Cloud Request Rate (%)")
        ax.set_title(f"{split.upper()} split", fontweight='bold')
        ax.set_xlim(left=-0.5)
        ax.set_ylim(-0.05, 1.15)
        ax.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Timely Detection Rate")
    axes[1].legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)

    fig.suptitle(f"Timely Detection vs Cloud Request Rate (deadline = {deadline*1000:.0f} ms)",
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig2_detection_vs_request_rate.png")
    fig.savefig(FIGURES_DIR / "fig2_detection_vs_request_rate.pdf")
    plt.close(fig)
    print("  Saved fig2_detection_vs_request_rate")


# ============================================================================
# FIGURE 3: Detection Delay by Policy
# ============================================================================
def fig3_detection_delay(runs, deadline=0.150):
    """Box plot of detection delay per policy, with missed episodes shown separately."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, split in zip(axes, ['dev', 'test']):
        data = runs[(runs['split'] == split) & (runs['deadline_s'] == deadline)]

        # Only keep runs with detected episodes (non-NaN delay)
        data = data.dropna(subset=['mean_detection_delay_s'])

        policies_present = [p for p in POLICY_LABELS if p in data['policy'].unique()]

        delays_by_policy = []
        labels = []
        colors = []
        missed_by_policy = {}

        for p in policies_present:
            pdata = data[data['policy'] == p]
            vals = pdata['mean_detection_delay_s'].values * 1000  # convert to ms
            vals = vals[~np.isnan(vals)]
            if len(vals) > 0:
                delays_by_policy.append(vals)
                labels.append(POLICY_LABELS[p])
                colors.append(POLICY_COLORS[p])

            # Count missed from full runs data
            full_pdata = runs[(runs['split'] == split) & (runs['deadline_s'] == deadline) & (runs['policy'] == p)]
            total_missed = full_pdata['missed_episodes'].sum()
            missed_by_policy[POLICY_LABELS[p]] = total_missed

        if delays_by_policy:
            bp = ax.boxplot(delays_by_policy, labels=labels, patch_artist=True, widths=0.6)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            # Deadline line
            ax.axhline(y=deadline * 1000, color='red', linestyle='--', alpha=0.7,
                       label=f'Deadline ({deadline*1000:.0f} ms)')

            ax.set_ylabel("Detection Delay (ms)")
            ax.set_title(f"{split.upper()} split", fontweight='bold')
            ax.tick_params(axis='x', rotation=45)
            ax.legend(fontsize=8)
            ax.grid(True, axis='y', alpha=0.3)

            # Annotate missed episodes below
            missed_text = ", ".join(f"{k}: {v}" for k, v in missed_by_policy.items() if v > 0)
            if missed_text:
                ax.text(0.02, -0.18, f"Missed episodes: {missed_text}",
                        transform=ax.transAxes, fontsize=7, style='italic', color='red')

    fig.suptitle(f"Detection Delay by Policy (deadline = {deadline*1000:.0f} ms)",
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig3_detection_delay.png")
    fig.savefig(FIGURES_DIR / "fig3_detection_delay.pdf")
    plt.close(fig)
    print("  Saved fig3_detection_delay")


# ============================================================================
# FIGURE 4: False Alerts per Normal Driving Hour
# ============================================================================
def fig4_false_alerts(summary, deadline=0.150):
    """Grouped false alerts per normal driving hour by policy and budget."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

    for ax, split in zip(axes, ['dev', 'test']):
        data = summary[(summary['split'] == split) & (summary['deadline_s'] == deadline)]

        policies_present = [p for p in POLICY_LABELS if p in data['policy'].unique()]
        x_positions = np.arange(len(policies_present))
        width = 0.15

        budgets = sorted(data['budget_req_per_sec'].dropna().unique())
        # Add NaN budget for baselines
        budget_groups = [float('nan')] + budgets

        for i, budget in enumerate(budget_groups):
            vals = []
            for p in policies_present:
                if np.isnan(budget):
                    pdata = data[(data['policy'] == p) & (data['budget_req_per_sec'].isna())]
                else:
                    pdata = data[(data['policy'] == p) & (data['budget_req_per_sec'] == budget)]
                if not pdata.empty:
                    vals.append(pdata['false_alerts_per_hr'].values[0])
                else:
                    vals.append(0)

            label = 'No budget' if np.isnan(budget) else f'{budget:.0f} req/s'
            offset = (i - len(budget_groups)/2 + 0.5) * width
            bars = ax.bar(x_positions + offset, vals, width, label=label, alpha=0.8)

        ax.set_xticks(x_positions)
        ax.set_xticklabels([POLICY_LABELS[p] for p in policies_present],
                           rotation=45, ha='right')
        ax.set_title(f"{split.upper()} split", fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3)

    axes[0].set_ylabel("Grouped False Alerts / Normal Driving Hour")
    axes[1].legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)

    fig.suptitle(f"False Alert Burden by Policy (deadline = {deadline*1000:.0f} ms)",
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig4_false_alerts.png")
    fig.savefig(FIGURES_DIR / "fig4_false_alerts.pdf")
    plt.close(fig)
    print("  Saved fig4_false_alerts")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("V2C-Sentinel Figure Generation")
    print("=" * 60)

    summary, runs, config = load_data()
    print(f"Loaded {len(runs)} runs, {len(summary)} summary rows")

    fig1_architecture()
    fig2_detection_vs_request_rate(summary)
    fig3_detection_delay(runs)
    fig4_false_alerts(summary)

    # Also generate for other deadlines
    for dl in [0.100, 0.200, 0.300]:
        fig2_detection_vs_request_rate(summary, deadline=dl)
        fig3_detection_delay(runs, deadline=dl)

    print("\nAll figures saved to figures/final/")


if __name__ == '__main__':
    main()
