# Architecture Impact

## Unchanged

MongoDB remains authoritative. Canon Governance, Canon Proposal Queue, Decision History, Story Bible rebuilds, Narrative Analysis Engine/shared graph, scene/chapter draft lineage, Writer's Room, Paragraph Editor, chronology checks, manuscript/revision lineage, backup/restore, publication governance, and provider validation remain the owning boundaries.

## Modified

The existing chapter-draft model now accepts `workflow_mode=discovery` and nullable planning links. The legacy unique chapter index is partial for structured plans, so discovery versions no longer collide on `null`. Context construction now puts canon, approved decisions, and timeline evidence ahead of general retrieval. Assistant generation now uses the existing failover gateway.

## New persistence only

`story_studio_jobs` stores author-facing work state and summaries; it is not story authority. `discovery_extractions` stores candidate knowledge with source draft/version provenance; it is never silently promoted to canon.

