# NovelForge Narrative Studio Production Audit

Audit date: 2026-06-07

## Executive Result

Status: PASS with documented maintenance warnings.

NovelForge now executes a story-first Narrative Studio workflow:

`Provider-backed agents -> structured artifact processing -> MongoDB -> Story Bible -> SSE refresh -> workspace UI`

The production workspace no longer runs the retired chapter-first LangGraph workflow, renders
hardcoded story artifacts, or exposes raw workflow payloads. A new project completed two real
Gemini cycles, question resolution, canon locking, proposal approval, scene planning, database
validation, and browser validation.

## Workspace Architecture

- `/projects` is a project-only library with create, search, sort, archive, duplicate, and delete.
- `/project/:projectId` is the Narrative Studio workspace.
- The workspace sidebar contains Story Vision, Discussion Room, Characters, World, Power System,
  Factions, Relationships, Plot Threads, Themes, Mysteries, Timeline, Arcs, Questions, AI Insights,
  Drafting, Workflow, and Settings.
- Drafting is secondary to narrative planning.
- Zustand hydrates the workspace from one persisted Story Bible response.
- Project SSE events invalidate and reload the Story Bible without requiring a manual refresh.

## Dependency Map

All workspace sections use `GET /api/projects/{projectId}/story-bible` through
`story_bible_service.rebuild_story_bible`. Section-specific endpoints remain available for API
clients and editing operations, but production page rendering uses the aggregate.

| Page | Route / Component | Primary collection(s) | Agent source | Cache / update path | Result |
| --- | --- | --- | --- | --- | --- |
| Projects | `/projects`, `frontend/app/projects/page.tsx` | `projects` | None | Direct project query; mutation refresh | PASS |
| Story Vision | `/project/:id`, workspace section | `story_visions`, `story_vision_versions` | NarrativeDirectorAgent | Story Bible + SSE; editable/versioned | PASS |
| Discussion Room | `/project/:id`, workspace section | `discussion_messages`, `decision_registry`, `audit_logs` | All studio agents + user | Story Bible + SSE | PASS |
| Characters | `/project/:id`, workspace section | `character_bibles`, `character_journeys` | CharacterJourneyAgent | Story Bible + SSE | PASS |
| World | `/project/:id`, workspace section | `world_bibles` | WorldAgent | Story Bible + SSE | PASS |
| Power System | `/project/:id`, workspace section | `power_systems` | PowerSystemAgent | Story Bible + SSE | PASS |
| Factions | `/project/:id`, workspace section | `factions` | FactionAgent | Story Bible + SSE | PASS |
| Relationships | `/project/:id`, `RelationshipGraph.tsx` | `relationship_graphs` | RelationshipAgent | Story Bible + SSE | PASS |
| Plot Threads | `/project/:id`, workspace section | `plot_threads` | StoryArchitectAgent | Story Bible + SSE | PASS |
| Themes | `/project/:id`, workspace section | `theme_registry` | ThemeAgent | Story Bible + SSE | PASS |
| Mysteries | `/project/:id`, workspace section | `mystery_registry` | MysteryAgent | Story Bible + SSE | PASS |
| Timeline | `/project/:id`, workspace section | `story_timelines` | ArcArchitectAgent | Story Bible + SSE | PASS |
| Arcs | `/project/:id`, workspace section | `story_arcs` | ArcArchitectAgent | Story Bible + SSE | PASS |
| Questions | `/project/:id`, workspace section | `questions`, `decision_registry`, `canon_registry` | QuestionAgent | Story Bible + SSE | PASS |
| AI Insights | `/project/:id`, workspace section | `ai_insights`, `contradiction_reports` | NarrativeDirectorAgent, PacingAgent | Story Bible + SSE | PASS |
| Drafting | `/project/:id`, workspace section | `scene_registry`, `scene_drafts` | ScenePlannerAgent | Explicit late-stage action + SSE | PASS |
| Workflow | `/project/:id`, `WorkflowFlow.tsx` | `runs`, `cycles`, `agent_outputs`, `orchestration_runs` | Actual execution sequence | Story Bible + SSE | PASS |
| Settings | `/settings`, `frontend/app/settings/page.tsx` | `app_settings`, `execution_traces`, model validation collections | Provider/model configuration | Direct settings API | PASS |

## Story Bible

`backend/app/services/story_bible_service.py` is the project aggregation boundary and persists
the aggregate in `story_bibles`.

Included sections:

