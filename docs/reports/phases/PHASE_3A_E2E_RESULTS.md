# NovelForge Narrative Studio V2 - Phase 3A E2E Results

Validation date: 2026-06-14

## Result

Passed.

Scenario: `The Kingdom of Ash and Stars 1781426823855`

Project ID: `6a2e6a8771f06421d23d670e`

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

## Planning And Draft Authority

Arc 1 reached:

- readiness: READY;
- maturity: 100;
- development state: draftable;
- checklist blockers: 0;
- dependency blockers: 0.

The scenario created:

- two approved chapter plans;
- two approved Scene Plan V2 records;
- two approved scene drafts;
- two approved chapter drafts.

The approved source scene was captured before editorial work and compared
after revision generation. It remained byte-for-byte unchanged.

## Editorial Results

Persisted reports:

| Report type | Count |
| --- | ---: |
| Scene editorial | 2 |
| Scene dialogue | 2 |
| Chapter editorial | 2 |
| Arc editorial | 1 |
| Total | 7 |

Persisted deterministic score records: 11

Score types:

- `scene_editorial`
- `chapter_editorial`
- `arc_editorial`

Observed score range after 0-100 normalization: 67-93.

The dashboard exposed findings, recommendations, scores, pending revision
work, and blockers without granting approval authority to an agent.

## Revision Results

- revision branches: 1
- revision versions: 1
- source version preserved: yes
- source SHA-256 verification: passed
- branch status after scenario: review
- lineage versions: 1
- source-versus-revision comparison: passed
- automatic source replacement: 0
- automatic approvals: 0

## Dynamic Orchestration

Editorial traces:

| Agent | Calls |
| --- | ---: |
| `EditorAgent` | 5 |
| `DialogueAgent` | 2 |
| `RevisionAgent` | 1 |
| Total | 8 |

Each explicit request selected exactly one editorial agent. All unrelated
agents were persisted as skipped with selection reasons.

Planning changes did not invoke editorial agents, and editorial actions did
not invoke drafting agents recursively.

## Provider Metrics

- successful editorial-agent traces: 8
- tokens: 33,027
- recorded cost: USD 0.013210
- total limiter wait: 28,358 ms
- configured limit: 5 requests/minute
- maximum admissions in any rolling 60-second window: 5
- retries in final persisted scenario: 0

An earlier targeted run received a live Gemini HTTP 503. The provider gateway
recorded the transient failure, applied exponential backoff, retried, and
completed successfully. The final full-suite scenario required no retries.

## UI Validation

Playwright verified:

- the authority notice that approved drafts remain authoritative;
- editorial score cards;
- scene, chapter, dialogue, and arc reports;
- the revision branch and proposal;
- revision comparison;
- editorial and revision status.

Screenshot:

`test-results/editorial-v3-Phase-3A-edit-edfa9-ut-replacing-approved-prose-chromium/kingdom-of-ash-and-stars-editorial.png`

The screenshot size is 115,060 bytes.

The same workspace was inspected through the in-app browser. It rendered the
authority notice, persisted branch, and arc score with zero console errors.

## Full Test Matrix

- Backend full suite: 72 passed, 7 skipped.
- Frontend: 46 passed.
- Production build: passed.
- Full Playwright: 21 passed, 2 intentionally skipped.
- Real Gemini Phase 3A scenario: passed.
- Phase 1A, 1B, 2A, and 2B Playwright regressions: passed.
- Migration rerun: passed.
- Plaintext credential scan: clean.
- Public settings credential contract: clean.
- Forbidden manuscript-agent scan: clean.

Phase 3A editorial intelligence, revision governance, authority preservation,
dynamic orchestration, rate limiting, migration, security, and UI gates all
passed.
