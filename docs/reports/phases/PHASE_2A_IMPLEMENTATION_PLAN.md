# NovelForge Narrative Studio V2 - Phase 2A Implementation Plan

Plan date: 2026-06-14

Source of truth:

- `PRODUCTION_ARCHITECTURE_AUDIT.md`
- `DATABASE_MODEL_AUDIT.md`
- `AGENT_ARCHITECTURE_AUDIT.md`
- `PHASE_1A_COMPLETION_REPORT.md`
- `PHASE_1B_IMPLEMENTATION_PLAN.md`
- `PHASE_1B_COMPLETION_REPORT.md`
- `PHASE_1B_E2E_RESULTS.md`

Scope: Arc-Centric Story Development only. This phase does not add prose
generation, WriterAgent, EditorAgent, DialogueAgent, chapter text, scene text,
or a prose editor.

## Current Architecture Summary

Phase 1A routes production cycles through `OrchestrationServiceV2`. It detects
typed project events, traverses a code-owned impact graph, persists selected
and skipped agents, enforces rate/cost/call/depth limits, and executes only the
selected agent specifications.

Phase 1B added deterministic readiness, stable arc IDs, an approval lifecycle,
Timeline V2 uncertainty, character progression, typed knowledge, foreshadowing,
artifacts, and bounded agent memory. Readiness is arc-scoped, so an approved
current arc can be eligible while future arcs remain incomplete.

The remaining workflow is still collection-driven:

- arc approval and readiness do not measure development maturity;
- no explicit current/next/future focus model exists;
- no configurable arc development checklist exists;
- arc dependencies are loose string arrays;
- chapter plans do not exist;
- ScenePlanner writes legacy `scene_registry` records without a V2 chapter
  relationship or full change-impact structure;
- progression has only current/desired state rather than start/midpoint/end;
- power progression is embedded in unrelated records;
- knowledge, foreshadowing, and artifacts have state but no ordered evolution
  chains;
- no single arc development workspace or story-room projection exists;
- no agent owns selected-arc development proposals.

## Problems To Resolve

1. Readiness alone can mark an arc eligible without proving development depth.
2. Arc lifecycle vocabulary does not represent idea through draftable maturity.
3. Development criteria are not configurable per project or arc.
4. Only one arc should normally be active, but this is not enforced.
5. Activation does not validate reveal, artifact, progression, knowledge, or
   prior-arc dependencies.
6. Chapter and scene planning have no normalized, arc-owned data model.
7. Character and power changes cannot be inspected across arc start, midpoint,
   and end.
8. Foreshadow, artifact, and knowledge changes cannot be followed as chains.
9. The orchestrator cannot prioritize current, next, and future arcs.
10. The workspace scatters development context across many sections.

## Proposed Architecture

### Arc Development Lifecycle

Normalize `story_arcs.development_status` to:

- `idea`
- `discussion`
- `outline`
- `development`
- `approved`
- `active`
- `draftable`
- `completed`
- `archived`

The existing Phase 1B `approval_status` remains as a compatibility projection
during migration. Deterministic transition validation will prevent invalid
skips and ensure only one non-archived arc is normally `active`.

`draftable` requires:

- deterministic Phase 1B readiness `READY`;
- maturity score at or above the configured threshold;
- all required arc checklist items satisfied;
- activation dependencies satisfied;
- approved or active arc authority.

Future arcs may remain at any earlier lifecycle state and do not block the
current arc.

### Deterministic Arc Maturity

Add `ArcDevelopmentService`, a non-AI authority that calculates a 0-100 score
from persisted evidence. The dimensions are:

- goal clarity;
- conflict clarity;
- stakes clarity;
- character growth;
- progression coverage;
- knowledge coverage;
- foreshadow coverage;
- artifact coverage;
- timeline coverage;
- mystery coverage;
- resolution planning.

Each dimension has a configurable weight stored with checklist configuration.
Scoring uses concrete records and satisfied checklist items. It does not call a
provider and does not infer approval from AI output.

The service returns:

- total score;
- per-dimension scores and evidence;
- blockers;
- unsatisfied required items;
- dependency validation;
- focus role;
- lifecycle and draftable eligibility.

The calculated score and timestamp are persisted on the arc.

### Configurable Checklists

Add `arc_checklists`.

Every row is project-owned and arc-owned, with a stable item ID, free-form
category/title/description, priority (`required`, `recommended`, `optional`),
status, score dimension, weight, evidence, source, and timestamps.

Templates are data, not a closed enum. A deterministic seed service creates a
default set only when an arc has no checklist. Users can add, edit, remove, and
reweight items.

AI may propose checklist work, but only approved/completed user-authoritative
items satisfy required maturity gates.

### Arc Focus And Dependencies

Add explicit `focus_role` on arcs:

- `current`
- `next`
- `future`

