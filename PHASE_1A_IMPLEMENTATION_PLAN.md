# NovelForge Narrative Studio V2 - Phase 1A Implementation Plan

Plan date: 2026-06-13

Source of truth:

- `PRODUCTION_ARCHITECTURE_AUDIT.md`
- `DATABASE_MODEL_AUDIT.md`
- `AGENT_ARCHITECTURE_AUDIT.md`

Scope: Production Orchestrator Activation only. This phase does not add story
readiness, arc drafting, chapter writing, dynamic timeline, progression,
KnowledgeAgent, ArtifactAgent, ForeshadowingAgent, world expansion, or any new
story-development agent.

## Current Architecture Summary

The active workflow is FastAPI plus MongoDB with a Next.js workspace. Both
`POST /api/projects/{project_id}/run` and `/cycle` schedule a background task,
build broad persistent state, and call `NarrativeStudioService.run()` without
an agent selection. The service then executes the same 12 planning agents in
the fixed `AGENT_SPECS` order.

The current service persists each agent's artifacts immediately, reindexes
project memory after each agent, rebuilds the Story Bible after each agent, and
rebuilds it again at cycle completion. A separate `OrchestrationEngine`
contains partial budget and observability behavior but is not connected to the
production workflow and does not persist Narrative Studio artifacts.

Provider calls go through `ProviderGateway`, which retries failed requests but
does not enforce a per-provider request rate. Agent `enabled` flags and cycle
budget settings are ignored by the active path. Provider credentials are stored
and returned in plaintext. Several child-resource routes query only by child ID
and do not verify project ownership.

The frontend uses a single project workspace, Zustand state, and SSE-triggered
Story Bible invalidation. It exposes workflow output but not the production
selection plan or skip reasons.

## Problems Discovered By Audit

1. The production cycle is a static 12-agent pipeline.
2. The unused adaptive engine is not a safe replacement for the production
   artifact-writing path.
3. There is no persisted impact graph, execution plan, task status, or skip
   explanation.
4. No-change cycles still invoke every planning agent.
5. Agent enablement, call caps, and dollar budgets are not enforced.
6. There is no loop-depth guard or provider request limiter.
7. Story Bible aggregation and memory indexing are repeated after every agent.
8. Memory embeddings accumulate stale source versions.
9. Provider API keys are plaintext at rest and disclosed by the settings API.
10. Run, output, question, answer, and cycle ownership checks are inconsistent.
11. Core workflow, event, memory, Story Bible, and trace queries lack indexes.
12. The UI cannot explain why an agent ran, skipped, failed, or stopped.

## Proposed Solution

Add `OrchestrationServiceV2` as the only normal `/run` and `/cycle` execution
planner. It will:

1. Read unprocessed project events, cycle trigger messages, queued tasks, and
   initial project fields.
2. Classify meaningful changed entities and affected narrative domains.
3. Traverse a code-owned dependency and impact graph with cycle detection and a
   configurable depth cap.
4. Remove disabled agents.
5. enforce `max_agent_calls_per_cycle`, `max_cycle_cost_usd`,
   `MAX_AGENT_CALLS_PER_CYCLE`, and `MAX_ORCHESTRATION_DEPTH`.
6. Persist one `orchestration_plans` record and one
   `orchestration_tasks` record for every planning agent, including explicit
   skip reasons.
7. Execute only the ordered selected-agent list through
   `NarrativeStudioService`.
8. Mark task and plan status as execution proceeds.
9. terminate without provider calls when no meaningful changes remain.

The graph will be declared in code as domain seeds plus agent impact edges. A
bounded breadth-first traversal will produce order and selection reasons;
execution will not derive from the static `AGENT_SPECS` sequence.

`NarrativeStudioService` will remain the artifact persistence executor, but it
will require an explicit ordered agent list for production cycles, honor plan
task status, stop on enforced budget/call limits, index project memory once
before and once after a cycle, and rebuild the Story Bible once at cycle
completion.

