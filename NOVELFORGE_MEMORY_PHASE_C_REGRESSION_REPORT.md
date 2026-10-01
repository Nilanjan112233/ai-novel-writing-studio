# NovelForge Memory Phase C Regression Report

## Automated verification

| Suite | Result |
|---|---|
| Focused P0/A/B/C/E, orchestration, Story Studio | 57 passed |
| Final memory safety/index tests after eligibility refactor | 21 passed |
| Phase A/Phase C status and cache checks | 8 passed |
| Complete backend | 209 passed, 7 skipped, no timeout |
| Complete frontend | 87 passed across 23 files |
| Production build | passed, Next.js 15.5.22 |

The final-state backend suite completed in 435.13 seconds. The frontend suite completed in 15.39 seconds; production build completed in 45 seconds. Deprecation warnings remain pre-existing and are not reported as failures.

## Permanent safety cases

The regression matrix retains:

- duplicate Chapter Intelligence identity: pass, zero logical duplicate hits;
- authoritative chronology conflict: pass;
- POV/person continuity detection: pass;
- confirmed relationship contradiction: pass;
- rejected brainstorming: pass;
- candidate leakage: pass;
- superseded state: pass;
- future knowledge: pass;
- character-specific knowledge: pass.

Across Phase C scale tests: candidate/rejected/future/POV leakage is zero and duplicate logical hits are zero. Authority, chronology, and knowledge filtering execute before Phase C scoring.

## Failure/fallback cases

Focused tests cover missing/corrupt Phase C readiness and verify complete Phase B retrieval. Phase A tests continue to cover interrupted rebuild, duplicate delivery, replay, mismatch detection, backup/restore, and index recovery. Tencent remains unnecessary. Phase C checkpoints are derived and excluded from backup.

The first parallel full-suite launch was not counted: its frontend artifact path was invalid and the launch returned before a result. Both suites were rerun cleanly to the results above. The initial Develop Story harness setup failure likewise made zero provider calls and was not counted as a matched run.

Test logs are retained in `artifacts/memory-phase-c/`.
