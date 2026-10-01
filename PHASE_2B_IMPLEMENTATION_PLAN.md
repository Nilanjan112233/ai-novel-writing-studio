# NovelForge Narrative Studio V2 - Phase 2B Implementation Plan

Plan date: 2026-06-14

Source of truth:

- `PRODUCTION_ARCHITECTURE_AUDIT.md`
- `DATABASE_MODEL_AUDIT.md`
- `AGENT_ARCHITECTURE_AUDIT.md`
- `PHASE_1A_COMPLETION_REPORT.md`
- `PHASE_1B_COMPLETION_REPORT.md`
- `PHASE_2A_IMPLEMENTATION_PLAN.md`
- `PHASE_2A_COMPLETION_REPORT.md`
- `PHASE_2A_E2E_RESULTS.md`

Scope: Controlled scene and chapter draft generation only. This phase adds
`SceneWriterAgent` and `ChapterAssemblerAgent`. It does not add EditorAgent,
DialogueAgent, RevisionAgent, LineEditorAgent, ManuscriptAgent,
BookWriterAgent, full-manuscript generation, or autonomous writing.

## Current Architecture Summary

Phase 1A owns production execution through the demand-driven
`OrchestrationServiceV2`, with persisted plans/tasks, bounded graph traversal,
provider rate limiting, call/cost/depth limits, agent enablement, and
no-change termination.

Phase 1B added deterministic readiness plus the knowledge, timeline,
progression, artifact, foreshadow, and bounded-memory ledgers.

Phase 2A added deterministic arc maturity, configurable checklists, typed arc
dependencies, current/next/future focus, chapter plans, Scene Plan V2,
progression/evolution histories, `StoryDevelopmentAgent`, Arc Development
Workspace, and Story Room.

The current drafting surface is intentionally incomplete:

- `scene_drafts` and `continuity_reports` are read by the Story Bible but have
  no production write authority;
- `/draft-scenes` still means “run ScenePlannerAgent”, not generate prose;
- the frontend has a legacy `SceneDraft` type and Scene Planning panel but no
  review/version workflow;
- no chapter draft collection or assembler exists;
- no deterministic draft validation service exists;
- no version lineage, active-version, rollback, or approval contract exists;
- the global Narrative Studio prompt still forbids all prose;
- orchestration knows scene-plan changes but has no drafting domains.

## Problems To Resolve

1. Draft eligibility is not enforced at scene/chapter ownership boundaries.
2. Generated prose has no immutable version lineage.
3. Draft approval has no deterministic continuity gate.
4. Existing continuity records have no draft subject or violation taxonomy.
5. A chapter assembler could invent, omit, reorder, or rewrite scenes unless
   its authority is structurally constrained.
6. Regeneration and rollback are not represented.
7. Draft review actions are absent from Story Room and Arc Workspace.
8. Dynamic orchestration cannot select drafting agents from draft events.
9. The legacy `/draft-scenes` name is ambiguous and must not become a bypass.

## Proposed Architecture

### Authority Boundary

Planning records remain authoritative:

- readiness and arc development reports;
- arc dependencies;
- chapter and scene plans;
- knowledge entries;
- timeline entries;
- character and power progression;
- artifacts;
- foreshadowing.

Drafts consume those records and never update them. Generated prose and
generation claims are derivative evidence only.

### Drafting Service

Add `DraftingService`, responsible for:

- project/arc/chapter/scene ownership validation;
- deterministic eligibility preflight;
- explicit one-scene generation;
- explicit chapter assembly;
- immutable content version creation;
- active-version switching;
- approval, rejection, archive, regeneration, and rollback;
- event emission and Story Bible rebuild after mutations.

Direct generation endpoints call explicit agents through the existing provider
gateway, settings, trace, memory, cost, and rate-limit path. They do not create
an unbounded orchestration cycle.

### SceneWriterAgent

The agent receives exactly one approved scene plan and its approved chapter
plan, draftable arc, and linked authoritative context.

It returns:

- `generated_text`;
- a concise generation summary;
- structured continuity claims containing only authoritative IDs and declared
  character/power states;
- generation notes.

The service persists exactly one scene draft version per call. The agent
cannot approve the draft or mutate planning.

### ChapterAssemblerAgent

The agent receives ordered approved active scene drafts for one approved
chapter plan.

It returns transitions only, keyed between adjacent scene draft IDs. The
service constructs the chapter text deterministically:

1. preserve every approved scene text verbatim;
2. preserve approved scene order;
3. insert only returned transitions between adjacent scenes;
4. reject unknown, missing, duplicate, or reordered scene references.

This prevents the assembler from inventing scenes or rewriting scene drafts.