A process-wide, provider-specific sliding-window limiter will enforce a
configurable 5-10 requests per minute. Every retry must reacquire capacity.
429 responses will use exponential backoff, and rate-limit wait/retry metadata
will be recorded in execution traces.

Provider credentials will be encrypted with Fernet before MongoDB persistence.
The API will return only `configured` state and an empty input value. Existing
plaintext settings will be migrated in place. Production deployments will use
`SETTINGS_ENCRYPTION_KEY`; local development may use a separately stored local
key file.

## Files Affected

Expected backend additions:

- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/provider_rate_limiter.py`
- `backend/app/services/secret_encryption_service.py`
- `backend/app/migrations/phase_1a.py`
- Phase 1A backend tests

Expected backend modifications:

- `backend/app/api/workflow.py`
- `backend/app/api/data.py`
- `backend/app/api/projects.py`
- `backend/app/api/settings.py`
- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/services/narrative_studio.py`
- `backend/app/services/provider_gateway.py`
- `backend/app/services/execution_trace_service.py`
- `backend/app/services/settings_service.py`
- `backend/app/services/ai_provider.py`
- `backend/app/services/memory_retrieval_service.py`
- `backend/app/services/story_bible_service.py`
- `backend/requirements.txt`

Expected frontend additions:

- `frontend/src/components/workspace/OrchestrationInspector.tsx`
- Orchestration Inspector tests

Expected frontend modifications:

- `frontend/src/app/projects/[id]/page.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/stores/projectStore.ts`
- `frontend/src/types/index.ts`
- provider settings UI and tests where needed

Expected validation additions:

- `e2e/orchestration-v2.spec.ts`
- `PHASE_1A_COMPLETION_REPORT.md`
- `PHASE_1A_MIGRATION_GUIDE.md`
- `PHASE_1A_E2E_RESULTS.md`

The exact list may narrow after implementation, but no later-phase story system
will be introduced.

## Database Changes

Add only these collections:

### `orchestration_plans`

Required fields:

- `project_id`
- `run_id`
- `cycle_id`
- `trigger_type`
- `changed_entities`
- `affected_domains`
- `selected_agents`
- `skipped_agents`
- `selection_reasons`
- `created_at`
- `status`

Operational metadata may include ordered graph nodes, estimated/actual calls,
estimated/actual cost, stop reason, limits, and completion timestamps.

### `orchestration_tasks`

Required fields:

- `plan_id`
- `agent_name`
- `status`
- `reason`
- `started_at`
- `completed_at`

Operational metadata may include order, provider, model, token, cost, retry, and
error summaries.

Add migration-managed indexes from the database audit for:

- `runs`
- `cycles`
- `agent_outputs`
- `questions`
- `timeline_messages`
- `discussion_messages`
- `story_bibles`
- `memory_embeddings`
- `project_events`
- `execution_traces`
- `orchestration_plans`
- `orchestration_tasks`

Before unique indexes are created, the migration will normalize or deduplicate
the affected identity groups. Memory records will receive `source_version` and
`active`; only the latest source version will be active, and older redundant
versions will be bounded by cleanup.

No other collection will be created in Phase 1A.

## API Changes

`GET /api/projects/{project_id}/orchestration/latest` will return the latest
plan, selected agents, skipped agents, selection reasons, graph/order, task
statuses, stop reason, and execution totals.

`GET /api/projects/{project_id}/orchestration/history` will return project-owned
plan history with task summaries.

The existing run and cycle APIs keep their public start contracts, but their
background path will invoke `OrchestrationServiceV2`.

Settings responses will no longer include usable credentials. Provider entries
will expose `configured: true|false`, a blank `api_key`, and non-secret model
configuration. Blank keys submitted from an already configured provider will
preserve the encrypted credential; explicit clearing will require a clear flag.

Child-resource reads and mutations will include `project_id` in their database
filters. Invalid cross-project IDs will return 404.

## UI Changes

Add a minimal Orchestration Inspector to the existing workflow area. It will
show:

- plan and execution status;
- selected agents;
- skipped agents;
- per-agent selection or skip reason;
- graph execution order;
- task state and stop reason.

