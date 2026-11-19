# Develop Story Cost Reduction Report

## Aggregate result

| Metric | Legacy broad | Phase E compact |
|---|---:|---:|
| Prompt tokens | 396,636 | 33,551 |
| Prompt reduction | — | **91.54%** |
| Response tokens | 3,792 matched replay | 4,267 real |
| Cost on matched Gemini pricing | $0.160171 projected | $0.015127 actual |
| Cost reduction | — | **90.56%** |
| Full workflow provider status | failed after one specialist | completed all five |
| Full workflow latency | unavailable; run failed | 145.141 s |
| Provider retries | failure occurred after provider retry | 3 transient retries, recovered |
| Model fallback | none | none |

The raw replay artifact's generic replay-provider cost field is not a provider bill and must not be used. The normalized legacy estimate applies the same Gemini model pricing to the measured legacy input and matched response size.

## Actual legacy failure cost

The latest broad real-provider attempt spent an estimated **$0.062251** and **31.49 seconds** while completing only Relationship. Character Journey then failed after a 503/429 sequence. An earlier OpenRouter attempt also failed to complete the broad workflow. These are recorded failures, not passed benchmarks.

## Current real-provider operation

The corrected compact system completed five calls:

| Specialist | Prompt | Response | Wall latency |
|---|---:|---:|---:|
| Relationship | 4,620 | 473 | 22.795 s |
| Character Journey | 5,852 | 1,253 | 13.342 s |
| Mystery | 5,849 | 820 | 71.027 s |
| Arc Architect | 8,542 | 1,073 | 32.317 s |
| Pacing | 8,688 | 648 | 4.584 s |

Mystery absorbed two transient 503 retries; Relationship absorbed one. There was no model fallback and all calls completed.

## Largest savings

1. Full Story Bible delivery: 340,190 tokens became 1,338 role-projection tokens.
2. Native retrieval: 31,908 became 15,339 through role limits and deduplication.
3. Chapter memory: 16,220 became 8,953 through role inclusion and bounded recent evidence.
4. Core/important/recent agent-memory duplication: 75 became 5 workflow-only tokens.

## Cost conclusion

Yes, the optimized system is cheaper in real provider cost. The measured compact workflow cost less than one quarter of the amount already spent by the failed broad attempt, and its normalized complete-workflow estimate is 90.56% lower.
