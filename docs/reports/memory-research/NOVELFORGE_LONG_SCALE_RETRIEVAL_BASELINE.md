# NovelForge Long-Scale Retrieval Baseline

## Corpus

The provider-free scale runner seeds 10, 25, 50, 100, 250, and 500 chapter fixtures with five ordinary derived records per chapter plus labelled state transitions and traps: rare Asterlock artifacts, paraphrased river memory, relationship changes, Northglass ownership, injury/healing, mystery state, rejected villain brainstorming, candidate projections, revised duplicate intelligence, future knowledge, character-private knowledge, and a dormant Chapter 1 callback.

| Chapters | Seeded records | Legacy Recall@8 | Current Recall@8 | Legacy P95 | Current P95 | Current safety |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 10 | 65 | 0.8333 | 1.0000 | 2.49 ms | 3.62 ms | PASS |
| 25 | 140 | 0.8333 | 1.0000 | 4.09 ms | 6.57 ms | PASS |
| 50 | 265 | 0.8333 | 1.0000 | 7.33 ms | 10.91 ms | PASS |
| 100 | 515 | 0.8333 | 1.0000 | 10.54 ms | 18.95 ms | PASS |
| 250 | 1,265 | 0.5000 | 0.8333 | 25.24 ms | 47.10 ms | PASS |
| 500 | 2,515 | 0.0000 | 0.8333 | 40.35 ms | 111.33 ms | PASS |

PASS means zero selected candidate/rejected/stale, future-boundary, POV-knowledge, and duplicate-logical hits. It does not mean perfect relevance.

## 2,000 and 1,000 limits

The old retrieval path materialized only the first 2,000 active embeddings. In the 500-chapter fixture, labelled late and dormant sources fall outside that prefix and aggregate Recall@8 reaches 0.0. The old per-source refresh path similarly materialized only 1,000 owners. A focused test now indexes 1,005 plot-thread owners and retrieves a rare record inserted after 2,004 fillers.

Both silent caps are removed. Mongo cursors are streamed through the complete matching set. The cost is visible linear scan growth.

## Interpretation

At 100 chapters, P95 remains under 20 ms in this local synthetic run. At 500 chapters, complete full-scan retrieval is still interactive but is roughly 2.8 times the legacy incomplete P95. The ranker recovers five of six labelled facts at 250 and 500 chapters; it is not yet robust enough for perfect dormant/paraphrased recall.

The next phase should not reintroduce a cap. It should make indexing incremental and introduce indexed candidate generation with an explicit completeness signal. BM25/semantic/RRF is still deferred until that measurement foundation is retained.

Full per-query data is in `artifacts/memory-p0/long-scale-before-after.json`.

