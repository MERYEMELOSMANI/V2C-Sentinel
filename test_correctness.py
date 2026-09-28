"""
V2C-Sentinel Correctness Tests
================================
Step 4: Small examples with known answers.
All must pass before running the full experiment.

Test cases:
  1. Attack message receives timely positive cloud reply → timely detection
  2. Cloud reply arrives after deadline → local fallback, NOT timely cloud
  3. Normal message causes false warning during attack interval → false alert counted
  4. Local detector identifies attack without cloud help → local_immediate warning
  5. Periodic offsets produce different sample times → verified
  6. Budget enforcement → requests denied when bucket empty
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_unified_experiment import (
    simulate_policy, evaluate_run, extract_episodes, group_alerts,
    TokenBucket, UnlimitedBucket, TraceProvider, CONFIG
)


class FakeTraceProvider:
    """Returns a fixed sequence of delays for testing."""

    def __init__(self, delays):
        self.delays = delays
        self.idx = 0
        self.max_time = 1000.0
        self.times = np.arange(len(delays)) * 10.0

    def get_delay_at(self, sim_time):
        d = self.delays[self.idx % len(self.delays)]
        self.idx += 1
        return d


def make_recording(timestamps, true_labels, local_scores, local_preds,
                   cloud_preds, cloud_scores=None):
    """Create a synthetic recording DataFrame."""
    n = len(timestamps)
    if cloud_scores is None:
        cloud_scores = [0.5] * n
    return pd.DataFrame({
        'timestamp': timestamps,
        'true_label': true_labels,
        'local_score': local_scores,
        'local_pred': local_preds,
        'cloud_score': cloud_scores,
        'cloud_pred': cloud_preds,
        'recording_id': ['test'] * n,
        'split': ['test'] * n
    })


PASS_COUNT = 0
FAIL_COUNT = 0


def assert_test(condition, name, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        print(f"  PASS: {name}")
        PASS_COUNT += 1
    else:
        print(f"  FAIL: {name} - {detail}")
        FAIL_COUNT += 1


# ============================================================================
# TEST 1: Attack message receives timely positive cloud reply
# ============================================================================
def test_1_timely_cloud_detection():
    print("\nTest 1: Timely positive cloud reply -> timely detection")

    # One attack message at t=1.0, cloud correctly predicts 1
    # Cloud delay: 50ms → returns at 1.0 + 0.005 + 0.050 + 0.010 = 1.065
    # Deadline: 1.0 + 0.005 + 0.150 = 1.155
    # 1.065 < 1.155 → timely
    rec = make_recording(
        timestamps=[1.0],
        true_labels=[1],
        local_scores=[0.1],  # below threshold → won't trigger suspicion
        local_preds=[0],
        cloud_preds=[1]
    )

    provider = FakeTraceProvider([0.050])
    bucket = UnlimitedBucket()

    warnings, requests, late = simulate_policy(
        rec, provider, 'cloud_unlimited',
        score_threshold=0.5, deadline=0.150,
        bucket=bucket
    )

    assert_test(len(requests) == 1, "One request sent")
    assert_test(len(warnings) == 1, "One warning issued",
                f"Got {len(warnings)} warnings")
    if len(warnings) > 0:
        assert_test(warnings.iloc[0]['source'] == 'cloud_timely',
                    "Warning source is cloud_timely",
                    f"Got {warnings.iloc[0]['source']}")

    episodes = [{'onset': 1.0, 'end': 1.0}]
    eval_r = evaluate_run(rec, warnings, episodes, 0.150)
    assert_test(eval_r['timely_detections'] == 1, "Episode counted as timely")


# ============================================================================
# TEST 2: Cloud reply arrives after deadline
# ============================================================================
def test_2_late_cloud_reply():
    print("\nTest 2: Cloud reply after deadline -> local fallback, not timely cloud")

    # Attack at t=1.0, local predicts 1, cloud predicts 1
    # Cloud delay: 200ms → returns at 1.0 + 0.005 + 0.200 + 0.010 = 1.215
    # Deadline: 1.0 + 0.005 + 0.150 = 1.155
    # 1.215 > 1.155 → late
    # Because local_pred=1 and cloud is late, local_fallback at deadline
    rec = make_recording(
        timestamps=[1.0],
        true_labels=[1],
        local_scores=[0.9],
        local_preds=[1],
        cloud_preds=[1]
    )

    provider = FakeTraceProvider([0.200])
    bucket = UnlimitedBucket()

    warnings, requests, late = simulate_policy(
        rec, provider, 'cloud_unlimited',
        score_threshold=0.5, deadline=0.150,
        bucket=bucket
    )

    assert_test(len(requests) == 1, "One request sent")

    fallback_warnings = warnings[warnings['source'] == 'local_fallback'] if not warnings.empty else pd.DataFrame()
    assert_test(len(fallback_warnings) == 1, "Local fallback warning issued",
                f"Got {len(fallback_warnings)} fallback warnings")

    cloud_timely = warnings[warnings['source'] == 'cloud_timely'] if not warnings.empty else pd.DataFrame()
    assert_test(len(cloud_timely) == 0, "No timely cloud warning",
                f"Got {len(cloud_timely)} cloud_timely warnings")

    assert_test(len(late) == 1, "Late reply logged",
                f"Got {len(late)} late entries")


# ============================================================================
# TEST 3: Normal message causes false warning during attack interval
# ============================================================================
def test_3_false_warning_in_attack_interval():
    print("\nTest 3: Normal message false warning during attack interval")

    # Messages: normal(0.9), attack(1.0), normal(1.1) in attack interval, attack(1.2)
    # Local falsely flags the normal at 1.1 as attack
    rec = make_recording(
        timestamps=[0.9, 1.0, 1.1, 1.2],
        true_labels=[0, 1, 0, 1],
        local_scores=[0.1, 0.1, 0.9, 0.1],
        local_preds=[0, 0, 1, 0],  # false positive on normal msg at t=1.1
        cloud_preds=[0, 1, 0, 1]
    )

    warnings, requests, late = simulate_policy(
        rec, FakeTraceProvider([0.050]), 'local_only',
        score_threshold=0.5, deadline=0.150,
        bucket=UnlimitedBucket()
    )

    # The warning at t=1.1 is on a normal message → it's a false warning
    assert_test(len(warnings) == 1, "One warning from local",
                f"Got {len(warnings)}")
    if not warnings.empty:
        label = rec.loc[warnings.iloc[0]['window_idx'], 'true_label']
        assert_test(label == 0, "Warning is on a normal message (false alert)",
                    f"Label was {label}")

    episodes = extract_episodes(rec)
    eval_r = evaluate_run(rec, warnings, episodes, 0.150)
    assert_test(eval_r['raw_false_warnings'] == 1, "One raw false warning counted",
                f"Got {eval_r['raw_false_warnings']}")


# ============================================================================
# TEST 4: Local detector identifies attack without cloud
# ============================================================================
def test_4_local_only_detection():
    print("\nTest 4: Local detector identifies attack without cloud help")

    rec = make_recording(
        timestamps=[1.0, 1.05, 1.10],
        true_labels=[1, 1, 1],
        local_scores=[0.9, 0.9, 0.9],
        local_preds=[1, 1, 1],
        cloud_preds=[1, 1, 1]
    )

    warnings, requests, late = simulate_policy(
        rec, FakeTraceProvider([0.050]), 'local_only',
        score_threshold=0.5, deadline=0.150,
        bucket=UnlimitedBucket()
    )

    assert_test(len(requests) == 0, "No cloud requests in local_only")
    assert_test(len(warnings) == 3, "Three local_immediate warnings",
                f"Got {len(warnings)}")
    if not warnings.empty:
        assert_test(all(warnings['source'] == 'local_immediate'),
                    "All warnings are local_immediate",
                    f"Sources: {warnings['source'].tolist()}")

    episodes = [{'onset': 1.0, 'end': 1.10}]
    eval_r = evaluate_run(rec, warnings, episodes, 0.150)
    assert_test(eval_r['timely_detections'] == 1, "Episode detected timely")
    assert_test(eval_r['missed_episodes'] == 0, "No missed episodes")


# ============================================================================
# TEST 5: Periodic offsets produce different sample times
# ============================================================================
def test_5_periodic_offsets():
    print("\nTest 5: Different periodic offsets -> different sample times")

    rec = make_recording(
        timestamps=[float(i) / 100.0 for i in range(100)],  # 0.00 to 0.99
        true_labels=[0] * 100,
        local_scores=[0.1] * 100,
        local_preds=[0] * 100,
        cloud_preds=[0] * 100
    )

    request_times_by_offset = {}
    for offset in [0.0, 0.05, 0.10]:
        _, reqs, _ = simulate_policy(
            rec, FakeTraceProvider([0.020] * 100), 'periodic',
            score_threshold=0.5, deadline=0.150,
            bucket=UnlimitedBucket(),
            periodic_interval=0.20, offset=offset
        )
        times = tuple(round(t, 4) for t in reqs['sent'].tolist()) if not reqs.empty else ()
        request_times_by_offset[offset] = times

    # Offsets 0.0 and 0.05 should produce different request times
    assert_test(
        request_times_by_offset[0.0] != request_times_by_offset[0.05],
        "Offset 0.00 and 0.05 produce different request patterns",
        f"Both produced: {request_times_by_offset[0.0][:5]}..."
    )
    assert_test(
        request_times_by_offset[0.0] != request_times_by_offset[0.10],
        "Offset 0.00 and 0.10 produce different request patterns"
    )


# ============================================================================
# TEST 6: Budget enforcement — requests denied when bucket empty
# ============================================================================
def test_6_budget_enforcement():
    print("\nTest 6: Budget limits actual request count")

    # 100 messages over 1 second, budget = 5 req/s
    # Even if policy wants every message, should get ~5 requests
    rec = make_recording(
        timestamps=[float(i) / 100.0 for i in range(100)],
        true_labels=[0] * 100,
        local_scores=[0.9] * 100,
        local_preds=[0] * 100,
        cloud_preds=[0] * 100
    )

    # With unlimited bucket → should get many requests
    _, reqs_unlimited, _ = simulate_policy(
        rec, FakeTraceProvider([0.020] * 100), 'suspicion',
        score_threshold=0.5, deadline=0.150,
        bucket=UnlimitedBucket()
    )

    # With 5 req/s budget → should get much fewer
    bucket = TokenBucket(5.0)
    _, reqs_limited, _ = simulate_policy(
        rec, FakeTraceProvider([0.020] * 100), 'suspicion',
        score_threshold=0.5, deadline=0.150,
        bucket=bucket
    )

    assert_test(len(reqs_unlimited) == 100,
                f"Unlimited: all 100 messages requested",
                f"Got {len(reqs_unlimited)}")
    assert_test(len(reqs_limited) < len(reqs_unlimited),
                f"Budget: fewer requests than unlimited ({len(reqs_limited)} < {len(reqs_unlimited)})")
    assert_test(len(reqs_limited) <= 10,
                f"Budget: at most ~10 requests for 5 req/s over 1s (got {len(reqs_limited)})",
                f"Got {len(reqs_limited)}")

    # Verify actual rate
    if not reqs_limited.empty:
        duration = reqs_limited['sent'].max() - reqs_limited['sent'].min()
        if duration > 0:
            actual_rate = len(reqs_limited) / duration
            print(f"    Actual rate: {actual_rate:.1f} req/s (budget: 5.0 req/s)")


# ============================================================================
# TEST 7: Strong-local baseline uses cloud_pred locally
# ============================================================================
def test_7_strong_local():
    print("\nTest 7: Strong-local baseline uses RF predictions locally")

    rec = make_recording(
        timestamps=[1.0, 1.1],
        true_labels=[1, 0],
        local_scores=[0.1, 0.1],
        local_preds=[0, 0],
        cloud_preds=[1, 0]  # RF correctly detects attack, correctly passes normal
    )

    warnings, requests, late = simulate_policy(
        rec, FakeTraceProvider([0.050]), 'strong_local',
        score_threshold=0.5, deadline=0.150,
        bucket=UnlimitedBucket()
    )

    assert_test(len(requests) == 0, "No network requests for strong_local")
    assert_test(len(warnings) == 1, "One warning issued",
                f"Got {len(warnings)}")
    if not warnings.empty:
        assert_test(warnings.iloc[0]['source'] == 'strong_local',
                    "Source is strong_local",
                    f"Got {warnings.iloc[0]['source']}")
        assert_test(warnings.iloc[0]['window_idx'] == 0,
                    "Warning on attack message (idx 0)")


# ============================================================================
# TEST 8: Episode extraction with interleaved normal messages
# ============================================================================
def test_8_episode_extraction():
    print("\nTest 8: Episode extraction handles interleaved normal messages")

    rec = make_recording(
        timestamps=[1.0, 1.1, 1.2, 1.3, 5.0, 5.1],
        true_labels=[1, 1, 0, 1, 1, 1],
        local_scores=[0.1] * 6,
        local_preds=[0] * 6,
        cloud_preds=[0] * 6
    )

    episodes = extract_episodes(rec, gap_tolerance=0.5)

    # Messages at 1.0, 1.1, 1.3 (attack) with gap at 1.2 (normal) → within 0.5s tolerance
    # Messages at 5.0, 5.1 (attack) → separate episode (gap > 0.5s from 1.3)
    assert_test(len(episodes) == 2, f"Two episodes extracted (got {len(episodes)})")
    if len(episodes) == 2:
        assert_test(abs(episodes[0]['onset'] - 1.0) < 0.01, "Episode 1 starts at 1.0")
        assert_test(abs(episodes[0]['end'] - 1.3) < 0.01, "Episode 1 ends at 1.3")
        assert_test(abs(episodes[1]['onset'] - 5.0) < 0.01, "Episode 2 starts at 5.0")


# ============================================================================
# TEST 9: False alert grouping
# ============================================================================
def test_9_alert_grouping():
    print("\nTest 9: False alert grouping within 1-second window")

    times = [1.0, 1.3, 1.5, 3.0, 3.2, 6.0]
    # Groups: [1.0, 1.3, 1.5], [3.0, 3.2], [6.0] → 3 grouped alerts
    groups = group_alerts(times, threshold=1.0)
    assert_test(groups == 3, f"3 grouped alerts (got {groups})")

    # Empty
    assert_test(group_alerts([], threshold=1.0) == 0, "Empty -> 0 groups")

    # Single
    assert_test(group_alerts([5.0], threshold=1.0) == 1, "Single -> 1 group")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("V2C-Sentinel Correctness Tests")
    print("=" * 60)

    test_1_timely_cloud_detection()
    test_2_late_cloud_reply()
    test_3_false_warning_in_attack_interval()
    test_4_local_only_detection()
    test_5_periodic_offsets()
    test_6_budget_enforcement()
    test_7_strong_local()
    test_8_episode_extraction()
    test_9_alert_grouping()

    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    print("=" * 60)

    if FAIL_COUNT > 0:
        print("\n*** CORRECTNESS TESTS FAILED - DO NOT PROCEED ***")
        sys.exit(1)
    else:
        print("\nAll correctness tests passed. Safe to proceed with full experiment.")
        sys.exit(0)
