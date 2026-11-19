# NovelForge Narrative Studio V2 - Phase 2B Completion Report

Completion date: 2026-06-14

Status: Complete

## Outcome

NovelForge now supports controlled scene and chapter drafting without making
generated prose authoritative.

The production system can:

- generate exactly one scene draft from one approved Scene Plan V2 record;
- assemble a chapter only from approved, active scene draft versions;
- enforce readiness, maturity, checklist, dependency, chapter, and scene gates;
- validate continuity deterministically before approval;
- preserve immutable prose history with version lineage and active versions;
- review, approve, reject, archive, regenerate, and roll back drafts;
- expose draft queues, continuity reports, and version history in Story Room
  and Arc Development;
- persist a demand-driven orchestration plan for every provider generation;
- keep planning records authoritative and unchanged by drafting.

No EditorAgent, DialogueAgent, RevisionAgent, LineEditorAgent,
ManuscriptAgent, BookWriterAgent, or full-manuscript workflow was added.

## Architecture Decisions

### Draft Generation

`DraftingService` owns project/arc/chapter/scene validation, eligibility
preflight, provider execution, version creation, lifecycle transitions,
rollback, events, and Story Bible refresh.

`SceneWriterAgent` receives one approved scene plan plus bounded,
project-owned planning context. Its response contains prose and structured
continuity claims. It cannot approve its output or mutate planning records.

`ChapterAssemblerAgent` returns only transitions between adjacent approved
scene draft IDs. The service constructs the chapter, preserving every source
scene verbatim and in plan order. Unknown, duplicate, missing, or reordered
scene references are rejected.

### Planning Authority

Readiness, arc development, dependencies, chapter plans, scene plans,
knowledge, timeline, progression, artifacts, and foreshadowing remain the
source of truth. Draft generation reads these ledgers but never writes to
them.

Generated continuity claims are derivative assertions. They do not satisfy
planning gates or alter story authority.

### Versioning

Each generation creates a new immutable content record with:

- stable `draft_id`;
- monotonically increasing `version_number`;
- optional `parent_version_id`;
- `active` version marker;
- generation metadata and agent identity;
- lifecycle status;
- creation and review timestamps.

Prose and lineage are never overwritten. Lifecycle fields may change through
validated review actions. Regeneration creates a child version. Rollback
reactivates a preserved version and deactivates the prior active version.

The lifecycle is:

`draft -> review -> approved`

`draft` or `review` may instead become `rejected` or `archived`. Approval is
never automatic and requires a fresh non-FAIL continuity report.

### Continuity

`DraftValidationService` is deterministic and has no provider authority. It
checks:

- project, arc, chapter, and scene membership;
- current draftability and dependency state;
- scene order and chapter membership;
- linked knowledge, artifact, timeline, progression, and foreshadow IDs;
- character focus and undeclared power changes;
- approved source scene versions;
- exact preservation and order of source prose;
- transition adjacency.

Results are `PASS`, `WARNING`, or `FAIL`. A FAIL blocks approval.

Every generated draft receives a post-generation report. Approval produces a
new approval-stage report, so the verified six-scene/three-chapter scenario
created 18 successful validation results.

### Dynamic Orchestration

Explicit draft generation persists a Phase 1A orchestration plan and tasks:

- scene generation selects only `SceneWriterAgent`;
- chapter assembly selects only `ChapterAssemblerAgent`;
- the other 16 eligible agents are recorded as skipped with reasons;
- enablement, call limit, cost budget, depth limit, provider rate limit, and
  execution trace controls remain active.

Ordinary project events do not generate prose. Drafting is an explicit author
action. Continuity failures route only to implicated planning agents such as
`KnowledgeAgent` and `StoryDevelopmentAgent`.

## Database

Collections added:

- `scene_drafts`
- `chapter_drafts`
- `continuity_reports`

Ten named indexes were installed:

- four on `scene_drafts`;
- four on `chapter_drafts`;
- two on `continuity_reports`.

They cover project ownership, stable IDs, unique version numbers, review
queues, active versions, version lineage, validation stage, and result.

The standalone migration rerun returned:

```json
{
  "scene_drafts_normalized": 0,
  "continuity_reports_normalized": 0,
  "indexes_installed": true
}
```

This confirms the verified migration is idempotent.

## API

The project-owned drafting router adds:

- scene and chapter generation;
- scene and chapter regeneration;
- scene and chapter history;
- review status transitions;
- scene and chapter rollback;
- explicit continuity validation;
- continuity report history;
- draft review queue.

Every route validates the project and all referenced arc, chapter, scene,
draft, and planning records. Cross-project references fail before provider
execution.

## UI

Added:

- top-level Controlled Drafting workspace;
- Drafting tab in Arc Development;
- scene and chapter generation status;
- PASS, WARNING, and FAIL validation display;
- review, approve, reject, archive, regenerate, and rollback actions;
- version lineage and generation history;
- Story Room draft queue and continuity warnings.

The final browser inspection found no console errors or warnings.

## Files Changed

Backend:

- `backend/app/api/drafting.py`
- `backend/app/services/drafting_service.py`
- `backend/app/services/draft_validation_service.py`
- `backend/app/services/narrative_studio.py`
- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/orchestration_engine.py`
- `backend/app/services/provider_gateway.py`
- `backend/app/services/settings_service.py`
- `backend/app/services/story_bible_service.py`
- `backend/app/services/database_audit_service.py`
- `backend/app/core/database.py`
- `backend/app/api/data.py`
- `backend/app/api/development.py`
- `backend/app/api/projects.py`
- `backend/main.py`
- `backend/app/migrations/phase_2b.py`
- `backend/scripts/run_phase_2b_migration.py`

Frontend:

- `frontend/components/DraftingWorkspace.tsx`
- `frontend/components/ArcDevelopmentWorkspace.tsx`
- `frontend/components/StoryRoom.tsx`
- `frontend/app/project/[projectId]/page.tsx`
- `frontend/store/projectStore.ts`
- `frontend/lib/api.ts`
- `frontend/types/index.ts`

Tests:

- `backend/tests/test_drafting_v2.py`
- `backend/tests/conftest.py`
- `frontend/components/ArcDevelopmentWorkspace.test.tsx`
- `e2e/drafting-v2.spec.ts`

## Performance

Real Gemini validation used nine provider calls for nine requested draft
operations. Each explicit plan selected one agent and skipped 16, for 144
recorded skips and an average of one agent call per operation.

Against applying the legacy static 12-agent cycle to each operation, this is
91.7% fewer provider calls.

The final real-provider run recorded:

- model: `gemini-3.1-flash-lite`;
- provider calls: 9;
- tokens: 32,973;
- cost: USD 0.013190;
- total limiter wait: 22,984 ms;
- maximum admissions in any rolling 60 seconds: 5;
- retries: 0.

## Verification

- Backend: 66 passed, 7 skipped
- Frontend: 45 passed
- Production build: passed
- Full Playwright matrix: 20 passed, 2 skipped
- Final Phase 2B real-Gemini Playwright: 1 passed
- Migration: passed and idempotent
- Browser console: 0 errors, 0 warnings

The two full-matrix skips are environment-gated lifecycle reuse cases. The
Phase 1A, Phase 1B, Phase 2A, and Phase 2B scenarios executed through their
configured real-provider paths.

## Remaining Manuscript-Phase Work

Phase 2B intentionally does not provide manuscript aggregation, editorial
passes, dialogue specialization, revision branches, line editing,
book-level continuity sweeps, publication export, or autonomous writing.

Those are future manuscript-phase capabilities. They do not block controlled
scene and chapter drafting delivered in this phase.
