# NovelForge UX Integration Implementation Report

Date: 2026-08-09

## Outcome

NovelForge now exposes a unified author-facing writing projection over the existing MongoDB authorities. Discovery chapters are no longer invisible to the Dashboard, Story Studio, or next-action guidance. A new Writing surface indexes existing chapter drafts and versions, and exposes chapter reading, revision entry points, continuation, status, word count, continuity status, extraction status, and bounded story-context details.

No new canon, graph, manuscript, memory authority, writing pipeline, or TencentDB integration was added.

## Implemented

- `WritingExperienceService.state()` projects Discovery and structured writing into one read model.
- `GET /api/projects/{project_id}/writing-state` exposes the projection.
- `GET /api/projects/{project_id}/writing-state/chapters/{chapter_number}/context` exposes bounded author-facing context.
- Dashboard and Story Studio use the projection for chapter count, latest approved chapter, and next action.
- `WritingWorkspace` provides a chapter library over existing chapter drafts, versions, approval state, continuity reports, extraction records, and chapter intelligence.
- Chapter context explicitly distinguishes derived candidate details from approved story truth and includes provenance-oriented source labels.
- Story Studio renders persisted Story Studio jobs as a durable conversation-like history while stating that conversation is separate from approved story state.
- Chapter approval now separates core prose approval from downstream enrichment. Enrichment may be pending, running, completed, or failed without falsely reporting that the approved prose failed.
- Approved Discovery chapters now enter the existing Narrative Analysis Engine before Story Bible rebuilding. Workspace bootstrap and the Narrative Intelligence endpoint repair stale source manifests and default health snapshots when current chapter intelligence has changed.
- Native chapter-intelligence retrieval now records provenance and deterministic quality signals and deduplicates equivalent records without promoting candidates to authority.
- Story Studio project questions now receive the current writing-state projection and bounded approved-prose context for explicitly mentioned chapters, preventing stale analysis summaries from claiming that an established project has no chapters.

## Browser evidence

On the running application, the live continuity project displayed:

- `6 chapters in this story`;
- `Chapter 6 is your latest approved chapter`;
- a `Chapter library` with Chapter 1 through Chapter 6;
- status, word count, active version, continuity status, extraction count, and story-context readiness;
- opening Chapter 3 and Chapter 6 in the same Writing surface;
- `What NovelForge remembers about Chapter 3/6` with the candidate/provenance boundary;
- a Story Studio banner linking the author to the chapter library.

The browser also exposed a real pre-fix defect: an existing persisted Story Studio response incorrectly described the project as having no chapters. That evidence drove the shared assistant-context correction above. The post-build dev harness lost its backend listener before a second live browser answer could be captured; this is recorded as a validation limitation, not hidden.

## Authority impact

The changes are read-model and integration changes. Existing chapter drafts, scene drafts, revision lineage, Paragraph Editor, canon proposals, Decision History, Story Bible, Narrative Analysis Engine, manuscript, backup/recovery, chronology, Writer's Room, and provider gateway remain authoritative in their existing owners.

Conversational responses do not directly mutate authoritative story state. Explicit conversational changes still route through governed proposal/decision behavior.

