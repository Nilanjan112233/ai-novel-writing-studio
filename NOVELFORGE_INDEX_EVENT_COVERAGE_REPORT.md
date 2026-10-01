# NovelForge Index Event Coverage Report

## Sources

Phase A centralizes 36 indexed owner types plus the project owner in `SOURCE_SPECS`. Materialization uses the P0 identity and eligibility metadata for both rebuild and incremental work.

## Change coverage

| Change | Trigger | Incremental action |
|---|---|---|
| project create/update/duplicate | durable `project_created` / `project_updated` event | project owner upsert |
| decision confirm/change/reopen | question/decision project events | decision owner resolve/upsert/invalidate |
| canon approval/review | canon project event | canon owner resolve/upsert |
| candidate project/confirm/reconsider/reject | Story Knowledge events | changed structured owners since watermark |
| Develop Story specialist completion | `agent_completed` | changed owner batch since last successful update |
| Story Bible/workspace/discussion/intelligence update | existing project event | changed owner batch |
| chapter approval/intelligence refresh/revision | Chapter Intelligence hook | exact intelligence owner upsert |
| archive/delete/supersede | exact event where supplied; otherwise changed-owner batch | resolve current owner, or invalidate only if absent |
| repeated delivery | unique event key | no second sequence/event/write |
| event ordering | processor resolves current owner | current owner wins |

Batch updates query `(project_id, updated_at)` indexes and inspect only records changed since the checkpoint watermark. They do not scan all documents in each collection.

## Failure boundary

The owner mutation commits before derived enqueue. If enqueue fails, the hook marks the checkpoint incomplete where Mongo is available; the author save is not rolled back. Processing failure records the error and moves the checkpoint to `FAILED`. Startup requeues `processing` events. A validated rebuild acknowledges pending/failed events up to its captured state version.

## Known limitation

Writes that bypass all application owner services and durable project events (for example, manual database edits) do not emit events. `verify` detects missing/corrupt/mismatched derived rows, but it is an explicit diagnostic rather than an O(project-size) operation on every read. Operational code must continue routing owner changes through application services.
