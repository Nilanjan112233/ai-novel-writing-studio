# NovelForge V2 RC9 — Test Results

Date: 2026-08-03

## Release gates

| Gate | Result | Reproducible evidence |
|---|---:|---|
| Backend regression | PASS | Final release run: 153 passed, 7 skipped; see `artifacts/rc9-backend-full-release.txt`. Earlier post-timeout run: 152 passed, 7 skipped in 603.58 s. |
| Frontend regression | PASS | 22 files and 83 tests; `artifacts/rc9-frontend-full-final.txt`. |
| ESLint | PASS | Zero warnings/errors; `artifacts/rc9-lint-final.txt`. |
| Production build | PASS | Next.js 15.5.22 production build; `artifacts/rc9-build-final.txt`. |
| npm audit | PASS | Frontend and root scopes report zero vulnerabilities; `artifacts/rc9-frontend-audit-final.txt` and `artifacts/rc9-root-audit-final.txt`. |
| Targeted RC9 Playwright | PASS | Backup/restore/privacy/support journeys: 2 passed in 1.6 min; `artifacts/rc9-playwright-targeted-final.txt`. |
| Full real-stack Playwright | PASS | 50 passed, 2 intentionally conditional tests skipped, 0 failed in 28.6 min; `artifacts/rc9-playwright-full-final.txt`. |
| Database integrity | PASS | Representative projects and dedicated E2E isolation passed; `artifacts/rc9-database-integrity-final.txt`. |
| Dedicated E2E cleanup | PASS | 32 exact project IDs cleaned; projects, backups, restores, support bundles, feedback and models all zero afterward in `novelforge_e2e`. |
| Docker Compose validation | PASS | `docker compose config --quiet` exit 0. |
| Windows launcher syntax | PASS | All five PowerShell launchers parsed with zero errors. |
| Secret/log source scan | PASS | No credential-like source matches; Gemini key moved to header; raw provider body logging removed. |

The two Playwright skips are environment/lifecycle guards in the real-provider suite, not failed product assertions: one avoids recreating an already supplied completed lifecycle and one requires a supplied lifecycle project for visual verification.

## Mandatory RC9 behavior evidence

- Backup create, download checksum, validation, import, restore-as-copy, identity remapping and post-restore Story Bible availability pass.
- Corrupt archives are rejected before persistence.
- Simulated post-restore verification failure rolls back the incomplete copy and preserves the original.
- Two concurrent restores plus a retry with the same request identity return one restored project and one logical operation.
- Backup-all reports per-project partial failures and preserves completed archives.
- Pre-RC6, RC6, RC7 and RC8 synthetic legacy projects migrate additively and a second migration makes no content changes.
- The strengthened compatibility fixture then passed 3/3 focused checks while preserving scene prose, paragraph versions, canon, decisions, Story Bible and Narrative Intelligence records byte-for-value across migration.
- Expired migration ownership is safely recovered and migration completion is durable.
- Support bundle tests inject both credential-shaped and story-text canaries; neither appears in the archive.
- AI-unconfigured readiness is `offline_ready`; projects remain listable.
- Live database outage: frontend HTTP 200 in 0.028 s; readiness HTTP 200 with `blocked` in 5.085 s; after MongoDB recovery readiness HTTP 200 in 0.067 s and project count remained five.
- Live Gemini model test for `gemini-3.1-flash-lite` returned Working in 7.8 s. The full Playwright suite exercised configured Gemini paths successfully.
- RC8 trust invariants remain covered: Writer's Room author control, character chronology, atomic generation idempotency, reference reconciliation, scene ordering, visible write failures and frozen Paragraph Editor regression.

## Desktop and accessibility

The full suite exercised 1280×720 with Toolbox and Companion plus 1366×768, 1440×900, 1920×1080 and 2560×1440 layouts. Keyboard/focus, ARIA, reduced motion and frozen Paragraph Editor flows passed their existing release assertions. No console, duplicate-key or hydration failure was reported by the release run.

## Performance results

Measured artifact: `artifacts/rc9-operational-performance.json`.

| Chapters | Cold bootstrap | Warm bootstrap | Dashboard | Working set |
|---:|---:|---:|---:|---:|
| 50 | 1,137 ms | 12.98 ms | 121 ms | 57.55 MB after workload |
| 100 | 2,414 ms | 15.15 ms | 169 ms | — |
| 250 | 2,942 ms | 30.67 ms | 162 ms | 65.20 MB |
| 500 | 5,688 ms | 42.83 ms | 158 ms | 79.25 MB |
| 1,000 | 11,670 ms | 71.90 ms | 265 ms | 100.96 MB |

At 50 chapters, 30 warm-bootstrap calls had a 10.93 ms median. The long-session sample showed 0 MB retained growth after cleanup. A 500-chapter backup took 1,843 ms and validation took 823 ms. Story Bible projection remains the dominant cold path at 1,000 chapters.

## Warnings

Backend regression reports 66 non-fatal deprecation warnings: 65 from Pydantic v2 compatibility surfaces and one LangGraph serializer-default warning. They are recorded as maintenance debt rather than hidden or suppressed.
