# NovelForge Memory Phase B Regression Report

## Automated verification

- Final complete backend after supersession and chronology-overlap tightening: 206 passed, 7 skipped (12m51s).
- Final focused P0/Phase A/Phase B/Phase E matrix: 24 passed.
- Chapter Intelligence compatibility rerun: passed.
- Frontend: 23 files, 87 tests passed.
- Next.js production build: passed.
- Phase B provider-free scale corpus: completed at all six scales.
- Real-provider matched Develop Story: completed, five calls, zero fallback.

One targeted run initially reported 55 passed and one failure: the compact chapter-memory response had removed the established top-level `chapter_number`. The compatibility field was restored, specialist-only projection was isolated, and all subsequent focused/full tests passed.

## Safety outcomes

Candidate leakage, rejected leakage, future leakage, POV knowledge leakage, and duplicate logical hits remain zero in replay/scale results. Contradictory derived atomics cannot compete with authority. Chronology-bounded historical atomics remain available for as-of retrieval.

## Scope verification

No frontend contract changed, no authority schema was replaced, and no Tencent dependency was introduced.
