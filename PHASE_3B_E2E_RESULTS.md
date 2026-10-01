# NovelForge Narrative Studio V2 - Phase 3B E2E Results

Validation date: 2026-06-14

## Result

Passed.

Scenario: `The Eternal Throne 1781437449598`

Project ID: `6a2e9409c8b269f54233b5a7`

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

Configured provider limit: 5 requests per minute

## Source Authority

The scenario created:

- one approved arc;
- one approved chapter plan;
- one approved scene plan;
- one approved scene draft;
- one approved chapter draft;
- one Phase 3A chapter editorial score.

The manuscript was assembled from the approved chapter draft only.

Verified:

- approved chapter text remained byte-for-byte unchanged;
- source scene lineage remained attached;
- a SHA-256 source text hash was stored;
- no manuscript or canon agent rewrote planning or draft content.

## Manuscript Results

| Metric | Result |
| --- | --- |
| Manuscripts | 1 |
| Manuscript versions | 1 |
| Source chapters | 1 |
| Active version | 1 |
| Validation | PASS |
| Final lifecycle | approved |
| Manual approval | verified |
| Version-to-manuscript links | valid |
| Source text hash | present |

Three manuscript/canon report records were persisted.

## Canon Results

Two artifact authority records were promoted for the same subject and field
with contradictory values.

The deterministic validator produced:

- result: `FAIL`;
- conflict type: `artifact_authority_conflict`;
- severity: `high`;
- persisted conflict status: `open`.

Targeted backend regression also verified that deactivating superseded
authority clears the active conflict without deleting history.

## Dynamic Orchestration

| Action | Selected | Skipped | Calls | Status |
| --- | --- | ---: | ---: | --- |
| Manuscript review | `ManuscriptAgent` | 21 | 1 | completed |
| Canon review | `CanonAgent` | 21 | 1 | completed |

Metrics:

- explicit review plans: 2;
- total agent calls: 2;
- average selected agents per plan: 1.0;
- selection skip rate: 95.45%;
- recursive follow-up calls: 0;
- deterministic assembly provider calls: 0;
- deterministic validation provider calls: 0.

Unrelated agents were persisted as skipped with selection reasons.

## Provider Traces

| Agent | Provider | Model | Cost | Retries | Result |
| --- | --- | --- | ---: | ---: | --- |
| `ManuscriptAgent` | Gemini | `gemini-3.1-flash-lite` | $0.000492 | 0 | success |
| `CanonAgent` | Gemini | `gemini-3.1-flash-lite` | $0.000620 | 0 | success |

Observed total review cost: $0.001112.

No 429 response occurred in the final scenario. The full Playwright suite also
exercised transient-provider retry behavior successfully.

## Database Audit

The production project-scoped audit returned:

```json
{
  "status": "pass",
  "findings": [],
  "phase_3b_counts": {
    "manuscripts": 1,
    "manuscript_versions": 1,
    "manuscript_reports": 3,
    "canon_registry": 2,
    "canon_conflicts": 1
  }
}
```

All Phase 3B records had project ownership. Manuscript/version links and canon
source links were valid.

## UI Validation

The in-app browser verified:

- Manuscript Workspace rendering;
- approved manuscript status;
- active version and PASS validation;
- report rendering;
- Canon Dashboard rendering;
- active typed canon;
- high-severity conflict rendering;
- no browser console warnings or errors.

Screenshots:

- `test-results/manuscript-v3-Phase-3B-man-ff39f-ne-with-real-Gemini-reviews-chromium/phase-3b-manuscript-workspace.png`
- `test-results/manuscript-v3-Phase-3B-man-ff39f-ne-with-real-Gemini-reviews-chromium/phase-3b-canon-dashboard.png`

## Test Matrix

| Test surface | Result |
| --- | --- |
| Backend | 77 passed, 7 skipped |
| Frontend | 48 passed |
| Production build | passed |
| Full Playwright | 22 passed, 2 intentionally skipped |
| Final real-Gemini Phase 3B Playwright | 1 passed |
| Migration twice | passed, zero changed records |
| Plaintext Google-key scan | no findings |
| Forbidden publishing-agent scan | no findings |

## Acceptance

Phase 3B passed:

- manuscript assembly and immutable versions;
- version lineage and rollback coverage;
- book-level deterministic validation;
- typed canon registry and conflict detection;
- manual manuscript approval;
- approved chapter authority preservation;
- bounded dynamic orchestration;
- project ownership enforcement;
- migration idempotency;
- real Gemini review execution.

No EPUB, PDF, DOCX, publishing, collaboration, or autonomous manuscript
generation capability was introduced.
