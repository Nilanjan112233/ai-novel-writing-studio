# NovelForge Index Rebuild and Recovery Report

## Rebuild design

Rebuild is project-scoped, provider-free, and writes materialized owners to `memory_index_staging` under a unique rebuild ID. Progress records the next source in the project checkpoint. A resumed run reuses staged rows and continues from that source.

Before commit it verifies unique logical identities and rechecks `authority_state_version`. If an owner event advanced the version during the rebuild, commit is refused with `owner_changed_during_rebuild`; the existing index is not presented as complete. Commit deterministically upserts staged rows, invalidates active rows absent from the snapshot, computes a stable count/hash, and marks `READY` only after validation. No owner is modified.

## Tested recovery

- interrupted rebuild: returned `REBUILDING`, resumed to validated `READY`;
- 500-chapter interrupted/resumed rebuild: 2,521 current records, 13,978.39 ms resume;
- duplicate delivery and double processing: one active logical row;
- simulated crash in `processing`: startup recovery requeued it;
- out-of-order delete: current owner remained active;
- temporary Mongo failure: checkpoint became `FAILED`, retry returned `READY`;
- owner changed during rebuild: commit refused and restart required;
- missing/corrupt derived row: count/hash verification detected mismatch and marked `INCOMPLETE`;
- backup/restore: derived index excluded, restored authority preserved, checkpoint incomplete, rebuild and recall passed;
- Tencent unavailable: no indexing/rebuild dependency; existing Native fallback tests passed.

## Timings

| Corpus | Full validated rebuild |
|---:|---:|
| 100 chapters / 515 logical rows | 4,035.53 ms |
| 500 chapters / 2,515 logical rows | 48,003.50 ms |

Rebuild is intentionally an administrative/repair path, not a writing-request path. The 500-chapter interrupted resume was faster because already-staged sources were reused and unchanged upserts were idempotent.