### Versioning

Add versioned `scene_drafts` and `chapter_drafts`.

Scene draft identity:

- stable `draft_id` for the version record;
- `scene_id`, `chapter_plan_id`, and `arc_id`;
- monotonically increasing `version_number` per project/scene;
- optional `parent_version_id`;
- `active` flag;
- status: `draft`, `review`, `approved`, `rejected`, or `archived`;
- immutable `generated_text`, generation metadata, generated-by agent, and
  continuity claims;
- change reason and timestamps.

Chapter drafts use the same model, keyed by chapter plan, and also store the
ordered source scene draft IDs and transition records.

New generation or regeneration creates a new record and deactivates the prior
active version. Content is never overwritten. Review actions may update
status/timestamps, but not generated text or lineage.

Rollback switches the selected historical version to active after ownership
and validation checks. It does not delete newer versions.

### Deterministic Draft Validation

Add `DraftValidationService`. It performs no provider calls.

Pre-generation checks:

- arc exists and evaluates as draftable;
- readiness is READY;
- maturity threshold is satisfied;
- blocking dependencies are satisfied;
- chapter plan belongs to the arc and is approved;
- scene plan belongs to the chapter and arc and is approved;
- scene ordering is valid.

Post-generation scene checks:

- draft membership and active lineage;
- non-empty generated text;
- every claimed knowledge, artifact, timeline, foreshadow, progression, and
  dependency ID belongs to the project and allowed scene/arc context;
- required plan-linked IDs are represented in continuity claims;
- undeclared power changes fail;
- character claims are limited to the scene focus/progression records.

Post-assembly checks:

- all chapter scene plans are represented once and in order;
- every source scene draft is active and approved;
- each approved scene text occurs verbatim and in order;
- transitions occur only between adjacent approved scenes;
- chapter claims are the union of source scene claims;
- no planning records are mutated.

Validation result:

- `PASS`: no violations;
- `WARNING`: non-blocking omissions or advisory continuity concerns;
- `FAIL`: ownership, authority, ordering, contradiction, or undeclared-state
  violations.

Drafts with `FAIL` cannot enter `approved`.

### Continuity Reports

Use the existing `continuity_reports` collection as the Phase 2B authority,
with new draft-scoped records:

- stable `report_id`;
- subject type (`scene_draft` or `chapter_draft`);
- subject ID and version;
- project, arc, chapter, and optional scene identity;
- validation stage (`pre_generation`, `post_generation`, `approval`);
- result (`PASS`, `WARNING`, `FAIL`);
- missing knowledge;
- contradictions;
- artifact, timeline, character, power, dependency, and foreshadow violations;
- chapter membership and scene ordering violations;
- warnings, evidence, and timestamps.

A report is generated after every draft and immediately before approval.

### Approval Workflow

Allowed status transitions:

- `draft` -> `review`, `rejected`, or `archived`;
- `review` -> `approved`, `rejected`, or `archived`;
- `approved` -> `archived`;
- `rejected` -> `archived`;
- rollback may reactivate any non-archived historical version.

Generation never sets `approved`. Approval is a user action and requires a
fresh non-FAIL report.

Regeneration creates a new `draft` version with a required change reason and a
parent reference. Rejection preserves the version. Archive removes it from the
active review queue without deletion.

### Dynamic Orchestration

Add drafting domains without restoring a static pipeline:

- approved scene-plan changes may select `SceneWriterAgent`;
- scene-draft approval changes may select `ChapterAssemblerAgent`;
- draft validation failures select only agents implicated by violation types,
  including `KnowledgeAgent` and `StoryDevelopmentAgent`;
- unrelated planning or world changes skip drafting agents;
- direct generation remains one explicit agent call, while normal cycles retain
  existing limits and skip reasons.

The drafting agents have no outgoing graph edges that can create loops.

### Story Room And Arc Workspace

Add a Draft Review Queue showing:

- draft/review/approved/rejected/archived counts;
- active versions;
- validation result and continuity warnings;
- approve, reject, regenerate, archive, and rollback actions;
- generation history and parent lineage.

Extend Arc Development Workspace with a Drafting tab containing:

- chapter draft status;
- scene draft status;
- generate actions gated by approved plans;
- continuity reports;
- review actions;
- version history.

Story Room receives draft queue, review queue, continuity warnings, approval
status, and generation history projections.

## Database Changes

Add:

- `chapter_drafts`

Formalize existing:

- `scene_drafts`
- `continuity_reports`

Indexes:

