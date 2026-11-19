# NovelForge Phase C Discovery Report

The real Memory Fantasy Chapter 2 replay used the same project state, query, Chapter 1 boundary, Mara POV, top-k 8, and expected Elias/Mara/Northglass labels as Phase B. It was provider-free.

| Metric | Phase B | Phase C |
|---|---:|---:|
| Retrieved evidence tokens | 917 | 316 |
| Recall@8 | 1.0000 | 1.0000 |
| MRR | 1.0000 | 1.0000 |
| Latency | 48.700 ms | 27.209 ms |
| Records scored | 142 | 7 |
| Duplicate logical hits | 0 | 0 |
| Candidate/rejected/stale leakage | 0 | 0 |
| Future leakage | 0 | 0 |
| POV knowledge leakage | 0 | 0 |

The packet still contains every labelled important entity. The 601-token reduction is relevance selection, not Phase D progressive retrieval: Phase C simply ranks a bounded candidate set and the existing Phase B compact representations enter context normally.

Diagnostics identify `metadata_lexical_hash_weighted`, 142 project records, 25 raw lexical candidates, 7 P0-eligible scored records, discriminative terms `disappearance` and `ivo`, no fallback, and complete matching coverage for those terms.

Discovery is therefore non-inferior on the required real small-project case and faster/smaller in this replay. Evidence is in `artifacts/memory-phase-c/discovery-phase-c.json`.