- Story Vision
- Characters and Character Journeys
- World
- Power System
- Factions
- Relationships
- Plot Threads
- Themes
- Mysteries and foreshadowing
- Timeline events
- Story Arcs
- Questions
- AI Insights
- Drafting plans and drafts
- Canon Registry
- Decision Registry
- Discussion messages and decisions
- Contradiction and continuity reports
- Workflow runs, cycles, outputs, and orchestration summary

Pages do not parse agent prose. Agent responses are validated structured JSON and are transformed
into owned collections before Story Bible rebuild.

## Agent Architecture

The production execution order is dynamic data persisted with each run:

1. NarrativeDirectorAgent: Story Vision and AI Insights
2. StoryArchitectAgent: Plot Threads
3. CharacterJourneyAgent: Characters and Character Journeys
4. WorldAgent: World Bible
5. PowerSystemAgent: Power System
6. FactionAgent: Factions
7. RelationshipAgent: Relationship Graph
8. ThemeAgent: Theme Registry
9. MysteryAgent: Mystery Registry
10. ArcArchitectAgent: Story Arcs and distinct Timeline Events
11. PacingAgent: Pacing analysis in AI Insights
12. QuestionAgent: unresolved discovery Questions

ScenePlannerAgent is invoked explicitly from Drafting after planning data exists.

Each specification declares purpose and structured output schema. Every execution receives:

- Current Story Bible
- Canon Registry
- Decision Registry
- Approved proposals
- Resolved questions
- Retrieved persistent project memory
- Current cycle and provider assignment

Every output records provider, model, tokens, estimated cost, latency, trace ID, cycle, timestamp,
source type, mock usage, fallback usage, and artifact counts.

## Discussion Room

Discussion proposals are persisted cards with summary, reasoning, concerns, recommendation, trace,
and cycle metadata.

- Approve creates an approved decision, canon entry, audit log, Story Bible rebuild, and event.
- Reject stores a rejected decision and reason, rebuilds the Story Bible, and emits an event.
- Modify stores revision history and a child proposal.
- Discuss creates a proposal-linked discussion thread/message.
- Expand stores a queued next-cycle task and parent-child proposal link.
- Canon contradictions block approval and persist a contradiction report.
- The newest cycle is rendered first.

## Canon And Questions

- Approved proposals and answered questions create Decision Registry records.
- Approved facts create Canon Registry entries.
- Agent context loads both registries before every execution.
- Resolved questions are removed from the active queue and deduplicated in future cycles.
- Canon validation compares local factual fragments to avoid broad false-positive negation matches.
- Contradictions are persisted and require resolution before approval.

## Arc, Timeline, Power, Character, And Mystery Models

- Story Arcs store goal, estimated chapters, events, conflicts, payoffs, mysteries, character
  growth, dependencies, and completion status.
- Timeline stores actual dated/aged events, discoveries, revelations, relationship milestones,
  payoffs, participants, consequences, dependencies, and owning arc.
- Power System stores ranks, levels, cultivation, skills, classes, evolution paths, concept tree,
  limitations, resources, costs, compatibility rules, progression logic, and curve.
- Character Journey stores goals, fears, beliefs, growth, relationships, status, future plans,
  payoffs, timeline, and agent notes.
- Mystery Registry stores question, truth, known/hidden clues, red herrings, reveal target, and status.

## Mock And Raw Data Audit

Production source scan result:

- No mock/demo/sample/fallback story datasets in production pages, APIs, stores, or services.
- No hardcoded workflow agent graph in the UI.
- No production raw JSON `<pre>` or `JSON.stringify` payload renderer.
- No automatic environment-level mock story generator.
- Explicit mock provider behavior remains only for isolated automated tests.
- Full execution mode rejects mock assignments and does not silently fall back to mock output.

## Real Provider Verification

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

Test project:

- Title: The Last Concept Gardener
- Premise: A reincarnated boy develops a subconscious System that grows concepts as living powers.
- Project ID: `6a2480b3cf1dfe8653557be7`

Verified:

- Provider/model validation succeeded.
- Cycle 1 completed with 12 real agent outputs.
- Questions were answered and locked into decision/canon registries.
- Cycle 2 completed and consumed prior decisions.
- 24 total real agent outputs were persisted across cycles 1 and 2.
- Narrative Director, Power System, and Faction proposals were approved.
- Real ScenePlanner output created two persisted scene plans.
- All real outputs report Gemini, the configured model, source `real_ai`, and `mock_used=false`.
- A transient Gemini 503 was recovered by bounded provider retry.

## Database Audit

Latest project audit status: PASS

Findings: none

