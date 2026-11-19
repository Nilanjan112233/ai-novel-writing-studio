# NovelForge Phase B Before/After Context Report

| Metric | Phase E | Phase B | Change |
|---|---:|---:|---:|
| Develop Story total prompt | 33,551 | 23,622 | -29.59% |
| Native retrieval evidence | 15,339 | 6,864 | -55.25% |
| Chapter/episode evidence | 8,953 | 8,040 | -10.20% |
| Combined evidence layer | 24,292 | 14,904 | -38.65% |
| Legacy broad workflow | 396,636 | 23,622 | -94.04% |
| Discovery retrieved tokens | 1,486 | 917 | -38.29% |
| Discovery Recall@8 | 1.0 | 1.0 | unchanged |
| Discovery MRR | 1.0 | 1.0 | unchanged |

The largest saving came from compacting Native hit attribution/metadata and replacing verbose Chapter Intelligence retrieval text with bounded episode evidence. No authority section was removed.

Discovery retrieval latency rose from 17.202 ms to 48.700 ms on the real packet because more derived candidates are scored. This is a measured regression and is not hidden; it motivates a later Phase C evaluation.
