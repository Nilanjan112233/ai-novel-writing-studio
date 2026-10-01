# NovelForge Memory Phase A Benchmark

## Required comparison

| Metric | P0 | Phase A |
|---|---:|---:|
| 500-chapter Recall@8 | 0.8333 | 0.8333 |
| 500-chapter retrieval P50 | 91.84 ms | 67.75 ms |
| 500-chapter retrieval P95 | 111.33 ms | 80.13 ms |
| Safety leakage | 0 | 0 |
| Duplicate logical hits | 0 | 0 |
| Full source scans/query | 37 owner scans during refresh | 0 when READY |
| Owner records inspected/query | all indexed owners during refresh | 0 when READY |
| Index writes/query | upsert attempt per materialized owner | 0 when READY |
| Index writes/single mutation | not isolated | 1 (0 if unchanged) |
| Index update P50/P95 | mixed into request | 36.49 / 38.52 ms |
| Rebuild duration 100 chapters | not separated | 4,035.53 ms |
| Rebuild duration 500 chapters | not separated | 48,003.50 ms |
| Recovery after interrupted rebuild | absent | PASS |
| Checkpoint mismatch detection | absent | PASS |

Checkpoint verification itself measured P50/P95 3.67/5.17 ms at 500 chapters. Mutation work was constant in records inspected: one owner for chapter 501 approval, relationship change, planning confirmation, candidate rejection, artifact ownership, approved-chapter revision, and intelligence regeneration. The unchanged regeneration wrote zero rows.

The real Memory Fantasy Discovery replay retained Recall@k 1.0, MRR 1.0, zero leaks, and zero logical duplicates. Its retrieved tokens changed from 1,486 to 2,365 after rebuilding from current owners; this increase is reported, not hidden. It reflects drift between the old P0 embedding snapshot and current owner-derived materialization, and is not a Phase A packet optimization target.

No provider calls were made. Evidence is in `artifacts/memory-phase-a/phase-a-benchmark.json` and `memory-fantasy-phase-a-comparison.json`.
