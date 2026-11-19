# NovelForge V2 RC5 Test Results

## Post-RC5 validation update — 2026-07-23

| Gate | Result |
| --- | --- |
| Backend | 110 passed, 7 skipped, 81 dependency migration warnings, 376.61 s |
| Frontend | 15 files passed, 60 tests passed, 34.82 s |
| Production build | Passed; project route 207 kB, first load 357 kB |
| npm audit | 0 vulnerabilities |
| Playwright | 43 executable scenarios passed, 2 conditional skips, 0 unresolved failures |
| Accessibility | Axe serious/critical findings: 0 on Projects and primary workspace |
| Gemini | `gemini-3.1-flash-lite`; 104 HTTP 200 responses, 0 HTTP errors in the final provider-backed run |
| 500-chapter benchmark | 1.924 s uncached, 0.109 s cached |
| Database integrity | Pass, 0 findings on a production project |

The complete 45-test Playwright inventory was executed twice. The first run found nine defects or stale expectations; all nine passed targeted reruns after correction. The final complete run passed 42, conditionally skipped 2, and hit one invalid `networkidle` wait on the EventSource-backed accessibility page. Replacing that wait with visible product anchors made the accessibility scenario pass in 36.9 seconds. No application failure remains.

Date: 2026-07-19  
Result: passed

## Backend regression

Command:

```powershell
cd backend
py -3.11 -m pytest
```

Result: **104 passed, 7 skipped** in 315.14 seconds.

The skipped cases are pre-existing conditional/integration cases. The suite reported dependency migration notices from Pydantic, FastAPI, LangChain, and pytest-asyncio; no backend test failed.

The RC5-specific backend coverage verifies:

- complete Application Knowledge catalog and valid navigation destinations;
- application, project, and combined Assistant routing;
- application questions answered without narrative-context retrieval;
- Project Timeline and Explainability Timeline projections;
- stable Companion recommendations, lifecycle actions, cooldowns, and recap state.

## Frontend regression

Command:

```powershell
cd frontend
npm test -- --run
```

Result: **15 files passed, 60 tests passed** in 31.27 seconds.

The RC5 component tests cover contextual page guidance, author-readable values, application/project Assistant presentation, Companion visual state, recommendation actions, and reduced-motion behavior. Vite emitted only its Node CJS API deprecation notice.

## Production build

Command:

```powershell
cd frontend
npm run build
```

Result: **passed**. Next.js compiled, type-checked, generated routes, and emitted no application build warning.

- `/project/[projectId]`: 205 kB route bundle
- `/project/[projectId]` first load: 354 kB
- shared first-load JavaScript: 99.2 kB

## Playwright desktop verification

The complete discovery run executed **41 tests**: 34 passed, 2 were conditionally skipped, and 5 old assertions failed because they expected UI content intentionally removed or renamed by RC5. Those assertions were updated without weakening product checks.

Targeted reruns then passed all five corrected tests: four passed in the first rerun and the final Phase 7 selector passed in the second rerun. Cumulative closure result: **39 executable tests passed, 2 conditionally skipped, 0 remaining failures**.

Coverage includes:

- exact desktop viewports: 1366×768, 1440×900, 1920×1080, and 2560×1440;
- every workspace section, direct recommendation navigation, and Canon Queue discoverability;
- application-first Assistant answers and navigation actions;
- Project Timeline and Story Health explainability history;
- author-readable Knowledge Graph cards without raw JSON or metadata;
- Companion appearance, state animation, lifecycle actions, deduplication, and reduced-motion support;
- Developer Mode gating for workflow and technical settings;
- governed Drafting with no fabricated placeholder manuscript;
- browser console warnings, errors, uncaught page errors, duplicate-key warnings, and hydration warnings.

The dedicated RC5 browser capture completed with an empty application warning/error list. The polished Companion was also visually reviewed at 1440×900; evidence is stored in `artifacts/rc5-workspace-companion-desktop.png`.

## Real Google AI Studio verification

The database-configured Google AI Studio provider was exercised with **Gemini 3.1 Flash Lite** during Assistant and analysis verification. Provider requests returned HTTP 200 responses. The stored credential was used through the existing protected settings path and was not printed or copied into reports.

## Large-project benchmark

Command:

```powershell
py -3.11 -m pytest backend/tests/test_product_experience_completion.py::test_product_experience_large_novel_benchmark -q -s
```

Result: **1 passed**.

| Workload | Measured time |
| --- | ---: |
| 500-chapter uncached product experience analysis | 1.983 s |
| Cached Narrative Analysis reuse | 0.118 s |

The benchmark covers Narrative Analysis, Narrative Completeness, Narrative Critique, and Workspace Companion projections. It confirms that RC5 consumes the cached analysis contract rather than creating a second narrative-analysis path.

## Console and warning disposition

No React duplicate-key, undefined-key, hydration, or application console warnings remain in the audited Chromium workflow. Remaining command-line notices are dependency/toolchain deprecations and are listed in `RC5_CONSOLE_WARNING_REPORT.md`.
