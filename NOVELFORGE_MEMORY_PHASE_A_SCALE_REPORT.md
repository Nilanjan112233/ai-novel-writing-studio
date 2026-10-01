# NovelForge Memory Phase A Scale Report

All measurements are provider-free and use actual Mongo owner collections, rebuild, checkpoint verification, and Native ranking. The temporary database was removed.

| Chapters | Owner/index rows | Recall@8 | MRR | Retrieval P50 | Retrieval P95 | Rebuild |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 66 / 65 | 1.0000 | 0.9167 | 1.26 ms | 2.48 ms | 404.02 ms |
| 25 | 141 / 140 | 1.0000 | 0.8056 | 2.76 ms | 4.77 ms | 756.32 ms |
| 50 | 266 / 265 | 1.0000 | 0.8056 | 6.50 ms | 7.48 ms | 1,551.86 ms |
| 100 | 516 / 515 | 1.0000 | 0.7833 | 13.18 ms | 14.87 ms | 4,035.53 ms |
| 250 | 1,266 / 1,265 | 0.8333 | 0.7500 | 31.77 ms | 39.92 ms | 14,021.30 ms |
| 500 | 2,516 / 2,515 | 0.8333 | 0.7500 | 67.75 ms | 80.13 ms | 48,003.50 ms |

Every scale had zero candidate/rejected leakage, future leakage, POV knowledge leakage, and duplicate logical hits. Every READY retrieval reported zero owner scans and zero index writes. The P0 500-chapter Recall@8 of 0.8333 is preserved. Synthetic MRR is lower than P0's 0.8333 because the Phase A corpus is rebuilt from real owners rather than pre-seeded embeddings; the required real Discovery case remains MRR 1.0 before and after.

At 500 chapters, cold cache-fill retrieval was 103.72 ms. Warm P95 is 28.0% below the P0 111.33 ms complete-scan baseline. This is a read-path/cache improvement, not a relevance redesign.

Machine-readable evidence: `artifacts/memory-phase-a/phase-a-benchmark.json`.

