# NovelForge Narrative Studio V2 - Phase 1B Migration Guide

Migration date: 2026-06-14

The migration is additive and runs automatically at backend startup. The
standalone runner is recommended before deployment so its result can be
reviewed before application traffic resumes.

## Prerequisites

1. Back up the NovelForge MongoDB database.
2. Stop cycle execution and planning mutations.
3. Retain the Phase 1A `SETTINGS_ENCRYPTION_KEY`.
4. Install backend dependencies:

```powershell
cd backend
py -3.11 -m pip install -r requirements.txt
```

## Run

From the backend directory:

```powershell
py -3.11 scripts\run_phase_1b_migration.py
```

The migration:

- assigns deterministic stable IDs to legacy arcs;
- maps legacy arc status into the V2 lifecycle;
- adds chapter range, readiness, and drafting fields;
- migrates legacy timeline records into `timeline_entries`;
- deduplicates migrated timeline entries by legacy source identity;
- installs all Phase 1B named indexes;
- leaves legacy timeline data intact.

`arcs_normalized` reports the number of legacy arc records processed by the
normalizer. It does not mean new arc records were inserted.

The final repeat verification produced:

```json
{
  "arcs_normalized": 461,
  "timeline_entries_migrated": 0,
  "indexes_installed": true
}
```

The zero timeline count confirms that the repeat run created no duplicate V2
timeline entries.

## Added Collections

- `story_readiness`
- `timeline_entries`
- `character_progressions`
- `knowledge_entries`
- `foreshadow_registry_v2`
- `artifact_registry`
- `agent_memories`

`story_arcs` is normalized in place. `story_timelines` is retained.

## Verification

Run:

```powershell
npm run test:backend
npm run test:frontend
npm run build
npm run test:e2e
```

Operational checks:

- Arc 1 can report `READY` and drafting eligible.
- An unresolved future arc does not block Arc 1.
- Timeline V2 accepts `certainty: unknown`.
- Reader and character knowledge can differ without membership overlap.
- ReadinessAgent and KnowledgeAgent are selected only for impacted work.
- Agent memory remains within configured recent, important, and compressed
  bounds.
- Story Bible responses use Timeline V2 and include readiness and ledgers.
- Legacy timeline rows are not deleted.

## Deployment Order

1. Back up MongoDB.
2. Stop active cycles.
3. Deploy backend code and run the migration.
4. Verify indexes and migration output.
5. Deploy the frontend.
6. Run API, readiness, Timeline V2, and no-op orchestration smoke checks.
7. Monitor failed plans, memory growth, readiness blockers, limiter waits, and
   provider retries.

## Rollback

1. Stop new planning mutations and cycles.
2. Redeploy the Phase 1A application.
3. Keep the Phase 1B collections and indexes; Phase 1A ignores them.
4. Restore the legacy timeline read path, which remains untouched.
5. Disable ReadinessAgent and KnowledgeAgent assignments if only agent
   execution needs to be isolated.
6. Restore the database backup only if normalized arc fields conflict with an
   older custom deployment.

Do not remove the Phase 1A encryption key during rollback. The Phase 1B
collections are additive and may remain until retention and deletion policies
are approved.

