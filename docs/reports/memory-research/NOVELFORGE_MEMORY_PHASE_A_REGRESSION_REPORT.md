# NovelForge Memory Phase A Regression Report

## P0 safety

All permanent P0 cases still pass: duplicate Chapter Intelligence, Elias chronology, POV/person shift, Mara/Lindon relationship contradiction, rejected brainstorming, candidate leakage, superseded state, future knowledge, and character-specific knowledge.

Measured gates:

- candidate/rejected leakage: 0;
- future leakage: 0;
- POV knowledge leakage: 0;
- duplicate logical hits: 0;
- real Discovery Recall@k/MRR: 1.0 / 1.0 before and after;
- 500-chapter Recall@8: 0.8333 before and after.

## Test results

- final focused Phase A + P0 + provider + restore + workflow/Story Studio: 31 passed, 1 skipped;
- complete backend: 195 passed, 7 skipped, 0 failed in 367.57 seconds;
- first 124-second backend attempt: timed out and was not counted as passed;
- frontend: 87 passed across 23 files;
- Next.js 15.5.22 production build: passed;
- browser acceptance: not required because no normal-author frontend surface changed;
- paid provider calls: zero.

The final focused 31-test set was rerun after rebuild acknowledgement and immediate decision-supersession cache invalidation changes and passed. Full-suite evidence preceding those narrow changes is retained at `artifacts/memory-phase-a/backend-full.xml`.

## Remaining warnings

The suites emit existing `datetime.utcnow()` and Pydantic deprecation warnings. They are not Phase A failures, but should be addressed separately from memory architecture work.
