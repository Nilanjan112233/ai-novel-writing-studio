# NovelForge Narrative Studio V2 - Phase 3A Completion Report

Completion date: 2026-06-14

Status: Complete

## Outcome

NovelForge now has a governed Editorial Intelligence Layer for approved Phase
2B scene and chapter drafts.

The production system can:

- review approved scenes, chapters, and arcs without changing their prose;
- analyze style, voice, dialogue, pacing, emotional progression, and planned
  objective fulfillment;
- calculate deterministic scene, chapter, and arc editorial scores;
- persist findings, evidence, recommendations, and blockers;
- create immutable revision branches and revision-version lineage;
- compare an approved source against a revision proposal;
- require author-controlled branch review and approval;
- expose editorial status, queues, scores, reports, and comparisons in the
  existing workspace;
- route each editorial action through one bounded, demand-driven agent plan.

Approved drafts remain authoritative. No editorial action automatically
rewrites, replaces, approves, or publishes content.

No `BookWriterAgent`, `ManuscriptAgent`, `PublishingAgent`, manuscript
assembly, book export, EPUB, or PDF workflow was added.

## Architecture

### Editorial Authority

`EditorialService` owns deterministic authority for:

- project, arc, chapter, scene, draft, report, and branch ownership;
- approved-draft eligibility;
- report normalization and persistence;
- score calculation and score history;
- branch lifecycle validation;
- immutable revision-version lineage;
- approved-source hash verification;
- comparison and dashboard projections.

`EditorAgent` and `DialogueAgent` produce derivative analysis only.
`RevisionAgent` produces alternative prose only inside a revision branch.
None of these agents can update an approved Phase 2B draft.

### Editorial Scoring

Agent dimension evidence is normalized to a 0-100 scale. Responses using a
common 0-10 model scale are deterministically converted to 0-100.

The service calculates:

- scene editorial score from style, dialogue, pacing, objective fulfillment,
  and emotional progression;
- chapter editorial score from scene quality, pacing, continuity, emotional
  progression, and objective fulfillment;
- arc editorial score from chapter quality, progression quality,
  consistency, pacing, and payoff readiness.

Scores do not approve content. They explain quality and blockers for the
author.

### Revision Governance

A revision branch references one approved source draft and stores its source
version and SHA-256 hash.

Revision versions are immutable and include:

- monotonically increasing version number;
- parent revision ID;
- generated proposal text;
- applied recommendations;
- author change reason;
- provider metadata;
- creation timestamp.

The branch lifecycle is:

`draft -> review -> approved`

`draft` or `review` may instead become `rejected` or `archived`. Approval is
manual and does not replace the approved source draft.

### Dynamic Orchestration

Explicit actions create persisted Phase 1A plans:

| Action | Selected agent | Other agents |
| --- | --- | --- |
| Editorial review | `EditorAgent` | skipped with reasons |
| Dialogue review | `DialogueAgent` | skipped with reasons |
| Revision proposal | `RevisionAgent` | skipped with reasons |

Planning events do not trigger editorial agents. Editorial events do not
recursively trigger drafting agents.

The existing enablement, cost, call, depth, no-change, retry, and provider
rate-limit controls remain authoritative.

During full validation, two shared production weaknesses were also fixed:

- provider admission now uses a protected rolling window so trace timestamps
  never show more than the configured limit;
- prior cycle outputs are compressed to summaries, recommendations, concerns,
  and artifact counts before later agents receive them.

This prevents both agent storms and prompt growth beyond the 30,000-character
context ceiling.

## Database

Collections added:

- `editorial_reports`
- `revision_branches`
- `revision_versions`
- `editorial_scores`

Indexes installed:

- `editorial_reports_project_subject`
- `editorial_reports_type_score`
- `revision_branches_project_branch`
- `revision_branches_source`
- `revision_versions_branch_version`
- `editorial_scores_subject`
- `editorial_scores_project_type`

The final migration rerun reported zero normalized records and
`indexes_installed: true`, confirming idempotency.

## API

Project-owned routes now support:

- scene, chapter, and arc editorial review;
- scene and chapter dialogue review;
- editorial report and score history;
- editorial dashboard projection;
- revision branch creation;
- revision proposal generation;
- branch review, approval, rejection, and archive;
- revision lineage;
- source-versus-revision comparison.

Every route validates project ownership before provider execution.

The public settings response now omits `api_key` entirely and exposes only
configuration state and non-secret provider settings.

## UI

Added:

- Editorial workspace;
- editorial score cards;
- approved-draft review controls;
- findings, blockers, and recommendations;
- revision branches, status controls, lineage, and comparisons;
- editorial and dialogue status on drafting cards;
- editorial queue, revision queue, and editorial blockers in Story Room.

The existing project workspace and navigation model were preserved.

## Files Changed

Primary backend additions:

- `backend/app/services/editorial_service.py`
- `backend/app/api/editorial.py`
- `backend/app/migrations/phase_3a.py`
- `backend/scripts/run_phase_3a_migration.py`
- `backend/tests/test_editorial_v3.py`

Primary backend integrations:

- `backend/app/services/narrative_studio.py`
- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/orchestration_engine.py`
- `backend/app/services/settings_service.py`
- `backend/app/services/provider_rate_limiter.py`
- `backend/app/services/secret_encryption_service.py`
- `backend/app/services/story_bible_service.py`
- `backend/app/core/database.py`
- `backend/main.py`

Primary frontend additions and integrations:

- `frontend/components/EditorialWorkspace.tsx`
- `frontend/components/EditorialWorkspace.test.tsx`
- `frontend/components/DraftingWorkspace.tsx`
- `frontend/components/StoryRoom.tsx`
- `frontend/app/project/[projectId]/page.tsx`
- `frontend/store/projectStore.ts`
- `frontend/lib/api.ts`
- `frontend/types/index.ts`

E2E:

- `e2e/editorial-v3.spec.ts`

## Final Validation

- Backend: 72 passed, 7 skipped.
- Frontend: 46 passed.
- Production build: passed.
- Full Playwright: 21 passed, 2 intentionally skipped.
- Real Gemini Phase 3A: passed with `gemini-3.1-flash-lite`.
- Migration rerun: passed and idempotent.
- Plaintext Google credential scan: clean.
- Public settings credential contract: clean.
- Forbidden manuscript/publishing agent scan: clean.
- In-app browser inspection: rendered correctly with zero console errors.

All Phase 3A acceptance gates are satisfied.
