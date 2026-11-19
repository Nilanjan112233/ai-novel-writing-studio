# NovelForge Narrative Studio V2 - Phase 2A E2E Results

Validation date: 2026-06-14

## Result

Passed.

Scenario: `The Last Kingdom of Aether 1781382172858`

Project ID: `6a2dbc1cfa02f93a7f358be6`

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

## Arc Results

| Arc | Focus | Lifecycle | Maturity | Draftable |
| --- | --- | --- | ---: | --- |
| Arc 1: The Aether Crown | current | draftable | 100 | yes |
| Arc 2: The Broken Meridian | next | development | 54 | no |
| Arc 3: Beyond the Last Road | future | idea | 4 | no |

The initial concept cycle also proposed one additional future idea arc. It
remained non-draftable and did not affect current-arc gating.

Only Arc 1 became draftable. Arc 2's incomplete dependency remained valid, and
Arc 3 remained a legal placeholder.

## Persisted Planning Evidence

- 48 checklist rows across four arcs
- 1 typed arc dependency
- 3 chapter plans
- 3 Scene Plan V2 records
- 1 character progression
- 1 power progression
- 8 timeline entries
- 3 knowledge entries
- 1 knowledge evolution
- 1 foreshadow registry record
- 4 foreshadow chain nodes
- 1 artifact registry record
- 3 artifact evolution events

The chapter-plan prose injection test returned HTTP 400.

## Orchestration Results

| Cycle | Selected agents | Calls | Skipped |
| --- | --- | ---: | ---: |
| Concept | Narrative Director, Story Architect, Question, Theme, Arc Architect, Pacing | 6 | 9 |
| Arc development | Arc Architect, Pacing, Readiness, Story Development, Character Journey, Relationship, Power System, Knowledge, Mystery, World | 10 | 5 |
| World-only | World, Faction | 2 | 13 |

Totals:

- cycles: 3
- actual calls: 18
- skipped tasks: 27
- skip percentage: 60%
- average calls per cycle: 6
- reduction against current 15-task eligibility set: 60%
- reduction against legacy static 12-agent cycles: 50%
- recorded cost: USD 0.065444

`StoryDevelopmentAgent` executed for arc work and was explicitly skipped for
the world-only cycle.

## Provider Traces

- 18 successful Gemini traces
- 163,611 recorded input/output tokens
- configured rate limit: 5 requests/minute
- total limiter wait: 45,921 ms
- maximum single limiter wait: 26,890 ms
- Phase 2A retries: 0

The wider Playwright regression observed one Gemini 503 during Phase 1B and
successfully recovered through exponential backoff.

## UI Validation

The test opened:

- Arc Development Workspace
- Story Room

It verified draftable status, chapter plans, scene plans, current arc focus,
and real agent proposals.

Screenshot:

`test-results/arc-development-v2-Phase-2-bd0d6-er-without-generating-prose-chromium/last-kingdom-of-aether-story-room.png`

## Full Test Matrix

- Backend: 62 passed, 7 skipped
- Frontend: 45 passed
- Production build: passed
- Phase 2A Playwright: 1 passed
- Remaining Playwright matrix: 18 passed, 2 skipped
- Combined Playwright: 19 passed, 2 skipped

The two skips are environment-variable-gated real-lifecycle reuse cases.
Phase 1A, Phase 1B, and Phase 2A real Gemini scenarios all executed and passed.

