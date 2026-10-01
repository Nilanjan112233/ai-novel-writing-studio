# NovelForge Narrative Studio V2 - Phase 2A Completion Report

Completion date: 2026-06-14

Status: Complete

## Outcome

NovelForge now has an arc-centric development layer between readiness and
future prose drafting.

The production system can:

- move arcs through `idea`, `discussion`, `outline`, `development`,
  `approved`, `active`, `draftable`, `completed`, and `archived`;
- keep one current arc while preserving next and future arcs;
- calculate deterministic arc maturity from persisted planning evidence;
- gate draftability on maturity, required checklists, dependencies, readiness,
  and author approval;
- plan chapters and scenes without storing prose;
- track arc-specific character and power growth;
- trace knowledge, foreshadow, and artifact evolution;
- develop one selected arc through `StoryDevelopmentAgent`;
- skip `StoryDevelopmentAgent` for unrelated work;
- present the complete arc context in Arc Development and Story Room views.

No WriterAgent, EditorAgent, DialogueAgent, chapter text, or scene text was
introduced.

## Architecture Decisions

### Deterministic Authority

`ArcDevelopmentService` is the authority for maturity, dependency validation,
focus, lifecycle gates, and draftability. AI proposals cannot approve
checklists, satisfy dependencies, advance lifecycle, or change the score.

The default draftable threshold is 85. Maturity covers goal, conflict, stakes,
character growth, progression, knowledge, foreshadowing, artifacts, timeline,
mystery, and resolution planning.

### Configurable Checklists

Default checklist rows are seeded as data. Categories, titles, priorities,
weights, statuses, evidence, and dimensions remain editable and extensible.
Only required blocking items prevent draftability.

### Arc Focus

Arcs now carry `current`, `next`, or `future` focus. Activation validates
dependencies, promotes the requested arc, and derives the next/future order.
Incomplete future arcs do not block the current arc.

### Planning Without Prose

`chapter_plans` and `scene_plans` store purpose, conflict, character change,
knowledge change, artifact involvement, foreshadowing, and timeline impact.
API guards reject prose fields with HTTP 400.

### Dynamic Orchestration

The Phase 1A graph gained typed domains for arc development, chapter plans,
scene plans, power progression, knowledge evolution, foreshadow chains, and
artifact evolution.

`StoryDevelopmentAgent` is proposal-only and receives the current/target arc
context. The graph remains bounded by the existing cost, call, depth,
enablement, no-change, and provider-rate controls.

## New Collections

- `arc_checklists`
- `arc_dependencies`
- `chapter_plans`
- `scene_plans`
- `power_progressions`
- `foreshadow_chains`
- `artifact_evolutions`
- `knowledge_evolutions`

`story_arcs` and `character_progressions` were extended in place. Legacy scene
records were retained for rollback.

## Indexes Added

The migration installed 17 named Phase 2A indexes:

- 2 on `arc_checklists`
- 2 on `arc_dependencies`
- 3 on `chapter_plans`
- 2 on `scene_plans`
- 1 on `power_progressions`
- 2 on each evolution collection
- 1 focus/status/order index on `story_arcs`

The standalone migration rerun returned zero data changes and
`indexes_installed: true`, proving idempotency.

## API Surface

Added project-owned APIs for:

- arc development reports, activation, and status transitions;
- checklist CRUD and seeding;
- dependency CRUD and validation;
- chapter plans and Scene Plan V2;
- power progression;
- knowledge, foreshadow, and artifact evolution;
- Story Room projection.

Every cross-ledger ID is validated against the same project.

## UI Delivered

- Arc Development Workspace
- Story Room
- maturity score and dimension evidence
- lifecycle and current/next/future focus
- checklist actions and blockers
- dependency status
- chapter and scene planning
- character/power progression
- knowledge/foreshadow/artifact evolution
- updated Arc Board lifecycle columns

The former Drafting navigation label is now Scene Planning for Phase 2A.

## Primary Files Changed

Backend:

- `backend/app/services/arc_development_service.py`
- `backend/app/services/narrative_studio.py`
- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/orchestration_engine.py`
- `backend/app/services/story_bible_service.py`
- `backend/app/services/memory_retrieval_service.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/development.py`
- `backend/app/api/planning.py`
- `backend/app/api/data.py`
- `backend/app/api/projects.py`
- `backend/app/migrations/phase_2a.py`
- `backend/app/core/database.py`
- `backend/main.py`
- `backend/scripts/run_phase_2a_migration.py`

Frontend:

- `frontend/components/ArcDevelopmentWorkspace.tsx`
- `frontend/components/StoryRoom.tsx`
- `frontend/components/ArcBoard.tsx`
- `frontend/app/project/[projectId]/page.tsx`
- `frontend/store/projectStore.ts`
- `frontend/lib/api.ts`
- `frontend/types/index.ts`

Validation:

- `backend/tests/test_arc_development_v2.py`
- `frontend/components/ArcDevelopmentWorkspace.test.tsx`
- `e2e/arc-development-v2.spec.ts`
- supporting Phase 1A/1B fixture and regression updates

## Validation

- Backend: 62 passed, 7 environment-gated skips
- Frontend: 45 passed
- Production build: passed
- Playwright: 19 passed, 2 environment-reuse skips
- Real Gemini Phase 2A scenario: passed
- Model: `gemini-3.1-flash-lite`
- Migration rerun: idempotent
- Forbidden writing-agent scan: no implementation found
- Prose API contract: rejected as required

The Playwright matrix also recovered from a real transient Gemini 503 using
the provider gateway's exponential retry path.

## Performance Impact

The production Aether validation executed three cycles:

- 45 eligible agent tasks
- 18 selected calls
- 27 skipped tasks
- 60% skip rate
- 50% fewer calls than the old static 12-agent-per-cycle baseline
- 18 successful Gemini traces
- 5 requests/minute enforced
- 45.921 seconds of recorded limiter wait
- USD 0.065444 recorded cycle cost

The broad arc-development mutation batch selected 10 affected agents, while
the unrelated world cycle selected only `WorldAgent` and `FactionAgent`.
`StoryDevelopmentAgent` ran once and was skipped for world-only work.

## Remaining Boundaries Before Drafting

Phase 2A intentionally does not define:

- chapter or scene prose persistence;
- WriterAgent, DialogueAgent, or EditorAgent authority;
- prose revision and approval workflow;
- manuscript formatting/export;
- prose-specific continuity validation.

Those are drafting-phase decisions, not Phase 2A defects. Existing FastAPI and
Pydantic deprecation warnings are non-critical maintenance work.

