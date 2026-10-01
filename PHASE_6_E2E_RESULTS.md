# Phase 6 E2E and Validation Results

## Backend

- Full suite: `py -3.11 -m pytest backend/tests -q`
- Result after live-provider stabilization: **89 passed, 7 skipped** in 264.60 seconds.
- Warnings: 86 dependency/framework deprecation warnings; no ignored test failures.
- Phase 6 focused and Story Auditor regression suite: **6 passed**.
- Post-stabilization lazy Story Bible/integrity regression: **6 passed**.
- The seven skips are existing provider-dependent tests in an environment without external provider credentials.

The full suite initially exposed a missing local Jinja2 installation in a frozen paragraph regression. Jinja2 was already declared in `backend/requirements.txt`; installing the declared dependency restored that test without changing paragraph behavior.

## Frontend

- Command: `npm test -- --run` from `frontend/`.
- Result: **49 passed across 11 files**.
- The formerly noisy polling test mock was completed, so the final unit run has no application error output.

## Production build

- Command: `npm run build` from `frontend/`.
- Result: **passed**.
- Routes built: `/`, `/dashboard`, `/project/[projectId]`, `/projects`, `/settings`.
- `/project/[projectId]`: 193 kB route bundle, 341 kB first-load JavaScript.
- Two pre-existing React hook warnings remain in `AiSuggestionPanel.tsx` and the frozen `ParagraphEditor.tsx`; neither failed lint/type checking/build/runtime tests.

## Playwright

- Phase 6 focused test: desktop and 390px mobile primary Story Health, all seven domain APIs, cache hit, keyboard focus, no mobile horizontal overflow, Canon/Timeline/Character/Plot navigation, and evidence empty state.
- Project workflow regression: project creation/navigation and project library controls.
- UI stability: Projects, Workspace, and AI Settings at 1280, 1440, 1920, and 2560 widths.
- Final scoped matrix: **15 passed in 1.4 minutes**. The result is recorded in `test-results/.last-run.json` and the HTML report.
- Captures:
  - `artifacts/phase6-story-health-desktop.png`
  - `artifacts/phase6-story-health-mobile.png`

The matrix found and closed two issues: synchronous Story Bible construction delayed project creation in a populated database, and the desktop toolbox remained open on mobile. Story Bible construction now uses its existing lazy path, and mobile opens with the toolbox collapsed.

## Performance

Command: `py -3.11 backend/scripts/run_phase_6_benchmark.py`

| Scenario | Wall time | Recomputed | Reused | Graph |
|---|---:|---:|---:|---:|
| Full analysis | 0.9538 s | 500 | 0 | 500 nodes / 499 edges |
| Cache hit | 0.1060 s | 0 | 500 | 500 nodes / 499 edges |
| Single chapter edit | 0.2140 s | 1 | 499 | 500 nodes / 499 edges |

Machine-readable results: `artifacts/phase6-performance-benchmark.json`.

## Provider note

The encrypted Google AI Studio credential already present in the canonical database settings was validated without exporting or printing it.

- Credential catalog validation: **passed**.
- Requested model discovery: `gemini-3.1-flash-lite` was present among 18 discovered Gemini models.
- Direct provider-gateway model test: **passed**, 1,622 ms, 6 reported tokens.
- Live 50-chapter StoryAuditorAgent review: **passed through the provider**, 9 deterministic findings plus 3 AI findings, successful execution trace, persisted orchestration plan, and 8,067 ms end-to-end API duration.
- Playwright-generated live trace: provider latency 4,537 ms, 2,718 prompt tokens, 858 response tokens, no provider error.
- Scoped Playwright real-provider check: **1 passed in 21.0 seconds**.

The first live whole-novel run exposed a 30,000-character prompt guard failure. StoryAuditor now consumes a severity-prioritized, evidence-preserving projection of the shared analysis graph with a 22,000-character internal budget instead of duplicating the full graph, chapter memory, canon, and decisions. The large-context regression and existing Story Intelligence tests pass.
