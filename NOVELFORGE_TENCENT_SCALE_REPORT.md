# Tencent 25/50/100-Chapter Synthetic Scale Report

Synthetic records were indexed through the existing Native memory adapter and the Tencent adapter, with temporary Native benchmark records removed after each run. No paid generation was used.

| Stored records | Native mean latency | Tencent mean latency | Native mean tokens | Tencent mean tokens | Tencent hits/query |
|---:|---:|---:|---:|---:|---:|
| 25 | 2.3 ms | 458.7 ms | 166 | 278 | 5 |
| 50 | 3.3 ms | 484.7 ms | 166 | 95 | 2 |
| 100 | 7.0 ms | 481.0 ms | 168 | 96 | 2 |

The lower Tencent token estimate at 50/100 records is not compression success: the FTS/L0 search returned fewer matching records. Recall degraded from five hits to two for the exact labeled queries while Native remained at five. This local keyword-only path therefore has a scale/relevance problem, not a long-horizon efficiency advantage.

