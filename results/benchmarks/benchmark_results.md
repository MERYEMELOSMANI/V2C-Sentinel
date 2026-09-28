# Model Benchmark Results (Development Machine)

**Machine:** Development laptop (not a constrained CAN gateway)
**Date:** 2026-09-27

## Results

| Metric | Local (Logistic Regression) | Cloud (Random Forest, 50 trees) |
|---|---|---|
| Batch inference (937,278 msgs) | 0.199 sec (0.21 μs/msg) | 0.732 sec (0.78 μs/msg) |
| Single-message latency | 220.5 μs | 16,004 μs (~16 ms) |

## Notes
- The single-message latency for the RF (16 ms) is significant: it exceeds our
  assumed `cloud_proc_time` of 10 ms in the simulation. This means the simulation
  is slightly optimistic about cloud processing time.
- On a constrained ARM gateway (typical CAN gateway), these times could be
  10-100× slower. The LR model (220 μs single) would likely still be feasible
  at CAN message rates (~1 msg/ms), but the RF model (16 ms single) would
  require hardware acceleration or batching.
- Batch inference is orders of magnitude faster than single-message due to
  vectorization. A real-time system processes one message at a time.

## Model Sizes
| Model | File size |
|---|---|
| local_lr.joblib (LR) | 1,055 bytes |
| cloud_rf.joblib (RF) | 52,953 bytes |
| scaler.joblib | 1,759 bytes |

## Implications for V2C Claim
The 73× single-message latency difference between LR and RF provides the
computational motivation for cloud offloading: even if the RF could run locally,
it would consume significantly more compute per message on a constrained gateway.