| Collection | Count |
| --- | ---: |
| story_bibles | 1 |
| canon_registry | 5 |
| decision_registry | 5 |
| discussion_messages | 25 |
| story_visions | 1 |
| story_arcs | 3 |
| power_systems | 1 |
| character_bibles | 2 |
| character_journeys | 2 |
| world_bibles | 1 |
| mystery_registry | 3 |
| ai_insights | 1 |
| factions | 2 |
| relationship_graphs | 1 |
| plot_threads | 2 |
| theme_registry | 1 |
| story_timelines | 4 |
| questions | 3 |
| scene_registry | 2 |
| runs / cycles / orchestration_runs | 2 / 2 / 2 |
| agent_outputs | 24 |
| contradiction_reports | 0 |

The project audit checks project references, duplicate cycle artifacts, stale mock records, invalid
cycle metadata, missing provider traces, and orphaned records.

## Realtime And Cycle Validation

- Agent completion persists Mongo artifacts, rebuilds Story Bible, and emits a project SSE event.
- Zustand reloads the Story Bible on each `project_update`.
- Workflow/cycle actions do not depend on periodic polling.
- Direct verification reported Story Bible cycle `2`, persisted cycles `1,2`, and discussion cycles
  `1,2`.
- The workspace action now displays the real next cycle number.

## Test Results

- Backend: `37 passed, 7 skipped`
- Frontend unit tests: `36 passed`
- Next.js production build: PASS
- Playwright: `17 passed, 1 skipped`
- Health endpoint: PASS (`healthy`)
- Projects page HTTP check: PASS (`200`)
- Database production audit: PASS, zero findings
- Real Gemini lifecycle: PASS

The seven backend skips are tests for retired Intake/Brainstorm/Critic/Revision chapter-first mock
execution. Their non-execution graph structure checks remain, while current Narrative Studio agents
are covered by production-integrity tests and real-provider E2E.

## Visual Validation

Playwright checked Projects, Workspace, Discussion, Settings, Workflow, Timeline, Characters, World,
Power System, Relationships, Factions, Plot Threads, Themes, Mysteries, Arcs, Questions, AI Insights,
and Drafting.

Validated widths: 1280, 1440, 1920, and 2560 pixels.

Checks include horizontal overflow, clipped actions, hidden controls, raw JSON, provider metadata,
real artifact presence, workflow nodes, and relationship graph entities.

Screenshots:

- `test-results/real-discussion-room.png`
- `test-results/real-relationships.png`
- `test-results/real-workflow.png`

## Updated File Tree

Key production additions and changes:

```text
backend/app/
  api/
    data.py
    projects.py
    settings.py
    workflow.py
  services/
    canon_service.py
    canon_validation_service.py
    database_audit_service.py
    memory_retrieval_service.py
    narrative_studio.py
    project_event_service.py
    provider_gateway.py
    settings_service.py
    story_bible_service.py
    workflow_persistence.py

frontend/
  app/
    projects/page.tsx
    project/[projectId]/page.tsx
    settings/page.tsx
  components/
    RelationshipGraph.tsx
    WorkflowFlow.tsx
  store/
    projectStore.ts

e2e/
  dashboard.spec.ts
  real-provider.spec.ts
  settings.spec.ts
  ui-stability.spec.ts
  workflow.spec.ts
```

## Production Readiness Matrix

Pages: all PASS.

Current production agents: all PASS.

Workflow persistence, cycle metadata, Story Bible aggregation, canon enforcement, question
resolution, proposal actions, provider tracing, SSE synchronization, database audit, build,
healthcheck, and visual stability: PASS.

## Maintenance Warnings And Roadmap

1. Migrate FastAPI startup/shutdown handlers to lifespan APIs.
2. Migrate deprecated Pydantic class config and JSON encoders before Pydantic 3.
3. Remove the retired chapter-first LangGraph modules entirely after any external callers are
   confirmed migrated.
4. Add dedicated ContinuityAgent and ReviewAgent passes when chapter drafting becomes a production
   workflow; continuity reports and review collections are already represented in the Story Bible.
5. Add database indexes for very large multi-book projects after production query telemetry is
   available, especially `(project_id, cycle_generated)` and `(project_id, updated_at)`.

## Assumptions

- MongoDB is the durable system of record; Chroma remains retrieval support rather than page state.
- Cost values are provider/model estimates when the upstream API does not return monetary cost.
- A Story Bible rebuild is intentionally performed after each agent so later agents can consume
  earlier artifacts from the same cycle.
- Drafting remains user-triggered and late-stage rather than part of every planning cycle.
