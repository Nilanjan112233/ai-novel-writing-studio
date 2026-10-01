# NovelForge Phase D Cost and Latency Analysis

## Develop Story token opportunity

| Metric | Current Phase C | Progressive shadow | Change |
|---|---:|---:|---:|
| Evidence tokens | 13,810 | 3,890 | -9,920 (-71.83%) |
| Total prompt tokens | 22,326 | 12,406 | -9,920 (-44.43%) |

NovelForge's current flat Gemini accounting is $0.0004 per 1,000 total tokens. If output tokens remain equal and no extra provider call occurs, the projected input saving is $0.003968 per five-specialist operation. Against the observed $0.012803 Phase C run, that implies about $0.008835, or 30.99% lower total estimated cost. This is a projection, not a billed matched run.

## Read-only lookup latency

Forty exact-pointer reads on the real Memory Fantasy project measured:

| Lookup | P50 | P95 |
|---|---:|---:|
| Atomic fact | 1.123 ms | 1.546 ms |
| Episode | 0.514 ms | 1.242 ms |
| Approved prose | 0.405 ms | 0.971 ms |

With deterministic routing and the labelled task mix, estimated 500-chapter cold P50 rises from 47.115 to 48.646 ms. A conservative weighted P95 estimate is 63.704 ms versus the measured Phase C 61.175 ms. This is not a material latency regression.

## Sequential model-requested expansion

Literal fact-first behavior would need at least one additional evidence step for 64.29% of corpus tasks and raw depth for 19.05%. If that step requires another provider turn, seconds of model latency dominate the millisecond lookup cost and may erase monetary savings. The audit made no such calls.

## Recommended cost model

- classify role/task before serialization;
- fetch the declared evidence level directly, with pointer reads parallelized where possible;
- reserve model-requested expansion for rare unresolved cases;
- charge and attribute any expansion call separately;
- compare total operation cost, including retries and outputs, not prompt savings alone.

Machine evidence: `artifacts/memory-phase-d/cost-latency.json` and `scale-results.json`.
