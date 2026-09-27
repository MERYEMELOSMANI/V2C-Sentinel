# V2C-Sentinel: Deadline-Aware Cloud Assistance for CAN Masquerade Detection

## Abstract
(To be written after results are finalized)

## 1. Introduction

### Motivation
- CAN bus is vulnerable to masquerade attacks (spoofed messages mimicking legitimate traffic)
- Lightweight on-vehicle detectors may lack accuracy; stronger cloud/edge detectors incur communication delay
- Key tension: when should a constrained vehicle request a remote second opinion?

### Research Question
Under limited cloud requests and variable communication delays, how do periodic,
random, suspicion-based, and combined selection policies compare in timely CAN
masquerade detection?

### Contributions
(See paper/literature_evidence_table.md for provisional paragraph)

## 2. Related Work

### 2.1 CAN Intrusion Detection
- ROAD dataset [Verma et al., 2024]: benchmark for masquerade attacks
- CANShield [Hanselmann et al., 2022]: signal-level deep autoencoder detection
- Graph-based approaches [Lo et al., 2024]: MSG embeddings for masquerade detection
- IF/RF classifiers: common baselines for CAN anomaly detection

### 2.2 Cloud/Edge-Assisted Vehicle Security
- Hybrid local+edge architectures: lightweight local, complex remote
- DRL-based offloading: optimized scheduling under latency constraints
- *Difference from our work:* existing approaches use simulated delays and optimize
  throughput; we use recorded delays and measure episode-level timeliness

### 2.3 5G Communication for Connected Vehicles
- CICV5G dataset [Zhu et al., 2025]: real 5G V2N2V delay measurements
- We repurpose these traces for IDS communication simulation

## 3. System Design

### 3.1 Architecture
- Vehicle processes each CAN message through local detector (LR)
- Request-selection policy decides whether to query cloud detector (RF)
- Cloud response arrives after real 5G delay (from CICV5G trace)
- Decision engine: cloud reply overrides local if timely; local fallback at deadline

### 3.2 Request-Selection Policies
1. **Periodic:** Query cloud on fixed time grid
2. **Random:** Query with fixed probability per message
3. **Suspicion:** Query when local score exceeds threshold
4. **Combined:** Query when suspicious OR periodic grid fires

### 3.3 Budget Mechanism
- Token bucket rate limiter shared across all policies
- Ensures fair comparison at equal communication cost

### 3.4 Deadline and Fallback
- Configurable deadline (100-300ms); primary: 150ms
- If cloud reply is late and local predicts attack → local fallback warning at deadline
- If cloud reply is late and local predicts normal → no warning until cloud returns (late diagnostic)

## 4. Experimental Setup

### 4.1 Datasets
- **CAN recordings:** ROAD dataset, correlated signal masquerade attacks
- **Network delays:** CICV5G, Urban road n78 traces
- **Splits:** Train (attack_01, normal_01), Dev (attack_02, normal_02), Test (attack_03, normal_03)

### 4.2 Detectors
- **Local:** Logistic Regression (sklearn, threshold at dev 90th percentile)
- **Cloud:** Random Forest (50 trees, max_depth=15)
- Both trained on train split only

### 4.3 Baselines
- Local-only: No cloud requests
- Strong-local: RF running locally (upper bound)
- Cloud-unlimited: Every message sent to cloud

### 4.4 Parameters
- Deadlines: 100, 150, 200, 300 ms
- Request budgets: 1, 5, 10, 50 req/s
- Random seeds: 0-9; Periodic offsets: 10 per interval
- See paper/evaluation_protocol.md for complete specification

### 4.5 Metrics
- Timely detection rate (per attack episode)
- Mean detection delay
- Grouped false alerts per normal driving hour
- Actual request rate
- Late reply percentage

## 5. Results

### 5.1 Development Machine Benchmark
(See results/final/benchmark_results.md)

### 5.2 Main Comparison
(To be filled from results/final/summary.csv)

### 5.3 Deadline Sensitivity
(Results at 100, 150, 200, 300 ms)

### 5.4 Budget Analysis
(Results across 1, 5, 10, 50 req/s)

## 6. Discussion

### Q1: Does cloud assistance improve over local-only?
### Q2: Could the stronger detector simply run locally?
### Q3: Does combined selection beat simpler policies?
### Q4: Do improvements persist across recordings?
### Q5: What is the cost in false alerts and communication?

### Limitations
- Only 3 attack recordings (same attack type, same vehicle)
- Network delays not synchronized with CAN recordings
- Processing times are assumed constants, not measured on target hardware
- Test split was previously inspected (disclosed)

## 7. Conclusion
(To be written after results)

## References
1. Verma et al., "ROAD Dataset," PLOS ONE, 2024
2. Hanselmann et al., "CANShield," arXiv:2205.13506, 2022
3. Zhu et al., "CICV5G," Scientific Data, 2025
4. (Additional references as needed)
