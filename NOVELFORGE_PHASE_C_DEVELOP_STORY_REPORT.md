# NovelForge Phase C Develop Story Report

## Matched run

One isolated copy was restored from the same Memory Fantasy benchmark backup. The instruction, five specialists, role manifests, delta handoffs, provider, and model matched Phase B:

- RelationshipAgent;
- CharacterJourneyAgent;
- MysteryAgent;
- ArcArchitectAgent;
- PacingAgent;
- Gemini `gemini-3.1-flash-lite`.

All five calls completed. There were zero provider retries, model fallbacks, or broad-context fallbacks. All five context packets reported complete authority coverage.

## Comparison

| Metric | Phase B | Phase C | Change |
|---|---:|---:|---:|
| Prompt tokens | 23,622 | 22,326 | -5.49% |
| Response tokens | 3,472 | 4,033 | +16.16% |
| Evidence tokens | 14,904 | 13,810 | -7.34% |
| Estimated provider cost | $0.010837 | $0.012803 | +18.14% |
| Wall latency | 56.676 s | 47.817 s | -15.63% |
| Retries | 0 | 0 | unchanged |
| Model/broad fallbacks | 0 | 0 | unchanged |

The cost increase is caused by longer stochastic responses, not prompt growth. Phase C reduced prompt/evidence tokens but this single real run is not evidence of lower total bill. That regression is retained explicitly.

## Per-specialist prompt attribution

| Specialist | Final prompt | Native retrieval | Episode memory | Authority complete |
|---|---:|---:|---:|---|
| Relationship | 3,884 | 1,000 | 1,619 | yes |
| Character Journey | 4,283 | 999 | 1,619 | yes |
| Mystery | 4,129 | 999 | 1,619 | yes |
| Arc Architect | 5,142 | 1,360 | 1,619 | yes |
| Pacing | 4,888 | 1,357 | 1,619 | yes |

All packets used the Phase C ranking strategy. Every output retained Mara, Elias, and the Chapter 10 boundary; Northglass appeared where role-relevant. Structured specialist payloads remained non-generic and same-cycle handoffs completed. No confirmed authority disappeared, and no candidate relationship was promoted.

The failed harness setup before this run made zero provider calls and was removed as an exact temporary restored project. The successful benchmark copy remains available as project `6a7e31d7fed9b9eec7b6791f`; its original source and backup were unchanged.

Machine evidence: `artifacts/memory-phase-c/phase-c-provider-run.json`.
