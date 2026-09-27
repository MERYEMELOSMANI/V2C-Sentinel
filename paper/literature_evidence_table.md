# Literature Evidence Table

## Research Question
Under limited cloud requests and variable communication delays, how do periodic,
random, suspicion-based, and combined selection compare in timely CAN masquerade
detection?

## Evidence Table

| # | Paper | What it studied | Data | Comparison methods | Timing considered? | Difference from our study |
|---|---|---|---|---|---|---|
| 1 | Verma, Bridges et al., "ROAD: A Real ORNL Automotive Dynamometer CAN Intrusion Dataset," *PLOS ONE*, Jan 2024 | Benchmark dataset of real & simulated CAN attacks including masquerade; signal-level extraction | ROAD dataset (same as ours) | Provides baselines: frequency-based, payload-based | No — purely offline detection accuracy | We use ROAD's signal extractions but evaluate **timeliness** under communication constraints, not offline accuracy. ROAD defines the attacks; we study the detection *delivery* problem. |
| 2 | Hanselmann, Strauss et al., "CANShield: Signal-Based Intrusion Detection for Controller Area Networks," arXiv:2205.13506 | Deep autoencoder ensemble for signal-level CAN anomaly detection | ROAD (+ others) | Multiple autoencoder architectures, compared to prior CAN IDS | No — batch evaluation | CANShield evaluates detection accuracy on stored recordings. We study whether a lightweight local detector can benefit from selectively querying a stronger remote detector under real-time deadline constraints. |
| 3 | Lo, Peng et al., "Graph-Based Intrusion Detection for CAN Bus," arXiv (2023–2024) | Message Sequence Graphs + shallow embeddings for masquerade detection | ROAD | Graph ML vs. traditional ML (RF, SVM, LSTM) | No — offline F1/AUC | Our study does not propose a new detection architecture. We fix two existing classifiers and study the **selection/scheduling** problem of when to consult the stronger one. |
| 4 | Cloud/MEC IDS offloading literature (survey-level: multiple 2022–2024 works) | Hybrid local+edge architectures for vehicle IDS; DRL-based offloading decisions | Synthetic or simulation-based (SUMO, ns-3) | DRL vs. heuristic scheduling; latency-throughput tradeoffs | Yes — latency modeled analytically or via network simulators | These works model offloading at the system/optimization level with simulated delays. We use **recorded 5G delays** from the CICV5G dataset and evaluate detection **episode-level timeliness** on real attack recordings, not throughput-optimal scheduling. |
| 5 | Zhu, Xu et al., "5G Communication Delay Dataset for Cloud-Based Vehicle Planning and Control (CICV5G)," *Scientific Data* / arXiv:2504.08255 | Real 5G V2N2V delay measurements across urban/arterial/rural driving | CICV5G dataset (same as ours) | Delay modeling, prediction accuracy | Yes — delay characterization | CICV5G provides the delay traces we replay. That paper characterizes delay distributions; we use them to simulate the communication channel in a CAN IDS context. |
| 6 | General CAN IDS with IF/RF (multiple works: Ashraf et al., Zhang et al., 2022–2024) | Isolation Forest and/or Random Forest for CAN anomaly and masquerade detection | Various (ROAD, Car Hacking, SynCAN) | IF vs. RF vs. DNN | No — offline metrics | These works compare classifier accuracy. We fix the classifiers and study how to schedule limited cloud queries of the stronger one, measuring timeliness and false-alert burden under real network conditions. |

## Key Observations

1. **No reviewed work** compares request-selection policies (periodic, random, suspicion-based, combined) for cloud-assisted CAN IDS under recorded 5G delays with episode-level timeliness metrics.
2. **Cloud/MEC IDS papers** consider offloading optimization but use simulated network conditions and focus on throughput/latency tradeoffs, not on whether a specific attack episode is detected before a safety deadline.
3. **CAN IDS papers** evaluate detection accuracy offline; none simulate the effect of communication delays on detection timeliness.
4. **CICV5G** is used for vehicle planning/control delay analysis; we repurpose it for IDS communication simulation, which is a novel application of this dataset.

## Provisional Contribution Paragraph

> Existing CAN intrusion detection research evaluates detector accuracy on stored
> recordings without considering the communication cost and timing of consulting a
> remote detector. Cloud and edge offloading studies model scheduling optimization
> with simulated delays but do not evaluate whether specific attack episodes are
> detected within safety-relevant deadlines. We bridge this gap by replaying CAN
> masquerade attacks from the ROAD dataset through a two-tier detection architecture
> where the vehicle selects which messages to send to a cloud detector, using
> recorded 5G delays from the CICV5G dataset as the communication channel. We
> compare four request-selection policies — periodic, random, suspicion-based, and
> combined — under shared request budgets and multiple deadlines, measuring
> episode-level timely detection, detection delay, and false-alert burden per normal
> driving hour. To our knowledge, this is the first study to evaluate request-
> selection policies for cloud-assisted CAN IDS using recorded network delays and
> episode-level timeliness metrics on physically verified masquerade attacks.

**Note:** The claim "first study" is supported by the absence of such a combination
in the reviewed works. If a closer match is discovered during further review, this
should be narrowed to "among the first" or the specific differentiating factor
should be stated.
