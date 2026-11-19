# NovelForge Narrative Studio V2 - Phase 1A Completion Report

Completion date: 2026-06-13

Status: Complete

Scope: Production Orchestrator Activation only. No readiness, arc drafting,
chapter writing, progression, knowledge, artifact, foreshadowing, dynamic
timeline, world expansion, or new story-agent systems were added.

## Production Architecture

`POST /api/projects/{project_id}/run` and
`POST /api/projects/{project_id}/cycle` now enter
`OrchestrationServiceV2`. The old implicit 12-agent call to
`NarrativeStudioService.run()` is no longer the default production path.

The active flow is:

1. Read unprocessed project events and the current trigger.
2. Detect changed entities and affected narrative domains.
3. Traverse the code-owned dependency and impact graph.
4. Exclude disabled agents and apply depth, call, and cost limits.
5. Persist an orchestration plan and one task for each planning agent.
6. Execute only selected agents through `NarrativeStudioService`.
7. Persist task, plan, trace, run, and cycle terminal states.
8. Rebuild the Story Bible once after cycle finalization.
9. Stop without provider calls when no meaningful change exists.

## Implemented Capabilities

- Demand-driven agent selection with persisted run and skip reasons.
- Bounded graph traversal with `MAX_ORCHESTRATION_DEPTH=5`.
- Hard cycle cap with `MAX_AGENT_CALLS_PER_CYCLE=10`.
- Active enforcement of `max_agent_calls_per_cycle` and
  `max_cycle_cost_usd`.
- `NO_CHANGE_TERMINATION` with zero provider calls.
- Disabled agents cannot be selected.
- Provider-specific sliding-window queues, configurable from 5 to 10 requests
  per minute.
- Exponential retry handling for 429 and transient provider failures.
- Rate-limit wait and retry metadata in execution traces.
- Fernet encryption for provider credentials at rest.
- Settings APIs return configuration state, never stored credential values.
- Project ownership validation for runs, cycles, outputs, questions, answers,
  and other child workflow resources.
- Memory source versioning, active-state filtering, and stale duplicate cleanup.
- One Story Bible rebuild at the true cycle terminal point.
- Latest and historical orchestration APIs.
- Minimal Orchestration Inspector with selected agents, skipped agents,
  reasons, graph, status, and stop reason.

## Database Changes

Only the two approved collections were added:

- `orchestration_plans`
- `orchestration_tasks`

Installed indexes:

- `runs_project_started_at`
- `runs_project_status`
- `cycles_project_cycle`
- `agent_outputs_project_created_at`
- `agent_outputs_run_created_at`
- `questions_project_answered_created_at`
- `timeline_messages_project_created_at`
- `discussion_messages_project_cycle_created_at`
- `story_bibles_project`
- `memory_source_version`
- `memory_project_active_source`
- `project_events_project_id`
- `execution_traces_project_created_at`
- `execution_traces_run`
- `orchestration_plans_project_created_at`
- `orchestration_plans_run`
- `orchestration_tasks_plan_agent`
- `orchestration_tasks_plan_status`

The migration is idempotent. Its final verification run reported zero pending
Story Bible deletions, zero pending secret migrations, zero pending memory
normalizations, and all indexes installed.

## API Changes

Added:

- `GET /api/projects/{project_id}/orchestration/latest`
- `GET /api/projects/{project_id}/orchestration/history`

Changed:

- `/run` and `/cycle` use the production V2 orchestrator.
- Provider settings responses expose `configured` state and a blank key input.
- Child-resource operations validate the parent project and related run/cycle.
- Execution traces include project, run, cycle, plan, limiter, and retry data.

## Files Changed

Backend production:

- `backend/app/api/data.py`
- `backend/app/api/projects.py`
- `backend/app/api/settings.py`
- `backend/app/api/workflow.py`
- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/migrations/phase_1a.py`
- `backend/app/services/execution_trace_service.py`
- `backend/app/services/memory_retrieval_service.py`
- `backend/app/services/narrative_studio.py`
- `backend/app/services/orchestration_engine.py`
- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/provider_gateway.py`
- `backend/app/services/provider_rate_limiter.py`
- `backend/app/services/secret_encryption_service.py`
- `backend/app/services/settings_service.py`
- `backend/app/services/story_bible_service.py`
- `backend/app/services/workflow_persistence.py`
- `backend/requirements.txt`
- `backend/.gitignore`
- `backend/scripts/run_phase_1a_migration.py`

Frontend production:

- `frontend/app/project/[projectId]/page.tsx`
- `frontend/app/settings/page.tsx`
- `frontend/components/OrchestrationInspector.tsx`
- `frontend/store/projectStore.ts`
- `frontend/types/index.ts`

Tests:

- `backend/tests/test_narrative_intelligence.py`
- `backend/tests/test_orchestration_context.py`
- `backend/tests/test_orchestration_v2.py`
- `backend/tests/test_production_integrity.py`
- `frontend/app/settings/page.test.tsx`
- `frontend/components/OrchestrationInspector.test.tsx`
- `e2e/orchestration-v2.spec.ts`

## Measured Production Result

The real-provider Ashes of Valeria simulation completed four cycles:

| Metric | Result |
| --- | ---: |
| Total cycles | 4 |
| Total agent calls | 12 |
| Static baseline | 48 |
| Average agents per cycle | 3.0 |
| Skipped agent slots | 36 of 48 |
| Skip percentage | 75% |
| Call reduction | 75% |
| Provider traces | 12 |
| Actual cost | $0.031380 |
| Configured cycle budget | $2.00 |

The final no-op cycle selected no agents, created all 12 task records with skip
reasons, made zero provider calls, and ended with
`NO_CHANGE_TERMINATION`.

## Acceptance Verification

- Backend: 55 passed, 7 skipped.
- Frontend: 40 passed.
- Production Next.js build: passed.
- Playwright: 17 passed, 2 skipped.
- Real Gemini model: `gemini-3.1-flash-lite`, passed.
- Production orchestrator path: dynamic and persisted.
- Provider rate limit: 5 requests/minute, observed in every provider trace.
- Story Bible aggregation: once at cycle completion.
- API key plaintext fields: no configured plaintext values found.
- Critical Phase 1A audit findings: resolved.

Remaining warnings are non-blocking Pydantic, FastAPI lifespan, pytest-asyncio,
and Vite CommonJS deprecations. They do not affect Phase 1A behavior.
