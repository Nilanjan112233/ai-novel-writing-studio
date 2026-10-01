# Phase D Real Provider Cost Comparison

## Operation totals

All arms used five successful Gemini `gemini-3.1-flash-lite` calls with no retries or fallbacks.

| Metric | Current Phase C | Fact only | Progressive |
| --- | ---: | ---: | ---: |
| Prompt tokens | 22,729 | 9,962 | 14,225 |
| Response tokens | 3,288 | 3,211 | 3,644 |
| Total tokens | 26,017 | 13,173 | 17,869 |
| Normalized estimated cost | $0.010407 | $0.005269 | $0.007147 |
| Gateway-recorded operation cost | $0.012696 | $0.005892 | $0.008113 |
| Wall latency | 34.514 s | 52.791 s | 29.494 s |

Progressive reduced prompt tokens 37.41%. Responses grew 10.83%, but total tokens still fell 31.32%. The increase in response length therefore did not erase the cost benefit.

Using the gateway's recorded operation cost, progressive saved $0.004583 on this bounded cycle, or 36.10%. The normalized attribution estimate reports a 31.33% reduction. Both accounting views agree on direction and on material savings.

## Evidence composition

| Evidence source | Current | Fact only | Progressive |
| --- | ---: | ---: | ---: |
| Atomic/Native facts | 6,060 | 1,000 | 1,272 |
| Episode evidence | 8,095 | 0 meaningful | 3,221 |
| Raw evidence | 0 | 0 | 0 |
| Serialized evidence total | 14,155 | 1,010 | 4,498 |

The serializer estimates one token for an empty section; this accounts for the small difference between meaningful and serialized fact-only/progressive totals. No raw prose was loaded in the matched five-specialist workflow.

## Per-role progressive prompt

| Role | Current prompt | Progressive prompt | Reduction |
| --- | ---: | ---: | ---: |
| Relationship | 3,871 | 2,303 | 40.51% |
| Character Journey | 4,233 | 2,767 | 34.63% |
| Mystery | 4,099 | 2,575 | 37.18% |
| Arc Architect | 5,115 | 3,401 | 33.51% |
| Pacing | 5,411 | 3,179 | 41.25% |

## Latency caution

Progressive happened to finish 14.55% faster; fact-only was slower despite having the smallest prompts. With one matched sample, provider latency variance dominates. This pilot proves no obvious latency regression, not a stable latency improvement.

## Cost conclusion

The cost gate passed. Production is still not recommended because the blind quality gate failed.

