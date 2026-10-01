# NovelForge Narrative Studio V2 - Phase 3C Implementation Plan

Plan date: 2026-06-14

## Mission

Phase 3C validates whether NovelForge can support a human author across a
full-length novel without losing canon, memory, control, or narrative quality.
This is a production-readiness phase, not an export or publishing phase.

## Source Of Truth

The implementation was based on the existing architecture audits, database
audits, agent definitions, Phase 1A through Phase 3B plans and reports,
migrations, backend services, frontend workspaces, orchestration graph, tests,
and prior E2E evidence.

## Scope

Phase 3C adds:

- deterministic chapter intelligence for every approved chapter;
- bounded chapter-intelligence memory for future agents;
- read-only `StoryAuditorAgent`;
- deterministic story auditing and prose-pattern analysis;
- deterministic pre-mutation change impact analysis;
- a Story Health Dashboard;
- project isolation and long-range memory validation;
- a 50-chapter, 89,063-word, two-arc production corpus;
- complete workspace navigation and responsive-layout validation;
- author workflow, agent, memory, UX, and prose-quality audits.

Phase 3C does not add export, publishing, EPUB, PDF, DOCX, collaboration,
marketplace, team, or autonomous authoring features.

## Authority Model

`ChapterIntelligenceService` is authoritative for approved-chapter summaries,
events, characters, changes, reveals, mysteries, foreshadowing, artifacts,
relationships, timeline effects, canon effects, open questions, and future
obligations.

`StoryAuditorService` is authoritative for deterministic project-wide
findings. `StoryAuditorAgent` can add observations but cannot modify any story
record.

`ChangeImpactService` is authoritative for project-scoped previews and
approve/reject decisions. Approval records author intent; it does not silently
perform the requested mutation.

`StoryHealthService` is authoritative for the current health snapshot and
score. It reads existing records and does not rewrite the story.

## Workstreams

### 1. Chapter Intelligence

- Generate intelligence on chapter approval and approved rollback.
- Support idempotent backfill.
- Index chapter intelligence for retrieval.
- Prefer structured chapter memory over historical prose.
- Preserve old unresolved obligations outside the recent chapter window.

### 2. Story Audit And Quality

- Detect unresolved mysteries and promises.
- Detect abandoned artifacts, foreshadowing, characters, and relationships.
- Detect canon, continuity, motivation, pacing, exposition, and contradiction
  risks.
- Detect repetitive chapter shapes, openings, dialogue, emotional beats,
  over-uniform length, over-polished rhythm, and overly clean resolutions.
- Return findings only and never auto-rewrite prose.

### 3. Change Impact

- Preview character, relationship, timeline, arc, ending, mystery, artifact,
  and foreshadowing changes.
- Scan chapters, scenes, arcs, canon, knowledge, foreshadowing, artifacts,
  manuscripts, and editorial reports.
- Enforce project ownership and stable record identity.
- Require an explicit approve or reject decision before later mutation.

### 4. Story Health

- Calculate all requested project metrics.
- Persist a current snapshot.
- Present score, metrics, latest findings, chapter memory, and change impact
  controls in one author-facing dashboard.

### 5. Orchestration And Agents

- Add `StoryAuditorAgent` to assignments and routing.
- Supply bounded chapter memory to agents.
- Prevent audit discussions, proposals, agent memory, or story mutations.
- Strengthen SceneWriter guidance against formulaic, over-explained prose.
- Add one observable corrective retry for missing mandatory derivative prose.

### 6. Production-Scale Validation

- Create two uneven arcs with 50 chapters and 70,000 to 100,000 words.
- Preserve Chapters 4 and 9 as long-range obligations.
- Verify Chapters 45 and 50 receive both recent and long-range memory.
- Create a second project and assert zero cross-project references.
- Exercise planning, drafting, editorial, manuscript, and rollback workflows
  through the combined regression and E2E suite.

### 7. Author Experience

- Validate all 26 workspace sidebar sections.
- Validate Projects, Dashboard, Settings, and project workspace pages.
- Validate desktop widths from 1280 to 2560 pixels.
- Validate Story Health at a 390-pixel mobile viewport.
- Capture the six required production screenshots.
- Record missing search, filter, sort, pagination, queue, and mobile affordances
  as UX findings rather than inventing unrelated features.

## Database Changes

Add:

- `chapter_intelligence`
- `story_audit_reports`
- `story_health_snapshots`
- `change_impacts`

The Phase 3C migration installs project-scoped and lookup indexes and is safe
to rerun.

## API

Add project-owned routes for:

- chapter intelligence listing, memory, and backfill;
- story audit execution and history;
- story health retrieval;
- change impact preview, history, approval, and rejection.

## Acceptance Strategy

The phase is accepted only after:

- backend regression passes;
- frontend regression passes;
- production build passes;
- full Playwright passes;
- real Gemini Story Auditor passes;
- real Gemini legacy drafting, editorial, manuscript, and planning paths pass;
- 50 chapters and 70,000 to 100,000 words are present;
- long-range memory and project isolation assertions pass;
- screenshots and all required reports exist.
