import sys

with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_cloud_confirmation_experiment.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update CONFIG policies
content = content.replace(
    '        "local_only", "strong_local", "cloud_unlimited",\n        "periodic", "random", "suspicion", "combined"\n',
    '        "local_only", "strong_local", "cloud_unlimited",\n        "suspicion", "cloud_confirm", "cloud_confirm_fallback", "cloud_confirm_budgeted"\n'
)

old_build_jobs = """def build_jobs(config, avg_msg_rate):
    \"\"\"Build the list of (policy, budget, deadline, seed, offset) jobs.\"\"\"
    jobs = []

    for deadline in config['deadlines_s']:
        # --- Baselines (no budget) ---
        jobs.append({
            'policy': 'local_only', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })
        jobs.append({
            'policy': 'strong_local', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })
        jobs.append({
            'policy': 'cloud_unlimited', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })

        # --- Budget-controlled policies ---
        for budget in config['request_budgets_per_sec']:
            periodic_interval = 1.0 / budget
            random_prob = budget / avg_msg_rate if avg_msg_rate > 0 else 0.05

            # Periodic: vary offsets
            for i in range(config['num_periodic_offsets']):
                offset = periodic_interval * i / config['num_periodic_offsets']
                jobs.append({
                    'policy': 'periodic', 'budget': budget, 'deadline': deadline,
                    'seed': 0, 'offset': offset,
                    'periodic_interval': periodic_interval, 'random_prob': random_prob
                })

            # Random: vary seeds
            for seed in range(config['num_random_seeds']):
                jobs.append({
                    'policy': 'random', 'budget': budget, 'deadline': deadline,
                    'seed': seed, 'offset': 0.0,
                    'periodic_interval': periodic_interval, 'random_prob': random_prob
                })

            # Suspicion: one run (deterministic given threshold)
            jobs.append({
                'policy': 'suspicion', 'budget': budget, 'deadline': deadline,
                'seed': 0, 'offset': 0.0,
                'periodic_interval': periodic_interval, 'random_prob': random_prob
            })

            # Combined: vary offsets (periodic component varies)
            for i in range(config['num_periodic_offsets']):
                offset = periodic_interval * i / config['num_periodic_offsets']
                jobs.append({
                    'policy': 'combined', 'budget': budget, 'deadline': deadline,
                    'seed': 0, 'offset': offset,
                    'periodic_interval': periodic_interval, 'random_prob': random_prob
                })

    return jobs"""

new_build_jobs = """def build_jobs(config, avg_msg_rate):
    \"\"\"Build the list of (policy, budget, deadline, seed, offset) jobs.\"\"\"
    jobs = []

    for deadline in config['deadlines_s']:
        # --- Baselines (no budget) ---
        jobs.append({
            'policy': 'local_only', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })
        jobs.append({
            'policy': 'strong_local', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })
        jobs.append({
            'policy': 'cloud_unlimited', 'budget': None, 'deadline': deadline,
            'seed': 0, 'offset': 0.0, 'periodic_interval': 0.1, 'random_prob': 0.0
        })

        # --- Budget-controlled policies ---
        for budget in config['request_budgets_per_sec']:
            periodic_interval = 1.0 / budget
            random_prob = budget / avg_msg_rate if avg_msg_rate > 0 else 0.05

            # Suspicion: one run (deterministic given threshold)
            jobs.append({
                'policy': 'suspicion', 'budget': budget, 'deadline': deadline,
                'seed': 0, 'offset': 0.0,
                'periodic_interval': periodic_interval, 'random_prob': random_prob
            })
            
            # Cloud Confirmation: one run (deterministic)
            jobs.append({
                'policy': 'cloud_confirm', 'budget': budget, 'deadline': deadline,
                'seed': 0, 'offset': 0.0,
                'periodic_interval': periodic_interval, 'random_prob': random_prob
            })
            
            # Cloud Confirmation Fallback: one run (deterministic)
            jobs.append({
                'policy': 'cloud_confirm_fallback', 'budget': budget, 'deadline': deadline,
                'seed': 0, 'offset': 0.0,
                'periodic_interval': periodic_interval, 'random_prob': random_prob
            })
            
            # Budgeted Cloud Confirmation: one run (deterministic)
            jobs.append({
                'policy': 'cloud_confirm_budgeted', 'budget': budget, 'deadline': deadline,
                'seed': 0, 'offset': 0.0,
                'periodic_interval': periodic_interval, 'random_prob': random_prob
            })

    return jobs"""

if old_build_jobs.replace("\r\n", "\n") not in content.replace("\r\n", "\n"):
    print("Old build_jobs not found!")
else:
    # Use exact match or simple replacement
    content_normalized = content.replace("\r\n", "\n")
    content_normalized = content_normalized.replace(old_build_jobs.replace("\r\n", "\n"), new_build_jobs)
    with open(r"c:\Users\marya\Downloads\V2C-Sentinel\run_cloud_confirmation_experiment.py", "w", encoding="utf-8") as f:
        f.write(content_normalized)
    print("build_jobs replaced successfully.")
