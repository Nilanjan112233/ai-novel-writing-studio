# NovelForge Narrative Studio V2 - Phase 3B Implementation Plan

Plan date: 2026-06-14

## Source Of Truth

- `PRODUCTION_ARCHITECTURE_AUDIT.md`
- `DATABASE_MODEL_AUDIT.md`
- `AGENT_ARCHITECTURE_AUDIT.md`
- `PHASE_1A_COMPLETION_REPORT.md`
- `PHASE_1B_COMPLETION_REPORT.md`
- `PHASE_2A_COMPLETION_REPORT.md`
- `PHASE_2B_COMPLETION_REPORT.md`
- `PHASE_3A_COMPLETION_REPORT.md`
- `PHASE_3A_E2E_RESULTS.md`

## Scope

Phase 3B adds a governed book layer:

- deterministic `ManuscriptService`;
- deterministic `CanonGovernanceService`;
- review-only `ManuscriptAgent`;
- review-only `CanonAgent`;
- immutable manuscript versions and rollback;
- typed canon authority and conflict detection;
- book-level structural, continuity, canon, and editorial validation;
- manuscript and canon workspaces;
- manuscript, canon, and conflict queues in Story Room.

It does not add EPUB, PDF, DOCX, export, publishing, collaboration,
marketplace, `PublishingAgent`, or autonomous manuscript rewriting.

## Current Architecture

Phase 2B provides immutable approved scene and chapter drafts. Phase 3A adds
editorial reports, scores, revision branches, and author-controlled revision
governance. Dynamic orchestration already supports explicit one-agent actions,
rate limits, budgets, trace persistence, disabled-agent enforcement, and
no-change termination.

The current canon registry is a locked-fact ledger used by story-bible context
and contradiction checks. It is not yet a typed, source-versioned authority
layer. Approved chapters remain separate records and there is no immutable
book assembly, manuscript lifecycle, or book-level validation.

## Problems

The production system cannot currently:

- assemble approved chapter drafts into an ordered manuscript;
- preserve manuscript version lineage and source hashes;
- roll back the active manuscript version without rewriting history;
- calculate book-level structural, continuity, canon, and editorial results;
- promote typed authoritative records without breaking legacy locked facts;
- detect project-wide character, timeline, artifact, knowledge, and power
  conflicts;
- expose manuscript readiness and canon conflicts to authors;
- route manuscript and canon review through bounded orchestration.

## Authority Model

`ManuscriptService` is the deterministic authority for:

- project and source ownership;
- approved chapter eligibility;
- chapter ordering and completeness;
- immutable manuscript assembly;
- version activation and rollback;
- deterministic manuscript validation;
- lifecycle transitions and manual approval;
- dashboard and queue projections.

`CanonGovernanceService` is the deterministic authority for:

- typed canon normalization and promotion;
- active canon authority;
- source and evidence tracking;
- deterministic conflict detection;
- conflict persistence and status;
- manuscript canon verification;
- Story Bible canon projection.

`ManuscriptAgent` and `CanonAgent` produce observations, findings, evidence,
and recommendations only. They cannot rewrite chapters, change canon, alter
planning records, assemble or approve a manuscript, or resolve conflicts.

## Legacy Canon Compatibility

Phase 3B evolves the existing `canon_registry` collection in place.

Legacy locked facts retain their `fact`, `fingerprint`, `status`, and source
fields and remain visible through the existing `/canon` contract. Migration
adds stable `canon_id`, `canon_type`, `source_collection`, `source_version`,
`authority_level`, `active`, `evidence`, and timestamps. New typed promotions
use the same collection, so NovelForge has one canon authority rather than
parallel registries.

## Manuscript Assembly

A manuscript contains only active approved chapter drafts whose chapter plans
belong to the same project. Chapters are ordered by approved chapter-plan
number. Assembly preserves approved chapter text byte-for-byte and records:

- source chapter-plan and draft IDs;
- source draft versions;
- SHA-256 hashes;
- arc IDs and chapter numbers;
- assembled chapter boundaries;
- parent manuscript version;
- deterministic validation result.

Each assembly creates a new immutable `manuscript_versions` record and moves
the manuscript's active-version pointer. Rollback only changes that pointer.

Lifecycle:

- `draft`
- `review`
- `validated`
- `approved`
- `archived`

`FAIL` validation blocks `validated` and `approved`. Approval remains a manual
user action.

## Validation

Deterministic manuscript validation returns `PASS`, `WARNING`, or `FAIL`.

Checks include:

- contiguous chapter order and complete source references;
- current approved source identity and hash preservation;
- chapter, arc, timeline, knowledge, artifact, character, and power
  continuity;
- active canon conflicts;
- unresolved Phase 2B continuity failures;
- unresolved Phase 3A editorial blockers and low chapter scores;
- source scene lineage.

Warnings remain reviewable. Failures block manuscript approval.

## Canon Governance

Typed canon domains are:

- character
- power
- artifact
- timeline
- knowledge
- faction
- world
- mystery
- relationship

Promotion records source collection, source ID, source version, authority
level, evidence, normalized subject, field, and value. A newer promotion may
supersede an active record without deleting history.

Conflict detection is deterministic and records:

- contradictory active values for the same typed subject and field;
- character state, age, relationship, and progression conflicts;
- impossible or duplicate timeline order;
- artifact ownership, location, destruction, and evolution conflicts;
- knowledge reveal and known/unknown conflicts;
- unsupported or regressive power changes.

