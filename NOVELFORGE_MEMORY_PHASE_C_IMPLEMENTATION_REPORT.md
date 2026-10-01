# NovelForge Memory Phase C Implementation Report

## Decision and scope

Phase C is implemented as a derived, project-scoped lexical candidate index followed by weighted lexical, existing hash-vector, and story-metadata ranking. Phase D was not started. Atomic/episode derivation, Story Bible, Narrative Intelligence, MongoDB ownership, and all authority rules remain unchanged.

The bake-off selected the simplest winning path:

```text
query
  -> Phase A/Phase C checkpoint readiness
  -> project + active + story-domain narrowing
  -> rare indexed query-term candidate generation
  -> P0 eligibility, chronology, branch, and knowledge filtering
  -> BM25 + existing hash + story-metadata weighted score
  -> logical/version/content deduplication
  -> top-k and attributed context
```

The production weights are the measured bake-off winner: lexical `0.48`, hash `0.30`, metadata `0.22`. Authority is not a ranking feature; it remains a hard eligibility boundary and the existing authority-priority tie-break.

## Implementation

- `memory_phase_c_ranker.py` provides tokenization, per-record lexical fields, BM25, metadata features, graph evaluation helpers, and replay fusion helpers.
- `memory_phase_c_service.py` owns readiness, bounded candidate generation, checkpointing, failure fallback, and a revision-keyed bounded candidate cache.
- `memory_retrieval_service.py` stores lexical fields in the existing `memory_embeddings` projection, filters through P0 before ranking, ranks only eligible candidates, and preserves the complete Phase B fallback.
- `memory_incremental_index_service.py` validates Phase C completion after rebuild, advances its processed watermark after bounded owner events, and exposes Phase C status in existing developer diagnostics.
- `memory_phase_c.py` adds one compound multikey lexical index and one project checkpoint index.
- backup excludes the derived Phase C checkpoint; lifecycle ownership includes it. Restores therefore remain authority-first and rebuildable.

No external search service, graph database, embedding provider, paid search call, or Tencent dependency was added.

## Compatibility and failure behavior

Old projects without a Phase C checkpoint use the complete Phase B path. A rebuild backfills lexical fields and marks Phase C `READY` only when active record counts and ranker versions match. Missing, failed, partial, or version-mismatched Phase C state records a fallback reason and uses Phase B. The focused corruption test returned the labelled fact through Phase B with no authority mutation.

Incremental updates write lexical fields in the same deterministic memory upsert. Candidate-cache keys include project, processed revision, and normalized query; owner events, rebuilds, and failures invalidate the project entries. Duplicate event and logical identity behavior remains owned by Phase A/P0.

## Measured outcome

At 500 chapters / 2,522 indexed records:

| Metric | Phase B | Phase C |
|---|---:|---:|
| Recall@8 | 0.8333 | 1.0000 |
| MRR | 0.6905 | 0.8111 |
| P50 | 492.301 ms | 47.115 ms cold / 7.727 ms warm |
| P95 | 621.363 ms | 61.175 ms cold / 8.812 ms warm |
| Records scored/query | effectively complete eligible corpus | 1.93 mean |
| Safety leakage | 0 | 0 |
| Duplicate logical hits | 0 | 0 |

All acceptance gates passed. The small-scale synthetic MRR is lower than the old Phase B small-corpus score, but Recall@8 is 1.0 at every scale, the real Discovery replay remains 1.0/1.0, and the required 250/500 MRR improves materially.

## Explicitly not implemented

No progressive retrieval, new atomic/episode design, semantic production model, BM25 service, RRF production path, graph persistence, preference memory, new agent, Tencent writing path, destructive cleanup, or Story Studio redesign was introduced.
