# NovelForge V2 RC6 Test Results

## Final status

| Gate | Result |
| --- | --- |
| Backend regression | PASS — 114 passed, 7 skipped |
| Final RC6/backend compatibility subset | PASS — 15 passed |
| Frontend regression | PASS — 62 passed in 16 files |
| Production build | PASS — compiled, linted, and type-checked |
| Playwright | PASS — 45 passed, 2 provider-gated tests skipped |
| Desktop matrix | PASS — 12 checks |
| Serious accessibility scan | PASS |
| Live Gemini call | PASS — `gemini-3.1-flash-lite`, HTTP 200 |
| Database integrity audit | PASS — no findings |

## Backend

Full command:

```text
py -3.11 -m pytest backend/tests -q
```

Result: **114 passed, 7 skipped**.

Final compatibility subset:

```text
py -3.11 -m pytest backend/tests/test_rc6_commercial_experience.py backend/tests/test_post_rc5_hardening.py backend/tests/test_manuscript_v3.py -q
```

Result: **15 passed**.

Coverage includes:

- Story Health semantic duplicate prevention;
- seven-step Creation Guide completion and skip/edit behavior;
- decision history, change, undo, and question reopening;
- Shared Narrative Context supersession and provenance;
- canon approval propagation;
- companion recommendation identity, cooldown, dismiss, and completion;
- shared publication readiness and legacy compatibility;
- incremental Narrative Analysis;
- workspace bootstrap;
- project-library pagination and favorites;
- actionable workspace entry creation;
- manuscript approval and export governance.

The remaining output is 80 dependency deprecation warnings from Pydantic v2 compatibility APIs. No test failed because of them.

## Frontend

Command:

```text
npm test -- --run
```

Result: **16 files and 62 tests passed**.

The suite covers the RC6 beginner guide, API contracts, workspace store/bootstrap behavior, Story Health presentation, assistant navigation, companion behavior, settings, manuscript governance, planning, drafting, and prior product-experience regressions.

## Production build

Command:

```text
npm run build
```

Result:

- optimized production compilation passed;
- lint passed;
- TypeScript validation passed;
- static and dynamic routes generated;
- no build warning, hydration warning, or React key warning was emitted.

## Playwright

The Chromium project contains 47 tests in 22 specifications. Long real-provider workflows were executed in bounded groups to avoid a single harness timeout.

Final result: **45 passed, 2 skipped**.

The two skips are the dedicated opt-in tests in `real-provider.spec.ts`. Real-provider behavior was nevertheless exercised by the other workflow specifications.

Passed browser coverage includes:

- new-project and amateur-author guided setup;
- decision editing and undo;
- actionable empty states;
- server project library and overflow actions;
- dashboard, settings, and navigation;
- RC5/RC6 product intelligence;
- Story Health and Story Intelligence;
- canon and manuscript governance;
- workflow orchestration;
- arc development, drafting, editorial, and readiness;
- interactive narrative studio;
- frozen Paragraph Editor regressions;
- 12 desktop-layout checks;
- accessibility and package download.

## Real Gemini validation

The active provider configuration was loaded from the database:

```text
provider=gemini
model=gemini-3.1-flash-lite
```

The StoryAuditorAgent test issued:

```text
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent
```

Result: **HTTP/1.1 200 OK**.

Arc, drafting, editorial, orchestration, interactive narrative, manuscript, readiness, and Story Intelligence workflows also completed with the configured Gemini model during split Playwright validation.

## Performance measurements

Local live API, 20 warm requests per endpoint:

| Endpoint | Median | p95 | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Workspace bootstrap | 88.6 ms | 111.4 ms | 78.6 ms | 129.3 ms |
| Project library, 24 items | 60.2 ms | 134.4 ms | 57.3 ms | 138.0 ms |

The existing 500-chapter regression verifies:

- 500 narrative nodes are analyzed;
- a fully unchanged second run reuses all 500 nodes;
- the cache-hit flag is true;
- full analysis remains below the 15-second test ceiling.

The architecture benchmark artifact retains the more precise engine measurements: 0.9538 s full, 0.1060 s cached, and 0.2140 s for one changed chapter with 499/500 nodes reused.

## Integrity audit

`GET /api/projects/{project_id}/audit` was run against a live local project after validation.

Result:

```text
project_exists=true
status=pass
findings=[]
```

## Known validation limitations

- The in-app Browser connector reported no available browser instance. Live UI acceptance therefore used the repository's Playwright-controlled Chromium browser.
- A monolithic Playwright invocation exceeded the outer 15-minute command budget because multiple real AI workflows are intentionally long. Every specification was then completed in smaller runs.
- Pydantic deprecation warnings remain technical debt for a future dependency-maintenance release.