## Dynamic Orchestration

Explicit actions create persisted Phase 1A plans:

- manuscript review selects only `ManuscriptAgent`;
- canon review selects only `CanonAgent`.

Assembly, validation, promotion, lifecycle changes, and rollback are
deterministic and make no provider call. Their project events update queues
and Story Bible projections without replaying either agent in a later cycle.
Unrelated changes record both Phase 3B agents as skipped.

All existing enablement, budget, rate-limit, retry, trace, call-depth, and
no-change controls remain authoritative.

## Database Changes

Add:

- `manuscripts`
- `manuscript_versions`
- `manuscript_reports`
- `canon_conflicts`

Evolve the existing:

- `canon_registry`

Indexes:

- `manuscripts_project_version`
- `manuscript_versions_manuscript_version`
- `manuscript_reports_subject`
- `canon_registry_project_type`
- `canon_registry_active`
- `canon_conflicts_project_status`

The migration builds typed canon records from approved existing ledgers,
normalizes legacy canon safely, installs indexes, records its version, and is
idempotent.

## API Changes

Project-owned manuscript endpoints support:

- create;
- assemble;
- validate;
- review;
- lifecycle transition;
- approve and archive;
- version history;
- rollback;
- reports and dashboard.

Project-owned canon endpoints support:

- registry listing;
- typed promotion;
- deterministic validation;
- agent review;
- conflict history and status;
- reports;
- promotion history and dashboard.

All endpoints validate project, manuscript, version, chapter plan, chapter
draft, source scene, canon source, and conflict ownership.

## UI Changes

Add a minimal Manuscript section to the existing workspace:

- chapter ordering;
- active version and lineage;
- deterministic validation status;
- reports and blockers;
- manual lifecycle controls.

Add a Canon section:

- active typed canon;
- promotion history;
- open conflicts;
- validation and review actions;
- findings and recommendations.

Story Room gains manuscript, canon-review, and conflict queues. The existing
workspace and navigation model remain intact.

## Files Affected

Primary backend additions:

- `backend/app/services/manuscript_service.py`
- `backend/app/services/canon_governance_service.py`
- `backend/app/api/manuscript.py`
- `backend/app/migrations/phase_3b.py`
- `backend/scripts/run_phase_3b_migration.py`
- `backend/tests/test_manuscript_v3.py`

Backend integrations:

- `backend/app/services/canon_service.py`
- `backend/app/services/story_bible_service.py`
- `backend/app/services/narrative_studio.py`
- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/orchestration_engine.py`
- `backend/app/services/database_audit_service.py`
- `backend/app/core/database.py`
- `backend/app/api/projects.py`
- `backend/main.py`
- test provider fixtures.

Frontend additions and integrations:

- `frontend/components/ManuscriptWorkspace.tsx`
- `frontend/components/CanonDashboard.tsx`
- component tests;
- `frontend/app/project/[projectId]/page.tsx`
- `frontend/components/StoryRoom.tsx`
- `frontend/store/projectStore.ts`
- `frontend/lib/api.ts`
- `frontend/types/index.ts`.

E2E:

- `e2e/manuscript-v3.spec.ts`

## Migration Plan

1. Normalize legacy canon records with additive fields.
2. Promote approved planning ledgers into typed canon records using stable
   source-based IDs.
3. Normalize any compatible manuscript records.
4. Install the six Phase 3B indexes.
5. Record migration version and completion time.
6. Re-run migration and verify zero duplicate stable records.

## Test Plan

Backend tests cover:

- assembly from approved chapters only;
- ordering and source hash preservation;
- immutable versions and rollback;
- lifecycle transitions and manual approval;
- validation failure gates;
- typed canon promotion and supersession;
- character, timeline, artifact, knowledge, and power conflicts;
- ownership enforcement;
- explicit ManuscriptAgent and CanonAgent selection;
- migration idempotency;
- legacy `/canon` compatibility.

Frontend tests cover:

- manuscript versions, validation, and lifecycle controls;
- canon records, conflicts, and recommendations;
- Story Room queues;
- existing drafting and editorial regression coverage.

Playwright and real Gemini use `The Eternal Throne` to:

- create approved arcs, scenes, and chapter drafts;
- assemble and validate multiple manuscript versions;
- review a manuscript and canon with the new agents;
- introduce and detect a canon conflict;
- verify approved chapter hashes remain unchanged;
- verify approval remains manual;
- verify unrelated changes skip Phase 3B agents;
- verify trace and rate-limit compliance.

## Acceptance Gates

Phase 3B is complete only when:

- manuscript assembly, versions, lineage, rollback, validation, and manual
  approval work;
- typed canon authority and conflict detection work;
- approved chapters and scenes remain authoritative and unchanged;
- manuscript and canon reviews are observational only;
- orchestration remains bounded and demand-driven;
- migration is idempotent;
- backend, frontend, production build, Playwright, and real Gemini validation
  pass;
- plaintext credential and forbidden publishing/export-agent scans pass.

## Rollback

1. Stop manuscript and canon-governance requests.
2. Disable `ManuscriptAgent` and `CanonAgent`.
3. Redeploy Phase 3A backend and frontend together.
4. Retain additive collections, typed fields, indexes, versions, conflicts,
   reports, and canon history.
5. Keep the legacy `/canon` locked-fact contract available.

No approved scene, chapter, editorial report, revision, manuscript version,
or canon history is deleted or rewritten during routine rollback.
