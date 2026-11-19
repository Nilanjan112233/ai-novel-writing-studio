# NovelForge Memory Before/After Benchmark

## Primary table

| Metric | Before | After |
| --- | ---: | ---: |
| Duplicate logical hits | 1 | 0 |
| Discovery context tokens | 5,428 | 3,884 |
| Duplicate context tokens | 1,344 | 0 |
| Candidate leakage (labelled query) | 1 | 0 |
| Rejected leakage (labelled query) | 1 | 0 |
| Future knowledge leakage (labelled query) | 1 | 0 |
| Chronology cases passed | 0/2 | 2/2 |
| Character knowledge cases passed | 0/1 | 1/1 |
| POV contradiction detection | no | yes |
| Relationship contradiction detection | no | yes |
| Real-packet Recall@k | 1.0000 | 1.0000 |
| Real-packet MRR | 1.0000 | 1.0000 |
| Scale-corpus retrieval P50 | 9.586 ms | 16.972 ms |
| Scale-corpus retrieval P95 | 37.575 ms | 102.151 ms |
| 10 chapter result | R@8 0.8333; 5 unsafe hits | PASS; R@8 1.0000; 0 unsafe |
| 25 chapter result | R@8 0.8333; 5 unsafe hits | PASS; R@8 1.0000; 0 unsafe |
| 50 chapter result | R@8 0.8333; 5 unsafe hits | PASS; R@8 1.0000; 0 unsafe |
| 100 chapter result | R@8 0.8333; 4 unsafe hits | PASS; R@8 1.0000; 0 unsafe |
| 250 chapter result | R@8 0.5000; incomplete | PASS; R@8 0.8333; 0 unsafe |
| 500 chapter result | R@8 0.0000; incomplete | PASS; R@8 0.8333; 0 unsafe |

“Unsafe hits” is the scale artifact's candidate/rejected/stale count across eight queries; future and character-knowledge leakage are reported separately in the JSON. The primary candidate/rejected rows use the dedicated Elias-villain query, where legacy selection includes both `candidate-villain` and `rejected-villain` and current safe retrieval includes neither.

## Discovery result

The untouched baseline packet is 5,428 estimated tokens. With the target chapter interpreted correctly as an `as_of_chapter=1` boundary, the replayed packet is 3,884 tokens: a 28.4% reduction. Important terms Elias, Mara, and Northglass remain found; Recall@k and MRR stay at 1.0.

At `as_of_chapter=2`, which intentionally permits Chapter 2 material, the packet is 4,679 tokens. That result is retained to show why caller-provided chronology boundaries matter.

## Regressions disclosed

Latency rises because retrieval now scans all active embeddings rather than silently stopping at 2,000. At 500 chapters, P95 changes from 40.35 ms for an incomplete scan to 111.33 ms for a complete scan. This is acceptable for P0 correctness but should be addressed by Phase A incremental/event-driven indexing and bounded candidate generation, not by restoring silent truncation.

The scale ranker still misses one of six labelled relevant items at 250 and 500 chapters. This is a relevance limitation, not a correctness leak, and is evidence for later rank-fusion work.

No paid model was used, so this benchmark does not claim a literary-quality delta.

