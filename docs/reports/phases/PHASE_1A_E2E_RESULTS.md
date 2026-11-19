# NovelForge Narrative Studio V2 - Phase 1A E2E Results

Validation date: 2026-06-13

Status: Passed

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

Scenario: `The Ashes of Valeria`

## Story Simulation

| Cycle | Change | Selected agents | Calls | Skipped |
| --- | --- | --- | ---: | ---: |
| 1 | Project premise | NarrativeDirector, StoryArchitect, Question, Theme, ArcArchitect, Pacing | 6 | 6 |
| 2 | Protagonist notes | CharacterJourney, Relationship, ArcArchitect, Pacing | 4 | 8 |
| 3 | World detail | World, Faction | 2 | 10 |
| 4 | No-op world update | None | 0 | 12 |

Cycle 2 skipped PowerSystem, World, and Faction. Cycle 3 skipped
CharacterJourney. Cycle 4 terminated without provider execution.

## Orchestration Metrics

| Metric | Result | Requirement |
| --- | ---: | ---: |
| Total cycles | 4 | 4 |
| Total agent calls | 12 | Below static baseline |
| Static 12-agent baseline | 48 | Reference |
| Average agents per cycle | 3.0 | Less than 5 |
| Skip percentage | 75% | At least 50% |
| Call reduction | 75% | At least 50% |
| Budget usage | $0.031380 | At most $2.00 per cycle |
| Provider traces | 12 | Equal to calls |
| Tasks persisted | 48 | 12 per plan |

All four plans completed. Each plan persisted selected agents, skipped agents,
selection reasons, limits, actual calls, actual cost, and a task for every
planning agent.

## Rate Limit Audit

- Configured Gemini limit: 5 requests/minute.
- Every provider trace recorded limit 5.
- Observed limiter waits included 22,140 ms, 5,046 ms, 6,796 ms, and 5,515 ms.
- Retry count was zero for all 12 successful requests.
- All real provider calls returned successfully.
- No provider storm or orchestration loop occurred.

## Database Audit

- `orchestration_plans`: present and indexed.
- `orchestration_tasks`: present and indexed.
- Plan task counts: 12, 12, 12, 12.
- Required workflow, Bible, memory, event, and trace indexes: present.
- Configured provider plaintext key fields: empty.
- Configured Gemini and OpenRouter credentials: encrypted at rest.
- Ashes project memory records: 30 active and 1 retained inactive predecessor.

## API And UI Audit

- Latest orchestration endpoint returned the no-op plan and stop reason.
- History endpoint returned all four plans in cycle history.
- Orchestration Inspector rendered selected and skipped agents, reasons,
  execution graph, status, and no-change stop reason.
- Workspace run status was terminal after the Story Bible rebuild.
- Screenshot:
  `artifacts/phase-1a-orchestration-inspector.png`

## Automated Validation

| Suite | Result |
| --- | --- |
| Backend pytest | 55 passed, 7 skipped |
| Frontend Vitest | 40 passed |
| Next.js production build | Passed |
| Playwright | 17 passed, 2 skipped |
| Real Gemini orchestration | Passed |

The Playwright scenario also asserts that the workspace header does not remain
in `running` state after the no-op cycle reaches its terminal state.

## Conclusion

The active production path is demand-driven. The default static 12-agent cycle
has been removed from `/run` and `/cycle`, unrelated agents are skipped with
persisted explanations, limits are enforced, and no-change work terminates
without provider execution.
