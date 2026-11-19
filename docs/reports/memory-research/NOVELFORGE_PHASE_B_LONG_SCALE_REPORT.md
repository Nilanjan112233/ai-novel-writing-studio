# NovelForge Phase B Long-Scale Report

Provider-free controlled corpora were run at 10, 25, 50, 100, 250, and 500 chapters.

| Chapters | Atomics | Episodes | Atomic/chapter | Recall@8 | MRR | P50 ms | P95 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 50 | 10 | 5.00 | 1.0000 | 1.0000 | 5.175 | 6.233 |
| 25 | 110 | 25 | 4.40 | 1.0000 | 0.9167 | 17.588 | 20.509 |
| 50 | 210 | 50 | 4.20 | 1.0000 | 0.8056 | 18.578 | 20.868 |
| 100 | 410 | 100 | 4.10 | 0.8333 | 0.7500 | 39.510 | 56.668 |
| 250 | 1,010 | 250 | 4.04 | 0.8333 | 0.6944 | 98.725 | 140.512 |
| 500 | 2,010 | 500 | 4.02 | 0.8333 | 0.6905 | 492.301 | 621.363 |

Duplicate logical hits, future leakage, and POV knowledge leakage were zero at every scale. The 500-chapter Recall@8 remains equal to the Phase A 0.8333 baseline; Phase B does not claim ranking improvement.

Storage (atomic plus episode BSON) was approximately 0.65 MB at 100 chapters, 1.62 MB at 250, and 3.23 MB at 500. Episode storage averaged about 1.31 KB/chapter.

The P95 increase at 250/500 chapters is the primary remaining bottleneck. Phase B makes units smaller but increases candidate count; the current linear hash-vector scoring path does not scale efficiently enough.
