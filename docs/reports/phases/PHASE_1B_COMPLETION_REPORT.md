# NovelForge Narrative Studio V2 - Phase 1B Completion Report

Completion date: 2026-06-14

Status: Complete

Scope: Story Readiness Foundation. No chapter prose, WriterAgent, EditorAgent,
DialogueAgent, ArtifactAgent, or ForeshadowAgent was added.

## Architecture Decisions

- `ReadinessService` is the deterministic authority. AI may propose readiness
  items, but cannot approve requirements or silently block drafting.
- Readiness is evaluated per arc. An approved or active current arc can be
  draft-eligible while later arcs remain partial or unknown.
- `story_arcs` was normalized in place with stable IDs, lifecycle, chapter
  range, calculated readiness, and drafting eligibility.
- `timeline_entries` is the V2 timeline authority. It stores lightweight,
  arc-scoped anchors and treats `unknown` as a valid future state.
- Reader knowledge, character knowledge, and world truth use separate typed
  records. False character beliefs and hidden reader clues are representable.
- Character progression, foreshadowing, and artifacts are arc-linked ledgers,
  not instructions to generate prose.
- Agent memory is bounded by tier and source version, with deterministic
  compaction and stale cleanup.
- Phase 1A orchestration remains the production path. Readiness, arc,
  knowledge, timeline, progression, foreshadow, and artifact events extend its
  existing impact graph.

## Implemented Systems

### Readiness And Arcs

- Extensible `story_readiness` items with free-form categories.
- Statuses: `missing`, `discussed`, `proposed`, `approved`, `ready`.
- Priorities: `required`, `recommended`, `optional`.
- Reports: `READY`, `PARTIALLY_READY`, `NOT_READY`.
- Arc lifecycle: `draft`, `discussed`, `approved`, `active`, `completed`,
  `archived`.
- Scene planning now requires an explicit draft-eligible `arc_id`; it remains
  planning only and does not create prose.

### Planning Ledgers

- Timeline V2 supports known, probable, and unknown entries.
- Character progression is scoped to character and arc.
- Knowledge supports `WORLD_TRUTH`, `READER_KNOWLEDGE`, and
  `CHARACTER_KNOWLEDGE`.
- Foreshadow Registry V2 tracks planting and payoff lifecycle.
- Artifact Registry links items to arcs, characters, timeline entries, and
  knowledge entries.

### Agents And Memory

- Added only `ReadinessAgent` and `KnowledgeAgent`.
- ReadinessAgent output is persisted as non-blocking proposed work.
- KnowledgeAgent owns AI-created knowledge entries.
- Agents receive bounded compressed, important, and recent memory.
- Active memory is source-versioned, deduplicated, compacted, and cleaned.
- No static planning pipeline was reintroduced.

## New Collections

- `story_readiness`
- `timeline_entries`
- `character_progressions`
- `knowledge_entries`
- `foreshadow_registry_v2`
- `artifact_registry`
- `agent_memories`

Existing `story_arcs` was normalized in place. Legacy `story_timelines` was
retained for rollback.

## Indexes Added

- `readiness_project_item`
- `readiness_project_arc_gate`
- `story_arcs_project_arc`
- `story_arcs_project_lifecycle_order`
- `timeline_entries_project_entry`
- `timeline_entries_project_arc_certainty_order`
- `character_progressions_arc_character`
- `knowledge_entries_project_entry`
- `knowledge_entries_project_type_arc`
- `foreshadow_v2_project_entry`
- `foreshadow_v2_project_status_payoff`
- `artifact_registry_project_artifact`
- `artifact_registry_project_owner_status`
- `agent_memories_source_version`
- `agent_memories_agent_tier_active`

## API And UI

The additive planning API supports project-owned readiness, reports, arcs,
draft eligibility, Timeline V2, progressions, knowledge, foreshadowing,
artifacts, and memory diagnostics. Mutations validate linked resources and emit
typed orchestration events.

The workspace now includes:

- Readiness Dashboard
- Arc Board
- Knowledge View
- Timeline V2
- Arc-scoped character progression display

Unknown future entries are visually separated from known and probable entries.
The existing workspace and Orchestration Inspector were not redesigned.

## Files Changed

Backend:

- `backend/main.py`
- `backend/app/core/database.py`
- `backend/app/api/data.py`
- `backend/app/api/planning.py`
- `backend/app/api/projects.py`
- `backend/app/migrations/phase_1b.py`
- `backend/app/services/agent_memory_service.py`
- `backend/app/services/memory_retrieval_service.py`
- `backend/app/services/narrative_studio.py`
- `backend/app/services/orchestration_engine.py`
- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/readiness_service.py`
- `backend/app/services/settings_service.py`
- `backend/app/services/story_bible_service.py`
- `backend/scripts/run_phase_1b_migration.py`

Frontend:

- `frontend/app/project/[projectId]/page.tsx`
- `frontend/components/ArcBoard.tsx`
- `frontend/components/KnowledgeView.tsx`
- `frontend/components/ReadinessDashboard.tsx`
- `frontend/components/TimelineV2.tsx`
- `frontend/lib/api.ts`
- `frontend/store/projectStore.ts`
- `frontend/types/index.ts`

Validation:

- `backend/tests/test_story_readiness_v2.py`
- Phase 1A regression tests updated for the expanded agent registry
- `frontend/components/PlanningFoundation.test.tsx`
- `e2e/story-readiness-v2.spec.ts`

## Performance Impact

The real Phase 1B simulation persisted 42 agent task decisions across three
cycles: 18 executed and 24 skipped. This is a 57.1% skip rate. Readiness-only
work selected three agents; the system did not run every available agent.

Story Bible aggregation still occurs once at cycle completion. Timeline V2,
readiness, and ledger updates are indexed, project-scoped operations.

## Validation

| Gate | Result |
| --- | --- |
| Backend pytest | 59 passed, 7 skipped |
| Frontend Vitest | 43 passed |
| Next.js production build | Passed |
| Playwright | 18 passed, 2 skipped |
| Real Gemini | 18 successful Phase 1B calls |
| Model | `gemini-3.1-flash-lite` |
| Migration repeat | 0 duplicate timeline entries |
| Plaintext key scan | No Google API key found |

Non-blocking warnings remain for Pydantic V2 migration, FastAPI lifespan,
pytest-asyncio defaults, and Vite's CommonJS API.

## Remaining Before Drafting Phase

- Define the chapter and scene artifact model before adding prose generation.
- Add richer author editing forms for the new ledgers; Phase 1B UI is primarily
  inspection-oriented.
- Add explicit reconciliation controls for AI-proposed arcs that overlap an
  author-created arc or chapter range.
- Decide how approved knowledge and artifact facts promote into canon.
- Plan legacy timeline retirement only after a separate retention review.

These are drafting-phase or operational enhancements, not blockers to the
Phase 1B planning foundation.

