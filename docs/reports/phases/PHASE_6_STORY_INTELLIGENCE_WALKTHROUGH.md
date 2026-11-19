# Phase 6 Story Intelligence Walkthrough

## Starting point

Open a project. Story Health is now the primary dashboard, and the header identifies the workspace as the Narrative Intelligence Platform. The frozen editor remains available through Continue Writing, but it is no longer the product's default center.

## Story Intelligence

The Narrative Intelligence section shows one shared graph's node/dependency counts and cache behavior. Character, Canon, Timeline, Plot, Pacing, Continuity, and Balance cards expose the current domain scores. Select a domain to filter the shared finding stream.

Every warning displays severity, explanation, affected chapters, affected scenes, confidence, supporting evidence, and a recommended action. This evidence contract is reused across domain views and the AI reviewer.

## Story Health

Overall Story Health is the average of the seven authoritative domain scores. Compatibility metrics—chapters, words, mysteries, promises, conflicts, continuity warnings, pacing warnings, and editorial blockers—remain visible, but they no longer implement an independent scoring system.

Canon conflicts, timeline errors, unresolved plot promises, character drift, pacing outliers, continuity failures, and balance problems automatically reduce their domain score and Overall Story Health. Resolving the underlying finding removes its deduction on the next analysis.

## Canon Intelligence

Open Canon from the toolbox to see grouped active canon and open conflicts. Typed conflicts show their original source, conflicting sources, values, affected locations, impact, severity, evidence, acknowledgement state, and resolution controls. Deactivating or validating canon rebuilds the Story Bible and refreshes shared analysis.

Use Change Impact Preview before a significant canon change. High-risk previews are flagged as requiring confirmation and report downstream canon, timeline, character, thread, scene, chapter, and manuscript consequences.

## Timeline Intelligence

Open Timeline to see known, probable, and intentionally unknown chronology grouped by arc. Dependencies are rendered on each event as source-to-target links; missing dependencies are visually marked. The shared engine detects impossible ranges, duplicate/overlapping positions, chronology gaps, and missing dependency events. The corresponding evidence also appears under Timeline Health.

## Character Intelligence

Open Characters for existing character bibles, goals, fears, journey, and arc progression. Character Health adds whole-novel evidence such as active-character presence gaps and personality drift against established traits. Relationship records and character progressions are graph sources, so their references contribute to change impact and Story Bible context.

## Plot Thread Intelligence

Open Plot Threads for the project registry and select Plot Threads on Story Health for evidence-backed risks. The engine analyzes plot threads, mysteries, foreshadowing, chapter obligations/promises, references, introduction locations, recent development, resolution status, and abandoned storylines. Missing resolutions automatically reduce Plot Health and Overall Story Health.

## Story Bible

The Story Bible is rebuilt automatically from project-owned story knowledge. Phase 6 adds the shared analysis snapshot/findings and an explicit `approved_story_content` section containing only active approved or validated chapter/scene drafts. Its source policy is recorded as `approved_active_content_only`; authors do not maintain a second manual intelligence database.

## Change Impact Analysis

From Story Health, choose the structural change type and target, then request Preview. The result reports affected chapters, scenes, characters, plot threads, canon entries, timeline entries, manuscripts, knowledge, artifacts, foreshadowing, and editorial records. Low/medium/high estimated narrative risk and `requires_confirmation` make high-impact decisions explicit before application.

## AI Narrative Reviewer

Run Story Audit for a read-only AI review. StoryAuditorAgent consumes the same analysis snapshot and findings plus bounded chapter memory. Its scope explicitly covers pacing, repetition, emotional rhythm, structural weaknesses, continuity, unresolved threads, chapter balance, and tension progression. It can persist findings and recommendations but cannot rewrite drafts, change canon, edit planning, or mutate the Story Bible.

## Background and incremental analysis

Interactive reads use the current snapshot or run incremental analysis. A caller can POST `{"background": true}` to `/narrative-analysis`, then inspect the persisted job endpoint. Source fingerprints reuse unchanged graph nodes; unchanged projects are cache hits, and a single edited chapter invalidates only that chapter node before derived project checks refresh.

