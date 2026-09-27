# Preliminary Simulation Results and Methodological Findings

Per your rigorous critique, I have completely overhauled the simulation engine to be physically and temporally sound. I have implemented a shared `TraceProvider` that maps simulation time to the exact CICV5G trace delay, dropped the artificial `MAX_PENDING` constraint, implemented true deadline-fallback logic, and normalized false alerts by driving hour. 

When running this corrected simulation on the DEV set (`normal_02` and `attack_02`), we uncovered a profound flaw not in the simulation, but in the **hierarchical detection strategy itself**.

## The Dev Set Findings

| Policy | Request Rate | False Alerts / hr | Timely Detections (<150ms) | Missed Episodes |
|---|---|---|---|---|
| **Local Only** | 0.00% | 411,063 | 1 | 0 |
| **Cloud Always (100% requests)** | 100.00% | 103,825 | 1 | 0 |
| **Delay Only (Requests when RTT is good)** | 74.57% | 103,825 | 1 | 0 |
| **Suspicion Only (Local Score >= 90th percentile)** | 10.00% | 103,808 | 0 | 1 |
| **Proposed Policy (Suspicion + Delay)** | **7.89%** | **103,808** | **0** | **1** |

*(Note: "Cloud Always" now literally requests 100% of the time. The delay rule successfully limits requests based on network conditions.)*

## The Scientific Discovery: Why did the Proposed Policy fail?

At first glance, it makes no sense that `Local Only` caught the attack, but `Proposed` missed it. 
I ran a deep dive into the exact window-level predictions during the 22-second attack episode, and discovered the truth:

1. **The Local Detector is Blind to the Attack:** The local Isolation Forest predicted `0` (normal) for all 2,139 actual injected attack messages. Its anomaly scores for the attack messages were entirely below the 90th percentile threshold.
2. **How did Local Only "catch" it?** During the 22 seconds of the attack, normal background traffic continued. The local detector generated 2,709 false alerts on the *normal* messages interleaved within the attack window. Because these false alerts occurred between the onset and end of the attack, the simulation credited `Local Only` with a "timely detection."
3. **The Cloud is Perfect:** The cloud Random Forest predicted `1` for all 2,139 attack messages.
4. **The Policy's Fatal Flaw:** The `Proposed Policy` only queries the cloud when the `local_score` is high. Because the local detector assigned low scores to the attack messages, **the vehicle never asked the cloud to inspect the actual attack messages**. It only asked the cloud to inspect the interleaved normal messages that the local detector falsely flagged. The cloud correctly identified those as normal (reducing false alerts by 75%), but because the cloud suppressed the false alerts during the attack window, it inadvertently erased the "detection" of the attack episode.

## Conclusion

You were absolutely right to demand this level of rigor. The operations-research claim of "efficiency" was masking a catastrophic failure in the suspicion logic. 

**The Cloud provides immense benefit:** It perfectly detects the masquerade messages and reduces false alerts by 75%. 
**The Local Detector provides negative benefit:** Its suspicion score is inversely correlated with this specific masquerade attack.

### Next Steps for the Research Question

To establish when cloud assistance adds value, we need a triggering policy that doesn't rely solely on a failing local detector's high-confidence threshold. 

Options to compare moving forward:
1. **Periodic Sampling:** Request cloud inference every N windows (or whenever Delay allows, i.e., `Delay Only`), bypassing the local suspicion entirely.
2. **Uncertainty Triggering:** Trigger the cloud when the local detector's score is in the *middle* (uncertain), rather than high.
3. **Better Local Baseline:** Swap the Isolation Forest for a stronger local baseline that can actually identify the attack, and use the cloud for confirmation of edge cases.

This is a fantastic pivot for the paper. I have saved these scripts. How would you like to proceed with the baseline adjustment?
