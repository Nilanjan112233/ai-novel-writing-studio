# NovelForge Narrative Studio V2 - Phase 2A Migration Guide

Migration date: 2026-06-14

## Scope

Phase 2A is additive. It adds eight collections, extends `story_arcs` and
`character_progressions`, and migrates eligible legacy scene planning records.
It does not delete Phase 1B data or generate prose.

## Prerequisites

1. Back up the MongoDB database.
2. Stop active orchestration cycles and planning mutations.
3. Deploy backend and frontend from the same Phase 2A release.
4. Confirm the MongoDB account can create indexes.

## Run

From `backend`:

```powershell
py -3.11 scripts/run_phase_2a_migration.py
```

The same migration runs during backend startup through
`backend/app/core/database.py`.

## Migration Behavior

The migration:

1. normalizes arc development lifecycle, focus, maturity, and resolution
   fields;
2. normalizes character start/midpoint/end and growth fields;
3. copies eligible legacy `scene_registry` planning rows to `scene_plans`;
4. seeds default checklist data only for arcs without checklist rows;
5. installs Phase 2A indexes.

Legacy records remain available. Migrated scenes retain a source identity for
deduplication.

## Expected Output

The command returns:

```json
{
  "arcs_normalized": 0,
  "progressions_normalized": 0,
  "scene_plans_migrated": 0,
  "checklist_items_seeded": 0,
  "indexes_installed": true
}
```

Non-zero counts are expected on the first run. The values above were observed
on the verified idempotent rerun.

## Verification

Confirm these collections exist:

- `arc_checklists`
- `arc_dependencies`
- `chapter_plans`
- `scene_plans`
- `power_progressions`
- `foreshadow_chains`
- `artifact_evolutions`
- `knowledge_evolutions`

Confirm the named indexes from `backend/app/migrations/phase_2a.py` exist,
especially the unique project-owned IDs and ordered arc/chapter lookups.

Run:

```powershell
py -3.11 -m pytest -q
cd ..
npm run test:frontend
npm run build
npm run test:e2e
```

## Compatibility

- Phase 1B `approval_status` remains available.
- Legacy `scene_registry` remains intact.
- `drafted` is a planning lifecycle marker only; no text is stored.
- Existing arcs default safely to `idea`/`future` when authority is unclear.
- Future incomplete arcs do not block the current arc.

## Rollback

1. Stop active cycles and planning mutations.
2. Redeploy the Phase 1B backend and frontend together.
3. Leave additive collections and indexes in place; Phase 1B ignores them.
4. Restore `scene_registry` as the scene-planning read path.
5. Disable `StoryDevelopmentAgent` if isolating provider behavior.
6. Restore the database backup only for an external consumer that cannot
   tolerate additive arc/progression fields.

Do not drop Phase 2A collections during routine rollback. Retaining them keeps
the rollback reversible.

