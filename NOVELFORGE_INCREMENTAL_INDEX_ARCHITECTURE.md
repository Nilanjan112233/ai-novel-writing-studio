# NovelForge Incremental Index Architecture

## Boundary

Mongo owner records remain authoritative. `memory_index_events`, `memory_index_checkpoints`, `memory_index_staging`, `memory_embeddings`, and the in-process cache are derived and disposable. Tencent is not involved.

## Previous runtime flow

Before Phase A, the public memory search and Native provider defaulted `refresh_index=True`. Context Engine therefore caused `index_project_memory` to scan the project plus every indexed owner collection before retrieval. Narrative Studio also performed a full refresh before a run, after every specialist, and after the run. Chapter Intelligence separately wrote its embedding. Refresh recreated/upserted all materializations and performed stale/alias cleanup. Retrieval then scanned every active embedding. This mixed index maintenance with request latency.

## Phase A flow

```text
owner transaction
  -> existing durable project event / Chapter Intelligence hook
  -> idempotent memory_index_event
  -> checkpoint authority_state_version advances
  -> affected owner is resolved in its current state
  -> deterministic logical upsert or invalidation
  -> processed_version advances

retrieval
  -> read checkpoint/status
  -> apply at most 32 known pending events
  -> READY: query existing complete index
  -> not READY + strict writing: scan current authority owners, write nothing
```

`index_memory` uses project + source type + logical source ID + source version. An exact content/metadata replay writes nothing. A late delete event resolves the current owner first, so it cannot invalidate a subsequently recreated record.

## Status contract

| State | Meaning | Strict-writing behavior |
|---|---|---|
| READY | complete validated index and no pending work | query index |
| LAGGING | known pending events | synchronously process at most 32; otherwise authority fallback |
| INCOMPLETE | legacy/unverified/mismatched | authority-only fallback |
| REBUILDING | shadow rebuild has not validated | authority-only fallback |
| FAILED | event processing failed | authority-only fallback |

Internal endpoints expose status, processing, verify, and rebuild under `/api/projects/{project_id}/memory/index/*`. No normal-author UI was added.

## Compatibility

Projects without a checkpoint are `INCOMPLETE`, never implicitly complete. They continue opening; strict writing uses the safe fallback until a developer-triggered rebuild. Restores discard derived Native collections, create an incomplete checkpoint, and remain usable without Tencent.

## Read performance

The complete active index is cached in process by `(project_id, processed_version)`. Incremental writes invalidate that project. The cache is not persistence or authority and can always be repopulated from Mongo.