- unique scene draft ID by project;
- unique scene/version number by project;
- scene lookup by project/arc/chapter/scene/status/active;
- scene lineage by project/scene/parent/version;
- unique chapter draft ID by project;
- unique chapter/version number by project;
- chapter lookup by project/arc/chapter/status/active;
- chapter lineage by project/chapter/parent/version;
- unique continuity report ID by project;
- continuity lookup by project/subject/version/stage/result;
- review queue lookup by project/status/active/created time.

No planning collection is replaced or made derivative from draft text.

## API Changes

Add project-owned endpoints for:

- generate one scene draft;
- regenerate one scene draft;
- generate one chapter draft;
- scene and chapter draft history;
- approve, reject, archive, and move to review;
- rollback active version;
- continuity report retrieval and revalidation;
- draft review queue.

All endpoints validate project, arc, chapter, scene, draft, and linked
authoritative records. The legacy `/draft-scenes` endpoint remains planning
only and is not a prose-generation bypass.

## UI Changes

Add:

- Draft Review Queue component;
- Arc Development Drafting tab;
- per-scene generation and validation state;
- per-chapter assembly state;
- status actions and rejection/change reasons;
- active version and version history;
- continuity category summaries.

Reuse the existing workspace, Story Room, Zustand store, SSE refresh, and
Story Bible aggregation.

## Migration Plan

1. Add idempotent Phase 2B migration and standalone runner.
2. Normalize any legacy scene draft records into inactive archived history
   unless they already have full project/scene/version lineage.
3. Add missing status, active, version, generation metadata, and timestamps
   without modifying generated text.
4. Normalize legacy continuity reports as non-draft historical reports.
5. Install scene draft, chapter draft, and continuity indexes.
6. Add the two agent assignments without overwriting provider/model choices.
7. Leave Phase 2A planning and legacy scene records intact.

## Test Plan

Backend:

- eligibility denial for non-draftable arcs and unapproved chapter/scenes;
- project/arc/chapter/scene/draft ownership validation;
- one-scene-per-call enforcement;
- immutable content and monotonic versions;
- regeneration parent lineage and required reason;
- rollback active-version behavior;
- legal review status transitions and no automatic approval;
- deterministic PASS/WARNING/FAIL categories;
- FAIL approval denial;
- exact chapter scene membership and order;
- approved-scenes-only assembly;
- verbatim scene preservation with transitions;
- no planning artifact mutation;
- dynamic selection and skip reasons for both new agents;
- migration idempotency and index verification.

Frontend:

- review queue grouping and validation badges;
- generation and assembly actions;
- approval/rejection/archive/regeneration controls;
- version history and rollback;
- Arc Development Drafting tab;
- Story Room draft summaries;
- existing Phase 1A-2A regressions.

Playwright and real Gemini:

1. Create `The Crown of Emberfall`.
2. Prepare Arc 1 to deterministic maturity above 85 and draftable.
3. Create three approved chapter plans and six approved scene plans.
4. Generate six scene drafts one at a time using real Gemini.
5. Verify six post-generation continuity reports are non-FAIL.
6. Move each scene to review and approve it manually.
7. Assemble three chapter drafts from ordered approved scenes.
8. Verify chapter reports PASS and scene text is preserved.
9. Regenerate one scene, verify lineage, then rollback.
10. Keep Arc 2 partial and Arc 3 placeholder; verify both return 409 for
    generation.
11. Verify drafting agents are selected for drafting changes and skipped for
    unrelated changes.

Final gates:

- backend suite;
- frontend suite;
- production build;
- complete Playwright suite;
- real `gemini-3.1-flash-lite` scene and chapter generation;
- migration/index verification;
- plaintext credential scan;
- forbidden-agent scan;
- no planning truth mutation.

## Rollback Plan

1. Stop generation requests and active cycles.
2. Deploy Phase 2A backend and frontend together.
3. Retain additive draft collections and indexes.
4. Disable `SceneWriterAgent` and `ChapterAssemblerAgent`.
5. Restore the Phase 2A Scene Planning panel as the only drafting-adjacent
   surface.
6. Keep all draft versions as inactive historical data.
7. Restore the database backup only if an external consumer cannot tolerate
   additive draft fields or collections.

## Acceptance Gates

Phase 2B is complete only when:

- scene drafts derive only from approved plans in a draftable arc;
- chapter drafts derive only from approved active scene drafts;
- versions are monotonic and content history is preserved;
- regeneration and rollback work;
- every draft has deterministic continuity validation;
- FAIL drafts cannot be approved;
- no draft is automatically approved;
- planning truth remains unchanged by generation;
- Arc 2 and Arc 3 remain blocked;
- dynamic orchestration remains bounded and demand-driven;
- backend, frontend, build, Playwright, migration, and real Gemini checks pass;
- no forbidden writing or manuscript agents are introduced.