The existing workspace navigation and information architecture will not be
redesigned. Provider settings will show configured state without receiving the
secret.

## Migration Plan

1. Add idempotent Phase 1A migration code and run it at database startup.
2. Encrypt any legacy plaintext provider keys and remove plaintext fields.
3. Normalize memory records with source versions and active state.
4. Mark newest memory source versions active and clean redundant stale copies.
5. Deduplicate Story Bible/project identities if necessary before unique index
   creation.
6. Create minimum indexes using stable names so reruns are safe.
7. Deploy backend code that can read both pre-migration and migrated documents
   during the transition.
8. Activate `OrchestrationServiceV2` for `/run` and `/cycle`.
9. Deploy the inspector against the new read APIs.

Migration scripts will be executable independently and verified against the
configured database.

## Test Plan

Backend tests:

- change classification for premise, character, world, power, faction,
  relationship, theme, mystery, arc, approval, rejection, answer, and no-op;
- graph traversal order, cycle prevention, and depth enforcement;
- selected and skipped task persistence with reasons;
- disabled agents never selected;
- call cap and dollar budget enforcement;
- no-change termination with zero provider calls;
- per-provider 5-10 RPM validation, queueing, retries, and trace metadata;
- encrypted storage, masked settings responses, key preservation, and legacy
  key migration;
- project ownership rejection for runs, cycles, outputs, questions, and
  answers;
- one Story Bible rebuild per cycle;
- bounded active/stale memory versions;
- migration and required index verification.

Frontend tests:

- inspector renders selected, skipped, reason, graph order, status, and stop
  reason;
- provider settings render configured state without secret values;
- Zustand/API synchronization uses the new plan contract.

Playwright:

- create "The Ashes of Valeria";
- run a premise cycle;
- modify protagonist and verify character graph selection;
- modify world detail and verify world graph selection;
- submit a no-op and verify no-change termination;
- inspect the plan in the workspace;
- compute total cycles, calls, average agents/cycle, skip percentage, budget,
  and rate-limit compliance;
- assert average agents per cycle is below five and call count is at least 50%
  lower than the old 12-agent-per-cycle baseline.

Final verification:

- full backend suite;
- full frontend suite;
- production frontend build;
- Playwright suite;
- migration verification;
- active-path proof that normal cycles no longer default to all 12 agents.

## Rollback Plan

1. Keep the previous `NarrativeStudioService` artifact-writing methods intact
   during Phase 1A so persisted narrative documents remain readable.
2. Roll back application code to the pre-Phase 1A workflow entry point if
   orchestration activation must be disabled.
3. Leave `orchestration_plans` and `orchestration_tasks` in place; they are
   additive audit records and do not alter existing artifact schemas.
4. Keep new indexes unless a measured regression identifies a specific index;
   indexes can be dropped independently by name.
5. Encrypted provider keys must not be rolled back to plaintext. A code rollback
   must retain the compatible decryption reader or require providers to be
   reconfigured.
6. Memory cleanup is intentionally bounded and non-destructive to the active
   version. Rollback can ignore `source_version` and `active`, but should retain
   the new retrieval filter only if the migration has already marked versions.
7. If a cycle fails after plan creation, mark the plan and active task failed,
   leave unstarted tasks skipped with the stop reason, and retain all records
   for diagnosis.

## Production Acceptance Gates

Phase 1A is complete only when:

- `/run` and `/cycle` use `OrchestrationServiceV2`;
- no-change execution performs zero agent/provider calls;
- disabled agents are never selected;
- call, depth, cost, and provider-rate limits are enforced;
- every planning agent has a persisted run or skip reason for each plan;
- API keys are encrypted at rest and absent from API responses;
- child resources are project-owned in API queries;
- Story Bible aggregation occurs once per completed cycle;
- memory source versions remain bounded;
- required migrations and indexes are verified;
- the Ashes of Valeria simulation meets the call-reduction targets;
- backend tests, frontend tests, production build, and Playwright pass.
