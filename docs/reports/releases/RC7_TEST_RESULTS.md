# NovelForge V2 RC7 — Final Test and Acceptance Report

## Release decision

**RC7 validation passed.**

The implementation, regression, build, accessibility, desktop, live-provider,
database-integrity, and measured-performance gates are green. The live
narrative-quality audit also behaved correctly: it accepted the focused novice
scene as a useful draft and rejected a separate deliberately repetitive
multi-chapter planning fixture instead of presenting weak material as
publication-ready.

## Automated regression

| Gate | Result | Evidence |
|---|---:|---|
| Backend | **118 passed, 7 skipped** in 529.76 seconds | `artifacts/rc7-backend-full-rerun.stdout.log` |
| Frontend | **17 files, 63 tests passed** in 40.60 seconds | `artifacts/rc7-frontend-final.log` |
| ESLint | **Passed with zero warnings** | `artifacts/rc7-eslint-final.log` |
| Production build | **Passed** with type checking and seven generated routes | `artifacts/rc7-production-build.log` |
| Playwright Chromium | **46 passed, 2 environment-conditional tests skipped** in 26.8 minutes | `artifacts/rc7-playwright-full-final.stdout.log` |

The backend skips are established optional/integration cases. The browser suite
executed the configured real-provider lifecycle; its two conditional variants
do not remove coverage from the primary Gemini journeys.

## Live browser acceptance

The final Playwright run started the real frontend and FastAPI backend, used
MongoDB persistence, and called the configured
`gemini-3.1-flash-lite` model. It covered:

- first-time project creation and all seven beginner foundation steps;
- the planning-to-writing transition;
- an exploratory first scene with visible approval blockers;
- reader-facing generation, explanation, review, companion coaching, and
  assistant guidance;
- six approved scenes across three chapters and three assembled chapters;
- editorial, dialogue, revision, manuscript, canon, Story Bible, Narrative
  Intelligence, and export workflows;
- reload, navigation history, project switching, and workspace recovery;
- protected Paragraph Editor versions, restore, autosave, undo/redo, comments,
  and AI suggestion review;
- console cleanliness and non-duplicated output;
- project and workspace layouts at 1366x768, 1440x900, 1920x1080, and
  2560x1440.

The RC7 amateur-author journey captured no browser console warning, browser
console error, or page error.

## Accessibility

The browser suite passed the existing axe-based projects/workspace check with
no serious accessibility violations. It also verified keyboard-accessible
controls, visible workspace behavior at constrained viewports, ARIA-labelled
writing actions, and reduced-motion support for the Workspace Companion.

## Real Gemini and agent health

The final browser log contains **93 HTTP 200** responses from Google AI Studio
and no provider HTTP 4xx or 5xx response. MongoDB contains **92 successful
execution traces**, zero failed traces, zero fallbacks, and zero recorded
retries for the final acceptance window.

All **24 active Narrative Studio agents** have successful real
`gemini-3.1-flash-lite` evidence. The bounded Scene Planner probe returned its
structured contract without persisting a duplicate scene plan. Provider
validation is recorded separately from the agent roster.

Detailed per-agent call counts and latency are in
`artifacts/rc7-agent-health.json`.

## Database integrity

The integrity audit ran after the final browser suite against the exact latest
projects:

- `RC7 Amateur Draft 1785076004034` — **pass**, zero findings;
- `The Crown of Emberfall 1785075074329` — **pass**, zero findings.

The audit checked project ownership, duplicate artifact keys, cycle metadata,
question/decision references, Story Bible existence, and mock-data leakage.
Evidence is in `artifacts/rc7-database-integrity.json`.

## Performance

| Chapters | Bootstrap cold | Bootstrap cached | Writing dashboard cold | Dashboard cached median | Scene history (100 rows) |
|---:|---:|---:|---:|---:|---:|
| 100 | 1,411.21 ms | 8.02 ms | 102.59 ms | 88.38 ms | 4.85 ms |
| 250 | 2,005.44 ms | 9.88 ms | 99.50 ms | 99.75 ms | 3.52 ms |
| 500 | 3,497.50 ms | 23.32 ms | 123.89 ms | 109.37 ms | 4.20 ms |
| 1,000 | 6,765.67 ms | 33.05 ms | 214.13 ms | 158.49 ms | 7.55 ms |

The cached 1,000-chapter bootstrap is about 205 times faster than the cold
projection. Scene history remains below 8 ms in the measured synthetic
fixtures. Full benchmark data is in
`artifacts/rc7-writing-performance.json`.

The production project route reports 217 kB route JavaScript and 368 kB First
Load JavaScript. This is acceptable for RC7 but remains a code-splitting
opportunity.

## Narrative-quality acceptance

The novice scene had a concrete goal, active trouble, personal and public
stakes, a forward handoff, sensory emotional subtext, and no long exposition
dump. It also proved that newly invented stable facts enter the Canon Proposal
Queue rather than silently becoming canon.

The separate six-scene fixture was intentionally created with the same generic
purpose, conflict, and outcome on every scene. The Story Auditor reported 27
raw issues consolidated to 20 findings:

- 1 high continuity warning;
- 11 repetitive-scene findings;
- 1 repetitive chapter-opening finding;
- 6 unresolved-promise findings;
- 1 unresolved-thread finding.

This is a **product-behavior pass and a manuscript-readiness failure**.
NovelForge identified the weak plan and withheld a false quality claim. RC7
now exposes duplicate-plan coaching before final prose, derives distinct
progression from the linked timeline event, and preserves author control rather
than silently rewriting the plan. The raw report is
`artifacts/rc7-live-story-audit.json`.

## Warnings and limitations

The backend suite reports 81 migration deprecation warnings: 80 from legacy
Pydantic v2 compatibility paths and one pending LangGraph default change.
There are no React key, hydration, production-build, ESLint, or captured
browser-console warnings.

Remaining non-blocking limitations are documented in
`RC7_KNOWN_LIMITATIONS.md`.
