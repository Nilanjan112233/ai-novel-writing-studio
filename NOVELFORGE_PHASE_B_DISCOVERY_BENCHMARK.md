# NovelForge Phase B Discovery Benchmark

The real Memory Fantasy Chapter 2 replay used the same query, Chapter 1 boundary, Mara POV, top-k 8, and expected terms.

| Metric | Before | Phase B |
|---|---:|---:|
| Retrieved tokens | 1,486 | 917 |
| Reduction | - | 38.29% |
| Recall@8 | 1.0 | 1.0 |
| MRR | 1.0 | 1.0 |
| Duplicate logical hits | 0 | 0 |
| Candidate/rejected/stale leakage | 0 | 0 |
| Future leakage | 0 | 0 |
| POV knowledge leakage | 0 | 0 |
| Latency | 17.202 ms | 48.700 ms |

The packet became smaller without losing Elias, Mara, or Northglass. The latency regression is attributable to the additional compact candidates in the current scan-based/hash-vector retrieval path.