At most one non-archived arc may be `current`. Activating an arc assigns
`current`, demotes the prior current arc appropriately, and derives next/future
roles by order.

Add `arc_dependencies` with stable dependency IDs and typed requirements:

- `requires_arc`
- `follows_arc`
- `depends_on_reveal`
- `depends_on_artifact`
- `depends_on_character_growth`
- `depends_on_knowledge_state`

Each dependency stores the target/link identity, required state, blocking flag,
status, evidence, and validation metadata. Activation and draftable transitions
must fail while a blocking dependency is unsatisfied.

### Chapter And Scene Planning

Add `chapter_plans` with stable chapter-plan IDs, chapter number, arc ID,
purpose, conflict, character focus, knowledge changes, artifact links,
foreshadow links, timeline links, and planning status:

- `planned`
- `approved`
- `drafted`
- `completed`

`drafted` remains a lifecycle marker for later phases; Phase 2A never creates
chapter text.

Add `scene_plans` as the V2 scene authority. Each scene is linked to a chapter
plan and contains purpose, conflict, outcome, character change, knowledge
change, foreshadow links, artifact interactions, timeline impact, order, and
planning status. No prose fields are permitted.

The existing ScenePlannerAgent is updated to produce V2 planning proposals and
persist only `scene_plans`. Legacy `scene_registry` remains for rollback.

### Development Ledgers

Extend `character_progressions` in place with:

- arc start state;
- arc midpoint state;
- arc end state;
- emotional growth;
- maturity growth;
- power growth;
- relationship growth;
- belief changes;
- goal changes.

Add `power_progressions` with character/arc identity, starting and ending
power, new/mastered abilities, limitations, costs, and future evolution.
Validation requires a stated progression path for a power increase and rejects
an ending state that has no supporting change evidence.

Extend Phase 1B records with ordered evolution events:

- `foreshadow_chains`: seed, development, reinforcement, and payoff nodes
  linked to the existing foreshadow registry.
- `artifact_evolutions`: discovery, ownership, usage, awakening, hidden
  ability, destruction, transfer, and relevance events.
- `knowledge_evolutions`: discovery, misunderstanding, confirmation, reveal,
  and twist events linked to knowledge entries, arcs, and optional chapters.

The Phase 1B registries remain the current-state authority; evolution
collections provide history and traceability.

### StoryDevelopmentAgent

Add only `StoryDevelopmentAgent`.

It receives one selected arc plus its readiness, maturity, checklist,
dependencies, chapter/scene plans, progression, knowledge, foreshadowing,
artifacts, and bounded memory.

It returns development proposals only:

- arc refinements;
- checklist proposals;
- chapter-plan proposals;
- scene-plan proposals;
- progression proposals;
- knowledge/foreshadow/artifact evolution proposals;
- unresolved development questions.

It cannot approve checklist items, satisfy dependencies, advance lifecycle, or
write prose. Deterministic services retain authority over scoring and gates.

### Dynamic Orchestration

Extend the Phase 1A/1B graph:

- arc-development and checklist changes select StoryDevelopmentAgent and
  affected arc/pacing analysis;
- chapter-plan changes select StoryDevelopmentAgent, ArcArchitectAgent, and
  PacingAgent;
- scene-plan changes select ScenePlannerAgent only when explicitly requested,
  plus affected progression/knowledge analysis when linked state changes;
- power progression selects PowerSystemAgent and CharacterJourneyAgent;
- knowledge evolution selects KnowledgeAgent and affected mystery/arc work;
- foreshadow chains select MysteryAgent and ArcArchitectAgent;
- artifact evolution selects only affected world/power/character planning;
- focus changes prioritize the current arc in context and agent instructions.

No graph edge may cause unbounded execution. Existing call, depth, cost,
rate-limit, enablement, and no-change termination controls remain authoritative.

### Story Room And Arc Workspace

Add an Arc Development Workspace that assembles one arc's:

- focus and lifecycle;
- maturity score and dimensions;
- checklist and blockers;
- dependencies;
- readiness;
- chapter plans;
- scene plans;
- character and power progression;
- knowledge evolution;
- foreshadow chains;
- artifact evolution.

Add a Story Room projection that displays active discussions, open planning
items, blocked items, deterministic suggestions, and pending agent proposals.
It reuses existing discussion records rather than creating a second discussion
system.

## Database Changes

Add:

- `arc_checklists`
- `arc_dependencies`
- `chapter_plans`
- `scene_plans`
- `power_progressions`
- `foreshadow_chains`
- `artifact_evolutions`
- `knowledge_evolutions`

Normalize:

- `story_arcs`: development status, focus role, maturity score/details,
  maturity threshold, evaluation timestamp;
- `character_progressions`: start/midpoint/end and typed growth fields.

Planned indexes:

