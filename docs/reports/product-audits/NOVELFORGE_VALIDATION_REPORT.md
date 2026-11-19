# NovelForge Validation Report

Date: 2026-08-08

## Automated validation

- Backend broad suite: 159 passed, 7 skipped.
- Latest orchestration/readiness/arc targeted run: 21 existing tests passed; the only initial failure was whitespace in a newly added recovery assertion.
- Provider payload recovery: 3 passed after correcting that assertion.
- Frontend: 23 files, 86 tests passed.
- Production build: passed, including TypeScript and route generation.
- Backup creation and checksum/integrity preview: passed in the real UI.

The skipped backend tests are environment-conditional, not observed product failures. Existing Pydantic and `datetime.utcnow` deprecation warnings remain.

## Real browser journey

The in-app browser was used on the running local application and real MongoDB state.

Validated journey:

1. Opened an automatically developed project with characters, world, relationships, timeline, plot threads, an arc, and readiness evidence.
2. Confirmed an optional author answer does not block development.
3. Changed an earlier author answer and observed visible planning reconsideration.
4. Ran targeted development; three bounded passes completed and cleared the invalidation.
5. Reviewed the current arc, confirmed required supported planning checks, and reached `DRAFTABLE`/`READY` while optional depth remained nonblocking.
6. Created and saved a chapter plan and scene plan.
7. Approved both plans through the new author controls.
8. Started a real SceneWriterAgent request using OpenRouter and DeepSeek v4 Flash.
9. Observed the initial structured-output failure, safe failure banner, unchanged state, and retry action.
10. Confirmed the old client timeout fired before the backend was finished; extended only long AI actions and added visible busy state.
11. Retried after provider-shape recovery. A 679-word Version A persisted with provider/model provenance.
12. Moved the draft to review. It did not become approved automatically.
13. Verified three new story facts entered the Canon Proposal Queue, including high-impact confirmation gates.
14. Opened paragraph planning and the frozen Paragraph Editor. The outline, pipeline, warnings, purpose, dependencies, editor, save/version action, history, comments, analytics, locks, and validation surfaces rendered without mutation.
15. Opened Editorial. Development, line, copy, style, continuity, dialogue, emotion, description, consistency, and grammar passes were available as protected review/revision paths.
16. Opened Story Health and verified the shared Narrative Intelligence explanation, domains, evidence-backed findings, and change-impact preview.
17. Opened Manuscript and verified that it waits for approved chapter drafts.
18. Opened Canon and found/fixed a real missing-field rendering crash. The registry then rendered safely.
19. Opened the Canon Proposal Queue and verified AI facts remained pending.
20. Created and downloaded a project backup: 808 records, 588.8 KB, RC9 format.
21. Ran restore preview. Integrity passed and the UI promised a separate copy; restore itself was not executed.

## Provider evidence

- OpenRouter transport succeeded with DeepSeek v4 Flash.
- Application validation correctly distinguished provider success from unusable structured output.
- OpenRouter showed no application rate-limit wait.
- The successful draft remained derivative and unapproved.
- Credentials stayed masked and are not included in this report or backup evidence.

## Agent/orchestration evidence

- The active development run completed three bounded passes with 20 specialist calls and no lost outputs.
- Same-cycle downstream summaries reflected upstream planning.
- Optional questions did not block.
- Author-change invalidation was visible, targeted, and cleared after reconsideration.
- Project Activity exposed completed task counts and recent outcomes; historical outputs are now labeled snapshots.
- All configured active agents remain selectable through their registered responsibilities; automated routing and agent roster tests passed.

## Frozen-feature result

No confirmed regression was found in Paragraph Editor safety, Writer's Room lineage, revision lineage, character chronology, or backup contracts. Their automated regression suites passed. The live Paragraph Editor was inspected without altering prose. Writer's Room was not charged through another real generation because one live provider draft plus the protected automated lineage tests supplied adequate evidence without unnecessary cost.

## Accessibility and desktop behavior

- Controls used semantic headings, buttons, tabs, lists, status/alert regions, progress bars, and labeled filters in the inspected surfaces.
- Busy animations include reduced-motion behavior.
- Responsive grid/flex layouts and progressive Toolbox disclosure remained intact in the production build.
- A complete dedicated screen-reader and every-resolution manual matrix was not performed; this remains a validation limitation rather than a claimed pass.

