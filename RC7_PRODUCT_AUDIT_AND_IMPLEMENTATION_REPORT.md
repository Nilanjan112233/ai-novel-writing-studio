# NovelForge V2 RC7 — Product Audit and Implementation Report

Status: Pre-implementation audit complete  
Scope: Writing experience, collaborative revision, draft safety, novice guidance, performance, reliability, accessibility, and validation  
Architecture decision: Extend the frozen architecture; do not introduce a second writing pipeline or a second source of narrative truth.

## Evidence reviewed

- Architecture: Paragraph Engine, Narrative Intelligence, Interactive Narrative Studio, production architecture, and RC5/RC6 architecture notes.
- Implementation: Drafting, Editorial, Narrative Studio, Narrative Analysis, Workspace Context, Workspace Companion, Application Knowledge, beginner setup, project entry, project bootstrap, persistence, and provider services.
- Current tests: backend drafting/editorial/workspace suites, frontend Drafting/Editorial/Companion suites, RC6 novice-author Playwright, and post-RC5 hardening journeys.
- Live novice journey: created a project, supplied a character-driven premise, completed all seven beginner steps, entered Drafting, opened the Companion, and asked the Project Assistant why writing was blocked.

## Architecture boundaries

| Concern | Authoritative existing system | RC7 approach |
|---|---|---|
| Paragraph prose and recovery | Paragraph Engine (`paragraph_content`, immutable `paragraph_versions`) | Critical safety fixes only; no editor capability expansion |
| Scene alternatives | `scene_drafts` version lineage | Add comparison, labels, favorite and author-controlled promotion to the existing lineage |
| Revision alternatives | Editorial revision branches and versions | Add pass types and explainability to existing branches |
| Story context | Persistent state plus Narrative Analysis graph | Reuse and cache bounded context; no independent analysis |
| Story quality | Story Health, critique, canon, timeline, character and plot services | Surface existing evidence; do not rescore independently |
| Guidance | Workspace Companion, Application Knowledge and workspace bootstrap | Make writing-aware and action-oriented |
| AI roles | Existing Scene Writer, Editor, Dialogue and Revision agents | Correct and extend their contracts; do not add another agent |

## Live novice findings

### Critical

1. The guided setup ends at a planned scene, but the first arc remains ineligible for drafting. The Drafting page says that writing is blocked without identifying the exact approval/readiness blockers or offering a direct resolution action.
2. The Project Assistant answers “why is writing blocked?” with generic page documentation and navigates back to the page the author is already viewing.
3. Scene generation currently converts the Scene Writer result into planning-summary lines instead of reader-facing prose.
4. Regenerating a scene deletes and recreates `scene_paragraphs`. That can discard the active Paragraph Editor structure and is a critical draft-safety defect.

### High

1. The workflow is Generate → Approve → Editorial, while the required author-controlled flow is Plan → Generate → Review → Revise → Approve.
2. Scene versions exist but are exposed as technical history rather than Version A/B/C alternatives with preview, compare, favorite, restore and discard actions.
3. Revision branches exist but do not expose structured Development, Line, Copy, Style, Continuity, Dialogue, Emotion, Description, Consistency and Grammar passes.
4. AI operations lack a consistent author-facing contract for why the suggestion exists, expected impact, affected narrative areas, change scope and what remains unchanged.
5. The Companion recommends unrelated foundation work while the author is blocked in Drafting and retains multiple low-value progress messages.

### Medium

1. There is no compact writing dashboard joining current scene, draft status, safe recovery, pending suggestions, scene health and the next action.
2. Draft generation has no persisted idempotency key, so repeated client submissions can create duplicate versions.
3. Story momentum is visible primarily as completeness percentages rather than writing-stage milestones.
4. Existing planning inputs are available to the Scene Writer through persistent state and narrative context, but the generated draft does not expose which inputs were used.

## Existing coverage that must be reused

- Immutable scene/chapter version lineage, rollback and review status transitions.
- Paragraph autosave, manual versions, suggestion approval/rejection, undo/redo and restore.
- Editorial review findings, revision branches, revision comparison and approval.
- Canon, Story Bible, timeline, character, relationships, plot threads, themes and approved decisions in persistent agent state.
- Workspace bootstrap, recommendation identity/cooldown/dismiss/snooze lifecycle, publication-readiness policy and domain-event refresh paths.
- Provider gateway failover, execution traces, agent assignment and generation metadata.

## RC7 implementation groups

### Group 1 — Safe writing bridge and dashboard

- Add an additive writing-dashboard response assembled from existing planning, drafting, revision and Narrative Intelligence records.
- Report exact drafting blockers with direct destinations and a deliberate “prepare for writing” confirmation path.
- Preserve all existing routes and payloads.

### Group 2 — Collaborative scene drafts

- Make Scene Writer return reader-facing prose plus structured scene information.
- Store operation, rationale, expected impact, affected areas, scope, preserved elements, context evidence and request identity on the existing scene draft.
- Preserve existing Paragraph Editor content during scene regeneration.
- Add additive compare, favorite and discard operations over `scene_drafts`.

### Group 3 — Structured revision

- Permit review and revision of a review-stage draft while keeping the source snapshot immutable.
- Add structured revision-pass metadata and author-facing explanations to existing revision branches and versions.
- Promote an approved revision into the existing scene-draft lineage only after explicit author confirmation.

### Group 4 — Writing-aware guidance

- Prioritize Drafting blockers, review, revision, approval and continuation when the Companion is on a writing surface.
- Answer workflow questions from live writing state before project-story retrieval.
- Suppress duplicate progress celebrations and expose one-click next actions.

### Group 5 — Reliability, performance and verification

- Add request idempotency and frontend request cancellation/deduplication where compatible with current synchronous provider calls.
- Reuse bootstrap/context results and avoid repeated Story Health fetches.
- Add backend, frontend, Playwright, accessibility, integrity, build, performance and real-provider evidence.

## Agent decision

No additional agent is justified. NovelForge already has Scene Writer, Editor, Dialogue, Revision, Canon, Manuscript and Story Auditor roles. The observed failure is a contract and workflow-integration problem: the Scene Writer is instructed not to write prose even though its runtime validation expects prose. Correcting that existing role and reusing the Revision agent prevents duplicated business logic and context.

## Completion gates

RC7 is complete only after:

1. Targeted tests pass after every implementation group.
2. The complete backend and frontend suites pass.
3. Production build, Playwright desktop journeys, accessibility checks and console checks pass.
4. Database integrity and 100/250/500/1000-chapter benchmarks pass.
5. A real Gemini journey demonstrates planning input reuse, draft generation, review, revision, approval, recovery, Story Bible/Narrative Intelligence refresh and export.
6. Final implementation, UX, test, known-limitations and architecture documents are updated with measured evidence.
