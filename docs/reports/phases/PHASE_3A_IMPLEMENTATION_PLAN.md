# NovelForge Narrative Studio V2 - Phase 3A Implementation Plan

Plan date: 2026-06-14

## Source Of Truth

- `PRODUCTION_ARCHITECTURE_AUDIT.md`
- `DATABASE_MODEL_AUDIT.md`
- `AGENT_ARCHITECTURE_AUDIT.md`
- `PHASE_1A_COMPLETION_REPORT.md`
- `PHASE_1B_COMPLETION_REPORT.md`
- `PHASE_2A_COMPLETION_REPORT.md`
- `PHASE_2B_COMPLETION_REPORT.md`
- `PHASE_2B_E2E_RESULTS.md`

## Scope

Phase 3A adds an Editorial Intelligence Layer:

- `EditorAgent`
- `DialogueAgent`
- `RevisionAgent`
- deterministic `EditorialService`
- editorial reports and scores
- revision branches and immutable revision versions
- Editorial Dashboard and Revision Workspace
- editorial and revision queues in Story Room

It does not add manuscript or book generation, publishing/export, autonomous
rewriting, autonomous approval, `BookWriterAgent`, `ManuscriptAgent`, or
`PublishingAgent`.

Approved Phase 2B drafts remain authoritative. Editorial outputs are
derivative findings and proposals. They cannot silently modify approved
content.

## Current Architecture

Phase 2B provides approved scene and chapter drafts, deterministic continuity
validation, immutable versions, rollback, explicit author review, provider
traces, and one-agent demand-driven orchestration.

The current system has no first-class editorial report, quality score,
revision branch, comparison, or editorial queue. Existing pacing analysis is
planning-focused and does not evaluate approved prose. There is also no
governed route from an editorial recommendation to an alternative revision
version.

## Problems

The system cannot currently:

- assess style, voice, dialogue, pacing, emotional progression, or objective
  fulfillment for approved prose;
- calculate scene, chapter, or arc editorial readiness;
- explain editorial blockers with evidence;
- preserve alternative revision proposals without replacing approved drafts;
- compare revision branches and lineage;
- route editorial work through bounded dynamic orchestration;
- expose editorial and revision queues to authors.

## Authority Model

`EditorialService` is the deterministic authority for:

- draft and branch ownership validation;
- editorial workflow and report persistence;
- deterministic score calculation;
- branch lifecycle and immutable lineage;
- revision comparison;
- queue and dashboard projections.

Agents may produce observations, evidence, recommendations, and revision
proposal text. They cannot:

- approve reports, drafts, branches, or revisions;
- replace or mutate an approved Phase 2B draft;
- alter planning truth;
- publish or assemble a manuscript.

## Editorial Analysis

`EditorAgent` reviews one approved scene or chapter draft and returns:

- style findings;
- voice findings;
- pacing findings;
- emotional progression findings;
- objective-fulfillment findings;
- evidence and recommendations.

`DialogueAgent` reviews the same immutable draft and returns:

- realism;
- distinctiveness;
- exposition-in-dialogue;
- speaker differentiation;
- conversation flow;
- evidence and recommendations.

The deterministic service normalizes findings, bounds dimension scores to
0-100, records blockers, and calculates:

- scene score from style, dialogue, pacing, objective fulfillment, and
  emotional progression;
- chapter score from source-scene quality, pacing, continuity, emotional
  progression, and objective fulfillment;
- arc score from approved chapter quality, progression, consistency, pacing,
  and payoff readiness.

Agent scores are evidence inputs, not direct approval authority.

## Revision Branching

A revision branch references one approved source scene or chapter draft.
Branches preserve source identity and may have a parent branch.

Branch statuses:

- `draft`
- `review`
- `approved`
- `rejected`
- `archived`

`RevisionAgent` consumes the approved source, selected editorial reports, and
an author change request. It creates a new immutable `revision_versions`
record. It cannot update the source draft or automatically approve the
branch.

