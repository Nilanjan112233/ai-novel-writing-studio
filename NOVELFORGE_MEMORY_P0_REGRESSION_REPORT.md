# NovelForge Memory P0 Regression Report

## Automated results

| Gate | Result |
| --- | --- |
| P0 plus Tencent/provider boundary | 14 passed, 0 failed |
| Focused memory/context/continuity set | 39 passed, 0 failed |
| Complete backend | 190 passed, 7 skipped, 0 failed; 463.06 seconds |
| Complete frontend | 87 passed in 23 files, 0 failed |
| Production build | passed; Next.js 15.5.22 |
| Replay diagnostics | passed; zero provider calls |
| Scale diagnostics | six scales completed; temporary database removed |

The first complete backend command timed out at 120 seconds. It is explicitly not counted. The suite was rerun with a 15-minute bound and completed in 7m43s. The seven skipped tests are recorded by pytest and are not represented as passes.

## Covered acceptance cases

- Same logical Chapter Intelligence version selects once, with multiple evidence pointers retained.
- Direct and refresh indexing share logical identity and are idempotent.
- Real duplicate pair is discoverable by dry run; isolated persisted repair deletes no authority.
- Candidate and rejected brainstorming do not enter safe-writing retrieval.
- Raw Story Studio chat does not bypass retrieval policy into Discovery active context.
- Candidate structured projection does not bypass policy into Discovery working memory.
- Older bounded ownership state is used at an earlier chapter; successor is used later.
- Future-chapter truth and knowledge private to another character are withheld.
- POV/person, chronology, relationship, ownership, knowledge, and direct-authority conflicts are classified with evidence.
- Explicitly planned POV evolution remains allowed.
- A record beyond the legacy first 2,000 is retrievable.
- All 1,005 owners in one source refresh are indexed.
- Tencent failure falls back to Native; writing-safe hybrid/Tencent modes keep Native primary.

## Artifacts

JUnit results: `artifacts/memory-p0/p0-regression.xml` and `artifacts/memory-p0/backend-full.xml`. Replay and scale JSON are described in the harness report.

## Browser acceptance decision

No browser-only behavior or user-facing frontend component changed. Running a browser generation flow would either duplicate API coverage or trigger a paid writing call, so it was not appropriate. Frontend tests, TypeScript/build validation, and static page generation all passed. The previously running frontend dev server was stopped for a clean build and restored on port 3000 afterward.

## Open regressions/limitations

- Complete scans are slower, especially at 500 chapters.
- Scale Recall@8 is 0.8333 rather than 1.0 at 250 and 500 chapters.
- Existing old projects lack complete chronology/knowledge metadata.
- Historical Develop Story packets lack full per-source attribution; new packets will include it.
- Continuity checks are intentionally high-confidence, not general semantic reasoning.

