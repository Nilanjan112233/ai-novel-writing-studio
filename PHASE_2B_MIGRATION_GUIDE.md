# NovelForge Narrative Studio V2 - Phase 2B Migration Guide

Migration date: 2026-06-14

## Scope

Phase 2B is additive. It adds controlled draft storage and continuity reports
without replacing or deleting Phase 2A planning collections.

Collections added:

- `scene_drafts`
- `chapter_drafts`
- `continuity_reports`

Planning records remain authoritative throughout migration and rollback.

## Prerequisites

1. Back up MongoDB.
2. Stop active orchestration cycles and draft mutations.
3. Deploy the Phase 2B backend and frontend together.
4. Confirm the MongoDB account can create unique and compound indexes.
5. Confirm provider secrets are already stored through encrypted settings.

## Run

From `backend`:

```powershell
py -3.11 scripts/run_phase_2b_migration.py
```

The same idempotent migration runs during backend startup through
`backend/app/core/database.py`.

## Migration Behavior

The migration:

1. assigns stable IDs to legacy scene draft records;
2. preserves legacy draft text as `generated_text`;
3. archives legacy drafts that cannot be associated with a Scene Plan V2 ID;
4. initializes version, active, status, lineage, metadata, and timestamps;
5. normalizes existing continuity records to the Phase 2B taxonomy;
6. creates the Phase 2B indexes;
7. records migration version 1 in global settings.

It does not delete legacy content or modify readiness, arc, chapter-plan,
scene-plan, knowledge, timeline, progression, artifact, or foreshadow
authority.

## Indexes

`scene_drafts`:

- `scene_drafts_project_draft`
- `scene_drafts_scene_version`
- `scene_drafts_review_queue`
- `scene_drafts_lineage`

`chapter_drafts`:

- `chapter_drafts_project_draft`
- `chapter_drafts_chapter_version`
- `chapter_drafts_review_queue`
- `chapter_drafts_lineage`

`continuity_reports`:

- `continuity_reports_project_report`
- `continuity_reports_subject_result`

Unique indexes enforce stable project-owned IDs and version numbers. Compound
indexes support active review queues, arc/chapter/scene lookups, lineage, and
continuity history.

## Expected Output

An idempotent rerun returns:

```json
{
  "scene_drafts_normalized": 0,
  "continuity_reports_normalized": 0,
  "indexes_installed": true
}
```

Non-zero normalization counts are expected on the first run when legacy
records exist.

## Verification

Run:

```powershell
py -3.11 -m pytest -q
cd ..
npm run test:frontend
npm run build
npm run test:e2e
```

Verify:

- all ten named indexes exist;
- legacy unowned scene drafts are archived, inactive, and still readable;
- one active version is returned for each drafted scene/chapter;
- generation is denied for non-draftable arcs;
- chapter assembly is denied unless every source scene is approved;
- FAIL continuity reports prevent approval;
- provider traces contain `rate_limit_acquired_at`;
- orchestration history shows one selected drafting agent and explicit skips.

## Compatibility

- Phase 2A chapter and scene plans are unchanged.
- Existing Story Bible readers receive draft summaries without making drafts
  canon.
- The legacy `/draft-scenes` action remains scene planning and is not a prose
  generation bypass.
- Old application versions ignore the additive collections.
- Phase 2B statuses do not change arc lifecycle or readiness.

## Rollback

1. Stop active cycles and drafting requests.
2. Deploy the Phase 2A backend and frontend together.
3. Disable `SceneWriterAgent` and `ChapterAssemblerAgent` if mixed-version
   workers are still draining.
4. Leave the three additive collections and ten indexes in place.
5. Retain all draft versions and continuity reports for a later forward
   migration.
6. Restore the pre-migration database backup only if an external consumer
   cannot tolerate additive collections.

Do not routinely drop Phase 2B collections. Keeping them preserves generated
history and makes rollback reversible.

## Forward Re-enable

After redeploying Phase 2B:

1. rerun the migration;
2. enable both drafting agents;
3. confirm execution budgets and the 5-10 requests/minute provider setting;
4. validate one scene in review mode;
5. confirm its orchestration plan, trace, continuity report, and active
   version before reopening drafting to users.
