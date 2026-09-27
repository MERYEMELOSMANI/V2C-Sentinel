import sys
import re

with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_cloud_confirmation_experiment.py", "r", encoding="utf-8") as f:
    content = f.read()

# normalize newlines for easy replacement
content = content.replace("\r\n", "\n")

old_str = """        # --- Policy decision ---
        is_suspicious = row.local_score >= score_threshold

        is_periodic = False
        if obs_time >= next_periodic_time:
            is_periodic = True
            while next_periodic_time <= obs_time:
                next_periodic_time += periodic_interval

        wants_request = False

        if policy_type == "local_only":
            wants_request = False
        elif policy_type == "strong_local":
            wants_request = False
        elif policy_type == "cloud_unlimited":
            wants_request = True
        elif policy_type == "periodic":
            wants_request = is_periodic
        elif policy_type == "random":
            wants_request = rng.random() < random_prob
        elif policy_type == "suspicion":
            wants_request = is_suspicious
        elif policy_type == "combined":
            wants_request = is_suspicious or is_periodic

        # --- Budget check ---
        if wants_request and not bucket.try_consume(local_done_time):
            wants_request = False  # budget exhausted

        # --- Execute request or local-only decision ---
        if wants_request:
            actual_delay = delay_provider.get_delay_at(local_done_time)
            cloud_return_time = local_done_time + actual_delay + CONFIG['cloud_proc_time_s']
            deadline_time = local_done_time + deadline

            reply = {
                'return_time': cloud_return_time,
                'rtt': actual_delay,
                'deadline': deadline_time,
                'pred': row.cloud_pred,
                'window_idx': idx
            }
            heapq.heappush(pending_replies, (cloud_return_time, seq, reply))
            seq += 1

            is_late = cloud_return_time > deadline_time

            # Local fallback logic: if cloud will be late AND local says attack,
            # issue local_fallback warning at deadline
            if row.local_pred == 1:
                if is_late:
                    warnings.append({
                        'time': deadline_time,
                        'source': 'local_fallback',
                        'window_idx': idx
                    })
                elif row.cloud_pred == 0:
                    # Cloud arrives in time and says normal → suppress local warning
                    pass
                # else: cloud arrives in time and says attack → cloud_timely handles it

            request_log.append({
                'sent': local_done_time,
                'returned': cloud_return_time,
                'late': is_late,
                'rtt': actual_delay
            })

        else:
            # No cloud request — use local/strong_local decision
            if policy_type == "strong_local":
                if row.cloud_pred == 1:  # RF prediction used locally
                    warnings.append({
                        'time': local_done_time,
                        'source': 'strong_local',
                        'window_idx': idx
                    })
            else:
                if row.local_pred == 1:
                    warnings.append({
                        'time': local_done_time,
                        'source': 'local_immediate',
                        'window_idx': idx
                    })"""

new_str = """        # --- Policy decision ---
        is_suspicious = row.local_score >= score_threshold

        is_periodic = False
        if obs_time >= next_periodic_time:
            is_periodic = True
            while next_periodic_time <= obs_time:
                next_periodic_time += periodic_interval

        wants_request = False

        if policy_type == "local_only":
            wants_request = False
        elif policy_type == "strong_local":
            wants_request = False
        elif policy_type == "cloud_unlimited":
            wants_request = True
        elif policy_type == "periodic":
            wants_request = is_periodic
        elif policy_type == "random":
            wants_request = rng.random() < random_prob
        elif policy_type == "suspicion":
            wants_request = is_suspicious
        elif policy_type == "combined":
            wants_request = is_suspicious or is_periodic
        elif policy_type == "cloud_confirm":
            wants_request = (row.local_pred == 1)
        elif policy_type == "cloud_confirm_fallback":
            wants_request = (row.local_pred == 1)
        elif policy_type == "cloud_confirm_budgeted":
            wants_request = (row.local_pred == 1 and is_suspicious)

        # --- Budget check ---
        budget_allows = True
        if wants_request and not bucket.try_consume(local_done_time):
            wants_request = False  # budget exhausted
            budget_allows = False

        # --- Execute request or local-only decision ---
        if wants_request:
            actual_delay = delay_provider.get_delay_at(local_done_time)
            cloud_return_time = local_done_time + actual_delay + CONFIG['cloud_proc_time_s']
            deadline_time = local_done_time + deadline

            reply = {
                'return_time': cloud_return_time,
                'rtt': actual_delay,
                'deadline': deadline_time,
                'pred': row.cloud_pred,
                'window_idx': idx
            }
            heapq.heappush(pending_replies, (cloud_return_time, seq, reply))
            seq += 1

            is_late = cloud_return_time > deadline_time

            if policy_type in ["cloud_confirm", "cloud_confirm_fallback", "cloud_confirm_budgeted"]:
                if is_late:
                    if policy_type in ["cloud_confirm_fallback", "cloud_confirm_budgeted"]:
                        # Cloud is late, fallback to local decision
                        if row.local_pred == 1:
                            warnings.append({
                                'time': deadline_time,
                                'source': 'local_fallback',
                                'window_idx': idx
                            })
                    elif policy_type == "cloud_confirm":
                        # Strict confirmation: if cloud is late, no timely alert is generated
                        pass
                else:
                    # Cloud is on time.
                    # If it says attack, it will be added as cloud_timely by the pending_replies loop.
                    # If it says normal, it suppresses the alert automatically (no warning appended here).
                    pass
            else:
                # Old fallback logic for other policies
                if row.local_pred == 1:
                    if is_late:
                        warnings.append({
                            'time': deadline_time,
                            'source': 'local_fallback',
                            'window_idx': idx
                        })
                    elif row.cloud_pred == 0:
                        # Cloud arrives in time and says normal → suppress local warning
                        pass

            request_log.append({
                'sent': local_done_time,
                'returned': cloud_return_time,
                'late': is_late,
                'rtt': actual_delay
            })

        else:
            # No cloud request — use local/strong_local decision
            if policy_type == "strong_local":
                if row.cloud_pred == 1:  # RF prediction used locally
                    warnings.append({
                        'time': local_done_time,
                        'source': 'strong_local',
                        'window_idx': idx
                    })
            elif policy_type in ["cloud_confirm", "cloud_confirm_fallback", "cloud_confirm_budgeted"]:
                if row.local_pred == 1:
                    if policy_type in ["cloud_confirm_fallback", "cloud_confirm_budgeted"]:
                        # Budget didn't allow asking cloud, fallback to local
                        warnings.append({
                            'time': local_done_time,
                            'source': 'local_immediate',
                            'window_idx': idx
                        })
                    elif policy_type == "cloud_confirm":
                        # Strict confirmation requires cloud. If budget didn't allow, no alert.
                        pass
            else:
                if row.local_pred == 1:
                    warnings.append({
                        'time': local_done_time,
                        'source': 'local_immediate',
                        'window_idx': idx
                    })"""

if old_str not in content:
    print("Old string not found after normalization!")
    # Try finding via regex to handle spacing
    print("Content preview:")
    print(content[content.find("# --- Policy decision ---"):content.find("# --- Policy decision ---")+500])
else:
    content = content.replace(old_str, new_str)
    with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_cloud_confirmation_experiment.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Replacement successful.")
