# NovelForge Narrative Studio V2 - Phase 1B E2E Results

Validation date: 2026-06-14

Status: Passed

Scenario: `The Chronicles of Elysium`

Provider: Google Gemini

Model: `gemini-3.1-flash-lite`

## Story Validation

| Story area | Persisted result | Expected |
| --- | --- | --- |
| Arc 1 | Approved, `READY`, drafting eligible | Draftable |
| Arc 2 | Discussed, `PARTIALLY_READY` | Planning may continue |
| Arc 3 | Draft, `NOT_READY` | May remain incomplete |
| Timeline | 8 known, 3 unknown | Uncertainty retained |
| Progression | 1 arc-specific Elara record | Supported |
| Knowledge | Reader, character, and world layers | Supported |
| Foreshadow | 1 seeded registry record | Supported |
| Artifact | 1 linked artifact record | Supported |

Arc 1 remained eligible despite unresolved Arc 2 and Arc 3 work. The generated
draft arc proposal remained non-eligible and did not block the approved arc.

## Hidden Reader Layer

The E2E scenario persisted:

- World truth: the compass contains a sleeping name.
- Reader knowledge: the compass glows near the old name.
- Character knowledge: Elara falsely believes the compass is only a map.
- `not_known_by`: Elara and Soren on the reader clue.

The API rejected contradictory overlap between `known_by` and
`not_known_by`. KnowledgeAgent later added valid world-truth entries without
collapsing the three knowledge layers.

## Dynamic Orchestration

| Cycle | Affected domains | Selected | Skipped |
| --- | --- | ---: | ---: |
| 1 | Concept, theme | 6 | 8 |
| 2 | Arc, readiness | 3 | 11 |
| 3 | Timeline, arc, progression, knowledge, foreshadow, artifact | 9 | 5 |

Measured totals:

| Metric | Result |
| --- | ---: |
| Cycles | 3 |
| Selected calls | 18 |
| Skipped task decisions | 24 |
| Persisted task decisions | 42 |
| Average calls per cycle | 6.0 |
| Skip percentage | 57.1% |
| Orchestration cost | $0.072800 |

Readiness changes selected ReadinessAgent and arc/pacing analysis. Knowledge
changes selected KnowledgeAgent and impacted planning agents. Unaffected agents
were persisted with skip reasons.

## Provider And Memory Audit

- Phase 1B project traces: 18 successful Gemini calls.
- Configured limiter: 5 requests per minute.
- Recorded limiter wait: 30,512 ms.
- Phase 1B project retries: 0.
- Full Playwright run also exercised a transient Gemini 503 retry successfully.
- Provider trace cost: $0.047062.
- Active bounded memories: 36.
- Active memory tiers: 18 important, 18 recent.
- ReadinessAgent: 1 important and 1 recent record.
- KnowledgeAgent: 1 important and 1 recent record.

## Database Audit

Scenario document counts:

| Collection | Count |
| --- | ---: |
| `story_readiness` | 8 |
| `timeline_entries` | 11 |
| `character_progressions` | 1 |
| `knowledge_entries` | 5 |
| `foreshadow_registry_v2` | 1 |
| `artifact_registry` | 1 |
| `agent_memories` | 36 |
| `orchestration_plans` | 3 |
| `execution_traces` | 18 |

All Phase 1B named indexes were present. A repeated migration inserted zero
legacy timeline records, confirming deduplication.

## UI And Automated Validation

- Readiness Dashboard rendered status groups and drafting eligibility.
- Arc Board rendered lifecycle columns.
- Knowledge View rendered reader, character, and world layers.
- Timeline V2 rendered arc-grouped known and unknown entries.
- Screenshot: `artifacts/phase-1b-chronicles-of-elysium.png`

| Suite | Result |
| --- | --- |
| Backend pytest | 59 passed, 7 skipped |
| Frontend Vitest | 43 passed |
| Next.js production build | Passed |
| Playwright | 18 passed, 2 skipped |
| Playwright unexpected failures | 0 |
| Real Gemini Phase 1B scenario | Passed |

## Conclusion

NovelForge can draft the approved current arc without requiring future-story
completion. Partial planning and explicit unknowns coexist, typed narrative
knowledge remains consistent, bounded memory persists, and production
orchestration remains demand-driven.

