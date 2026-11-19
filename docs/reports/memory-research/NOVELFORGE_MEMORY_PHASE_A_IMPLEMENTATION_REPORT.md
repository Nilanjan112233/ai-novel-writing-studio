# NovelForge Memory Phase A Implementation Report

## Outcome

Phase A is implemented. Normal Native retrieval is checkpointed and read-only. Owner changes enqueue durable, idempotent Mongo events; bounded processing updates only affected logical records. Strict writing never treats an incomplete, failed, or rebuilding derived index as complete.

Implemented components:

- deterministic owner materialization shared by rebuild and incremental paths;
- Mongo event ledger, project checkpoint/watermark, and shadow rebuild staging;
- `READY`, `LAGGING`, `INCOMPLETE`, `REBUILDING`, and `FAILED` status contract;
- bounded synchronous catch-up (32 events);
- authority-only, provider-free strict-writing fallback;
- crash requeue, failure retry, duplicate delivery protection, current-owner ordering;
- resumable project rebuild with logical count/hash and owner-version guard;
- checkpoint/index verification and internal diagnostic endpoints;
- version-keyed complete-index cache;
- derived-index exclusion from portable backups and rebuild after restore;
- Chapter Intelligence incremental hook;
- removal of Narrative Studio full refreshes;
- Phase A replay/scale/mutation diagnostics.

## Preserved boundaries

No approved prose, canon, decision, planning, or structured owner was migrated or mutated. Candidate/rejected/derived/Tencent records cannot override authority. No atomic memory, L1/L2 store, BM25, semantic provider, RRF, graph database, progressive retrieval, preference memory, Develop Story packet redesign, or Tencent dependency was added.

## Old limits

The P0 pass already removed the active 2,000-row retrieval and 1,000-owner refresh caps. Phase A retains complete streaming scans for rebuild and complete cache fill. The remaining `length=1000` occurrence in `index_memory` is only bounded deletion of excess inactive legacy predecessors in the legacy non-versioned maintenance path; Phase A incremental owner writes use explicit versions and do not silently truncate active retrieval or rebuild.

## Operational result

At 500 chapters, READY retrieval performs zero owner scans and zero index writes; P95 is 80.13 ms versus P0's 111.33 ms. A single mutation inspected one owner and wrote one row, independent of novel size. Unchanged replay wrote zero.

## Files and diagnostics

Core implementation is in `memory_incremental_index_service.py`, `memory_index_cache.py`, the Phase A migration, provider/retrieval/event integration, Chapter Intelligence, backup/restore, and internal data API routes. Machine-readable outputs are under `artifacts/memory-phase-a/`.