Every revision version has a monotonically increasing version number,
optional parent revision, generated text, generation metadata, change reason,
and creation timestamp. Branch approval is an author action and still does
not replace the approved Phase 2B draft.

## Dynamic Orchestration

Explicit editorial actions create persisted Phase 1A plans:

- editorial review selects only `EditorAgent`;
- dialogue review selects only `DialogueAgent`;
- revision proposal selects only `RevisionAgent`.

All other agents are recorded as skipped with reasons. Existing enablement,
cost, call, depth, rate-limit, retry, trace, and no-change controls remain in
force. Ordinary planning changes do not invoke editorial agents. Editorial
actions never enqueue drafting agents recursively.

## Database Changes

Add only:

- `editorial_reports`
- `revision_branches`
- `revision_versions`
- `editorial_scores`

Indexes:

- `editorial_reports_project_subject`
- `editorial_reports_type_score`
- `revision_branches_project_branch`
- `revision_branches_source`
- `revision_versions_branch_version`
- `editorial_scores_subject`
- `editorial_scores_project_type`

The Phase 3A migration normalizes compatible legacy records, preserves all
Phase 2B data, installs indexes, records a migration version, and is
idempotent.

## API Changes

Project-owned endpoints will support:

- scene, chapter, and arc editorial review;
- dialogue review;
- editorial report and score history;
- editorial dashboard and queues;
- revision branch creation;
- revision proposal generation;
- branch review, approval, rejection, and archive;
- branch lineage and revision comparison.

Every endpoint validates project, draft, branch, report, arc, chapter, and
scene ownership before provider execution.

## UI Changes

Add:

- Editorial Dashboard with scores, blockers, findings, evidence, and
  recommendations;
- Revision Workspace with branches, lineage, comparisons, versions, and
  author-controlled statuses;
- editorial status on scene/chapter draft cards;
- editorial and revision queues in Story Room;
- a minimal Editorial section in the existing project workspace.

No workspace redesign is included.

## Migration Plan

Create:

- `backend/app/migrations/phase_3a.py`
- `backend/scripts/run_phase_3a_migration.py`

The migration is additive. Routine rollback retains collections, indexes,
reports, scores, branches, and revisions.

## Test Plan

Backend tests cover:

- deterministic score calculation;
- style, voice, dialogue, pacing, emotional, scene-objective, and
  chapter-objective reports;
- approved-draft requirement;
- branch creation and immutable revision lineage;
- branch status transitions;
- approved source preservation;
- ownership enforcement;
- explicit orchestration selection and skips;
- migration idempotency.

Frontend tests cover:

- dashboard and score rendering;
- findings, blockers, and recommendations;
- branch lineage and comparison;
- editorial and revision queues;
- regression of existing drafting controls.

Playwright with real Gemini uses `The Kingdom of Ash and Stars` to:

- create a draftable Arc 1 with approved scene and chapter drafts;
- run scene, chapter, arc, dialogue, and revision workflows;
- verify persisted reports and scores;
- verify source drafts remain byte-for-byte unchanged;
- verify revision lineage;
- verify editorial agents are selected only on explicit actions;
- verify unrelated changes skip editorial agents;
- verify rate limiting and provider traces.

## Acceptance Gates

Phase 3A is complete only when:

- editorial, dialogue, pacing, emotional, and objective analysis exist;
- scene, chapter, and arc scores persist;
- revision branches and immutable versions work;
- approved drafts remain authoritative and unchanged;
- no automatic rewriting or approval exists;
- no manuscript generation exists;
- orchestration remains bounded and demand-driven;
- migration is idempotent;
- backend, frontend, build, Playwright, and real Gemini validation pass;
- plaintext credential and forbidden manuscript-agent scans pass.

## Rollback

1. Stop editorial requests.
2. Disable `EditorAgent`, `DialogueAgent`, and `RevisionAgent`.
3. Redeploy Phase 2B backend and frontend together.
4. Retain additive Phase 3A collections and indexes.
5. Preserve reports, scores, branches, and revision history.
6. Restore a backup only when an external consumer cannot tolerate additive
   collections.

No approved draft content is modified or removed during rollback.
