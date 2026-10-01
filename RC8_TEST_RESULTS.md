# NovelForge V2 RC8 — Test Results

## Release-gate result

All RC8 gates for the supported local/private deployment passed on 2 August
2026. The configured stack used FastAPI, MongoDB, Next.js/Chromium, and Google
Gemini `gemini-3.1-flash-lite`. No primary browser or provider workflow was
mocked in the release Playwright pair or 50-scene soak.

## Automated regression

| Gate | Command | Result | Evidence |
|---|---|---:|---|
| Backend | `py -3.11 -m pytest -q` | 134 passed, 7 skipped | `artifacts/rc8-backend-final.log` |
| Frontend | `npm run test -- --run` | 19 files, 71 passed | `artifacts/rc8-frontend-final.log` |
| ESLint | `npm run lint` | 0 warnings/errors | `artifacts/rc8-eslint-final.log` |
| Production build | `npm run build` | passed | `artifacts/rc8-production-build-final.log` |
| Playwright pass 1 | `npx playwright test --reporter=line` | 48 passed, 2 skipped; 24.6 min | `artifacts/rc8-playwright-release-pass-1.log` |
| Playwright pass 2 | same command, unchanged candidate | 48 passed, 2 skipped; 23.3 min | `artifacts/rc8-playwright-release-pass-2.log` |
| Database integrity | `py -3.11 scripts/run_rc8_database_integrity.py` | passed | `artifacts/rc8-database-integrity.json` |

The seven backend skips are deliberate environment/legacy workflow skips, not
new RC8 failures. The suite reports 66 Pydantic/LangGraph compatibility
warnings; they are documented and do not affect current execution.

## Required RC8 invariants

`backend/tests/test_rc8_launch_hardening.py` contributes 15 explicit tests and
the wider regression proves the contracts around them:

1. failed writing operations remain visible, safe, and retryable;
2. Writer's Room leaves the active approved source unchanged;
3. bounded Character Conversation rejects future and unknown knowledge;
4. simultaneous request IDs reuse one logical generation without HTTP 500;
5. semantic story labels reconcile to stable internal identities;
6. scenes sort by chapter number and scene order, not UUID;
7. all seven beginner AI actions return narrative-development content;
8. equivalent findings affect Story Health once;
9. publication blockers explain the problem and navigate to its owner;
10. provider HTTP success followed by application rejection is recorded as an
    application failure.

Frontend regression additionally verifies the persistent failure banner,
writing/dashboard readiness language, Workspace Companion lifecycle, beginner
flow, scalable editorial/drafting surfaces, and Assistant navigation.

## Real-stack Playwright

Two consecutive, clean-state full runs passed. Coverage includes:

- novice, writing, planning, revision, manuscript, publication, and resume
  journeys;
- real Gemini story development, SceneWriter, editor, and assistant paths;
- frozen Paragraph Editor productivity, planning, history, AI suggestion, and
  layout regressions;
- accessibility checks, focus/error announcements, reduced motion, and console
  warning checks;
- 1280×720 with Toolbox plus Companion, and 1366×768, 1440×900,
  1920×1080, and 2560×1440 desktop layouts.

Pass 1 observed one transient provider network failure; the bounded retry
recovered and the test passed. This is positive recovery evidence, not a hidden
failure.

The dedicated `novelforge_e2e` database was empty after each run. Final state:
0 projects, 0 model records, 30 exactly recorded/cleaned project IDs. The normal
`novelforge` project count remained 2,657.

## Real Gemini 50-scene soak

Artifact: `artifacts/rc8-gemini-50-scene-soak.json`.

| Measure | Result |
|---|---:|
| Chapters / scenes | 10 / 50 |
| Usable scenes | 50 |
| Approved scenes | 50 |
| Completion | 100% (target >=95%) |
| Total generated words | 14,650 |
| Median / p95 latency | 11.02 s / 17.72 s |
| Maximum latency | 21.45 s |
| Duplicate request records | 0 |
| Chapter drafts generated | 10/10 |

Writer's Room produced three inactive alternatives while the source remained
active and approved. Revision, editorial review, canon approval, Narrative
Analysis, and Story Audit passed. The unsafe Character Conversation was visibly
withheld with no memory saved. Manuscript assembly was visibly blocked because
chapter drafts had not been explicitly approved; publication preflight returned
seven actionable blockers. The soak database was exactly cleaned.

## Character chronology adversarial probe

Artifact: `artifacts/rc8-real-character-chronology.json`.

- Direct request for hidden causes/future fate: HTTP 409, response withheld, no
  forbidden text, no response or memory saved.
- Indirect request for later knowledge: HTTP 200, safe response, no forbidden
  text, five allowed evidence items.
- Dedicated database cleanup: passed.

## Performance

Artifact: `artifacts/rc8-launch-performance.json`.

| Chapters | Cold bootstrap | Warm bootstrap | Writing Desk | Drafting first 60 | Editorial first 60 |
|---:|---:|---:|---:|---:|---:|
| 100 | 2.04 s | 10.60 ms | 95.98 ms | 2.92 ms | 4.32 ms |
| 250 | 2.18 s | 17.12 ms | 106.16 ms | 2.41 ms | 2.95 ms |
| 500 | 3.69 s | 24.22 ms | 117.06 ms | 3.80 ms | 4.45 ms |
| 1,000 | 7.24 s | 52.55 ms | 152.82 ms | 2.81 ms | 6.79 ms |
| 2,000 stress | 12.31 s | 70.55 ms | 222.86 ms | 2.43 ms | 17.19 ms |

Canon Queue and Project Timeline also used bounded first-60 queries. Working-set
memory was unavailable, so no memory-efficiency claim is made.

## Integrity and boundaries

The integrity runner found no findings in the latest novice or multi-chapter
acceptance projects. RC8 is validated for trusted local/private desktop-style
deployment. Hosted multi-tenant security is not covered and remains a separate
audit gate.
