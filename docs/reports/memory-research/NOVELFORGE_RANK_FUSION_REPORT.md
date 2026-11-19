# NovelForge Rank Fusion Report

## Compared approaches

The bake-off compared single-path lexical/hash/metadata scores, weighted score fusion, full reciprocal-rank fusion, graph-augmented weighted fusion, and lexical/semantic/metadata RRF.

At 500 chapters:

| Fusion | Recall@8 | MRR | Records scored |
|---|---:|---:|---:|
| Weighted lexical + metadata + hash | 1.0000 | **0.8452** | **1.93** |
| Full lexical/hash/metadata RRF | 1.0000 | 0.7381 | 2,187.13 |
| Weighted winner + graph | 1.0000 | 0.8452 | 1.93 |
| Lexical/semantic/metadata RRF | 1.0000 | 0.7500 | 2,187.13 |

## Selection

Weighted fusion won. It is staged: Mongo lexical/story-domain narrowing first, P0 filtering second, then three explainable scores over the bounded set. This is materially cheaper than fusing complete rankings.

Production attribution reports `metadata_lexical_hash_weighted` and each score component. Authority is deliberately absent from the weighted formula; authority and validity are hard gates, with the existing authority priority used only when choosing among equivalent logical representations.

RRF remains in replay helpers for future evaluation but is not the production ranker.
