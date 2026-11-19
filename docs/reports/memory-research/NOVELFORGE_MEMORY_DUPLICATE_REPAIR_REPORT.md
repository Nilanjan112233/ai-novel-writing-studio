# NovelForge Memory Duplicate Repair Report

## Confirmed defect

The real Memory Fantasy project has one active logical Chapter Intelligence version represented by two embeddings:

- logical identity: `chapter_intelligence:b8da1d0a-5bf7-54e8-b5c3-33409acb34cb:v1`;
- physical embedding IDs: `6a7886051b7d54bdba814b98` and `6a7886c81b7d54bdba814b9f`;
- source IDs: domain `intelligence_id` and Mongo owner `_id` respectively.

The dry run changed zero records. Evidence is in `artifacts/memory-p0/real-duplicate-repair-dry-run.json`.

## Identity rule

The indexed identity is now:

```text
project + source type + logical domain source + owner source version
```

Mongo `_id` remains a physical/evidence pointer. Chapter Intelligence direct indexing and project refresh both use `intelligence_id`. Other source types use their domain ID map, falling back to physical ID only when the owner has no domain identifier.

## Idempotency and repair

Owner-versioned indexing upserts the deterministic logical source/version. Replaying unchanged indexing produces one active materialization for that version. Query-time grouping also resolves old Chapter Intelligence aliases, so the real duplicate occupies one retrieval slot even before persisted repair.

`find_logical_memory_duplicates` is read-only. `repair_logical_memory_duplicates(dry_run=False)` rebuilds canonical derived rows and deactivates legacy aliases. It deletes no canon, decision, planning, prose, Chapter Intelligence owner, or other authority record. The derived index remains rebuildable.

Isolated tests verify:

- two legacy alias rows are identified as one logical group;
- retrieval selects at most one item and retains two evidence pointers;
- repair leaves the Chapter Intelligence owner intact;
- repeated unchanged indexing produces one active logical version;
- bounded historical versions remain retrievable for their interval.

## Operational decision

This pass did not mutate the real project's duplicate rows. Query-time protection is already active, and the real repair artifact is a dry run. A future operator may run persisted repair after backup using the same diagnostic, but broad/destructive cleanup is explicitly deferred.

