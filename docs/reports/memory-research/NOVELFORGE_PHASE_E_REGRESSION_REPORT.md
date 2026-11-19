# Phase E Regression Report

## Final status

| Verification | Result |
|---|---:|
| Phase E unit tests | 6 passed |
| Orchestration/workflow focused | 26 passed, 1 skipped |
| Phase E + P0 + Phase A/provider boundary focused | 25 passed |
| Large-authority fallback integration | 1 passed |
| Complete backend | **201 passed, 7 skipped** |
| Complete frontend | **23 files, 87 tests passed** |
| Next.js production build | **PASS** |
| Matched compact real-provider workflow | **5/5 completed** |

No test was reported as passing after a timeout.

## P0 and Phase A guarantees

Focused suites confirmed:

- duplicate logical retrieval remains zero;
- candidate/rejected safe-writing policy remains active;
- chronology and future boundaries remain active;
- character-knowledge boundaries remain active;
- retrieval remains incremental/read-only under Phase A;
- Tencent remains optional and outside the Develop Story authority path.

The measured role projections contained zero unsafe candidate/rejected/stale records.

## Defects found during verification

### 1. Unique authority count versus duplicate copies

Initial compact attribution compared deduplicated authority against raw record count and selected broad fallback. Fixed by comparing unique compact authority identities.

### 2. Confirmed planning payload omission

Initial authority serialization retained planning source IDs but omitted typed `values`. Fixed before final benchmark. Final packets contain seven of seven planning records with meaning and provenance.

### 3. Broad fallback budget

The first complete backend run produced 200 passes and one failure: a legitimate large-authority broad fallback was still constrained to the compact role budget. Fixed so broad fallback uses the selected model's existing safe context budget. The failing integration test then passed, followed by a clean complete-suite run.

## Progress and resume UX

Existing orchestration tests passed with the new context shape. Runtime code still emits the same `agent_started`/completion events and maintains current agent, position, total, heartbeat, completed agents, retry/failure state, and final summary. No frontend contract or normal author-facing screen was changed.

## Build

Next.js 15.5.22 compiled, type-checked, generated all static pages, and produced the dynamic project route successfully.