- unique checklist identity by project/item ID;
- checklist lookup by project/arc/priority/status/dimension;
- unique dependency identity by project/dependency ID;
- dependency lookup by project/arc/type/status/blocking;
- unique chapter plan ID and unique project/arc/chapter number;
- chapter lookup by project/arc/status/number;
- unique scene plan ID and scene lookup by chapter/order/status;
- unique power progression by project/arc/character;
- unique evolution IDs and ordered lookup by project/parent/arc/chapter/order;
- arc focus/status/order lookup with a partial unique current-arc index where
  supported by MongoDB.

## API Changes

Add project-owned APIs for:

- arc development reports and evaluation;
- arc lifecycle/focus activation;
- checklist CRUD and default seeding;
- dependency CRUD and validation;
- chapter-plan CRUD;
- Scene Plan V2 CRUD and explicit ScenePlanner execution;
- extended character progression;
- power progression;
- knowledge, foreshadow, and artifact evolution;
- Story Room projection.

All child IDs and cross-ledger links must be validated against the same
project. No endpoint accepts or returns chapter prose.

## UI Changes

Add:

- Arc Development workspace;
- maturity score with dimension breakdown;
- checklist controls and blockers;
- dependency validation;
- chapter and scene plan cards;
- progression/evolution panels;
- Story Room view.

The existing Arc Board remains the navigation entry and gains focus/maturity
indicators. The existing workspace shell and orchestration inspector remain.

## Migration Plan

1. Add an idempotent Phase 2A migration and standalone runner.
2. Normalize existing arcs to a development status and focus role.
3. Assign one current arc only when an existing active arc is unambiguous.
4. Seed configurable default checklists only for existing non-archived arcs
   without checklist rows.
5. Normalize character progression fields without deleting legacy fields.
6. Migrate eligible legacy `scene_registry` planning records into
   `scene_plans`, preserving source IDs for deduplication.
7. Install Phase 2A indexes.
8. Leave Phase 1B collections and legacy scene records intact.

## Test Plan

Backend:

- deterministic maturity calculation and weighted dimensions;
- configurable checklist CRUD, seeding, and required gates;
- legal lifecycle transitions and one-current-arc rule;
- dependency validation for each supported dependency type;
- current arc priority and future arc isolation;
- chapter plan and Scene Plan V2 ownership/link validation;
- no prose fields accepted or emitted;
- extended character progression and power jump prevention;
- ordered foreshadow, artifact, and knowledge evolution;
- StoryDevelopmentAgent proposal authority limits;
- dynamic orchestration selection and skip reasons;
- migration idempotency and indexes.

Frontend:

- maturity and lifecycle rendering;
- checklist/blocker interaction;
- chapter and scene plan rendering;
- dependency and progression/evolution panels;
- Story Room active/open/blocked/proposal groups;
- store synchronization and existing workspace regressions.

Playwright and real Gemini:

1. Create `The Last Kingdom of Aether`.
2. Create and focus Arc 1.
3. Satisfy required checklist, readiness, and dependencies.
4. Add complete timeline, chapter, scene, progression, knowledge,
   foreshadowing, artifact, and power planning.
5. Verify deterministic maturity exceeds 85 and only Arc 1 is draftable.
6. Keep Arc 2 between 30 and 70 maturity.
7. Keep Arc 3 as a valid placeholder.
8. Trigger selected-arc development and verify StoryDevelopmentAgent executes.
9. Trigger an unrelated/no-op change and verify StoryDevelopmentAgent skips.
10. Verify no prose, WriterAgent, EditorAgent, or DialogueAgent exists.

Final gates:

- full backend suite;
- full frontend suite;
- production build;
- full Playwright suite;
- real `gemini-3.1-flash-lite` execution;
- migration and index verification;
- plaintext credential and forbidden-agent scans.

## Rollback Plan

1. Stop planning mutations and active cycles.
2. Redeploy Phase 1B backend and frontend together.
3. Retain additive Phase 2A collections and indexes; Phase 1B ignores them.
4. Restore `scene_registry` as the prior scene-planning read path.
5. Keep normalized arc and progression fields; legacy fields remain available.
6. Disable StoryDevelopmentAgent if provider behavior must be isolated.
7. Restore the database backup only if a custom pre-Phase 2A consumer cannot
   tolerate additive arc fields.

## Acceptance Gates

Phase 2A is complete only when:

- deterministic arc maturity and configurable checklists work;
- activation validates dependencies and normally permits one current arc;
- chapter and scene planning contain no prose;
- character and power progression are arc-visible;
- knowledge, foreshadow, and artifact evolution are traceable;
- Arc 1 can exceed 85 and become draftable;
- Arc 2 remains partially developed and Arc 3 remains a placeholder;
- StoryDevelopmentAgent is demand-selected for selected-arc work only;
- the production path remains dynamic and bounded;
- backend, frontend, build, Playwright, migration, and real Gemini checks pass;
- no writing agent or chapter text generation is introduced.
