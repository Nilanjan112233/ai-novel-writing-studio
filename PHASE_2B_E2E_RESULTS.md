# NovelForge Narrative Studio V2 - Phase 2B E2E Results

Validation date: 2026-06-14

## Result

Passed.

Scenario: `The Crown of Emberfall 1781418280707`

Project ID during execution: `6a2e492800d68c5ffa4fc04c`

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

The Playwright fixture data was removed after the report and screenshot were
captured. The embedded Playwright attachment preserves the metrics below.

## Planning Gates

Arc 1, `The Remembering Flame`, reached:

- readiness: READY;
- maturity: 100;
- approval: approved;
- focus: current;
- development state: draftable;
- checklist blockers: 0;
- dependency blockers: 0.

The test created three approved chapter plans and six approved Scene Plan V2
records. Every draft request re-evaluated the current planning gates rather
than trusting a stale flag.

Arc 2 remained partial and Arc 3 remained a placeholder. Both draft requests
returned HTTP 409 before provider execution.

## Draft Results

| Subject | Generated | Reviewed | Approved | Active |
| --- | ---: | ---: | ---: | ---: |
| Scene drafts | 6 | 6 | 6 | 6 |
| Chapter drafts | 3 | 3 | 3 | 3 |

Chapter assembly used two approved scene drafts per chapter. The deterministic
assembler preserved scene text and order and inserted transitions only
between adjacent source drafts.

No draft was approved automatically.

## Continuity Results

Each of the nine drafts produced:

1. one post-generation validation report;
2. one fresh approval validation report.

Results:

- reports evaluated: 18;
- PASS: 18;
- WARNING: 0;
- FAIL: 0;
- review queue continuity warnings: 0.

Separate backend tests verified that a FAIL prevents approval, undeclared
authority claims are rejected, and partial arcs cannot generate.

## Versioning Results

Backend integration tests verified:

- monotonic scene and chapter versions;
- parent-version lineage;
- one active version per scene/chapter;
- regeneration without content overwrite;
- rejection and archive transitions;
- rollback to a preserved historical version;
- approved-source enforcement during chapter assembly.

## Orchestration Results

Nine explicit demand-driven plans were created:

| Operation | Plans | Selected agent | Agents skipped per plan |
| --- | ---: | --- | ---: |
| Scene generation | 6 | `SceneWriterAgent` | 16 |
| Chapter assembly | 3 | `ChapterAssemblerAgent` | 16 |

Totals:

- plans: 9;
- provider calls: 9;
- selected agents per plan: 1;
- skipped tasks: 144;
- task skip percentage: 94.1%;
- static pipeline executions: 0.

The explicit-plan backend assertions also verify that skip reasons are
persisted and available through the Phase 1A orchestration APIs.

## Provider Metrics

- successful Gemini traces: 9
- tokens: 32,973
- recorded cost: USD 0.013190
- total limiter wait: 22,984 ms
- configured limit: 5 requests/minute
- maximum admissions in any rolling 60-second window: 5
- retries: 0
- scenario duration: 128.177 seconds

Provider traces record the actual limiter admission timestamp, retry metadata,
wait duration, configured limit, provider, model, tokens, and cost.

## Authority And Security

Verified:

- scene drafts require approved scene and chapter plans;
- chapter drafts require active approved scene versions;
- cross-project arc/chapter/scene/draft references are rejected;
- generated claims cannot update planning collections;
- future incomplete arcs do not block the current arc;
- future incomplete arcs cannot draft;
- provider credentials remain masked in settings responses;
- no bypass endpoint invokes a writer without gate validation.

## UI Validation

Playwright opened the Controlled Drafting workspace and verified:

- `Drafting gates satisfied`;
- all six scene titles;
- all three chapter titles;
- approved status;
- continuity status;
- review and history presentation.

Screenshot:

`test-results/drafting-v2-Phase-2B-contr-3f8d7-real-Gemini-authority-gates-chromium/crown-of-emberfall-drafting.png`

The same UI was inspected in the in-app browser. Console errors: 0. Console
warnings: 0.

## Full Test Matrix

- Backend: 66 passed, 7 skipped
- Frontend: 45 passed
- Production build: passed
- Full Playwright matrix: 20 passed, 2 skipped
- Final Phase 2B real-Gemini run: 1 passed
- Migration rerun: passed

Acceptance gates for controlled drafting, authority preservation, versioning,
rollback, validation, review, dynamic orchestration, rate limiting, and real
Gemini execution all passed.
