# NovelForge Narrative Studio V2 - Phase 3C E2E Results

Validation date: 2026-06-14

## Result

Passed.

Full Playwright result: 25 passed, 2 conditional skips, 0 failures.

The final run took 18.1 minutes and included all legacy real-Gemini workflows,
the Phase 3C Story Auditor, production workspace screenshots, mobile
validation, and UI stability checks.

## Production Corpus

| Metric | Result |
| --- | --- |
| Project ID | `6a2ef4727851cfbde7d3b439` |
| Isolation project ID | `6a2ef4727851cfbde7d3b43a` |
| Arcs | 2 |
| Arc chapter spans | 22 and 28 |
| Approved chapters | 50 |
| Words | 89,063 |
| Story health score | 80 |
| Audit result | WARNING |
| Audit findings | 10 |
| Story Bible version | 2 |
| Isolation leaks | 0 |
| Chapter 45 memory | present |
| Chapter 50 memory | present |

## Long-Range Memory

The final memory layer retained:

- Chapter 4 obligation: return the broken bell clapper before the thaw vote;
- Chapter 9 obligation: tell Soren who ordered the dockworkers' oath erased.

Chapters 45 and 50 remained present in the current Story Bible chapter
intelligence while the old obligations remained available outside the recent
chapter window.

## Human Workflow Coverage

The combined regression and E2E suite exercised:

- gradual planning and readiness changes;
- character, mystery, world, knowledge, and arc planning;
- scene and chapter generation;
- scene regeneration and version rollback;
- draft review, rejection, and approval gates;
- editorial reports and revision branches;
- revision rejection and approval;
- manuscript assembly, versions, validation, approval, and rollback;
- canon promotion, conflict detection, and conflict status;
- author-controlled change impact approval and rejection.

## Navigation And Layout

The workspace smoke test opened all 26 sidebar sections:

`discussion`, `vision`, `story-room`, `story-health`, `characters`, `world`,
`power`, `factions`, `relationships`, `threads`, `themes`, `mysteries`,
`readiness`, `knowledge`, `timeline`, `arcs`, `arc-development`, `questions`,
`insights`, `drafting`, `editorial`, `manuscript`, `canon`, `workflow`, and
`settings`.

Projects, project workspace, and AI Settings were validated at widths of 1280,
1440, 1920, and 2560 pixels with no horizontal overflow. Story Health was also
validated at 390 by 844 pixels.

## Real Gemini

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

Configured limit: 5 requests per minute

The final suite passed real-provider paths for planning, drafting, editorial,
manuscript, canon, and Story Auditor execution.

Latest Story Auditor trace:

| Metric | Result |
| --- | --- |
| Status | success |
| Latency | 4,366 ms |
| Tokens | 7,924 |
| Cost | $0.003170 |
| Retries | 0 |
| Fallback | false |

## Corrective Retry Validation

An earlier full-suite run exposed a valid JSON SceneWriter response with an
empty mandatory prose field. Phase 3C added one bounded corrective retry.

Verification:

- forced-empty backend regression passed;
- combined token and latency metadata persisted;
- exact real-Gemini drafting E2E passed in 2.3 minutes;
- final full Playwright passed.

## Screenshots

- `artifacts/phase-3c-story-health.png`
- `artifacts/phase-3c-story-room.png`
- `artifacts/phase-3c-arc-workspace.png`
- `artifacts/phase-3c-editorial-workspace.png`
- `artifacts/phase-3c-manuscript-workspace.png`
- `artifacts/phase-3c-canon-dashboard.png`

## Test Matrix

| Surface | Result |
| --- | --- |
| Backend | 80 passed, 7 skipped |
| Frontend | 49 passed |
| Next.js production build | passed |
| Dedicated Phase 3C E2E | 3 passed |
| Exact repaired Gemini drafting E2E | 1 passed |
| Full Playwright | 25 passed, 2 skipped |
| Browser console review | no actionable errors |
