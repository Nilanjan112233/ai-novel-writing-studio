# NovelForge Narrative Studio V2 - Phase 3B Completion Report

Completion date: 2026-06-14

Status: Complete

## Outcome

NovelForge now has a governed manuscript and canon layer above approved
planning, drafting, and editorial records.

The production system can:

- assemble only approved chapter drafts into an ordered manuscript;
- preserve approved chapter text and source-scene lineage;
- create immutable manuscript versions with SHA-256 source hashes;
- roll the active manuscript pointer back without deleting history;
- validate book structure, continuity, canon, progression, and editorial state;
- require manual manuscript approval and block approval after `FAIL`;
- promote typed canon authority with evidence and source versions;
- detect and persist character, timeline, artifact, knowledge, and power
  conflicts;
- deactivate superseded canon authority without deleting its history;
- expose manuscript, canon, and conflict queues in the Story Room;
- route review work through one bounded agent at a time.

No export, publishing, collaboration, autonomous approval, or autonomous
manuscript rewriting was added.

## Authority Model

### ManuscriptService

`ManuscriptService` is the deterministic authority for:

- project and source ownership;
- approved chapter eligibility;
- chapter ordering and completeness;
- immutable manuscript assembly;
- source text and source hash preservation;
- version lineage and rollback;
- deterministic manuscript validation;
- lifecycle transitions;
- manual approval;
- dashboard and queue projections.

Manuscript lifecycle:

- `draft`
- `review`
- `validated`
- `approved`
- `archived`

Only users can approve a manuscript. Validation result `FAIL` blocks the
`validated` and `approved` transitions.

### CanonGovernanceService

`CanonGovernanceService` is the deterministic authority for:

- typed canon normalization and promotion;
- source ownership and source-version evidence;
- active authority records;
- canon deactivation without history deletion;
- deterministic conflict detection;
- conflict status and history;
- manuscript canon verification;
- Story Bible canon projection.

Supported domains:

- character
- power
- artifact
- timeline
- knowledge
- faction
- world
- mystery
- relationship

The existing `canon_registry` was evolved in place. Legacy locked facts remain
compatible with the existing canon contract.

## Review Agents

`ManuscriptAgent` produces book-level structure, continuity, and review
findings.

`CanonAgent` produces canon observations, conflict findings, and
recommendations.

Neither agent can:

- rewrite an approved chapter;
- assemble or approve a manuscript;
- promote, deactivate, or resolve canon;
- modify authoritative planning records.

## Dynamic Orchestration

Phase 3B extends the demand-driven graph with:

- `manuscript_review` -> `ManuscriptAgent`
- `canon_validation` -> `CanonAgent`

Assembly, deterministic validation, promotion, lifecycle transitions,
conflict status changes, and rollback make no provider calls.

The final E2E plans each:

- selected one required agent;
- skipped 21 unrelated agents with reasons;
- made one provider call;
- completed without recursion;
- remained within the configured five requests-per-minute limit.

Phase 3B events terminate after persistence and Story Bible refresh. They do
not replay manuscript or canon agents in a later static cycle.

## Database Changes

Added:

- `manuscripts`
- `manuscript_versions`
- `manuscript_reports`
- `canon_conflicts`

Evolved:

- `canon_registry`

Indexes:

| Collection | Index |
| --- | --- |
| `manuscripts` | `manuscripts_project_version` |
| `manuscript_versions` | `manuscript_versions_manuscript_version` |
| `manuscript_reports` | `manuscript_reports_subject` |
| `canon_registry` | `canon_registry_project_type` |
| `canon_registry` | `canon_registry_active` |
| `canon_conflicts` | `canon_conflicts_project_status` |

The manuscript-version index is unique by project, manuscript, and version
number.

## API

Phase 3B adds 22 project-owned routes covering:

- manuscript creation, listing, assembly, validation, review, lifecycle,
  approval, archival, history, rollback, reports, and dashboard;
- canon registry, promotion, activation state, validation, review, conflicts,
  conflict status, reports, promotion history, and dashboard.

Every route validates project ownership and the ownership of referenced
manuscripts, versions, drafts, chapter plans, canon sources, and conflicts.

## UI

Added:

- Manuscript Workspace;
- Canon Dashboard;
- manuscript version and chapter-order views;
- validation, report, approval, archive, and rollback controls;
- active canon and promotion history;
- canon conflict status and authority deactivation controls;
- manuscript, canon, and conflict Story Room queues.

The existing workspace navigation and planning surfaces were retained.

## Files Changed

Backend:

- `backend/app/api/manuscript.py`
- `backend/app/core/database.py`
- `backend/main.py`
- `backend/app/migrations/phase_3b.py`
- `backend/app/services/canon_governance_service.py`
- `backend/app/services/database_audit_service.py`
- `backend/app/services/manuscript_service.py`
- `backend/app/services/narrative_studio.py`
- `backend/app/services/orchestration_engine.py`
- `backend/app/services/orchestration_service_v2.py`
- `backend/app/services/settings_service.py`
- `backend/app/services/story_bible_service.py`
- `backend/app/api/development.py`
- `backend/app/api/projects.py`
- `backend/scripts/run_phase_3b_migration.py`
- `backend/tests/conftest.py`
- `backend/tests/test_manuscript_v3.py`

Frontend:

- `frontend/app/project/[projectId]/page.tsx`
- `frontend/components/CanonDashboard.tsx`
- `frontend/components/ManuscriptWorkspace.tsx`
- `frontend/components/ManuscriptGovernance.test.tsx`
- `frontend/components/StoryRoom.tsx`
- `frontend/lib/api.ts`
- `frontend/store/projectStore.ts`
- `frontend/types/index.ts`

E2E and documentation:

- `e2e/manuscript-v3.spec.ts`
- `PHASE_3B_IMPLEMENTATION_PLAN.md`
- `PHASE_3B_COMPLETION_REPORT.md`
- `PHASE_3B_E2E_RESULTS.md`
- `PHASE_3B_MIGRATION_GUIDE.md`

## Verification

| Gate | Result |
| --- | --- |
| Backend | 77 passed, 7 skipped |
| Frontend | 48 passed |
| Production build | Passed |
| Full Playwright suite | 22 passed, 2 intentionally skipped |
| Final Phase 3B Playwright | 1 passed |
| Real Gemini | Passed with `gemini-3.1-flash-lite` |
| Migration rerun | Zero changed records, indexes installed |
| Production DB audit | Passed, zero findings |
| Plaintext credential scan | Passed |
| Forbidden publishing-agent scan | Passed |

The remaining warnings are dependency deprecations for Pydantic, FastAPI
startup events, pytest-asyncio defaults, and Vite's CommonJS API. They are not
Phase 3B correctness failures.

## Acceptance Result

All Phase 3B acceptance gates are satisfied. Approved chapters remain
authoritative, manuscript approval remains manual, canon changes remain
governed, and the production execution path remains dynamic and bounded.

Phase 4 export, publishing, collaboration, and team-permission work remains
explicitly out of scope.
